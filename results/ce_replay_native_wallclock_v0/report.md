# CE-Replay-Native-WallClock-v0

## Outcome

All admitted correctness gates passed. Warm full replay was faster than the
client-observed PostgreSQL oracle for both workloads. Native CE was slower than
full Python replay on Census but faster on DMV. Semantic incremental replay was
faster than full replay in every ADD/DROP/SWAP workload and affected-scope
cell, and reproduced the 19-move Census trajectory 5.62x faster.

Overall classification: **R0 — strong runtime evidence**.

## State and implementation

- Start: `HEAD = main = origin/main = 9ff43888013b694c4920cd4bef31f4c4af9ba42d`;
  research freeze peeled commit `22cf494f954cffff86080236473ca847064dca74`.
- Pre-existing uncommitted DMV files were preserved. Nothing was reset,
  cleaned, committed, pushed, or tagged.
- PostgreSQL 16.14 was built with the measurement-only patch in
  `postgres_patch.diff`. Disabled-by-default `ce_replay_measure_timing`
  brackets the complete `clauselist_selectivity()` call in
  `set_baserel_size_estimates()`, accumulates nanoseconds/invocations, and
  suppresses existing `CE_REPLAY_MCV/FD/RAW_ROWS` notices while timing.
  The persisted diff is against pristine PostgreSQL 16.14, so it also displays
  the pre-existing semantic-trace NOTICE instrumentation for full provenance.
- `T_PG-plan` is client-observed `EXPLAIN (FORMAT JSON)` request-to-result time.
  `T_PG-CE` is server-side time inside the bracket. `T_Replay-full` is warm
  complete-workload replay plus objective aggregation. `T_Replay-inc` is exact
  supplied-move affected-scope evaluation and delta aggregation; trajectory
  time also includes commit/invalidation.

## Correctness gates

| Gate | Result |
|---|---:|
| Timing off/on representative cases | 4/4 exact raw-row matches |
| Semantic CE trace notices during timing | 0 |
| Census fresh native/replay | 468/468; max rel. error 5.83e-16 |
| DMV fresh native/replay | 1,965/1,965; max rel. error 2.94e-14 |
| Sampled full/incremental moves | 192/192 |
| Census trajectory objective states | 19/19 |

Census used the existing final mixed design, physically recreated as 205 MCV
plus 56 FD objects with fresh matching payloads and fixed OID precedence. Its
objective was 794.770340895. DMV used the corrected
`dmv_nonzero_baseline_v0` state (12 MCV plus 4 FD), without claiming a valid
maintenance-constrained optimum. Its positive-truth objective was
45,259.9012541; both zero-truth queries remained semantic checks only.

## Environment and protocol

- Intel Core i7-14650HX, 24 logical CPUs, WSL2 kernel
  `6.6.87.2-microsoft-standard-WSL2`, Python 3.12.3, PostgreSQL 16.14.
- One client/backend; no parallel replay; no affinity pinning. Frequency
  scaling and host contention were not controlled. Normal Python GC remained
  enabled.
- PostgreSQL: 512 MB shared buffers, random page cost 1.1, statistics target
  100.
- Five warmup batches, power-of-two calibration above 100 ms, exactly 30
  measured batches. Raw batch times and calibration attempts are persisted.

## Full-workload results

| Workload / path | Median | p25 | p75 | p95 | Mean | SD | batch ops |
|---|---:|---:|---:|---:|---:|---:|---:|
| Census `T_PG-plan` | 90.867 ms | 89.382 | 92.366 | 94.827 | 90.831 | 2.558 | 2 |
| Census `T_PG-CE` | 10.241 ms | 10.158 | 10.343 | 10.491 | 10.254 | 0.150 | 2 |
| Census `T_Replay-full` | 1.884 ms | 1.841 | 1.911 | 2.025 | 1.892 | 0.085 | 64 |
| DMV `T_PG-plan` | 294.542 ms | 287.262 | 304.257 | 360.306 | 303.086 | 26.738 | 1 |
| DMV `T_PG-CE` | 47.603 ms | 46.638 | 48.224 | 52.329 | 48.056 | 2.133 | 1 |
| DMV `T_Replay-full` | 85.472 ms | 84.408 | 87.029 | 88.784 | 85.723 | 1.877 | 2 |

