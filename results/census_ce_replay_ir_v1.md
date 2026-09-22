# Census CE-Replay-IR-v1-A: removing singleton response probes

## Milestone

This experiment asks whether the v0 empirical atom

`rho_s = estimate(query with only s) / estimate(query without extstats)`

can be removed. The v1-A IR instead serializes each real PostgreSQL MCV
payload through `pg_mcv_list_items` and computes the statistic response from:

- the fixed clause context;
- the no-extstats simple selectivity of the covered clauses;
- matching MCV item frequencies;
- matching MCV item base frequencies;
- total MCV-list frequency;
- PostgreSQL 16's `mcv_combine_selectivities` formula.

There are no singleton extended-statistics response measurements in v1-A.
The design-dependent GreedyCover transition is replayed exactly as in v0.

## Numerical node

For each consumed statistic, the payload evaluator computes

`other_sel = clamp(simple_sel - mcv_base_sel)`

`other_sel = min(other_sel, 1 - mcv_total_sel)`

`stat_sel = clamp(mcv_sel + other_sel)`

and applies `stat_sel / simple_sel` as the correction to the frozen no-MCV
query estimate. MCV item matching is evaluated directly against the frozen
integer equality/range predicates of Census `query.184`.

An important implementation finding is that `pg_mcv_list_items.values[]`
follows `pg_statistic_ext.stxkeys` attribute-number order, not necessarily the
textual column order in `CREATE STATISTICS`. Ignoring this distinction produced
a false 22.76x error for `(drpincome, idisabl1)`; resolving and serializing the
payload schema from `stxkeys` eliminated it.

## Exhaustive validation

Five candidates give 32 possible designs. The complete space was validated at
four statistics targets, with a fresh `ANALYZE` and fresh PostgreSQL oracle
estimates for every run.

| Target | Exact after rounding | Within 1% | Within 5% | Median error | Max error |
|---:|---:|---:|---:|---:|---:|
| 100 | 28/32 | 32/32 | 32/32 | 0.0571% | 0.1764% |
| 500 | 30/32 | 32/32 | 32/32 | 0.1979% | 0.7563% |
| 1000 | 31/32 | 32/32 | 32/32 | 0.0336% | 0.8165% |
| 2000 | 28/32 | 24/32 | 32/32 | 0.2702% | 1.7495% |
| **Combined** | **117/128** | **120/128** | **128/128** | **0.0347%** | **1.7495%** |

The largest relative error occurs at target 2000 for `{good}`: replay predicts
22.385 rows and PostgreSQL reports 22. Its absolute discrepancy is less than
one row; the percentage is inflated by the very small estimate. All 128 cases
are within 5%.

## What this establishes

Within the tested PG16/base-restriction/integer-MCV fragment, both halves are
now executable from a statistics-parametric IR:

`D -> GreedyCover(D) -> consumed MCV payloads -> MCV selectivity -> rows`

The design-dependent numerical response no longer comes from singleton query
measurements. It comes from serialized statistics payloads and PostgreSQL's
documented source semantics.

## Remaining boundary

This is route **v1-A**, an external semantic implementation, not yet the
preferred backend replay primitive. PostgreSQL still supplies fixed,
design-independent simple-selectivity context during instrumentation, and the
external evaluator currently supports the exact predicate forms used here
(integer equality and closed ranges). The residual sub-row differences arise
primarily because `EXPLAIN` exposes integer `Plan Rows`, including for the
frozen simple-selectivity context.

The next implementation step is v1-B: expose the same MCV node as a PostgreSQL
backend replay primitive so that it returns floating-point selectivities and
serves as reference semantics without duplicating version-specific estimator
code.

## Artifacts

- `tools/ce_replay_ir_v1.py`
- `results/census_ce_replay_ir_v1.json` (target 1000)
- `results/census_ce_replay_ir_v1_target100.json`
- `results/census_ce_replay_ir_v1_target500.json`
- `results/census_ce_replay_ir_v1_target2000.json`

All temporary extended-statistics objects were removed; the post-run catalog
count on `climate` was zero.
