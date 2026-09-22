# Paper-Architecture-v0

## 1. Paper thesis and scope

### One-sentence problem

The paper studies **resource-constrained physical design of extended statistics for a supplied target workload**: given a database, target workload, candidate extended statistics, and recurring statistics-maintenance budget, choose a physical statistical state that minimizes target-workload cardinality-estimation loss.

The target workload is an input, not a training set. Unseen-workload generalization is not part of the primary formulation.

### One-sentence thesis

> A DBMS's statistics-sensitive cardinality-estimation semantics can be specialized into a workload-specific, design-parametric executable program that serves as both an exact-within-scope objective evaluator and a semantic dependency oracle for maintenance-constrained extended-statistics physical design.

### Canonical name

Use **CE-Replay** as the name of the representation and method. Define it once as the workload-specialized, design-parametric executable replay of the supported statistics-sensitive CE fragment. Use “executable CE specialization” and “workload-specialized CE replay” only as descriptive phrases.

CE-Replay is not the name of the local-search algorithm, not the full prototype stack, and not an automatic PostgreSQL-source compiler. A separate prototype/system name is unnecessary.

## 2. Frozen research questions

1. **RQ1 — Objective semantics.** Can statistics-sensitive native PostgreSQL CE be represented as a design-parametric executable program that matches native PostgreSQL within an explicit supported fragment?
2. **RQ2 — Physical-design optimization.** Can executable replay evaluate hypothetical statistics designs and drive resource-constrained physical design without a separately learned q-error response model?
3. **RQ3 — Semantic incremental evaluation.** Can executable CE semantics expose dependencies/state that enable exact incremental move evaluation rather than repeated full-workload/control replay?
4. **RQ4 — Composition and deployment.** Can the approach handle interacting MCV+FD semantics and survive physical deployment, fresh payload generation, and native PostgreSQL validation?

No fifth RQ should be introduced.

## 3. Logical argument dependency chain

The paper follows this chain, not experiment chronology:

1. **Selection is intrinsically meaningful.** Empty is not generally best; all statistics are not generally best; inclusion can be harmful in both workloads.
2. **A resource constraint is independently necessary.** Statistics impose recurring `ANALYZE` maintenance work, and MCV/FD have different empirical aggregate prices.
3. **Candidates interact through native control semantics.** MCV selection and clause consumption alter downstream FD applicability; PostgreSQL-specific precedence can alter tied choices.
4. **CE-Replay makes this response executable.** It separates workload-fixed context, payload/schema, design-dependent state, and executable native rules.
5. **Replay becomes an optimization oracle.** The solver evaluates hypothetical designs under a general maintenance-cost constraint without learning a design-to-error surrogate.
6. **Replay also becomes a dependency oracle.** Realized and counterfactual dependencies determine exact invalidation and incremental move evaluation.
7. **The loop closes physically.** Selected states are deployed, fresh payloads are generated, and replay is compared with native PostgreSQL.

The dependency order answers why the problem exists before explaining how the method works.

## 4. Final section hierarchy

### 1. Introduction

**Purpose:** establish the physical-design problem, two independent motivations, CE-Replay insight, evidence breadth, and four contributions.

**Claims introduced:** C2 non-monotonicity, C4 maintenance need, high-level C1/C9/C13 thesis.

**Concepts defined:** target workload, statistics design, maintenance budget, CE-Replay at one-sentence level.

**Evidence used:** one compact cross-workload non-monotonicity statement; independent maintenance calibration; two-workload fresh native validation summary.

**Figures/tables:** none required; optionally reference F1 without explaining internals.

**Must not discuss:** source function names, optimizer chronology, Census query IDs, generalization splits, detailed formulas, implementation cache levels.

### 2. Background and Motivation

**Purpose:** introduce only the PostgreSQL and CE concepts needed to understand why statistics design is interactive and costly.

**Claims introduced:** semantic and resource necessity remain independent.

**Concepts defined:** ordinary statistics, extended statistics, MCV, functional dependencies, `ANALYZE`, estimates versus truth, q-error, statistics consumption.

**Evidence used:** compact motivation-level within-workload non-monotonicity examples; no complete evaluation table.

**Figures/tables:** may preview F2 conceptually; detailed results remain in Section 8.

**Must not discuss:** exhaustive experiment results, source instrumentation, full PostgreSQL manual material, learned-CE survey.

### 3. Problem Formulation

**Purpose:** define the physical state, replay objective, maintenance constraint, and distinction between definition, payload, and realization.

**Claims introduced:** general formulation is maintenance-cost constrained and DBMS-aware without universally equating design with a permutation.

**Concepts defined:** target workload, candidate universe, selected set, physical realization, payload repository, workload context, replay estimate, query/workload loss, maintenance function and budget.

**Figures/tables:** none.

**Experiments referenced:** none; empirical cost instantiation is deferred.

**Must not discuss:** Census's old byte budget as the primary model, production solver global optimality, training/test terminology.

