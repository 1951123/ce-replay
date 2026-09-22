# Semantic-Optimizer-v0

## Headline results

| Metric | Result |
|---|---:|
| Complete trajectory identical | **True** |
| Final design / loss identical | **True / True** |
| Accepted moves | 17 |
| Accepted ADD / DROP / SWAP | 1 / 0 / 16 |
| Initial → final loss | 812.671173249842 → 806.257701987431 |
| Total feasible moves considered | 5,639,186 |
| Safely pruned | 1.89% |
| Cached numerical | 93.39% |
| Requiring local control replay | 4.72% |
| Query control-replay reduction | 171.31x |
| Oracle / semantic phase runtime | 289.013s / 82.422s |
| Wall-clock phase speedup | 3.51x |
| Cache hit rate | 99.97% |
| False safe-prunes / fast false positives | 0 / 0 |

The full round-by-round trajectory is in the CSV and JSON. Every round is a
full-neighborhood audit, stronger than the four required periodic checkpoints.
State was also recomputed from scratch after every accepted move; all row,
q-error, objective, and winner-trace audits have zero unexplained divergence.

## Search space versus evaluation cost

Only the 1.89% safe-pruned moves reduce exact search
work. Cached numerical evaluation does **not** reduce the configuration space;
it reduces the cost of evaluating configurations that are still considered.

## Cache policy

Current per-query rows, q-error and control traces depend on the selected
candidates incident to that query. Single-toggle entries `(candidate, query)`
have the same dependency. After an accepted move, the complete structural
query union of its endpoint(s) is invalidated—even when current rows and winner
trace happen not to change—and all candidate-query entries incident to those
queries are evicted lazily and recomputed on demand. Disjoint-query
SWAPs compose cached toggle estimates; shared-query SWAPs require the certified
same-control path or local GreedyCover replay.

## Final verdict

1. **Yes.** The complete exhaustive best-improvement trajectory is preserved.
2. **Yes.** Cached numerical evaluation remains exact after all accepted changes.
3. **Yes.** Dependency-aware invalidation produces zero cache drift in full state audits.
4. `95.28%` of all feasible moves require no control replay (safe-pruned plus cached numerical).
5. `1.89%` are safely pruned.
6. Query-level control replay is reduced by `171.31x`.
7. The measured optimizer-phase runtime is reduced by `3.51x`.
8. After acceleration, the dominant counted work is 50,142,840 scalar q-error updates plus move/bound iteration.
9. The remaining bottleneck is move enumeration and numerical objective work, not CE control replay or cache maintenance.
10. **Yes.** Exact semantic move evaluation should become the default architecture for this fixed-precedence MCV optimizer; this result does not extend to precedence or FD semantics without separate validation.

## Artifacts

- `results/census_semantic_optimizer_v0.json`
- `results/census_semantic_optimizer_v0_rounds.csv`
