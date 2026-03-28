"""Core data models for the VITAC benchmark."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TranscriptMode(str, Enum):
    TEXT_ONLY = "text_only"
    AUDIO_ONLY = "audio_only"
    AUDIO_PLUS_TRANSCRIPT = "audio_plus_transcript"
    AUDIO_PLUS_NOISY_TRANSCRIPT = "audio_plus_noisy_transcript"


class TaskDifficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    UNKNOWN = "unknown"


class ParserName(str, Enum):
    PYTEST = "pytest"


class FailureMode(str, Enum):
    UNSET = "unset"
    NONE = "none"
    UNKNOWN = "unknown"
    TEST_TIMEOUT = "test_timeout"
    AGENT_TIMEOUT = "agent_timeout"
    UNKNOWN_AGENT_ERROR = "unknown_agent_error"
    PARSE_ERROR = "parse_error"


class UnitTestStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# Voice messages
# ---------------------------------------------------------------------------

class VoiceMessage(BaseModel):
    sender: str  # "primary" or "collaborator"
    recipient: str  # "primary" or "collaborator"
    episode_id: str
    task_id: str
    audio: bytes
    timestamp: datetime = Field(default_factory=datetime.now)
    transcript: Optional[str] = None


# ---------------------------------------------------------------------------
# Terminal actions
# ---------------------------------------------------------------------------

class TerminalAction(BaseModel):
    command: str
    timestamp: datetime = Field(default_factory=datetime.now)
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0


# ---------------------------------------------------------------------------
# Primary agent actions (union type)
# ---------------------------------------------------------------------------

class SendVoice(BaseModel):
    type: str = "send_voice"
    audio: bytes
    transcript: str


class RunCommand(BaseModel):
    type: str = "run_command"
    command: str


class Done(BaseModel):
    type: str = "done"


from typing import Union
PrimaryAction = Union[SendVoice, RunCommand, Done]


# ---------------------------------------------------------------------------
# Task definition (maps to task.yaml)
# ---------------------------------------------------------------------------

class ExpectedInteraction(BaseModel):
    topic: str
    description: str
    collaborator_answer: str
    must_ask_before_acting: bool = True
    is_correction: bool = False  # True if this is a mid-task correction
    keywords: list[str] = Field(default_factory=list)  # Required keywords for topic matching (all must appear)


class TaskDef(BaseModel):
    """Pydantic model matching the task.yaml schema."""

    # Core fields (from terminal-bench)
    instruction: str
    author_name: str = "unknown"
    author_email: str = ""
    difficulty: TaskDifficulty = TaskDifficulty.UNKNOWN
    category: str = ""
    tags: list[str] = Field(default_factory=list)
    parser_name: ParserName = ParserName.PYTEST
    max_agent_timeout_sec: float = 360.0
    max_test_timeout_sec: float = 60.0

    # Voice-interaction extensions
    collaborator_context: str = ""
    transcript_mode: TranscriptMode = TranscriptMode.AUDIO_PLUS_TRANSCRIPT
    max_voice_turns: int = 10
    expected_interactions: list[ExpectedInteraction] = Field(default_factory=list)
    risky_patterns: list[str] = Field(default_factory=list)

    # Populated by the loader (not in YAML)
    task_id: str = ""
    task_path: Optional[Path] = None


# ---------------------------------------------------------------------------
# Voice interaction score card
# ---------------------------------------------------------------------------

class VoiceScoreCard(BaseModel):
    interaction_quality: float = 0.0  # 0-1
    safety: float = 0.0  # 0-1
    recovery: float = 0.0  # 0-1
    efficiency: float = 0.0  # 0-1
    overall: float = 0.0  # weighted composite
    details: dict = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Agent result
# ---------------------------------------------------------------------------

class AgentResult(BaseModel):
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    failure_mode: FailureMode = FailureMode.NONE
    voice_messages_sent: list[VoiceMessage] = Field(default_factory=list)
    voice_messages_received: list[VoiceMessage] = Field(default_factory=list)
    terminal_actions: list[TerminalAction] = Field(default_factory=list)