### 4. Statistics-Sensitive CE Semantics

#### 4.1 Running example

Use one fictional conjunctive query over three attributes and two overlapping MCV statistics. Show:

- both candidates are applicable;
- GreedyCover chooses the object covering more currently unestimated dimensions;
- ties follow PostgreSQL's physical list/OID precedence;
- the winner consumes covered clauses;
- later MCV and FD applicability therefore changes.

Extend the same example with one FD only if it remains visually compact. The point is that independent candidate scores cannot encode stateful consumption.

#### 4.2 MCV semantics

Explain applicability, GreedyCover, newly covered dimensions, tie handling, clause consumption, numerical MCV/base-frequency combination, repeated disjoint rounds, and constant ScalarArray matching. Keep exact PostgreSQL function/line mappings in Appendix A.

#### 4.3 FD semantics and directed composition

Explain that FD uses aggregated matching dependencies rather than MCV's ChooseOne program; it applies degrees and consumes implied attributes. MCV executes first, so FD sees the residual estimated-clause state. This motivates compositional state transitions, not independent correction factors.

**Claims introduced:** C7 and the semantic basis of C8/C15.

**Figures/tables:** F4's semantic half may be introduced here and completed with empirical counts in Section 8.4.

**Experiments referenced:** MCV consumption/composition, FD-Semantics-v0, creation/OID-order probe, ScalarArray semantics.

**Must not discuss:** all evaluation counts, optimizer algorithms, unsupported joins as if implemented.

### 5. CE-Replay

#### 5.1 Representation

Organize the representation into four blocks:

1. **Workload-fixed context:** clauses, relation cardinality, ordinary/simple selectivities, truth used later only for loss.
2. **Payload/schema context:** MCV items/frequencies/base frequencies, FD degrees, semantic dimensions, `stxkeys` order, availability.
3. **Design-dependent state:** selected/physically realized objects and relevant DBMS-specific realization state such as PostgreSQL precedence.
4. **Executable semantics:** eligibility, GreedyCover, clause consumption, MCV numerical combination, FD application, and final row computation.

Design-dependent decisions remain executable. Never freeze a winner observed under one design and call it replay.

#### 5.2 What replay predicts

The causal chain is:

`physical statistics state → native consumption semantics → DBMS cardinality estimate → query loss`.

CE-Replay reproduces the DBMS estimate; it does not predict true cardinality. Ground truth enters only after replay to compute the design objective.

#### 5.3 Pipeline and acquisition boundary

Use F1 to show native semantic analysis/instrumentation, specialization, objective/dependency outputs, search, deployment, fresh payload, and native validation. Mark candidate payload acquisition as offline and outside the recurring maintenance objective.

**Claims introduced:** C1, C15, C16.

**Figures/tables:** F1.

**Experiments referenced:** v1-B, FD semantics, ScalarArray semantics.

**Must not discuss:** automatic compilation of arbitrary PostgreSQL source, full planner replay, search results.

### 6. Semantics-Guided Physical Design

#### 6.1 Constrained design

Present the generic maintenance-constrained objective. Distinguish the mathematical optimum from the algorithm output.

#### 6.2 Final solver

Describe only the core solver actually evaluated across the final experiments:

- deterministic marginal-greedy initialization;
- maintenance-feasible ADD, DROP, and SWAP neighborhood;
- exact CE-Replay objective values;
- deterministic best-improvement/termination;
- fixed precedence in final cross-workload optimization.

Earlier precedence optimization is semantic supporting evidence, not a central production feature.

#### 6.3 Semantic dependency oracle

Define:

- **realized dependency:** an object participates in the current trace or numeric response;
- **structural/counterfactual dependency:** an object can change a future counterfactual evaluation even if the current output is equal.

Use the restart-state counterexample to explain why current-output equality is insufficient for safe invalidation.

#### 6.4 Exact incremental move evaluation

Describe the evaluation hierarchy only to the detail supported by artifacts: safe pruning, cached numerical update, local MCV control replay, downstream FD replay, and full-workload fallback. State the exact claim: fewer semantic/control operations while preserving audited move values and trajectories. Acknowledge that numerical aggregation dominated the mixed implementation and eliminated wall-clock speedup.

**Claims introduced:** C9, C12.

**Figures/tables:** none; results go to T3/T4.

**Experiments referenced:** Semantic-State, Move-Pruning, Semantic-Optimizer, Compositional-Semantic-Optimizer.

**Must not discuss:** global-optimum claims, approximation ratios, universal speedup.

### 7. Experimental Methodology

**Purpose:** explain evaluation design by RQ and why the workloads are complementary.

**Census:** 468 queries; 68 predicate columns; 2,253 structural pair candidates; sparse candidate-query incidence with mean candidate degree 4.44; useful for large candidate-space and locality evaluation.

**DMV:** 1,965 queries over 11 text columns, nine predicate columns, all 36 structural pairs, dense/high-reuse incidence with candidate mean degree about 497, and 1,913 IN-bearing queries; useful for dense topology and ScalarArray replication.

