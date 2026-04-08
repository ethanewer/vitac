"""Harbor agent that runs OpenCode Audio (text-only mode) inside task containers."""

from __future__ import annotations

import asyncio
import importlib
import inspect
import os
import shlex
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Import Harbor's BaseAgent (graceful fallback for local testing)
# ---------------------------------------------------------------------------
_base_agent_cls: type[object] = object
try:
    _harbor_base_module = importlib.import_module("harbor.agents.base")
    candidate = getattr(_harbor_base_module, "BaseAgent", object)
    if isinstance(candidate, type):
        _base_agent_cls = candidate
except Exception:
    _base_agent_cls = object

HarborBaseAgent = _base_agent_cls

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_SCRIPT_DIR = Path(__file__).resolve().parent
_BIN_DIR = _SCRIPT_DIR / "bin"
_REMOTE_BIN_DIR = "/tmp/opencode-bin"
_REMOTE_OPENCODE = "/usr/local/bin/opencode"

# Architecture mapping: uname -m output -> binary name
_ARCH_MAP = {
    "aarch64": "opencode-linux-arm64",
    "arm64": "opencode-linux-arm64",
    "x86_64": "opencode-linux-x64",
    "amd64": "opencode-linux-x64",
}

# Environment variables to forward into the container
_FORWARD_ENV_KEYS = (
    "OPENROUTER_API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "OPENCODE_EXPERIMENTAL_PLAN_MODE",
    "OPENCODE_PERMISSION",
    "OPENCODE_CONFIG_CONTENT",
    "OPENCODE_DISABLE_PROJECT_CONFIG",
)


# ---------------------------------------------------------------------------
# Helpers (modelled after the reference small-agent harbor agent)
# ---------------------------------------------------------------------------
async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


async def _env_exec(
    *,
    environment: Any,
    command: str,
    cwd: str | None = None,
    env: dict[str, str] | None = None,
    timeout_sec: int | None = None,
) -> Any:
    """Call environment.exec with progressively simpler kwargs on TypeError."""
    executor = getattr(environment, "exec", None)
    if not callable(executor):
        raise RuntimeError("Harbor environment does not expose an exec method.")

    attempts: list[dict[str, Any]] = [
        {"command": command, "cwd": cwd, "env": env, "timeout_sec": timeout_sec},
        {"command": command, "cwd": cwd, "env": env},
        {"command": command},
    ]
    for kwargs in attempts:
        try:
            return await _maybe_await(executor(**kwargs))
        except TypeError:
            continue
    return await _maybe_await(executor(command))


def _extract(result: Any) -> tuple[int, str, str]:
    """Extract (exit_code, stdout, stderr) from an exec result."""
    if result is None:
        return 0, "", ""
    if isinstance(result, tuple):
        if len(result) >= 3:
            return int(result[0]), str(result[1] or ""), str(result[2] or "")
        if len(result) == 2:
            return int(result[0]), str(result[1] or ""), ""
    if isinstance(result, str):
        return 0, result, ""
    if isinstance(result, dict):
        ec = int(result.get("exit_code", result.get("returncode", 0)))
        return ec, str(result.get("stdout", "")), str(result.get("stderr", ""))
    ec = int(getattr(result, "exit_code", getattr(result, "returncode", 0)))
    return ec, str(getattr(result, "stdout", "")), str(getattr(result, "stderr", ""))


def _raise_on_failure(result: Any, action: str) -> None:
    ec, stdout, stderr = _extract(result)
    if ec != 0:
        detail = stderr.strip() or stdout.strip() or "no output"
        raise RuntimeError(f"{action} failed (exit_code={ec}): {detail}")


def _safe_set(obj: Any, name: str, value: Any) -> None:
    try:
        setattr(obj, name, value)
    except Exception:
        pass


