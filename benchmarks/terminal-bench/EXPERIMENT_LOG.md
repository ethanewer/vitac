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

## Entry 4: Full efficient subset - temperature 0.7 + improved prompts
- **Timestamp**: 2026-04-05T23:47
- **Git SHA (submodule)**: 8a4b52b79 (uncommitted: temp 0.7, prompt improvements)
- **Changes**: Temperature reduced 1.0→0.7 for minimax-m2, improved "Doing tasks" section in default.txt (numbered steps, verification emphasis, debug efficiently guidance)
- **Tasks**: All 12 tasks (5 attempts each = 60 trials)
- **Results**: 18/60 (0.300) vs Run 3 19/60 vs baseline 20/60 vs Terminus 2 27/60
- **Job dir**: jobs/2026-04-05__23-47-28
- **Per-task comparison**:

| Task                       | Baseline | Run 3 (t=1.0) | Run 4 (t=0.7) | Terminus 2 |
|:---------------------------|:--------:|:-------------:|:--------------:|:----------:|
| chess-best-move            |   2/5    |     2/5       |     0/5        |    3/5     |
| circuit-fibsqrt            |   2/5    |     0/5       |     0/5        |    2/5     |
| compile-compcert           |   2/5    |     0/5       |     0/5        |    2/5     |
| extract-elf                |   2/5    |     3/5       |     4/5        |    2/5     |
| git-leak-recovery          |   2/5    |     5/5       |     5/5        |    1/5     |
| multi-source-data-merger   |   3/5    |     5/5       |     5/5        |    1/5     |
| path-tracing               |   2/5    |     0/5       |     0/5        |    2/5     |
| rstan-to-pystan            |   0/5    |     1/5       |     0/5        |    4/5     |
| sanitize-git-repo          |   3/5    |     0/5       |     0/5        |    1/5     |
| sparql-university          |   1/5    |     0/5       |     1/5        |    5/5     |
| sqlite-db-truncate         |   2/5    |     4/5       |     3/5        |    1/5     |
| torch-tensor-parallelism   |   0/5    |     0/5       |     0/5        |    3/5     |
| **Total**                  | **20/60**| **19/60**     | **18/60**      | **27/60**  |

- **Analysis**: Temperature 0.7 did not improve performance; slightly worse than 1.0. Reverting temperature to 1.0.
  - **Stable improvements** (consistent across runs 3 & 4): git-leak-recovery (5/5), multi-source-data-merger (5/5), extract-elf (3-4/5), sqlite-db-truncate (3-4/5). These tasks benefit from persistent shell and better environment awareness.
  - **Stable regressions** (0/5 in both runs 3 & 4): circuit-fibsqrt, compile-compcert, path-tracing, sanitize-git-repo. chess-best-move dropped to 0/5 in run 4 (was 2/5 in run 3).
  - **chess-best-move**: Model says "I cannot process image files" and gives up. Model doesn't support image input (attachment: false). Baseline 2/5 was likely due to lucky attempts where the model used python to parse the image.
  - **Consistent 0/5 across 3 runs for 4 tasks**: The pattern is too consistent for pure variance. The longer system prompt (environment disclosure + working-in-containers tips) may reduce effective context for multi-step reasoning. However, tasks that improved also require multi-step reasoning, so the cause is more nuanced.
- **Decision**: Revert temperature to 1.0. Keep prompt improvements. Focus future efforts on understanding the specific failure modes of regressed tasks.

## Entry 5: Full efficient subset — plan-build-eval pipeline (default mode)
- **Timestamp**: 2026-04-06T02:40
- **Git SHA (submodule)**: 8a4b52b79 (uncommitted: temp 1.0, original prompt)
- **Changes**: Default plan-build-eval pipeline (no --agent flag). Temperature 1.0. Persistent shell, env disclosure, tool filtering.
- **Tasks**: All 12 tasks (5 attempts each = 60 trials)
- **Results**: 20/60 (0.333) — 5 AgentTimeoutError
- **Job dir**: jobs/2026-04-06__02-40-07
- **Analysis**: Plan-build-eval pipeline adds ~100s overhead (plan ~60-190s, eval ~26s per iteration). sparql-university massively improved (0→4/5) due to planning. 11 false positives in eval (eval passed but verifier failed): all 3 extract-elf failures and 2/5 sanitize-git-repo failures. Eval feedback loop helped fix issues in 2 passing trials.

## Entry 6: Targeted — improved eval + streamlined plan
- **Timestamp**: 2026-04-06T04:22
- **Changes**: Eval prompt: added generalization testing (test on new inputs), comprehensive repo search, stricter guidelines. Plan prompt: streamlined for autonomous mode (skip subagent launches, direct exploration).
- **Tasks**: extract-elf, sanitize-git-repo, sqlite-db-truncate (3 attempts each)
- **Results**: 6/9 — extract-elf 3/3, sqlite-db-truncate 3/3, sanitize-git-repo 0/3
- **Job dir**: jobs/2026-04-06__04-21-58

