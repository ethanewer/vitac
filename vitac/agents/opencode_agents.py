"""Agents backed by the opencode-audio SDK voice sessions.

Each agent runs inside its own Docker container with an OpenCode server.
A TypeScript runner on the host creates voice sessions and routes audio.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Optional

import docker
import docker.errors

from vitac.agents.base_agent import CollaboratorAgent, PrimaryAgent
from vitac.terminal.docker_compose_manager import DockerComposeManager
from vitac.types import AgentResult, VoiceMessage

logger = logging.getLogger(__name__)

OPENCODE_BINARY = Path(__file__).parent.parent.parent / "ts-runner" / "bin" / "opencode-linux-arm64"
TS_RUNNER = Path(__file__).parent.parent.parent / "ts-runner" / "run-trial.ts"
COLLAB_COMPOSE = Path(__file__).parent.parent.parent / "ts-runner" / "docker-compose.collaborator.yaml"


def _get_container_host_port(container, container_port: int = 4096) -> int:
    """Get the host port mapped to a container port."""
    container.reload()
    ports = container.ports
    key = f"{container_port}/tcp"
    if key in ports and ports[key]:
        return int(ports[key][0]["HostPort"])
    raise RuntimeError(f"No host port mapped for {key} on container {container.name}")


def _inject_opencode(container) -> None:
    """Copy the opencode binary into a running container."""
    if not OPENCODE_BINARY.exists():
        raise FileNotFoundError(f"OpenCode binary not found: {OPENCODE_BINARY}")

    DockerComposeManager.copy_to_container(
        container=container,
        paths=[OPENCODE_BINARY],
        container_dir="/usr/local/bin",
        container_filename="opencode",
    )
    container.exec_run("chmod +x /usr/local/bin/opencode")
    logger.info(f"Injected opencode binary into {container.name}")


def _start_opencode_server(container, port: int = 4096, timeout: int = 60) -> None:
    """Start the OpenCode server inside a container and wait for it to be ready."""
    container.exec_run(
        f"bash -c 'nohup /usr/local/bin/opencode serve --hostname 0.0.0.0 --port {port} > /tmp/opencode.log 2>&1 &'",
        detach=True,
        environment={
            "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY", ""),
            "GOOGLE_API_KEY": os.environ.get("GOOGLE_API_KEY", ""),
            "OPENROUTER_API_KEY": os.environ.get("OPENROUTER_API_KEY", ""),
        },
    )

    for i in range(timeout):
        try:
            result = container.exec_run("cat /tmp/opencode.log")
            output = result.output.decode("utf-8", errors="replace")
            if "opencode server listening" in output:
                logger.info(f"OpenCode server ready in {container.name} after {i+1}s")
                return
        except Exception:
            pass
        time.sleep(1)

    try:
        logs = container.exec_run("cat /tmp/opencode.log")
        logger.error(f"OpenCode server logs from {container.name}: {logs.output.decode()[:500]}")
    except Exception:
        pass

    raise TimeoutError(f"OpenCode server in {container.name} not ready after {timeout}s")


class OpencodePrimaryAgent(PrimaryAgent):
    """Primary agent that runs inside a Docker container via opencode-audio SDK."""

    def __init__(
        self,
        model_config: dict,
        voice: str = "coral",
        native_audio_input: bool = False,
        native_audio_output: bool = False,
        reasoning_effort: str | None = None,
        collab_model_config: dict | None = None,
    ):
        self._model_config = model_config
        self._voice = voice
        self._native_audio_input = native_audio_input
        self._native_audio_output = native_audio_output
        self._reasoning_effort = reasoning_effort
        self._collab_model_config = collab_model_config

        # Set by harness before perform_task
        self.collaborator_context: str = ""
        self._collab_container = None
        self._docker_client = None

    @staticmethod
    def name() -> str:
        return "opencode"

    def _start_collaborator_container(self, trial_name: str) -> tuple:
        """Start a collaborator container and return (container, host_port)."""
        self._docker_client = docker.from_env()

        collab_name = f"vitac-collab-{trial_name}".replace(".", "-").lower()
        collab_image = "vitac-collaborator"

        try:
            self._docker_client.images.get(collab_image)
        except docker.errors.ImageNotFound:
            logger.info("Building collaborator Docker image...")
            subprocess.run(
                ["docker", "compose", "-f", str(COLLAB_COMPOSE.resolve()), "build"],
                env={**os.environ},
                check=True,
                capture_output=True,
            )

        container = self._docker_client.containers.run(
            collab_image,
            command="sleep infinity",
            name=collab_name,
            detach=True,
            environment={
                "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY", ""),
                "GOOGLE_API_KEY": os.environ.get("GOOGLE_API_KEY", ""),
                "OPENROUTER_API_KEY": os.environ.get("OPENROUTER_API_KEY", ""),
            },
            ports={"4096/tcp": None},
        )

        self._collab_container = container

        _inject_opencode(container)
        _start_opencode_server(container)
        host_port = _get_container_host_port(container)

        logger.info(f"Collaborator container {collab_name} on port {host_port}")
        return container, host_port

    def _stop_collaborator_container(self) -> None:
        """Stop and remove the collaborator container."""
        if self._collab_container:
            try:
                self._collab_container.stop(timeout=5)
                self._collab_container.remove(force=True)
            except Exception as e:
                logger.warning(f"Error stopping collaborator container: {e}")
            self._collab_container = None

    def perform_task(
        self,
        instruction: str,
        session,  # TmuxSession
        voice_queue,  # VoiceQueue
        logging_dir: Path | None = None,
    ) -> AgentResult:
        container = session.container
        container_name = container.name

        _inject_opencode(container)
        _start_opencode_server(container)
        primary_port = _get_container_host_port(container)
        logger.info(f"Primary container {container_name} on port {primary_port}")

        collab_container, collab_port = self._start_collaborator_container(container_name)

        try:
            config = {
                "primaryUrl": f"http://127.0.0.1:{primary_port}",
                "collabUrl": f"http://127.0.0.1:{collab_port}",
                "instruction": instruction,
                "collaboratorContext": self.collaborator_context,
                "model": self._model_config,
                "nativeAudioInput": self._native_audio_input,
                "nativeAudioOutput": self._native_audio_output,
                "voice": self._voice,
                "ttsOptions": {
                    "apiKey": os.environ.get("OPENAI_API_KEY", ""),
                },
                "sttOptions": {
                    "apiKey": os.environ.get("OPENAI_API_KEY", ""),
                },
            }
            if self._collab_model_config:
                config["collabModel"] = self._collab_model_config
            if self._reasoning_effort:
                config["reasoningEffort"] = self._reasoning_effort

            config_file = tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False, prefix="vitac-config-"
            )
            json.dump(config, config_file)
            config_file.close()

            output_file = tempfile.NamedTemporaryFile(
                suffix=".json", delete=False, prefix="vitac-result-"
            )
            output_file.close()

            try:
                ts_timeout = 240
                config["maxTimeoutMs"] = (ts_timeout - 30) * 1000
                with open(config_file.name, "w") as f:
                    json.dump(config, f)

                cmd = ["bun", "run", str(TS_RUNNER.resolve()), config_file.name, output_file.name]
                logger.info(f"Starting TypeScript runner for {container_name}")
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=ts_timeout,
                    cwd=str(TS_RUNNER.parent.resolve()),
                )

                if result.stdout:
                    logger.info(f"TS Runner stdout:\n{result.stdout[-2000:]}")
                if result.stderr:
                    logger.warning(f"TS Runner stderr:\n{result.stderr[-1000:]}")

                try:
                    with open(output_file.name) as f:
                        ts_result = json.load(f)
                except (FileNotFoundError, json.JSONDecodeError) as e:
                    logger.error(f"Failed to read TS runner result: {e}")
                    ts_result = {"completed": False, "error": str(e),
                                 "totalInputTokens": 0, "totalOutputTokens": 0,
                                 "voiceMessages": [], "terminalCommands": []}

                for msg_data in ts_result.get("voiceMessages", []):
                    sender = msg_data.get("sender", "primary")
                    recipient = "collaborator" if sender == "primary" else "primary"
                    voice_msg = VoiceMessage(
                        sender=sender,
                        recipient=recipient,
                        episode_id=container_name,
                        task_id=container_name,
                        audio=msg_data.get("transcript", "").encode("utf-8"),
                        transcript=msg_data.get("transcript", ""),
                    )
                    voice_queue.send(voice_msg)

                for cmd in ts_result.get("terminalCommands", []):
                    voice_queue.record_terminal_command(cmd)

                return AgentResult(
                    total_input_tokens=ts_result.get("totalInputTokens", 0),
                    total_output_tokens=ts_result.get("totalOutputTokens", 0),
                )

            finally:
                os.unlink(config_file.name)
                try:
                    os.unlink(output_file.name)
                except FileNotFoundError:
                    pass

        finally:
            self._stop_collaborator_container()


class OpencodeCollaboratorAgent(CollaboratorAgent):
    """No-op collaborator - the real collaborator runs inside the TS runner."""

    @staticmethod
    def name() -> str:
        return "opencode-noop"

    def respond(
        self,
        inbox: list[VoiceMessage],
        context: str,
    ) -> Optional[VoiceMessage]:
        return None


# ---------------------------------------------------------------------------
# Model-specific subclasses (no-arg constructors for agent_factory)
# ---------------------------------------------------------------------------

class GeminiFlashPrimary(OpencodePrimaryAgent):
    def __init__(self):
        super().__init__(
            model_config={"providerID": "openrouter", "modelID": "google/gemini-3.1-flash-lite-preview"},
            voice="coral",
        )

    @staticmethod
    def name() -> str:
        return "gemini-3.1-flash-lite-preview"


class GeminiFlashCollaborator(OpencodeCollaboratorAgent):
    @staticmethod
    def name() -> str:
        return "gemini-3.1-flash-collab"


class Gpt54MiniPrimary(OpencodePrimaryAgent):
    def __init__(self):
        super().__init__(
            model_config={"providerID": "openai", "modelID": "gpt-5.4-mini"},
            voice="coral",
            reasoning_effort="medium",
        )

    @staticmethod
    def name() -> str:
        return "gpt-5.4-mini"


class Gpt54MiniCollaborator(OpencodeCollaboratorAgent):
    @staticmethod
    def name() -> str:
        return "gpt-5.4-mini-collab"
