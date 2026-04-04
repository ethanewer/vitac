# Report: Build Agent Premature Termination

## Summary

The build-only agent terminates after a single write-then-exit cycle without verifying its output. On tasks that require iterative refinement — writing code, testing it, observing errors, and fixing — the agent produces an answer in 2-5 tool calls and declares the task complete. This uses only 83-173 seconds of a 900-second timeout. The same model (minimax-m2.7) scores 5/5 on the same tasks when used through Terminus-2's terminal loop, which inherently provides iterative feedback.

## Impact

| Task | Build-Only | Terminus-2 | Gap | Build Avg Duration | Timeout |
|------|:-:|:-:|:-:|:-:|:-:|
| sparql-university | 1/5 | 5/5 | **-4** | 118s | 900s |
| rstan-to-pystan | 0/5 | 4/5 | **-4** | 921s | 1800s |

These two tasks account for the entire 8-trial gap between build-only (19/60) and terminus-2 (27/60). Excluding them, build-only matches or exceeds terminus-2 on every other task.

## Evidence

### sparql-university: 1/5 vs 5/5 baseline

The agent reads the TTL data, writes a SPARQL query, and exits — without ever executing the query to check if it returns correct results. 4 of 5 trials fail because the query has logic errors that would be immediately visible if the agent ran the query.

**Failing trial pzVpbFD** (`jobs/2026-04-04__11-53-29/sparql-university__pzVpbFD/`):

Complete tool sequence from `artifacts/opencode-output.log`:
1. `READ /app/university_graph.ttl` — reads 11,695 chars of TTL data
2. `WRITE /app/solution.sparql` — writes first query attempt (616 chars)
3. `READ /app/solution.sparql` — re-reads to check
4. `WRITE /app/solution.sparql` — rewrites with fixes (1,114 chars)
5. `READ /app/solution.sparql` — re-reads again

Total: 5 tool calls, 142 seconds, 6 LLM steps, reward=0.0.

The agent's final text: "Query saved. The query: (1) Filters for full professors... (2) Uses a subquery to find departments with >10 currently enrolled students... (3) Verifies the professor works in at least one EU country..."

**The agent never ran `rasqal` or any SPARQL engine to test the query.** It wrote the query, read it back, and declared success. The query has a semantic bug: `FILTER(CONTAINS(?role, "Professor of"))` matches both "Professor of X" and "Assistant Professor of X", and the `FILTER NOT EXISTS` clause intended to exclude assistants doesn't work correctly due to the variable scoping.

**Passing trial 82WAAkg** (`jobs/2026-04-04__11-53-29/sparql-university__82WAAkg/`):

Tool sequence: `READ` → `WRITE` → `edit` → `READ`. Duration: 86s, reward=1.0.

This trial happened to produce a correct query using `FILTER(STRSTARTS(?role, "Professor"))` with `FILTER(!STRSTARTS(?role, "Assistant"))`. But this was luck — the agent used the same write-and-exit pattern.

**All 5 trials followed the same pattern:**

| Trial | Duration | Tool Calls | LLM Steps | Reward |
|-------|:--------:|:----------:|:---------:|:------:|
| 82WAAkg | 86s | 4 | 5 | 1.0 |
| ebMzhJK | 173s | 5 | 6 | 0.0 |
| gQg4BXh | 105s | 3 | 4 | 0.0 |
| pzVpbFD | 142s | 5 | 6 | 0.0 |
| yPgGqrc | 83s | 2 | 3 | 0.0 |

Average: 118 seconds and 3.8 tool calls. With a 900-second timeout, **the agent used only 13% of its available time**.

**Contrast with Terminus-2**: Terminus-2 scored 5/5 on sparql-university using the same model. Terminus-2's terminal loop approach means it naturally writes a query, runs it, sees the output, and refines — the iterative feedback is built into its architecture. All 5 Terminus-2 trials passed: `b6QQp8J`, `htrHDsi`, `wKkWQL7`, `ekAdffy`, `XrrxjHJ`.

