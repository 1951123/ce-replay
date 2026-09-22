# Analyze-Cost-Model-v0

## Scope and method

PostgreSQL 16.14, Census `climate` (2,458,285 rows), 2,253 available MCV candidates and 758 available FD candidates. Each configuration was measured with 10 wall-clock `ANALYZE` repetitions after definitions existed. Non-all pure-mechanism counts use 3 deterministic subsets. Configuration order after `EMPTY` was deterministically shuffled. CREATE/DROP time is excluded.

All catalog and payload mutations ran in an isolated database snapshot cloned from `census`. The snapshot was dropped after measurement; the source database's original 205 MCV + 56 FD deployment was never modified.

## Baseline

`EMPTY` mean/median/std/CV: **0.236111s / 0.234644s / 0.007073s / 3.00%**.

Individual times: `[0.253561, 0.240691, 0.238588, 0.238203, 0.233581, 0.229181, 0.230791, 0.235706, 0.233253, 0.227552]`.

## Fitted first-order models

| Model | Intercept (s) | MCV/object (ms) | FD/object (ms) | R² | RMSE (s) | Median relative error |
|---|---:|---:|---:|---:|---:|---:|
| MCV-only | 0.234038 | 1.874997 | — | 0.994936 | 0.101248 | 3.09% |
| FD-only | 0.250559 | — | 2.717261 | 0.996367 | 0.036700 | 2.57% |
| Uniform | 0.332317 | 1.900413 (uniform) | 1.900413 (uniform) | 0.971460 | 0.208315 | 13.46% |
| Mechanism-specific | 0.236684 | 1.875234 | 2.776223 | 0.994751 | 0.089337 | 2.82% |

Approximate 95% normal confidence intervals and all observed-versus-predicted residuals are in the JSON artifact. The intervals treat repeated timings as observations and are descriptive rather than cluster-robust inferential intervals. These are empirical first-order fits, not claims that PostgreSQL's true cost is exactly linear.

## Noise and subset variation

Median/max within-configuration CV is 3.57%/9.28%. Median/max CV across subset means at the same mechanism/count is 1.56%/4.62%. The largest observed aggregate count effect over `EMPTY` is 4.223067s, compared with baseline run-to-run std 0.007073s.

The mechanism-specific model improves RMSE over the uniform model by 57.11%; the pure-curve marginal slope ratio is 1.449x. Under the preregistered practical rules in the JSON, linear first-order adequacy is **yes** and separate mechanism costs are **warranted**.

## Interpretation

This experiment measures recurring `ANALYZE` wall-clock cost after definitions exist. It excludes CREATE/DROP, candidate generation, replay, and optimization. Object count is a defensible first-order proxy in this environment. It is not a complete model of collection/refresh cost across tables, schemas, hardware, targets, PostgreSQL versions, or candidate arities.

## Required verdict

1. **What is the measured table-level baseline ANALYZE latency?** Mean 0.236111s; median 0.234644s; std 0.007073s; CV 3.00%.
2. **Does ANALYZE latency increase systematically with the number of deployed extended statistics?** Yes; fitted pure-mechanism slopes are 1.874997 ms/MCV and 2.717261 ms/FD.
3. **What is the estimated average marginal cost per MCV object?** 1.874997 ms/object (MCV-only first-order fit).
4. **What is the estimated average marginal cost per FD object?** 2.717261 ms/object (FD-only first-order fit).
5. **How large is run-to-run ANALYZE timing noise relative to the aggregate statistics-count effect?** Baseline std is 0.007073s versus a largest observed mean effect of 4.223067s; median/max within-configuration CV is 3.57%/9.28%.
6. **How large is variation between different subsets having the same object count?** Median/max CV of subset means is 1.56%/4.62%; per-count values are in `noise.subset_variation`.
7. **Is a linear model adequate as a first-order approximation?** Yes under the stated R² and median-error rule.
8. **Is a single uniform per-object cost adequate?** No.
9. **Or should MCV and FD use separate average costs?** Yes; mechanism-specific RMSE improvement is 57.11% and pure slope ratio is 1.449x.
10. **Is statistics-object count a defensible proxy for recurring ANALYZE maintenance cost?** Yes, as a first-order proxy in this tested setting.
11. **Should the current physical-design formulation use a uniform count budget or a mechanism-weighted count budget?** mechanism-weighted object-count budget if this empirical maintenance resource is adopted; the optimizer is not modified here.
12. **What limitations must accompany this cost model?** One table/workload, one PostgreSQL version and machine, pair-column candidates, target 100, warm repeated runs, limited mixed points, average rather than per-object costs, and no CREATE/DROP, payload-size, collection-frequency, concurrency, I/O-regime, higher-arity, or cross-table effects.
