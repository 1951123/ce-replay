# Research-Synthesis-v0

## Executive conclusion

The strongest demonstrated contribution is not a globally optimal statistics
designer. It is a workload-specialized, design-parametric executable
representation of native PostgreSQL cardinality-estimation semantics that
serves simultaneously as:

1. an objective evaluator for physical designs;
2. a semantic dependency oracle for exact incremental evaluation; and
3. a validation boundary separating estimator semantics from fresh-ANALYZE
   payload uncertainty.

For the tested PostgreSQL 16.14 base-relation restriction fragment, this has
been demonstrated end to end for MCV and functional-dependency statistics,
including the directed `MCV → estimatedclauses → FD` interaction. What has not
been demonstrated is global optimality at Census scale, general PostgreSQL CE,
join replay, robustness across ANALYZE realizations, or a mixed optimizer that
is faster than a carefully factorized exact oracle.

The best-supported paper framing is therefore an executable-CE specialization
and compositional physical-design architecture paper. Local search is a
demonstration consumer of the evaluator, not the central algorithmic claim.

## 1. Current problem and system layers

For the current selection-only mixed problem,

\[
S=S_{MCV}\cup S_{FD},\qquad Y\subseteq S,
\]

subject to

\[
\sum_{s\in Y}c_s\le B.
\]

For each query, CE-Replay computes \(\widehat N_q(Y)\), and the workload loss is

\[
L(Y)=\sum_{q\in Q}QErr(\widehat N_q(Y),N_q).
\]

The outer problem is \(\min_Y L(Y)\) under the budget. CE-Replay does **not**
solve this combinatorial problem or imply global optimality. It supplies an
exact objective evaluator within a supported semantic fragment.

The evidence separates into six layers:

| Layer | Role | Current evidence |
|---|---|---|
| A. Native CE semantics | PostgreSQL statistics-sensitive control and numerical behavior | Source audit, order/consumption probes, MCV and FD native instrumentation |
| B. CE-Replay representation | Workload-specialized executable semantics parameterized by design | IR-v0/v1/v1-B, FD semantics, mixed composition |
| C. Objective evaluation | Design → rows → q-error workload loss | Optimize-v0/v1/v4, deployment validations |
| D. Dependency/incremental evaluation | Affected queries, cache boundaries, invalidation | locality, semantic-state, pruning and semantic optimizers |
| E. Physical-design search | Budgeted selection and optional precedence moves | deterministic ADD/DROP/SWAP local search; Optimize-v2/v3 precedence studies |
| F. Physical realization | CREATE STATISTICS, OID order, ANALYZE and fresh payloads | MCV-Deploy-v0 and Mixed-Deploy-v0 |

## 2. Three distinct meanings of exactness

These claims must never be collapsed into one word.

**Semantic exactness.** Within the supported fragment,
`Replay(Y) ≈ NativePG(Y)`. Native v1-B matched 128/128 MCV designs with maximum
relative error `5.55e-16`. Mixed-Deploy-v0 matched all 468 queries after fresh
MCV+FD deployment within `1e-12`, with maximum relative error `8.05e-16` and
zero workload-loss discrepancy.

**Move-evaluation exactness.** Incremental evaluation returns the same move
objective and deterministic move as direct replay. Semantic-Optimizer-v0 and
Compositional-Semantic-Optimizer-v0 preserved their complete local-search
trajectories with no false safe-prunes or fast-path false positives.

**Search optimality.** The current large-scale search is not globally exact.
It exhaustively evaluates the *current neighborhood*, not every feasible
design. Global optimality was established only for explicitly enumerated small
candidate universes.

## 3. Current search algorithm

The optimizer is deterministic best-improvement local search over feasible
ADD, DROP and SWAP moves:

\[
m_t^*=\arg\min_{m\in\mathcal N(Y_t)}L(Y_t\oplus m).
\]

It accepts \(m_t^*\) only if the objective improves, otherwise it terminates.
“Exhaustive oracle” in the trajectory experiments means exhaustive enumeration
of \(\mathcal N(Y_t)\) at every round. It does not mean exhaustive enumeration
of the full budget-feasible subset space.

## 4. Chronological evidence map

The machine-readable companion contains one record per experiment. The
research progression is summarized below.

