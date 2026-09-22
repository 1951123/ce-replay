# Optimize-v2: semantic move locality and reachable OID ties

## Setup

The experiment reuses the frozen 468-query, 2,253-candidate Census pair-MCV
IR. PostgreSQL is not invoked. The starting design is the full-scale replay
marginal-greedy result:

- selected candidates: 208;
- budget: 105,061 bytes;
- workload loss: 812.671173.

Two graphs are distinguished:

- dependency adjacency: two candidates affect at least one common query;
- semantic interaction adjacency: they occur in a common query and share a
  predicate column, so GreedyCover consumption can make them conflict.

## A. Anatomy of improving swaps

At the marginal design there are 283,164 budget-feasible swaps. Exhaustive
one-round evaluation takes 13.98 seconds and finds 3,768 improving swaps.

| Class | Improving swaps | Fraction | Best delta |
|---|---:|---:|---:|
| 1-hop semantic | 82 | 2.18% | -1.84695 |
| 2-hop semantic, excluding 1-hop | 1,492 | 39.60% | **-3.40434** |
| Disconnected budget exchange | 2,194 | 58.23% | -1.45008 |

No improving swap remains in the separate same-query/non-conflicting class:
for this pair-candidate graph those cases are connected through a two-hop
semantic path.

The strongest individual move is two-hop. Nevertheless, most improving moves
by count are genuine budget exchanges between candidates with no semantic
interaction path of length at most two. Thus interaction locality alone is not
a complete move generator; it needs a small global budget-exchange channel.

## Restricted local search

All searches start from the same marginal-greedy design and repeatedly accept
the best improving move in their restricted neighborhood.

| Search | Final loss | Improvement | Runtime | Moves enumerated | Accepted |
|---|---:|---:|---:|---:|---:|
| Previous naive full add/drop/swap | 806.258 | 0.789% | 278.68 s | — | — |
| 1-hop semantic swaps | 806.162 | 0.801% | **13.24 s** | 241,022 | 35 |
| 2-hop semantic swaps | **806.000** | **0.821%** | 136.53 s | 2,410,447 | 20 |
| 1-hop + 64 budget candidates | 806.395 | 0.772% | 21.38 s | 393,405 | 26 |

The restricted and full searches follow different best-improvement paths, so
their final local optima are not ordered by neighborhood inclusion. This is why
1-hop can finish slightly below the previous naive full-search run.

The practically important result is that 1-hop semantic search reaches the
same objective region in 13.2 seconds, roughly 21x faster than the previous
full search. Two-hop captures the strongest first move and improves the final
loss by another 0.162, but costs ten times more than one-hop. The simple global
budget shortlist does not improve the final result in this run, although the
swap census shows that budget exchange cannot be omitted in general.

## B. Reachable OID-tie locality

Under the fixed marginal selection and original OID order:

| Metric | Result |
|---|---:|
| Consumption rounds | 634 |
| Conflicting reachable rounds | 245 |
| Queries with a reachable conflict | 180 / 468 |
| Tie-graph nodes | 194 / 2,253 |
| Tie-graph edges | 540 |
| Mean / median / max tie degree | 5.57 / 5 / 16 |
| Connected components | 1 |

The tie graph is globally connected but small: only 194 selected candidates
participate in reachable conflicts, and degree remains low. As with the earlier
dependency graph, component count alone would miss the useful locality.

## Fixed-selection precedence refinement

Keeping `Y` fixed, a best-improvement search considers only the 540 reachable
tie edges and swaps the corresponding precedence ranks. With a limit of 25
accepted moves:

- initial loss: 812.671173;
- final loss: 802.113109;
- relative improvement: **1.299%**;
- edge evaluations: 13,500;
- runtime: **0.847 seconds**.

This is a lower bound on order opportunity, not a global optimum over all
reachable precedence assignments. The search reaches its configured 25-move
limit. Even this bounded refinement improves more than the earlier selection
SWAP phase (1.30% versus 0.79%) and is much cheaper.

## Conclusions

1. Semantic neighborhoods are effective pruning structures: one-hop search
   reproduces the full-SWAP objective region at about one twenty-first of the
   runtime.
2. They are not sufficient by themselves: 58% of first-round improving swaps
   are disconnected budget exchanges.
3. Two-hop locality contains the strongest individual selection swap, but its
   larger neighborhood has a substantial runtime cost.
4. Reachable precedence is a real optimization dimension. It provides more
   improvement than selection SWAP in this experiment at negligible runtime.
5. The useful design variable is therefore `D=(Y, pi)`, while both move and
   order search should be generated from CE semantics rather than the full
   Cartesian/permutation spaces.

## Artifacts

- Experiment: `tools/ce_replay_optimize_v2.py`
- Full result: `results/census_ce_replay_optimize_v2.json`
- Source workload IR: `results/census_ce_replay_optimize_v1_full_pairs.json`
