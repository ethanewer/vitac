# Voice Interaction Bench — Agent Instructions

This repository contains multiple benchmarks for evaluating voice-based AI agent interactions.

## Repository structure

```
opencode-audio/          Git submodule — OpenCode Audio SDK
scripts/                 Shared build scripts
results/                 Benchmark output (gitignored)
benchmarks/
  vitac/                 VITAC benchmark (see below)
  terminal-bench/        Terminal Bench benchmark (see below)
```

## Benchmarks

Each benchmark is self-contained under `benchmarks/<name>/` with its own tasks and documentation.

- **[VITAC](benchmarks/vitac/AGENTS.md)** — Voice-Interactive Terminal Agent Collaboration. See `benchmarks/vitac/AGENTS.md` for full agent instructions.
- **[Terminal Bench](benchmarks/terminal-bench/)** — Runs terminal-bench@2.0 tasks via Harbor CLI, comparing the Terminus 2 agent against the OpenCode Audio agent (text-only mode).
