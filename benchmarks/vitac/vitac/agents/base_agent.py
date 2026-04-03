"""Abstract base classes for Primary and Collaborator agents."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from vitac.types import AgentResult, VoiceMessage

if TYPE_CHECKING:
    from vitac.terminal.tmux_session import TmuxSession
    from vitac.voice import VoiceQueue


class PrimaryAgent(ABC):
    """Agent under test. Has terminal access and communicates via voice."""

    @staticmethod
    @abstractmethod
    def name() -> str:
        """Return a short identifier for this agent."""
        ...

    @abstractmethod
    def perform_task(
        self,
        instruction: str,
        session: TmuxSession,
        voice_queue: VoiceQueue,
        logging_dir: Path | None = None,
    ) -> AgentResult:
        """Execute the task using terminal + voice interaction.

        The agent should:
        1. Read the instruction.
        2. Use voice_queue to ask clarification questions.
        3. Use session to run terminal commands.
        4. Return an AgentResult when done.
        """
        ...


class CollaboratorAgent(ABC):
    """Holds external context, answers questions via voice. No terminal access."""

    @staticmethod
    @abstractmethod
    def name() -> str:
        """Return a short identifier for this collaborator."""
        ...

    @abstractmethod
    def respond(
        self,
        inbox: list[VoiceMessage],
        context: str,
    ) -> Optional[VoiceMessage]:
        """Given incoming voice messages and task context, optionally respond.

        Returns a VoiceMessage to send back, or None if no response needed.
        """
        ...
