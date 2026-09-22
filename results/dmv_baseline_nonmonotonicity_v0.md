# DMV-Baseline-and-Nonmonotonicity-v0

## Scope and correctness gate

The isolated DMV table contains 11,591,877 rows, 11 text columns, and the complete 1,965-query truth-bearing workload. Exactly 36 workload-generated pairs produced 72 mechanism-specific candidates. Candidate payloads came from one target-100 ANALYZE realization; this is offline acquisition, not a recurring maintenance-cost measurement. All 36 MCV payloads and 34/36 FD payloads were usable; `fd:county:record_type` and `fd:revocation_indicator:suspension_indicator` had no dependency payload and were retained explicitly as unusable candidates.

The fixed precedence is lexicographic workload-pair order within each mechanism, materialized as creation/OID order. It was not optimized. In the all-statistics design, pair MCV GreedyCover consumes every usable pair opportunity before the FD stage, explaining why all 36 MCV candidates but none of the 34 available FD candidates are consumed there.

Native PostgreSQL pre-clamp rows and external frozen-payload replay matched in 27,510/27,510 real query/design comparisons at tolerance 1e-12. Maximum relative error was 1.40286e-14; maximum absolute error was 9.31323e-09.

## Objective and inclusion results

| Design | Workload loss |
|---|---:|
| Empty | 87276.581132002626 |
| All MCV | 92850.151303207211 |
| All FD | 95404.855145577036 |
| All MCV+FD | 92850.151303207211 |

| Context / mechanism | Beneficial | Neutral | Harmful |
|---|---:|---:|---:|
| Singleton / MCV | 19 | 0 | 17 |
| Singleton / FD | 6 | 0 | 28 |
| Singleton / all | 25 | 0 | 45 |
| Remove from all / MCV | 17 | 0 | 19 |
| Remove from all / FD | 0 | 34 | 0 |

Here a beneficial leave-one-out row means removal lowers loss. The strongest harmful singleton is `fd:body_type:record_type` with delta 73068.924878719190. Query `dmv.1037` consumes dependency `body_type => record_type` with degree 0.9136333333333333: its estimate moves from 336394.1327826705 to 763498.5951691011 while truth is 6, increasing q-error by 71184.07706440511. This is an FD consumption/control effect, not rounding noise. The strongest improving removal is `mcv:body_type:fuel_type` with delta -50810.315415170611.

All-statistics consumption: MCV 36/36; FD 0/34. Selected, consumed, and beneficial remain distinct properties.

Within PostgreSQL 16.14, the DMV target workload, the evaluated pair-MCV+FD candidate universe, frozen payload realization, and fixed precedence, the workload CE objective is empirically non-monotone in statistics-set inclusion. Thus the qualitative Census motivation for subset selection replicates; no claim of universal PostgreSQL non-monotonicity is made.

## Required final verdict

1. **Was the expected 36-pair / 72-mechanism candidate universe obtained?** Yes: 36 pairs and 72 candidates.
2. **How many MCV and FD payloads were usable?** 36 MCV and 34 FD.
3. **What was the empty-design workload loss?** 87276.581132002626.
4. **How many real-DMV native/replay comparisons were performed?** 27,510.
5. **How many matched within strict tolerance?** 27,510/27,510.
6. **What was the maximum relative semantic replay error?** 1.40286e-14.
7. **Among singleton additions from empty, how many were beneficial, neutral, and harmful?** 25, 0, and 45.
8. **What is the MCV/FD breakdown?** MCV 19/0/17; FD 6/0/28 (beneficial/neutral/harmful).
9. **What was the strongest harmful singleton and why was it harmful?** `fd:body_type:record_type`, delta 73068.924878719190. On `dmv.1037`, consuming `body_type => record_type` changes the estimate from 336394.1327826705 to 763498.5951691011 for truth 6, increasing q-error by 71184.07706440511; this is an FD consumption/control effect, not rounding noise.
10. **What was the all-MCV loss?** 92850.151303207211.
11. **What was the all-FD loss?** 95404.855145577036.
12. **What was the all-MCV+FD loss?** 92850.151303207211.
13. **How many leave-one-out removals from all-statistics improved the objective?** 17.
14. **What was the strongest improving removal?** `mcv:body_type:fuel_type`, delta -50810.315415170611.
15. **How many MCV and FD candidates were actually consumed in the all-statistics design?** 36 MCV and 0 FD.
16. **Does DMV provide an empirical non-monotonicity witness?** Yes.
17. **Does the qualitative Census motivation for statistics selection replicate on DMV?** Yes.
18. **Is CE-Replay semantically faithful on the real IN-heavy DMV workload?** Yes, over all 27,510 tested query/design comparisons at the established tolerance.
19. **Are there any correctness blockers before measuring DMV ANALYZE maintenance cost?** No.

## Final gate

READY FOR DMV COST MODEL