| Experiment | Question and result | Outcome | Consequence |
|---|---|---|---|
| Census locality | Can the workload split into independent components? One giant component contains 467/468 queries and all pair candidates; local degrees remain small. | Global negative, local positive | Abandon component decomposition; exploit affected-query sparsity. |
| Order sensitivity | Does physical creation/OID order matter? The same selected objects produced radically different estimates. | Positive | Preserve and, where studied, optimize precedence. |
| First-applicable pilot | Is the rule simply first-statistic-wins? Disjoint objects both contributed and the rule failed by up to 98.91x. | Negative | Model dynamic consumption and sequential composition. |
| Consumption/composition | Can winner consumption and numerical corrections reconstruct native behavior? Targeted masks and composition supported it. | Positive | Separate control, numerical and objective IR. |
| IR-v0 | Can five candidates support design-parametric replay? All 32 subsets were within 5% of rounded observations. | Positive pilot | Remove response probes and instrument native raw quantities. |
| IR-v1 | Can payloads directly drive replay? 128/128 were within 5%, but observation residual remained. | Positive, incomplete | Build v1-B pre-clamp oracle. |
| Native v1-B | Was the residual semantic? No: 128/128 floating-point matches, max `5.55e-16`. | Strong positive | Freeze reference MCV semantics. |
| Optimize-v0 | Can replay close a small exact design loop? All 32 designs and budget thresholds matched native exact optima. | Positive | Scale to Census. |
| Optimize-v1 | Does contextual optimization matter? At 2,253 candidates, random/singleton/marginal/local losses were `4922.86/6966.36/812.67/806.26`; incremental toggles were 47.7x faster. | Strong positive | Study semantic moves and precedence. |
| Optimize-v2 | Do semantic neighborhoods contain improving SWAPs? Most improving moves by count were disconnected budget exchanges; precedence refinement was cheap and useful. | Mixed | Keep global budget exchange; model reachable precedence. |
| Optimize-v3 | Are selection and precedence coupled? Alternating refinement reduced loss `812.671 → 795.512`. | Positive | Record coupling, but later mixed work fixes precedence. |
| MCV-Deploy-v0 | Does fresh deployment preserve semantics? 468/468 matched; frozen-to-fresh loss drifted +2.2992%. | Positive semantics | Separate payload uncertainty. |
| FD-Semantics-v0 | Can a different mechanism be replayed? FD selection/application and applicability probes matched native behavior. | Positive | Add explicit heterogeneous boundary. |
| Optimize-v4 | Does joint composition affect design? Joint loss `806.444` beat independent `813.942`; 72/97 independently selected FD objects became unconsumed. | Strong positive | Build mixed incremental evaluation. |
| CE-Semantic-State-v0 | Is projected execution state restart-safe? No; a lower-OID extension exposed a previously irrelevant selected object. | Negative | Distinguish execution state from counterfactual/restart state. |
| MCV-Commutativity-v0 | Does partial-order reduction remove the main explosion? 31.37% of enabled pairs commute, but PG already uses one canonical schedule. | Negative for design search | Do not optimize nonexistent interleavings. |
| MCV factorization | Can candidate responses factor? Scalar numerical composition works, but every nonempty Census graph is connected; zero subset reduction. | Negative for Census | Return to incremental local evaluation. |
| Semantic-Move-Pruning-v0 | Can one SWAP round avoid control replay? 95.29% cache-eligible, zero mismatches, same best move. | Positive | Test dynamic caches. |
| Semantic-Optimizer-v0 | Does MCV-only acceleration remain exact? Complete 18-round trace matched; 171.31x fewer control replays and 3.51x runtime speedup. | Strong positive | Make `Qstruct` invalidation mandatory. |
| Compositional optimizer | Does this generalize to MCV+FD? Complete trajectory matched and 95.13% of moves were numerical-only, but runtime was 145.68s versus 45.05s. | Correctness positive, performance negative | Bottleneck is numerical aggregation/move iteration. |
| Mixed-Deploy-v0 | Does fresh mixed deployment still match native? Frozen/fresh/native losses were `805.316/819.191/819.191`; 468/468 matched. | Strong positive semantics | Close current loop; expose payload robustness as next uncertainty. |

## 5. What semantics contributes to search

There are three separate contributions.

**Search-space reduction is weak.** In the mixed optimizer only `0.15%` of
moves were safely pruned. Semantic caching must not be described as pruning.

**Evaluation-cost reduction is strong logically.** `95.13%` of mixed move
evaluations were numerical-only. Query locality reduced hypothetical full-query
control work by `58.89x`, and mechanism-aware reuse reduced it by a further
`154.61x` beyond query-local replay.

