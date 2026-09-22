# 8. Evaluation

## 8.1 RQ1 — Native-semantic fidelity

RQ1 asks whether CE-Replay reproduces native PostgreSQL estimates inside the supported statistics-sensitive fragment. We evaluate controlled mechanism semantics, the real workloads, and fresh physical deployments. Table T2 compresses the strongest evidence.

**Table T2: Native semantic fidelity within the supported fragment.** Comparisons use matched query, design, precedence, and payload realization. Maximum error is relative error in the reported raw/native cardinality boundary.

| Validation setting | Semantic fragment | Comparisons | Result | Maximum relative error |
|---|---|---:|---|---:|
| Census MCV raw oracle | Scalar MCV | Four targets × 32 designs | All matched | 5.55e-16 |
| Controlled FD scenarios | FD selection, application, and order | 13 subset/order scenarios | All matched | 0 |
| Synthetic ScalarArray | Constant `IN`/`= ANY` MCV | 29 cases | 29/29; scalar regression 128/128 | 4.38e-15 |
| DMV baseline realization | Real equality/IN MCV+FD | 27,510 | 27,510/27,510 | 1.40286e-14 |
| Census fresh deployment | Fresh mixed MCV+FD | 468 | 468/468 | 6.92e-16 |
| DMV fresh deployment | Fresh mixed MCV+FD | 1,965 | 1,965/1,965 | 2.43422e-14 |

The MCV raw oracle removes the rounding/clamping ambiguity of integer plan rows. Across four statistics targets and every subset of five candidates, replay agrees with the native pre-clamp result at floating-point precision. FD validation separately covers 13 subset/order scenarios with zero maximum relative error and confirms that FD executes a different selection/application program after MCV's estimated-clause state.

ScalarArray validation adds the predicate family needed by DMV without changing existing scalar behavior. All 29 synthetic cases pass, the 128-case scalar regression remains intact, and canonical DMV semantic coverage rises from 52 of 1,965 queries to all 1,965. On a real frozen DMV realization, 27,510 query/design comparisons all pass, with maximum relative error 1.40286e-14.

Fresh deployment provides the strongest end-to-end check because payloads are regenerated rather than reused from hypothetical optimization. CE-Replay matches native PostgreSQL on all 468 fresh Census queries and all 1,965 fresh DMV queries. These are same-fresh-realization comparisons; they establish semantic fidelity, not equality between frozen and fresh estimates.

**Answer to RQ1.** Within the explicitly supported PostgreSQL 16.14 statistics-sensitive base-restriction fragment, CE-Replay matches native CE to floating-point tolerance across controlled MCV, FD, and ScalarArray tests, both real workloads, and both fresh deployments. This result does not extend to joins, full planner search, arbitrary predicates, unsupported statistics mechanisms, or other PostgreSQL versions.

## 8.2 RQ2 — Maintenance-constrained physical design

RQ2 asks whether replay can drive resource-constrained statistics design without a separately learned design-to-q-error model. We first separate the semantic need for selection from the resource need for a budget, then evaluate maintenance-constrained search.

### Selection remains meaningful without scarcity

Figure F2 uses separate workload panels because raw objective scales are not comparable.

**Figure F2: Cross-workload non-monotonicity.** The Census panel shows empty, all-statistics, and optimized-subset loss in one frozen realization; the DMV panel shows empty and complete mechanism states in its baseline realization. Annotate harmful singleton additions and improving removals. Use no connecting line or shared vertical scale.

In the Census realization, empty, all-statistics, and optimized-subset losses are 11,808.960379, 10,932.295550, and 805.316472. Of 3,011 singleton additions to empty, 1,560 worsen loss; 317 single removals from the all-statistics design improve it. In the DMV baseline realization, empty, all-MCV, all-FD, and all-mixed losses are 87,276.581132, 92,850.151303, 95,404.855146, and 92,850.151303. Among 70 usable singleton additions, 25 improve and 45 worsen; 17 removals from all improve. All-mixed equals all-MCV because MCV consumption suppresses every usable FD in that state.

These results establish **semantic necessity**: capacity alone does not make every statistic desirable. The independent maintenance measurements in Figure F3 establish **resource necessity**: deployed objects also impose recurring collection work. Selection is therefore neither simple budget filling nor a budget-only artifact.

### Maintenance-aware designs

Table T3 reports the final searches. The raw DMV objective is preserved but is dominated by its two zero-truth queries and is not compared with Census.

**Table T3: Maintenance-budget physical-design outcomes.** “Local optimum” refers only to the complete audited ADD/DROP/SWAP neighborhood under the frozen payload and fixed precedence.

| Workload | Usable universe | Budget | Selected design | Cost / unused | Frozen loss | Correctness audit |
|---|---|---:|---|---|---:|---|
| Census | 2,253 MCV + 758 FD | 286.144 | 276 MCV + 7 FD | 286.143 / 0.001 | 787.809381 | 565,031 terminal moves; best delta 3.7454e-05; local optimum |
| DMV optimization realization | 36 MCV + 34 FD | 43.724603 | 11 MCV + 12 FD | 29.158543 / 14.566060 | 7.83651388676e298 | 47 ADD, 23 DROP, 1,081 SWAP; best delta 0; local optimum |

