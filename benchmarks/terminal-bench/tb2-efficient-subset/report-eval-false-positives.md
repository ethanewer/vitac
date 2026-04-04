# Report: Eval Agent False Positives in Headless Mode

## Summary

The eval agent in the plan-build-eval pipeline approves solutions that fail verification. Across 60 trials, **10 false positives** were observed (eval passed but verifier failed), concentrated in 3 tasks. The eval agent performs static code review but never executes the code to check runtime correctness, rendering it unable to catch semantic bugs.

## Impact

| Task | Eval Passed | Verifier Passed | False Positives |
|------|:-:|:-:|:-:|
| torch-tensor-parallelism | 5/5 | 0/5 | **5** |
| sparql-university | 5/5 | 2/5 | **3** |
| sanitize-git-repo | 2/5 | 0/5 | **2** |
| **Total** | **12** | **2** | **10** |

Because the eval agent approves these solutions on the first attempt, the fix-iteration loop never triggers. The build agent never receives feedback to correct its mistakes. Plan-build-eval scores only 0.333 vs 0.317 for build-only — the eval loop adds almost no value.

## Evidence

### torch-tensor-parallelism: 5/5 false positives

Every trial follows the same pattern. The eval agent reads the implementation, runs a syntax check, and approves without executing any tests.

**Trial GQfyPyB** (`jobs/2026-04-04__12-40-22/torch-tensor-parallelism__GQfyPyB/`):

The eval agent's complete tool sequence (from `artifacts/opencode-output.log`):
1. `READ /app/parallel_linear.py` — reads the implementation
2. `glob` — searches for related files
3. `glob` — searches again
4. `READ` plan file
5. `BASH: python3 -m py_compile parallel_linear.py` — syntax check only
6. `BASH: python -m py_compile parallel_linear.py` — syntax check again
7. `grep` — searches for patterns in source
8. `eval_result: pass=True`

The eval agent **never runs the actual tensor parallelism code**. It never tests whether `all_gather` or `all_reduce` produce correct results, whether weight sharding dimensions are correct, or whether forward passes match expected outputs. It approves based on reading the code and confirming it "looks correct."

Eval summary from GQfyPyB:
> "The implementation in /app/parallel_linear.py correctly implements both ColumnParallelLinear and RowParallelLinear classes according to the requirements: ColumnParallelLinear: Weight matrix is split along dim=0 (output features)..."

But the verifier gives reward=0.0 — the implementation has runtime bugs not visible from code review alone.

All 5 torch trials show the same pattern:
- `GQfyPyB`: eval pass, verifier fail (`result.json`)
- `NdTzRTa`: eval pass (after 2 attempts), verifier fail (`result.json`)
- `btuZ9Rv`: eval pass, verifier fail (`result.json`)
- `t4PVwh3`: eval pass, verifier fail (`result.json`)
- `yiNTY2K`: eval pass, verifier fail (`result.json`)

### sparql-university: 3/5 false positives

The eval agent approves SPARQL queries that have logic errors — incorrect filter semantics, missing PREFIX declarations, or wrong join patterns.

**Trial AN8aXbb** (`jobs/2026-04-04__12-40-22/sparql-university__AN8aXbb/`):

Eval summary:
> "The SPARQL query correctly implements all three requirements: 1. Full professors only: Uses FILTER(STRSTARTS(?role, \"Professor\")) which correctly matches \"Professor of...\" but excludes \"Assistant Professor of...\" roles."

Verifier: reward=0.0. The query has semantic errors not detectable by code review — the eval agent cannot execute the query against the TTL data to check results.

**Trial hJ8CKaq** (`jobs/2026-04-04__12-40-22/sparql-university__hJ8CKaq/`):

Eval summary:
> "The solution is correct and complete. It properly: (1) filters for full professors using STRSTARTS(?role, \"Professor\"), (2) checks that professors work in at least one EU country..."

Verifier: reward=0.0. Again, the eval agent reviews the SPARQL syntax and logic patterns but cannot detect that the query returns wrong results when executed.

3 of 5 trials are false positives: `AN8aXbb`, `G6dNiMy`, `hJ8CKaq`.
The 2 trials that correctly passed both eval and verifier (`PX898Nj`, `sbxF9kp`) happened to produce correct queries on the first build attempt.

### sanitize-git-repo: 2/2 false positives (of 2 eval runs)

**Trial 9PY4MXx** (`jobs/2026-04-04__12-40-22/sanitize-git-repo__9PY4MXx/`):

This trial notably used 2 eval attempts — the eval correctly identified an issue on the first attempt and triggered a fix iteration. After the fix, the eval approved (attempt 2). But the verifier still gave reward=0.0.

Eval summary:
> "All API keys, GitHub tokens, and HuggingFace tokens have been replaced with appropriate placeholder values... All placeholder values are consistent..."

The eval agent confirmed that secrets were replaced with placeholders by reading the files. But the verifier checks git history (the task requires sanitizing the repo history, not just the current files). The eval agent didn't check `git log` or `git diff` to verify history was clean.

## Root Cause

The eval agent (`session/eval.ts`) operates as a **static code reviewer**. It:
1. Reads the build agent's output files
2. Compares them against the task instruction
3. Makes a pass/fail judgment based on code/content analysis

It does **not**:
- Execute the code to test runtime behavior
- Run the output through the task's actual test suite
- Use bash to verify outputs match expected results
- Check side effects (git history, file system state, process output)

The eval agent has no mechanism to run verification commands. Its `eval_result` tool is called with a boolean pass/fail and a text summary — there is no execution step.

## Recommendation

The eval agent should be augmented to **execute verification commands** before making its pass/fail judgment. Specifically:

1. Give the eval agent access to the `bash` tool so it can run the code and check outputs
2. Include task-specific verification hints in the eval prompt (e.g., "run the SPARQL query against the data file and check the results")
3. For code generation tasks, require the eval agent to compile and run the code before approving
4. For file modification tasks (like sanitize-git-repo), require the eval agent to check the broader system state (git history, file permissions, etc.)

Without runtime verification, the eval loop is effectively a no-op for tasks where correctness depends on execution behavior rather than code structure.
