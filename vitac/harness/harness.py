"""Main benchmark orchestrator, following terminal-bench patterns."""

from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)

from vitac.agents.base_agent import CollaboratorAgent, PrimaryAgent
from vitac.dataset.dataset import Dataset
from vitac.evaluator import evaluate_voice_interaction
from vitac.harness.models import BenchmarkResults, TrialResults
from vitac.parsers.pytest_parser import PytestParser
from vitac.terminal.docker_compose_manager import DockerComposeManager
from vitac.terminal.terminal import Terminal
from vitac.types import (
    FailureMode,
    TaskDef,
    UnitTestStatus,
    VoiceMessage,
)
from vitac.voice import VoiceQueue, text_to_audio

logger = logging.getLogger(__name__)


class Harness:
    """Orchestrates benchmark execution across tasks."""

    def __init__(
        self,
        output_path: Path,
        run_id: str,
        primary: PrimaryAgent,
        collaborator: CollaboratorAgent,
        dataset: Dataset,
        no_rebuild: bool = False,
        cleanup: bool = False,
        n_concurrent_trials: int = 4,
        n_attempts: int = 1,
        global_timeout_multiplier: float = 1.0,
        transcript_mode_override: str | None = None,
    ):
        self._output_path = output_path
        self._run_id = run_id
        self._primary = primary
        self._collaborator = collaborator
        self._dataset = dataset
        self._no_rebuild = no_rebuild
        self._cleanup = cleanup
        self._n_concurrent_trials = n_concurrent_trials
        self._n_attempts = n_attempts
        self._global_timeout_multiplier = global_timeout_multiplier
        self._transcript_mode_override = transcript_mode_override

        self._run_path.mkdir(parents=True, exist_ok=True)

    @property
    def _run_path(self) -> Path:
        return self._output_path / self._run_id

    @property
    def _results_path(self) -> Path:
        return self._run_path / "results.json"

    def run(self) -> BenchmarkResults:
        """Execute all tasks and return results."""
        results = BenchmarkResults()

        tasks_to_run = []
        for task in self._dataset:
            task_path = self._dataset.get_task_path(task.task_id)
            for attempt in range(1, self._n_attempts + 1):
                trial_name = (
                    f"{task.task_id}.{attempt}-of-{self._n_attempts}.{self._run_id}"
                )
                # Skip if already completed
                trial_dir = self._run_path / task.task_id / trial_name
                results_file = trial_dir / "results.json"
                if results_file.exists():
                    try:
                        existing = TrialResults.model_validate_json(
                            results_file.read_text()
                        )
                        results.results.append(existing)
                        logger.info(f"Skipping completed trial: {trial_name}")
                        continue
                    except Exception:
                        pass

                tasks_to_run.append((task, task_path, trial_name, attempt))

        if not tasks_to_run:
            logger.info("All trials already completed.")
            self._write_results(results)
            return results

        max_workers = min(len(tasks_to_run), self._n_concurrent_trials)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
        ) as progress:
            progress_task = progress.add_task(
                f"Running {len(tasks_to_run)} trials...",
                total=len(tasks_to_run),
            )

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {}
                for task, task_path, trial_name, attempt in tasks_to_run:
                    future = executor.submit(
                        self._execute_trial,
                        task=task,
                        task_path=task_path,
                        trial_name=trial_name,
                    )
                    futures[future] = trial_name

                for future in as_completed(futures):
                    trial_name = futures[future]
                    try:
                        trial_result = future.result()
                        results.results.append(trial_result)
                        status = "PASS" if trial_result.is_resolved else "FAIL"
                        logger.info(f"{trial_name}: {status}")
                    except Exception as e:
                        logger.error(f"{trial_name}: ERROR - {e}")

                    progress.advance(progress_task)
                    self._write_results(results)

        self._write_results(results)
        return results

    def _execute_trial(
        self,
        task: TaskDef,
        task_path: Path,
        trial_name: str,
    ) -> TrialResults:
        """Execute a single task trial."""
        trial_started = datetime.now(timezone.utc).isoformat()

        # Set up output directories
        trial_dir = self._run_path / task.task_id / trial_name
        trial_dir.mkdir(parents=True, exist_ok=True)
        sessions_dir = trial_dir / "sessions"
        sessions_dir.mkdir(exist_ok=True)
        agent_logs_dir = trial_dir / "agent-logs"
        agent_logs_dir.mkdir(exist_ok=True)

        # Container naming
        container_name = f"vitac-{trial_name}".replace(".", "-").lower()
        image_name = f"vitac-{task.task_id}".replace(".", "-").lower()
        docker_compose_path = task_path / "docker-compose.yaml"

        terminal = Terminal(
            client_container_name=container_name,
            client_image_name=image_name,
            docker_compose_path=docker_compose_path,
            sessions_logs_path=sessions_dir,
            agent_logs_path=agent_logs_dir,
            no_rebuild=self._no_rebuild,
            cleanup=self._cleanup,
        )

        failure_mode = FailureMode.NONE
        parser_results = None
        agent_started = ""
        agent_ended = ""
        test_started = ""
        test_ended = ""
        from vitac.types import TranscriptMode

        if self._transcript_mode_override:
            mode = TranscriptMode(self._transcript_mode_override)
        else:
            mode = task.transcript_mode
        voice_queue = VoiceQueue(mode)

        try:
            # Start container
            terminal.start()

            # Create agent session
            agent_session = terminal.create_session("agent")

            # Pass task metadata to opencode agents.
            # NOTE: perform_task runs in its own thread (see _run_agent_with_collaborator),
            # so we use a shallow copy to avoid concurrent threads stomping on each other's
            # task_id / collaborator_context on the shared self._primary instance.
            import copy

            primary_copy = copy.copy(self._primary)
            if hasattr(primary_copy, "collaborator_context"):
                primary_copy.collaborator_context = task.collaborator_context
            if hasattr(primary_copy, "task_id"):
                primary_copy.task_id = task.task_id

            # Initialize voice queue with instruction
            initial_audio = text_to_audio(task.instruction)
            initial_msg = VoiceMessage(
                sender="collaborator",
                recipient="primary",
                episode_id=trial_name,
                task_id=task.task_id,
                audio=initial_audio,
                transcript=task.instruction,
            )
            voice_queue.send(initial_msg)

            # Run primary agent
            agent_started = datetime.now(timezone.utc).isoformat()
            try:
                agent_timeout = (
                    task.max_agent_timeout_sec * self._global_timeout_multiplier
                )
                # The agent runs synchronously with the voice queue
                agent_result = self._run_agent_with_collaborator(
                    task=task,
                    primary=primary_copy,
                    agent_session=agent_session,
                    voice_queue=voice_queue,
                    logging_dir=agent_logs_dir,
                    timeout_sec=agent_timeout,
                )
            except TimeoutError:
                failure_mode = FailureMode.AGENT_TIMEOUT
                agent_result = None
            except Exception as e:
                logger.error(f"Agent error on {task.task_id}: {e}")
                failure_mode = FailureMode.UNKNOWN_AGENT_ERROR
                agent_result = None

            agent_ended = datetime.now(timezone.utc).isoformat()

            # Run tests
            if failure_mode == FailureMode.NONE:
                test_started = datetime.now(timezone.utc).isoformat()
                failure_mode = self._run_tests(terminal, task, task_path)

                if failure_mode == FailureMode.NONE:
                    # Create test session as root (agent can't tamper)
                    test_session = terminal.create_session(
                        "tests", as_configured_user=False
                    )

                    # Kill any background processes the agent may have left,
                    # protect test files from tampering, and make tests
                    # read-only before running them.
                    try:
                        test_session.send_keys(
                            [
                                "pkill -f 'inotifywait\\|fswatch\\|entr' 2>/dev/null; "
                                f"chmod -R 555 {DockerComposeManager.CONTAINER_TEST_DIR} 2>/dev/null; "
                                "true",
                                "Enter",
                            ],
                            block=True,
                            max_timeout_sec=10,
                        )
                    except TimeoutError:
                        pass  # Best-effort protection
                    test_timeout = (
                        task.max_test_timeout_sec * self._global_timeout_multiplier
                    )
                    try:
                        test_session.send_keys(
                            [
                                f"bash {DockerComposeManager.CONTAINER_TEST_DIR}/run-tests.sh",
                                "Enter",
                            ],
                            block=True,
                            max_timeout_sec=test_timeout,
                        )
                    except TimeoutError:
                        failure_mode = FailureMode.TEST_TIMEOUT

                    if failure_mode == FailureMode.NONE:
                        post_test = test_session.capture_pane(capture_entire=True)
                        parser = PytestParser()
                        try:
                            parser_results = parser.parse(post_test)
                        except Exception as e:
                            logger.error(f"Parse error on {task.task_id}: {e}")
                            failure_mode = FailureMode.PARSE_ERROR

                test_ended = datetime.now(timezone.utc).isoformat()

        finally:
            terminal.stop()

        # Determine if resolved
        is_resolved = (
            parser_results is not None
            and all(s == UnitTestStatus.PASSED for s in parser_results.values())
            if parser_results
            else False
        )

        # Score voice interaction
        voice_score = evaluate_voice_interaction(
            task=task, voice_queue=voice_queue, agent_logs_dir=agent_logs_dir
        )

        trial_result = TrialResults(
            trial_name=trial_name,
            task_id=task.task_id,
            instruction=task.instruction,
            is_resolved=is_resolved,
            failure_mode=failure_mode,
            parser_results=parser_results,
            voice_score=voice_score,
            total_input_tokens=(agent_result.total_input_tokens if agent_result else 0),
            total_output_tokens=(
                agent_result.total_output_tokens if agent_result else 0
            ),
            trial_started_at=trial_started,
            trial_ended_at=datetime.now(timezone.utc).isoformat(),
            agent_started_at=agent_started,
            agent_ended_at=agent_ended,
            test_started_at=test_started,
            test_ended_at=test_ended,
        )

        # Write individual trial result
        trial_result_path = trial_dir / "results.json"
        trial_result_path.write_text(trial_result.model_dump_json(indent=2))

        return trial_result

    def _run_agent_with_collaborator(
        self,
        task: TaskDef,
        primary: PrimaryAgent,
        agent_session,
        voice_queue: VoiceQueue,
        logging_dir: Path,
        timeout_sec: float,
    ):
        """Run primary agent, routing voice messages through the collaborator."""
        import threading
        import time

        result_holder = [None]
        error_holder = [None]

        def agent_thread():
            try:
                result_holder[0] = primary.perform_task(
                    instruction=task.instruction,
                    session=agent_session,
                    voice_queue=voice_queue,
                    logging_dir=logging_dir,
                )
            except Exception as e:
                error_holder[0] = e

        # Start a background thread that polls for collaborator messages
        stop_collaborator = threading.Event()

        def collaborator_thread():
            while not stop_collaborator.is_set():
                inbox = voice_queue.receive("collaborator")
                if inbox:
                    logger.debug(f"Collaborator received {len(inbox)} message(s)")
                    try:
                        response = self._collaborator.respond(
                            inbox=inbox,
                            context=task.collaborator_context,
                        )
                        if response:
                            response.episode_id = agent_session._session_name
                            response.task_id = task.task_id
                            voice_queue.send(response)
                            logger.debug("Collaborator sent response")
                        else:
                            logger.debug("Collaborator returned None")
                    except Exception as e:
                        logger.error(f"Collaborator error: {e}", exc_info=True)
                time.sleep(0.1)

        agent_t = threading.Thread(target=agent_thread, daemon=True)
        collab_t = threading.Thread(target=collaborator_thread, daemon=True)

        agent_t.start()
        collab_t.start()

        agent_t.join(timeout=timeout_sec)

        stop_collaborator.set()
        collab_t.join(timeout=5)

        if agent_t.is_alive():
            raise TimeoutError(f"Agent timed out after {timeout_sec} seconds")

        if error_holder[0]:
            raise error_holder[0]

        return result_holder[0]

    def _run_tests(
        self,
        terminal: Terminal,
        task: TaskDef,
        task_path: Path,
    ) -> FailureMode:
        """Copy test files into the container."""
        run_tests_path = task_path / "run-tests.sh"
        tests_dir = task_path / "tests"

        paths_to_copy = [run_tests_path]
        if tests_dir.exists():
            paths_to_copy.append(tests_dir)

        terminal.copy_to_container(
            paths=paths_to_copy,
            container_dir=str(DockerComposeManager.CONTAINER_TEST_DIR),
        )
        return FailureMode.NONE

    def _write_results(self, results: BenchmarkResults) -> None:
        """Write results to disk."""
        self._results_path.write_text(results.model_dump_json(indent=2))