**Dependency information is independently useful.** The semantics identifies
affected queries, the `MCV → FD` invalidation direction, reusable mechanism
boundaries, and which query-local cache entries must be invalidated.

The mixed Python implementation nevertheless ran slower than its factorized
exact oracle: `145.68s` versus `45.05s`. Replay occupied only about `6.58s`;
move iteration, safe-bound sorting and roughly 72 million numerical query
updates dominated. Semantic incremental evaluation reduces CE control work,
but does not currently make the complete mixed optimizer faster.

## 6. Negative representation results

### Restart-safe state quotient

Projected `(remaining clauses, current rows)` state can be sufficient to finish
the *current* execution. It is not sufficient to predict response after an
arbitrary design extension. A lower-OID candidate may change the winner and
expose a previously unconsumed selected statistic. A restart-safe state must
retain more counterfactual availability information; the conservative version
retains the selected subset and therefore gives no subset compression.

### Partial-order reduction

Disjoint MCV actions commute, and the Census condition had no false positives
in the tested exhaustive instances. But PostgreSQL already chooses one
canonical OID-ordered winner sequence. Execution interleaving is not the source
of the physical-design subset explosion, so partial-order reduction does not
materially reduce the outer search.

### Factorization

MCV numerical composition admits a compact normalized multiplier interface:
all 3,374,717 evaluated designs reconstructed within `1e-12`. Yet the all-pairs
Census candidate universe makes every nonempty per-query overlap graph
connected. Factor-table enumeration therefore saves exactly zero configuration
bits on this workload.

The combined conclusion is that the stable exploitable property is **local
affected-query and semantic-dependency sparsity, not global decomposability**.

## 7. Three interaction layers

**Control interaction** changes eligibility, winner selection, consumed
clauses, precedence behavior or downstream mechanism execution.

**Estimation interaction** is numerical composition of multiple statistic
contributions in CE, even if their control scopes are independent.

**Objective interaction** arises because q-error is nonlinear. Two
semantically independent corrections can have context-dependent objective
marginals:

\[
NoControlDependency\not\Rightarrow IndependentObjectiveMarginal.
\]

This explains why cached numerical composition may be exact while
`delta(DROP)+delta(ADD)` is not, and why singleton-benefit ranking can fail.

## 8. Validated PostgreSQL 16 semantics

### MCV

The validated fragment uses dynamic GreedyCover over compatible clauses. At
each round PostgreSQL maximizes newly covered unestimated dimensions, minimizes
the statistic's total key count, and breaks an exact tie by the catalog list,
which is ascending OID in the tested path. Winning clauses enter
`estimatedclauses`; eligibility is recomputed. Compatible disjoint statistics
can both contribute sequentially. Numerical contribution is reconstructed from
simple selectivity, matching MCV frequency, matching base frequency and total
MCV frequency. Physical precedence is therefore semantically relevant.

The demonstrated scope is the Census base-relation restriction predicate and
data-type fragment encoded in the frozen IR. It is not a claim about arbitrary
expressions, operators, joins or PostgreSQL versions.

### Functional dependencies

FD statistics expose an aggregate dependency payload. The tested native path
selects fully covered dependencies by maximum arity and then maximum degree;
an exact priority tie replaces the previous winner during scanning. Selecting
a dependency consumes its implied attribute, and numerical application occurs
in reverse selected order where required by the native implementation. Equality
forms and exact supported expression matches were validated. Range predicates,
inequality forms and nonmatching expressions were shown not to enter the same
FD path.

This mechanism is structurally different from MCV GreedyCover, which is
evidence that CE-Replay is not merely one hard-coded MCV formula.

### MCV-to-FD composition

The supported pipeline is

\[
MCV\rightarrow estimatedclauses\rightarrow FD\rightarrow rows.
\]

MCV consumption can remove clauses/attributes needed for downstream FD
applicability. This dependency is directed from MCV to FD at the control
boundary. Optimize-v4 demonstrated that independent optimization selected 97
FD objects of which 72 were suppressed in the composed design; joint semantics
selected 54 and left none unconsumed. In the complete compositional local
trajectory, four accepted MCV moves changed FD traces and one accepted move was
an MCV-to-FD SWAP.

No universal composition rule is claimed for other PostgreSQL mechanisms.

## 9. Physical-design and precedence evidence