def _set_result(
    context: Any,
    *,
    success: bool,
    exit_code: int,
    stdout: str,
    stderr: str,
) -> None:
    _safe_set(context, "success", success)
    _safe_set(context, "exit_code", exit_code)
    _safe_set(context, "stdout", stdout)
    _safe_set(context, "stderr", stderr)
    metadata = getattr(context, "metadata", None)
    if not isinstance(metadata, dict):
        metadata = {}
        _safe_set(context, "metadata", metadata)
    if isinstance(metadata, dict):
        metadata["opencode_audio_result"] = {
            "success": success,
            "exit_code": exit_code,
            "stdout": stdout,
            "stderr": stderr,
        }


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------
class OpenCodeAudioAgent(HarborBaseAgent):  # type: ignore[misc]
    """Runs ``opencode run --model <model> "<instruction>"`` in the container."""

    def __init__(
        self,
        *,
        model_name: str | None = None,
        **kwargs: object,
    ) -> None:
        try:
            super().__init__(**kwargs)
        except TypeError:
            try:
                super().__init__()
            except Exception:
                pass

        self.model: str = (
            model_name
            or os.environ.get("OPENCODE_MODEL", "")
            or "openrouter/minimax/minimax-m2.7"
        )
        self._remote_binary: str = f"{_REMOTE_BIN_DIR}/opencode-linux-arm64"

    # -- metadata -----------------------------------------------------------

    @staticmethod
    def name() -> str:
        return "opencode-audio"

    def version(self) -> str | None:
        return "0.1.0"

    # -- setup --------------------------------------------------------------

    async def setup(self, environment: Any) -> None:
        """Upload the opencode binary and symlink it on PATH."""
        max_retries = 3
        for attempt in range(max_retries + 1):
            try:
                await self._install_binary(environment)
                return
            except (ProcessLookupError, TimeoutError, OSError):
                if attempt >= max_retries:
                    raise
                await asyncio.sleep(float(2**attempt))

    async def _install_binary(self, environment: Any) -> None:
        # Upload the bin/ directory
        uploader = getattr(environment, "upload_dir", None)
        if not callable(uploader):
            raise RuntimeError(
                "Harbor environment does not expose upload_dir. "
                "Cannot install the opencode binary."
            )

        attempts: list[dict[str, Any]] = [
            {"source_dir": _BIN_DIR, "target_dir": _REMOTE_BIN_DIR},
            {"source_dir": str(_BIN_DIR), "target_dir": _REMOTE_BIN_DIR},
        ]
        for kwargs in attempts:
            try:
                await _maybe_await(uploader(**kwargs))
                break
            except TypeError:
                continue
        else:
            await _maybe_await(uploader(str(_BIN_DIR), _REMOTE_BIN_DIR))

        # Install tmux (needed by the execute_commands tool), detect
        # architecture, chmod, and create a wrapper script on PATH
        setup_cmd = (
            "set -e; "
            "if ! command -v tmux >/dev/null 2>&1; then "
            "  if command -v apt-get >/dev/null 2>&1; then "
            "    apt-get update -qq && apt-get install -y -qq tmux >/dev/null 2>&1; "
            "  elif command -v apk >/dev/null 2>&1; then "
            "    apk add --no-cache tmux >/dev/null 2>&1; "
            "  elif command -v yum >/dev/null 2>&1; then "
            "    yum install -y tmux >/dev/null 2>&1; "
            "  fi; "
            "fi; "
            "ARCH=$(uname -m); "
            'case "$ARCH" in '
            "aarch64|arm64) BIN=opencode-linux-arm64 ;; "
            "x86_64|amd64)  BIN=opencode-linux-x64 ;; "
            '*) echo "Unsupported arch: $ARCH" >&2; exit 1 ;; '
            "esac; "
            f"chmod +x {_REMOTE_BIN_DIR}/$BIN; "
            f"ln -sf {_REMOTE_BIN_DIR}/$BIN {_REMOTE_OPENCODE}; "
            f"ln -sf {_REMOTE_BIN_DIR}/$BIN /usr/bin/opencode; "
            f"ls -la {_REMOTE_BIN_DIR}/$BIN; "
            f"{_REMOTE_BIN_DIR}/$BIN version || echo 'opencode installed (version check skipped)'"
        )
        result = await _env_exec(
            environment=environment,
            command=setup_cmd,
            timeout_sec=120,
        )
        _raise_on_failure(result, "OpenCode binary setup")

        # Detect which binary name was installed and store the full path
        arch_result = await _env_exec(
            environment=environment,
            command="uname -m",
            timeout_sec=5,
        )
        _, arch_stdout, _ = _extract(arch_result)
        arch = arch_stdout.strip()
        bin_name = _ARCH_MAP.get(arch, "opencode-linux-arm64")
        self._remote_binary = f"{_REMOTE_BIN_DIR}/{bin_name}"

    # -- run ----------------------------------------------------------------

    async def run(
        self,
        instruction: str,
        environment: Any,
        context: Any,
    ) -> None:
        instruction = instruction.strip()
        if not instruction:
            _set_result(
                context,
                success=False,
                exit_code=1,
                stdout="",
                stderr="Empty instruction.",
            )
            return

        # Build environment variables to forward
        env: dict[str, str] = {}
        for key in _FORWARD_ENV_KEYS:
            val = os.environ.get(key)
            if val:
                env[key] = val

        # Build the opencode run command using the full binary path
        binary = getattr(
            self, "_remote_binary", f"{_REMOTE_BIN_DIR}/opencode-linux-arm64"
        )
        model_flag = f"--model {shlex.quote(self.model)}" if self.model else ""

        # Support --agent flag via OPENCODE_AGENT env var (e.g. "build", "plan")
        agent_mode = os.environ.get("OPENCODE_AGENT", "")
        agent_flag = f"--agent {shlex.quote(agent_mode)}" if agent_mode else ""

        # Log file paths inside the container
        log_file = "/tmp/opencode-output.log"
        debug_log = "/tmp/opencode-debug.log"

        # Use --format json for structured event logging (plans, tool calls,
        # eval results). Use --print-logs to capture server-side debug info
        # on stderr.  Write JSON events to the log file and pipe a copy to
        # stdout so the exec result still contains a summary.
        command = (
            f"{binary} run --format json --print-logs "
            f"{agent_flag} {model_flag} {shlex.quote(instruction)} "
            f">{log_file} 2>{debug_log}; "
            # Preserve the exit code from opencode run
            f"OC_EXIT=$?; "
            # Append debug log to the output log for single-artifact collection
            f"echo '' >> {log_file}; "
            f"echo '=== STDERR/DEBUG LOG ===' >> {log_file}; "
            f"cat {debug_log} >> {log_file} 2>/dev/null; "
            # Print a brief summary to stdout for the exec result metadata
            f'echo "opencode exited with code $OC_EXIT"; '
            f"exit $OC_EXIT"
        )

        # No timeout here — let Harbor's own agent timeout manage cancellation.
        result = await _env_exec(
            environment=environment,
            command=command,
            env=env,
            timeout_sec=None,
        )

        exit_code, stdout, stderr = _extract(result)

        # Detect process-level OOM: the opencode binary can be killed by the
        # cgroup OOM killer inside the container while the shell survives,
        # resulting in exit_code=0 but "Killed" in the output.
        if exit_code == 0 and "Killed" in (stdout + stderr):
            exit_code = 137

        _set_result(
            context,
            success=exit_code == 0,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
        )
