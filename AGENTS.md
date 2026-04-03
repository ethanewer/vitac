# Voice Interaction Bench — Agent Instructions

This repository contains multiple benchmarks for evaluating voice-based AI agent interactions.

## Repository structure

```
opencode-audio/          Git submodule — OpenCode Audio SDK
scripts/                 Shared build scripts
results/                 Benchmark output (gitignored)
benchmarks/
  vitac/                 VITAC benchmark (see below)
```

## Benchmarks

Each benchmark is self-contained under `benchmarks/<name>/` with its own `pyproject.toml`, tasks, and documentation.

- **[VITAC](benchmarks/vitac/AGENTS.md)** — Voice-Interactive Terminal Agent Collaboration. See `benchmarks/vitac/AGENTS.md` for full agent instructions.
