# Mixed-Deploy-v0

| Metric | Value |
|---|---:|
| selected MCV | 205 |
| selected FD | 56 |
| frozen loss | 805.316471766631 |
| fresh replay loss | 819.191022950055 |
| fresh native PG loss | 819.191022950055 |
| payload drift | 13.874551183424 |
| payload drift percent | 1.7229% |
| semantic error | 0 |
| max per-query semantic relative error | 8.05e-16 |
| queries within 1e-12 | 468 / 468 |
| frozen storage | 105,060 bytes |
| fresh storage | 104,958 bytes |
| selected FD consumed after deployment | 54 / 56 |

## Correctness layers

| Layer | Queries checked | Exact/tolerance matches | Max error |
|---|---:|---:|---:|
| MCV trace | 468 | 468 | 0 |
| estimatedclauses | 0 | — | not emitted by native instrumentation |
| FD trace identity | 0 | — | native CHOOSE lacks source-statistic identity |
| raw selectivity | 468 | 468 | 8.25e-16 |
| raw rows | 468 | 468 | 8.05e-16 |

The deployed OID order matches the frozen intra-mechanism policy. The report
does not claim completeness for intermediate layers absent from instrumentation.
Payload drift and semantic replay error are kept separate.

This final artifact comes from a clean cluster and exactly one post-deployment
`ANALYZE`. PostgreSQL reported `reltuples = 2,458,452`; all replay base context,
MCV payloads, FD payloads and native estimates were taken from that snapshot.

## Payload and consumption diagnostics

- All 205 MCV objects produced fresh payloads; 72 changed payload size.
- FD 97 and FD 683 produced no dependency payload after fresh ANALYZE. These
  are exactly the two selected FD objects that became never-consumed.
- 55 of 56 FD payloads changed dependency availability or degree relative to
  the frozen snapshot.
- FD consumption changed only for queries 303 and 353: query 303 lost FD 683,
  and query 353 lost FD 97.
- Frozen-to-fresh estimate-factor drift was 1.0094 median, 1.0344 p90,
  1.0566 p95, 1.1863 p99 and 1.6705 maximum.
- The largest estimate drift was query 465: 925.58 frozen rows versus 1,546.22
  fresh rows. This is deployment/payload drift, not semantic replay error.

## Final verdict

1. **Yes.** The selected mixed design and intended fixed intra-mechanism order were physically realized.
2. **Yes.** Fresh replay matches all 468 native raw-row estimates within 1e-12: 468/468.
3. Maximum per-query semantic relative error is `8.05e-16`.
4. Fresh native minus fresh replay workload loss is `0`.
5. Frozen-to-fresh deployment drift is `13.874551183424` (`1.7229%`).
6. MCV→FD consumption changed on 2 queries relative to the frozen realization; fresh external replay remains the semantic reference for the same snapshot.
7. Selected FD objects never consumed after deployment: `2`.
8. Payload storage changed by `-102` bytes (105,060 → 104,958).
9. The dominant uncertainty is **payload realization**.
10. **Yes.** This closes the physical loop for the supported PostgreSQL 16 base-restriction MCV+FD fragment only.
