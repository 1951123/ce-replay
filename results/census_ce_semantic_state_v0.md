# CE-Semantic-State-v0

## 1. Source-derived state model

PostgreSQL 16.14 preprocesses compatible clauses into `list_attnums`/`list_exprs`, then repeatedly calls `choose_best_statistics`. It maximizes the number of still-unestimated covered attributes, minimizes total statistic keys, and retains the first exact tie in the statistics list. `RelationGetStatExtList` sorts that list by OID. For the present pair-MCV universe, all eligible objects cover two attributes and have two keys, so the exact tie-break is fixed ascending OID precedence. After a winner, its covered clauses are marked in `estimatedclauses` and the corresponding list entries are nulled.

| state/input item | workload-fixed? | candidate-fixed? | design-dependent? | mutable? | future control flow? | numerical only? |
|---|---|---|---|---|---|---|
| compatible clause representation | yes | no | no | no | yes, through coverage | no |
| `estimatedclauses` / remaining clauses | initial only | no | yes | yes | yes | no |
| `list_attnums`, `list_exprs` | derived initially | no | yes through nulling | yes | yes | no |
| selected statistics availability | no | no | yes | no within one replay | yes | no |
| statistics-list/OID order | no | yes | precedence is fixed here | no | yes | no |
| MCV payload | no | yes | selected payloads used | no | no | yes |
| simple selectivity inputs | yes per query/stat group | yes per group | no | no | no | yes |
| accumulated MCV selectivity/rows | baseline fixed | contributions fixed | yes | yes | no for winner choice | yes |

Thus remaining clauses are a sufficient projected control state for continuing an already started fixed-design execution when candidate availability is held fixed. They are not by themselves sufficient for arbitrary physical-design extension followed by replay from the initial state. No minimality claim is made.

## 2. Experimental scope

Census, PostgreSQL 16.14, MCV only, frozen pair-MCV payloads, original OID precedence, 468 queries. All 229 queries with at most 15 relevant candidates were exhaustively enumerated (2,395,773 subsets). The remaining 239 queries used exactly 4,096 deterministic samples each (978,944 evaluations); these results are not labeled exhaustive.

No PostgreSQL execution, fresh ANALYZE, FD, deployment, join, order optimization, or global physical-design optimization was performed.

## 3. Canonical-state definitions

- **Projected control state:** final remaining compatible columns; numerical output excluded.
- **Strict trace:** every round's remaining state, complete applicable-statistics set, winner,   OID rank, consumed columns, next state, and exact hexadecimal contribution.
- **Numerical equivalence:** raw replay rows within relative tolerance `1e-12`.
- **Projected full semantic state:** `(remaining columns, exact IEEE-754 row accumulator)`;   this is conservative for current output but was tested rather than assumed safe for extensions.
- **Conservative merge-safe state:** projected full state plus the selected physical subset.   It is sufficient for arbitrary extension but intentionally gives no subset compression.

## 4. Soundness methodology

Every subset was evaluated by direct frozen CE-Replay-v1 semantics. Distinct subsets sharing a projected full state were paired; common additions were exhaustively enumerated when at most 10 candidates remained, otherwise 256 deterministic continuations were sampled. Each union was replayed from the initial state and final control/numerical results compared.

Projected-state counterexamples occurred in **182/229** exhaustive-query domains; **111** already have fully exhaustive continuation checks. Therefore the projected state is rejected as merge-safe for arbitrary design extension. Counterexamples are stored verbatim in the JSON. The only claimed arbitrary-extension-safe key includes the subset, so it has no distinct-history merges and zero claimed divergences.

A representative exhaustive counterexample is query.4: masks 2 and 10 initially have the same projected full state, but adding mask 1 yields winner traces `[230]` and `[230,448]` and different exact row estimates. The extra previously unconsumed selected candidate becomes relevant after the new candidate changes the greedy matching.

## 5. Exhaustive coverage and state-space compression

Across exhaustive queries, strict traces equal physical subsets exactly: the first round's recorded applicable set exposes the selected subset. Projecting to control or current output compresses substantially, but those projected merges are not generally extension-safe.

| ratio over exhaustive queries | min | median | mean | p90 | p95 | max |
|---|---:|---:|---:|---:|---:|---:|
| subsets / control states | 1.000 | 64.000 | 337.559 | 1024.000 | 1024.000 | 1024.000 |
| subsets / projected full states | 1.000 | 39.385 | 146.977 | 431.158 | 431.158 | 461.521 |

## 6. Equivalence-class comparison

The 229 exhaustive queries contain 2,395,773 physical subsets, 3,865 per-query control states, 2,395,773 strict traces, 7,234 numerical classes, and 7,711 projected full states. Control-equivalent configurations frequently differ numerically; exact current-output equivalence in turn does not imply equal response to future candidate additions.

## 7. Commutativity

Across all realized remaining-clause states, 2,831,172 enabled candidate pairs were tested. 1,590,204 (56.17%) were fully semantic-commutative. 1,240,968 (43.83%) were non-commutative because overlapping columns made the second transition inapplicable. Disjointness was confirmed by execution, not assumed as the classification rule; no numerical-order counterexample occurred.

## 8. Semantic dependency versus realized interaction

For all 158 exhaustive queries with at most 10 candidates, 750,414 contextual marginal comparisons were executed. Source-derived nondependency did **not** certify equal q-error marginals: 58,576 nondependent contexts differed. The saved query.4 counterexample uses disjoint candidates `(dincome2,isex)` and `(dincome7,drearning)`. Their CE transitions commute, but q-error is nonlinear in the combined estimate, so `Delta_b(D) != Delta_b(D union {a})`.

This falsifies the implication exactly as phrased for loss marginals. It does not falsify a narrower theorem about control-state independence or multiplicative CE correction factors.

## 9. Counterexamples

Two counterexample families were found and preserved:

1. projected current-state equivalence is unsafe under arbitrary subset additions and restart;
2. semantic nondependency does not imply context-invariant q-error marginal benefit.

No counterexample occurred for the deliberately conservative subset-containing key, and no commutativity counterexample occurred among transitions that remained enabled in both orders.

## 10. Runtime and correctness checks

Runtime: **105.43 seconds**. Direct results: 3,374,717; deterministic duplicate replays: 7,101. The program asserts one result per mask and exactly repeatable canonical trace/IEEE key. Full projected keys cannot merge materially different current outputs by construction. Claimed merge-safe continuation divergences: 0.

## 11. Strict limitations

- Results are query-local and MCV-only under frozen pair payloads and fixed precedence.
- Queries above 15 candidates are sampled; their compression numbers are sample-relative.
- Continuations above 10 free candidates are sampled, so absence of a counterexample there is not proof.
- The conservative safe state obtains safety by retaining the physical subset and therefore does not solve optimization.
- The interaction result uses q-error loss; a semantic-output noninteraction theorem requires a different statement.
- This experiment does not establish a polynomial bound or a global optimizer.

## 12. Conclusions and required questions

1. **Can distinct configurations be safely merged using a future-relevant semantic state?** For continuation of a fixed execution, yes. For arbitrary candidate additions followed by restart, not with the compact `(remaining, accumulator)` state tested here. A conservative state retaining selected-candidate availability is safe but showed no physical-subset compression.

2. **What information is required?** Remaining/estimated compatible clauses, immutable selected statistics availability, fixed OID precedence, and the exact numerical accumulator/payload contributions. Dropping selected-but-currently-unconsumed availability is unsound when design extensions can restart greedy selection.

3. **How much reduction is observed?** Current-state projection is large: median 64x for control and 39.385x for projected full state over exhaustive queries. Strict traces and the currently justified arbitrary-extension-safe state provide 1x reduction.

4. **Does semantic nondependency certify zero realized interaction?** No for the requested q-error marginal definition; 58,576 counterexample contexts were found in the fully exhaustive <=10-candidate domain.