For Census, the budget equals the modeled maintenance cost of the previous 205-MCV + 56-FD byte-budget design. Under the maintenance interpretation, the unchanged solver instead selects 276 MCV and seven FD objects. Its frozen loss is 787.809381 versus 805.316472 for the previous design in the shared frozen context, a 2.1739% reduction. Typed-design Jaccard similarity is 42.7822%, and all seven selected FDs are consumed. Thus changing only the resource semantics materially changes both composition and loss; payload bytes remain an earlier controlled proxy, not the final resource definition.

For DMV, the complete usable universe costs 87.449206 normalized units and the primary budget is half that amount. The selected 11-MCV + 12-FD state costs only 29.158543, leaving 14.566060 units unused; all selected objects contribute in the frozen state, and 417 queries consume FD. The 25% budget selects 11 MCV + seven FD, whereas the 50%, 75%, and 100% budgets all return 11 MCV + 12 FD. Additional capacity does not force the local search to accept non-improving objects. This is a neighborhood-search result, not proof that the full global optimum uses that cost.

Candidate utility is contextual. In DMV, 11 candidates harmful when evaluated as additions to the empty state have beneficial removal-marginal evidence in the final design. The result does not make those candidates universally beneficial; it shows that empty-design singleton ranking does not determine their contribution under composed native semantics.

Small-instance audits calibrate correctness without overstating guarantees. The five-candidate Census experiment recovers the exhaustive native optimum across its feasible budget thresholds. The DMV production optimizer recovers the exact restricted optimum in all four audited subproblems within the documented tolerance. Full Census and DMV results remain local optima under their tested neighborhoods.

**Answer to RQ2.** CE-Replay drives maintenance-constrained statistics design without a separately learned design-to-q-error response model. It produces nontrivial mixed states that reflect native contextual interaction and the chosen resource model, with exhaustive correctness evidence on small/restricted instances and neighborhood-local guarantees at workload scale—not full global optimality.

## 8.3 RQ3 — Semantic incremental evaluation

RQ3 asks how much repeated semantic/control work can be avoided while preserving move values and search behavior. Table T4 separates sparse and dense incidence, control-work reduction, and wall-clock behavior.

**Table T4: Exact incremental evaluation under sparse and dense incidence.** Heterogeneous work metrics are reported in separate columns and are not collapsed into one speedup.

| Setting | Incidence | Audited search | Exactness | Replay/control reduction | Wall-clock result |
|---|---|---:|---|---|---|
| Census MCV local search | Sparse; mean degree 4.44 | 5,639,186 moves | 17 accepted moves and final state identical | 171.31× fewer query control replays; 95.28% require no control replay | 82.422 s vs 289.013 s; 3.51× |
| Census mixed local search | Sparse with directed MCV→FD state | 9,107,766 moves | 19 accepted moves and final state identical | 95.13% numerical-only; 154.61× mechanism-aware control reduction | 145.68 s vs 45.05 s; 3.23× slower |
| DMV mixed optimization | Dense; mean degree 497.13 | 1,151 terminal moves | Terminal local audit; four restricted exact recoveries | 67.91% of full-workload query replay operations avoided | No comparable speedup claim |

Census's 2,253-pair graph has one giant component despite mean candidate degree 4.44. Global connected-component decomposition is therefore ineffective, but a typical candidate affects only a small query set. In a direct MCV toggle experiment, full replay takes 1.602 ms versus 33.6 microseconds for affected-query evaluation; the latter touches 4.36 of 468 queries on average, yielding a 47.7× evaluator-time difference and 107.3× fewer query replay operations. These are evaluator-specific measurements, not whole-system speedups.

The complete MCV local-search audit is stronger than a single round: every one of 17 accepted moves and the terminal result matches the exhaustive current-neighborhood oracle. Control replay falls by 171.31×, while the measured phase improves by 3.51×. Exactness requires structural/counterfactual invalidation: current output equality does not imply that two states will respond equally to a future toggle.

Mixed MCV+FD evaluation preserves the complete 19-move trajectory and final result, and 95.13% of move evaluations use numerical-only updates. However, the semantic implementation takes 145.68 s versus 45.05 s for the already factorized algebraic oracle, making it 3.23× slower. Once control replay is reduced, numerical aggregation and Python move-loop overhead dominate. This negative result prevents converting a semantic-work reduction into a universal runtime claim.

DMV supplies the complementary dense case. Candidate degree has mean 497.13, median 498, 90th percentile 520, and maximum 546. Even there, dependency-aware evaluation avoids 67.91% of full-workload query replay operations. The saving is weaker than in sparse Census and is not a directly comparable time metric, but it shows that semantic invalidation remains useful without sparse incidence.

Other decomposition attempts do not change this interpretation. Census's giant component, lack of useful semantic factorization, limited outer-space benefit from commutativity, and absence of a proven restart-safe compact state indicate that CE-Replay primarily reduces exact move-evaluation work; it does not decompose away the combinatorial design problem.

