# DMV-Analyze-Cost-Model-v0

## Measurement and interpretation

This experiment measures recurring PostgreSQL 16.14 statistics collection/refresh work: aggregate wall-clock latency of `ANALYZE dmv`. It does not measure synchronous DML cost, one-time candidate acquisition, catalog bytes, or optimizer runtime. A disposable 11,591,877-row DMV database, target 100, 36 pair-MCV and 34 usable pair-FD definitions were used.

We measured 35 deterministic configurations spanning empty, full mechanism-specific ranges, same-count subset variants, and eight mixed designs. Every configuration used one unmeasured warm-up followed by 7 measured complete `ANALYZE` executions; object creation was outside the timed interval. Total measured executions: 245.

## Timing noise and models

- Empty mean: 0.114857189 s.
- Median/max within-configuration CV: 2.3396% / 25.6450%.
- Same-count between-subset median/max CV: 4.4147% / 7.1575%; maximum relative range 13.9812%.
- The maximum CV is caused by one preserved `fd_04_s0` timing of 0.284 s after six timings between 0.158 and 0.171 s. It was not deleted or winsorized; the remaining configurations have maximum CV 6.1782%, so this isolated timing event does not make the aggregate slopes indistinguishable.
- MCV-only slope: 4.101326 ms/object; R² 0.957253; RMSE 8.862768 ms.
- FD-only slope: 5.759152 ms/object; R² 0.954445; RMSE 12.562738 ms.
- Combined: intercept 0.124815397 s, MCV 3.903845 ms/object, FD 5.907345 ms/object; R² 0.974868; RMSE 12.605940 ms.
- Uniform-count RMSE 22.844577 ms versus mechanism-aware 12.605940 ms; relative improvement 44.8187%.

The mixed residuals have mixed signs, mean 1.596061 ms, maximum absolute 29.026584 ms, and maximum relative error 12.3645%. Strong invalidating interaction: **no**.

The DMV-specific normalized proxy is `C_maint(Y) = |Y_MCV| + 1.51321194083715|Y_FD|`. These are aggregate first-order prices in this environment, not per-candidate latency claims and not the Census coefficient.

## Required final verdict

1. **How many configurations were measured?** 35.
2. **How many total measured `ANALYZE` executions were performed?** 245.
3. **What was the empty-design mean `ANALYZE` latency?** 0.114857189 seconds.
4. **What was the median within-configuration timing CV?** 2.3396%.
5. **What was the maximum within-configuration timing CV?** 25.6450%.
6. **What was the same-count different-subset variability?** Median between-subset CV 4.4147%, maximum 7.1575%, maximum relative range 13.9812%.
7. **What is the fitted MCV slope?** MCV-only 4.101326 ms/object; combined-model coefficient 3.903845 ms/object.
8. **What is the fitted FD slope?** FD-only 5.759152 ms/object; combined-model coefficient 5.907345 ms/object.
9. **What is the MCV-only linear fit quality?** R² 0.957253, RMSE 8.862768 ms; intercept 0.120552040 s versus empty 0.114857189 s.
10. **What is the FD-only linear fit quality?** R² 0.954445, RMSE 12.562738 ms; intercept 0.126547084 s versus empty 0.114857189 s.
11. **What are the coefficients of the combined mechanism-aware model?** Intercept 0.124815397 s; MCV 3.903845 ms/object; FD 5.907345 ms/object.
12. **What is its fit quality?** R² 0.974868, RMSE 12.605940 ms, max absolute error 31.500749 ms, max relative error 17.5057%.
13. **How does it compare with the uniform-count model?** Uniform RMSE 22.844577 ms; mechanism-aware RMSE 12.605940 ms; relative improvement 44.8187%.
14. **What is the normalized DMV FD/MCV maintenance-cost ratio?** 1.51321194083715.
15. **How accurately does the model predict the full-MCV configuration?** Observed 0.277433274 s, predicted 0.265353829 s, relative error 4.3540%.
16. **How accurately does it predict the full-FD configuration?** Observed 0.332540752 s, predicted 0.325665140 s, relative error 2.0676%.
17. **How accurately does it predict the full-MCV+FD configuration?** Observed 0.449511746 s, predicted 0.466203573 s, relative error 3.7133%.
18. **Is there evidence of strong MCV/FD cost interaction that invalidates the additive model?** No.
19. **Does the first-order mechanism-weighted maintenance model appear adequate for the next DMV optimization experiment?** Yes.
20. **Are the DMV coefficients materially different from the Census coefficients?** Yes; DMV was independently fitted and no Census coefficient constrained it.

## Final gate

READY FOR DMV MAINTENANCE OPTIMIZATION