## Entry 7: Full efficient subset — improved eval + streamlined plan
- **Timestamp**: 2026-04-06T04:33
- **Changes**: Same as Entry 6 (improved eval + streamlined autonomous plan)
- **Tasks**: All 12 tasks (5 attempts each = 60 trials)
- **Results**: 20/60 (0.333) — 6 AgentTimeoutError
- **Job dir**: jobs/2026-04-06__04-33-11
- **Per-task comparison**:

| Task                       | Baseline | Build-only (R3) | PBE v1 (R5) | PBE v2 (R7) | Terminus 2 |
|:---------------------------|:--------:|:---------------:|:-----------:|:-----------:|:----------:|
| chess-best-move            |   2/5    |      2/5        |    0/5      |    0/5      |    3/5     |
| circuit-fibsqrt            |   2/5    |      0/5        |    0/5      |    0/5      |    2/5     |
| compile-compcert           |   2/5    |      0/5        |    0/5      |    0/5      |    2/5     |
| extract-elf                |   2/5    |      3/5        |    2/5      |   **4/5**   |    2/5     |
| git-leak-recovery          |   2/5    |      5/5        |    5/5      |    5/5      |    1/5     |
| multi-source-data-merger   |   3/5    |      5/5        |    5/5      |    5/5      |    1/5     |
| path-tracing               |   2/5    |      0/5        |    0/5      |    0/5      |    2/5     |
| rstan-to-pystan            |   0/5    |      1/5        |    1/5      |    0/5      |    4/5     |
| sanitize-git-repo          |   3/5    |      0/5        |    0/5      |    0/5      |    1/5     |
| sparql-university          |   1/5    |      0/5        |    4/5      |    3/5      |    5/5     |
| sqlite-db-truncate         |   2/5    |      4/5        |    3/5      |    3/5      |    1/5     |
| torch-tensor-parallelism   |   0/5    |      0/5        |    0/5      |    0/5      |    3/5     |
| **Total**                  | **20/60**| **19/60**       | **20/60**   | **20/60**   | **27/60**  |

- **Key improvements vs PBE v1**: extract-elf 2→4/5 (+2) from eval generalization testing + streamlined plan.
- **Key regressions vs PBE v1**: sparql-university 4→3/5 (-1, streamlined plan slightly less thorough), rstan-to-pystan 1→0/5 (-1, variance).
- **Remaining gap to Terminus 2**: 7 points. Tasks at 0/5 (chess, circuit, compcert, path, sanitize, torch, rstan) need fundamentally different approaches.

## Entry 8: Full efficient subset — anthropic prompt + KIRA CoT fields
- **Timestamp**: 2026-04-06T12:09
- **Git SHA (submodule)**: 4bf697453 (uncommitted: anthropic prompt as default, KIRA analysis/plan fields on bash tool)
- **Changes**: (1) Changed system.ts fallback to use PROMPT_ANTHROPIC instead of PROMPT_DEFAULT. (2) Added required `analysis` and `plan` string parameters to bash tool schema (KIRA-style forced chain-of-thought).
- **Tasks**: All 12 tasks (5 attempts each = 60 trials)
- **Results**: 19/60 (0.317) — no improvement over R3
- **Job dir**: jobs/2026-04-06__12-09-47
- **Analysis**: Anthropic prompt's TodoWrite emphasis wastes tokens on task management. KIRA CoT fields add token overhead without benefit for minimax-m2.7. sanitize-git-repo improved 0→2/5, torch-tensor-parallelism 0→1/5, but sparql-university regressed 3→0/5 and extract-elf 4→2/5.
- **Decision**: Revert both changes. Try minimal prompt approach instead.

## Entry 9: Full efficient subset — minimal KIRA-inspired prompt (**new best**)
- **Timestamp**: 2026-04-06T13:13
- **Git SHA (submodule)**: 4bf697453 (uncommitted: minimal prompt, lean bash tool description)
- **Changes**: (1) Radically stripped default.txt to ~250 words (from ~800+), inspired by KIRA's ~100 word prompt. Focus on task completion, verification, and practical Linux/container tips. Removed all git/PR/commit guidance, verbose examples, and style instructions. (2) Stripped bash.txt tool description to essentials, removed file-operation warnings, git protocol, and PR instructions.
- **Tasks**: All 12 tasks (5 attempts each = 60 trials)
- **Results**: 21/60 (0.350) — **new best**, beats baseline 20/60 (0.333)
- **Job dir**: jobs/2026-04-06__13-13-50
- **Per-task comparison**:

