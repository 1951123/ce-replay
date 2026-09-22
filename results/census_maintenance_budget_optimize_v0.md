# Maintenance-Budget-Optimize-v0

## Scope

The frozen 468-query Census MCV+FD evaluator, candidate universe, payloads, q-error objective, fixed precedence, deterministic construction, and exhaustive best-improvement ADD/DROP/SWAP search are unchanged. Only candidate resource costs and budget feasibility use the empirical maintenance model. PostgreSQL and `ANALYZE` were not invoked.

## Maintenance model and budget

\[
C(Y)=|Y_{MCV}|+1.449|Y_{FD}|,
\qquad B_0=205+1.449(56)=\mathbf{286.144}.
\]

One MCV unit corresponds to approximately 1.875 ms/ANALYZE; one FD object to approximately 2.717 ms/ANALYZE in the measured environment. These are average, environment-specific coefficients.

## Result at B0

| Metric | Old byte-budget final design | Maintenance-budget design |
|---|---:|---:|
| Workload loss | 805.316471766631 | 787.809381279634 |
| MCV objects | 205 | 276 |
| FD objects | 56 | 7 |
| Total objects | 261 | 283 |
| Maintenance cost | 286.144 | 286.143 |
| Selected FD consumed | — | 7/7 |

Typed-candidate Jaccard similarity is **42.7822%** (163 intersection / 381 union). The new design adds 120 and removes 98 candidates relative to the old design. Loss changes by -17.507090486997 (-2.1739%).

## Optimizer audit

The unchanged v4 construction took 60.063s; the unchanged compositional local optimizer took 174.428s; total experiment time was 234.777s. It accepted 12 moves and then audited 565,031 feasible terminal ADD/DROP/SWAP moves. Terminal best delta is 3.74539805201e-05; local optimality under this neighborhood is **yes**. This is not a global-optimality claim.

All 7 selected FDs are consumed by at least one query.

## Interpretation

This is a resource-model alignment experiment, not a new optimization algorithm. Under explicit practical thresholds (Jaccard below 0.8 or symmetric change at least 20% of the old design), the selected design changes **materially**. Under a 1% relative-loss threshold, workload loss changes **materially**. The coefficients are not universal PostgreSQL costs and do not estimate individual-candidate maintenance latency.

## Required verdict

1. **What maintenance budget corresponds to the old final mixed design?** \(B_0=286.144\) normalized MCV units.
2. **Under that budget, what design does the optimizer select?** A fixed-precedence design with 276 MCV and 7 FD objects; complete IDs are in the JSON artifact.
3. **What is its workload loss?** 787.809381279634.
4. **How many MCV and FD objects are selected?** 276 MCV and 7 FD (283 total).
5. **How different is it from the previous byte-budget design?** Jaccard 42.7822%; 120 added and 98 removed; MCV/FD count changes +71/-49.
6. **Does changing the resource model materially change the selected design?** Yes under the stated design-change threshold.
7. **Does changing the resource model materially change workload loss?** Yes under a 1% relative threshold; change is -17.507090486997 (-2.1739%).
8. **Are selected FD objects actually consumed?** Yes; 7/7 are consumed.
9. **Is the resulting design locally optimal under the current ADD/DROP/SWAP neighborhood?** Yes; all 565,031 feasible terminal moves were audited and best delta is 3.74539805201e-05.
10. **Does the experiment support replacing payload-byte budget with mechanism-weighted maintenance budget in the core formulation?** Yes as an environment-specific first-order recurring-maintenance constraint: it is reproducible, keeps semantics/search unchanged, and directly represents the measured resource. It does not establish universal coefficients or per-candidate cost accuracy.
