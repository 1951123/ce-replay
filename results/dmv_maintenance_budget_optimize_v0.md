# DMV-Maintenance-Budget-Optimize-v0

## Frozen instance and scope

The previous DMV artifact preserved extended-stat payloads and query baselines but not clause-level simple selectivities, while its isolated database had been removed. Exact reconstruction was therefore impossible. This experiment created one new internally consistent target-100 realization and recomputed every payload-dependent baseline, singleton, fidelity, and optimization quantity. No value from the old realization is mixed into the objective. Native/replay fidelity passed 21,615/21,615 comparisons with maximum relative error 4.86e-14.

FD payload availability changed with the required new sample: the prior unavailable pair `county:record_type` remains unavailable, while `county:fuel_type` replaces `revocation_indicator:suspension_indicator` as the second unavailable FD. The current instance still has exactly 34 usable FD candidates; no missing payload was synthesized, and only current usable candidates were optimized.

The usable universe is 36 pair MCV plus 34 pair FD candidates under fixed lexicographic pair/OID precedence. The full normalized maintenance cost is 87.449205988463092; the primary 50% budget is 43.724602994231546. Normalized units represent proportional recurring ANALYZE refresh capacity, not milliseconds.

## Budget curve

- 25%: budget 21.862301497115773, MCV 11, FD 7, cost 21.592483585860052, remaining 0.269817911255721, loss 7.83651388676e+298.
- 50%: budget 43.724602994231546, MCV 11, FD 12, cost 29.158543290045799, remaining 14.566059704185747, loss 7.83651388676e+298.
- 75%: budget 65.586904491347326, MCV 11, FD 12, cost 29.158543290045799, remaining 36.428361201301527, loss 7.83651388676e+298.
- 100%: budget 87.449205988463092, MCV 11, FD 12, cost 29.158543290045799, remaining 58.290662698417293, loss 7.83651388676e+298.

At 50%, empty loss is 7.84003745648e+298, all-MCV 7.91074972338e+298, all-FD 7.99346220399e+298, all mixed 7.91074972338e+298, singleton ranking 7.8391182656e+298, marginal greedy 7.83651388676e+298, and final local search 7.83651388676e+298. Random feasible loss across 30 fixed seeds has mean/median/min/max 7.95631215219e+298 / 7.93268316474e+298 / 7.83782262882e+298 / 8.28989128064e+298.

The canonical workload contains two zero-truth queries (`dmv.173`, `dmv.943`). Under the unchanged Census-compatible q-error definition, a positive estimate for truth zero is divided by the `1e-300` floor, so aggregate losses are legitimately around `1e298`. All values remain finite; restricted gaps are interpreted with the established relative numerical tolerance.

The primary design selects 11 MCV and 12 FD, consuming 11 and 12; selected-but-never-consumed counts are 0 and 0. 417 queries consume FD, unlike the all-statistics design where FD was fully suppressed. The complete terminal neighborhood contains 47 ADD, 23 DROP, and 1081 SWAP moves; best delta 0.

Incremental evaluation affected a candidate-degree mean/median/p90/max of 497.13 / 498.00 / 520.00 / 546 queries. It avoided 67.91% of full-workload query replay operations. DMV is far denser than Census, so the saving is weaker but remains material.

Restricted exhaustive audits recovered 4/4 exact optima at the established `1e-12` relative numerical tolerance; largest relative gap was 1.18557e-16. The nonzero absolute gaps are one-ULP-scale effects of the approximately 7.84e298 zero-truth-dominated objective. These audits do not establish global optimality for the 70-candidate instance.

## Required final verdict

1. **What is the normalized maintenance cost of the complete usable DMV candidate universe?** 87.449205988463092.
2. **What exact budgets correspond to 25%, 50%, 75%, and 100%?** 25%=21.862301497115773, 50%=43.724602994231546, 75%=65.586904491347326, 100%=87.449205988463092.
3. **What is the primary 50% budget?** 43.724602994231546.
4. **What is the empty-design loss?** 7.84003745648e+298.
5. **What is the all-statistics loss?** 7.91074972338e+298.
6. **What is the random-feasible baseline distribution at the primary budget?** n=30; mean 7.95631215219e+298, median 7.93268316474e+298, min 7.83782262882e+298, max 8.28989128064e+298.
7. **What is the singleton-ranking loss?** 7.8391182656e+298.
8. **What is the marginal-greedy loss?** 7.83651388676e+298.
9. **What is the final ADD/DROP/SWAP local-search loss?** 7.83651388676e+298.
10. **How many MCV and FD candidates are selected in the final primary design?** 11 MCV and 12 FD.
11. **What is its exact modeled maintenance cost?** 29.158543290045799.
12. **How much budget remains?** 14.566059704185747.
13. **How many selected MCV and FD candidates are actually consumed?** 11 MCV and 12 FD.
14. **Are any selected candidates never consumed?** No; MCV 0, FD 0.
15. **Does the optimized design allow FD consumption that was completely suppressed in the all-statistics design?** Yes; 417 queries consume FD.
16. **How many accepted local-search moves occurred after marginal greedy?** 0.
17. **What is the complete terminal-neighborhood best move delta?** 0.
18. **Is the final primary design a local optimum under ADD/DROP/SWAP?** Yes.
19. **How do the 25%, 50%, 75%, and 100% budget solutions compare?** See the exact budget curve above.
20. **Does target-workload loss decrease monotonically with resource budget for the optimized solutions?** Yes.
21. **How many restricted exhaustive audits were performed?** 4.
22. **How often did the production optimizer recover the restricted exact optimum?** 4/4 at the established `1e-12` relative numerical tolerance.
23. **What were the largest restricted optimality gaps?** Maximum absolute 9.29385567799e+282; maximum relative 1.18557e-16.
24. **How many queries does a typical DMV candidate/move affect during optimization?** Candidate degree mean 497.13, median 498.00, p90 520.00, max 546.
25. **How does this compare qualitatively with Census locality?** DMV is much denser: moves affect hundreds rather than a small local neighborhood.
26. **What fraction of move evaluations avoid full-workload control replay?** 67.91% of query replay operations are avoided.
27. **Does semantic incremental evaluation remain useful on this dense workload?** Yes; the advantage is weaker than Census.
28. **Are harmful singleton candidates ever selected because of contextual interactions?** Yes; 11 have direct beneficial removal-marginal evidence in the final context.
29. **Are beneficial singleton candidates omitted because of contextual interactions or maintenance price?** Yes; 4 are omitted (the experiment does not assign a unique cause without a counterfactual path).
30. **Does the optimized subset outperform empty statistics?** Yes.
31. **Does it outperform all-statistics?** Yes.
32. **Are there any correctness blockers before physical deployment?** No.

## Final gate

READY FOR DMV DEPLOYMENT
