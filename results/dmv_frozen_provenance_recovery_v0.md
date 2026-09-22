# DMV-Frozen-Provenance-Recovery-v0

## Outcome

The original frozen final-design per-query estimate vector was not persisted, and exact numerical replay cannot be reconstructed from the persisted optimization realization. The authoritative JSON retains 36 MCV and 34 FD payloads, the exact 11+12 design, precedence, trajectory, resource values, and aggregate loss, but omits all 1,965 baseline rows, clause selectivities, final estimates, q-errors, and evaluator loss state. The original `dmv_maint_opt_v0` database is absent.

This is **artifact/provenance incompleteness**, not CE-Replay semantic failure. No replacement database, ANALYZE, payload, replay realization, inference, or approximation was used. Consequently `results/dmv_frozen_query_baseline_v0.csv` was not created.

## Evidence inspected

- Authoritative optimization JSON, design JSON, report, and source code, with hashes preserved in the JSON audit.
- Immediate upstream baseline/nonmonotonicity artifacts; rejected because they belong to a different realization.
- Fresh deployment JSON/CSV/report/source; valid for fresh claims but forbidden as frozen numerical input.
- Cost-model and static-fit artifacts; no query CE vector.
- PostgreSQL server log; lifecycle messages only, no client NOTICE estimate stream.
- PostgreSQL catalog; no DMV database remains.
- `/tmp`, workspace hidden/temporary/cache/manifest candidates; no serialized process state or replay cache.
- Legacy v2 DMV oracle/postgres/per-lambda directories (1273, 1928, and 1927 JSON files); rejected because they predate this optimization and use a different rounded-estimate pipeline/design provenance.

The deploy comparison CSV has 1,965 rows, but its frozen estimate/q-error columns are empty, exactly as documented by `DMV-Deploy-v0`.

## Claims that remain independently supported

All requested fresh-side claims remain supported: exact 11+12 deployment and OID order; one ANALYZE; 11/11 MCV materialized and consumed; 11/12 FD materialized and all 11 materialized FD consumed; 389 FD-consuming queries; 1,965/1,965 replay/native matches; maximum relative semantic error 2.43422e-14; identical fresh replay/native aggregate loss; fresh nonzero-truth loss 85014.8083461; and physical survival of useful MCV+FD composition.

Structural paired control evidence also remains valid: 0 MCV trace changes and 37 FD trace changes. Those traces are deterministically recoverable from persisted clauses, selected identities, payload availability/degrees, and precedence; unlike numerical estimates, their decisions do not require the missing baseline/simple-selectivity values.

The deployment ANALYZE prediction/observation remains 0.238645841 / 0.303734822 seconds (21.4295% error). It supports only a first-order resource proxy interpretation; no model was refitted.

## Required final verdict

1. **Was the original frozen final-design per-query estimate vector persisted anywhere?** No.
2. **If not directly persisted, were all original-realization numerical inputs required for exact deterministic reconstruction persisted?** No; original baseline rows and clause-level simple selectivities are missing.
3. **Can all 1,965 frozen estimates be recovered with unambiguous provenance?** No.
4. **Does the recovered query-level objective reproduce the stored frozen aggregate loss?** Not testable because no valid recovered vector exists.
5. **Which two queries have zero truth?** `dmv.173` and `dmv.943`.
6. **What were their frozen and fresh objective contributions?** Frozen unavailable; fresh contribution 9.96836642987e+298.
7. **What is the frozen nonzero-truth diagnostic loss?** Unavailable.
8. **What is the fresh nonzero-truth diagnostic loss?** 85014.8083461.
9. **What is the paired frozen-to-fresh estimate-drift distribution?** Unavailable.
10. **How many paired MCV control traces changed?** 0.
11. **How many paired FD control traces changed?** 37.
12. **Which `DMV-Deploy-v0` claims remain independently supported even if recovery fails?** Exact deployment/order, one ANALYZE, fresh payload materialization and consumption, 389 FD-consuming queries, 1,965/1,965 semantic matches and recorded maximum error, fresh replay/native loss equality, fresh nonzero-truth loss, and physical MCV+FD composition.
13. **Is the remaining issue semantic correctness or artifact/provenance completeness?** Artifact/provenance completeness; fresh semantic correctness remains supported.

## Final gate

FROZEN BASELINE UNRECOVERABLE
