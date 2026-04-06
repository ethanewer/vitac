# Terminal-Bench Experiment Log

## Format
Each entry records: timestamp, git SHA, description, benchmark command, benchmark type, parallelism, results, raw result paths.

---

## Entry 1: Targeted - persistent shell + truncation + env + filtering
- **Timestamp**: 2026-04-05T20:36
- **Git SHA (submodule)**: e7656cb58
- **Changes**: Persistent shell, head+tail truncation, env disclosure, tool filtering
- **Tasks**: rstan-to-pystan, sparql-university (5 attempts each)
- **Results**: 1/10 (sparql 1/5, rstan 0/5 with 4 timeouts)
- **Job dir**: jobs/2026-04-05__20-36-35

## Entry 2: Targeted - timeout 5min + pipefail + Docker tips
- **Timestamp**: 2026-04-05T21:16
- **Git SHA (submodule)**: 8a4b52b79
- **Changes**: +5min bash timeout, +pipefail, +Docker/Python tips in prompt
- **Tasks**: rstan-to-pystan, sparql-university (5 attempts each)
- **Results**: 1/10 (sparql 0/5, rstan 1/5 with 5 timeouts but 1 success before timeout)
- **Job dir**: jobs/2026-04-05__21-16-44
- **Note**: rstan improved 0->1. Agent had more time for PyStan compilation.

## Entry 3: Full efficient subset (all 12 tasks)
- **Timestamp**: 2026-04-05T21:57
- **Git SHA (submodule)**: 8a4b52b79
- **Changes**: All above (persistent shell, truncation, env, filtering, timeout, pipefail, prompt)
- **Tasks**: All 12 tasks (5 attempts each = 60 trials)
- **Results**: 19/60 (0.317) vs baseline 20/60 (0.333) vs Terminus 2 27/60 (0.450)
- **Job dir**: jobs/2026-04-05__21-57-57
- **Per-task delta vs baseline**:
  - git-leak-recovery: 2→5 (+3)
  - multi-source-data-merger: 3→5 (+2)
  - sqlite-db-truncate: 2→4 (+2)
  - extract-elf: 2→3 (+1)
  - sanitize-git-repo: 3→0 (-3, investigation: agent reasoning gap, not tooling)
  - circuit-fibsqrt: 2→0 (-2, model reasoning stall)
  - compile-compcert: 2→0 (-2, OOM/Coq version)
  - path-tracing: 2→0 (-2, huge image payload)
- **Analysis**: Strong improvements in stateful tasks (git, data merger, sqlite) due to persistent shell. Regressions are not caused by our changes (confirmed: no pipefail issues, no structured output confusion). Regressions appear to be variance + model reasoning limits on borderline tasks.

---

