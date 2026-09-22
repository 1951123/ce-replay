# Optimize-v3: joint selection--precedence alternating refinement

## Question

Does optimizing reachable OID precedence alter the selection landscape enough
to justify treating the physical design as `D=(Y, pi)` rather than optimizing
`Y` once and applying order as a post-processing step?

## Method

The experiment starts from the full Census pair-MCV marginal-greedy design:

- 468 queries;
- 2,253 candidates;
- budget 105,061 bytes;
- 208 selected candidates;
- initial loss 812.671173;
- original physical OID precedence.

Each alternating round performs:

1. precedence refinement over the currently reachable conflicting tie edges;
2. selection refinement under the new precedence;
3. recomputation of all design-dependent marginals.

Selection refinement uses monotonic ADD/DROP, one-hop semantic SWAP, and a
64-candidate global budget channel. Precedence refinement uses monotonic
best-improvement swaps on the dynamically recomputed reachable tie graph. This
is a block-coordinate heuristic, not a global optimizer.

## Convergence

| Round | Before | After order | After selection | Order moves | Selection moves |
|---:|---:|---:|---:|---:|---:|
| 1 | 812.671173 | 802.113109 | 796.738081 | 25 | 29 |
| 2 | 796.738081 | 796.240300 | 795.595127 | 9 | 6 |
| 3 | 795.595127 | 795.511630 | 795.511630 | 2 | 0 |
| 4 | 795.511630 | 795.511630 | 795.511630 | 0 | 0 |

Overall:

- final loss: 795.511630;
- total improvement from marginal greedy: 2.1115%;
- final selected candidates: 209;
- total runtime: 37.15 seconds;
- total affected-query replays: 6,616,998.

## Coupling strength

The decisive comparison is within the first round:

`812.671 -> 802.113` by precedence refinement, then

`802.113 -> 796.738` by recomputing selection under the new precedence.

The second step contributes another 5.375 loss units, or 0.670% relative to
the order-refined design. This is much larger than a numerical tail such as
`802.113 -> 801.9`. Precedence changes enough consumption decisions to expose
materially different selection marginals.

The coupling is not indefinitely strong. The second alternating round gains
1.143 additional units, the third gains 0.0835, and the fourth gains nothing.
Most value is captured in two rounds.

Compared with one-dimensional refinements from the same marginal start:

| Method | Loss |
|---|---:|
| Marginal selection, original order | 812.671 |
| 1-hop selection refinement only | 806.162 |
| Precedence refinement only (25 moves) | 802.113 |
| Joint alternating refinement | **795.512** |

Thus neither selection-only nor order-only refinement recovers the joint
result.

## Runtime

| Round | Order time | Selection time |
|---:|---:|---:|
| 1 | 0.981 s | 28.411 s |
| 2 | 0.361 s | 5.731 s |
| 3 | 0.104 s | 0.757 s |
| 4 | 0.035 s | 0.769 s |

Order search remains cheap. Recomputing and enumerating selection moves after
the first precedence change dominates runtime. This reinforces the earlier
finding that CE replay arithmetic is not the bottleneck.

## Conclusion

The experiment supports treating physical design as `D=(Y, pi)` from the
start. Precedence is not merely a deployment post-processing choice: changing
it materially changes `Delta_s(Y, pi)`, and re-optimizing selection captures
substantial additional benefit.

At the same time, convergence is rapid enough that no elaborate joint solver
is currently justified. Two alternating rounds capture nearly all observed
improvement. The MCV optimization algorithm can now be frozen as:

1. replay marginal selection;
2. reachable-tie precedence refinement;
3. selection refinement under the new precedence;
4. repeat until stable, normally a small number of rounds.

The remaining limitation is that this experiment evaluates arbitrary
precedence directly in the already validated external semantics. A future
end-to-end deployment test should physically create selected objects in the
final precedence order and re-specialize their newly sampled payloads. It is
not necessary for measuring the structural coupling isolated here, but is
required before claiming operational deployment fidelity for the final joint
design.

## Artifacts

- Experiment: `tools/ce_replay_optimize_v3.py`
- Full result: `results/census_ce_replay_optimize_v3.json`
- Source workload IR: `results/census_ce_replay_optimize_v1_full_pairs.json`
