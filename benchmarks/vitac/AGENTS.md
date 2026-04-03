# VITAC — Voice-Interactive Terminal Agent Collaboration Benchmark

Benchmarks voice-based multi-agent collaboration on software engineering tasks. Two AI agents (primary + collaborator) communicate over synthesized voice to solve tasks inside Docker containers, scored by pytest pass/fail.

## Prerequisites

- Python >= 3.12, [uv](https://docs.astral.sh/uv/)
- Docker (running)
- [Bun](https://bun.sh/) (runs the TypeScript voice trial runner)
- OpenCode binary at `ts-runner/bin/opencode-linux-arm64` (run `../../scripts/update-opencode.sh` from this directory, or `scripts/update-opencode.sh` from the repo root)

### Environment variables (must be set before running)

```
OPENAI_API_KEY       # Required: STT/TTS (all systems) + OpenAI model systems
ANTHROPIC_API_KEY    # Required for Claude systems
OPENROUTER_API_KEY   # Required for Gemini and MiniMax systems (routed via OpenRouter)
```

Optional: `GOOGLE_API_KEY`, `OPENCODE_API_KEY`.

## Quick start

All commands below should be run from the `benchmarks/vitac/` directory.

```sh
# Install Python package
uv run vitac list-systems          # verify install + list available voice systems

# Generate seed audio (one-time, requires OPENAI_API_KEY)
uv run python -m vitac.generate_audio

# Run a single task
uv run vitac run --system claude-opus-medium-voice --task-id debug-calculator --concurrency 1

# Run all easy tasks
uv run vitac run --system minimax-m2-voice --difficulty easy

# Run full benchmark
uv run vitac run --system gpt-high-voice
```

## CLI commands

All commands are run via `uv run vitac <command>` (alias: `uv run vb <command>`).

| Command | Purpose |
|---------|---------|
| `run --system <name>` | Run benchmark. Key flags: `--task-id`, `--difficulty`, `--concurrency`, `--n-attempts`, `--collab-system`, `--text-only`, `--no-rebuild`, `--cleanup` |
| `list-systems` | Print available voice system names |
| `list-tasks` | List all tasks with difficulty and category |
| `validate-tasks` | Check task directories for required files |
| `show-results <path>` | Display results from a previous run |

## Available voice systems

```
claude-opus-medium-voice    anthropic/claude-opus-4-6 (medium reasoning)
claude-opus-high-voice      anthropic/claude-opus-4-6 (high reasoning)
claude-opus-max-voice       anthropic/claude-opus-4-6 (max reasoning)
gpt-medium-voice            openai/gpt-5.4 (medium)
gpt-high-voice              openai/gpt-5.4 (high)
gpt-xhigh-voice             openai/gpt-5.4 (xhigh)
gpt-audio-voice             openai/gpt-audio (native audio I/O)
gemini-flash-voice          openrouter/google/gemini-3.1-flash-lite-preview
gemini-pro-voice            openrouter/google/gemini-3.1-pro-preview-customtools
minimax-m2-voice            openrouter/minimax/minimax-m2.7
```

System definitions live in the SDK: `../../opencode-audio/packages/sdk/js/src/v2/voice.ts` (the `voiceSystems` map, relative to this directory). The Python list that must stay in sync is `BUILT_IN_SYSTEMS` in `vitac/agents/opencode_agents.py`.

## Project structure

All paths below are relative to `benchmarks/vitac/`.

```
vitac/                          Core Python package
  cli.py                        Typer CLI entry point (run, list-systems, list-tasks, etc.)
  types.py                      Pydantic models, enums (TaskDef, VoiceMessage, etc.)
  voice.py                      VoiceQueue, TTS (gTTS), STT (whisper), transcript degradation
  evaluator.py                  Score card (scoring is purely pytest pass/fail)
  generate_audio.py             Generates seed WAV files via OpenAI TTS
  agents/
    opencode_agents.py          Main agent classes + BUILT_IN_SYSTEMS + API key forwarding
    base_agent.py               Abstract PrimaryAgent / CollaboratorAgent
  harness/
    harness.py                  Benchmark orchestrator (Docker lifecycle, threading, test execution)
    models.py                   TrialResults / BenchmarkResults
  dataset/
    dataset.py                  Task discovery and loading from tasks/ directory
  terminal/
    terminal.py                 Docker container + tmux session management
    tmux_session.py             Send keys, capture pane, run commands in Docker
    docker_compose_manager.py   Docker Compose build/start/stop, file copy
  parsers/
    pytest_parser.py            Parses pytest output into per-test PASSED/FAILED

ts-runner/                      TypeScript (Bun) voice trial runner
  run-trial.ts                  Creates voice sessions, seeds audio, routes PCM, detects TASK_COMPLETE
  types.ts                      TrialConfig, TrialResult interfaces
  docker-compose.collaborator.yaml
  Dockerfile.collaborator
  bin/opencode-linux-arm64      OpenCode server binary (gitignored, must be built)

tasks/                          20 active benchmark tasks
  <task-id>/
    task.yaml                   Task definition (instruction, difficulty, collaborator_context, etc.)
    Dockerfile                  Task container image
    docker-compose.yaml         Container config (env vars, ports, volumes)
    tests/                      Pytest tests that determine pass/fail
    run-tests.sh                Test runner script
    solution.sh                 Reference solution

audio/                          Seed audio files
  instructions.json             Maps task_id -> {start_agent, text}
  <task-id>.wav                 Pre-generated TTS audio (gitignored, generate with generate_audio.py)

viewer/                         Web UI for viewing results
  server.py                     FastAPI backend
  static/                       SPA frontend (HTML, JS, CSS)

../../opencode-audio/           OpenCode Audio SDK (git submodule at repo root)
../../scripts/                  Shared build scripts (at repo root)
../../results/                  Benchmark output (at repo root, gitignored)
```

## Execution flow

1. CLI creates agent instances and loads the dataset
2. `Harness.run()` launches concurrent trials via `ThreadPoolExecutor`
3. Per task: Docker Compose builds/starts the task container, creates a tmux session
4. `VoiceSystemPrimaryAgent.perform_task()`:
   - Injects the `opencode` binary into both the task container and a new collaborator container
   - Starts OpenCode servers in both containers (API keys forwarded via `_opencode_env()`)
   - Writes a trial config JSON and runs `bun run ts-runner/run-trial.ts`
5. The TS runner creates voice sessions via the SDK, seeds audio to the starting agent, routes PCM audio bidirectionally, and monitors for `TASK_COMPLETE`
6. Back in Python: test files are copied into the container, pytest runs via tmux, output is parsed
7. Results are aggregated: resolved = all pytest tests pass

## API key propagation

Keys flow through three paths — all must stay in sync:

1. **`_opencode_env()`** in `vitac/agents/opencode_agents.py:86` — forwarded to `container.exec_run()` when starting OpenCode servers
2. **Task docker-compose files** (`tasks/*/docker-compose.yaml`) — `${VAR:-}` shell substitution from host env
3. **Collaborator docker-compose** (`ts-runner/docker-compose.collaborator.yaml`) — same pattern

To add a new key: add it to all three locations.

## Task anatomy

Each `task.yaml` contains: `instruction`, `difficulty` (easy/medium/hard), `category`, `collaborator_context` (domain knowledge for the collaborator agent), `parser_name` (pytest), `transcript_mode`, `max_agent_timeout_sec`, `max_test_timeout_sec`. See `vitac/types.py:TaskDef` for the full schema.

## Tests

Task-level tests live inside each `tasks/<task-id>/tests/` and run via pytest inside Docker during benchmark execution. There is no standalone test suite to run outside of the benchmark.

## Adding a new voice system

1. Add the entry to `voiceSystems` in `../../opencode-audio/packages/sdk/js/src/v2/voice.ts`
2. Add the matching name to `BUILT_IN_SYSTEMS` in `vitac/agents/opencode_agents.py`
3. These two lists must match exactly

## Adding a new task

1. Create `tasks/<task-id>/` with: `task.yaml`, `Dockerfile`, `docker-compose.yaml`, `run-tests.sh`, `tests/`, `solution.sh`
2. Add an entry to `audio/instructions.json` with `start_agent` and `text`
3. Run `uv run python -m vitac.generate_audio` to generate the seed WAV
4. Validate with `uv run vitac validate-tasks`
5. Use existing tasks as templates — `tasks/debug-calculator/` is a good reference
