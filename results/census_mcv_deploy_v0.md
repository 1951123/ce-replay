# MCV-Deploy-v0

The final joint design was physically deployed in its optimized precedence,
`ANALYZE` was run again, and all 468 Census queries were re-specialized.

| quantity | value |
|---|---:|
| selected MCV statistics | 209 |
| frozen-payload predicted loss | 795.5116302533107 |
| new-payload external replay loss | 813.8024070230607 |
| fresh native PostgreSQL loss | 813.8024070230607 |
| sampling drift | +18.2907767697500 (+2.2992%) |
| native/replay matches at 1e-12 | 468 / 468 |
| maximum relative semantic error | 5.64e-15 |

The deployment closed loop therefore separates the two effects cleanly:
external replay still implements native MCV semantics to floating-point
precision, while rebuilding the payload changes the objective by about 2.30%.
Across queries, the new/frozen estimate drift factor has median 1.00570, p90
1.02785, p99 1.19061, and maximum 1.88233. Q-error improved for 228 queries
and worsened for 240.

Machine-readable results are in `census_mcv_deploy_v0.json`; the executable
experiment is `tools/mcv_deploy_v0.py`.

