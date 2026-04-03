"""Voice interaction evaluation using Gemini Flash Lite via OpenRouter.

Analyzes voice message transcripts and text segments from a trial to score
the quality of voice communication on multiple dimensions.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from vitac.types import TaskDef, VoiceScoreCard
from vitac.voice import VoiceQueue

logger = logging.getLogger(__name__)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
EVAL_MODEL = "google/gemini-3.1-flash-lite-preview"

EVAL_PROMPT = """\
You are an expert evaluator of voice-based AI agent communication quality.

You will be given:
1. A task instruction that was given to an AI agent
2. Voice message transcripts — these are the ACTUAL AUDIO messages exchanged between a primary agent (who executes commands) and a collaborator agent (who has domain knowledge). These were spoken aloud as audio.
3. Text segments — these include both spoken text AND internal agent reasoning that was NOT spoken aloud. The spoken portions overlap with voice messages. Internal reasoning text was never heard by anyone.

IMPORTANT: Focus your evaluation on the VOICE MESSAGES, which represent what was actually spoken and heard. The text segments provide context but include internal reasoning that should be ignored when scoring naturalness and clarity.

Your job is to evaluate the PRIMARY agent's voice communication quality on these dimensions:

## Scoring Dimensions (each 0.0 to 1.0)

### naturalness (0.0–1.0)
Does the primary agent's SPOKEN output (voice messages) sound natural and conversational?
- 1.0: Sounds like a real person talking. No markdown, no code, no file paths, no special characters in spoken output.
- 0.5: Mostly conversational but occasionally includes technical artifacts (file paths, code snippets, markdown formatting) in spoken output.
- 0.0: Spoken output reads like a text document — full of markdown, code blocks, structured lists, or raw technical output.

### clarity (0.0–1.0)
Is the spoken communication clear and easy to understand when heard aloud?
- 1.0: Every spoken utterance would be perfectly clear if heard as audio. No ambiguity.
- 0.5: Generally clear but some spoken utterances would be confusing as audio.
- 0.0: Much of the spoken output would be incomprehensible or confusing as audio.

### conciseness (0.0–1.0)
Is the agent appropriately brief in what it speaks?
- 1.0: Short, to-the-point spoken utterances. No unnecessary narration of thinking process, no filler phrases.
- 0.5: Some unnecessary verbosity in spoken output.
- 0.0: Extremely verbose spoken output. Long monologues, excessive detail.

### relevance (0.0–1.0)
Does the agent avoid speaking irrelevant implementation details?
- 1.0: Only speaks information the listener needs to hear. Does not mention internal details, file paths, exact commands, or implementation specifics.
- 0.5: Sometimes speaks implementation details the listener doesn't need.
- 0.0: Frequently dumps technical details into spoken output.

### task_communication (0.0–1.0)
Does the agent communicate effectively about the task via voice?
- 1.0: Asks clear questions to the collaborator. Acknowledges answers. Summarizes results concisely when done. Good conversational flow.
- 0.5: Communicates about the task but sometimes fails to ask needed questions, or gives awkward summaries.
- 0.0: Poor task communication — doesn't ask questions when needed, doesn't summarize, or doesn't acknowledge collaborator input.

## Input Data

### Task Instruction
{instruction}

### Voice Messages (actual audio exchanged, chronological)
{voice_messages}

### Text Segments (includes spoken text AND internal reasoning, chronological)
{text_segments}

## Output Format