Singleton benefit is inadequate because candidate response depends on current
winner competition, compatible sequential contributions, budget exchange and
nonlinear q-error. At full Census scale singleton greedy was worse than the
tested random baseline (`6966.36` versus `4922.86`), while marginal greedy
reached `812.67`; the singleton and marginal selected sets had low overlap.

Selection and precedence are separate but coupled dimensions. Optimize-v2
found only 194 selected candidates participating in reachable tie conflicts and
540 reachable tie edges, much smaller than arbitrary permutations. Fixed-set
precedence refinement improved `812.671 → 802.113`; alternating selection and
precedence reached `795.512`. However, the final mixed optimizer fixes
precedence, and Mixed-Deploy-v0 only preserves that policy. A final joint mixed
selection-plus-precedence design has not been optimized and deployed.

## 10. `Qstruct` versus `Qreal`

`Qreal(s)` denotes queries whose current output changes when candidate `s` is
toggled. `Qstruct(s)` conservatively denotes queries whose current or future
counterfactual responses may depend on `s`.

The first dynamic MCV optimizer attempt invalidated only currently changed
rows/traces. At the next round 2,771 fast evaluations were stale, even though
the oracle-best move still happened to agree. A move had left current outputs
unchanged while changing how later candidate toggles would behave. Invalidating
the complete structural query union removed every mismatch.

This is conceptually aligned with the execution-sufficient versus
restart-sufficient state distinction, but the two have not been proved
formally identical. The system principle is narrower and well supported:
**incremental physical-design evaluation requires conservative counterfactual
dependency tracking, not only realized-output invalidation.**

## 11. Physical deployment and uncertainty boundary

The frozen optimizer operates on payload repository \(P_0\):

\[
Y^*=\arg\min_Y L(Y;P_0).
\]

Deployment and fresh ANALYZE produce \(P_1\), and the deployed objective is
\(L(Y^*;P_1)\). Semantic validation asks a different question:

\[
Replay(Y;P_1)\approx NativePG(Y;P_1).
\]

Mixed-Deploy-v0 measured:

\[
L_{frozen}=805.316471766631,
\]

\[
L_{fresh\ replay}=L_{fresh\ PG}=819.191022950055.
\]

Thus payload/deployment drift was `+13.874551183424` (`+1.7229%`), while the
measured semantic workload discrepancy was zero. All 468 queries matched
within `1e-12`; maximum relative row error was `8.05e-16`. Fresh payload
storage changed `105,060 → 104,958` bytes. FD objects 97 and 683 generated no
fresh dependency payload and became unconsumed; FD traces changed on two
queries. This is payload realization uncertainty, not replay error.

The earlier MCV-only deployment independently showed the same conceptual
separation, with `+2.2992%` frozen-to-fresh drift and 468/468 replay/native
matches. Two single realizations do not establish a sampling variance model.

## 12. Strongest currently supported claims

| Claim | Evidence | Scope | Strength | Remaining caveat |
|---|---|---|---|---|
| Native consumption semantics, not singleton benefit alone, matters for statistics design. | Order, first-applicable, Optimize-v1 | PG16 Census MCV | Strong empirical | One workload and candidate construction |
| Statistics-sensitive CE can be specialized into a design-parametric executable replay program. | IR-v1-B, FD semantics | Supported base restrictions | Strong | Not general planner replay |
| MCV replay matches native CE. | v1-B; both deployments | Tested MCV predicates/payloads | Very strong | PG16.14 fragment only |
| FD replay matches native CE. | FD-Semantics-v0; mixed deployment final rows | Tested equality/expression fragment | Strong | Intermediate FD object identity not instrumented for all mixed queries |
| Heterogeneous MCV-to-FD state dependence is executable through an explicit boundary. | FD composition, Optimize-v4, mixed deployment | MCV+FD base restrictions | Strong | No other mechanism families |
| Joint semantics changes design decisions relative to independent optimization. | Optimize-v4 | Frozen Census payloads | Strong empirical | Search remains heuristic/local |
| Semantic dependencies enable exact incremental move evaluation. | Move pruning and both semantic optimizers | ADD/DROP/SWAP neighborhoods | Strong | Implementation-specific costs remain |
| Exact incremental evaluation preserves a deterministic local-search trajectory. | 18-round MCV and 20-round mixed audits | Tested starts/neighborhood | Very strong | Does not imply global optimum |
| Fresh deployment preserves replay/native equivalence. | MCV-Deploy and Mixed-Deploy | Supported fragment, single realization each | Very strong | Not sampling robustness |
| Fresh statistics realization is a separate uncertainty source. | Both deployments | Same table and target setting | Strong observation | Distribution across ANALYZE runs unknown |

