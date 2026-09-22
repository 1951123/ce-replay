# CE-Replay-Optimize-v4: Joint MCV+FD Workload Optimization

## Setup

- Workload: 468 Census queries.
- MCV candidates: 2,253 frozen pair-MCV nodes from v1.
- FD candidates: 758 query-applicable pair objects with non-empty native
  dependency payloads in this `ANALYZE` realization.
- Shared storage budget: 105,061 bytes.
- Objective: sum of per-query q-errors.
- Replay order: MCV GreedyCover updates `remaining/estimatedclauses`, then FD
  collects all still-applicable dependencies, greedily consumes implied
  attributes, and applies the selected dependencies in reverse order.

The FD payload is read through `pg_dependencies_send()` and decoded as native
binary doubles. Simple selectivities, baseline estimates, and `reltuples` are
all captured from the same `ANALYZE` realization.

## Four-strategy ablation

| strategy | loss | MCV | FD | used bytes | selected FD never consumed |
|---|---:|---:|---:|---:|---:|
| MCV-only | 813.521522 | 209 | 0 | 105,046 | 0 |
| FD-only | 11,791.247523 | 0 | 203 | 5,943 | 0 |
| independent MCV+FD | 813.942274 | 203 | 97 | 105,043 | 72 |
| **joint semantic** | **806.443575** | 206 | 54 | 105,056 | **0** |

The empty-design loss is 11,808.960379. FD-only exhausts its positive moves
after only 5,943 bytes, so it is complementary but not competitive with MCV on
this workload.

Joint semantic optimization improves over independent selection by
`7.498699` loss units, or **0.9213%**, and over MCV-only by `7.077947`, or
**0.8700%**. The winning joint trajectory starts from the independent design,
removes harmful/redundant choices under the composed semantics, and refills
the budget using true joint marginal benefits.

The independent optimizer selects each mechanism using its isolated marginal
response. After composing the resulting design, only 25 of its 97 selected FD
objects are ever consumed. Thus **72/97 (74.23%)** of selected FD objects and
2,210 bytes (**2.10% of the total budget**) pay physical-design cost but have
zero workload contribution. The joint design selects 54 FD objects and every
one is consumed by at least one query.

This is direct workload-level evidence that

`G(MCV + FD) != G(MCV) x G(FD)`

is relevant to the physical-design decision, not merely to replay fidelity.

## Cross-mechanism interaction census

- Potential directed `MCV -> FD` suppression edges: **37,808**.
- MCV nodes incident to a cross edge: 2,239 / 2,253.
- FD nodes incident to a cross edge: 758 / 758.
- FD candidates affected per MCV: mean 16.89, median 16, maximum 59.
- MCV candidates capable of affecting each FD: mean 49.88, median 49,
  maximum 99.
- Per query: mean 106.50 cross edges, median 63, maximum 1,025.
- Queries with at least one cross edge: 435 / 468.
- In the final joint design, 58 query-level FD-consumption events differ from
  the same FD selection evaluated without MCV.

The cross-mechanism graph is therefore neither rare nor confined to a few
hubs. Nevertheless, explicit semantics allow the optimizer to avoid all
globally never-consumed FD selections.

## Native validation

The selected FD-only workload design was physically activated and checked on
all 468 queries against native pre-clamp PostgreSQL estimates:

- matches at relative tolerance `1e-12`: **468 / 468**;
- median relative error: **0.0**;
- maximum relative error: **6.66e-16**.

Two implementation details were necessary for floating-point fidelity:

1. `pg_dependencies::text` prints degrees to only six decimal places, so the
   replay must consume the binary payload rather than its textual rendering.
2. Per-column simple selectivities must use `reltuples` from the same
   `ANALYZE`; reusing the earlier MCV IR denominator introduced an artificial
   relative discrepancy of roughly `7e-5`.

The mixed final design has not been physically redeployed in this experiment:
its MCV nodes intentionally use the frozen v1 payload while its FD nodes use
the current payload. Native mixed-node composition itself was already checked
in `FD-Semantics-v0`; a fresh mixed deployment would additionally measure
sampling drift and should be treated as a separate deployment experiment.

## Artifacts

- `tools/ce_replay_optimize_v4.py`: specialization, stateful replay,
  optimization, census, and native FD validation.
- `results/census_ce_replay_optimize_v4.json`: full candidate payloads,
  workload IR, selected designs, traces, and measurements.

