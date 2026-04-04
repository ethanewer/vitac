# TerminalBench 2.0: 12-Task Efficient Subset

This document defines a 12-task subset of TerminalBench 2.0 that efficiently estimates full benchmark scores. Each task should be run **5 times** (N=5), matching the full benchmark protocol.

**Accuracy**: 95% confidence the estimate is within **6.0%** of the true score; 99% confidence within **9.2%**.

## Tasks

Run these 12 tasks, each 5 times:

1. chess-best-move
2. circuit-fibsqrt
3. compile-compcert
4. extract-elf
5. git-leak-recovery
6. multi-source-data-merger
7. path-tracing
8. rstan-to-pystan
9. sanitize-git-repo
10. sparql-university
11. sqlite-db-truncate
12. torch-tensor-parallelism

## Score Conversion

Compute each task's pass rate (fraction of 5 trials that passed). Then apply these weights:

```
estimated_full_score = -0.028084
    + 0.252448 * git_leak_recovery
    + 0.071363 * circuit_fibsqrt
    + 0.068956 * sparql_university
    + 0.067675 * sqlite_db_truncate
    + 0.063315 * path_tracing
    + 0.060527 * compile_compcert
    + 0.057654 * multi_source_data_merger
    + 0.055432 * rstan_to_pystan
    + 0.054852 * torch_tensor_parallelism
    + 0.044294 * chess_best_move
    + 0.037903 * extract_elf
    + 0.032998 * sanitize_git_repo
```

Each variable is the pass rate for that task (0.0, 0.2, 0.4, 0.6, 0.8, or 1.0).

## Estimated Runtime

| Concurrency | Mean Runtime | Std Dev |
|------------:|-------------:|--------:|
| 1           | 13.0 h       | 1.2 h   |
| 4           | 3.5 h        | 0.4 h   |
| 8           | 2.0 h        | 0.3 h   |
| 12          | 1.5 h        | 0.2 h   |
| 16          | 1.3 h        | 0.2 h   |

## Interpreting Results

The error bounds mean: if your estimated full score is 72%, the true full-benchmark score is between roughly 66% and 78% with 95% confidence.

The subset is most accurate in the middle of the score range (30-80%) and may be slightly less reliable at the extremes.

## Accuracy vs. Number of Trials

Running fewer trials per task saves time but widens the error bounds. The table below shows how the 12-task subset degrades with fewer trials:

| N (trials/task) | Serial Runtime | ε₉₅   | ε₉₉   |
|----------------:|---------------:|-------:|-------:|
| 1               | 2.6 h          | 11.9%  | 18.8%  |
| 2               | 5.2 h          | 8.8%   | 12.9%  |
| 3               | 7.8 h          | 7.6%   | 10.9%  |
| 4               | 10.4 h         | 6.5%   | 10.1%  |
| 5               | 13.0 h         | 6.0%   | 9.2%   |

## Pareto Frontier

The table below shows the Pareto-optimal configurations: those where no other configuration achieves both lower error and lower runtime. All error bounds are computed with the same methodology (LOOCV + trial resampling) and are directly comparable.

| Tasks |  N | Serial | ε₉₅    | ε₉₉    |
|------:|---:|-------:|-------:|-------:|
| 5     |  1 | 1.3 h  | 14.0%  | 20.6%  |
| 7     |  1 | 1.8 h  | 13.8%  | 19.1%  |
| 9     |  1 | 2.0 h  | 12.3%  | 18.0%  |
| 10    |  1 | 2.5 h  | 12.2%  | 17.9%  |
| 12    |  1 | 2.6 h  | 11.9%  | 18.8%  |
| 5     |  2 | 2.6 h  | 11.6%  | 17.1%  |
| 7     |  2 | 3.6 h  | 10.5%  | 15.8%  |
| 9     |  2 | 3.9 h  | 9.9%   | 13.8%  |
| 12    |  2 | 5.2 h  | 8.8%   | 12.9%  |
| 13    |  2 | 5.6 h  | 8.6%   | 12.9%  |
| 12    |  3 | 7.8 h  | 7.6%   | 10.9%  |
| 13    |  3 | 8.4 h  | 7.3%   | 10.7%  |
| 15    |  3 | 10.1 h | 6.9%   | 10.9%  |
| 12    |  4 | 10.4 h | 6.5%   | 10.1%  |
| 13    |  4 | 11.3 h | 6.3%   | 9.9%   |
| 12    |  5 | 13.0 h | 6.0%   | 9.2%   |
| 13    |  5 | 14.1 h | 5.9%   | 8.8%   |
| 15    |  5 | 16.9 h | 5.7%   | 8.7%   |

Key observations:
- **More tasks at fewer trials beats fewer tasks at more trials.** At ~5h, 12 tasks × N=2 (ε₉₅=8.8%) beats 5 tasks × N=4 (ε₉₅=9.7%).
- **12-13 tasks dominate the frontier.** They appear at every N from 1 to 5, confirming that 12 tasks is the right subset size.
- **At ~8h, 12 tasks × N=3 (ε₉₅=7.6%)** is the best configuration, beating 8 tasks × N=4 and 5 tasks × N=5.
- **At ~10h, 12 tasks × N=4 (ε₉₅=6.5%)** is the most efficient way to reach sub-7% error.
- **Diminishing returns beyond N=3** are steep: going from N=3 to N=5 costs 5.2h more serial time but only reduces ε₉₅ from 7.6% to 6.0%.

## Reproducing

```bash
# Run the analysis (produces results.json)
python analyze.py

# Generate the Pareto frontier figure (produces pareto_frontier.png)
python plot.py
```

`analyze.py` expects the TerminalBench 2.0 leaderboard repo at `../terminal-bench-2-leaderboard/`. Override with `--data-dir`.

## Methodology

### Task Selection and Weighting

The subset was selected by greedy forward selection: starting from an empty set, at each step the task whose addition most improves leave-one-out cross-validation R² is added. At each step, an OLS linear model with one weight per task plus an intercept is fit to predict the full 85-task benchmark score. After greedy selection, local search (single-task swaps) was applied to further improve the LOOCV R².

Each task has its own learned weight, allowing the model to account for the fact that some tasks are more informative about overall agent ability than others.

### Error Bounds

Error bounds were computed via LOOCV combined with trial resampling. For each of the 45 held-out submissions: (1) OLS weights are fit on the remaining 44, (2) N trials per task are resampled with replacement from the held-out submission's trial pool, (3) the resampled pass rates are used with the held-out weights to predict the full score. This is repeated 2,000 times per fold. The 95th and 99th percentiles of |error| across all folds and resamples give the reported bounds. This captures both model estimation error and binomial sampling noise from running a finite number of trials.

### Runtime Estimates

Runtimes were estimated via Monte Carlo simulation (10,000 trials). For each simulation, per-task trial runtimes were sampled from the empirical distribution of wall-clock times observed across all TerminalBench 2.0 submissions. Task runs were placed in random order and dispatched to a pool of concurrent workers using a greedy scheduler.

### Data Source

All data was pulled from the TerminalBench 2.0 leaderboard repository (terminal-bench/terminal-bench-2-leaderboard on HuggingFace). 45 submissions covering at least 85 of 89 tasks were included, with scores ranging from 17.6% to 82.8%.
