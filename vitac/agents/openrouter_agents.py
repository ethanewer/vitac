"""OpenRouter-based agents for running benchmarks with various models."""

from __future__ import annotations

import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Optional

from openai import OpenAI

from vitac.agents.base_agent import CollaboratorAgent, PrimaryAgent
from vitac.types import AgentResult, VoiceMessage
from vitac.voice import VoiceQueue

logger = logging.getLogger(__name__)

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)


def _strip_thinking(text: str) -> str:
    """Strip <think>...</think> tags from model output."""
    return _THINK_RE.sub("", text).strip()


class OpenRouterPrimaryAgent(PrimaryAgent):
    """Primary agent that uses OpenRouter-hosted models."""

    def __init__(self, model: str):
        self._model = model
        self._client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.environ["OPENROUTER_API_KEY"],
        )

    @staticmethod
    def name() -> str:
        return "openrouter-primary"

    def perform_task(
        self,
        instruction: str,
        session,  # TmuxSession
        voice_queue: VoiceQueue,
        logging_dir: Path | None = None,
    ) -> AgentResult:
        total_input = 0
        total_output = 0

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a terminal agent that completes tasks by running shell commands. "
                    "You can also communicate with a collaborator via text messages to get "
                    "clarification, missing information, or approval.\n\n"
                    "You must respond with a JSON object with one of these formats:\n"
                    '{"action": "ask", "message": "your question to the collaborator"}\n'
                    '{"action": "command", "command": "shell command to run"}\n'
                    '{"action": "done"}\n\n'
                    "IMPORTANT RULES:\n"
                    "- Before taking any destructive or irreversible action, ASK the collaborator for details.\n"
                    "- If the instruction is vague or missing information, ASK before acting.\n"
                    "- After running commands, check the output and decide your next step.\n"
                    "- When you believe the task is complete, respond with done.\n"
                    "- Only respond with valid JSON, nothing else.\n"
                    "- Commands MUST be single-line. No multi-line scripts. No heredocs.\n"
                    "- Keep commands simple and short. Avoid piping through many tools.\n"
                    "- Do NOT use set -euo pipefail or other shell options in commands."
                ),
            },
            {
                "role": "user",
                "content": f"Task instruction:\n{instruction}\n\nWhat would you like to do first?",
            },
        ]

        max_steps = 30
        for step in range(max_steps):
            inbox = voice_queue.receive("primary")
            for msg in inbox:
                text = msg.transcript or msg.audio.decode("utf-8", errors="replace")
                messages.append({
                    "role": "user",
                    "content": f"Message from collaborator: {text}",
                })

            try:
                response = self._client.chat.completions.create(
                    model=self._model,
                    messages=messages,
                    max_tokens=512,
                    extra_body={"provider": {"require_parameters": True}, "reasoning": {"effort": "none"}},
                )
            except Exception as e:
                logger.error(f"OpenRouter API error: {e}")
                break

            total_input += response.usage.prompt_tokens if response.usage else 0
            total_output += response.usage.completion_tokens if response.usage else 0

            raw = response.choices[0].message.content.strip()
            messages.append({"role": "assistant", "content": raw})

            # Strip thinking tags and extract first JSON object
            raw = _strip_thinking(raw)

            try:
                if raw.startswith("```"):
                    raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
                # Extract first JSON object if multiple are present
                brace_start = raw.find("{")
                if brace_start >= 0:
                    depth = 0
                    for i in range(brace_start, len(raw)):
                        if raw[i] == "{":
                            depth += 1
                        elif raw[i] == "}":
                            depth -= 1
                            if depth == 0:
                                raw = raw[brace_start:i + 1]
                                break
                action = json.loads(raw)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse agent response: {raw}")
                messages.append({
                    "role": "user",
                    "content": "Your response was not valid JSON. Please respond with a JSON object.",
                })
                continue

            act_type = action.get("action", "")

            if act_type == "ask":
                text = action.get("message", "")
                logger.info(f"[primary -> collaborator] {text}")
                msg = VoiceMessage(
                    sender="primary",
                    recipient="collaborator",
                    episode_id="",
                    task_id="",
                    audio=text.encode("utf-8"),
                    transcript=text,
                )
                voice_queue.send(msg)
                got_response = False
                for _ in range(15):
                    time.sleep(0.2)
                    inbox = voice_queue.receive("primary")
                    if inbox:
                        for m in inbox:
                            t = m.transcript or m.audio.decode("utf-8", errors="replace")
                            logger.info(f"[collaborator -> primary] {t}")
                            messages.append({
                                "role": "user",
                                "content": f"Message from collaborator: {t}",
                            })
                        got_response = True
                        break
                if not got_response:
                    messages.append({
                        "role": "user",
                        "content": (
                            "The collaborator did not respond. "
                            "Proceed with the task using your best judgment. "
                            "Do NOT ask again — just do your best with the information you have."
                        ),
                    })

            elif act_type == "command":
                cmd = action.get("command", "")
                cmd = cmd.split("\n")[0].strip()
                if not cmd:
                    messages.append({
                        "role": "user",
                        "content": "Empty command. Please provide a valid single-line command.",
                    })
                    continue
                logger.info(f"[primary] Running: {cmd}")
                voice_queue.record_terminal_command(cmd)
                try:
                    session.send_keys(
                        [cmd, "Enter"],
                        block=True,
                        max_timeout_sec=15,
                    )
                except TimeoutError:
                    logger.warning(f"Command timed out: {cmd}")
                    session.send_keys(["C-c"], min_timeout_sec=0.5)

                time.sleep(0.5)
                output = session.capture_pane(capture_entire=True)
                lines = output.strip().splitlines()
                if len(lines) > 100:
                    output = "\n".join(lines[-100:])
                messages.append({
                    "role": "user",
                    "content": f"Terminal output:\n{output}",
                })

            elif act_type == "done":
                logger.info("[primary] Task marked as done")
                break

            else:
                messages.append({
                    "role": "user",
                    "content": f"Unknown action '{act_type}'. Use 'ask', 'command', or 'done'.",
                })

        return AgentResult(
            total_input_tokens=total_input,
            total_output_tokens=total_output,
        )


