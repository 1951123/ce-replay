# DMV-Deploy-v0

## Outcome

Exactly 11 MCV and 12 FD objects from the authoritative design artifact were created in its recorded order; physical OIDs were strictly increasing. Exactly one fresh target-100 `ANALYZE` was executed. No reoptimization, design change, precedence optimization, or repeated ANALYZE occurred.

Fresh replay/native semantic validation passed 1,965/1,965 comparisons at tolerance 1e-12; maximum relative error 2.43422e-14, maximum absolute error 7.45058e-09, bitwise equal 688.

The deployment exposed an upstream artifact blocker: The authoritative frozen artifacts omit per-query baseline rows and clause selectivities, so frozen per-query estimates, zero-truth contributions, nonzero-truth loss, and frozen-to-fresh estimate-drift distribution cannot be reconstructed exactly after cleanup. Fresh semantics and physical composition are validated, but the mandatory frozen numerical drift and frozen zero-truth decomposition cannot be supplied without inventing data or running a new optimization realization. The final gate is therefore a blocker.

## Fresh realization

- Cost-model prediction: 0.238645841 s; observed: 0.303734822 s; absolute/relative error 0.065088981 s / 21.4295%.
- Fresh MCV payloads: 11/11; consumed 11/11.
- Fresh FD payloads: 11/12; consumed 11/12; unavailable 1.
- Queries consuming FD: 389.
- Fresh replay/native loss: 9.96836642987e+298 / 9.96836642987e+298; nonzero-truth diagnostic 85014.8083461 / 85014.8083461.
- Zero-truth queries: dmv.173, dmv.943; fresh contribution 9.96836642987e+298; frozen contribution unavailable for the stated artifact reason.
- Frozen/fresh structural MCV trace changes: 0; FD trace changes: 37.

## Required final verdict

1. **Were exactly 11 MCV and 12 FD objects deployed?** Yes.
2. **Did physical OID/creation order match the frozen design?** Yes.
3. **Was exactly one fresh ANALYZE executed?** Yes.
4. **What ANALYZE latency did the DMV cost model predict?** 0.238645841 seconds.
5. **What latency was observed?** 0.303734822 seconds.
6. **What was the prediction error?** 0.065088981 seconds (21.4295%).
7. **How many deployed MCV payloads materialized?** 11/11.
8. **How many deployed FD payloads materialized?** 11/12.
9. **What was the frozen optimization loss?** 7.83651388676e+298.
10. **What was the fresh replay loss?** 9.96836642987e+298.
11. **What was the fresh native PostgreSQL loss?** 9.96836642987e+298.
12. **What was the frozen-to-fresh payload-realization drift?** Aggregate change 2.1318525431e+298; per-query drift distribution is unavailable because the frozen specialization was not preserved.
13. **How many fresh replay/native comparisons were performed?** 1,965.
14. **How many passed strict tolerance?** 1,965/1,965.
15. **What was the maximum relative semantic replay error?** 2.43422e-14.
16. **How many queries changed MCV control trace?** 0.
17. **How many changed FD control trace?** 37.
18. **How many selected MCV objects were consumed after deployment?** 11/11.
19. **How many selected FD objects were consumed after deployment?** 11/12.
20. **How many fresh queries consumed at least one FD?** 389.
21. **Did the optimized MCV/FD compositional behavior survive physical deployment?** Yes.
22. **Which two queries have zero truth?** dmv.173, dmv.943.
23. **How much of the original aggregate objective is contributed by those two queries?** Fresh replay 9.96836642987e+298; frozen contribution unavailable because the required frozen per-query numbers were not preserved.
24. **What is the frozen nonzero-truth diagnostic loss?** Unavailable for the documented artifact reason.
25. **What is the fresh nonzero-truth diagnostic loss?** 85014.8083461.
26. **What is the multiplicative estimate-drift distribution?** Unavailable because exact frozen per-query estimates were not preserved.
27. **Is the fresh deployment discrepancy attributable to payload realization rather than semantic replay error?** Fresh replay/native semantic error is bounded by 2.43422e-14; aggregate frozen/fresh change is payload/context drift, but its query-level distribution cannot be reconstructed.
28. **Did any correctness issue require changing the frozen design?** No; the design was unchanged.
29. **Does this experiment close the complete DMV fixed-workload physical-design loop?** No: physical deployment and fresh semantic validation succeed, but the required frozen numerical drift audit is incomplete.

## Final gate

DEPLOYMENT/CORRECTNESS BLOCKER