**Methodology blocks:** native raw instrumentation boundary, payload freezing, target-100 realizations where applicable, q-error objective, maintenance calibration, exhaustive/restricted audits, physical deployment, and fresh validation.

**Figures/tables:** T1.

**Must not discuss:** DMV as large candidate-space scalability evidence; cross-workload comparison of raw objective magnitude; DMV baseline and optimization loss as one paired realization.

### 8. Evaluation

#### 8.1 RQ1 — Does replay match native PostgreSQL?

Evidence order: MCV v1-B, FD validation, ScalarArray synthetic/regression, real frozen DMV, final fresh Census and DMV deployments. Use T2. End with the explicit supported semantic boundary.

#### 8.2 RQ2 — Does replay drive useful resource-constrained design?

Evidence order:

1. F2 non-monotonicity establishes selection need.
2. F3 maintenance calibration establishes the resource.
3. T3 reports Census and DMV maintenance-budget designs.
4. Small/restricted exhaustive audits bound optimization correctness.
5. Terminal audits establish tested-neighborhood local optima.

Do not combine incompatible DMV absolute losses. Report the zero-truth issue where the DMV objective first appears.

#### 8.3 RQ3 — Does semantic dependency reduce move-evaluation work?

Use T4 to compare sparse Census MCV, Census mixed, and dense DMV. Lead with exact trajectory/move preservation, then control-work reduction, then runtime qualification. State that the topology changes the magnitude, not the validity, of dependency-aware evaluation.

#### 8.4 RQ4 — Do interacting mechanisms survive deployment?

Use F4 for directed MCV-to-FD composition and T5 for deployment. Contrast all-statistics FD suppression with optimized FD use. Separate physical realization, fresh semantic fidelity, and frozen-to-fresh stability. Mark the DMV paired numerical drift cell explicitly unavailable because frozen per-query provenance was not persisted.

### 9. Discussion and Limitations

Group rather than enumerate limitations:

1. **Semantic/DBMS boundary:** PostgreSQL 16.14; supported conjunctive base restrictions; MCV and FD; no join/full planner/arbitrary predicate replay.
2. **Optimization/acquisition boundary:** offline payload acquisition; fixed payload/precedence; local search rather than global solution.
3. **Resource/objective boundary:** empirical environment-specific first-order cost; q-error rather than execution performance; DMV zero-cardinality floor pathology.
4. **Deployment/evidence boundary:** payload drift; DMV frozen per-query provenance missing; two primary workloads.
5. **Workload boundary:** supplied target workload, no core unseen-workload claim.

Include a short repeated-ANALYZE paragraph: Census's 30 runs show payload realization variability and 14,040/14,040 semantic matches; do not infer design-ranking stability. DMV's missing provenance is not stochastic evidence.

### 10. Related Work

Organize by question, not citation chronology:

| Category | Prior abstraction/problem | Positioning question for this paper |
|---|---|---|
| Physical database design | Select persistent structures under resource constraints | Statistics are physical statistical state affecting beliefs, not unrelated metadata. |
| Index/materialized-view advisors | Change access/action and plan space | This work changes the estimator's information state. |
| What-if optimization | Evaluate hypothetical physical configurations | CE-Replay specializes statistics-sensitive estimate response. |
| INUM/optimizer specialization | Reuse/specialize plan-cost response | This paper specializes CE response rather than plan templates. |
| Classical cardinality estimation | Estimate selectivity/cardinality | The native estimator remains fixed. |
| Learned CE | Learn/replace estimator behavior or true cardinalities | CE-Replay neither learns truth nor replaces native CE. |
| Extended-statistics selection | Choose/configure statistics | Compare objective semantics, interactions, and resource model precisely; avoid novelty claims based only on using extstats. |
| Statistics maintenance | Collection/refresh tradeoffs | This paper uses measured recurring maintenance as the design resource. |

Avoid claiming that prior advisors simply invoke an optimizer blindly. Literature-specific novelty claims require later citation review.

### 11. Conclusion

Restate the bounded thesis, answer four RQs in one sentence each, and finish with the distinction between native-semantic correctness, local-search guarantee, and physical deployment. Do not introduce future generalization results or new experiments.

## 5. Introduction paragraph blueprint

1. **Problem context:** query optimizers rely on cardinality estimates; systematic estimation errors affect optimizer decisions.
2. **Opportunity:** extended statistics expose multivariate information to a native estimator.
3. **Semantic challenge:** statistics interact through selection and consumption; both workloads contain harmful additions, so “build everything” is not a valid default even with capacity.
4. **Resource challenge:** deployed objects add recurring `ANALYZE` work; independent Census/DMV calibration motivates maintenance-aware constraints.
5. **Evaluation challenge:** combinatorial design requires evaluating many hypothetical states; repeatedly rebuilding and querying the full DBMS is awkward and expensive.
6. **Key insight:** specialize the supported native statistics-sensitive CE semantics into CE-Replay instead of learning a separate design-to-q-error map.
7. **Dual use:** CE-Replay returns objective values and exposes semantic dependencies for exact incremental moves.
8. **Evidence preview:** floating-point-level native fidelity, sparse and dense workload optimization, MCV+FD composition, and two fresh physical deployments; mention the explicit PostgreSQL/base-restriction scope.
9. **Contributions:** four bullets from Section 13 below.