class OpenRouterCollaboratorAgent(CollaboratorAgent):
    """Collaborator agent that uses OpenRouter-hosted models."""

    def __init__(self, model: str):
        self._model = model
        self._client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.environ["OPENROUTER_API_KEY"],
        )

    @staticmethod
    def name() -> str:
        return "openrouter-collaborator"

    def respond(
        self,
        inbox: list[VoiceMessage],
        context: str,
    ) -> Optional[VoiceMessage]:
        if not inbox:
            return None

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a collaborator helping an agent complete a task. "
                    "You have the following context and knowledge:\n\n"
                    f"{context}\n\n"
                    "Answer the agent's questions based ONLY on this context. "
                    "Be concise and direct. Only provide information that is asked about. "
                    "Do not volunteer extra information."
                ),
            },
        ]

        for msg in inbox:
            text = msg.transcript or msg.audio.decode("utf-8", errors="replace")
            messages.append({"role": "user", "content": text})

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                max_tokens=256,
                extra_body={"provider": {"require_parameters": True}, "reasoning": {"effort": "none"}},
            )
        except Exception as e:
            logger.error(f"OpenRouter collaborator API error: {e}")
            return None

        reply_text = _strip_thinking(response.choices[0].message.content.strip())
        logger.info(f"[collaborator] {reply_text}")

        return VoiceMessage(
            sender="collaborator",
            recipient="primary",
            episode_id="",
            task_id="",
            audio=reply_text.encode("utf-8"),
            transcript=reply_text,
        )


# Thin subclasses with hardcoded models for agent_factory (which calls cls() with no args)

class Qwen35FlashPrimary(OpenRouterPrimaryAgent):
    def __init__(self): super().__init__("qwen/qwen3.5-flash-02-23")

class Qwen35FlashCollaborator(OpenRouterCollaboratorAgent):
    def __init__(self): super().__init__("qwen/qwen3.5-flash-02-23")

class Qwen359bPrimary(OpenRouterPrimaryAgent):
    def __init__(self): super().__init__("qwen/qwen3.5-9b")

class Qwen359bCollaborator(OpenRouterCollaboratorAgent):
    def __init__(self): super().__init__("qwen/qwen3.5-9b")
