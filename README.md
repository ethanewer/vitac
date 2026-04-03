# Voice Interaction Bench

A suite of benchmarks for evaluating voice-based AI agent interactions, built to test the [OpenCode Audio](https://github.com/ethanewer/opencode-audio) agent.

## Benchmarks

| Benchmark | Description |
|-----------|-------------|
| [VITAC](benchmarks/vitac/) | Voice-Interactive Terminal Agent Collaboration — two AI agents collaborate over synthesized voice to solve SWE tasks inside Docker containers |

## Shared infrastructure

- `opencode-audio/` — OpenCode Audio SDK (git submodule)
- `scripts/` — Shared build scripts (e.g. `update-opencode.sh`)
- `results/` — Benchmark output (gitignored)

## Getting started

```sh
# Clone with submodules
git clone --recurse-submodules <repo-url>

# Build the OpenCode binary (requires Bun)
scripts/update-opencode.sh

# Run a benchmark
cd benchmarks/vitac
uv run vitac list-systems
uv run vitac run --system claude-opus-medium-voice --task-id debug-calculator --concurrency 1
```

See each benchmark's README for detailed setup and usage instructions.
