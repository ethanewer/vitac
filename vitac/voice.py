"""Voice message queue and TTS/STT helpers."""

from __future__ import annotations

import io
import random
import string
import threading
from collections import deque
from datetime import datetime
from typing import Optional

from vitac.types import TranscriptMode, VoiceMessage


class VoiceQueue:
    """FIFO voice message queues per recipient.

    Enforces the voice-only communication constraint by being the sole
    channel between agents. Applies transcript mode rules on send.
    """

    def __init__(self, transcript_mode: TranscriptMode) -> None:
        self.transcript_mode = transcript_mode
        self._queues: dict[str, deque[VoiceMessage]] = {
            "primary": deque(),
            "collaborator": deque(),
        }
        self._lock = threading.Lock()
        self._all_messages: list[VoiceMessage] = []
        self._terminal_commands: list[tuple[int, str]] = []  # (global_seq, command)
        self._global_seq: int = 0

    def _next_seq(self) -> int:
        """Return the next global sequence number."""
        seq = self._global_seq
        self._global_seq += 1
        return seq

    def send(self, msg: VoiceMessage) -> None:
        """Enqueue a voice message to the recipient's inbox."""
        # Apply transcript mode rules
        delivered = msg.model_copy()
        if self.transcript_mode == TranscriptMode.TEXT_ONLY:
            # Text-only mode: transcript is the primary content, audio is just encoded text
            if delivered.transcript is None and delivered.audio:
                delivered.transcript = delivered.audio.decode("utf-8", errors="replace")
        elif self.transcript_mode == TranscriptMode.AUDIO_ONLY:
            delivered.transcript = None
        elif self.transcript_mode == TranscriptMode.AUDIO_PLUS_NOISY_TRANSCRIPT:
            if delivered.transcript is not None:
                delivered.transcript = degrade_transcript(delivered.transcript)

        with self._lock:
            seq = self._next_seq()
            self._queues[msg.recipient].append(delivered)
            # Store the delivered (possibly degraded) copy, not the original.
            # This ensures the evaluator scores what the agent actually received.
            self._all_messages.append((seq, delivered))

    def receive(self, recipient: str) -> list[VoiceMessage]:
        """Drain and return all pending messages for a recipient."""
        with self._lock:
            messages = list(self._queues[recipient])
            self._queues[recipient].clear()
        return messages

    def peek(self, recipient: str) -> int:
        """Return count of pending messages without consuming them."""
        with self._lock:
            return len(self._queues[recipient])

    def record_terminal_command(self, command: str) -> None:
        """Record a terminal command executed by the primary agent."""
        with self._lock:
            seq = self._next_seq()
            self._terminal_commands.append((seq, command))

    @property
    def all_messages(self) -> list[VoiceMessage]:
        """Return messages only (without sequence numbers)."""
        with self._lock:
            return [msg for _, msg in self._all_messages]

    @property
    def terminal_commands(self) -> list[str]:
        """Return command strings only (without sequence numbers)."""
        with self._lock:
            return [cmd for _, cmd in self._terminal_commands]

    def get_ordered_events(self) -> list[tuple[int, str, str, str]]:
        """Return all events in global order: (seq, kind, data, sender).

        kind is 'voice' or 'command'. sender is 'primary'/'collaborator'/'' for commands.
        """
        with self._lock:
            events = []
            for seq, msg in self._all_messages:
                events.append((seq, "voice", msg.transcript or "", msg.sender))
            for seq, cmd in self._terminal_commands:
                events.append((seq, "command", cmd, ""))
            events.sort(key=lambda x: x[0])
            return events


# ---------------------------------------------------------------------------
# TTS / STT wrappers
# ---------------------------------------------------------------------------

def text_to_audio(text: str) -> bytes:
    """Convert text to audio bytes.

    Tries gTTS first, falls back to encoding text as UTF-8 bytes
    (useful for testing without TTS dependencies).
    """
    try:
        from gtts import gTTS
        tts = gTTS(text=text, lang="en")
        buf = io.BytesIO()
        tts.write_to_fp(buf)
        return buf.getvalue()
    except ImportError:
        # Fallback: encode text as bytes for testing
        return text.encode("utf-8")


def audio_to_text(audio: bytes) -> str:
    """Convert audio bytes to text.

    Tries whisper first, falls back to decoding as UTF-8
    (useful for testing without STT dependencies).
    """
    try:
        import whisper
        import tempfile
        import os

        model = whisper.load_model("base")
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(audio)
            f.flush()
            result = model.transcribe(f.name)
        os.unlink(f.name)
        return result["text"].strip()
    except ImportError:
        # Fallback: decode as UTF-8
        try:
            return audio.decode("utf-8")
        except UnicodeDecodeError:
            return "<audio:undecoded>"


def degrade_transcript(text: str, error_rate: float = 0.1) -> str:
    """Introduce realistic STT-like errors into a transcript.

    Randomly substitutes, drops, or inserts characters at the given rate.
    """
    if not text:
        return text

    chars = list(text)
    result = []
    for ch in chars:
        r = random.random()
        if r < error_rate / 3:
            # Substitution
            if ch.isalpha():
                result.append(random.choice(string.ascii_lowercase))
            else:
                result.append(ch)
        elif r < 2 * error_rate / 3:
            # Deletion — skip this character
            continue
        elif r < error_rate:
            # Insertion — add a random char before this one
            result.append(random.choice(string.ascii_lowercase))
            result.append(ch)
        else:
            result.append(ch)

    return "".join(result)
