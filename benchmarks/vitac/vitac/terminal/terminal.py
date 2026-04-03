"""Terminal wrapper that manages a Docker container with tmux sessions."""

from __future__ import annotations

import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from vitac.terminal.docker_compose_manager import DockerComposeManager
from vitac.terminal.tmux_session import TmuxSession

logger = logging.getLogger(__name__)


class Terminal:
    """Manages a Docker container and its tmux sessions for a task trial."""

    def __init__(
        self,
        client_container_name: str,
        client_image_name: str,
        docker_compose_path: Path,
        docker_image_name_prefix: str | None = None,
        sessions_logs_path: Path | None = None,
        agent_logs_path: Path | None = None,
        commands_path: Path | None = None,
        no_rebuild: bool = False,
        cleanup: bool = False,
    ):
        self._sessions: dict[str, TmuxSession] = {}
        self.container = None

        self._compose_manager = DockerComposeManager(
            client_container_name=client_container_name,
            client_image_name=client_image_name,
            docker_image_name_prefix=docker_image_name_prefix,
            docker_compose_path=docker_compose_path,
            no_rebuild=no_rebuild,
            cleanup=cleanup,
            sessions_logs_path=sessions_logs_path,
            agent_logs_path=agent_logs_path,
        )

    def create_session(
        self, session_name: str, as_configured_user: bool = True
    ) -> TmuxSession:
        """Create a new tmux session inside the container."""
        if self.container is None:
            raise ValueError("Container not started. Call start() first.")
        if session_name in self._sessions:
            raise ValueError(f"Session {session_name} already exists")

        if as_configured_user:
            user = self.container.attrs["Config"].get("User", "")
        else:
            user = "root"

        session = TmuxSession(
            session_name=session_name,
            container=self.container,
            user=user,
        )
        self._sessions[session_name] = session
        session.start()
        return session

    def get_session(self, session_name: str) -> TmuxSession:
        if session_name not in self._sessions:
            raise ValueError(f"Session {session_name} does not exist")
        return self._sessions[session_name]

    def start(self) -> None:
        """Start the Docker container."""
        self.container = self._compose_manager.start()

    def stop(self) -> None:
        """Stop all sessions and the container."""
        for session in self._sessions.values():
            try:
                session.stop()
            except Exception as e:
                logger.warning(f"Error stopping session: {e}")

        self._compose_manager.stop()
        self._sessions.clear()

    def copy_to_container(
        self,
        paths: list[Path] | Path,
        container_dir: str | None = None,
        container_filename: str | None = None,
    ) -> None:
        self._compose_manager.copy_to_client_container(
            paths=paths,
            container_dir=container_dir,
            container_filename=container_filename,
        )


@contextmanager
def spin_up_terminal(
    client_container_name: str,
    client_image_name: str,
    docker_compose_path: Path,
    docker_image_name_prefix: str | None = None,
    sessions_logs_path: Path | None = None,
    agent_logs_path: Path | None = None,
    commands_path: Path | None = None,
    no_rebuild: bool = False,
    cleanup: bool = False,
) -> Generator[Terminal, None, None]:
    terminal = Terminal(
        client_container_name=client_container_name,
        client_image_name=client_image_name,
        docker_image_name_prefix=docker_image_name_prefix,
        docker_compose_path=docker_compose_path,
        sessions_logs_path=sessions_logs_path,
        agent_logs_path=agent_logs_path,
        commands_path=commands_path,
        no_rebuild=no_rebuild,
        cleanup=cleanup,
    )
    try:
        terminal.start()
        yield terminal
    finally:
        terminal.stop()
