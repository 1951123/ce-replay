# DMV-Analyze-Cost-Model-v0

## Measurement and interpretation

This experiment measures recurring PostgreSQL 16.14 statistics collection/refresh work: aggregate wall-clock latency of `ANALYZE dmv`. It does not measure synchronous DML cost, one-time candidate acquisition, catalog bytes, or optimizer runtime. A disposable 11,591,877-row DMV database, target 100, 36 pair-MCV and 35 usable pair-FD definitions were used.

We measured 35 deterministic configurations spanning empty, full mechanism-specific ranges, same-count subset variants, and eight mixed designs. Every configuration used one unmeasured warm-up followed by 7 measured complete `ANALYZE` executions; object creation was outside the timed interval. Total measured executions: 245.

## Timing noise and models

- Empty mean: 0.121401821 s.
- Median/max within-configuration CV: 2.4609% / 14.7147%.
- Same-count between-subset median/max CV: 2.6699% / 17.4906%; maximum relative range 33.5984%.
- MCV-only slope: 4.337502 ms/object; R² 0.963752; RMSE 8.602112 ms.
- FD-only slope: 5.580522 ms/object; R² 0.907071; RMSE 18.045574 ms.
- Combined: intercept 0.131583019 s, MCV 4.036684 ms/object, FD 6.103953 ms/object; R² 0.968437; RMSE 14.776539 ms.
- Uniform-count RMSE 24.635400 ms versus mechanism-aware 14.776539 ms; relative improvement 40.0191%.

The mixed residuals have mixed signs, mean 2.083501 ms, maximum absolute 26.824737 ms, and maximum relative error 10.0412%. Strong invalidating interaction: **no**.

The DMV-specific normalized proxy is undefined because the stability gate failed. These are aggregate first-order prices in this environment, not per-candidate latency claims and not the Census coefficient.

## Required final verdict

1. **How many configurations were measured?** 35.
2. **How many total measured `ANALYZE` executions were performed?** 245.
3. **What was the empty-design mean `ANALYZE` latency?** 0.121401821 seconds.
4. **What was the median within-configuration timing CV?** 2.4609%.
5. **What was the maximum within-configuration timing CV?** 14.7147%.
6. **What was the same-count different-subset variability?** Median between-subset CV 2.6699%, maximum 17.4906%, maximum relative range 33.5984%.
7. **What is the fitted MCV slope?** MCV-only 4.337502 ms/object; combined-model coefficient 4.036684 ms/object.
8. **What is the fitted FD slope?** FD-only 5.580522 ms/object; combined-model coefficient 6.103953 ms/object.
9. **What is the MCV-only linear fit quality?** R² 0.963752, RMSE 8.602112 ms; intercept 0.124252637 s versus empty 0.121401821 s.
10. **What is the FD-only linear fit quality?** R² 0.907071, RMSE 18.045574 ms; intercept 0.140965239 s versus empty 0.121401821 s.
11. **What are the coefficients of the combined mechanism-aware model?** Intercept 0.131583019 s; MCV 4.036684 ms/object; FD 6.103953 ms/object.
12. **What is its fit quality?** R² 0.968437, RMSE 14.776539 ms, max absolute error 53.802995 ms, max relative error 20.8028%.
13. **How does it compare with the uniform-count model?** Uniform RMSE 24.635400 ms; mechanism-aware RMSE 14.776539 ms; relative improvement 40.0191%.
14. **What is the normalized DMV FD/MCV maintenance-cost ratio?** Undefined.
15. **How accurately does the model predict the full-MCV configuration?** Observed 0.292341666 s, predicted 0.276903631 s, relative error 5.2808%.
16. **How accurately does it predict the full-FD configuration?** Observed 0.338638589 s, predicted 0.345221374 s, relative error 1.9439%.
17. **How accurately does it predict the full-MCV+FD configuration?** Observed 0.491655325 s, predicted 0.490541986 s, relative error 0.2264%.
18. **Is there evidence of strong MCV/FD cost interaction that invalidates the additive model?** No.
19. **Does the first-order mechanism-weighted maintenance model appear adequate for the next DMV optimization experiment?** No.
20. **Are the DMV coefficients materially different from the Census coefficients?** Yes; DMV was independently fitted and no Census coefficient constrained it.

## Final gate

COST MODEL BLOCKER