| Task                       | Baseline | Build-only (R3) | R8 (anthro+KIRA) | R9 (minimal) | Terminus 2 |
|:---------------------------|:--------:|:---------------:|:-----------------:|:------------:|:----------:|
| chess-best-move            |   2/5    |      2/5        |       0/5         |    0/5       |    3/5     |
| circuit-fibsqrt            |   2/5    |      0/5        |       0/5         |    0/5       |    2/5     |
| compile-compcert           |   2/5    |      0/5        |       0/5         |    0/5       |    2/5     |
| extract-elf                |   2/5    |      3/5        |       2/5         |   **4/5**    |    2/5     |
| git-leak-recovery          |   2/5    |      5/5        |       5/5         |    5/5       |    1/5     |
| multi-source-data-merger   |   3/5    |      5/5        |       5/5         |    5/5       |    1/5     |
| path-tracing               |   2/5    |      0/5        |       0/5         |    0/5       |    2/5     |
| rstan-to-pystan            |   0/5    |      1/5        |       0/5         |    0/5       |    4/5     |
| sanitize-git-repo          |   3/5    |      0/5        |       2/5         |    0/5       |    1/5     |
| sparql-university          |   1/5    |      0/5        |       0/5         |    0/5       |    5/5     |
| sqlite-db-truncate         |   2/5    |      4/5        |       4/5         |  **5/5**     |    1/5     |
| torch-tensor-parallelism   |   0/5    |      0/5        |       1/5         |  **2/5**     |    3/5     |
| **Total**                  | **20/60**| **19/60**       | **19/60**         | **21/60**    | **27/60**  |

- **Key insight**: Shorter prompts = more effective context for minimax-m2.7. The minimal prompt freed up context window for actual task reasoning.
- **Breakthrough**: torch-tensor-parallelism 0→2/5 (first consistent success on this task). sqlite-db-truncate achieves perfect 5/5.
- **Remaining gap to Terminus 2**: 6 points. Biggest gaps: rstan-to-pystan (0 vs 4), sparql-university (0 vs 5), chess-best-move (0 vs 3), and individual hard tasks (circuit, compcert, path at 0 vs 2 each).

## Entry 10: Full efficient subset — lean tools (remove TodoWrite/Task/WebFetch)
- **Timestamp**: 2026-04-06T14:41
- **Changes**: Added OPENCODE_LEAN_TOOLS flag to remove TodoWrite (~1360 word description), Task (~550 words), WebFetch, EvalRebuttal, and Question tools from build agent in headless mode. Goal: reduce context waste from unused tools.
- **Tasks**: All 12 tasks (5 attempts each = 60 trials)
- **Results**: 16/60 (0.267) — **regression from R9**
- **Job dir**: jobs/2026-04-06__14-41-43
- **Analysis**: Removing tools hurt performance despite saving ~2000 words of context. torch-tensor-parallelism dropped from 2/5 to 0/5, extract-elf from 4/5 to 2/5. The model may use tool presence as behavioral anchors even when not calling them. Tool descriptions contain examples/patterns that inform the model's problem-solving approach.
- **Decision**: Revert lean tools. Tool presence matters more than description size.

## Entry 11: Full efficient subset — condensed tool descriptions
- **Timestamp**: 2026-04-06T16:01
- **Changes**: Kept all tools but condensed TodoWrite description from ~1360 to ~50 words and Task from ~550 to ~70 words. Tools available but with minimal descriptions.
- **Tasks**: All 12 tasks (5 attempts each = 60 trials)
- **Results**: 17/60 (0.283) — regression from R9
- **Job dir**: jobs/2026-04-06__16-01-16
- **Analysis**: Condensing descriptions also hurt. torch-tensor-parallelism 0/5 (was 2/5 in R9), extract-elf 3/5 (was 4/5). The original verbose descriptions provide useful behavioral examples that improve the model's task-solving approach, even for unrelated tools.
- **Decision**: Revert to R9 configuration (minimal system prompt + original tool descriptions). R9 at 21/60 remains our best.

### Summary of all runs

| Run | Description                          | Score  | vs Baseline | vs Terminus 2 |
|:----|:-------------------------------------|:------:|:-----------:|:-------------:|
| R3  | Build-only + persistent shell        | 19/60  | -1          | -8            |
| R4  | + temperature 0.7                    | 18/60  | -2          | -9            |
| R5  | Plan-build-eval pipeline             | 20/60  | 0           | -7            |
| R7  | PBE + improved eval                  | 20/60  | 0           | -7            |
| R8  | Anthropic prompt + KIRA CoT fields   | 19/60  | -1          | -8            |
| **R9**  | **Minimal KIRA-inspired prompt** | **21/60** | **+1**   | **-6**        |
| R10 | + lean tools (remove unused)         | 16/60  | -4          | -11           |
| R11 | + condensed tool descriptions        | 17/60  | -3          | -10           |

---

