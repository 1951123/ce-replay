# CE-Replay-Optimize-v1: Census workload scaling

## Scope

- PostgreSQL 16 base-relation `AND` restrictions;
- integer equality and closed-range predicates;
- pair-column MCV statistics only;
- 468 queries in the current Census `query.sql`;
- 2,253 distinct pair candidates;
- candidates ordered by decreasing workload degree, with lexical ties;
- statistics target 100;
- storage budget equal to 10% of total payload bytes, but at least one object;
- objective: unweighted sum of query q-errors.

This experiment does not add a new CE node family. Every evaluated query and
candidate remains inside the frozen MCV semantic boundary.

## Workload IR construction

All candidates for the largest requested scale are created in one fixed OID
order and populated by one `ANALYZE`. The instrumenter serializes each MCV
payload, its `stxkeys` schema, byte cost, and query incidence. For every query
it freezes the no-MCV raw estimate and the native simple selectivity context
for each incident candidate. Candidate payloads are then removed before the
offline optimizer runs.

For the full 2,253-candidate universe:

- create plus `ANALYZE`: 7.27 seconds;
- complete workload specialization: 12.27 seconds.

## Evaluator scaling

| Candidates | Full evaluation | Incremental toggle | Queries/toggle | Time speedup | Replay-count speedup |
|---:|---:|---:|---:|---:|---:|
| 100 | 0.385 ms | 25.8 us | 9.35 / 468 | 14.9x | 50.1x |
| 500 | 0.795 ms | 32.8 us | 7.30 / 468 | 24.3x | 64.1x |
| 1,000 | 0.972 ms | 35.7 us | 6.49 / 468 | 27.2x | 72.1x |
| 2,253 | 1.602 ms | 33.6 us | 4.36 / 468 | 47.7x | 107.3x |

The affected-query count falls at larger scales because the nested ladder is
degree-ranked: high-degree candidates enter first and the tail is increasingly
local. The measured result directly confirms the algorithmic value of the
candidate-to-query dependency map.

## Optimization quality

| Candidates | Random | Singleton greedy | Replay marginal greedy | Add/drop/swap search |
|---:|---:|---:|---:|---:|
| 100 | 10653.95 | 10608.60 | 10592.54 | 10592.54 |
| 500 | 9937.34 | 9477.89 | 8711.77 | 8711.35 |
| 1,000 | 9100.35 | 7011.62 | 1280.43 | 1279.00 |
| 2,253 | 4922.86 | 6966.36 | 812.67 | 806.26 |

At 2,253 candidates, singleton ranking is 8.57x worse than replay marginal
greedy and is even worse than the best of 20 random feasible designs. This is
direct evidence that `Delta_s(empty)` is not a reliable substitute for
`Delta_s(D)` at workload scale.

The selected-set Jaccard similarity between singleton and marginal greedy
drops from 0.571 at 100 candidates to 0.219 at 2,253. In the full marginal
design, 245 of 634 consumption rounds contain an OID-sensitive conflicting
alternative, across 180 queries. Thus the divergence is accompanied by
substantial design-dependent GreedyCover interaction rather than only budget
packing noise.

## Exact-small validation

At 5, 10, and 20 candidates, Gray-code exhaustive search updates only queries
affected by each toggled candidate. Singleton greedy, marginal greedy, and
add/drop/swap search all found the exact optimum at the tested budget. Random
was exact at 5 and 10 and 0.069% above optimum at 20.

## Optimizer runtime

All figures below are offline; PostgreSQL is not on the evaluation path.

| Candidates | Random (20) | Singleton | Marginal | Add/drop/swap |
|---:|---:|---:|---:|---:|
| 100 | 0.008 s | 0.002 s | 0.016 s | 0.014 s |
| 500 | 0.017 s | 0.007 s | 0.409 s | 0.922 s |
| 1,000 | 0.024 s | 0.013 s | 1.810 s | 13.100 s |
| 2,253 | 0.041 s | 0.025 s | 8.829 s | 278.677 s |

Replay execution itself is no longer the bottleneck. The naive all-pairs SWAP
neighborhood is: at full scale it spends 279 seconds for a 0.79% improvement
over marginal greedy. The next optimization work should prune/cache move
enumeration using interaction neighborhoods, not optimize the CE arithmetic.

## Native deployed validation

The experiment activated exactly the catalog payloads selected by seven
representative designs (empty; singleton, marginal, and local-search designs at
100 and 2,253 candidates) and replanned all 468 queries with the instrumented
PostgreSQL backend.

- comparisons: 3,276;
- matches within `1e-12`: 3,276 / 3,276;
- maximum relative error: `7.14e-15`.

This validates both the generic query specialization and the workload
optimizer outputs against PostgreSQL native pre-clamp CE.

## Conclusion

The first workload-scale result answers RQ3 positively for pair MCVs:

1. dependency-local incremental replay materially reduces evaluation cost;
2. design-dependent marginal evaluation materially changes optimization
   quality;
3. exact-small results validate the simple algorithms where an optimum is
   available;
4. full-scale native deployment validation preserves semantic fidelity;
5. the remaining full-scale bottleneck is neighborhood search, especially
   naive SWAP enumeration.

## Artifacts

- Runner and algorithms: `tools/ce_replay_optimize_v1.py`
- 5--1,000 scale result: `results/census_ce_replay_optimize_v1_scale1000.json`
- Full pair-universe result and workload IR:
  `results/census_ce_replay_optimize_v1_full_pairs.json`
- Offline runtime result: `results/census_ce_replay_optimize_v1_runtime.json`
