# Native replay validation and exact optimization closed loop

## v1-B native validation

PostgreSQL 16.14 was built in an isolated `/tmp` prefix with two observation
points:

- native `simple`, matching MCV, matching base, total MCV, and combined
  statistic selectivity immediately after `mcv_combine_selectivities()`;
- raw base-relation rows immediately before `clamp_row_est()`.

The Census `climate` table was copied logically from the existing PG16.15
instance into the isolated server. No production data directory was opened by
the custom binary.

Across targets 100, 500, 1000, and 2000, all 32 candidate subsets were tested:

| Target | Floating-point matches | Median relative error | Maximum relative error |
|---:|---:|---:|---:|
| 100 | 32/32 | 1.36e-16 | 2.90e-16 |
| 500 | 32/32 | 2.20e-16 | 5.32e-16 |
| 1000 | 32/32 | 1.85e-16 | 5.55e-16 |
| 2000 | 32/32 | 1.28e-16 | 5.27e-16 |
| **Total** | **128/128** | — | **5.55e-16** |

This pins down the core claim for the tested fragment: serialized MCV payloads
plus executable IR semantics reproduce PostgreSQL's native, pre-clamp CE to
floating-point precision. The earlier percentage residuals were downstream
observation artifacts, particularly `clamp_row_est`, not missing MCV semantics.

## CE-Replay-Optimize-v0

The target-1000 IR was optimized for Census `query.184` with truth rows 13.
Candidate cost is the real `pg_column_size(stxdmcv)` payload size. All 32
designs and all 32 distinct feasible budget thresholds were enumerated.

| Candidate | Cost (bytes) |
|---|---:|
| `good` | 436 |
| `middle` | 410 |
| `bad` | 388 |
| `independent_1` | 1340 |
| `independent_2` | 218 |

The exact optimum changes at these budget points:

| Budget | Selected design | Used | Predicted rows | Native PG rows | q-error |
|---:|---|---:|---:|---:|---:|
| 0 | `{}` | 0 | 54222.066095 | 54222.066095 | 4170.9282 |
| 218 | `{independent_2}` | 218 | 54094.432274 | 54094.432274 | 4161.1102 |
| 410 | `{middle}` | 410 | 1231.656842 | 1231.656842 | 94.7428 |
| 436 | `{good}` | 436 | 30.431145 | 30.431145 | 2.3409 |
| 654 | `{good, independent_2}` | 654 | 30.359513 | 30.359513 | 2.3353 |

For every one of the 32 budget thresholds:

- the replay optimizer selected the same design as exhaustive native-PG oracle
  optimization;
- the selected design's predicted and deployed native rows agree within
  2.70e-16 relative error.

Thus the complete tested loop is operational:

`PG instrumentation -> G(D) -> exact optimize -> selected D* -> PG validation`

The experiment demonstrates utility beyond replay: native CE semantics can be
compiled into an offline physical-design objective whose exact optimum agrees
with exhaustive PostgreSQL reference semantics.

## Artifacts

- Native observation patch:
  `postgresql-16.14/src/backend/statistics/extended_stats.c` and
  `postgresql-16.14/src/backend/optimizer/path/costsize.c`
- External replay/instrumentation runner: `tools/ce_replay_ir_v1.py`
- Exact optimizer: `tools/ce_replay_optimize_v0.py`
- Frozen contract: `docs/ce-replay-ir-v1.md`
- Full optimization result: `results/census_ce_replay_optimize_v0.json`
- Native validation files:
  `results/census_ce_replay_ir_v1b_instrumented_target{100,500,1000,2000}.json`
