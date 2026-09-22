# MCV-Semantic-Factorization-v0

## Verdict

The conservative source-derived dependency graph does **not** split any nonempty Census query into multiple factors. Every query contains all pair candidates over its predicate columns; overlap edges therefore form the connected line graph of a complete column graph. This is **Outcome E**: exact numerical composition exists, but fixed-universe semantic factorization offers no exponential response-table reduction on Census.

## Source-derived dependency graph

A node is one relevant MCV candidate. Two nodes are connected if their complete compatible-clause scopes may overlap in any reachable state. Complete scope includes attributes and statistics expressions; plain `stxkeys` intersection is not used. Connected components are the conservative factors.

PostgreSQL computes each winner's `stat_sel` using `mcv_clauselist_selectivity()` and `mcv_combine_selectivities()`, then updates the AND-path accumulator with `sel *= stat_sel`. In the frozen replay IR, each candidate stores the normalized correction `stat_sel/simple_sel`; hence a factor can expose one normalized multiplier and the query estimate is reconstructed as `baseline_rows * product(factor_multiplier)`.

Mathematically the normalized factors compose multiplicatively, so composition is commutative and associative. IEEE-754 regrouping is not universally associative; native bitwise reproduction requires retaining and merging the OID-ordered contribution streams.

## Factor interfaces

| interface | contents | result |
|---|---|---|
| F1 | one normalized scalar correction multiplier | smallest tolerance-exact interface |
| F2 | F1 plus local simple selectivity | redundant after normalization |
| F3 | F1 plus consumed-clause identity | useful for control auditing; does not repair FP regrouping |
| F4 | OID-ordered local winner/contribution stream | bitwise exact, but violates the anti-triviality rule by retaining local execution history |

F1 reconstructed all 3,374,717 evaluated designs within relative tolerance `1e-12`: 2,039,200 (60.43%) were bitwise exact and 1,335,517 (39.57%) differed only by floating-point regrouping. Maximum exhaustive-query relative error was 4.397e-16. F4 was bitwise exact for all 3,374,717 designs, but is not accepted as a compact interface.

## Validation coverage

All 229 queries with at most 15 candidates were exhaustively evaluated (2,395,773 subsets). The other 239 queries used 4,096 deterministic subsets each. Total direct/factorized comparisons: 3,374,717. Divergences: 0.

Across the exhaustive domain:

- exactly reconstructed queries: 229/229;
- queries with counterexamples: 0;
- single-factor queries: 229;
- multi-factor queries: 0;
- median/mean/p95/max factor count: 1.000 / 0.996 / 1.000 / 1;
- median/mean/p95/max largest-factor size: 10.000 / 9.284 / 15.000 / 15;
- median dependency density: 0.667;
- structural log2 enumeration reduction: 0 for every query.

The one zero-candidate query has zero factors. Every other Census query has exactly one factor, including sampled queries up to 91 candidates.

## Nontrivial two-factor and background-invariance fixture

To test actual composition rather than only the Census single-factor identity, a restricted frozen query.4 fixture uses candidate 230 on `(dincome2,isex)` and candidate 448 on `(dincome7,drearning)`. Their scopes are disjoint, producing two singleton factors. All four designs reconstructed bitwise exactly. Four cross-factor background-invariance checks found zero failures.

This fixture shows that the source-derived composition works when a nontrivial factor split exists. It does not change the negative Census structural result.

## Expression safety

The synthetic expression fixture places `(a, lower(t))` and `(b, lower(t))` in the same factor. Although ordinary attribute `stxkeys` are disjoint, the shared expression clause creates a semantic dependency edge. This prevents the unsafe split identified in MCV-Commutativity-v0.

## Structural enumeration complexity

For each nonempty Census query, the sole factor has size `m_q`. Therefore:

```text
full log2 configurations       = m_q
factorized log2 enumeration   = log2(2^m_q) = m_q
structural log2 reduction     = 0
```

No runtime or optimizer speedup is inferred. The hypothetical factor-table cost is exactly the unfactorized response-table cost.

## Cross-factor invariance and counterexamples

Census cross-factor invariance is vacuous because it has no multi-factor queries. The nontrivial fixture performed 4 checks with 0 failures. No hidden-control, incomplete-interface, simple-selectivity, or tolerance-level numerical counterexample was found. Floating-point regrouping produced non-bitwise F1 results, which is recorded as a numerical-order effect rather than hidden semantic coupling.

## Why this does not contradict CE-Semantic-State-v0

State compression asked whether distinct complete design histories could be merged into a restart-safe execution state. Factorization retains every design bit and asks whether response tables can be evaluated componentwise. These are different properties. In this workload the latter route is blocked earlier: the conservative candidate dependency graph is connected, so there is no Cartesian factor structure to exploit.

## Runtime and limitations

Runtime: 67.13 seconds.

- Main evidence is frozen Census pair-MCV, fixed precedence, and single-attribute AND predicates.
- Large-query reconstruction is sampled, although graph connectivity is computed exactly for every query.
- F1 is tolerance-exact, not universally bitwise exact.
- F4 is a validation control, not an acceptable compact interface.
- The restricted two-factor fixture proves composition behavior but not structural prevalence.
- CE factorization does not make q-error additive.

## Required final answers

1. **Does the dependency relation produce nontrivial factors?** No. Every nonempty Census candidate graph is one connected component.
2. **Are factor responses independent of other factors?** In the nontrivial restricted fixture, yes; Census itself has no cross-factor backgrounds to test.
3. **Smallest tested interface?** One normalized scalar correction multiplier (F1) for tolerance-exact reconstruction. No compact universally bitwise-exact interface was established; F4 is bitwise exact but retains local history.
4. **Can every exhaustively tested estimate be reconstructed?** Yes within `1e-12` for all 2,395,773 exhaustive designs, with zero divergences.
5. **Counterexamples?** No tolerance-level semantic counterexample. Floating regrouping caused non-bitwise F1 results. No Census structural split exists.
6. **Factor sizes?** The largest factor equals the complete candidate set for every nonempty query; observed maximum is 91.
7. **Enumeration avoided?** None on Census: structural reduction is exactly 0 bits and ratio 1.
8. **Next direction?** The evidence does not justify factorized exact/DP representation as the primary route. Semantic components may still help incremental evaluation on workloads or restricted candidate universes that actually split, but Census requires returning to semantics-guided incremental search rather than factor-table DP.

## Per-query headline table

