# Compositional-Semantic-Optimizer-v0

## Headline

| Metric | Result |
|---|---:|
| Complete trajectory / final design / final loss identical | **yes / yes / yes** |
| Accepted moves / rounds including terminal | 19 / 20 |
| Initial → final loss | 806.443575058090 → 805.316471766631 |
| Feasible moves considered | 9,107,766 |
| Safe pruned | 0.15% |
| Numerical-only moves | 95.13% |
| FD-only replay moves | 0.19% |
| MCV+FD replay moves | 4.54% |
| Full→query-local control reduction | 58.89x |
| Query-local→mechanism-aware reduction | 154.61x |
| Exact algebraic oracle / semantic runtime | 45.05s / 145.68s (0.31x) |
| False prune / false fast path | 0 / 0 |

The runtime result is a negative performance result: despite the large control-
work reduction, the current semantic implementation is **3.23x slower** than
the exact algebraic oracle. Its 145.68 seconds break down into 112.85 seconds
of numerical aggregation and other move-loop overhead, 20.77 seconds of safe-
bound construction/sorting, 5.48 seconds of move enumeration, 4.84 seconds of
MCV replay, 1.74 seconds of FD replay, and 0.004 seconds of cache maintenance.
The semantic architecture is correct, but this Python realization is not yet a
runtime optimization over the already factorized oracle.

## Move-class breakdown

| class | feasible | improving | pruned | numerical | FD-only | MCV+FD | accepted |
|---|---:|---:|---:|---:|---:|---:|---:|
| MCV ADD | 3,423 | 714 | 289 | 3,134 | 0 | 0 | 0 |
| FD ADD | 6,824 | 1,197 | 836 | 5,988 | 0 | 0 | 1 |
| MCV DROP | 4,113 | 1 | 25 | 4,088 | 0 | 0 | 0 |
| FD DROP | 1,088 | 0 | 72 | 1,016 | 0 | 0 | 0 |
| MCV→MCV SWAP | 5,259,508 | 3,964 | 1,551 | 4,940,625 | 0 | 317,332 | 11 |
| FD→FD SWAP | 731,937 | 3,388 | 5,811 | 710,272 | 15,854 | 0 | 6 |
| MCV→FD SWAP | 2,893,912 | 1,633 | 2,301 | 2,801,418 | 1,288 | 88,905 | 1 |
| FD→MCV SWAP | 206,961 | 9,594 | 2,374 | 197,536 | 14 | 7,037 | 0 |

The source fingerprint and complete mechanism-specific move breakdown are in
the JSON. Every round received a full move-neighborhood audit and every accepted
state a full MCV-boundary, MCV-trace, FD-trace, rows, q-error and objective audit.

## Semantics and invalidation

The cached interface is `(post-MCV estimate, remaining/estimated clauses, MCV
trace)`. FD moves reuse it and replay only FD. MCV moves conservatively replay
both stages. The dependency is directed MCV→FD. Cache invalidation nevertheless
uses the complete structural affected-query union for both mechanism types,
because counterfactual toggle values also depend on the rest of the selected
design. Numerical caching reduces evaluation cost; only safe pruning reduces
the searched move set.

Four accepted MCV moves changed downstream FD consumption traces. One accepted
move was a cross-mechanism MCV→FD swap. All 56 FD objects in the final design
are consumed by at least one query; none is left globally unconsumed.

## Final verdict

1. **Yes.** The complete mixed trajectory matches exhaustive best improvement.
2. **Yes.** The MCV→FD boundary remains exact under structural invalidation.
3. `95.13%` of move evaluations are numerical-only.
4. `0.19%` require FD but not MCV replay.
5. `4.54%` require both MCV and FD replay.
6. Query locality alone saves `58.89x` control work versus all-query replay.
7. Mechanism-aware reuse saves a further `154.61x` beyond query locality.
8. Accepted cross-mechanism swaps: `1`.
9. The dominant residual cost is numerical q-error aggregation and Python move-loop overhead (112.85s), followed by safe-bound sorting (20.77s). Mechanism replay totals only 6.58s.
10. **Yes for correctness and semantic generality, but not yet for wall-clock performance.** The architecture generalizes across frozen base-restriction MCV+FD semantics; the current implementation must batch/vectorize numerical move evaluation before it can replace the exact algebraic oracle on runtime grounds.
