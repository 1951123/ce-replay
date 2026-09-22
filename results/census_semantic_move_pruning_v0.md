# Semantic-Move-Pruning-v0

## Setup and baseline lock

This experiment reuses the frozen 468-query / 2,253-candidate MCV IR and the
Optimize-v2 marginal-greedy design.  All four baseline checks passed: loss
`812.671173249842`, 283,164 feasible swaps, 3,768 improving
swaps, and best move `(383, 4)` with delta `-3.404339384873`.

## Headline result

| category | swaps | percent | improving swaps | best included? |
|---|---:|---:|---:|---:|
| safe prune | 99,403 | 35.10% | 563 | no |
| exact cached numerical | 174,343 | 61.57% | 3,088 | no |
| exact local/control replay | 9,418 | 3.33% | 117 | yes |
| full workload replay | 0 | 0.00% | 0 | no |

The cached eligibility certificate produced 0 false positives;
maximum row relative error was `0` and maximum
q-error loss error was `0`.  The end-to-end
simulation returned the same best move: **True**, with resulting loss
`809.266833864969`.

## Precise semantics

`Qstruct(s)` is the frozen candidate incident-query set. `Qreal(s)` contains
queries whose unrounded replayed rows change when `s` is toggled at the current
design. Case 1 preserves winner IDs; Case 2 changes winner IDs but preserves the
entire consumed-column-scope sequence; Case 3 changes that control sequence.
The numerical fast path is admitted only by a cached-state certificate. Query-
disjoint endpoints compose their already cached single-toggle estimates exactly.
For a shared query, either the changed candidate must be shadowed or a removed
winner must be replaced at the same round by a candidate with exactly the same
scope. Everything else falls back.

"Full direct replay" means replaying all 468 queries. It is never required here
because frozen dependency sets make affected-query replay exact. "Local/control
replay" means running GreedyCover only for the structural union of the two move
endpoints.

## Safe pruning and ranking

The safe bound is `delta >= -sum_q(max(L_q-1,0))` over structurally affected
queries. It is used only after an incumbent exists, so skipped moves are proven
unable to beat that incumbent; this is best-improvement branch-and-bound, not a
claim that skipped moves are non-improving. Detailed deterministic order results
and ranking recall are in the JSON.

## Final verdict

1. `35.10%` of swaps are safely skipped in the selected exact best-improvement order.
2. `95.29%` of all swaps have a conservative exact cached-numerical certificate before branch-and-bound.
3. Yes: the certificate uses cached rounds, ranks, scopes, and eligibility lists and has zero observed false positives.
4. The end-to-end iteration performs 9,418 move-level local control replays (102,099 query replays); no full-workload replay is required.
5. Only partly. Semantic-neighborhood-first ranks the global best at 99,017/283,164; candidate-ID and strongest-bound order find it earlier. Additive marginals recover 75.08% of improving swaps in the top 1%, but rank the single global best poorly.
6. ADD+DROP residuals occur both with unchanged and changed control traces. Nonzero residual under unchanged control is objective (q-error) nonlinearity; the changed group additionally contains CE control interaction.
7. Yes: the exact iteration returns `(383, 4)` and the exhaustive best loss exactly. Control replay work falls by `25.188x`; counting cheap numerical updates as query operations gives `1.416x`.
8. By operation count the remaining cost is 1,713,719 cached numerical/q-error updates; the expensive semantic cost is 102,099 affected-query GreedyCover replays concentrated in 9,418 moves.
9. Yes, the combination of 35.10% safe pruning, 95.29% global cache eligibility, zero validation mismatches, and 25.19x fewer control replays justifies a separate `Semantic-Optimizer-v0` experiment. This report deliberately stops before implementing it.

## Artifacts

- full metrics: `results/census_semantic_move_pruning_v0.json`
- compressed move oracle: `results/census_semantic_move_pruning_v0_moves.csv.gz`