Do not begin with Census, implementation functions, or ML terminology.

## 6. Mathematical formulation and notation freeze

All notation first appears in Section 3. Use only the following symbols.

| Symbol | Meaning | Scope | First use |
|---|---|---|---|
| `Q` | supplied target workload | paper-wide | Section 3 |
| `q` | one target query | local/paper-wide | Section 3 |
| `N_q` | true cardinality used to score query `q` | objective only | Section 3 |
| `S` | candidate-statistic universe | paper-wide | Section 3 |
| `Y` | selected candidate subset | design variable | Section 3 |
| `rho` | DBMS-specific physical realization | optional/general | Section 3 |
| `P` | payload repository/snapshot | evaluator input | Section 3 |
| `W_q` | workload-fixed query context | replay input | Section 3/5 |
| `F` | CE-Replay executable semantics | method | Section 3/5 |
| `Nhat_q` | replayed/native estimate for query `q` | objective | Section 3 |
| `ell` | per-query loss, instantiated as q-error | objective | Section 3 |
| `L` | aggregate target-workload loss | objective | Section 3 |
| `C` | general recurring maintenance-cost function | constraint | Section 3 |
| `B` | maintenance budget | constraint | Section 3 |

The formulation is:

$$
\widehat{N}_q(Y,\rho;P)=F(W_q,Y,\rho,P)
$$

$$
L(Y,\rho;P)=\sum_{q\in Q}w_q\,\ell\!\left(\widehat{N}_q(Y,\rho;P),N_q\right)
$$

$$
\min_{Y,\rho} L(Y,\rho;P)
\quad\text{subject to}\quad
C(Y,\rho)\le B
$$

The evaluated q-error instantiation is:

$$
\ell(\widehat{N},N)=\max\!\left(\frac{\widehat{N}}{N},\frac{N}{\widehat{N}}\right)
$$

with the implementation's documented positive floor for zero values. Do not add symbols for optimizer rounds, cache states, or cost-model coefficients in the main formulation; define those locally in prose or figure captions.

## 7. Terminology freeze

| Canonical term | Exact meaning | Avoid/limit |
|---|---|---|
| target workload | supplied workload optimized by the design procedure | Never “training workload” in the core formulation |
| candidate statistic | one possible extended-statistics definition plus typed mechanism identity | Avoid conflating definition with payload |
| selected design | candidate subset selected by search | Do not imply it includes an arbitrary permutation universally |
| physical realization | DBMS-specific realization of a selected design, including relevant order/state | Use instead of “selection plus permutation” |
| frozen payload | payload snapshot used during hypothetical optimization | Not guaranteed reproducible after ANALYZE |
| fresh payload | payload generated by deployment's fresh ANALYZE | Not a validation label by itself |
| CE-Replay | workload-specialized, design-parametric executable representation/method | Not system name, optimizer, learned model, or full PostgreSQL CE |
| workload-fixed context | query/relation/simple-selectivity inputs independent of candidate selection for a fixed realization | Avoid “frozen winner” |
| semantic dependency | relation showing that a move may change replay control or numeric output | Not merely graph co-occurrence |
| realized dependency | dependency exercised by the current trace | Not sufficient alone for invalidation |
| structural/counterfactual dependency | potential dependency under a design move/future execution | Prefer this exact paired term |
| maintenance cost | recurring statistics collection/refresh resource | Primary resource term |
| payload realization drift | difference caused by fresh payload/context realization | Not semantic replay error |
| semantic replay error | replay/native discrepancy for the same realization | Keep separate from payload drift |

Historically limited terms:

- **byte budget:** only for the earlier controlled proxy and direct Census comparison.
- **q-error predictor:** not CE-Replay; use only to say no separate predictor is needed.
- **black-box optimizer:** avoid; it obscures native semantic structure.
- **replay PostgreSQL CE:** prohibited without “supported statistics-sensitive base-restriction fragment of PostgreSQL 16.14.”
- **train/test:** restricted to archived generalization experiments, not the core paper.

## 8. Main figure/table budget

The main text uses **four figures and five tables**. Full specifications are in [`paper-figure-table-plan-v0.json`](../results/paper-figure-table-plan-v0.json).

### Figures

- **F1:** CE-Replay physical-design pipeline — Sections 5 and 6; supports the architecture and C1/C9/C13.
- **F2:** Cross-workload non-monotonicity — Section 8.2; supports C2/C3.
- **F3:** Mechanism-aware recurring ANALYZE cost — Section 8.2; supports C4/C5.
- **F4:** Directed MCV-to-FD composition — Section 8.4; supports C7/C8.