| query | candidates | dependency edges | factors | max factor size | full log2 configs | factorized log2 enumeration | exact reconstruction? | max relative error | subsets checked | bitwise exact | tolerance exact | divergent |
|---|---:|---:|---:|---:|---:|---:|:---:|---:|---:|---:|---:|---:|
| query.1 | 15 | 60 | 1 | 15 | 15.000 | 15.000 | yes | 3.245e-16 | 32768 | 17128 | 15640 | 0 |
| query.2 | 15 | 60 | 1 | 15 | 15.000 | 15.000 | yes | 1.874e-16 | 32768 | 23327 | 9441 | 0 |
| query.3 | 28 | 168 | 1 | 28 | 28.000 | 28.000 | yes | 2.753e-16 | 4096 | 2601 | 1495 | 0 |
| query.4 | 10 | 30 | 1 | 10 | 10.000 | 10.000 | yes | 1.849e-16 | 1024 | 792 | 232 | 0 |
| query.5 | 28 | 168 | 1 | 28 | 28.000 | 28.000 | yes | 3.160e-16 | 4096 | 1712 | 2384 | 0 |
| query.6 | 21 | 105 | 1 | 21 | 21.000 | 21.000 | yes | 2.835e-16 | 4096 | 2542 | 1554 | 0 |
| query.7 | 45 | 360 | 1 | 45 | 45.000 | 45.000 | yes | 6.111e-16 | 4096 | 2347 | 1749 | 0 |
| query.8 | 6 | 12 | 1 | 6 | 6.000 | 6.000 | yes | 1.417e-16 | 64 | 62 | 2 | 0 |
| query.9 | 6 | 12 | 1 | 6 | 6.000 | 6.000 | yes | 0.000e+00 | 64 | 64 | 0 | 0 |
| query.10 | 45 | 360 | 1 | 45 | 45.000 | 45.000 | yes | 4.439e-16 | 4096 | 1960 | 2136 | 0 |
| query.11 | 45 | 360 | 1 | 45 | 45.000 | 45.000 | yes | 4.833e-16 | 4096 | 1881 | 2215 | 0 |
| query.12 | 10 | 30 | 1 | 10 | 10.000 | 10.000 | yes | 1.280e-16 | 1024 | 522 | 502 | 0 |
| query.13 | 36 | 252 | 1 | 36 | 36.000 | 36.000 | yes | 3.761e-16 | 4096 | 2382 | 1714 | 0 |
| query.14 | 3 | 3 | 1 | 3 | 3.000 | 3.000 | yes | 0.000e+00 | 8 | 8 | 0 | 0 |
| query.15 | 15 | 60 | 1 | 15 | 15.000 | 15.000 | yes | 2.209e-16 | 32768 | 19240 | 13528 | 0 |
| query.16 | 21 | 105 | 1 | 21 | 21.000 | 21.000 | yes | 4.322e-16 | 4096 | 2079 | 2017 | 0 |
| query.17 | 28 | 168 | 1 | 28 | 28.000 | 28.000 | yes | 5.927e-16 | 4096 | 2104 | 1992 | 0 |
| query.18 | 15 | 60 | 1 | 15 | 15.000 | 15.000 | yes | 1.860e-16 | 32768 | 26199 | 6569 | 0 |
| query.19 | 21 | 105 | 1 | 21 | 21.000 | 21.000 | yes | 2.968e-16 | 4096 | 2312 | 1784 | 0 |
| query.20 | 15 | 60 | 1 | 15 | 15.000 | 15.000 | yes | 2.509e-16 | 32768 | 13738 | 19030 | 0 |
| query.21 | 21 | 105 | 1 | 21 | 21.000 | 21.000 | yes | 1.784e-16 | 4096 | 3008 | 1088 | 0 |
| query.22 | 28 | 168 | 1 | 28 | 28.000 | 28.000 | yes | 3.388e-16 | 4096 | 1635 | 2461 | 0 |
| query.23 | 21 | 105 | 1 | 21 | 21.000 | 21.000 | yes | 2.505e-16 | 4096 | 1373 | 2723 | 0 |
| query.24 | 36 | 252 | 1 | 36 | 36.000 | 36.000 | yes | 3.892e-16 | 4096 | 1814 | 2282 | 0 |
| query.25 | 15 | 60 | 1 | 15 | 15.000 | 15.000 | yes | 2.221e-16 | 32768 | 20496 | 12272 | 0 |
| query.26 | 1 | 0 | 1 | 1 | 1.000 | 1.000 | yes | 0.000e+00 | 2 | 2 | 0 | 0 |
| query.27 | 36 | 252 | 1 | 36 | 36.000 | 36.000 | yes | 3.947e-16 | 4096 | 1728 | 2368 | 0 |
| query.28 | 21 | 105 | 1 | 21 | 21.000 | 21.000 | yes | 3.950e-16 | 4096 | 2093 | 2003 | 0 |
| query.29 | 15 | 60 | 1 | 15 | 15.000 | 15.000 | yes | 1.886e-16 | 32768 | 16352 | 16416 | 0 |
| query.30 | 1 | 0 | 1 | 1 | 1.000 | 1.000 | yes | 0.000e+00 | 2 | 2 | 0 | 0 |
| query.31 | 6 | 12 | 1 | 6 | 6.000 | 6.000 | yes | 1.312e-16 | 64 | 59 | 5 | 0 |
| query.32 | 21 | 105 | 1 | 21 | 21.000 | 21.000 | yes | 3.301e-16 | 4096 | 3494 | 602 | 0 |
| query.33 | 6 | 12 | 1 | 6 | 6.000 | 6.000 | yes | 0.000e+00 | 64 | 64 | 0 | 0 |
| query.34 | 28 | 168 | 1 | 28 | 28.000 | 28.000 | yes | 3.942e-16 | 4096 | 2150 | 1946 | 0 |
| query.35 | 15 | 60 | 1 | 15 | 15.000 | 15.000 | yes | 1.427e-16 | 32768 | 26144 | 6624 | 0 |
| query.36 | 21 | 105 | 1 | 21 | 21.000 | 21.000 | yes | 4.421e-16 | 4096 | 2206 | 1890 | 0 |
| query.37 | 6 | 12 | 1 | 6 | 6.000 | 6.000 | yes | 2.059e-16 | 64 | 40 | 24 | 0 |
| query.38 | 15 | 60 | 1 | 15 | 15.000 | 15.000 | yes | 2.137e-16 | 32768 | 28874 | 3894 | 0 |
| query.39 | 3 | 3 | 1 | 3 | 3.000 | 3.000 | yes | 0.000e+00 | 8 | 8 | 0 | 0 |
| query.40 | 6 | 12 | 1 | 6 | 6.000 | 6.000 | yes | 1.465e-16 | 64 | 48 | 16 | 0 |
| query.41 | 15 | 60 | 1 | 15 | 15.000 | 15.000 | yes | 1.901e-16 | 32768 | 21256 | 11512 | 0 |
| query.42 | 55 | 495 | 1 | 55 | 55.000 | 55.000 | yes | 4.843e-16 | 4096 | 1483 | 2613 | 0 |
| query.43 | 15 | 60 | 1 | 15 | 15.000 | 15.000 | yes | 2.447e-16 | 32768 | 13924 | 18844 | 0 |
| query.44 | 15 | 60 | 1 | 15 | 15.000 | 15.000 | yes | 4.240e-16 | 32768 | 16820 | 15948 | 0 |
| query.45 | 3 | 3 | 1 | 3 | 3.000 | 3.000 | yes | 0.000e+00 | 8 | 8 | 0 | 0 |
| query.46 | 36 | 252 | 1 | 36 | 36.000 | 36.000 | yes | 4.033e-16 | 4096 | 1694 | 2402 | 0 |
| query.47 | 10 | 30 | 1 | 10 | 10.000 | 10.000 | yes | 1.434e-16 | 1024 | 760 | 264 | 0 |
| query.48 | 15 | 60 | 1 | 15 | 15.000 | 15.000 | yes | 2.155e-16 | 32768 | 28464 | 4304 | 0 |
| query.49 | 15 | 60 | 1 | 15 | 15.000 | 15.000 | yes | 2.507e-16 | 32768 | 21700 | 11068 | 0 |
| query.50 | 45 | 360 | 1 | 45 | 45.000 | 45.000 | yes | 3.854e-16 | 4096 | 1807 | 2289 | 0 |
| query.51 | 45 | 360 | 1 | 45 | 45.000 | 45.000 | yes | 3.851e-16 | 4096 | 1780 | 2316 | 0 |
| query.52 | 55 | 495 | 1 | 55 | 55.000 | 55.000 | yes | 5.456e-16 | 4096 | 2073 | 2023 | 0 |
| query.53 | 3 | 3 | 1 | 3 | 3.000 | 3.000 | yes | 0.000e+00 | 8 | 8 | 0 | 0 |
| query.54 | 21 | 105 | 1 | 21 | 21.000 | 21.000 | yes | 3.680e-16 | 4096 | 3003 | 1093 | 0 |
| query.55 | 15 | 60 | 1 | 15 | 15.000 | 15.000 | yes | 2.208e-16 | 32768 | 19260 | 13508 | 0 |
| query.56 | 21 | 105 | 1 | 21 | 21.000 | 21.000 | yes | 3.232e-16 | 4096 | 1944 | 2152 | 0 |
| query.57 | 15 | 60 | 1 | 15 | 15.000 | 15.000 | yes | 2.927e-16 | 32768 | 12006 | 20762 | 0 |
| query.58 | 15 | 60 | 1 | 15 | 15.000 | 15.000 | yes | 2.213e-16 | 32768 | 16022 | 16746 | 0 |
| query.59 | 36 | 252 | 1 | 36 | 36.000 | 36.000 | yes | 4.096e-16 | 4096 | 1921 | 2175 | 0 |
| query.60 | 36 | 252 | 1 | 36 | 36.000 | 36.000 | yes | 3.617e-16 | 4096 | 1684 | 2412 | 0 |
| query.61 | 28 | 168 | 1 | 28 | 28.000 | 28.000 | yes | 3.074e-16 | 4096 | 1923 | 2173 | 0 |
| query.62 | 28 | 168 | 1 | 28 | 28.000 | 28.000 | yes | 2.997e-16 | 4096 | 1718 | 2378 | 0 |
| query.63 | 36 | 252 | 1 | 36 | 36.000 | 36.000 | yes | 3.895e-16 | 4096 | 1957 | 2139 | 0 |
| query.64 | 10 | 30 | 1 | 10 | 10.000 | 10.000 | yes | 2.069e-16 | 1024 | 754 | 270 | 0 |
| query.65 | 28 | 168 | 1 | 28 | 28.000 | 28.000 | yes | 3.426e-16 | 4096 | 2186 | 1910 | 0 |
| query.66 | 21 | 105 | 1 | 21 | 21.000 | 21.000 | yes | 2.057e-16 | 4096 | 2433 | 1663 | 0 |
| query.67 | 28 | 168 | 1 | 28 | 28.000 | 28.000 | yes | 2.871e-16 | 4096 | 2110 | 1986 | 0 |
| query.68 | 15 | 60 | 1 | 15 | 15.000 | 15.000 | yes | 2.844e-16 | 32768 | 24730 | 8038 | 0 |
| query.69 | 36 | 252 | 1 | 36 | 36.000 | 36.000 | yes | 3.657e-16 | 4096 | 2097 | 1999 | 0 |
| query.70 | 21 | 105 | 1 | 21 | 21.000 | 21.000 | yes | 1.340e-16 | 4096 | 1605 | 2491 | 0 |
| query.71 | 28 | 168 | 1 | 28 | 28.000 | 28.000 | yes | 3.409e-16 | 4096 | 1548 | 2548 | 0 |
| query.72 | 21 | 105 | 1 | 21 | 21.000 | 21.000 | yes | 2.361e-16 | 4096 | 2800 | 1296 | 0 |
| query.73 | 21 | 105 | 1 | 21 | 21.000 | 21.000 | yes | 2.766e-16 | 4096 | 1921 | 2175 | 0 |
| query.74 | 36 | 252 | 1 | 36 | 36.000 | 36.000 | yes | 4.706e-16 | 4096 | 2262 | 1834 | 0 |
| query.75 | 3 | 3 | 1 | 3 | 3.000 | 3.000 | yes | 0.000e+00 | 8 | 8 | 0 | 0 |
| query.76 | 6 | 12 | 1 | 6 | 6.000 | 6.000 | yes | 1.683e-16 | 64 | 62 | 2 | 0 |
| query.77 | 36 | 252 | 1 | 36 | 36.000 | 36.000 | yes | 3.570e-16 | 4096 | 2502 | 1594 | 0 |
| query.78 | 1 | 0 | 1 | 1 | 1.000 | 1.000 | yes | 0.000e+00 | 2 | 2 | 0 | 0 |
| query.79 | 10 | 30 | 1 | 10 | 10.000 | 10.000 | yes | 2.063e-16 | 1024 | 752 | 272 | 0 |
| query.80 | 21 | 105 | 1 | 21 | 21.000 | 21.000 | yes | 2.367e-16 | 4096 | 2731 | 1365 | 0 |
| query.81 | 21 | 105 | 1 | 21 | 21.000 | 21.000 | yes | 3.758e-16 | 4096 | 2338 | 1758 | 0 |
| query.82 | 36 | 252 | 1 | 36 | 36.000 | 36.000 | yes | 3.611e-16 | 4096 | 2233 | 1863 | 0 |
| query.83 | 3 | 3 | 1 | 3 | 3.000 | 3.000 | yes | 0.000e+00 | 8 | 8 | 0 | 0 |
| query.84 | 10 | 30 | 1 | 10 | 10.000 | 10.000 | yes | 1.531e-16 | 1024 | 968 | 56 | 0 |
| query.85 | 1 | 0 | 1 | 1 | 1.000 | 1.000 | yes | 0.000e+00 | 2 | 2 | 0 | 0 |
| query.86 | 21 | 105 | 1 | 21 | 21.000 | 21.000 | yes | 3.351e-16 | 4096 | 2386 | 1710 | 0 |
| query.87 | 21 | 105 | 1 | 21 | 21.000 | 21.000 | yes | 2.063e-16 | 4096 | 2647 | 1449 | 0 |
| query.88 | 10 | 30 | 1 | 10 | 10.000 | 10.000 | yes | 1.559e-16 | 1024 | 638 | 386 | 0 |
| query.89 | 15 | 60 | 1 | 15 | 15.000 | 15.000 | yes | 2.052e-16 | 32768 | 25694 | 7074 | 0 |
| query.90 | 10 | 30 | 1 | 10 | 10.000 | 10.000 | yes | 2.170e-16 | 1024 | 846 | 178 | 0 |
| query.91 | 45 | 360 | 1 | 45 | 45.000 | 45.000 | yes | 4.421e-16 | 4096 | 2119 | 1977 | 0 |
| query.92 | 6 | 12 | 1 | 6 | 6.000 | 6.000 | yes | 0.000e+00 | 64 | 64 | 0 | 0 |
| query.93 | 6 | 12 | 1 | 6 | 6.000 | 6.000 | yes | 0.000e+00 | 64 | 64 | 0 | 0 |
| query.94 | 21 | 105 | 1 | 21 | 21.000 | 21.000 | yes | 1.930e-16 | 4096 | 2988 | 1108 | 0 |
| query.95 | 21 | 105 | 1 | 21 | 21.000 | 21.000 | yes | 3.155e-16 | 4096 | 2545 | 1551 | 0 |
| query.96 | 28 | 168 | 1 | 28 | 28.000 | 28.000 | yes | 5.666e-16 | 4096 | 1504 | 2592 | 0 |
| query.97 | 36 | 252 | 1 | 36 | 36.000 | 36.000 | yes | 4.350e-16 | 4096 | 1350 | 2746 | 0 |
| query.98 | 15 | 60 | 1 | 15 | 15.000 | 15.000 | yes | 1.464e-16 | 32768 | 21487 | 11281 | 0 |
| query.99 | 36 | 252 | 1 | 36 | 36.000 | 36.000 | yes | 3.487e-16 | 4096 | 2545 | 1551 | 0 |
| query.100 | 10 | 30 | 1 | 10 | 10.000 | 10.000 | yes | 2.069e-16 | 1024 | 356 | 668 | 0 |
| query.101 | 45 | 360 | 1 | 45 | 45.000 | 45.000 | yes | 3.979e-16 | 4096 | 2164 | 1932 | 0 |
| query.102 | 45 | 360 | 1 | 45 | 45.000 | 45.000 | yes | 3.572e-16 | 4096 | 2060 | 2036 | 0 |
| query.103 | 66 | 660 | 1 | 66 | 66.000 | 66.000 | yes | 6.898e-16 | 4096 | 2085 | 2011 | 0 |
| query.104 | 28 | 168 | 1 | 28 | 28.000 | 28.000 | yes | 3.404e-16 | 4096 | 2327 | 1769 | 0 |
| query.105 | 28 | 168 | 1 | 28 | 28.000 | 28.000 | yes | 3.114e-16 | 4096 | 2466 | 1630 | 0 |
| query.106 | 6 | 12 | 1 | 6 | 6.000 | 6.000 | yes | 1.627e-16 | 64 | 60 | 4 | 0 |
| query.107 | 1 | 0 | 1 | 1 | 1.000 | 1.000 | yes | 0.000e+00 | 2 | 2 | 0 | 0 |
| query.108 | 10 | 30 | 1 | 10 | 10.000 | 10.000 | yes | 1.974e-16 | 1024 | 856 | 168 | 0 |
| query.109 | 15 | 60 | 1 | 15 | 15.000 | 15.000 | yes | 1.658e-16 | 32768 | 16811 | 15957 | 0 |
| query.110 | 21 | 105 | 1 | 21 | 21.000 | 21.000 | yes | 2.641e-16 | 4096 | 2516 | 1580 | 0 |
| query.111 | 55 | 495 | 1 | 55 | 55.000 | 55.000 | yes | 4.429e-16 | 4096 | 2061 | 2035 | 0 |
| query.112 | 6 | 12 | 1 | 6 | 6.000 | 6.000 | yes | 1.322e-16 | 64 | 47 | 17 | 0 |
| query.113 | 15 | 60 | 1 | 15 | 15.000 | 15.000 | yes | 1.704e-16 | 32768 | 18398 | 14370 | 0 |
| query.114 | 15 | 60 | 1 | 15 | 15.000 | 15.000 | yes | 2.257e-16 | 32768 | 19428 | 13340 | 0 |
| query.115 | 6 | 12 | 1 | 6 | 6.000 | 6.000 | yes | 0.000e+00 | 64 | 64 | 0 | 0 |
| query.116 | 45 | 360 | 1 | 45 | 45.000 | 45.000 | yes | 4.413e-16 | 4096 | 1635 | 2461 | 0 |
| query.117 | 45 | 360 | 1 | 45 | 45.000 | 45.000 | yes | 4.402e-16 | 4096 | 1980 | 2116 | 0 |
| query.118 | 15 | 60 | 1 | 15 | 15.000 | 15.000 | yes | 3.027e-16 | 32768 | 10936 | 21832 | 0 |
| query.119 | 10 | 30 | 1 | 10 | 10.000 | 10.000 | yes | 1.415e-16 | 1024 | 658 | 366 | 0 |
| query.120 | 21 | 105 | 1 | 21 | 21.000 | 21.000 | yes | 2.606e-16 | 4096 | 1880 | 2216 | 0 |
| query.121 | 36 | 252 | 1 | 36 | 36.000 | 36.000 | yes | 3.330e-16 | 4096 | 1652 | 2444 | 0 |
| query.122 | 28 | 168 | 1 | 28 | 28.000 | 28.000 | yes | 2.841e-16 | 4096 | 1694 | 2402 | 0 |
| query.123 | 28 | 168 | 1 | 28 | 28.000 | 28.000 | yes | 3.253e-16 | 4096 | 1998 | 2098 | 0 |
| query.124 | 15 | 60 | 1 | 15 | 15.000 | 15.000 | yes | 2.155e-16 | 32768 | 21980 | 10788 | 0 |
| query.125 | 10 | 30 | 1 | 10 | 10.000 | 10.000 | yes | 1.552e-16 | 1024 | 848 | 176 | 0 |
| query.126 | 15 | 60 | 1 | 15 | 15.000 | 15.000 | yes | 1.409e-16 | 32768 | 10222 | 22546 | 0 |
| query.127 | 28 | 168 | 1 | 28 | 28.000 | 28.000 | yes | 3.579e-16 | 4096 | 2759 | 1337 | 0 |
| query.128 | 28 | 168 | 1 | 28 | 28.000 | 28.000 | yes | 2.574e-16 | 4096 | 1821 | 2275 | 0 |
| query.129 | 10 | 30 | 1 | 10 | 10.000 | 10.000 | yes | 1.922e-16 | 1024 | 718 | 306 | 0 |
| query.130 | 21 | 105 | 1 | 21 | 21.000 | 21.000 | yes | 2.000e-16 | 4096 | 2655 | 1441 | 0 |
| query.131 | 3 | 3 | 1 | 3 | 3.000 | 3.000 | yes | 0.000e+00 | 8 | 8 | 0 | 0 |
| query.132 | 10 | 30 | 1 | 10 | 10.000 | 10.000 | yes | 2.114e-16 | 1024 | 796 | 228 | 0 |
| query.133 | 10 | 30 | 1 | 10 | 10.000 | 10.000 | yes | 1.710e-16 | 1024 | 934 | 90 | 0 |
| query.134 | 45 | 360 | 1 | 45 | 45.000 | 45.000 | yes | 3.799e-16 | 4096 | 2521 | 1575 | 0 |
| query.135 | 28 | 168 | 1 | 28 | 28.000 | 28.000 | yes | 3.586e-16 | 4096 | 2242 | 1854 | 0 |
| query.136 | 15 | 60 | 1 | 15 | 15.000 | 15.000 | yes | 1.302e-16 | 32768 | 19724 | 13044 | 0 |
| query.137 | 10 | 30 | 1 | 10 | 10.000 | 10.000 | yes | 1.960e-16 | 1024 | 616 | 408 | 0 |
| query.138 | 36 | 252 | 1 | 36 | 36.000 | 36.000 | yes | 4.421e-16 | 4096 | 2350 | 1746 | 0 |
| query.139 | 3 | 3 | 1 | 3 | 3.000 | 3.000 | yes | 0.000e+00 | 8 | 8 | 0 | 0 |
| query.140 | 28 | 168 | 1 | 28 | 28.000 | 28.000 | yes | 3.710e-16 | 4096 | 3006 | 1090 | 0 |
| query.141 | 28 | 168 | 1 | 28 | 28.000 | 28.000 | yes | 4.082e-16 | 4096 | 1911 | 2185 | 0 |
| query.142 | 28 | 168 | 1 | 28 | 28.000 | 28.000 | yes | 2.629e-16 | 4096 | 2114 | 1982 | 0 |
| query.143 | 28 | 168 | 1 | 28 | 28.000 | 28.000 | yes | 3.598e-16 | 4096 | 2000 | 2096 | 0 |
| query.144 | 36 | 252 | 1 | 36 | 36.000 | 36.000 | yes | 3.735e-16 | 4096 | 2320 | 1776 | 0 |
| query.145 | 6 | 12 | 1 | 6 | 6.000 | 6.000 | yes | 1.457e-16 | 64 | 44 | 20 | 0 |
| query.146 | 1 | 0 | 1 | 1 | 1.000 | 1.000 | yes | 0.000e+00 | 2 | 2 | 0 | 0 |
| query.147 | 28 | 168 | 1 | 28 | 28.000 | 28.000 | yes | 4.037e-16 | 4096 | 2484 | 1612 | 0 |
| query.148 | 3 | 3 | 1 | 3 | 3.000 | 3.000 | yes | 0.000e+00 | 8 | 8 | 0 | 0 |
| query.149 | 21 | 105 | 1 | 21 | 21.000 | 21.000 | yes | 2.177e-16 | 4096 | 2364 | 1732 | 0 |
| query.150 | 36 | 252 | 1 | 36 | 36.000 | 36.000 | yes | 4.132e-16 | 4096 | 1931 | 2165 | 0 |
| query.151 | 10 | 30 | 1 | 10 | 10.000 | 10.000 | yes | 1.991e-16 | 1024 | 816 | 208 | 0 |
| query.152 | 10 | 30 | 1 | 10 | 10.000 | 10.000 | yes | 1.938e-16 | 1024 | 518 | 506 | 0 |
| query.153 | 6 | 12 | 1 | 6 | 6.000 | 6.000 | yes | 1.140e-16 | 64 | 60 | 4 | 0 |
| query.154 | 15 | 60 | 1 | 15 | 15.000 | 15.000 | yes | 2.155e-16 | 32768 | 29408 | 3360 | 0 |
| query.155 | 6 | 12 | 1 | 6 | 6.000 | 6.000 | yes | 1.326e-16 | 64 | 48 | 16 | 0 |
| query.156 | 36 | 252 | 1 | 36 | 36.000 | 36.000 | yes | 4.083e-16 | 4096 | 1540 | 2556 | 0 |
| query.157 | 6 | 12 | 1 | 6 | 6.000 | 6.000 | yes | 1.999e-16 | 64 | 56 | 8 | 0 |
| query.158 | 45 | 360 | 1 | 45 | 45.000 | 45.000 | yes | 4.557e-16 | 4096 | 1558 | 2538 | 0 |
| query.159 | 78 | 858 | 1 | 78 | 78.000 | 78.000 | yes | 6.276e-16 | 4096 | 1413 | 2683 | 0 |
| query.160 | 28 | 168 | 1 | 28 | 28.000 | 28.000 | yes | 3.949e-16 | 4096 | 1664 | 2432 | 0 |
| query.161 | 15 | 60 | 1 | 15 | 15.000 | 15.000 | yes | 2.687e-16 | 32768 | 18856 | 13912 | 0 |
| query.162 | 28 | 168 | 1 | 28 | 28.000 | 28.000 | yes | 3.407e-16 | 4096 | 1766 | 2330 | 0 |
| query.163 | 36 | 252 | 1 | 36 | 36.000 | 36.000 | yes | 4.380e-16 | 4096 | 1362 | 2734 | 0 |
| query.164 | 10 | 30 | 1 | 10 | 10.000 | 10.000 | yes | 1.882e-16 | 1024 | 664 | 360 | 0 |
| query.165 | 6 | 12 | 1 | 6 | 6.000 | 6.000 | yes | 1.506e-16 | 64 | 44 | 20 | 0 |
| query.166 | 15 | 60 | 1 | 15 | 15.000 | 15.000 | yes | 1.812e-16 | 32768 | 26634 | 6134 | 0 |
| query.167 | 28 | 168 | 1 | 28 | 28.000 | 28.000 | yes | 4.205e-16 | 4096 | 2050 | 2046 | 0 |
| query.168 | 15 | 60 | 1 | 15 | 15.000 | 15.000 | yes | 1.438e-16 | 32768 | 10422 | 22346 | 0 |
| query.169 | 10 | 30 | 1 | 10 | 10.000 | 10.000 | yes | 1.310e-16 | 1024 | 824 | 200 | 0 |
| query.170 | 28 | 168 | 1 | 28 | 28.000 | 28.000 | yes | 3.814e-16 | 4096 | 1723 | 2373 | 0 |
| query.171 | 6 | 12 | 1 | 6 | 6.000 | 6.000 | yes | 1.355e-16 | 64 | 56 | 8 | 0 |
| query.172 | 1 | 0 | 1 | 1 | 1.000 | 1.000 | yes | 0.000e+00 | 2 | 2 | 0 | 0 |
| query.173 | 28 | 168 | 1 | 28 | 28.000 | 28.000 | yes | 3.603e-16 | 4096 | 2517 | 1579 | 0 |
| query.174 | 6 | 12 | 1 | 6 | 6.000 | 6.000 | yes | 0.000e+00 | 64 | 64 | 0 | 0 |
| query.175 | 21 | 105 | 1 | 21 | 21.000 | 21.000 | yes | 1.567e-16 | 4096 | 2090 | 2006 | 0 |
| query.176 | 21 | 105 | 1 | 21 | 21.000 | 21.000 | yes | 2.156e-16 | 4096 | 2054 | 2042 | 0 |
| query.177 | 6 | 12 | 1 | 6 | 6.000 | 6.000 | yes | 1.505e-16 | 64 | 48 | 16 | 0 |
| query.178 | 3 | 3 | 1 | 3 | 3.000 | 3.000 | yes | 0.000e+00 | 8 | 8 | 0 | 0 |
| query.179 | 15 | 60 | 1 | 15 | 15.000 | 15.000 | yes | 2.552e-16 | 32768 | 21630 | 11138 | 0 |
| query.180 | 66 | 660 | 1 | 66 | 66.000 | 66.000 | yes | 4.590e-16 | 4096 | 1567 | 2529 | 0 |
| query.181 | 15 | 60 | 1 | 15 | 15.000 | 15.000 | yes | 3.454e-16 | 32768 | 14224 | 18544 | 0 |
| query.182 | 1 | 0 | 1 | 1 | 1.000 | 1.000 | yes | 0.000e+00 | 2 | 2 | 0 | 0 |
| query.183 | 28 | 168 | 1 | 28 | 28.000 | 28.000 | yes | 2.189e-16 | 4096 | 3116 | 980 | 0 |
| query.184 | 45 | 360 | 1 | 45 | 45.000 | 45.000 | yes | 4.182e-16 | 4096 | 1971 | 2125 | 0 |
| query.185 | 3 | 3 | 1 | 3 | 3.000 | 3.000 | yes | 0.000e+00 | 8 | 8 | 0 | 0 |
| query.186 | 15 | 60 | 1 | 15 | 15.000 | 15.000 | yes | 2.330e-16 | 32768 | 19630 | 13138 | 0 |
| query.187 | 28 | 168 | 1 | 28 | 28.000 | 28.000 | yes | 4.266e-16 | 4096 | 2312 | 1784 | 0 |
| query.188 | 10 | 30 | 1 | 10 | 10.000 | 10.000 | yes | 2.104e-16 | 1024 | 662 | 362 | 0 |
| query.189 | 1 | 0 | 1 | 1 | 1.000 | 1.000 | yes | 0.000e+00 | 2 | 2 | 0 | 0 |
| query.190 | 6 | 12 | 1 | 6 | 6.000 | 6.000 | yes | 1.674e-16 | 64 | 40 | 24 | 0 |
| query.191 | 10 | 30 | 1 | 10 | 10.000 | 10.000 | yes | 1.410e-16 | 1024 | 832 | 192 | 0 |
| query.192 | 10 | 30 | 1 | 10 | 10.000 | 10.000 | yes | 1.684e-16 | 1024 | 831 | 193 | 0 |
| query.193 | 15 | 60 | 1 | 15 | 15.000 | 15.000 | yes | 2.423e-16 | 32768 | 23397 | 9371 | 0 |
| query.194 | 28 | 168 | 1 | 28 | 28.000 | 28.000 | yes | 4.350e-16 | 4096 | 2028 | 2068 | 0 |
| query.195 | 78 | 858 | 1 | 78 | 78.000 | 78.000 | yes | 6.043e-16 | 4096 | 1281 | 2815 | 0 |
| query.196 | 45 | 360 | 1 | 45 | 45.000 | 45.000 | yes | 4.416e-16 | 4096 | 2267 | 1829 | 0 |
| query.197 | 10 | 30 | 1 | 10 | 10.000 | 10.000 | yes | 1.241e-16 | 1024 | 998 | 26 | 0 |
| query.198 | 6 | 12 | 1 | 6 | 6.000 | 6.000 | yes | 2.042e-16 | 64 | 60 | 4 | 0 |
| query.199 | 28 | 168 | 1 | 28 | 28.000 | 28.000 | yes | 3.469e-16 | 4096 | 2097 | 1999 | 0 |
| query.200 | 6 | 12 | 1 | 6 | 6.000 | 6.000 | yes | 0.000e+00 | 64 | 64 | 0 | 0 |
| query.201 | 21 | 105 | 1 | 21 | 21.000 | 21.000 | yes | 2.867e-16 | 4096 | 1973 | 2123 | 0 |
| query.202 | 10 | 30 | 1 | 10 | 10.000 | 10.000 | yes | 2.115e-16 | 1024 | 568 | 456 | 0 |
| query.203 | 55 | 495 | 1 | 55 | 55.000 | 55.000 | yes | 3.357e-16 | 4096 | 1677 | 2419 | 0 |
| query.204 | 15 | 60 | 1 | 15 | 15.000 | 15.000 | yes | 2.579e-16 | 32768 | 24490 | 8278 | 0 |
| query.205 | 21 | 105 | 1 | 21 | 21.000 | 21.000 | yes | 3.356e-16 | 4096 | 1859 | 2237 | 0 |
| query.206 | 21 | 105 | 1 | 21 | 21.000 | 21.000 | yes | 2.302e-16 | 4096 | 2825 | 1271 | 0 |
| query.207 | 6 | 12 | 1 | 6 | 6.000 | 6.000 | yes | 0.000e+00 | 64 | 64 | 0 | 0 |
| query.208 | 10 | 30 | 1 | 10 | 10.000 | 10.000 | yes | 1.560e-16 | 1024 | 952 | 72 | 0 |
| query.209 | 28 | 168 | 1 | 28 | 28.000 | 28.000 | yes | 3.794e-16 | 4096 | 2407 | 1689 | 0 |
| query.210 | 6 | 12 | 1 | 6 | 6.000 | 6.000 | yes | 0.000e+00 | 64 | 64 | 0 | 0 |
| query.211 | 21 | 105 | 1 | 21 | 21.000 | 21.000 | yes | 2.316e-16 | 4096 | 2480 | 1616 | 0 |
| query.212 | 3 | 3 | 1 | 3 | 3.000 | 3.000 | yes | 0.000e+00 | 8 | 8 | 0 | 0 |
| query.213 | 6 | 12 | 1 | 6 | 6.000 | 6.000 | yes | 1.387e-16 | 64 | 44 | 20 | 0 |
| query.214 | 6 | 12 | 1 | 6 | 6.000 | 6.000 | yes | 1.474e-16 | 64 | 62 | 2 | 0 |
| query.215 | 15 | 60 | 1 | 15 | 15.000 | 15.000 | yes | 1.987e-16 | 32768 | 11174 | 21594 | 0 |
| query.216 | 10 | 30 | 1 | 10 | 10.000 | 10.000 | yes | 1.994e-16 | 1024 | 820 | 204 | 0 |
| query.217 | 10 | 30 | 1 | 10 | 10.000 | 10.000 | yes | 1.508e-16 | 1024 | 428 | 596 | 0 |
| query.218 | 21 | 105 | 1 | 21 | 21.000 | 21.000 | yes | 2.169e-16 | 4096 | 2439 | 1657 | 0 |
| query.219 | 10 | 30 | 1 | 10 | 10.000 | 10.000 | yes | 2.150e-16 | 1024 | 734 | 290 | 0 |
| query.220 | 21 | 105 | 1 | 21 | 21.000 | 21.000 | yes | 3.015e-16 | 4096 | 1570 | 2526 | 0 |
| query.221 | 3 | 3 | 1 | 3 | 3.000 | 3.000 | yes | 0.000e+00 | 8 | 8 | 0 | 0 |
| query.222 | 6 | 12 | 1 | 6 | 6.000 | 6.000 | yes | 1.512e-16 | 64 | 40 | 24 | 0 |
| query.223 | 28 | 168 | 1 | 28 | 28.000 | 28.000 | yes | 3.891e-16 | 4096 | 2110 | 1986 | 0 |
| query.224 | 28 | 168 | 1 | 28 | 28.000 | 28.000 | yes | 3.564e-16 | 4096 | 2402 | 1694 | 0 |
| query.225 | 6 | 12 | 1 | 6 | 6.000 | 6.000 | yes | 0.000e+00 | 64 | 64 | 0 | 0 |
| query.226 | 10 | 30 | 1 | 10 | 10.000 | 10.000 | yes | 1.611e-16 | 1024 | 940 | 84 | 0 |
| query.227 | 10 | 30 | 1 | 10 | 10.000 | 10.000 | yes | 2.042e-16 | 1024 | 526 | 498 | 0 |
| query.228 | 10 | 30 | 1 | 10 | 10.000 | 10.000 | yes | 0.000e+00 | 1024 | 1024 | 0 | 0 |
| query.229 | 21 | 105 | 1 | 21 | 21.000 | 21.000 | yes | 4.371e-16 | 4096 | 1363 | 2733 | 0 |
| query.230 | 6 | 12 | 1 | 6 | 6.000 | 6.000 | yes | 0.000e+00 | 64 | 64 | 0 | 0 |
| query.231 | 21 | 105 | 1 | 21 | 21.000 | 21.000 | yes | 2.970e-16 | 4096 | 2700 | 1396 | 0 |
| query.232 | 21 | 105 | 1 | 21 | 21.000 | 21.000 | yes | 2.833e-16 | 4096 | 2398 | 1698 | 0 |
| query.233 | 21 | 105 | 1 | 21 | 21.000 | 21.000 | yes | 2.369e-16 | 4096 | 1072 | 3024 | 0 |
| query.234 | 3 | 3 | 1 | 3 | 3.000 | 3.000 | yes | 0.000e+00 | 8 | 8 | 0 | 0 |
| query.235 | 28 | 168 | 1 | 28 | 28.000 | 28.000 | yes | 3.497e-16 | 4096 | 1570 | 2526 | 0 |
| query.236 | 28 | 168 | 1 | 28 | 28.000 | 28.000 | yes | 4.185e-16 | 4096 | 2552 | 1544 | 0 |
| query.237 | 10 | 30 | 1 | 10 | 10.000 | 10.000 | yes | 1.769e-16 | 1024 | 1023 | 1 | 0 |
| query.238 | 21 | 105 | 1 | 21 | 21.000 | 21.000 | yes | 3.255e-16 | 4096 | 2982 | 1114 | 0 |
| query.239 | 3 | 3 | 1 | 3 | 3.000 | 3.000 | yes | 0.000e+00 | 8 | 8 | 0 | 0 |
| query.240 | 6 | 12 | 1 | 6 | 6.000 | 6.000 | yes | 2.022e-16 | 64 | 48 | 16 | 0 |
| query.241 | 6 | 12 | 1 | 6 | 6.000 | 6.000 | yes | 0.000e+00 | 64 | 64 | 0 | 0 |
| query.242 | 10 | 30 | 1 | 10 | 10.000 | 10.000 | yes | 2.133e-16 | 1024 | 884 | 140 | 0 |
| query.243 | 28 | 168 | 1 | 28 | 28.000 | 28.000 | yes | 4.384e-16 | 4096 | 2202 | 1894 | 0 |
| query.244 | 45 | 360 | 1 | 45 | 45.000 | 45.000 | yes | 4.356e-16 | 4096 | 2491 | 1605 | 0 |
| query.245 | 28 | 168 | 1 | 28 | 28.000 | 28.000 | yes | 3.245e-16 | 4096 | 1928 | 2168 | 0 |
| query.246 | 55 | 495 | 1 | 55 | 55.000 | 55.000 | yes | 5.613e-16 | 4096 | 2042 | 2054 | 0 |
| query.247 | 10 | 30 | 1 | 10 | 10.000 | 10.000 | yes | 1.758e-16 | 1024 | 438 | 586 | 0 |
| query.248 | 6 | 12 | 1 | 6 | 6.000 | 6.000 | yes | 1.967e-16 | 64 | 52 | 12 | 0 |
| query.249 | 10 | 30 | 1 | 10 | 10.000 | 10.000 | yes | 2.142e-16 | 1024 | 980 | 44 | 0 |
| query.250 | 10 | 30 | 1 | 10 | 10.000 | 10.000 | yes | 1.183e-16 | 1024 | 718 | 306 | 0 |
| query.251 | 21 | 105 | 1 | 21 | 21.000 | 21.000 | yes | 2.662e-16 | 4096 | 2507 | 1589 | 0 |
| query.252 | 15 | 60 | 1 | 15 | 15.000 | 15.000 | yes | 3.730e-16 | 32768 | 25568 | 7200 | 0 |
| query.253 | 36 | 252 | 1 | 36 | 36.000 | 36.000 | yes | 4.205e-16 | 4096 | 2571 | 1525 | 0 |
| query.254 | 21 | 105 | 1 | 21 | 21.000 | 21.000 | yes | 3.260e-16 | 4096 | 1722 | 2374 | 0 |
| query.255 | 15 | 60 | 1 | 15 | 15.000 | 15.000 | yes | 2.168e-16 | 32768 | 23031 | 9737 | 0 |
| query.256 | 6 | 12 | 1 | 6 | 6.000 | 6.000 | yes | 1.439e-16 | 64 | 52 | 12 | 0 |
| query.257 | 10 | 30 | 1 | 10 | 10.000 | 10.000 | yes | 1.133e-16 | 1024 | 1022 | 2 | 0 |
| query.258 | 28 | 168 | 1 | 28 | 28.000 | 28.000 | yes | 2.614e-16 | 4096 | 2390 | 1706 | 0 |
| query.259 | 28 | 168 | 1 | 28 | 28.000 | 28.000 | yes | 3.384e-16 | 4096 | 2164 | 1932 | 0 |
| query.260 | 3 | 3 | 1 | 3 | 3.000 | 3.000 | yes | 0.000e+00 | 8 | 8 | 0 | 0 |
| query.261 | 3 | 3 | 1 | 3 | 3.000 | 3.000 | yes | 0.000e+00 | 8 | 8 | 0 | 0 |
| query.262 | 21 | 105 | 1 | 21 | 21.000 | 21.000 | yes | 2.271e-16 | 4096 | 1950 | 2146 | 0 |
| query.263 | 28 | 168 | 1 | 28 | 28.000 | 28.000 | yes | 4.024e-16 | 4096 | 1839 | 2257 | 0 |
| query.264 | 15 | 60 | 1 | 15 | 15.000 | 15.000 | yes | 2.429e-16 | 32768 | 24085 | 8683 | 0 |
| query.265 | 21 | 105 | 1 | 21 | 21.000 | 21.000 | yes | 1.949e-16 | 4096 | 2492 | 1604 | 0 |
| query.266 | 15 | 60 | 1 | 15 | 15.000 | 15.000 | yes | 2.611e-16 | 32768 | 24874 | 7894 | 0 |
| query.267 | 36 | 252 | 1 | 36 | 36.000 | 36.000 | yes | 4.326e-16 | 4096 | 1686 | 2410 | 0 |
| query.268 | 3 | 3 | 1 | 3 | 3.000 | 3.000 | yes | 0.000e+00 | 8 | 8 | 0 | 0 |
| query.269 | 45 | 360 | 1 | 45 | 45.000 | 45.000 | yes | 4.431e-16 | 4096 | 1509 | 2587 | 0 |
| query.270 | 10 | 30 | 1 | 10 | 10.000 | 10.000 | yes | 2.046e-16 | 1024 | 733 | 291 | 0 |
| query.271 | 21 | 105 | 1 | 21 | 21.000 | 21.000 | yes | 2.239e-16 | 4096 | 2161 | 1935 | 0 |
| query.272 | 10 | 30 | 1 | 10 | 10.000 | 10.000 | yes | 1.972e-16 | 1024 | 848 | 176 | 0 |
| query.273 | 45 | 360 | 1 | 45 | 45.000 | 45.000 | yes | 5.089e-16 | 4096 | 1615 | 2481 | 0 |
| query.274 | 78 | 858 | 1 | 78 | 78.000 | 78.000 | yes | 6.316e-16 | 4096 | 1761 | 2335 | 0 |
| query.275 | 28 | 168 | 1 | 28 | 28.000 | 28.000 | yes | 3.839e-16 | 4096 | 1896 | 2200 | 0 |
| query.276 | 6 | 12 | 1 | 6 | 6.000 | 6.000 | yes | 1.640e-16 | 64 | 48 | 16 | 0 |
| query.277 | 21 | 105 | 1 | 21 | 21.000 | 21.000 | yes | 3.691e-16 | 4096 | 3250 | 846 | 0 |
| query.278 | 10 | 30 | 1 | 10 | 10.000 | 10.000 | yes | 1.343e-16 | 1024 | 598 | 426 | 0 |
| query.279 | 15 | 60 | 1 | 15 | 15.000 | 15.000 | yes | 2.110e-16 | 32768 | 22708 | 10060 | 0 |
| query.280 | 15 | 60 | 1 | 15 | 15.000 | 15.000 | yes | 1.888e-16 | 32768 | 28588 | 4180 | 0 |
| query.281 | 28 | 168 | 1 | 28 | 28.000 | 28.000 | yes | 4.080e-16 | 4096 | 2167 | 1929 | 0 |
| query.282 | 28 | 168 | 1 | 28 | 28.000 | 28.000 | yes | 3.495e-16 | 4096 | 3072 | 1024 | 0 |
| query.283 | 21 | 105 | 1 | 21 | 21.000 | 21.000 | yes | 2.733e-16 | 4096 | 3216 | 880 | 0 |
| query.284 | 15 | 60 | 1 | 15 | 15.000 | 15.000 | yes | 2.025e-16 | 32768 | 18857 | 13911 | 0 |
| query.285 | 66 | 660 | 1 | 66 | 66.000 | 66.000 | yes | 6.183e-16 | 4096 | 1200 | 2896 | 0 |
| query.286 | 10 | 30 | 1 | 10 | 10.000 | 10.000 | yes | 1.326e-16 | 1024 | 638 | 386 | 0 |
| query.287 | 10 | 30 | 1 | 10 | 10.000 | 10.000 | yes | 2.122e-16 | 1024 | 608 | 416 | 0 |
| query.288 | 15 | 60 | 1 | 15 | 15.000 | 15.000 | yes | 2.079e-16 | 32768 | 26644 | 6124 | 0 |
| query.289 | 21 | 105 | 1 | 21 | 21.000 | 21.000 | yes | 2.690e-16 | 4096 | 2471 | 1625 | 0 |
| query.290 | 45 | 360 | 1 | 45 | 45.000 | 45.000 | yes | 6.061e-16 | 4096 | 1924 | 2172 | 0 |
| query.291 | 10 | 30 | 1 | 10 | 10.000 | 10.000 | yes | 2.219e-16 | 1024 | 824 | 200 | 0 |
| query.292 | 3 | 3 | 1 | 3 | 3.000 | 3.000 | yes | 0.000e+00 | 8 | 8 | 0 | 0 |
| query.293 | 36 | 252 | 1 | 36 | 36.000 | 36.000 | yes | 3.966e-16 | 4096 | 1925 | 2171 | 0 |
| query.294 | 15 | 60 | 1 | 15 | 15.000 | 15.000 | yes | 2.210e-16 | 32768 | 26584 | 6184 | 0 |
| query.295 | 15 | 60 | 1 | 15 | 15.000 | 15.000 | yes | 4.397e-16 | 32768 | 22688 | 10080 | 0 |
| query.296 | 6 | 12 | 1 | 6 | 6.000 | 6.000 | yes | 0.000e+00 | 64 | 64 | 0 | 0 |
| query.297 | 36 | 252 | 1 | 36 | 36.000 | 36.000 | yes | 3.772e-16 | 4096 | 2497 | 1599 | 0 |
| query.298 | 15 | 60 | 1 | 15 | 15.000 | 15.000 | yes | 2.017e-16 | 32768 | 24806 | 7962 | 0 |
| query.299 | 15 | 60 | 1 | 15 | 15.000 | 15.000 | yes | 2.592e-16 | 32768 | 25580 | 7188 | 0 |
| query.300 | 21 | 105 | 1 | 21 | 21.000 | 21.000 | yes | 3.086e-16 | 4096 | 2388 | 1708 | 0 |
| query.301 | 45 | 360 | 1 | 45 | 45.000 | 45.000 | yes | 3.958e-16 | 4096 | 1749 | 2347 | 0 |
| query.302 | 3 | 3 | 1 | 3 | 3.000 | 3.000 | yes | 0.000e+00 | 8 | 8 | 0 | 0 |
| query.303 | 28 | 168 | 1 | 28 | 28.000 | 28.000 | yes | 3.459e-16 | 4096 | 2230 | 1866 | 0 |
| query.304 | 10 | 30 | 1 | 10 | 10.000 | 10.000 | yes | 1.309e-16 | 1024 | 812 | 212 | 0 |
| query.305 | 15 | 60 | 1 | 15 | 15.000 | 15.000 | yes | 1.394e-16 | 32768 | 24686 | 8082 | 0 |
| query.306 | 3 | 3 | 1 | 3 | 3.000 | 3.000 | yes | 0.000e+00 | 8 | 8 | 0 | 0 |
| query.307 | 55 | 495 | 1 | 55 | 55.000 | 55.000 | yes | 3.651e-16 | 4096 | 1550 | 2546 | 0 |
| query.308 | 28 | 168 | 1 | 28 | 28.000 | 28.000 | yes | 4.412e-16 | 4096 | 2014 | 2082 | 0 |
| query.309 | 10 | 30 | 1 | 10 | 10.000 | 10.000 | yes | 1.519e-16 | 1024 | 600 | 424 | 0 |
| query.310 | 45 | 360 | 1 | 45 | 45.000 | 45.000 | yes | 3.716e-16 | 4096 | 2108 | 1988 | 0 |
| query.311 | 21 | 105 | 1 | 21 | 21.000 | 21.000 | yes | 3.236e-16 | 4096 | 1789 | 2307 | 0 |
| query.312 | 6 | 12 | 1 | 6 | 6.000 | 6.000 | yes | 2.087e-16 | 64 | 56 | 8 | 0 |
| query.313 | 3 | 3 | 1 | 3 | 3.000 | 3.000 | yes | 0.000e+00 | 8 | 8 | 0 | 0 |
| query.314 | 15 | 60 | 1 | 15 | 15.000 | 15.000 | yes | 1.860e-16 | 32768 | 18246 | 14522 | 0 |
| query.315 | 6 | 12 | 1 | 6 | 6.000 | 6.000 | yes | 1.795e-16 | 64 | 56 | 8 | 0 |
| query.316 | 6 | 12 | 1 | 6 | 6.000 | 6.000 | yes | 1.540e-16 | 64 | 56 | 8 | 0 |
| query.317 | 6 | 12 | 1 | 6 | 6.000 | 6.000 | yes | 1.797e-16 | 64 | 48 | 16 | 0 |
| query.318 | 36 | 252 | 1 | 36 | 36.000 | 36.000 | yes | 5.198e-16 | 4096 | 1464 | 2632 | 0 |
| query.319 | 3 | 3 | 1 | 3 | 3.000 | 3.000 | yes | 0.000e+00 | 8 | 8 | 0 | 0 |
| query.320 | 21 | 105 | 1 | 21 | 21.000 | 21.000 | yes | 2.230e-16 | 4096 | 1971 | 2125 | 0 |
| query.321 | 28 | 168 | 1 | 28 | 28.000 | 28.000 | yes | 3.842e-16 | 4096 | 2432 | 1664 | 0 |
| query.322 | 10 | 30 | 1 | 10 | 10.000 | 10.000 | yes | 1.845e-16 | 1024 | 515 | 509 | 0 |
| query.323 | 0 | 0 | 0 | 0 | 0.000 | 0.000 | yes | 0.000e+00 | 1 | 1 | 0 | 0 |
| query.324 | 15 | 60 | 1 | 15 | 15.000 | 15.000 | yes | 1.403e-16 | 32768 | 25116 | 7652 | 0 |
| query.325 | 10 | 30 | 1 | 10 | 10.000 | 10.000 | yes | 1.731e-16 | 1024 | 602 | 422 | 0 |
| query.326 | 28 | 168 | 1 | 28 | 28.000 | 28.000 | yes | 2.175e-16 | 4096 | 2414 | 1682 | 0 |
| query.327 | 6 | 12 | 1 | 6 | 6.000 | 6.000 | yes | 1.403e-16 | 64 | 56 | 8 | 0 |
| query.328 | 21 | 105 | 1 | 21 | 21.000 | 21.000 | yes | 1.977e-16 | 4096 | 2472 | 1624 | 0 |
| query.329 | 45 | 360 | 1 | 45 | 45.000 | 45.000 | yes | 4.378e-16 | 4096 | 2240 | 1856 | 0 |
| query.330 | 36 | 252 | 1 | 36 | 36.000 | 36.000 | yes | 4.413e-16 | 4096 | 1879 | 2217 | 0 |
| query.331 | 21 | 105 | 1 | 21 | 21.000 | 21.000 | yes | 2.996e-16 | 4096 | 2306 | 1790 | 0 |
| query.332 | 36 | 252 | 1 | 36 | 36.000 | 36.000 | yes | 3.803e-16 | 4096 | 1993 | 2103 | 0 |
| query.333 | 3 | 3 | 1 | 3 | 3.000 | 3.000 | yes | 0.000e+00 | 8 | 8 | 0 | 0 |
| query.334 | 15 | 60 | 1 | 15 | 15.000 | 15.000 | yes | 1.959e-16 | 32768 | 13560 | 19208 | 0 |
| query.335 | 91 | 1092 | 1 | 91 | 91.000 | 91.000 | yes | 5.867e-16 | 4096 | 1667 | 2429 | 0 |
| query.336 | 45 | 360 | 1 | 45 | 45.000 | 45.000 | yes | 4.418e-16 | 4096 | 1443 | 2653 | 0 |
| query.337 | 10 | 30 | 1 | 10 | 10.000 | 10.000 | yes | 1.988e-16 | 1024 | 968 | 56 | 0 |
| query.338 | 36 | 252 | 1 | 36 | 36.000 | 36.000 | yes | 3.891e-16 | 4096 | 1567 | 2529 | 0 |
| query.339 | 36 | 252 | 1 | 36 | 36.000 | 36.000 | yes | 3.785e-16 | 4096 | 1817 | 2279 | 0 |
| query.340 | 10 | 30 | 1 | 10 | 10.000 | 10.000 | yes | 2.163e-16 | 1024 | 872 | 152 | 0 |
| query.341 | 10 | 30 | 1 | 10 | 10.000 | 10.000 | yes | 1.979e-16 | 1024 | 612 | 412 | 0 |
| query.342 | 66 | 660 | 1 | 66 | 66.000 | 66.000 | yes | 3.903e-16 | 4096 | 1719 | 2377 | 0 |
| query.343 | 36 | 252 | 1 | 36 | 36.000 | 36.000 | yes | 3.377e-16 | 4096 | 1638 | 2458 | 0 |
| query.344 | 15 | 60 | 1 | 15 | 15.000 | 15.000 | yes | 2.132e-16 | 32768 | 22064 | 10704 | 0 |
| query.345 | 15 | 60 | 1 | 15 | 15.000 | 15.000 | yes | 2.168e-16 | 32768 | 19138 | 13630 | 0 |
| query.346 | 36 | 252 | 1 | 36 | 36.000 | 36.000 | yes | 3.686e-16 | 4096 | 1931 | 2165 | 0 |
| query.347 | 10 | 30 | 1 | 10 | 10.000 | 10.000 | yes | 1.856e-16 | 1024 | 558 | 466 | 0 |
| query.348 | 21 | 105 | 1 | 21 | 21.000 | 21.000 | yes | 2.843e-16 | 4096 | 1791 | 2305 | 0 |
| query.349 | 66 | 660 | 1 | 66 | 66.000 | 66.000 | yes | 4.654e-16 | 4096 | 1903 | 2193 | 0 |
| query.350 | 21 | 105 | 1 | 21 | 21.000 | 21.000 | yes | 3.877e-16 | 4096 | 1945 | 2151 | 0 |
| query.351 | 6 | 12 | 1 | 6 | 6.000 | 6.000 | yes | 2.131e-16 | 64 | 40 | 24 | 0 |
| query.352 | 28 | 168 | 1 | 28 | 28.000 | 28.000 | yes | 2.322e-16 | 4096 | 1745 | 2351 | 0 |
| query.353 | 45 | 360 | 1 | 45 | 45.000 | 45.000 | yes | 4.353e-16 | 4096 | 2332 | 1764 | 0 |
| query.354 | 28 | 168 | 1 | 28 | 28.000 | 28.000 | yes | 2.534e-16 | 4096 | 2523 | 1573 | 0 |
| query.355 | 55 | 495 | 1 | 55 | 55.000 | 55.000 | yes | 4.445e-16 | 4096 | 1699 | 2397 | 0 |
| query.356 | 36 | 252 | 1 | 36 | 36.000 | 36.000 | yes | 3.861e-16 | 4096 | 2224 | 1872 | 0 |
| query.357 | 15 | 60 | 1 | 15 | 15.000 | 15.000 | yes | 2.082e-16 | 32768 | 23132 | 9636 | 0 |
| query.358 | 28 | 168 | 1 | 28 | 28.000 | 28.000 | yes | 4.358e-16 | 4096 | 1521 | 2575 | 0 |
| query.359 | 55 | 495 | 1 | 55 | 55.000 | 55.000 | yes | 4.744e-16 | 4096 | 1927 | 2169 | 0 |
| query.360 | 21 | 105 | 1 | 21 | 21.000 | 21.000 | yes | 2.134e-16 | 4096 | 3004 | 1092 | 0 |
| query.361 | 36 | 252 | 1 | 36 | 36.000 | 36.000 | yes | 3.864e-16 | 4096 | 1922 | 2174 | 0 |
| query.362 | 28 | 168 | 1 | 28 | 28.000 | 28.000 | yes | 4.361e-16 | 4096 | 1901 | 2195 | 0 |
| query.363 | 15 | 60 | 1 | 15 | 15.000 | 15.000 | yes | 2.605e-16 | 32768 | 13484 | 19284 | 0 |
| query.364 | 45 | 360 | 1 | 45 | 45.000 | 45.000 | yes | 4.959e-16 | 4096 | 2011 | 2085 | 0 |
| query.365 | 10 | 30 | 1 | 10 | 10.000 | 10.000 | yes | 1.361e-16 | 1024 | 766 | 258 | 0 |
| query.366 | 10 | 30 | 1 | 10 | 10.000 | 10.000 | yes | 1.669e-16 | 1024 | 806 | 218 | 0 |
| query.367 | 28 | 168 | 1 | 28 | 28.000 | 28.000 | yes | 3.583e-16 | 4096 | 3059 | 1037 | 0 |
| query.368 | 45 | 360 | 1 | 45 | 45.000 | 45.000 | yes | 5.693e-16 | 4096 | 2274 | 1822 | 0 |
| query.369 | 6 | 12 | 1 | 6 | 6.000 | 6.000 | yes | 1.113e-16 | 64 | 62 | 2 | 0 |
| query.370 | 28 | 168 | 1 | 28 | 28.000 | 28.000 | yes | 3.137e-16 | 4096 | 2752 | 1344 | 0 |
| query.371 | 36 | 252 | 1 | 36 | 36.000 | 36.000 | yes | 4.332e-16 | 4096 | 2266 | 1830 | 0 |
| query.372 | 36 | 252 | 1 | 36 | 36.000 | 36.000 | yes | 3.661e-16 | 4096 | 2140 | 1956 | 0 |
| query.373 | 10 | 30 | 1 | 10 | 10.000 | 10.000 | yes | 2.090e-16 | 1024 | 763 | 261 | 0 |
| query.374 | 55 | 495 | 1 | 55 | 55.000 | 55.000 | yes | 4.393e-16 | 4096 | 2080 | 2016 | 0 |
| query.375 | 15 | 60 | 1 | 15 | 15.000 | 15.000 | yes | 3.310e-16 | 32768 | 15682 | 17086 | 0 |
| query.376 | 28 | 168 | 1 | 28 | 28.000 | 28.000 | yes | 3.808e-16 | 4096 | 2529 | 1567 | 0 |
| query.377 | 21 | 105 | 1 | 21 | 21.000 | 21.000 | yes | 3.245e-16 | 4096 | 1603 | 2493 | 0 |
| query.378 | 45 | 360 | 1 | 45 | 45.000 | 45.000 | yes | 4.769e-16 | 4096 | 1849 | 2247 | 0 |
| query.379 | 15 | 60 | 1 | 15 | 15.000 | 15.000 | yes | 2.066e-16 | 32768 | 22740 | 10028 | 0 |
| query.380 | 21 | 105 | 1 | 21 | 21.000 | 21.000 | yes | 2.174e-16 | 4096 | 2190 | 1906 | 0 |
| query.381 | 45 | 360 | 1 | 45 | 45.000 | 45.000 | yes | 4.049e-16 | 4096 | 2458 | 1638 | 0 |
| query.382 | 21 | 105 | 1 | 21 | 21.000 | 21.000 | yes | 3.340e-16 | 4096 | 1856 | 2240 | 0 |
| query.383 | 45 | 360 | 1 | 45 | 45.000 | 45.000 | yes | 4.234e-16 | 4096 | 2110 | 1986 | 0 |
| query.384 | 15 | 60 | 1 | 15 | 15.000 | 15.000 | yes | 2.747e-16 | 32768 | 19746 | 13022 | 0 |
| query.385 | 28 | 168 | 1 | 28 | 28.000 | 28.000 | yes | 3.258e-16 | 4096 | 1930 | 2166 | 0 |
| query.386 | 28 | 168 | 1 | 28 | 28.000 | 28.000 | yes | 4.311e-16 | 4096 | 1541 | 2555 | 0 |
| query.387 | 55 | 495 | 1 | 55 | 55.000 | 55.000 | yes | 4.805e-16 | 4096 | 1636 | 2460 | 0 |
| query.388 | 36 | 252 | 1 | 36 | 36.000 | 36.000 | yes | 4.384e-16 | 4096 | 2468 | 1628 | 0 |
| query.389 | 15 | 60 | 1 | 15 | 15.000 | 15.000 | yes | 2.560e-16 | 32768 | 23777 | 8991 | 0 |
| query.390 | 21 | 105 | 1 | 21 | 21.000 | 21.000 | yes | 2.765e-16 | 4096 | 3075 | 1021 | 0 |
| query.391 | 6 | 12 | 1 | 6 | 6.000 | 6.000 | yes | 0.000e+00 | 64 | 64 | 0 | 0 |
| query.392 | 45 | 360 | 1 | 45 | 45.000 | 45.000 | yes | 3.403e-16 | 4096 | 2016 | 2080 | 0 |
| query.393 | 28 | 168 | 1 | 28 | 28.000 | 28.000 | yes | 3.729e-16 | 4096 | 2147 | 1949 | 0 |
| query.394 | 15 | 60 | 1 | 15 | 15.000 | 15.000 | yes | 1.912e-16 | 32768 | 26714 | 6054 | 0 |
| query.395 | 15 | 60 | 1 | 15 | 15.000 | 15.000 | yes | 2.190e-16 | 32768 | 19308 | 13460 | 0 |
| query.396 | 6 | 12 | 1 | 6 | 6.000 | 6.000 | yes | 0.000e+00 | 64 | 64 | 0 | 0 |
| query.397 | 15 | 60 | 1 | 15 | 15.000 | 15.000 | yes | 2.110e-16 | 32768 | 21605 | 11163 | 0 |
| query.398 | 28 | 168 | 1 | 28 | 28.000 | 28.000 | yes | 2.898e-16 | 4096 | 2981 | 1115 | 0 |
| query.399 | 6 | 12 | 1 | 6 | 6.000 | 6.000 | yes | 0.000e+00 | 64 | 64 | 0 | 0 |
| query.400 | 21 | 105 | 1 | 21 | 21.000 | 21.000 | yes | 3.675e-16 | 4096 | 2448 | 1648 | 0 |
| query.401 | 10 | 30 | 1 | 10 | 10.000 | 10.000 | yes | 1.593e-16 | 1024 | 936 | 88 | 0 |
| query.402 | 3 | 3 | 1 | 3 | 3.000 | 3.000 | yes | 0.000e+00 | 8 | 8 | 0 | 0 |
| query.403 | 36 | 252 | 1 | 36 | 36.000 | 36.000 | yes | 3.819e-16 | 4096 | 1365 | 2731 | 0 |
| query.404 | 21 | 105 | 1 | 21 | 21.000 | 21.000 | yes | 2.148e-16 | 4096 | 2689 | 1407 | 0 |
| query.405 | 15 | 60 | 1 | 15 | 15.000 | 15.000 | yes | 3.157e-16 | 32768 | 20506 | 12262 | 0 |
| query.406 | 21 | 105 | 1 | 21 | 21.000 | 21.000 | yes | 1.448e-16 | 4096 | 2383 | 1713 | 0 |
| query.407 | 21 | 105 | 1 | 21 | 21.000 | 21.000 | yes | 3.360e-16 | 4096 | 3060 | 1036 | 0 |
| query.408 | 10 | 30 | 1 | 10 | 10.000 | 10.000 | yes | 1.372e-16 | 1024 | 1022 | 2 | 0 |
| query.409 | 28 | 168 | 1 | 28 | 28.000 | 28.000 | yes | 4.025e-16 | 4096 | 2113 | 1983 | 0 |
| query.410 | 28 | 168 | 1 | 28 | 28.000 | 28.000 | yes | 3.476e-16 | 4096 | 2188 | 1908 | 0 |
| query.411 | 6 | 12 | 1 | 6 | 6.000 | 6.000 | yes | 0.000e+00 | 64 | 64 | 0 | 0 |
| query.412 | 21 | 105 | 1 | 21 | 21.000 | 21.000 | yes | 2.185e-16 | 4096 | 2003 | 2093 | 0 |
| query.413 | 21 | 105 | 1 | 21 | 21.000 | 21.000 | yes | 1.996e-16 | 4096 | 3072 | 1024 | 0 |
| query.414 | 3 | 3 | 1 | 3 | 3.000 | 3.000 | yes | 0.000e+00 | 8 | 8 | 0 | 0 |
| query.415 | 6 | 12 | 1 | 6 | 6.000 | 6.000 | yes | 2.018e-16 | 64 | 62 | 2 | 0 |
| query.416 | 3 | 3 | 1 | 3 | 3.000 | 3.000 | yes | 0.000e+00 | 8 | 8 | 0 | 0 |
| query.417 | 6 | 12 | 1 | 6 | 6.000 | 6.000 | yes | 0.000e+00 | 64 | 64 | 0 | 0 |
| query.418 | 6 | 12 | 1 | 6 | 6.000 | 6.000 | yes | 0.000e+00 | 64 | 64 | 0 | 0 |
| query.419 | 3 | 3 | 1 | 3 | 3.000 | 3.000 | yes | 0.000e+00 | 8 | 8 | 0 | 0 |
| query.420 | 55 | 495 | 1 | 55 | 55.000 | 55.000 | yes | 4.299e-16 | 4096 | 1694 | 2402 | 0 |
| query.421 | 15 | 60 | 1 | 15 | 15.000 | 15.000 | yes | 2.531e-16 | 32768 | 15511 | 17257 | 0 |
| query.422 | 28 | 168 | 1 | 28 | 28.000 | 28.000 | yes | 3.521e-16 | 4096 | 2067 | 2029 | 0 |
| query.423 | 15 | 60 | 1 | 15 | 15.000 | 15.000 | yes | 1.666e-16 | 32768 | 26908 | 5860 | 0 |
| query.424 | 10 | 30 | 1 | 10 | 10.000 | 10.000 | yes | 1.658e-16 | 1024 | 463 | 561 | 0 |
| query.425 | 3 | 3 | 1 | 3 | 3.000 | 3.000 | yes | 0.000e+00 | 8 | 8 | 0 | 0 |
| query.426 | 6 | 12 | 1 | 6 | 6.000 | 6.000 | yes | 0.000e+00 | 64 | 64 | 0 | 0 |
| query.427 | 10 | 30 | 1 | 10 | 10.000 | 10.000 | yes | 1.652e-16 | 1024 | 934 | 90 | 0 |
| query.428 | 15 | 60 | 1 | 15 | 15.000 | 15.000 | yes | 2.467e-16 | 32768 | 22252 | 10516 | 0 |
| query.429 | 66 | 660 | 1 | 66 | 66.000 | 66.000 | yes | 5.047e-16 | 4096 | 1786 | 2310 | 0 |
| query.430 | 36 | 252 | 1 | 36 | 36.000 | 36.000 | yes | 3.709e-16 | 4096 | 2006 | 2090 | 0 |
| query.431 | 45 | 360 | 1 | 45 | 45.000 | 45.000 | yes | 4.198e-16 | 4096 | 1888 | 2208 | 0 |
| query.432 | 6 | 12 | 1 | 6 | 6.000 | 6.000 | yes | 0.000e+00 | 64 | 64 | 0 | 0 |
| query.433 | 21 | 105 | 1 | 21 | 21.000 | 21.000 | yes | 2.523e-16 | 4096 | 1763 | 2333 | 0 |
| query.434 | 10 | 30 | 1 | 10 | 10.000 | 10.000 | yes | 1.835e-16 | 1024 | 924 | 100 | 0 |
| query.435 | 21 | 105 | 1 | 21 | 21.000 | 21.000 | yes | 2.664e-16 | 4096 | 2160 | 1936 | 0 |
| query.436 | 21 | 105 | 1 | 21 | 21.000 | 21.000 | yes | 2.463e-16 | 4096 | 1889 | 2207 | 0 |
| query.437 | 45 | 360 | 1 | 45 | 45.000 | 45.000 | yes | 4.397e-16 | 4096 | 1842 | 2254 | 0 |
| query.438 | 28 | 168 | 1 | 28 | 28.000 | 28.000 | yes | 3.719e-16 | 4096 | 1880 | 2216 | 0 |
| query.439 | 45 | 360 | 1 | 45 | 45.000 | 45.000 | yes | 4.120e-16 | 4096 | 1666 | 2430 | 0 |
| query.440 | 15 | 60 | 1 | 15 | 15.000 | 15.000 | yes | 2.095e-16 | 32768 | 23425 | 9343 | 0 |
| query.441 | 10 | 30 | 1 | 10 | 10.000 | 10.000 | yes | 2.017e-16 | 1024 | 632 | 392 | 0 |
| query.442 | 21 | 105 | 1 | 21 | 21.000 | 21.000 | yes | 2.541e-16 | 4096 | 1917 | 2179 | 0 |
| query.443 | 21 | 105 | 1 | 21 | 21.000 | 21.000 | yes | 2.217e-16 | 4096 | 3102 | 994 | 0 |
| query.444 | 45 | 360 | 1 | 45 | 45.000 | 45.000 | yes | 4.350e-16 | 4096 | 1393 | 2703 | 0 |
| query.445 | 36 | 252 | 1 | 36 | 36.000 | 36.000 | yes | 3.658e-16 | 4096 | 2482 | 1614 | 0 |
| query.446 | 1 | 0 | 1 | 1 | 1.000 | 1.000 | yes | 0.000e+00 | 2 | 2 | 0 | 0 |
| query.447 | 55 | 495 | 1 | 55 | 55.000 | 55.000 | yes | 3.979e-16 | 4096 | 1689 | 2407 | 0 |
| query.448 | 28 | 168 | 1 | 28 | 28.000 | 28.000 | yes | 3.521e-16 | 4096 | 1667 | 2429 | 0 |
| query.449 | 10 | 30 | 1 | 10 | 10.000 | 10.000 | yes | 1.382e-16 | 1024 | 636 | 388 | 0 |
| query.450 | 6 | 12 | 1 | 6 | 6.000 | 6.000 | yes | 1.219e-16 | 64 | 48 | 16 | 0 |
| query.451 | 21 | 105 | 1 | 21 | 21.000 | 21.000 | yes | 3.384e-16 | 4096 | 2046 | 2050 | 0 |
| query.452 | 21 | 105 | 1 | 21 | 21.000 | 21.000 | yes | 3.930e-16 | 4096 | 2454 | 1642 | 0 |
| query.453 | 10 | 30 | 1 | 10 | 10.000 | 10.000 | yes | 2.116e-16 | 1024 | 864 | 160 | 0 |
| query.454 | 36 | 252 | 1 | 36 | 36.000 | 36.000 | yes | 4.113e-16 | 4096 | 2075 | 2021 | 0 |
| query.455 | 28 | 168 | 1 | 28 | 28.000 | 28.000 | yes | 4.127e-16 | 4096 | 3008 | 1088 | 0 |
| query.456 | 36 | 252 | 1 | 36 | 36.000 | 36.000 | yes | 3.339e-16 | 4096 | 1870 | 2226 | 0 |
| query.457 | 15 | 60 | 1 | 15 | 15.000 | 15.000 | yes | 2.208e-16 | 32768 | 23788 | 8980 | 0 |
| query.458 | 21 | 105 | 1 | 21 | 21.000 | 21.000 | yes | 2.272e-16 | 4096 | 1826 | 2270 | 0 |
| query.459 | 21 | 105 | 1 | 21 | 21.000 | 21.000 | yes | 2.483e-16 | 4096 | 1528 | 2568 | 0 |
| query.460 | 10 | 30 | 1 | 10 | 10.000 | 10.000 | yes | 1.486e-16 | 1024 | 636 | 388 | 0 |
| query.461 | 55 | 495 | 1 | 55 | 55.000 | 55.000 | yes | 4.123e-16 | 4096 | 1997 | 2099 | 0 |
| query.462 | 6 | 12 | 1 | 6 | 6.000 | 6.000 | yes | 1.615e-16 | 64 | 48 | 16 | 0 |
| query.463 | 28 | 168 | 1 | 28 | 28.000 | 28.000 | yes | 3.865e-16 | 4096 | 2287 | 1809 | 0 |
| query.464 | 15 | 60 | 1 | 15 | 15.000 | 15.000 | yes | 2.005e-16 | 32768 | 18448 | 14320 | 0 |
| query.465 | 45 | 360 | 1 | 45 | 45.000 | 45.000 | yes | 6.577e-16 | 4096 | 1428 | 2668 | 0 |
| query.466 | 36 | 252 | 1 | 36 | 36.000 | 36.000 | yes | 3.549e-16 | 4096 | 2097 | 1999 | 0 |
| query.467 | 21 | 105 | 1 | 21 | 21.000 | 21.000 | yes | 2.574e-16 | 4096 | 2110 | 1986 | 0 |
| query.468 | 21 | 105 | 1 | 21 | 21.000 | 21.000 | yes | 3.199e-16 | 4096 | 2847 | 1249 | 0 |
