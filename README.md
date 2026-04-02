# VITAC — Voice-Interactive Terminal Agent Collaboration Benchmark

Benchmarks voice-based multi-agent collaboration on software engineering tasks. Two AI agents (primary + collaborator) communicate over synthesized voice to solve tasks inside Docker containers, scored by pytest pass/fail.

## Viewer

Browse benchmark results, listen to voice transcripts, and compare systems with the built-in web UI:

```sh
cd viewer && uv run uvicorn server:app --reload --port 8080
```

Then open [http://localhost:8080](http://localhost:8080).

**Features:**
- **Dashboard** — overall stats, system leaderboard with bar chart, pass/fail heatmap matrix (tasks x systems) grouped by difficulty
- **Runs list** — sortable/filterable table of all benchmark runs with accuracy bars
- **Run detail** — per-trial results with pass/fail status, failure mode, duration, expandable test results
- **Trace playback** — full conversation audio player with timeline visualization, chat-style message display, clickable messages that seek audio, speed controls (0.5x–3x), keyboard shortcuts (Space = play/pause, arrows = skip)

## Prerequisites

- Python >= 3.12
- [uv](https://docs.astral.sh/uv/)
- Docker (running)
- [Bun](https://bun.sh/)

### Environment variables

```
OPENAI_API_KEY       # Required: STT/TTS (all systems) + OpenAI model systems
ANTHROPIC_API_KEY    # Required for Claude systems
OPENROUTER_API_KEY   # Required for Gemini and MiniMax systems (routed via OpenRouter)
```

Optional: `GOOGLE_API_KEY`, `OPENCODE_API_KEY`.

## Setup

```sh
# Build the OpenCode binary (one-time)
scripts/update-opencode.sh

# Generate seed audio WAV files (one-time, requires OPENAI_API_KEY)
uv run python -m vitac.generate_audio

# Verify install
uv run vitac list-systems
```

## Running the benchmark

```sh
# Run a single task
uv run vitac run --system claude-opus-medium-voice --task-id debug-calculator --concurrency 1

# Run all easy tasks
uv run vitac run --system minimax-m2-voice --difficulty easy

# Run full benchmark
uv run vitac run --system gpt-high-voice
```

### CLI commands

All commands are run via `uv run vitac <command>` (alias: `uv run vb <command>`).

| Command | Purpose |
|---------|---------|
| `run --system <name>` | Run benchmark. Key flags: `--task-id`, `--difficulty`, `--concurrency`, `--n-attempts`, `--collab-system`, `--text-only`, `--no-rebuild`, `--cleanup` |
| `list-systems` | Print available voice system names |
| `list-tasks` | List all tasks with difficulty and category |
| `validate-tasks` | Check task directories for required files |
| `show-results <path>` | Display results from a previous run |

### Available voice systems

| System | Model |
|--------|-------|
| `claude-opus-medium-voice` | anthropic/claude-opus-4-6 (medium reasoning) |
| `claude-opus-high-voice` | anthropic/claude-opus-4-6 (high reasoning) |
| `claude-opus-max-voice` | anthropic/claude-opus-4-6 (max reasoning) |
| `gpt-medium-voice` | openai/gpt-5.4 (medium) |
| `gpt-high-voice` | openai/gpt-5.4 (high) |
| `gpt-xhigh-voice` | openai/gpt-5.4 (xhigh) |
| `gpt-audio-voice` | openai/gpt-audio (native audio I/O) |
| `gemini-flash-voice` | openrouter/google/gemini-3.1-flash-lite-preview |
| `gemini-pro-voice` | openrouter/google/gemini-3.1-pro-preview-customtools |
| `minimax-m2-voice` | openrouter/minimax/minimax-m2.7 |

## Project structure

```
vitac/                          Core Python package
  cli.py                        Typer CLI entry point
  types.py                      Pydantic models and enums
  voice.py                      VoiceQueue, TTS, STT, transcript degradation
  evaluator.py                  Scoring (pytest pass/fail)
  generate_audio.py             Generates seed WAV files via OpenAI TTS
  agents/
    base_agent.py               Abstract PrimaryAgent / CollaboratorAgent
    opencode_agents.py          Main agent classes + BUILT_IN_SYSTEMS
  harness/
    harness.py                  Benchmark orchestrator (Docker lifecycle, threading)
    models.py                   TrialResults / BenchmarkResults
  dataset/
    dataset.py                  Task discovery and loading
  terminal/
    terminal.py                 Docker container + tmux session management
    tmux_session.py             Send keys, capture pane in Docker
    docker_compose_manager.py   Docker Compose build/start/stop
  parsers/
    pytest_parser.py            Parses pytest output

ts-runner/                      TypeScript (Bun) voice trial runner
  run-trial.ts                  Voice sessions, audio routing, TASK_COMPLETE detection
  types.ts                      TrialConfig, TrialResult interfaces

tasks/                          20 benchmark tasks
  <task-id>/
    task.yaml                   Task definition (instruction, difficulty, etc.)
    Dockerfile                  Task container image
    docker-compose.yaml         Container config
    tests/                      Pytest tests that determine pass/fail
    run-tests.sh                Test runner script
    solution.sh                 Reference solution

viewer/                         Web UI for viewing results
  server.py                     FastAPI backend
  static/                       SPA frontend (HTML, JS, CSS)

audio/                          Seed audio files
  instructions.json             Maps task_id -> {start_agent, text}
  <task-id>.wav                 Pre-generated TTS audio

scripts/
  update-opencode.sh            Clone/build OpenCode binary

results/                        Benchmark output (gitignored)
```

## Execution flow

1. CLI creates agent instances and loads the dataset
2. `Harness.run()` launches concurrent trials via `ThreadPoolExecutor`
3. Per task: Docker Compose builds/starts the task container and creates a tmux session
4. The OpenCode binary is injected into both the task container and a collaborator container
5. OpenCode servers start in both containers with API keys forwarded
6. The TypeScript trial runner creates voice sessions, seeds audio to the starting agent, and routes PCM audio bidirectionally until `TASK_COMPLETE` is detected
7. Test files are copied into the container, pytest runs, and output is parsed
8. Results are aggregated: resolved = all pytest tests pass

## Adding a new task

1. Create `tasks/<task-id>/` with: `task.yaml`, `Dockerfile`, `docker-compose.yaml`, `run-tests.sh`, `tests/`, `solution.sh`
2. Add an entry to `audio/instructions.json` with `start_agent` and `text`
3. Run `uv run python -m vitac.generate_audio` to generate the seed WAV
4. Validate with `uv run vitac validate-tasks`

Use `tasks/debug-calculator/` as a reference template.

## Adding a new voice system

1. Add the entry to `voiceSystems` in `opencode-audio/packages/sdk/js/src/v2/voice.ts`
2. Add the matching name to `BUILT_IN_SYSTEMS` in `vitac/agents/opencode_agents.py`
3. These two lists must match exactly