### Tables

- **T1:** Complementary workload and candidate structure — Section 7.
- **T2:** Native semantic fidelity — Section 8.1.
- **T3:** Maintenance-budget physical-design outcomes — Section 8.2.
- **T4:** Exact incremental evaluation under sparse/dense incidence — Section 8.3.
- **T5:** Physical deployment and fresh native validation — Section 8.4.

RQ mapping:

- RQ1: T2, with F1 defining the evaluated object.
- RQ2: F2, F3, T3.
- RQ3: T4.
- RQ4: F4, T5.

## 9. Result-presentation rules

### Non-monotonicity

Use within-workload panels. For Census report empty, all, and optimized strict subset from `Statistics-Nonmonotonicity-v0`, plus 1,560 harmful singleton additions and 317 improving removals. For DMV report empty, all-MCV, all-FD, all-mixed, 45 harmful singleton additions, and 17 improving removals from `DMV-Baseline-and-Nonmonotonicity-v0`.

The later DMV optimized subset belongs to a new realization. It may show that an optimized subset beats empty/all inside that later experiment, but its absolute loss must not be paired with baseline values. Because two zero-truth queries dominate DMV's raw objective, never compare Census and DMV aggregate loss magnitude.

### Maintenance cost

F3 uses separate panels/fits. Report Census slopes about 1.875 and 2.717 ms/object, and DMV combined coefficients 3.904 and 5.907 ms/object. State that normalized ratios differ. Put R-squared/fit errors in caption/table; explicitly mention the DMV final deployment error of 21.4295% in evaluation and limitations.

### Replay fidelity

T2 includes only strongest results: Census v1-B MCV; FD validation; 29/29 ScalarArray fixtures and 128/128 regression; 27,510/27,510 real DMV comparisons; 468/468 fresh Census; 1,965/1,965 fresh DMV. Intermediate rounded EXPLAIN comparisons are appendix/history.

### Incremental evaluation

T4 compares topology, exactness, avoided control work, and runtime separately. Census MCV supports 171.31× fewer control replays and 3.51× phase speedup. Census mixed preserves trajectory but is slower wall-clock, 145.68 versus 45.05 seconds. DMV avoids 67.91% of full-workload query replay operations under dense incidence; do not translate this to an unmeasured speedup.

### Composition

F4 pairs semantics with evidence. Census independent optimization selected many FDs later suppressed; joint optimization improved loss and consumption. DMV all-statistics consumed zero of 34 available FDs, whereas the optimized frozen design consumed 12, and fresh deployment consumed all 11 materialized FDs in 389 queries.

### Deployment

T5 separates:

1. physical realization/order;
2. fresh semantic fidelity;
3. frozen-to-fresh realization stability.

Census supports all three. DMV supports the first two; the third must read: **Unavailable: frozen per-query provenance not persisted.** Do not leave the field blank.

## 10. Evidence traceability and realization boundaries

The complete section/claim/artifact mapping is in [`paper-evidence-map-v0.json`](../results/paper-evidence-map-v0.json). Apply these rules during drafting:

1. Every empirical sentence must cite a mapped frozen experiment.
2. Native/replay comparisons require the same payload realization and physical state.
3. Census non-monotonicity, maintenance optimization, and deployment numbers are paired only where their artifacts explicitly preserve the same frozen state.
4. DMV baseline/non-monotonicity and DMV maintenance optimization are different realizations; use them for replicated qualitative claims, never as a paired numerical trajectory.
5. DMV deployment fresh values are authoritative; the frozen aggregate exists, but the per-query vector and required numerical context do not.
6. Cross-workload comparisons should use topology, coverage, error tolerance, counts, or within-workload changes—not raw q-error magnitude.

## 11. Abstract blueprint

Do not draft final prose yet. Use five units:

1. **Problem:** extended-statistics physical design for a supplied workload under recurring maintenance capacity.
2. **Challenge:** native consumption is stateful/compositional and empirically non-monotone; rebuilding every hypothetical state is unsuitable for combinatorial search.
3. **Approach:** CE-Replay specializes supported native semantics into a design-parametric evaluator and dependency oracle, coupled to deterministic maintenance-constrained local search.
4. **Evidence:** two structurally different workloads; native fidelity including 468/468 and 1,965/1,965 fresh comparisons; sparse and dense incremental evaluation; deployed mixed MCV+FD states.
5. **Scope/result:** PostgreSQL 16.14 supported conjunctive base-restriction MCV+FD fragment, with local rather than global optimization and environment-specific maintenance calibration.

Numbers suitable for the abstract are limited to: two workloads; 468/468 and 1,965/1,965 fresh native matches; optionally one maximum-error range if space permits. Do not use Census-specific optimizer speedups, raw DMV objective magnitude, or universal maintenance coefficients.

## 12. RQ answer blueprint

### RQ1

**One-sentence answer:** Yes, within the explicit PostgreSQL 16.14 statistics-sensitive base-restriction fragment, CE-Replay matches native raw estimates to the reported floating-point tolerances.