Census native planner/full replay = **48.24x** and native CE/full replay =
**5.44x**. DMV ratios are **3.45x** and **0.557x** respectively; full Python
replay was about 1.80x slower than native DMV CE. Classifications are Census
**P1/E1** and DMV **P1/E3**.

## Independent move results

| Workload | Family | population | tertiles | median affected | full median | incremental | ratio |
|---|---|---:|---:|---:|---:|---:|---:|
| Census | ADD | 2,751 | 3 / 5 | 4.0 | 2.473 ms | 40.36 us | 61.28x |
| Census | DROP | 260 | 3 / 5 | 4.5 | 2.433 ms | 55.19 us | 44.08x |
| Census | SWAP | 715,260 | 7 / 9 | 7.5 | 2.786 ms | 88.48 us | 31.49x |
| DMV | ADD | 34 | 498 / 507 | 502.0 | 157.874 ms | 48.975 ms | 3.22x |
| DMV | DROP | 35 | 486 / 497 | 494.0 | 149.857 ms | 50.217 ms | 2.98x |
| DMV | SWAP | 1,190 | 752 / 861 | 847.0 | 139.273 ms | 72.432 ms | 1.92x |

Each pooled and tertile cell used eight deterministic moves. All 24 cells
favored incremental replay. Census ratios ranged from 16.34x to 190.90x; DMV
ranged from 1.82x to 3.46x. All six move families are therefore **I1**.
Affected-query counts are the exact structural work measure; DMV replayed that
affected set, while Census mechanism-level counts are reported for trajectory.

## Fixed Census trajectory

The exact 19 accepted moves from the recorded compositional trajectory were
used; search was not rerun. Every objective state matched. Full recomputation
median was **45.093 ms** and incremental evaluation including commit and
invalidation was **8.031 ms**, a **5.615x** ratio. Incremental work comprised
109 MCV-to-FD compositional replays and 33 FD-only replays.

## Existing evidence verification

- Semantic-Optimizer-v0: 289.01321861 s oracle, 82.422366446 s semantic,
  3.50649x; 51,222,119 versus 299,011 control replays (171.305x reduction).
- Compositional-Semantic-Optimizer-v0: 45.045419737 s factorized oracle versus
  145.677819196 s semantic (about 3.23x slower), with 58.892x full-to-local and
  154.607x local-to-semantic control reductions.

These remain supporting optimizer-phase measurements, not substitutes for the
new operation-level benchmark.

## Final matrix

| Case | T_PG-plan | T_PG-CE | T_Replay-full | T_Replay-inc |
|---|---|---|---|---|
| Census realized workload | COMPLETE | COMPLETE | COMPLETE | NOT APPLICABLE |
| DMV realized workload | COMPLETE | COMPLETE | COMPLETE | NOT APPLICABLE |
| Census ADD/DROP/SWAP | INVALID | INVALID | COMPLETE | COMPLETE |
| DMV ADD/DROP/SWAP | INVALID | INVALID | COMPLETE | COMPLETE |
| Census trajectory | INVALID | INVALID | COMPLETE | COMPLETE |

Native move cells are invalid because PostgreSQL exposes no frozen-payload
hypothetical-subset API. No physical realization or `ANALYZE` was inside a CE
timer.

## Claim boundary and confounders

Supported: in this environment, CE-Replay reduced black-box estimate-
acquisition time for both realized workloads, and exact semantic incremental
evaluation reduced counterfactual move and trajectory wall-clock relative to
full replay.

Not supported: search-algorithm superiority; universal Python/native CE
superiority; treating EXPLAIN time as estimator time; a valid DMV maintenance-
constrained optimum; or generalization beyond these workloads and machine.

Confounders include C versus Python, EXPLAIN formatting and IPC, one compact
post-region timing NOTICE in the black-box path, WSL2/host scheduling, unpinned
CPUs, uncontrolled frequency scaling, and workload-structure differences. No
implementation was tuned after timing began, no move/design was removed after
observing results, no optimizer-quality experiment ran, and DMV maintenance
optimization remained closed.

Recommended next action: freeze and review this evidence package before any
manuscript change; do not run another performance experiment.