## 13. Claims not currently supported

| Unsupported claim | Why it is unsupported |
|---|---|
| Globally optimal Census statistics design | Only local ADD/DROP/SWAP optimality is established at scale. |
| Exact optimization of the full feasible design space | “Exhaustive” large-scale results enumerate a move neighborhood, not all subsets. |
| General PostgreSQL CE replay | Only a narrow PG16.14 base-restriction MCV+FD fragment is implemented. |
| Join cardinality replay | No join CE path was modeled or validated. |
| PostgreSQL-version independence | Only the instrumented 16.14 semantics are grounded. |
| Universal composition across statistics mechanisms | Only MCV→FD was tested. |
| Robustness to ANALYZE sampling | Two single deployment realizations are not a distribution. |
| Query execution-time improvement | The objective is cardinality q-error; execution latency was not evaluated. |
| Globally optimal precedence | Reachable local precedence refinement is not exhaustive permutation optimization. |
| Mixed joint selection-plus-precedence deployment | Mixed selection kept precedence fixed. |
| Major mixed optimizer runtime acceleration | The mixed semantic implementation was 3.23x slower than its factorized oracle. |
| Major search-space reduction from semantics | Mixed safe pruning was only 0.15%. |
| General superiority over existing physical-design systems | No comparable end-to-end system study exists. |
| Payload-stable budget compliance | Payload sizes can change after ANALYZE. |

## 14. Novelty audit and contribution hierarchy

| Candidate | Assessment | Nature | Reason |
|---|---|---|---|
| C1: executable native-CE representation instead of learned response model | **Core** | Reusable abstraction / systems architecture | Unifies objective and dependencies and is validated end to end. |
| C2: PG16 MCV+FD semantic fidelity including composition | **Core evidence** | Empirical systems result | Gives credibility to C1 but must retain narrow scope. |
| C3: semantic dependencies for exact incremental evaluation | **Core** | Optimization technique / architecture | Complete trajectory audits establish utility beyond replay. |
| C4: joint semantics avoids suppressed mechanism choices | **Supporting** | Empirical optimization result | Strong ablation, but not a global solver theorem. |
| C5: semantic fidelity versus payload uncertainty | **Core systems insight** | Architecture / experimental methodology | Both deployments demonstrate the boundary cleanly. |
| C6: selection–precedence interaction | **Supporting/future work** | Empirical observation | Strong MCV evidence, absent from final mixed deployment. |

The smallest coherent contribution set is C1+C3+C5, supported by C2 and the
C4 ablation. C6 should not be central to the current paper.

None of these is currently a general theoretical result. Source-derived
semantics and exhaustive fixture validation are empirical/system construction;
the reusable novelty lies in the executable representation and its dual use as
objective and dependency oracle.

## 15. Search-algorithm gap

Under an **evaluator paper** framing, local search is sufficient to demonstrate
that replay can drive design decisions and exact incremental evaluation. The
lack of a global solver is not fatal if claims are disciplined.

Under a **physical-design algorithm** framing, the gap is serious. There are no
approximation guarantees, no global-quality bound at 2,253 or 3,011 candidates,
and limited workload comparison. A reviewer could attribute design quality to
an arbitrary local optimum.

Under a **systems architecture** framing, complete trajectory preservation,
heterogeneous state reuse and deployment closure are substantial even without
a novel global solver. This is the strongest current framing.

Global enumeration exists only for Optimize-v0's five candidates/32 designs
and the reduced exact-small Optimize-v1 cases. Those results validate plumbing
and show the heuristics can find small optima; they cannot be extrapolated to
Census scale. A reduced-set exact-solver quality experiment would materially
strengthen optimizer-quality claims, but is not necessary to establish the
core executable-CE architecture.

## 16. Ranked next experiments