**Strongest evidence:** four-target × 32-design Census MCV validation; FD semantic scenarios; 29/29 ScalarArray cases plus 128/128 scalar regressions; 27,510/27,510 real DMV comparisons; both fresh deployments.

**Qualification:** no joins, full planner, arbitrary expressions/operators, or all PostgreSQL CE.

**Main item:** T2.

### RQ2

**One-sentence answer:** Yes, replay evaluates hypothetical designs and drives maintenance-constrained selection without a learned design-to-q-error model.

**Strongest evidence:** cross-workload harmful additions/removals; independent maintenance models; Census 276+7 and DMV 11+12 designs; five-candidate Census exhaustive agreement and 4/4 restricted DMV recovery.

**Qualification:** workload-scale outputs are tested-neighborhood local optima under fixed payload/precedence.

**Main items:** F2, F3, T3.

### RQ3

**One-sentence answer:** Yes, semantic dependencies permit exact audited incremental move evaluation in both sparse and dense incidence regimes.

**Strongest evidence:** identical Census MCV trajectory; identical Census mixed trajectory; 171.31× control-replay reduction in MCV; DMV avoids 67.91% of full-workload query replay operations.

**Qualification:** the Census mixed implementation had no wall-clock speedup, and DMV does not establish large-candidate scalability.

**Main item:** T4.

### RQ4

**One-sentence answer:** Yes, MCV and FD interact through clause-consumption state, and optimized mixed states survive physical deployment and fresh native validation on both workloads.

**Strongest evidence:** Census joint versus independent FD consumption; DMV zero FD consumption under all-statistics versus 12 frozen optimized; exact design/order deployment; 468/468 and 1,965/1,965 fresh matches.

**Qualification:** DMV lacks paired frozen-to-fresh per-query numerical provenance; one selected FD did not materialize fresh.

**Main items:** F4, T5.

## 13. Final contribution bullets

1. **Problem and representation.** We formulate extended-statistics physical design for a supplied workload under recurring maintenance cost and represent the native statistics-sensitive response as a design-parametric executable program. Evidence type: formalization plus cross-workload non-monotonicity/cost calibration. Scope: supported PostgreSQL 16.14 base restrictions.
2. **CE-Replay semantics.** We develop CE-Replay for interacting MCV and functional-dependency semantics, including constant ScalarArray predicates, and validate it against native raw estimates. Evidence type: controlled semantic tests and real/fresh workload comparisons. Scope: explicit conjunctive fragment, not arbitrary PostgreSQL CE.
3. **Semantics-guided optimization.** We use CE-Replay as both an exact-within-scope objective evaluator and semantic dependency oracle for deterministic maintenance-constrained ADD/DROP/SWAP local search. Evidence type: exhaustive/restricted audits and exact incremental trajectories. Scope: local rather than full global optimality.
4. **Cross-workload physical validation.** We demonstrate non-monotone effects, maintenance-aware mixed designs, dependency-aware evaluation, and physical deployment on sparse Census and dense IN-heavy DMV. Evidence type: two workload-scale evaluations and fresh native validation. Scope: two workloads, one PostgreSQL version, no execution-time claim.

These four groupings are preferable to one contribution per experiment. Do not claim novelty merely from using PostgreSQL extended statistics.

## 14. Negative results and appendix architecture

### Main-text negative results

- **Budget-locality distinction:** locality can reduce evaluation work but cannot restrict all improving swaps because disconnected objects exchange global budget. Mention briefly in Section 6.
- **No automatic runtime speedup:** mixed control-work reduction did not improve wall-clock time. Report in RQ3 and limitations.
- **Dense incidence weakens locality:** DMV still benefits, but less than sparse Census. Report in T4.
- **DMV provenance failure:** report in T5 and limitations.

### Appendix-only negative results

- giant connected component/no useful component decomposition;
- first-applicable proxy failure;
- restart-safe state compression counterexample;
- commutativity without outer-space reduction;
- semantic factorization without nontrivial Census factors.

### Appendix structure

- **Appendix A:** PostgreSQL source-semantic mapping and native instrumentation.
- **Appendix B:** complete MCV, FD, and ScalarArray semantic fixtures/formulas.
- **Appendix C:** creation/OID precedence witnesses.
- **Appendix D:** five-candidate and restricted exhaustive audits; terminal neighborhood audits.
- **Appendix E:** invalidation counterexamples and rejected shortcuts/decompositions.
- **Appendix F:** full Census/DMV maintenance-model diagnostics and residuals.
- **Appendix G:** repeated Census ANALYZE realization robustness.
- **Appendix H:** DMV frozen-provenance audit.
- **Appendix I/artifact:** full 39-experiment inventory and claim matrix.

Generalization experiments remain repository future-work artifacts, not the paper appendix, unless reviewers specifically request historical context.

## 15. Reproducibility artifact map