5. **Next justified step?** **Partial-order reduction**, preceded by a precise formal statement of fixed-execution versus restart-under-design-extension semantics. Commutativity is common (56.17%), whereas the compact restart-state DP premise is falsified. A semantic-state DP or decision DAG is not yet justified as the primary representation.

## 13. Per-query headline table

| query | candidates | subsets evaluated | exhaustive? | control states | traces | numerical outcomes | full semantic states | subset/control compression | subset/full compression |
|---|---:|---:|:---:|---:|---:|---:|---:|---:|---:|
| query.1 | 15 | 32768 | yes | 32 | 32768 | 38 | 71 | 1024.000 | 461.521 |
| query.2 | 15 | 32768 | yes | 32 | 32768 | 76 | 76 | 1024.000 | 431.158 |
| query.3 | 28 | 4096 | no | 89 | 4096 | 318 | 318 | 46.022 | 12.881 |
| query.4 | 10 | 1024 | yes | 16 | 1024 | 26 | 26 | 64.000 | 39.385 |
| query.5 | 28 | 4096 | no | 90 | 4096 | 318 | 318 | 45.511 | 12.881 |
| query.6 | 21 | 4096 | no | 61 | 4096 | 165 | 165 | 67.148 | 24.824 |
| query.7 | 45 | 4096 | no | 149 | 4096 | 806 | 831 | 27.490 | 4.929 |
| query.8 | 6 | 64 | yes | 8 | 64 | 10 | 10 | 8.000 | 6.400 |
| query.9 | 6 | 64 | yes | 8 | 64 | 10 | 10 | 8.000 | 6.400 |
| query.10 | 45 | 4096 | no | 151 | 4096 | 824 | 824 | 27.126 | 4.971 |
| query.11 | 45 | 4096 | no | 157 | 4096 | 845 | 845 | 26.089 | 4.847 |
| query.12 | 10 | 1024 | yes | 16 | 1024 | 21 | 25 | 64.000 | 40.960 |
| query.13 | 36 | 4096 | no | 116 | 4096 | 527 | 527 | 35.310 | 7.772 |
| query.14 | 3 | 8 | yes | 4 | 8 | 4 | 4 | 2.000 | 2.000 |
| query.15 | 15 | 32768 | yes | 32 | 32768 | 76 | 76 | 1024.000 | 431.158 |
| query.16 | 21 | 4096 | no | 63 | 4096 | 162 | 162 | 65.016 | 25.284 |
| query.17 | 28 | 4096 | no | 92 | 4096 | 322 | 322 | 44.522 | 12.720 |
| query.18 | 15 | 32768 | yes | 32 | 32768 | 76 | 76 | 1024.000 | 431.158 |
| query.19 | 21 | 4096 | no | 61 | 4096 | 107 | 135 | 67.148 | 30.341 |
| query.20 | 15 | 32768 | yes | 32 | 32768 | 76 | 76 | 1024.000 | 431.158 |
| query.21 | 21 | 4096 | no | 61 | 4096 | 163 | 163 | 67.148 | 25.129 |
| query.22 | 28 | 4096 | no | 96 | 4096 | 314 | 314 | 42.667 | 13.045 |
| query.23 | 21 | 4096 | no | 64 | 4096 | 156 | 168 | 64.000 | 24.381 |
| query.24 | 36 | 4096 | no | 121 | 4096 | 520 | 520 | 33.851 | 7.877 |
| query.25 | 15 | 32768 | yes | 32 | 32768 | 66 | 76 | 1024.000 | 431.158 |
| query.26 | 1 | 2 | yes | 2 | 2 | 2 | 2 | 1.000 | 1.000 |
| query.27 | 36 | 4096 | no | 123 | 4096 | 520 | 520 | 33.301 | 7.877 |
| query.28 | 21 | 4096 | no | 62 | 4096 | 114 | 162 | 66.065 | 25.284 |
| query.29 | 15 | 32768 | yes | 32 | 32768 | 76 | 76 | 1024.000 | 431.158 |
| query.30 | 1 | 2 | yes | 2 | 2 | 2 | 2 | 1.000 | 1.000 |
| query.31 | 6 | 64 | yes | 8 | 64 | 10 | 10 | 8.000 | 6.400 |
| query.32 | 21 | 4096 | no | 62 | 4096 | 131 | 171 | 66.065 | 23.953 |
| query.33 | 6 | 64 | yes | 8 | 64 | 10 | 10 | 8.000 | 6.400 |
| query.34 | 28 | 4096 | no | 92 | 4096 | 310 | 310 | 44.522 | 13.213 |
| query.35 | 15 | 32768 | yes | 32 | 32768 | 56 | 76 | 1024.000 | 431.158 |
| query.36 | 21 | 4096 | no | 62 | 4096 | 137 | 162 | 66.065 | 25.284 |
| query.37 | 6 | 64 | yes | 8 | 64 | 9 | 9 | 8.000 | 7.111 |
| query.38 | 15 | 32768 | yes | 32 | 32768 | 76 | 76 | 1024.000 | 431.158 |
| query.39 | 3 | 8 | yes | 4 | 8 | 4 | 4 | 2.000 | 2.000 |
| query.40 | 6 | 64 | yes | 8 | 64 | 6 | 10 | 8.000 | 6.400 |
| query.41 | 15 | 32768 | yes | 32 | 32768 | 66 | 76 | 1024.000 | 431.158 |
| query.42 | 55 | 4096 | no | 183 | 4096 | 1078 | 1158 | 22.383 | 3.537 |
| query.43 | 15 | 32768 | yes | 32 | 32768 | 76 | 76 | 1024.000 | 431.158 |
| query.44 | 15 | 32768 | yes | 32 | 32768 | 56 | 76 | 1024.000 | 431.158 |
| query.45 | 3 | 8 | yes | 4 | 8 | 4 | 4 | 2.000 | 2.000 |
| query.46 | 36 | 4096 | no | 127 | 4096 | 526 | 526 | 32.252 | 7.787 |
| query.47 | 10 | 1024 | yes | 16 | 1024 | 22 | 26 | 64.000 | 39.385 |
| query.48 | 15 | 32768 | yes | 32 | 32768 | 66 | 76 | 1024.000 | 431.158 |
| query.49 | 15 | 32768 | yes | 32 | 32768 | 76 | 76 | 1024.000 | 431.158 |
| query.50 | 45 | 4096 | no | 147 | 4096 | 833 | 833 | 27.864 | 4.917 |
| query.51 | 45 | 4096 | no | 153 | 4096 | 581 | 714 | 26.771 | 5.737 |
| query.52 | 55 | 4096 | no | 187 | 4096 | 1113 | 1195 | 21.904 | 3.428 |
| query.53 | 3 | 8 | yes | 4 | 8 | 4 | 4 | 2.000 | 2.000 |
| query.54 | 21 | 4096 | no | 61 | 4096 | 163 | 163 | 67.148 | 25.129 |
| query.55 | 15 | 32768 | yes | 32 | 32768 | 76 | 76 | 1024.000 | 431.158 |
| query.56 | 21 | 4096 | no | 61 | 4096 | 163 | 163 | 67.148 | 25.129 |
| query.57 | 15 | 32768 | yes | 32 | 32768 | 56 | 76 | 1024.000 | 431.158 |
| query.58 | 15 | 32768 | yes | 32 | 32768 | 76 | 76 | 1024.000 | 431.158 |
| query.59 | 36 | 4096 | no | 109 | 4096 | 465 | 532 | 37.578 | 7.699 |
| query.60 | 36 | 4096 | no | 124 | 4096 | 499 | 499 | 33.032 | 8.208 |
| query.61 | 28 | 4096 | no | 90 | 4096 | 258 | 305 | 45.511 | 13.430 |
| query.62 | 28 | 4096 | no | 86 | 4096 | 293 | 293 | 47.628 | 13.980 |
| query.63 | 36 | 4096 | no | 129 | 4096 | 521 | 521 | 31.752 | 7.862 |
| query.64 | 10 | 1024 | yes | 16 | 1024 | 17 | 23 | 64.000 | 44.522 |
| query.65 | 28 | 4096 | no | 91 | 4096 | 313 | 313 | 45.011 | 13.086 |
| query.66 | 21 | 4096 | no | 59 | 4096 | 176 | 176 | 69.424 | 23.273 |
| query.67 | 28 | 4096 | no | 89 | 4096 | 220 | 314 | 46.022 | 13.045 |
| query.68 | 15 | 32768 | yes | 32 | 32768 | 76 | 76 | 1024.000 | 431.158 |
| query.69 | 36 | 4096 | no | 121 | 4096 | 519 | 535 | 33.851 | 7.656 |
| query.70 | 21 | 4096 | no | 60 | 4096 | 93 | 164 | 68.267 | 24.976 |
| query.71 | 28 | 4096 | no | 93 | 4096 | 298 | 316 | 44.043 | 12.962 |
| query.72 | 21 | 4096 | no | 62 | 4096 | 152 | 152 | 66.065 | 26.947 |
| query.73 | 21 | 4096 | no | 59 | 4096 | 160 | 160 | 69.424 | 25.600 |
| query.74 | 36 | 4096 | no | 127 | 4096 | 473 | 521 | 32.252 | 7.862 |
| query.75 | 3 | 8 | yes | 4 | 8 | 4 | 4 | 2.000 | 2.000 |
| query.76 | 6 | 64 | yes | 8 | 64 | 10 | 10 | 8.000 | 6.400 |
| query.77 | 36 | 4096 | no | 123 | 4096 | 523 | 523 | 33.301 | 7.832 |
| query.78 | 1 | 2 | yes | 2 | 2 | 2 | 2 | 1.000 | 1.000 |
| query.79 | 10 | 1024 | yes | 16 | 1024 | 26 | 26 | 64.000 | 39.385 |
| query.80 | 21 | 4096 | no | 62 | 4096 | 159 | 159 | 66.065 | 25.761 |
| query.81 | 21 | 4096 | no | 59 | 4096 | 157 | 157 | 69.424 | 26.089 |
| query.82 | 36 | 4096 | no | 123 | 4096 | 489 | 524 | 33.301 | 7.817 |
| query.83 | 3 | 8 | yes | 4 | 8 | 4 | 4 | 2.000 | 2.000 |
| query.84 | 10 | 1024 | yes | 16 | 1024 | 26 | 26 | 64.000 | 39.385 |
| query.85 | 1 | 2 | yes | 2 | 2 | 2 | 2 | 1.000 | 1.000 |
| query.86 | 21 | 4096 | no | 58 | 4096 | 160 | 161 | 70.621 | 25.441 |
| query.87 | 21 | 4096 | no | 62 | 4096 | 158 | 158 | 66.065 | 25.924 |
| query.88 | 10 | 1024 | yes | 16 | 1024 | 22 | 26 | 64.000 | 39.385 |
| query.89 | 15 | 32768 | yes | 32 | 32768 | 66 | 76 | 1024.000 | 431.158 |
| query.90 | 10 | 1024 | yes | 16 | 1024 | 26 | 26 | 64.000 | 39.385 |
| query.91 | 45 | 4096 | no | 127 | 4096 | 744 | 838 | 32.252 | 4.888 |
| query.92 | 6 | 64 | yes | 8 | 64 | 10 | 10 | 8.000 | 6.400 |
| query.93 | 6 | 64 | yes | 8 | 64 | 10 | 10 | 8.000 | 6.400 |
| query.94 | 21 | 4096 | no | 62 | 4096 | 144 | 158 | 66.065 | 25.924 |
| query.95 | 21 | 4096 | no | 63 | 4096 | 158 | 158 | 65.016 | 25.924 |
| query.96 | 28 | 4096 | no | 83 | 4096 | 322 | 322 | 49.349 | 12.720 |
| query.97 | 36 | 4096 | no | 117 | 4096 | 502 | 545 | 35.009 | 7.516 |
| query.98 | 15 | 32768 | yes | 32 | 32768 | 76 | 76 | 1024.000 | 431.158 |
| query.99 | 36 | 4096 | no | 118 | 4096 | 477 | 526 | 34.712 | 7.787 |
| query.100 | 10 | 1024 | yes | 16 | 1024 | 26 | 26 | 64.000 | 39.385 |
| query.101 | 45 | 4096 | no | 155 | 4096 | 827 | 832 | 26.426 | 4.923 |
| query.102 | 45 | 4096 | no | 149 | 4096 | 772 | 839 | 27.490 | 4.882 |
| query.103 | 66 | 4096 | no | 227 | 4096 | 1605 | 1605 | 18.044 | 2.552 |
| query.104 | 28 | 4096 | no | 93 | 4096 | 277 | 294 | 44.043 | 13.932 |
| query.105 | 28 | 4096 | no | 95 | 4096 | 308 | 308 | 43.116 | 13.299 |
| query.106 | 6 | 64 | yes | 8 | 64 | 10 | 10 | 8.000 | 6.400 |
| query.107 | 1 | 2 | yes | 2 | 2 | 2 | 2 | 1.000 | 1.000 |
| query.108 | 10 | 1024 | yes | 16 | 1024 | 26 | 26 | 64.000 | 39.385 |
| query.109 | 15 | 32768 | yes | 32 | 32768 | 70 | 71 | 1024.000 | 461.521 |
| query.110 | 21 | 4096 | no | 60 | 4096 | 120 | 168 | 68.267 | 24.381 |
| query.111 | 55 | 4096 | no | 207 | 4096 | 1189 | 1189 | 19.787 | 3.445 |
| query.112 | 6 | 64 | yes | 8 | 64 | 8 | 10 | 8.000 | 6.400 |
| query.113 | 15 | 32768 | yes | 32 | 32768 | 76 | 76 | 1024.000 | 431.158 |
| query.114 | 15 | 32768 | yes | 32 | 32768 | 66 | 76 | 1024.000 | 431.158 |
| query.115 | 6 | 64 | yes | 8 | 64 | 8 | 10 | 8.000 | 6.400 |
| query.116 | 45 | 4096 | no | 150 | 4096 | 864 | 864 | 27.307 | 4.741 |
| query.117 | 45 | 4096 | no | 158 | 4096 | 785 | 811 | 25.924 | 5.051 |
| query.118 | 15 | 32768 | yes | 32 | 32768 | 76 | 76 | 1024.000 | 431.158 |
| query.119 | 10 | 1024 | yes | 16 | 1024 | 26 | 26 | 64.000 | 39.385 |
| query.120 | 21 | 4096 | no | 63 | 4096 | 162 | 162 | 65.016 | 25.284 |
| query.121 | 36 | 4096 | no | 112 | 4096 | 547 | 547 | 36.571 | 7.488 |
| query.122 | 28 | 4096 | no | 90 | 4096 | 210 | 310 | 45.511 | 13.213 |
| query.123 | 28 | 4096 | no | 88 | 4096 | 296 | 304 | 46.545 | 13.474 |
| query.124 | 15 | 32768 | yes | 32 | 32768 | 76 | 76 | 1024.000 | 431.158 |
| query.125 | 10 | 1024 | yes | 16 | 1024 | 26 | 26 | 64.000 | 39.385 |
| query.126 | 15 | 32768 | yes | 32 | 32768 | 76 | 76 | 1024.000 | 431.158 |
| query.127 | 28 | 4096 | no | 92 | 4096 | 312 | 312 | 44.522 | 13.128 |
| query.128 | 28 | 4096 | no | 85 | 4096 | 314 | 314 | 48.188 | 13.045 |
| query.129 | 10 | 1024 | yes | 16 | 1024 | 26 | 26 | 64.000 | 39.385 |
| query.130 | 21 | 4096 | no | 60 | 4096 | 171 | 171 | 68.267 | 23.953 |
| query.131 | 3 | 8 | yes | 4 | 8 | 4 | 4 | 2.000 | 2.000 |
| query.132 | 10 | 1024 | yes | 16 | 1024 | 26 | 26 | 64.000 | 39.385 |
| query.133 | 10 | 1024 | yes | 16 | 1024 | 26 | 26 | 64.000 | 39.385 |
| query.134 | 45 | 4096 | no | 133 | 4096 | 681 | 844 | 30.797 | 4.853 |
| query.135 | 28 | 4096 | no | 88 | 4096 | 267 | 308 | 46.545 | 13.299 |
| query.136 | 15 | 32768 | yes | 32 | 32768 | 76 | 76 | 1024.000 | 431.158 |
| query.137 | 10 | 1024 | yes | 16 | 1024 | 26 | 26 | 64.000 | 39.385 |
| query.138 | 36 | 4096 | no | 133 | 4096 | 539 | 539 | 30.797 | 7.599 |
| query.139 | 3 | 8 | yes | 4 | 8 | 4 | 4 | 2.000 | 2.000 |
| query.140 | 28 | 4096 | no | 93 | 4096 | 75 | 282 | 44.043 | 14.525 |
| query.141 | 28 | 4096 | no | 95 | 4096 | 313 | 313 | 43.116 | 13.086 |
| query.142 | 28 | 4096 | no | 89 | 4096 | 231 | 277 | 46.022 | 14.787 |
| query.143 | 28 | 4096 | no | 95 | 4096 | 312 | 312 | 43.116 | 13.128 |
| query.144 | 36 | 4096 | no | 124 | 4096 | 480 | 496 | 33.032 | 8.258 |
| query.145 | 6 | 64 | yes | 8 | 64 | 10 | 10 | 8.000 | 6.400 |
| query.146 | 1 | 2 | yes | 2 | 2 | 2 | 2 | 1.000 | 1.000 |
| query.147 | 28 | 4096 | no | 92 | 4096 | 268 | 307 | 44.522 | 13.342 |
| query.148 | 3 | 8 | yes | 4 | 8 | 4 | 4 | 2.000 | 2.000 |
| query.149 | 21 | 4096 | no | 63 | 4096 | 83 | 159 | 65.016 | 25.761 |
| query.150 | 36 | 4096 | no | 125 | 4096 | 553 | 553 | 32.768 | 7.407 |
| query.151 | 10 | 1024 | yes | 16 | 1024 | 26 | 26 | 64.000 | 39.385 |
| query.152 | 10 | 1024 | yes | 16 | 1024 | 26 | 26 | 64.000 | 39.385 |
| query.153 | 6 | 64 | yes | 8 | 64 | 10 | 10 | 8.000 | 6.400 |
| query.154 | 15 | 32768 | yes | 32 | 32768 | 66 | 76 | 1024.000 | 431.158 |
| query.155 | 6 | 64 | yes | 8 | 64 | 10 | 10 | 8.000 | 6.400 |
| query.156 | 36 | 4096 | no | 123 | 4096 | 532 | 532 | 33.301 | 7.699 |
| query.157 | 6 | 64 | yes | 8 | 64 | 10 | 10 | 8.000 | 6.400 |
| query.158 | 45 | 4096 | no | 154 | 4096 | 829 | 829 | 26.597 | 4.941 |
| query.159 | 78 | 4096 | no | 271 | 4096 | 1964 | 1983 | 15.114 | 2.066 |
| query.160 | 28 | 4096 | no | 83 | 4096 | 310 | 310 | 49.349 | 13.213 |
| query.161 | 15 | 32768 | yes | 32 | 32768 | 76 | 76 | 1024.000 | 431.158 |
| query.162 | 28 | 4096 | no | 87 | 4096 | 305 | 305 | 47.080 | 13.430 |
| query.163 | 36 | 4096 | no | 121 | 4096 | 526 | 526 | 33.851 | 7.787 |
| query.164 | 10 | 1024 | yes | 16 | 1024 | 22 | 26 | 64.000 | 39.385 |
| query.165 | 6 | 64 | yes | 8 | 64 | 10 | 10 | 8.000 | 6.400 |
| query.166 | 15 | 32768 | yes | 32 | 32768 | 66 | 76 | 1024.000 | 431.158 |
| query.167 | 28 | 4096 | no | 95 | 4096 | 323 | 323 | 43.116 | 12.681 |
| query.168 | 15 | 32768 | yes | 32 | 32768 | 76 | 76 | 1024.000 | 431.158 |
| query.169 | 10 | 1024 | yes | 16 | 1024 | 22 | 26 | 64.000 | 39.385 |
| query.170 | 28 | 4096 | no | 95 | 4096 | 288 | 315 | 43.116 | 13.003 |
| query.171 | 6 | 64 | yes | 8 | 64 | 10 | 10 | 8.000 | 6.400 |
| query.172 | 1 | 2 | yes | 2 | 2 | 2 | 2 | 1.000 | 1.000 |
| query.173 | 28 | 4096 | no | 94 | 4096 | 309 | 309 | 43.574 | 13.256 |
| query.174 | 6 | 64 | yes | 8 | 64 | 10 | 10 | 8.000 | 6.400 |
| query.175 | 21 | 4096 | no | 61 | 4096 | 158 | 158 | 67.148 | 25.924 |
| query.176 | 21 | 4096 | no | 63 | 4096 | 161 | 161 | 65.016 | 25.441 |
| query.177 | 6 | 64 | yes | 8 | 64 | 10 | 10 | 8.000 | 6.400 |
| query.178 | 3 | 8 | yes | 4 | 8 | 4 | 4 | 2.000 | 2.000 |
| query.179 | 15 | 32768 | yes | 32 | 32768 | 76 | 76 | 1024.000 | 431.158 |
| query.180 | 66 | 4096 | no | 226 | 4096 | 1320 | 1654 | 18.124 | 2.476 |
| query.181 | 15 | 32768 | yes | 32 | 32768 | 66 | 76 | 1024.000 | 431.158 |
| query.182 | 1 | 2 | yes | 2 | 2 | 2 | 2 | 1.000 | 1.000 |
| query.183 | 28 | 4096 | no | 89 | 4096 | 180 | 285 | 46.022 | 14.372 |
| query.184 | 45 | 4096 | no | 164 | 4096 | 825 | 825 | 24.976 | 4.965 |
| query.185 | 3 | 8 | yes | 4 | 8 | 4 | 4 | 2.000 | 2.000 |
| query.186 | 15 | 32768 | yes | 32 | 32768 | 76 | 76 | 1024.000 | 431.158 |
| query.187 | 28 | 4096 | no | 92 | 4096 | 284 | 310 | 44.522 | 13.213 |
| query.188 | 10 | 1024 | yes | 16 | 1024 | 26 | 26 | 64.000 | 39.385 |
| query.189 | 1 | 2 | yes | 2 | 2 | 2 | 2 | 1.000 | 1.000 |
| query.190 | 6 | 64 | yes | 8 | 64 | 10 | 10 | 8.000 | 6.400 |
| query.191 | 10 | 1024 | yes | 16 | 1024 | 26 | 26 | 64.000 | 39.385 |
| query.192 | 10 | 1024 | yes | 16 | 1024 | 26 | 26 | 64.000 | 39.385 |
| query.193 | 15 | 32768 | yes | 32 | 32768 | 76 | 76 | 1024.000 | 431.158 |
| query.194 | 28 | 4096 | no | 89 | 4096 | 307 | 307 | 46.022 | 13.342 |
| query.195 | 78 | 4096 | no | 293 | 4096 | 2018 | 2044 | 13.980 | 2.004 |
| query.196 | 45 | 4096 | no | 153 | 4096 | 771 | 823 | 26.771 | 4.977 |
| query.197 | 10 | 1024 | yes | 16 | 1024 | 26 | 26 | 64.000 | 39.385 |
| query.198 | 6 | 64 | yes | 8 | 64 | 10 | 10 | 8.000 | 6.400 |
| query.199 | 28 | 4096 | no | 95 | 4096 | 319 | 319 | 43.116 | 12.840 |
| query.200 | 6 | 64 | yes | 8 | 64 | 10 | 10 | 8.000 | 6.400 |
| query.201 | 21 | 4096 | no | 61 | 4096 | 161 | 161 | 67.148 | 25.441 |
| query.202 | 10 | 1024 | yes | 16 | 1024 | 26 | 26 | 64.000 | 39.385 |
| query.203 | 55 | 4096 | no | 194 | 4096 | 682 | 1126 | 21.113 | 3.638 |
| query.204 | 15 | 32768 | yes | 32 | 32768 | 60 | 76 | 1024.000 | 431.158 |
| query.205 | 21 | 4096 | no | 60 | 4096 | 149 | 149 | 68.267 | 27.490 |
| query.206 | 21 | 4096 | no | 63 | 4096 | 127 | 158 | 65.016 | 25.924 |
| query.207 | 6 | 64 | yes | 8 | 64 | 10 | 10 | 8.000 | 6.400 |
| query.208 | 10 | 1024 | yes | 16 | 1024 | 18 | 26 | 64.000 | 39.385 |
| query.209 | 28 | 4096 | no | 92 | 4096 | 289 | 295 | 44.522 | 13.885 |
| query.210 | 6 | 64 | yes | 8 | 64 | 8 | 10 | 8.000 | 6.400 |
| query.211 | 21 | 4096 | no | 62 | 4096 | 166 | 166 | 66.065 | 24.675 |
| query.212 | 3 | 8 | yes | 4 | 8 | 4 | 4 | 2.000 | 2.000 |
| query.213 | 6 | 64 | yes | 8 | 64 | 10 | 10 | 8.000 | 6.400 |
| query.214 | 6 | 64 | yes | 8 | 64 | 10 | 10 | 8.000 | 6.400 |
| query.215 | 15 | 32768 | yes | 32 | 32768 | 76 | 76 | 1024.000 | 431.158 |
| query.216 | 10 | 1024 | yes | 16 | 1024 | 26 | 26 | 64.000 | 39.385 |
| query.217 | 10 | 1024 | yes | 16 | 1024 | 26 | 26 | 64.000 | 39.385 |
| query.218 | 21 | 4096 | no | 62 | 4096 | 153 | 153 | 66.065 | 26.771 |
| query.219 | 10 | 1024 | yes | 16 | 1024 | 26 | 26 | 64.000 | 39.385 |
| query.220 | 21 | 4096 | no | 64 | 4096 | 163 | 163 | 64.000 | 25.129 |
| query.221 | 3 | 8 | yes | 4 | 8 | 4 | 4 | 2.000 | 2.000 |
| query.222 | 6 | 64 | yes | 8 | 64 | 8 | 10 | 8.000 | 6.400 |
| query.223 | 28 | 4096 | no | 92 | 4096 | 307 | 307 | 44.522 | 13.342 |
| query.224 | 28 | 4096 | no | 93 | 4096 | 307 | 307 | 44.043 | 13.342 |
| query.225 | 6 | 64 | yes | 8 | 64 | 10 | 10 | 8.000 | 6.400 |
| query.226 | 10 | 1024 | yes | 16 | 1024 | 26 | 26 | 64.000 | 39.385 |
| query.227 | 10 | 1024 | yes | 16 | 1024 | 26 | 26 | 64.000 | 39.385 |
| query.228 | 10 | 1024 | yes | 16 | 1024 | 22 | 26 | 64.000 | 39.385 |
| query.229 | 21 | 4096 | no | 62 | 4096 | 162 | 162 | 66.065 | 25.284 |
| query.230 | 6 | 64 | yes | 8 | 64 | 8 | 10 | 8.000 | 6.400 |
| query.231 | 21 | 4096 | no | 60 | 4096 | 137 | 156 | 68.267 | 26.256 |
| query.232 | 21 | 4096 | no | 62 | 4096 | 158 | 158 | 66.065 | 25.924 |
| query.233 | 21 | 4096 | no | 62 | 4096 | 159 | 159 | 66.065 | 25.761 |
| query.234 | 3 | 8 | yes | 4 | 8 | 4 | 4 | 2.000 | 2.000 |
| query.235 | 28 | 4096 | no | 90 | 4096 | 312 | 312 | 45.511 | 13.128 |
| query.236 | 28 | 4096 | no | 92 | 4096 | 300 | 300 | 44.522 | 13.653 |
| query.237 | 10 | 1024 | yes | 16 | 1024 | 26 | 26 | 64.000 | 39.385 |
| query.238 | 21 | 4096 | no | 59 | 4096 | 156 | 156 | 69.424 | 26.256 |
| query.239 | 3 | 8 | yes | 4 | 8 | 4 | 4 | 2.000 | 2.000 |
| query.240 | 6 | 64 | yes | 8 | 64 | 8 | 10 | 8.000 | 6.400 |
| query.241 | 6 | 64 | yes | 8 | 64 | 10 | 10 | 8.000 | 6.400 |
| query.242 | 10 | 1024 | yes | 16 | 1024 | 26 | 26 | 64.000 | 39.385 |
| query.243 | 28 | 4096 | no | 92 | 4096 | 309 | 329 | 44.522 | 12.450 |
| query.244 | 45 | 4096 | no | 152 | 4096 | 499 | 782 | 26.947 | 5.238 |
| query.245 | 28 | 4096 | no | 89 | 4096 | 321 | 321 | 46.022 | 12.760 |
| query.246 | 55 | 4096 | no | 164 | 4096 | 1188 | 1188 | 24.976 | 3.448 |
| query.247 | 10 | 1024 | yes | 16 | 1024 | 26 | 26 | 64.000 | 39.385 |
| query.248 | 6 | 64 | yes | 8 | 64 | 8 | 9 | 8.000 | 7.111 |
| query.249 | 10 | 1024 | yes | 16 | 1024 | 23 | 25 | 64.000 | 40.960 |
| query.250 | 10 | 1024 | yes | 16 | 1024 | 26 | 26 | 64.000 | 39.385 |
| query.251 | 21 | 4096 | no | 61 | 4096 | 55 | 155 | 67.148 | 26.426 |
| query.252 | 15 | 32768 | yes | 32 | 32768 | 66 | 76 | 1024.000 | 431.158 |
| query.253 | 36 | 4096 | no | 126 | 4096 | 501 | 529 | 32.508 | 7.743 |
| query.254 | 21 | 4096 | no | 62 | 4096 | 159 | 159 | 66.065 | 25.761 |
| query.255 | 15 | 32768 | yes | 32 | 32768 | 66 | 75 | 1024.000 | 436.907 |
| query.256 | 6 | 64 | yes | 8 | 64 | 10 | 10 | 8.000 | 6.400 |
| query.257 | 10 | 1024 | yes | 16 | 1024 | 13 | 23 | 64.000 | 44.522 |
| query.258 | 28 | 4096 | no | 87 | 4096 | 210 | 301 | 47.080 | 13.608 |
| query.259 | 28 | 4096 | no | 89 | 4096 | 294 | 309 | 46.022 | 13.256 |
| query.260 | 3 | 8 | yes | 4 | 8 | 4 | 4 | 2.000 | 2.000 |
| query.261 | 3 | 8 | yes | 4 | 8 | 4 | 4 | 2.000 | 2.000 |
| query.262 | 21 | 4096 | no | 60 | 4096 | 147 | 157 | 68.267 | 26.089 |
| query.263 | 28 | 4096 | no | 89 | 4096 | 42 | 225 | 46.022 | 18.204 |
| query.264 | 15 | 32768 | yes | 32 | 32768 | 76 | 76 | 1024.000 | 431.158 |
| query.265 | 21 | 4096 | no | 62 | 4096 | 160 | 160 | 66.065 | 25.600 |
| query.266 | 15 | 32768 | yes | 32 | 32768 | 76 | 76 | 1024.000 | 431.158 |
| query.267 | 36 | 4096 | no | 129 | 4096 | 509 | 509 | 31.752 | 8.047 |
| query.268 | 3 | 8 | yes | 4 | 8 | 4 | 4 | 2.000 | 2.000 |
| query.269 | 45 | 4096 | no | 164 | 4096 | 669 | 785 | 24.976 | 5.218 |
| query.270 | 10 | 1024 | yes | 16 | 1024 | 26 | 26 | 64.000 | 39.385 |
| query.271 | 21 | 4096 | no | 61 | 4096 | 159 | 167 | 67.148 | 24.527 |
| query.272 | 10 | 1024 | yes | 16 | 1024 | 26 | 26 | 64.000 | 39.385 |
| query.273 | 45 | 4096 | no | 135 | 4096 | 775 | 875 | 30.341 | 4.681 |
| query.274 | 78 | 4096 | no | 264 | 4096 | 2010 | 2018 | 15.515 | 2.030 |
| query.275 | 28 | 4096 | no | 87 | 4096 | 180 | 284 | 47.080 | 14.423 |
| query.276 | 6 | 64 | yes | 8 | 64 | 10 | 10 | 8.000 | 6.400 |
| query.277 | 21 | 4096 | no | 58 | 4096 | 153 | 167 | 70.621 | 24.527 |
| query.278 | 10 | 1024 | yes | 16 | 1024 | 26 | 26 | 64.000 | 39.385 |
| query.279 | 15 | 32768 | yes | 32 | 32768 | 76 | 76 | 1024.000 | 431.158 |
| query.280 | 15 | 32768 | yes | 32 | 32768 | 76 | 76 | 1024.000 | 431.158 |
| query.281 | 28 | 4096 | no | 87 | 4096 | 307 | 307 | 47.080 | 13.342 |
| query.282 | 28 | 4096 | no | 90 | 4096 | 222 | 301 | 45.511 | 13.608 |
| query.283 | 21 | 4096 | no | 63 | 4096 | 158 | 158 | 65.016 | 25.924 |
| query.284 | 15 | 32768 | yes | 32 | 32768 | 76 | 76 | 1024.000 | 431.158 |
| query.285 | 66 | 4096 | no | 210 | 4096 | 1574 | 1603 | 19.505 | 2.555 |
| query.286 | 10 | 1024 | yes | 16 | 1024 | 26 | 26 | 64.000 | 39.385 |
| query.287 | 10 | 1024 | yes | 16 | 1024 | 26 | 26 | 64.000 | 39.385 |
| query.288 | 15 | 32768 | yes | 32 | 32768 | 76 | 76 | 1024.000 | 431.158 |
| query.289 | 21 | 4096 | no | 61 | 4096 | 159 | 159 | 67.148 | 25.761 |
| query.290 | 45 | 4096 | no | 153 | 4096 | 593 | 797 | 26.771 | 5.139 |
| query.291 | 10 | 1024 | yes | 16 | 1024 | 26 | 26 | 64.000 | 39.385 |
| query.292 | 3 | 8 | yes | 4 | 8 | 4 | 4 | 2.000 | 2.000 |
| query.293 | 36 | 4096 | no | 113 | 4096 | 564 | 564 | 36.248 | 7.262 |
| query.294 | 15 | 32768 | yes | 32 | 32768 | 72 | 76 | 1024.000 | 431.158 |
| query.295 | 15 | 32768 | yes | 32 | 32768 | 76 | 76 | 1024.000 | 431.158 |
| query.296 | 6 | 64 | yes | 8 | 64 | 6 | 10 | 8.000 | 6.400 |
| query.297 | 36 | 4096 | no | 111 | 4096 | 472 | 536 | 36.901 | 7.642 |
| query.298 | 15 | 32768 | yes | 32 | 32768 | 58 | 76 | 1024.000 | 431.158 |
| query.299 | 15 | 32768 | yes | 32 | 32768 | 76 | 76 | 1024.000 | 431.158 |
| query.300 | 21 | 4096 | no | 61 | 4096 | 164 | 164 | 67.148 | 24.976 |
| query.301 | 45 | 4096 | no | 146 | 4096 | 820 | 823 | 28.055 | 4.977 |
| query.302 | 3 | 8 | yes | 4 | 8 | 4 | 4 | 2.000 | 2.000 |
| query.303 | 28 | 4096 | no | 89 | 4096 | 314 | 314 | 46.022 | 13.045 |
| query.304 | 10 | 1024 | yes | 16 | 1024 | 18 | 26 | 64.000 | 39.385 |
| query.305 | 15 | 32768 | yes | 32 | 32768 | 64 | 74 | 1024.000 | 442.811 |
| query.306 | 3 | 8 | yes | 4 | 8 | 4 | 4 | 2.000 | 2.000 |
| query.307 | 55 | 4096 | no | 191 | 4096 | 1057 | 1183 | 21.445 | 3.462 |
| query.308 | 28 | 4096 | no | 87 | 4096 | 252 | 313 | 47.080 | 13.086 |
| query.309 | 10 | 1024 | yes | 16 | 1024 | 18 | 26 | 64.000 | 39.385 |
| query.310 | 45 | 4096 | no | 142 | 4096 | 739 | 847 | 28.845 | 4.836 |
| query.311 | 21 | 4096 | no | 63 | 4096 | 162 | 162 | 65.016 | 25.284 |
| query.312 | 6 | 64 | yes | 8 | 64 | 10 | 10 | 8.000 | 6.400 |
| query.313 | 3 | 8 | yes | 4 | 8 | 4 | 4 | 2.000 | 2.000 |
| query.314 | 15 | 32768 | yes | 32 | 32768 | 76 | 76 | 1024.000 | 431.158 |
| query.315 | 6 | 64 | yes | 8 | 64 | 10 | 10 | 8.000 | 6.400 |
| query.316 | 6 | 64 | yes | 8 | 64 | 10 | 10 | 8.000 | 6.400 |
| query.317 | 6 | 64 | yes | 8 | 64 | 10 | 10 | 8.000 | 6.400 |
| query.318 | 36 | 4096 | no | 118 | 4096 | 412 | 526 | 34.712 | 7.787 |
| query.319 | 3 | 8 | yes | 4 | 8 | 4 | 4 | 2.000 | 2.000 |
| query.320 | 21 | 4096 | no | 62 | 4096 | 161 | 161 | 66.065 | 25.441 |
| query.321 | 28 | 4096 | no | 91 | 4096 | 312 | 312 | 45.011 | 13.128 |
| query.322 | 10 | 1024 | yes | 16 | 1024 | 26 | 26 | 64.000 | 39.385 |
| query.323 | 0 | 1 | yes | 1 | 1 | 1 | 1 | 1.000 | 1.000 |
| query.324 | 15 | 32768 | yes | 32 | 32768 | 76 | 76 | 1024.000 | 431.158 |
| query.325 | 10 | 1024 | yes | 16 | 1024 | 26 | 26 | 64.000 | 39.385 |
| query.326 | 28 | 4096 | no | 89 | 4096 | 315 | 317 | 46.022 | 12.921 |
| query.327 | 6 | 64 | yes | 8 | 64 | 10 | 10 | 8.000 | 6.400 |
| query.328 | 21 | 4096 | no | 62 | 4096 | 159 | 159 | 66.065 | 25.761 |
| query.329 | 45 | 4096 | no | 151 | 4096 | 798 | 819 | 27.126 | 5.001 |
| query.330 | 36 | 4096 | no | 109 | 4096 | 532 | 532 | 37.578 | 7.699 |
| query.331 | 21 | 4096 | no | 61 | 4096 | 166 | 166 | 67.148 | 24.675 |
| query.332 | 36 | 4096 | no | 119 | 4096 | 503 | 532 | 34.420 | 7.699 |
| query.333 | 3 | 8 | yes | 4 | 8 | 4 | 4 | 2.000 | 2.000 |
| query.334 | 15 | 32768 | yes | 32 | 32768 | 76 | 76 | 1024.000 | 431.158 |
| query.335 | 91 | 4096 | no | 271 | 4096 | 2058 | 2426 | 15.114 | 1.688 |
| query.336 | 45 | 4096 | no | 153 | 4096 | 718 | 815 | 26.771 | 5.026 |
| query.337 | 10 | 1024 | yes | 16 | 1024 | 26 | 26 | 64.000 | 39.385 |
| query.338 | 36 | 4096 | no | 116 | 4096 | 403 | 499 | 35.310 | 8.208 |
| query.339 | 36 | 4096 | no | 127 | 4096 | 545 | 545 | 32.252 | 7.516 |
| query.340 | 10 | 1024 | yes | 16 | 1024 | 26 | 26 | 64.000 | 39.385 |
| query.341 | 10 | 1024 | yes | 16 | 1024 | 26 | 26 | 64.000 | 39.385 |
| query.342 | 66 | 4096 | no | 219 | 4096 | 1508 | 1606 | 18.703 | 2.550 |
| query.343 | 36 | 4096 | no | 128 | 4096 | 504 | 504 | 32.000 | 8.127 |
| query.344 | 15 | 32768 | yes | 32 | 32768 | 76 | 76 | 1024.000 | 431.158 |
| query.345 | 15 | 32768 | yes | 32 | 32768 | 66 | 76 | 1024.000 | 431.158 |
| query.346 | 36 | 4096 | no | 130 | 4096 | 520 | 535 | 31.508 | 7.656 |
| query.347 | 10 | 1024 | yes | 16 | 1024 | 26 | 26 | 64.000 | 39.385 |
| query.348 | 21 | 4096 | no | 62 | 4096 | 155 | 155 | 66.065 | 26.426 |
| query.349 | 66 | 4096 | no | 230 | 4096 | 1616 | 1616 | 17.809 | 2.535 |
| query.350 | 21 | 4096 | no | 61 | 4096 | 133 | 150 | 67.148 | 27.307 |
| query.351 | 6 | 64 | yes | 8 | 64 | 10 | 10 | 8.000 | 6.400 |
| query.352 | 28 | 4096 | no | 96 | 4096 | 323 | 323 | 42.667 | 12.681 |
| query.353 | 45 | 4096 | no | 160 | 4096 | 819 | 819 | 25.600 | 5.001 |
| query.354 | 28 | 4096 | no | 93 | 4096 | 293 | 302 | 44.043 | 13.563 |
| query.355 | 55 | 4096 | no | 196 | 4096 | 979 | 1149 | 20.898 | 3.565 |
| query.356 | 36 | 4096 | no | 126 | 4096 | 512 | 512 | 32.508 | 8.000 |
| query.357 | 15 | 32768 | yes | 32 | 32768 | 76 | 76 | 1024.000 | 431.158 |
| query.358 | 28 | 4096 | no | 89 | 4096 | 323 | 323 | 46.022 | 12.681 |
| query.359 | 55 | 4096 | no | 202 | 4096 | 1182 | 1182 | 20.277 | 3.465 |
| query.360 | 21 | 4096 | no | 60 | 4096 | 164 | 164 | 68.267 | 24.976 |
| query.361 | 36 | 4096 | no | 132 | 4096 | 495 | 495 | 31.030 | 8.275 |
| query.362 | 28 | 4096 | no | 91 | 4096 | 241 | 277 | 45.011 | 14.787 |
| query.363 | 15 | 32768 | yes | 32 | 32768 | 46 | 75 | 1024.000 | 436.907 |
| query.364 | 45 | 4096 | no | 144 | 4096 | 826 | 836 | 28.444 | 4.900 |
| query.365 | 10 | 1024 | yes | 16 | 1024 | 25 | 26 | 64.000 | 39.385 |
| query.366 | 10 | 1024 | yes | 16 | 1024 | 26 | 26 | 64.000 | 39.385 |
| query.367 | 28 | 4096 | no | 98 | 4096 | 323 | 323 | 41.796 | 12.681 |
| query.368 | 45 | 4096 | no | 144 | 4096 | 821 | 821 | 28.444 | 4.989 |
| query.369 | 6 | 64 | yes | 8 | 64 | 10 | 10 | 8.000 | 6.400 |
| query.370 | 28 | 4096 | no | 92 | 4096 | 336 | 336 | 44.522 | 12.190 |
| query.371 | 36 | 4096 | no | 115 | 4096 | 485 | 523 | 35.617 | 7.832 |
| query.372 | 36 | 4096 | no | 128 | 4096 | 496 | 526 | 32.000 | 7.787 |
| query.373 | 10 | 1024 | yes | 16 | 1024 | 26 | 26 | 64.000 | 39.385 |
| query.374 | 55 | 4096 | no | 172 | 4096 | 982 | 1164 | 23.814 | 3.519 |
| query.375 | 15 | 32768 | yes | 32 | 32768 | 76 | 76 | 1024.000 | 431.158 |
| query.376 | 28 | 4096 | no | 94 | 4096 | 275 | 303 | 43.574 | 13.518 |
| query.377 | 21 | 4096 | no | 60 | 4096 | 168 | 168 | 68.267 | 24.381 |
| query.378 | 45 | 4096 | no | 158 | 4096 | 800 | 800 | 25.924 | 5.120 |
| query.379 | 15 | 32768 | yes | 32 | 32768 | 46 | 74 | 1024.000 | 442.811 |
| query.380 | 21 | 4096 | no | 62 | 4096 | 108 | 157 | 66.065 | 26.089 |
| query.381 | 45 | 4096 | no | 149 | 4096 | 807 | 842 | 27.490 | 4.865 |
| query.382 | 21 | 4096 | no | 60 | 4096 | 164 | 164 | 68.267 | 24.976 |
| query.383 | 45 | 4096 | no | 148 | 4096 | 848 | 848 | 27.676 | 4.830 |
| query.384 | 15 | 32768 | yes | 32 | 32768 | 76 | 76 | 1024.000 | 431.158 |
| query.385 | 28 | 4096 | no | 93 | 4096 | 249 | 300 | 44.043 | 13.653 |
| query.386 | 28 | 4096 | no | 86 | 4096 | 289 | 315 | 47.628 | 13.003 |
| query.387 | 55 | 4096 | no | 188 | 4096 | 1012 | 1158 | 21.787 | 3.537 |
| query.388 | 36 | 4096 | no | 128 | 4096 | 510 | 510 | 32.000 | 8.031 |
| query.389 | 15 | 32768 | yes | 32 | 32768 | 76 | 76 | 1024.000 | 431.158 |
| query.390 | 21 | 4096 | no | 62 | 4096 | 169 | 169 | 66.065 | 24.237 |
| query.391 | 6 | 64 | yes | 8 | 64 | 10 | 10 | 8.000 | 6.400 |
| query.392 | 45 | 4096 | no | 142 | 4096 | 695 | 830 | 28.845 | 4.935 |
| query.393 | 28 | 4096 | no | 89 | 4096 | 306 | 306 | 46.022 | 13.386 |
| query.394 | 15 | 32768 | yes | 32 | 32768 | 76 | 76 | 1024.000 | 431.158 |
| query.395 | 15 | 32768 | yes | 32 | 32768 | 36 | 76 | 1024.000 | 431.158 |
| query.396 | 6 | 64 | yes | 8 | 64 | 10 | 10 | 8.000 | 6.400 |
| query.397 | 15 | 32768 | yes | 32 | 32768 | 66 | 76 | 1024.000 | 431.158 |
| query.398 | 28 | 4096 | no | 89 | 4096 | 223 | 273 | 46.022 | 15.004 |
| query.399 | 6 | 64 | yes | 8 | 64 | 10 | 10 | 8.000 | 6.400 |
| query.400 | 21 | 4096 | no | 59 | 4096 | 173 | 173 | 69.424 | 23.676 |
| query.401 | 10 | 1024 | yes | 16 | 1024 | 26 | 26 | 64.000 | 39.385 |
| query.402 | 3 | 8 | yes | 4 | 8 | 4 | 4 | 2.000 | 2.000 |
| query.403 | 36 | 4096 | no | 109 | 4096 | 395 | 525 | 37.578 | 7.802 |
| query.404 | 21 | 4096 | no | 58 | 4096 | 138 | 164 | 70.621 | 24.976 |
| query.405 | 15 | 32768 | yes | 32 | 32768 | 76 | 76 | 1024.000 | 431.158 |
| query.406 | 21 | 4096 | no | 62 | 4096 | 163 | 163 | 66.065 | 25.129 |
| query.407 | 21 | 4096 | no | 63 | 4096 | 169 | 169 | 65.016 | 24.237 |
| query.408 | 10 | 1024 | yes | 16 | 1024 | 18 | 26 | 64.000 | 39.385 |
| query.409 | 28 | 4096 | no | 84 | 4096 | 326 | 326 | 48.762 | 12.564 |
| query.410 | 28 | 4096 | no | 88 | 4096 | 265 | 285 | 46.545 | 14.372 |
| query.411 | 6 | 64 | yes | 8 | 64 | 10 | 10 | 8.000 | 6.400 |
| query.412 | 21 | 4096 | no | 60 | 4096 | 169 | 169 | 68.267 | 24.237 |
| query.413 | 21 | 4096 | no | 63 | 4096 | 98 | 157 | 65.016 | 26.089 |
| query.414 | 3 | 8 | yes | 4 | 8 | 3 | 4 | 2.000 | 2.000 |
| query.415 | 6 | 64 | yes | 8 | 64 | 10 | 10 | 8.000 | 6.400 |
| query.416 | 3 | 8 | yes | 4 | 8 | 4 | 4 | 2.000 | 2.000 |
| query.417 | 6 | 64 | yes | 8 | 64 | 10 | 10 | 8.000 | 6.400 |
| query.418 | 6 | 64 | yes | 8 | 64 | 10 | 10 | 8.000 | 6.400 |
| query.419 | 3 | 8 | yes | 4 | 8 | 4 | 4 | 2.000 | 2.000 |
| query.420 | 55 | 4096 | no | 195 | 4096 | 1022 | 1144 | 21.005 | 3.580 |
| query.421 | 15 | 32768 | yes | 32 | 32768 | 76 | 76 | 1024.000 | 431.158 |
| query.422 | 28 | 4096 | no | 86 | 4096 | 314 | 314 | 47.628 | 13.045 |
| query.423 | 15 | 32768 | yes | 32 | 32768 | 58 | 76 | 1024.000 | 431.158 |
| query.424 | 10 | 1024 | yes | 16 | 1024 | 26 | 26 | 64.000 | 39.385 |
| query.425 | 3 | 8 | yes | 4 | 8 | 4 | 4 | 2.000 | 2.000 |
| query.426 | 6 | 64 | yes | 8 | 64 | 10 | 10 | 8.000 | 6.400 |
| query.427 | 10 | 1024 | yes | 16 | 1024 | 26 | 26 | 64.000 | 39.385 |
| query.428 | 15 | 32768 | yes | 32 | 32768 | 76 | 76 | 1024.000 | 431.158 |
| query.429 | 66 | 4096 | no | 223 | 4096 | 1640 | 1640 | 18.368 | 2.498 |
| query.430 | 36 | 4096 | no | 110 | 4096 | 572 | 572 | 37.236 | 7.161 |
| query.431 | 45 | 4096 | no | 147 | 4096 | 771 | 801 | 27.864 | 5.114 |
| query.432 | 6 | 64 | yes | 8 | 64 | 10 | 10 | 8.000 | 6.400 |
| query.433 | 21 | 4096 | no | 61 | 4096 | 139 | 161 | 67.148 | 25.441 |
| query.434 | 10 | 1024 | yes | 16 | 1024 | 26 | 26 | 64.000 | 39.385 |
| query.435 | 21 | 4096 | no | 62 | 4096 | 166 | 166 | 66.065 | 24.675 |
| query.436 | 21 | 4096 | no | 63 | 4096 | 168 | 168 | 65.016 | 24.381 |
| query.437 | 45 | 4096 | no | 145 | 4096 | 821 | 821 | 28.248 | 4.989 |
| query.438 | 28 | 4096 | no | 90 | 4096 | 295 | 320 | 45.511 | 12.800 |
| query.439 | 45 | 4096 | no | 140 | 4096 | 738 | 830 | 29.257 | 4.935 |
| query.440 | 15 | 32768 | yes | 32 | 32768 | 76 | 76 | 1024.000 | 431.158 |
| query.441 | 10 | 1024 | yes | 16 | 1024 | 22 | 26 | 64.000 | 39.385 |
| query.442 | 21 | 4096 | no | 64 | 4096 | 163 | 163 | 64.000 | 25.129 |
| query.443 | 21 | 4096 | no | 62 | 4096 | 135 | 164 | 66.065 | 24.976 |
| query.444 | 45 | 4096 | no | 144 | 4096 | 794 | 828 | 28.444 | 4.947 |
| query.445 | 36 | 4096 | no | 132 | 4096 | 457 | 501 | 31.030 | 8.176 |
| query.446 | 1 | 2 | yes | 2 | 2 | 2 | 2 | 1.000 | 1.000 |
| query.447 | 55 | 4096 | no | 220 | 4096 | 1016 | 1134 | 18.618 | 3.612 |
| query.448 | 28 | 4096 | no | 87 | 4096 | 306 | 306 | 47.080 | 13.386 |
| query.449 | 10 | 1024 | yes | 16 | 1024 | 26 | 26 | 64.000 | 39.385 |
| query.450 | 6 | 64 | yes | 8 | 64 | 10 | 10 | 8.000 | 6.400 |
| query.451 | 21 | 4096 | no | 62 | 4096 | 163 | 163 | 66.065 | 25.129 |
| query.452 | 21 | 4096 | no | 64 | 4096 | 161 | 161 | 64.000 | 25.441 |
| query.453 | 10 | 1024 | yes | 16 | 1024 | 26 | 26 | 64.000 | 39.385 |
| query.454 | 36 | 4096 | no | 118 | 4096 | 554 | 554 | 34.712 | 7.394 |
| query.455 | 28 | 4096 | no | 82 | 4096 | 137 | 314 | 49.951 | 13.045 |
| query.456 | 36 | 4096 | no | 127 | 4096 | 516 | 516 | 32.252 | 7.938 |
| query.457 | 15 | 32768 | yes | 32 | 32768 | 76 | 76 | 1024.000 | 431.158 |
| query.458 | 21 | 4096 | no | 62 | 4096 | 155 | 155 | 66.065 | 26.426 |
| query.459 | 21 | 4096 | no | 61 | 4096 | 160 | 160 | 67.148 | 25.600 |
| query.460 | 10 | 1024 | yes | 16 | 1024 | 26 | 26 | 64.000 | 39.385 |
| query.461 | 55 | 4096 | no | 191 | 4096 | 1017 | 1145 | 21.445 | 3.577 |
| query.462 | 6 | 64 | yes | 8 | 64 | 10 | 10 | 8.000 | 6.400 |
| query.463 | 28 | 4096 | no | 94 | 4096 | 312 | 318 | 43.574 | 12.881 |
| query.464 | 15 | 32768 | yes | 32 | 32768 | 76 | 76 | 1024.000 | 431.158 |
| query.465 | 45 | 4096 | no | 150 | 4096 | 579 | 763 | 27.307 | 5.368 |
| query.466 | 36 | 4096 | no | 124 | 4096 | 530 | 530 | 33.032 | 7.728 |
| query.467 | 21 | 4096 | no | 64 | 4096 | 131 | 161 | 64.000 | 25.441 |
| query.468 | 21 | 4096 | no | 63 | 4096 | 160 | 160 | 65.016 | 25.600 |