### rstan-to-pystan: 0/5 vs 4/5 baseline

Two distinct failure modes:

**Mode 1: Quick exit (trials exuEb8Q, jxAqrZF)** — 135-235 seconds.

Trial exuEb8Q (`jobs/2026-04-04__11-53-29/rstan-to-pystan__exuEb8Q/`):

Tool sequence from `artifacts/opencode-output.log`:
1. `READ /app/gp_rstan.R` — reads the R Stan code
2. `READ /app/train_X.csv`, `READ /app/train_y.csv`, `READ /app/test_X.csv`
3. `READ /app/meta_public.json`
4. `BASH: pip install pystan==3.10.0` — installs PyStan
5. `BASH: pip install pystan==3.10.0 --break-system-packages`
6. `WRITE /app/pystan_analysis.py` — writes the conversion
7. `BASH: cd /app && python pystan_analysis.py` — runs it

Output: `/usr/bin/bash: line 1: python: command not found`

The agent used `python` instead of `python3` and did not recover. Total: 9 tool calls in 135 seconds, then exit. The agent did not try `python3` or investigate the error.

**Mode 2: Long struggle (trials kYWQ6we, ucukLYo, ZgCYN4h)** — 636-1800 seconds.

Trial kYWQ6we (`jobs/2026-04-04__11-53-29/rstan-to-pystan__kYWQ6we/`):

51 bash calls and 8 edit calls over 1800 seconds (full timeout). The agent wrote the script, encountered PyStan 3.x API errors, and spent the entire timeout trying to fix them:

Errors encountered (from `artifacts/opencode-output.log`):
- `ValueError: {'json': {'max_treedepth': ['Unknown field.']}}` — PyStan 3.x removed `max_treedepth` from sampling kwargs
- `ValueError: {'json': {'thin': ['Unknown field.']}}` — `thin` parameter also removed
- `AttributeError: 'Fit' object has no attribute 'sample'` — PyStan 3.x uses different API for extracting samples
- Memory exhaustion during Stan model compilation

The agent iterated many times but could not find the correct PyStan 3.x API. It kept trying variations of the same incorrect approach (passing Stan 2.x sampling parameters to PyStan 3.x).

**Contrast with Terminus-2**: Terminus-2 scored 4/5 using the same model and same task. The terminal loop approach means Terminus-2 sees error messages immediately and can quickly try different approaches. The key difference: Terminus-2's interaction style lets the model accumulate knowledge from each failed attempt in its terminal history, while OpenCode's build agent may lose context between tool calls.

## Root Cause

The build agent's `opencode run --agent build` flow terminates when the model produces a final text response without further tool calls. There is no built-in verification step. The agent's behavior is:

1. Read task files
2. Write solution
3. (Maybe) re-read solution to check
4. Produce summary text → session goes idle → exit

The agent never runs test commands to verify its output. This is a fundamental architectural difference from Terminus-2, which operates in a continuous terminal loop where every command's output is visible and feeds into the next decision.

For sparql-university, the fix would be trivial: run the SPARQL query against the data before declaring success. The agent has bash access and could do this. It simply doesn't.

For rstan-to-pystan Mode 1, the agent should retry with `python3` after `python` fails. The quick-exit behavior suggests the agent doesn't treat command-not-found as a recoverable error.

## Recommendation

1. **Add self-verification to the build agent's system prompt**: Instruct the agent to always test its output before concluding. For code tasks: compile and run. For data tasks: validate output format. For query tasks: execute and check results.

2. **Implement an explicit verification step in the build workflow**: After the build agent's initial solution, automatically run a verification command (if one can be derived from the task instruction) before marking the session as idle.

3. **Increase iteration persistence**: The agent gives up after seeing errors in Mode 1 trials. Configuring the model to be more persistent (e.g., via system prompt: "if a command fails, try alternative approaches before giving up") could help.

4. **Consider a hybrid approach**: Use OpenCode's structured tool access for file operations and code generation, but add a terminal-style feedback loop for testing and iteration — similar to how Terminus-2 operates.
