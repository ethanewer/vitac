"""OpenAI-based primary and collaborator agents for debugging with text messages."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Optional

from openai import OpenAI

from vitac.agents.base_agent import CollaboratorAgent, PrimaryAgent
from vitac.types import AgentResult, VoiceMessage
from vitac.voice import VoiceQueue

logger = logging.getLogger(__name__)

MODEL = "gpt-5.4-nano"


class OpenAIPrimaryAgent(PrimaryAgent):
    """Primary agent that uses OpenAI to decide when to ask questions vs run commands."""

    @staticmethod
    def name() -> str:
        return f"openai-primary-{MODEL}"

    def __init__(self, model: str = MODEL):
        self._model = model
        self._client = OpenAI()

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
            # Check for incoming messages from collaborator
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
                    max_completion_tokens=512,
                    reasoning_effort="medium",
                )
            except Exception as e:
                logger.error(f"OpenAI API error: {e}")
                break

            total_input += response.usage.prompt_tokens
            total_output += response.usage.completion_tokens

            raw = response.choices[0].message.content.strip()
            messages.append({"role": "assistant", "content": raw})

            # Parse the JSON action
            try:
                # Handle markdown code blocks
                if raw.startswith("```"):
                    raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
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
                # Send message to collaborator
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
                # Wait briefly for collaborator response (max 3s, non-blocking)
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
                # Sanitize: take only first line if multi-line
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
                    # Send Ctrl-C to cancel any stuck command
                    session.send_keys(["C-c"], min_timeout_sec=0.5)

                time.sleep(0.5)
                output = session.capture_pane(capture_entire=True)
                # Only send last 100 lines to keep context manageable
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


class OpenAICollaboratorAgent(CollaboratorAgent):
    """Collaborator agent that uses OpenAI to respond based on context.

    Stateless per-call: each respond() builds a fresh conversation from context + inbox.
    Thread-safe for concurrent trials.
    """

    @staticmethod
    def name() -> str:
        return f"openai-collaborator-{MODEL}"

    def __init__(self, model: str = MODEL):
        self._model = model
        self._client = OpenAI()

    def respond(
        self,
        inbox: list[VoiceMessage],
        context: str,
    ) -> Optional[VoiceMessage]:
        if not inbox:
            return None

        # Build a fresh conversation each call (stateless — safe for concurrent use)
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
                max_completion_tokens=256,
                reasoning_effort="medium",
            )
        except Exception as e:
            logger.error(f"OpenAI collaborator API error: {e}")
            return None

        reply_text = response.choices[0].message.content.strip()
        logger.info(f"[collaborator] {reply_text}")

        return VoiceMessage(
            sender="collaborator",
            recipient="primary",
            episode_id="",
            task_id="",
            audio=reply_text.encode("utf-8"),
            transcript=reply_text,
        )


class NoOpCollaboratorAgent(CollaboratorAgent):
    """Collaborator that never responds. For testing single-agent mode."""

    @staticmethod
    def name() -> str:
        return "noop-collaborator"

    def respond(
        self,
        inbox: list[VoiceMessage],
        context: str,
    ) -> Optional[VoiceMessage]:
        return None