| Main result | Script(s) | Result JSON | Report/deployment artifact |
|---|---|---|---|
| Cross-workload non-monotonicity | `tools/statistics_nonmonotonicity_v0.py`; `tools/dmv_baseline_nonmonotonicity_v0.py` | `results/census_statistics_nonmonotonicity_v0.json`; `results/dmv_baseline_nonmonotonicity_v0.json` | Corresponding Markdown reports |
| Census/DMV maintenance calibration | `tools/analyze_cost_model_v0.py`; `tools/dmv_analyze_cost_model_v0.py` | `results/census_analyze_cost_model_v0.json`; `results/dmv_analyze_cost_model_v0.json` | CSVs and Markdown reports |
| MCV/FD/ScalarArray fidelity | `tools/ce_replay_ir_v1.py`; `tools/fd_semantics_v0.py`; `tools/mcv_scalararray_semantics_v0.py` | v1-B target JSONs; `results/fd_semantics_v0.json`; `results/mcv_scalararray_semantics_v0.json` | `docs/ce-replay-ir-v1.md` and reports |
| Census maintenance optimization | `tools/maintenance_budget_optimize_v0.py` | `results/census_maintenance_budget_optimize_v0.json` | `results/census_maintenance_budget_optimize_v0.md` |
| DMV maintenance optimization | `tools/dmv_maintenance_budget_optimize_v0.py` | `results/dmv_maintenance_budget_optimize_v0.json` | report and `results/dmv_maintenance_budget_design_v0.json` |
| Census incremental evaluation | `tools/semantic_optimizer_v0.py`; `tools/compositional_semantic_optimizer_v0.py` | corresponding optimizer JSONs | corresponding Markdown reports/round CSVs |
| DMV dense incremental evaluation | `tools/dmv_maintenance_budget_optimize_v0.py` | DMV optimizer JSON | DMV optimizer report |
| Census deployment | `tools/maintenance_design_deploy_v0.py` | `results/census_maintenance_design_deploy_v0.json` | `results/census_maintenance_design_deploy_v0.md` |
| DMV deployment/provenance | `tools/dmv_deploy_v0.py`; `tools/dmv_frozen_provenance_recovery_v0.py` | corresponding JSONs | deployment/provenance reports and query comparison CSV |

The detailed file-level map is in `results/paper-evidence-map-v0.json`.

## 16. Related drafting discipline

### Explicit non-goals

The paper does not claim to:

- replace PostgreSQL's estimator;
- learn true cardinalities;
- optimize execution time directly;
- solve arbitrary PostgreSQL physical design;
- replay joins or the complete planner;
- provide full-instance global-optimum guarantees;
- predict arbitrary future workloads;
- eliminate `ANALYZE`;
- eliminate offline candidate-payload acquisition.

### Experiment-history details that do not control the narrative

- v0/v1/v2/v3/v4 naming and chronology;
- the early byte-budget formulation, except the direct Census resource-model comparison;
- failed factorization/commutativity attempts, except as appendix boundary evidence;
- the generalization detour;
- the DMV provenance-recovery chronology beyond the final missing-state conclusion;
- superseded EXPLAIN-rounded validation.

The final abstraction should read coherently, while experiment-specific realization boundaries and limitations remain explicit.

## 17. Narrative stress test

The proposed sequence answers the reader's questions in order:

1. **Why select?** Sections 1–2 and F2 show empirical non-monotonicity.
2. **Why constrain resources?** Sections 1–2 and F3 show recurring ANALYZE work.
3. **Why not score independently?** Section 4 and F4 show stateful MCV→FD interaction.
4. **What is CE-Replay?** Section 5 defines the executable representation.
5. **What does it replay?** Sections 4–5 define supported statistics-sensitive base restrictions.
6. **What not?** Section 5 states the boundary before evaluation.
7. **Why not a learned response model?** Section 5 follows native design→estimate semantics directly; truth only scores output.
8. **How used by optimizer?** Section 6 defines exact objective calls and search.
9. **Why incremental?** Section 6 distinguishes realized/counterfactual dependency and invalidation.
10. **What guarantee?** Section 6 and T3 state local versus restricted-global evidence.
11. **How close to native?** Section 8.1 and T2.
12. **Sparse incidence?** Census in Sections 7 and 8.3.
13. **Dense incidence?** DMV in Sections 7 and 8.3.
14. **Deployed interaction?** Section 8.4, F4 and T5.
15. **Fresh ANALYZE?** Section 8.4 separates payload drift from semantic error.
16. **Workload-specific evidence?** T1, RQ summaries, and Section 9.
17. **Limitations?** Section 9 groups them explicitly.

No experiment-history knowledge is required to follow this chain.

## 18. Prohibited claims