**Answer to RQ3.** CE-Replay's realized and counterfactual dependencies support exact incremental move evaluation and substantially reduce semantic/control replay in both sparse and dense regimes. The magnitude depends on topology, and reduced semantic work does not guarantee end-to-end wall-clock speedup when numerical aggregation dominates.

## 8.4 RQ4 — Composition and physical deployment

RQ4 asks whether interacting MCV and FD semantics can be optimized together and whether the resulting state survives physical deployment and fresh payload generation.

### Directed mechanism interaction

Figure F4 combines the semantic direction from Section 4 with consumption evidence.

**Figure F4: Directed MCV-to-FD composition.** Show MCV selection and clause consumption feeding the residual state used by FD. Beneath the semantic diagram, compare independent/all-statistics and joint/selected FD consumption for Census and DMV.

On Census, independent mechanism optimization yields loss 813.942274 and selects 97 FDs, of which 72 are never consumed after composition. Joint semantic optimization yields loss 806.443575, a 0.9213% improvement, and selects 54 FDs, all consumed. The result demonstrates that independent mechanism scores can spend maintenance resource on objects suppressed by upstream MCV semantics.

DMV shows the same interaction under a different topology. In its baseline all-statistics state, all 36 MCV objects consume while none of 34 usable FDs consumes. The optimized frozen state selects 12 FDs, all consumed, and 417 queries use at least one FD. After deployment, 11 FD payloads materialize and all 11 consume across 389 queries. Selection thus restores useful FD reachability and the composition remains observable after fresh `ANALYZE`.

### Physical realization and fresh validation

Table T5 distinguishes physical realization, same-fresh-realization semantic fidelity, and frozen-to-fresh drift.

**Table T5: Physical deployment and fresh native validation.** An unavailable DMV drift cell records missing frozen provenance rather than an assumed zero.

| Workload | Selected design | Fresh materialization | FD consumption | Fresh replay/native | Maximum relative semantic error | Frozen→fresh drift | Cost prediction error |
|---|---|---|---|---|---:|---|---:|
| Census | 276 MCV + 7 FD | 276/276 MCV; 7/7 FD | 7/7 | 811.553725 / 811.553725; 468/468 | 6.92e-16 | 787.809381 → 811.553725; +3.0140% | 7.20% |
| DMV | 11 MCV + 12 FD | 11/11 MCV; 11/12 FD | 11/11 materialized; 389 queries | 1,965/1,965; aggregate equal | 2.43422e-14 | Unavailable: frozen per-query provenance not persisted | 21.4295% |

The Census design is created in verified order and analyzed exactly once. The maintenance model predicts 0.773682 s and the observed `ANALYZE` takes 0.829417 s, a 7.20% error. Frozen loss 787.809381 becomes fresh loss 811.553725, a 3.0140% realization drift, while fresh replay/native semantic error is zero at aggregate precision. All selected objects materialize and consume.

Repeated Census collection separates semantic correctness from realization variability. Across 30 independent `ANALYZE` realizations, all 14,040 replay/native comparisons pass. Workload loss has mean 797.632243, standard deviation 14.636349, and range 764.982678–828.581271. MCV control never changes; 462 of 468 queries retain the complete control path, while six change FD control because payload availability varies. This establishes same-realization replay fidelity under payload variation, not stability of design rankings.

The DMV design is also created in verified order and analyzed exactly once. The cost model predicts 0.238645841 s; observation is 0.303734822 s, a 21.4295% error, reinforcing the first-order proxy interpretation. All 11 MCV payloads materialize and consume. Eleven of 12 FD payloads materialize; the unavailable object is `fd:scofflaw_indicator:suspension_indicator`, and all materialized FDs consume. Fresh replay matches native on every query, with maximum relative error 2.43422e-14. The fresh nonzero-truth diagnostic loss is 85,014.8083461; it is not the optimized objective.

The original DMV optimization artifact did not persist the 1,965 frozen per-query estimates/q-errors, baseline rows, or clause-level simple selectivities, and its database had been removed. Exact frozen-to-fresh per-query reconstruction is therefore impossible. The paper cannot report the frozen zero-truth contribution, frozen nonzero-truth diagnostic, or paired per-query drift distribution. This is artifact/provenance incompleteness, not a fresh semantic correctness failure: exact deployment/order, fresh payload materialization and consumption, 389 FD-consuming queries, and all fresh replay/native comparisons remain independently supported.

**Answer to RQ4.** CE-Replay composes directed MCV and FD semantics, avoids selecting many suppressed FDs, and remains faithful after physical deployment and fresh `ANALYZE` on both workloads. Fresh payload realization can change estimates and availability, so semantic replay error and payload realization drift must be reported separately; DMV supports the former and physical composition, but its paired per-query drift distribution is unavailable because frozen provenance was not persisted.

## Appendix placement

The main evaluation omits complete MCV/FD semantic matrices, all ScalarArray fixtures, precedence witnesses, move-category distributions, semantic-state counterexamples, commutativity and factorization experiments, full maintenance residual diagnostics, the complete repeated-`ANALYZE` distribution, the detailed DMV provenance search, and query-level deployment comparisons. These belong in the planned appendix or reproducibility artifact rather than additional main figures or tables.