Respond with ONLY a JSON object (no markdown, no explanation) with this exact structure:
{{"naturalness": <float>, "clarity": <float>, "conciseness": <float>, "relevance": <float>, "task_communication": <float>, "reasoning": "<brief explanation of scores>"}}
"""


def _call_openrouter(prompt: str) -> dict | None:
    """Call Gemini Flash Lite via OpenRouter and return parsed JSON response."""
    import httpx

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        logger.warning("OPENROUTER_API_KEY not set — skipping voice evaluation")
        return None

    try:
        response = httpx.post(
            f"{OPENROUTER_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": EVAL_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "max_tokens": 512,
            },
            timeout=60.0,
        )
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"].strip()

        # Strip markdown code fences if present
        if content.startswith("```"):
            lines = content.split("\n")
            # Remove first and last lines (the fences)
            lines = [l for l in lines if not l.strip().startswith("```")]
            content = "\n".join(lines).strip()

        return json.loads(content)
    except Exception as e:
        logger.error(f"Voice evaluation API call failed: {e}")
        return None


def evaluate_voice_interaction(
    task: TaskDef,
    voice_queue: VoiceQueue,
    agent_logs_dir: Path | None = None,
) -> VoiceScoreCard:
    """Evaluate voice communication quality using Gemini Flash Lite.

    Loads transcript data from the ts-runner result JSON if available,
    falls back to voice_queue messages otherwise.
    """
    voice_messages_text = ""
    text_segments_text = ""

    # Try to load rich data from ts-runner result
    ts_result = None
    if agent_logs_dir:
        ts_result_path = agent_logs_dir / "ts-runner-result.json"
        if ts_result_path.exists():
            try:
                ts_result = json.loads(ts_result_path.read_text())
            except Exception as e:
                logger.warning(f"Failed to load ts-runner result: {e}")

    if ts_result:
        # Format voice messages from ts-runner data
        msgs = ts_result.get("voiceMessages", [])
        if msgs:
            lines = []
            for m in msgs:
                sender = m.get("sender", "?")
                recipient = m.get("recipient", "?")
                transcript = m.get("transcript", "[no transcript]")
                lines.append(f"[{sender} -> {recipient}]: {transcript}")
            voice_messages_text = "\n".join(lines)

        # Format text segments
        segments = ts_result.get("textSegments", [])
        if segments:
            lines = []
            for s in segments:
                speaker = s.get("speaker", "?")
                text = s.get("text", "")
                lines.append(f"[{speaker}]: {text}")
            text_segments_text = "\n".join(lines)
    else:
        # Fall back to voice queue data
        all_msgs = voice_queue.all_messages
        if all_msgs:
            lines = []
            for m in all_msgs:
                lines.append(
                    f"[{m.sender} -> {m.recipient}]: {m.transcript or '[no transcript]'}"
                )
            voice_messages_text = "\n".join(lines)

    if not voice_messages_text and not text_segments_text:
        logger.warning("No voice data available for evaluation")
        return VoiceScoreCard(details={"error": "no_voice_data"})

    # Build the evaluation prompt
    prompt = EVAL_PROMPT.format(
        instruction=task.instruction,
        voice_messages=voice_messages_text or "(no voice messages recorded)",
        text_segments=text_segments_text or "(no text segments recorded)",
    )

    result = _call_openrouter(prompt)
    if result is None:
        return VoiceScoreCard(details={"error": "api_call_failed"})

    # Extract scores with defaults
    naturalness = float(result.get("naturalness", 0.0))
    clarity = float(result.get("clarity", 0.0))
    conciseness = float(result.get("conciseness", 0.0))
    relevance = float(result.get("relevance", 0.0))
    task_comm = float(result.get("task_communication", 0.0))

    # Clamp to [0, 1]
    naturalness = max(0.0, min(1.0, naturalness))
    clarity = max(0.0, min(1.0, clarity))
    conciseness = max(0.0, min(1.0, conciseness))
    relevance = max(0.0, min(1.0, relevance))
    task_comm = max(0.0, min(1.0, task_comm))

    # Weighted overall: naturalness and relevance matter most for voice quality
    overall = (
        0.25 * naturalness
        + 0.15 * clarity
        + 0.20 * conciseness
        + 0.25 * relevance
        + 0.15 * task_comm
    )

    reasoning = result.get("reasoning", "")

    return VoiceScoreCard(
        naturalness=naturalness,
        clarity=clarity,
        conciseness=conciseness,
        relevance=relevance,
        task_communication=task_comm,
        overall=overall,
        details={"reasoning": reasoning, "model": EVAL_MODEL},
    )