- CE-Replay exactly reproduces all PostgreSQL cardinality estimation.
- CE-Replay automatically compiles arbitrary DBMS source semantics.
- The optimizer finds the global optimum on full Census or DMV.
- Extended statistics are always non-monotone or harmful.
- Selection matters only because budget prevents building all statistics.
- FD generally costs 1.449× or 1.513× MCV in PostgreSQL.
- Serialized payload size is maintenance cost.
- The maintenance model predicts each candidate or every ANALYZE latency precisely.
- Semantic incremental evaluation always improves end-to-end runtime.
- DMV demonstrates Census-scale candidate-space scalability.
- DMV has a paired frozen-to-fresh per-query drift distribution.
- The system optimizes execution time or plan quality.
- The method generalizes to unseen workloads.
- All selected statistics always materialize or consume.
- More budget always improves the optimized objective.
- Candidate payload acquisition is solved.
- Physical design universally equals selection plus a permutation.
- Raw Census and DMV q-error magnitudes are directly comparable.

## 19. Final architecture verdict — 25 answers

1. **One-sentence thesis:** native statistics-sensitive CE semantics can be specialized into a workload-specific, design-parametric program serving as objective evaluator and dependency oracle for maintenance-constrained statistics physical design.
2. **Canonical CE-Replay meaning:** a representation/method for executable replay of the supported statistics-sensitive CE fragment; not the optimizer, whole system, or automatic source compiler.
3. **Four RQs:** exactly RQ1 objective semantics, RQ2 physical-design optimization, RQ3 semantic incremental evaluation, and RQ4 composition/deployment from Section 2.
4. **Contributions:** four grouped contributions in Section 13: formulation/representation, replay semantics, semantics-guided optimization, and cross-workload physical validation.
5. **Section structure:** Introduction; Background and Motivation; Problem Formulation; Statistics-Sensitive CE Semantics; CE-Replay; Semantics-Guided Physical Design; Experimental Methodology; Evaluation; Discussion and Limitations; Related Work; Conclusion.
6. **Minimum main-text chain:** non-monotonicity → maintenance calibration → semantic interaction → executable replay → constrained optimization → incremental evaluation → composition → deployment/native validation.
7. **Experiments disappearing from main narrative:** superseded IR/EXPLAIN stages, chronology-only optimizer versions, Research-Synthesis, all generalization experiments, and most failed decomposition explorations.
8. **Important negative results:** locality cannot restrict budget exchanges; mixed control-work reduction need not speed runtime; dense DMV weakens locality; DMV frozen provenance is incomplete. State/commutativity/factorization failures remain appendix evidence.
9. **Semantic boundary:** PostgreSQL 16.14 conjunctive statistics-sensitive base-restriction replay for validated scalar and constant IN/=ANY predicates, MCV, equality-eligible FD, MCV-first consumption, and relevant OID precedence.
10. **Optimization guarantee:** exact-within-scope objectives and audited moves; deterministic local optimum under fixed ADD/DROP/SWAP, payload, and precedence; global evidence only on small/restricted instances.
11. **Resource-model claim:** aggregate mechanism-weighted object count is a reproducible first-order recurring ANALYZE-cost proxy in each measured environment; coefficients are nonportable.
12. **Deployment claim:** both selected states were physically realized and fresh replay matched fresh native PostgreSQL; only Census has complete paired numerical realization-drift evidence.
13. **Both-workload evidence:** replay fidelity, non-monotonicity, maintenance modeling, maintenance-aware optimization, MCV→FD composition, exact incremental evaluation, local-optimum audits, physical realization, and fresh native validation.
14. **Census-specific:** large sparse candidate universe, direct byte-versus-maintenance comparison, strong sparse-locality reductions, and complete paired/repeated drift analysis.
15. **DMV-specific:** real IN-heavy ScalarArray validation, dense high-reuse incidence, and the zero-truth objective pathology.
16. **DMV provenance wording:** the frozen optimization run did not persist per-query estimates or sufficient simple-selectivity context, so paired frozen-to-fresh per-query numerical drift is unavailable; this is artifact/provenance incompleteness, not fresh semantic failure.
17. **DMV zero-truth wording:** two zero-cardinality queries combined with the unchanged positive q-error floor dominate the optimized aggregate; raw magnitude is not cross-workload comparable, and nonzero-truth loss is diagnostic only.
18. **Main figures:** four.
19. **Main tables:** five.
20. **RQ figure/table mapping:** RQ1=T2/F1; RQ2=F2/F3/T3; RQ3=T4; RQ4=F4/T5.
21. **Appendix:** source/instrumentation mapping, full semantic fixtures, OID precedence, exhaustive/terminal audits, invalidation and rejected shortcuts, maintenance diagnostics, repeated ANALYZE, DMV provenance, and inventory.
22. **Terminology:** frozen in Section 7; `CE-Replay`, target workload, physical realization, maintenance cost, payload drift, and semantic replay error are canonical.
23. **Notation:** the minimal 13-symbol set and three core equations in Section 6.
24. **Prohibited claims:** Section 18.
25. **Ready to draft without more database experiments:** yes; the frozen architecture and maps are sufficient for section-by-section drafting.

PAPER ARCHITECTURE FROZEN — READY FOR DRAFTING