| Rank | Experiment | Claim strengthened | Cost | Scientific value / risk | Required before submission? |
|---:|---|---|---|---|---|
| 1 | Repeated ANALYZE deployment study | Quantifies \(P_0→P_1\) robustness and budget drift | Medium | Very high; may expose instability | **Recommended** for core paper |
| 2 | Second workload with the same MCV+FD pipeline | Generality beyond Census | High | Very high; risk that structure/semantics differ | Strongly recommended |
| 3 | Reduced candidate sets with exact global solver | Local-search quality gap | Medium | High for optimizer framing | Required only if optimizer quality is central |
| 4 | Query execution-time evaluation | Practical value of q-error changes | Medium/high | High but confounded by plan changes | Recommended if systems impact is claimed |
| 5 | Second PostgreSQL version | Version sensitivity | Medium | Moderate/high | Useful, not mandatory with narrow PG16 claim |
| 6 | Mixed selection-plus-precedence deployment | Completes C6 | High | Moderate; expands design space | Future work for current framing |
| 7 | Vectorized/batched optimizer | Runtime engineering | Medium | Useful but limited scientific novelty | Not required; current negative result is honest |
| 8 | Stronger global search algorithm | Optimizer quality | High | Uncertain; risks shifting paper identity | Not required for architecture framing |
| 9 | Joins | Much broader CE scope | Very high | High value, high scope explosion | Explicit future work |

If exactly one experiment is available, repeated ANALYZE is the best choice:
the current semantic claim is already strong, while deployment robustness is
the largest uncertainty directly exposed by the final experiment.

## 17. Paper framing candidates

### A. CE-Replay / executable CE specialization — recommended

**Thesis:** Native statistics-sensitive CE can be specialized into a
workload-level executable program that is faithful enough to serve as both a
physical-design objective and dependency oracle.

The primary contribution is CE-Replay; the optimizer is a demonstration
consumer; PostgreSQL provides a source-grounded semantics and validation
target. Strongest experiments are v1-B, FD semantics, complete incremental
trajectories and both deployments. The largest reviewer objection is breadth:
one DBMS version, one workload and no joins.

### B. Semantics-guided statistics physical design

**Thesis:** Modeling native consumption and composition enables materially
better statistics choices than singleton-response heuristics.

The optimizer becomes central, with Optimize-v1/v4 and incremental evaluation
as evidence. PostgreSQL is the concrete target. The largest objection is the
absence of global-quality evidence, guarantees and broad baselines.

### C. Compositional extended-statistics optimization

**Thesis:** Explicit mechanism boundaries permit correct joint optimization
and incremental evaluation across heterogeneous extended statistics.

The primary contribution is MCV→FD composition; the optimizer demonstrates
joint choices and caching. Strongest experiments are FD-Semantics-v0,
Optimize-v4, the compositional trajectory and Mixed-Deploy-v0. The objection
is that only two mechanisms and one directed composition edge are covered, and
the mixed implementation has negative runtime speedup.

Framing A is best supported. Framing C is a strong secondary story inside it;
framing B currently overweights the weakest layer, global search quality.

## 18. Final research-gap verdict

1. **Single strongest contribution:** a source-grounded, workload-specialized,
   design-parametric executable CE representation that matches native PG16 MCV
   and FD behavior at measured floating-point precision and also exposes exact
   incremental dependencies.
2. **Strongest negative result:** compact global decomposition does not emerge
   on Census—restart-safe projection fails, partial-order reduction targets the
   wrong space, and the semantic factor graph is connected.
3. **Most important systems insight:** semantic fidelity and fresh-payload
   realization are separate interfaces and uncertainties; replay can be exact
   on \(P_1\) even when optimization over \(P_0\) drifts materially.
4. **Most important optimization insight:** semantics mainly reduces move
   evaluation cost through conservative local dependencies; it does not
   materially prune the combinatorial search space.
5. **Largest unsupported claim to avoid:** that the system finds the globally
   optimal statistics design, or is an “exact optimizer” without qualification.
6. **Is stronger search necessary?** No for the core evaluator/systems paper;
   yes if the paper is framed primarily as a new physical-design algorithm.
7. **One additional experiment:** repeated clean deployment/ANALYZE runs to
   quantify payload, objective, consumption and storage variability.
8. **Freeze now:** PG16 MCV and FD replay semantics, CE-Replay-IR boundary,
   deterministic local neighborhood, `Qstruct` invalidation rule, mixed
   deployment protocol and current evidence artifacts.
9. **Future work:** robust optimization over payload distributions, stronger
   global search, vectorized move aggregation, other workloads/versions,
   mixed precedence, joins and other CE mechanisms.
10. **Recommended thesis:** *A workload-specialized executable representation
    of native cardinality-estimation semantics can serve as both a faithful
    physical-design objective and a dependency oracle for exact incremental
    statistics design, while cleanly separating semantic correctness from
    fresh-statistics realization uncertainty.*

