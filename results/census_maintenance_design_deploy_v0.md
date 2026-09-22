# Maintenance-Design-Deploy-v0

## Scope and physical realization

The locally optimized maintenance-budget design was deployed once in an isolated PostgreSQL 16.14 Census database: **276 MCV + 7 FD** objects. Creation followed frozen MCV and FD `oid_rank`; actual catalog order was verified. Exactly one fresh `ANALYZE` was run. The isolated database was deleted afterward, and the source catalog was verified unchanged at 205 MCV + 56 FD.

## ANALYZE maintenance-cost sanity check

| Metric | Seconds |
|---|---:|
| Predicted by existing mechanism-specific linear model | 0.773682 |
| Observed fresh ANALYZE | 0.829417 |
| Absolute error | 0.055735 |
| Relative error | 7.20% |

This is one aggregate sanity check, not a refit or an independent cost-model study.

## Payload materialization

- MCV payloads materialized: 276/276.
- FD payloads materialized: 7/7.
- Unavailable FD IDs: `[]`.
- Fresh serialized sizes: MCV 150,962 bytes; FD 203 bytes; total 151,165 bytes.

## Three-way loss distinction

| Quantity | Workload loss |
|---|---:|
| Frozen optimization prediction | 787.809381279634 |
| Fresh replay | 811.553725117865 |
| Fresh native PostgreSQL | 811.553725117865 |

Frozen→fresh payload-realization drift is 23.744343838231 (3.0140%). Fresh native minus fresh replay semantic error is 0.

Fresh replay matched 468/468 native estimates within 1e-12; maximum relative error is 6.92e-16, median 1.28e-16, and 203/468 raw-row estimates are bitwise equal.

## Consumption audit

- MCV consumed by at least one query: 276/276.
- FD consumed under frozen/fresh payloads: 7/7 and 7/7.
- Fresh never-consumed FD IDs: `[]`.
- Queries whose FD trace changed from frozen to fresh: 0 (`[]`).
- FD availability changed: no.

## Previous deployment context

| Design | MCV | FD | Frozen loss | Fresh replay/native loss | Payload drift |
|---|---:|---:|---:|---:|---:|
| Previous byte-budget deployment | 205 | 56 | 805.316472 | 819.191023 | 13.874551 (1.7229%) |
| New maintenance-budget deployment | 276 | 7 | 787.809381 | 811.553725 | 23.744344 (3.0140%) |

The new single fresh loss is lower than the previous recorded realization, but these are different `ANALYZE` realizations and are not a controlled paired comparison.

## Required verdict

1. **Was the 276-MCV + 7-FD design physically deployed successfully?** Yes; catalog counts and fixed creation/OID order were verified in the isolated database.
2. **What was the observed ANALYZE latency?** 0.829417 seconds.
3. **What latency did the linear maintenance-cost model predict?** 0.773682 seconds.
4. **What was the prediction error?** Observed minus predicted 0.055735 seconds; absolute 0.055735 seconds (7.20%).
5. **What was the frozen predicted workload loss?** 787.809381279634.
6. **What was the fresh replay workload loss?** 811.553725117865.
7. **What was the frozen-to-fresh payload-realization drift?** 23.744343838231 (3.0140%).
8. **What was the fresh native PostgreSQL workload loss?** 811.553725117865.
9. **How closely did fresh CE-Replay match native PostgreSQL?** 468/468 within 1e-12; max relative error 6.92e-16; semantic loss error 0.
10. **How many selected MCV statistics were actually consumed?** 276/276.
11. **How many selected FD statistics were actually consumed?** 7/7.
12. **Did fresh ANALYZE change any relevant FD availability/control paths?** No; unavailable FD IDs `[]`, changed FD-trace queries 0.
13. **Does the deployment validate the new maintenance-budget physical-design loop?** Yes: the exact selected design was realized, fresh payload replayed, and fresh replay remained semantically faithful to native PostgreSQL within the validated fragment.
14. **What limitations remain?** One PostgreSQL 16.14 Census deployment and one fresh `ANALYZE`; environment-specific maintenance coefficients; base-restriction pair-MCV/equality-FD fragment; fixed precedence; payload drift; local rather than global optimality; and no robustness or paired superiority claim.
