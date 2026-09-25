# CE-Replay: Executable Cardinality-Estimation Semantics for Statistics Physical Design

## Abstract

Selecting extended statistics for a supplied target workload is a physical-design problem with two distinct constraints: statistics can interact non-monotonically through the estimator, and deployed objects consume recurring maintenance capacity. Independent candidate scores are therefore insufficient because native applicability, winner selection, clause consumption, and mechanism composition make each candidate's effect contextual. We introduce CE-Replay, a workload-specialized, design-parametric representation that keeps the supported statistics-sensitive estimator semantics executable and exposes both an objective oracle and a semantic dependency oracle. We instantiate CE-Replay for PostgreSQL 16.14 conjunctive base-relation restrictions with MCV, functional-dependency, and constant `IN`/`= ANY` MCV semantics, and use it with deterministic constrained local search. CE-Replay matches fresh native estimates on all 468 Census and 1,965 DMV queries. Census supplies a mixed design under a calibrated maintenance-capacity proxy and a local-optimum certificate; across both workloads, exact incremental replay is faster than full replay in every tested move/scope cell, while full Replay versus isolated native CE remains workload-dependent. These results establish that executable native semantics can support statistics physical design within a validated fragment, while broader CE coverage, hypothetical-payload acquisition, payload-robust selection, and runtime objectives remain open.

## 1. Introduction

Cost-based query optimization depends on estimates of how many tuples flow through candidate plans. Ordinary per-column statistics can be inadequate when predicates are correlated, so DBMSs provide extended statistics that expose multivariate information to the estimator. Deciding which extended statistics to maintain changes the information available during optimization and is therefore a physical-design decision, not merely a statistics-collection setting. This paper studies that decision for a supplied target workload.

Selection can remain necessary even without a tight capacity constraint because a DBMS may choose among overlapping statistics, consume clauses after using one statistic, compose statistics over disjoint dimensions, and suppress a downstream mechanism after an upstream mechanism changes the residual state. A candidate's effect therefore depends on the other selected objects, their effective precedence, and their payloads. In both evaluated realizations, some additions worsen the target-workload cardinality-estimation objective; selecting every statistic is therefore not a valid default in these settings.

Selection also has an independent resource justification. PostgreSQL must collect and refresh deployed statistics, and this recurring `ANALYZE` work depends on the mechanism and environment. A practical design must balance estimator utility against maintenance capacity: a statistic may be affordable yet harmful, or beneficial yet infeasible.

Automatic statistics management already considers dependencies among statistics, while prior work establishes contextual design-object interactions, hypothetical and configuration-parametric evaluation, and dependency-aware exact recomputation [@chaudhuri2001statistics; @schnaitter2009interactions; @chaudhuri1998whatif; @papadomanolakis2007inum; @bruno2008cpqo; @liu2016incremental]. CE-Replay's narrower contribution is the represented computation: the statistics-sensitive estimator transition system itself. Executing it under a hypothetical statistics state simultaneously produces the CE objective and the semantic dependencies needed for exact safe invalidation after a design move; generic configuration-parametric or incremental computation is not claimed.

Our key idea is to specialize the DBMS's supported statistics-sensitive estimator semantics to the supplied workload while leaving statistics-design-dependent behavior executable. Workload-fixed clauses, relation context, and ordinary selectivities become fixed context; candidate payloads remain explicit inputs; and applicability, winner selection, clause consumption, mechanism composition, and numerical updates execute for each hypothetical design. The result, CE-Replay, produces the DBMS-style cardinality estimate. Ground truth enters only at the design layer, where the estimate is converted into q-error and a workload objective. Candidate definitions and hypothetical payloads are assumed to have been acquired offline before search: CE-Replay operates over this supplied frozen repository, and payload acquisition itself is outside the paper.

Executable semantics provide two interfaces. The **objective oracle** evaluates the estimate and loss induced by a hypothetical physical statistics state without learning a separate subset-to-q-error response model inside the supported fragment. The **dependency oracle** identifies the queries, semantic dimensions, and downstream mechanisms that a design move can affect. Because both interfaces arise from the same executable state transitions, the optimizer can avoid semantically irrelevant recomputation while preserving audited move values.

We instantiate CE-Replay for the supported PostgreSQL 16.14 statistics-sensitive fragment of conjunctive base-relation restrictions. The implementation covers validated scalar predicates, constant `IN` and `= ANY` MCV predicates, multicolumn most-common-values statistics, functional dependencies, PostgreSQL precedence relevant to MCV ties, and directed MCV-to-FD composition. It is source-informed and validated against native instrumentation; it is not a complete PostgreSQL CE emulator or an automatic source compiler.

We evaluate two structurally contrasting workloads: Census has a large candidate universe with sparse candidate-query incidence, while DMV has a small, dense, high-reuse universe dominated by constant `IN` predicates. Within the supported semantic boundary, replay matches native raw estimates to floating-point tolerance, including all 468 fresh Census queries and all 1,965 fresh DMV queries after deployment. Census provides the complete design study under a calibrated maintenance-capacity proxy; DMV provides cross-workload semantic, non-monotonicity, physical-fidelity, and replay-performance validation. The evidence does not make the workloads representative or the workload-scale search globally optimal.

This paper makes four contributions:

1. **Problem and representation.** We formulate statistics design under a maintenance constraint over the supported native CE state transitions. Applicability, consumption, precedence, and downstream reachability remain executable design semantics. The formulation separates selected definitions, effective precedence, and frozen versus fresh payload realizations; the evaluated search fixes recorded precedence.
2. **PostgreSQL CE-Replay.** We implement and validate CE-Replay for the supported PostgreSQL 16.14 base-restriction MCV+FD fragment, including bounded constant ScalarArray semantics and directed mechanism composition. The scope is explicit and excludes arbitrary PostgreSQL CE.
3. **Semantics-guided optimization.** We use CE-Replay as a validated objective oracle and a statistics-semantic dependency oracle for deterministic maintenance-constrained ADD/DROP/SWAP search. Exact incremental move evaluation reproduces audited full replay and reduces controlled move-evaluation wall clock within the tested setting; workload-scale guarantees remain neighborhood-local rather than global.
4. **Cross-workload physical validation.** Census supplies a complete design and deployment case under a calibrated maintenance-capacity proxy, while dense IN-heavy DMV supplies semantic, non-monotonicity, physical-fidelity, and evaluator-performance validation. The evidence concerns CE loss and evaluator cost, not query-runtime improvement.

## 2. Background and Motivation

### 2.1 Extended statistics and cardinality estimation

A query optimizer estimates predicate selectivity and intermediate cardinality to compare candidate plans. Per-column statistics commonly induce an independence approximation for multiple predicates; correlations can make that approximation inaccurate. Work on correlation discovery and multivariate summaries addresses this gap, and PostgreSQL exposes functional-dependency and MCV extended statistics for selected attribute groups [@ilyas2004cords; @postgresql16docs].

PostgreSQL supports several extended-statistics mechanisms. The two used here have different semantics. A multicolumn MCV object stores frequent value combinations and frequencies, allowing compatible predicates to be tested directly against a joint distribution. A functional-dependency object records approximate dependency strengths and adjusts the treatment of equality-eligible predicates. Section 4 describes only the control and numerical behavior required by CE-Replay.

### 2.2 Statistics as physical design

A candidate statistic specifies a persistent definition that may be deployed and refreshed. Unlike an index, it does not primarily add an access operator; it changes the estimator's information state and hence the estimates used during plan search. Workload-aware statistics management, selective statistics collection, and resource-constrained physical design are established research areas [@chaudhuri2001statistics; @elhelw2007jits; @bruno2008constrained]. The selected design studied here additionally depends on native statistics-consumption semantics and recurring maintenance work.

Candidate definition, payload, and effective precedence are distinct. A definition identifies what PostgreSQL should collect; a payload contains sampled values, frequencies, dependency degrees, and their interpretation schema; and effective precedence captures the order observable by native statistics selection. PostgreSQL realizes that precedence through creation and OID-sorted catalog/list behavior, but CE-Replay consumes the induced order rather than raw OIDs. Re-running `ANALYZE` can change payload values or availability without changing the definition or precedence. Just-in-time, piggyback, and incremental collection address the complementary question of when and how to acquire or refresh statistics [@elhelw2007jits; @zhu2004piggyback; @pfeil2026redshift].

### 2.3 Why independent candidate scoring fails

Consider two overlapping MCV objects and one FD object. Adding the larger MCV object may cause it to win native selection, consume clauses that previously supported the smaller object, and suppress the FD stage. The same addition can help one query and hurt another, and its effect can change after another candidate is selected. A fixed singleton score cannot encode that state transition. The non-monotonicity measured in Section 7 makes this semantic concern operational rather than hypothetical.

### 2.4 Design requirements

The problem calls for six properties. Hypothetical evaluation must match native behavior within a stated semantic boundary; design-dependent control must remain executable; mechanisms must compose through explicit state; repeated evaluation should exploit safe dependencies; maintenance must be an explicit resource; and a selected state must be deployable and validated against fresh native behavior. CE-Replay addresses the representation and evaluation requirements. The deterministic local search in Section 6 is one replaceable consumer of its interfaces.

## 3. Problem Formulation

**General formulation.** We consider offline physical design for a supplied target workload. The inputs are a database instance, queries with ground-truth cardinalities, candidate-statistic definitions with a frozen payload repository, and a recurring maintenance budget. The output is a realizable physical statistical state minimizing cardinality-estimation loss on that workload. The workload is a direct input to physical design rather than data for fitting a learned estimator.

Let the target workload, one query, and its true cardinality be denoted by

$$
Q, \qquad q \in Q, \qquad N_q.
$$

For each query, workload-fixed context is denoted by

$$
W_q.
$$

It contains clauses, relation context, ordinary selectivities, and other design-independent inputs required by the supported estimator fragment. Ground truth scores estimates but is not consumed by CE-Replay.

Let the candidate universe and selected subset be

$$
S, \qquad Y \subseteq S.
$$

Selection need not fully determine estimator behavior because native selection can observe precedence. For a selected design $Y$, let

$$
\pi_Y:Y\rightarrow\{1,\ldots,|Y|\}
$$

be an injective rank function representing an effective total precedence order, with smaller rank meaning earlier relevant precedence. Let $\Pi(Y)$ denote the deployable effective precedence orders over $Y$. This total-order representation is sufficient and simple; only order within a native mechanism where a reachable tie is observable can affect replay. It does not imply cross-mechanism competition or that every permutation is deployable on every DBMS. For PostgreSQL 16.14, creation order induces OID order, the relation statistics list is OID-sorted, and exact native ties therefore observe the induced precedence. Raw OID is a deployment mechanism, not the semantic design variable.

Candidate definitions do not uniquely determine payloads. The frozen candidate-payload repository used for hypothetical evaluation is

$$
P.
$$

It includes mechanism values and the schema needed to interpret them, including semantic key order and availability. The current system assumes that an offline acquisition process populated this repository. A fresh deployment can generate a different fresh payload state from the frozen repository without changing precedence unless definitions are dropped or recreated.

CE-Replay's executable semantics are denoted by

$$
F.
$$

For one query, the replayed estimate is

$$
\widehat{N}_q(Y,\pi;P)=F(W_q,Y,\pi,P).
$$

CE-Replay is a workload-specialized, design-parametric executable representation of a supported statistics-sensitive native CE fragment. It is neither a learned predictor nor a table of complete-design responses: eligibility, selection, consumption, composition, and numerical updates remain executable.

The per-query loss is denoted by

$$
\ell.
$$

The evaluated q-error is

$$
\ell(\widehat{N},N)
=
\max\!\left(
\frac{\widehat{N}}{N},
\frac{N}{\widehat{N}}
\right),
$$

for $N>0$. Estimate-side numerical protection floors $\widehat{N}$ at $10^{-300}$. Queries with zero ground truth remain in semantic-fidelity validation but are outside multiplicative q-error aggregation. Let $Q^+=\{q\in Q:N_q>0\}$. The unweighted target-workload objective is

$$
L(Y,\pi;P)
=
\sum_{q\in Q^+}
\ell\!\left(\widehat{N}_q(Y,\pi;P),N_q\right).
$$

Recurring maintenance cost and its budget are

$$
C(Y)=\sum_{s\in Y}c_s, \qquad B.
$$

The constrained physical-design problem is

$$
\min_{Y\subseteq S,\;\pi\in\Pi(Y)} L(Y,\pi;P)
\quad \text{subject to} \quad
C(Y) \le B.
$$

**Evaluated fixed-precedence problem.** The general formulation exposes selection and deployable effective precedence as parts of the physical state. The evaluated optimizer does not jointly optimize them: it fixes a recorded precedence, denoted by

$$
\pi_0 \in \Pi(S),
$$

For each selected subset $Y$, it uses that order restricted to $Y$. All workload-scale local-optimum claims are for subset selection under this fixed effective precedence and the audited neighborhood; they do not solve the general joint problem. The objective is CE loss, not query latency, plan quality, or throughput.

CE loss is the direct objective for the computation represented here: extended statistics change the estimator's information state, and CE-Replay executes that statistics-sensitive CE layer. A plan-quality or runtime objective would additionally couple replay to planner search, the cost model, and execution effects outside the current representation. Those objectives remain important, but this paper neither treats q-error as a latency surrogate nor claims that reducing it improves runtime.

## 4. Statistics-Sensitive CE Semantics

### 4.1 Running example

Consider a conjunctive query with predicates over four attributes. A design contains an MCV object over three attributes, an overlapping MCV object over two of them, a disjoint MCV object, and an FD whose applicability depends on residual predicates. At the start, both overlapping MCV objects may be applicable. GreedyCover selects the object covering more currently unestimated semantic dimensions, and the selected object consumes its covered clauses. The smaller overlap may then cease to apply, while the disjoint object remains available in a later round. The FD stage receives this residual state and may be suppressed if its required predicate was consumed.

The example shows why candidate utility cannot be assigned independently. The selected subset determines a sequence of native state transitions rather than a sum of fixed corrections.

### 4.2 MCV applicability, selection, and consumption

Within the supported fragment, MCV applicability depends on compatible clauses for sufficient semantic dimensions. Compatibility includes predicate/operator form and payload schema, not merely textual column overlap. Supported predicates include the validated scalar forms and constant `IN`/`= ANY` forms described below.

PostgreSQL GreedyCover proceeds in validated rounds [@postgresql16source]. It first maximizes coverage of currently unestimated dimensions, then prefers fewer statistic keys, and finally retains relevant catalog/list order for a remaining tie. The winner evaluates its compatible clauses, consumes them, and leaves a residual state for later rounds. Disjoint MCV objects can contribute later; overlapping objects may become inapplicable. A faithful evaluator must therefore execute repeated selection rather than choose one global statistic.

For a selected MCV object, PostgreSQL tests clauses against MCV entries [@postgresql16docs; @postgresql16source]. Matching entries contribute stored and base frequencies, while residual simple selectivity accounts for distribution mass outside the list. CE-Replay executes this payload-dependent rule from values, frequencies, base frequencies, and schema metadata. It does not replace it with a learned factor.

### 4.3 Constant ScalarArray predicates

For supported constant `IN` and `= ANY` predicates, each relevant MCV item is compared with array elements using OR semantics. Duplicate values do not multiply the frequency of one matched item, and null elements do not create a match. Direct item evaluation preserves native bitmap and frequency behavior; expanding the array into independently estimated scalar equalities would not.

This bounded extension covers the canonical DMV predicate boundary. It does not support arbitrary ScalarArray operators, nonconstant arrays, general `OR`/`NOT` trees, arbitrary expressions, joins, or parameterized clauses.

### 4.4 Functional dependencies and directed composition

FD processing is not another GreedyCover instance. PostgreSQL identifies dependency entries compatible with residual equality-eligible predicates, aggregates their degrees, and adjusts selectivity while accounting for implied attributes [@postgresql16source]. Applicability depends on predicate form, semantic dimensions, payload availability, and the state entering the FD stage.

The supported mechanisms compose in a directed order:

```text
MCV applicability and GreedyCover
              |
              v
residual estimated-clause state
              |
              v
FD applicability and dependency application
```

An MCV winner can therefore suppress an FD that would otherwise apply. Conversely, removing or replacing an MCV can restore FD reachability. This directed state boundary is both an optimization interaction and a dependency boundary for incremental evaluation.

### 4.5 Consequence for physical design

Changing one candidate can alter applicability, MCV winners, consumed clauses, later MCV rounds, FD reachability, and payload-derived numerical contributions. Candidate response need not be additive and can be non-monotone. The physical-design evaluator must execute these design-parametric semantics; Section 5 describes their workload-specialized representation.

## 5. CE-Replay

CE-Replay is the conceptual center of the method. It turns the supported statistics-sensitive estimator fragment into an executable representation evaluated repeatedly under hypothetical selected definitions, effective precedence, and payload states. It is not the search algorithm, the complete DBMS, or the native estimator itself.

The representation contract combines three properties. First, workload-fixed estimator context is specialized for the supplied workload. Second, design-dependent applicability, winner selection, clause consumption, residual state, numerical updates, FD reachability, and relevant precedence remain executable across hypothetical designs rather than being resolved into one observed calculation. Third, those same state transitions supply both objective evaluation and statistics-semantic dependency/invalidation information. CE-Replay is therefore not merely a second implementation of one fixed cardinality calculation: its manually engineered, bounded representation retains the counterfactual structure needed to evaluate alternative statistics states and invalidate design moves safely.

**Figure F1** separates the two loops needed to interpret the method correctly. The upper loop combines frozen workload context and an offline frozen payload repository to evaluate hypothetical designs under recorded precedence and return objective values and semantic dependencies to search. Only the selected state enters the lower loop, where deployment creates definitions in recorded precedence order, fresh `ANALYZE` produces a new payload realization, and CE-Replay is compared with native PostgreSQL on that same payload realization.

> **Figure F1: CE-Replay physical-design pipeline.** For a supplied target workload, workload-fixed estimator context and an offline frozen candidate-payload repository specialize the supported PostgreSQL 16.14 statistics-sensitive base-restriction fragment while leaving design-dependent MCV selection, clause consumption, FD applicability, and numerical updates executable. CE-Replay exposes an objective oracle and a semantic dependency oracle to maintenance-feasible ADD/DROP/SWAP search under recorded effective precedence. The selected definitions are then created in that precedence order and analyzed afresh. Fresh payloads feed both CE-Replay and native PostgreSQL for matched-payload semantic validation; equality between frozen and fresh payloads is not assumed. *(Production note: render the frozen two-band specification in `docs/paper-figure-1-spec-v0.md`.)*

### 5.1 What is frozen and what remains executable

The representation has four blocks:

1. **Workload-fixed context:** clauses, relation cardinality, ordinary selectivities, predicate semantics, and truth retained only for later scoring.
2. **Payload and schema context:** MCV values and frequencies, base frequencies, FD degrees, semantic dimensions, key order, and payload availability.
3. **Design-dependent state:** the selected definitions and effective precedence, represented by recorded PostgreSQL ranks within each native mechanism where order is observable.
4. **Executable semantics:** applicability, GreedyCover, consumption, MCV numerical combination, FD application, and final row computation.

Specialization fixes the first block and loads the second, while the third remains an input and the fourth executes for every hypothetical state. Freezing a winner observed under one design would violate design-parametric replay. A response table over complete designs would also discard the state transitions needed for counterfactual dependency analysis.

### 5.2 Supported boundary and validation model

The validated boundary is PostgreSQL 16.14 conjunctive base-relation restrictions with supported scalar predicates, constant `IN`/`= ANY` MCV predicates, MCV, equality-eligible FD, MCV-first composition, and relevant fixed precedence. CE-Replay does not cover joins, complete planner/path search, arbitrary expressions or operators, general Boolean trees, all statistics mechanisms, or other PostgreSQL versions.

Native instrumentation exposes the supported estimator at a raw/pre-clamp boundary. Comparisons match query, design, effective precedence, and payload state, avoiding integer plan-row rounding as apparent semantic error. The native system is a semantic validation oracle; it is not invoked for every hypothetical state in the final search loop.

### 5.3 Objective and dependency interfaces

The objective oracle returns the replayed estimate and, after ground-truth scoring, the target-workload loss. It is exact only relative to the validated semantics, supplied payload state, and effective precedence. It does not predict truth.

The dependency oracle is derived from the executable state transitions rather than attached as post hoc metadata. It reports which queries, semantic dimensions, and downstream mechanisms a design move may affect, distinguishing **realized dependencies** exercised in the current trace from **structural/counterfactual dependencies** that can change a future trace even when current outputs coincide. State sufficient to continue one execution is not necessarily safe for arbitrary extension; current-output equivalence is not counterfactual-state equivalence.

### 5.4 Frozen and fresh payload realizations

Optimization is conditional on the frozen payload repository. Deployment invokes `ANALYZE` and creates a fresh payload realization whose values or availability may differ. **Semantic replay error** is the replay/native discrepancy for one matched payload state and precedence. **Payload realization drift** is the difference between frozen and fresh payload outcomes. Figure F1 separates these quantities, and Section 7 reports them separately.

## 6. Semantics-Guided Physical Design

The optimizer is one replaceable consumer of CE-Replay's two interfaces, not the primary contribution. The implementation below tests whether those interfaces suffice for a complete maintenance-constrained search loop.

### 6.1 Search policy

The solver first builds a maintenance-feasible design by repeatedly recomputing contextual loss reduction per maintenance unit. It then enumerates all feasible ADD, DROP, and SWAP moves under the fixed recorded precedence defined in Section 3; when a move changes $Y$, replay uses its restriction to $Y$. Each round accepts the deterministic best strict improvement and terminates when none exists.

```text
design ← empty
while a feasible candidate has positive contextual benefit per maintenance unit:
    add the deterministic best candidate and update replay state

repeat:
    best ← none
    for each feasible ADD, DROP, and SWAP:
        affected ← dependency_oracle(design, move)
        value ← objective_oracle.incremental(design, move, affected)
        best ← deterministic_best_improvement(best, value)
    if best is none or not a strict improvement:
        return design
    commit(best)
```

The result is locally optimal only under this audited neighborhood, payload repository, budget, and fixed precedence. Exhaustive global agreement is established only on a five-candidate Census instance and four restricted DMV instances; no approximation guarantee is claimed.

### 6.2 Safe incremental evaluation

Candidate-query incidence supplies an outer affected set. Within an affected query, the evaluator chooses the narrowest safe action: no work, a cached numerical update, local MCV control replay, FD replay after direct or upstream invalidation, or broader replay fallback. A computation is skipped only when structural/counterfactual dependencies show that the move cannot affect it.

Global graph connectivity does not invalidate this strategy. A candidate can affect few queries even when chains of shared candidates place nearly the whole workload in one connected component. Conversely, a shared maintenance budget prevents disjoint query neighborhoods from becoming completely independent optimization problems because candidates can exchange budget through SWAP moves.

Reduced semantic work is not synonymous with runtime improvement. Once control replay is avoided, numerical aggregation and move-loop overhead may dominate. Section 7 therefore reports exact trajectory preservation, replay-operation reduction, evaluator latency, and optimizer wall-clock separately.

### 6.3 Deployment boundary

After search, selected definitions are created in recorded precedence order. PostgreSQL assigns OIDs in that sequence and constructs its relation statistics list in OID order, thereby realizing the intended effective precedence; raw OIDs are not replay inputs. A subsequent fresh `ANALYZE` changes payload state, not precedence. Fresh payloads are passed both to CE-Replay and native PostgreSQL for matched-payload validation. Candidate-payload acquisition remains an offline input boundary and is not counted as recurring deployed maintenance.

## 7. Evaluation

### 7.1 Experimental Setup

The evaluation asks four questions: whether replay matches native semantics, supports constrained design, preserves move values while reducing work, and keeps interacting mechanisms faithful after deployment. All semantic claims target PostgreSQL 16.14.

**Table T1** establishes the complementary workload regimes used throughout the evaluation.

**Table T1: Complementary workload and candidate structure.** Degree counts target queries incident to a structural-pair candidate; these workloads are not claimed to represent all database workloads.

| Workload | Queries / rows | Predicate columns / form | Pairs | Candidate degree | Incidence | Main stress |
|---|---|---|---:|---|---|---|
| Census | 468 / 2,458,285 | 68; numeric equality/range | 2,253 | Mean 4.44; max 13 | Sparse, giant component | Large universe; sparse incremental evaluation |
| DMV | 1,965 / 11,591,877 | 9; categorical equality and constant `IN`/`= ANY` | 36 | Mean 497.08; median 498; max 546 | Dense/high reuse | ScalarArray semantics; dense incremental evaluation |

Census stresses a large pair universe, mixed-mechanism selection, sparse invalidation, design under a calibrated maintenance-capacity proxy, and payload realization. DMV's 1,913 IN-bearing queries stress bounded ScalarArray semantics, dense reuse, physical fidelity, and replay timing. Its small universe does not establish Census-scale search scalability.

Structural pairs induce mechanism-specific MCV and FD definitions. Census has 2,253 pair MCV definitions and 758 usable query-applicable FD payloads in the mixed payload realization. The DMV realization has 36 usable MCV and 35 usable FD payloads, or 71 usable candidates. Candidate definitions, selection, payload availability, payload values, effective precedence, and maintenance cost remain distinct.

Ground-truth rows score replayed estimates using the q-error in Section 3. DMV queries `dmv.173` and `dmv.943` have zero truth: all 1,965 queries remain in semantic validation, while the objective aggregates only the 1,963 positive-truth queries. No DMV objective or design result that aggregates the zero-truth queries is used.

For the complete Census design study, recurring maintenance is instantiated with mechanism-weighted object counts calibrated from aggregate `ANALYZE` latency. The measured Census slopes are 1.874997 ms/MCV and 2.717261 ms/FD, yielding normalized costs 1 and 1.449. This first-order resource proxy is specific to the environment; it is neither a PostgreSQL constant nor a per-candidate latency predictor.

The controls align with those questions. Raw native comparisons test semantic fidelity; exhaustive five-candidate Census search tests small-instance optimization; complete terminal ADD/DROP/SWAP audits establish neighborhood-local termination; and full-versus-incremental checks test move equivalence. Deployment evaluates fresh matched-payload fidelity separately from frozen-to-fresh drift.

### 7.2 RQ1 — Does replay match native PostgreSQL?

RQ1 asks whether CE-Replay reproduces native PostgreSQL estimates inside the supported fragment. **Table T2** combines controlled semantic cases, real workloads, and fresh deployments.

**Table T2: Native fidelity in the supported fragment.** Comparisons match query, design, effective precedence, and payload state; error is relative at the raw/native cardinality boundary.

| Validation setting | Semantic fragment | Comparisons | Result | Maximum relative error |
|---|---|---:|---|---:|
| Census MCV raw oracle | Scalar MCV | Four targets × 32 designs | All matched | 5.55e-16 |
| Controlled FD scenarios | FD selection, application, order | 13 scenarios | All matched | 0 |
| Synthetic ScalarArray | Constant `IN`/`= ANY` MCV | 29 cases | 29/29; scalar regression 128/128 | 4.38e-15 |
| DMV baseline realization | Real equality/IN MCV+FD | 27,510 | 27,510/27,510 | 2.69e-14 |
| Census fresh deployment | Fresh mixed MCV+FD | 468 | 468/468 | 6.92e-16 |
| DMV deployment | Fresh mixed MCV+FD | 1,965 | 1,965/1,965 | 2.94e-14 |

Raw instrumentation removes rounded plan rows as an observation artifact. ScalarArray support retains all 128 scalar regression cases while covering the canonical DMV workload. Fresh deployment is the strongest closure because new payloads are generated: CE-Replay matches native estimates for every fresh query in both workloads.

**Answer to RQ1.** Within the explicitly supported PostgreSQL 16.14 statistics-sensitive base-restriction fragment and matched payload state, CE-Replay matches native estimates to the reported floating-point tolerances. This result does not cover joins, full planner search, arbitrary predicates, other mechanisms, or other PostgreSQL versions.

### 7.3 RQ2 — Can replay drive resource-constrained statistics design?

RQ2 first asks whether selection can remain necessary before capacity becomes binding. **Figure F2** answers that question by separating semantic harm from maintenance scarcity.

> **Figure F2: Cross-workload non-monotonicity.** Independently scaled panels compare empty and complete states. Census has 1,444 beneficial, seven neutral, and 1,560 harmful additions among 3,011 candidates, plus 317 improving removals; DMV has 30 beneficial and 41 harmful additions among 71 candidates, plus 20 improving removals. This is contextual evidence from two frozen payload realizations, not a universal property. *(Production note: render from the frozen F2 plan.)*

In Census, empty, all-statistics, and optimized-subset losses are 11,808.960379, 10,932.295550, and 805.316472 in one frozen realization. DMV losses are 88,414.724832 empty, 95,562.954655 all-MCV/all-mixed, and 96,951.199966 all-FD. All-mixed equals all-MCV because MCV consumption suppresses every usable FD. In both realizations, selection remains useful for semantic reasons independently of capacity; the Census calibration above separately establishes resource demand.

Having established semantic need, **Table T3** asks what the optimizer selects under the validated Census maintenance constraint.

**Table T3: Census calibrated maintenance-proxy design outcome.** Local optimality is limited to the audited ADD/DROP/SWAP neighborhood under fixed payload and recorded effective precedence.

| Workload | Usable universe | Selected design | Budget; cost / unused | Frozen loss | Terminal audit |
|---|---|---|---|---:|---|
| Census | 2,253 MCV + 758 FD | 276 MCV + 7 FD | 286.144; 286.143 / 0.001 | 787.809381 | 565,031 moves; local optimum |

Under the calibrated Census proxy, the design changes from 205 MCV plus 56 FD to 276 MCV plus seven FD. Loss falls from 805.316472 to 787.809381; proxy cost 286.143 fits budget 286.144, and all seven FDs are consumed. Auditing 565,031 terminal moves certifies an ADD/DROP/SWAP local optimum under fixed precedence. DMV's calibration misses its preregistered stability criterion, so no DMV budgeted-design result is reported; general additive candidate costs are not falsified.

**Answer to RQ2.** On Census, CE-Replay drives mixed statistics design under a calibrated maintenance-capacity proxy without a learned design-to-q-error response model. The state is an audited neighborhood local optimum under fixed precedence, not a global optimum.

### 7.4 RQ3 — Do semantic dependencies reduce move-evaluation work?

RQ3 asks whether counterfactual-safe invalidation preserves exact move values, reduces replay work, and lowers evaluator cost. **Table T4** separates black-box planner/oracle cost, isolated native CE, full Replay, and incremental Replay.

Timing uses PostgreSQL 16.14 on the same host and environment with warm long-lived processes, five warm-up batches, 30 measured batches, and the smallest power-of-two batch exceeding 100 ms. Boundaries are client-observed estimate acquisition (native planner), the instrumented clause-selectivity routine (native CE), complete in-memory evaluation (full Replay), and a supplied move over persistent state (incremental Replay); the artifact contains the full protocol and raw timings.

**Table T4: Full-workload and exact incremental wall-clock results.** Times are warm medians. Native planner is a black-box estimate-acquisition path, not isolated estimator time; native CE times only the clause-selectivity routine inside base-relation sizing.

| Workload / operation | Native planner | Native CE | Full Replay | Incremental result |
|---|---:|---:|---:|---|
| Census full workload | 90.867 ms | 10.241 ms | 1.884 ms | Planner/Replay 48.24×; CE/Replay 5.44× |
| DMV full workload | 294.542 ms | 47.603 ms | 85.472 ms | Planner/Replay 3.45×; Replay/CE 1.80× |
| Census sampled moves | — | — | Control | ADD 61.28×; DROP 44.08×; SWAP 31.49× |
| DMV sampled moves | — | — | Control | ADD 3.22×; DROP 2.98×; SWAP 1.92× |
| Fixed Census trajectory | — | — | 45.093 ms | 8.031 ms; 5.615× |

Census contains a giant component despite sparse degree, so connected-component decomposition is ineffective. Counterfactual-safe structural scope remains useful because a typical move touches few queries, while currently consumed winners alone are insufficient: latent candidates can become eligible after a move. The timing patch preserves representative raw rows in 4/4 trace-on/off checks. Full Replay matches native on 468/468 Census and 1,965/1,965 DMV queries; 192/192 sampled full/incremental moves match, and incremental replay is faster in all 24 workload × move-family × affected-scope cells.

The fixed 19-move Census trajectory was not re-searched; every objective state matches, and incremental time includes commit and invalidation. Earlier whole-optimizer measurements remain informative: MCV-only used 171.31× fewer control replays but improved wall clock by 3.51×, not 171×. Mixed evaluation reduced controls yet took 145.678 s versus 45.045 s because numerical aggregation and broader bookkeeping dominated. The final benchmark isolates evaluator operations, so its positive result and the earlier whole-implementation slowdown measure different boundaries.

**Answer to RQ3.** Structural/counterfactual dependencies enable exact audited incremental move evaluation in the tested sparse and dense regimes. They reduce controlled evaluator wall clock in every tested cell and on the fixed Census trajectory; primitive native-CE versus full-Replay cost remains workload-dependent.

### 7.5 RQ4 — Does replay preserve interacting semantics after physical deployment?

RQ4 asks whether replay preserves the directed MCV-to-FD interaction through complete design and physical deployment. **Figure F4** links that mechanism to observed FD reachability.

> **Figure F4: Directed MCV-to-FD composition and FD consumption.** MCV clause consumption feeds FD residual state. Census independent mechanism selection chooses 97 FDs, 72 unused after composition, whereas fixed-precedence mixed selection chooses 54, all consumed. In DMV, the all-statistics state consumes zero of 35 usable FDs; a fixed physical validation state contains 12 MCV and four FD objects and is used only for semantic fidelity, not RQ2. *(Production note: render the frozen F4 specification.)*

Mixed-mechanism Census selection under fixed effective precedence improves over independently selected mechanisms and stops spending maintenance capacity on many suppressed FDs. DMV replicates all-statistics FD suppression under dense incidence. **Table T5** then separates fresh matched-payload fidelity from frozen-to-fresh payload drift.

**Table T5: Physical deployment and fresh validation.** Replay/native fidelity uses all queries; DMV q-error drift uses only its 1,963 positive-truth queries.

| Workload | Selected / fresh materialized | FD consumption | Fresh replay/native; max relative error | Frozen→fresh drift | Cost error |
|---|---|---|---|---|---:|
| Census | 276 MCV + 7 FD; 276/276 MCV, 7/7 FD | 7/7 | 811.553725 / 811.553725; 468/468; 6.92e-16 | 787.809381 → 811.553725; +3.0140% | 7.20% |
| DMV diagnostic fixed state | 12 MCV + 4 FD; 12/12 MCV, 4/4 FD | Physical state validated | 1,965/1,965; 2.94e-14 | 46,034.243090 → 45,259.901254; -1.6821% | Not a budget model |

For the final Census proxy-constrained design, all objects materialize and consume. Across 30 repeated `ANALYZE` payload realizations, 14,040/14,040 replay/native comparisons match while objective loss has 1.835% coefficient of variation. This demonstrates matched-payload fidelity under measurable payload variation, not stability of design rankings. In DMV, all 16 objects materialize and all fresh queries match native. Its maintenance calibration did not satisfy the preregistered stability criterion, so the 12-MCV+4-FD state is retained only as a fixed-state semantic-fidelity test and no DMV budgeted-design result is reported.

**Answer to RQ4.** CE-Replay composes directed MCV and FD semantics and remains faithful after fresh physical deployment on both workloads. Fresh payload realization can change values and availability, so semantic replay error and payload realization drift must remain separate.

## 8. Discussion and Limitations

### 8.1 Statistics as semantic physical design

Extended statistics change the optimizer's information state, and their utility depends on native selection, consumption, and mechanism composition—not only on captured correlation. The cross-workload non-monotonicity evidence therefore justifies selection independently of scarcity, while recurring collection work supplies a separate resource justification. A loose budget removes neither contextual harm nor the need to choose.

### 8.2 CE-Replay as an optimization representation

CE-Replay's value is representational rather than merely computational. Configuration-parametric representation and dependency-aware recomputation are established principles; CE-Replay instead represents statistics-sensitive estimator state transitions that provide both the hypothetical objective and the statistics-semantic information needed to invalidate that objective safely after a move. Within the supported fragment, native semantics supply the design response without a separately learned subset-to-error model; outside that boundary, approximate or learned components may still be useful.

Execution-sufficient state is not necessarily counterfactual-safe state. A currently unused object may change a future winner, and numerically equal current states can diverge after an extension. This is why structural/counterfactual dependencies supplement the realized trace.

### 8.3 Locality without decomposition

Census rejects a tempting but incorrect shortcut. Its graph is globally connected and tested factorization does not yield independent subproblems, yet sparse candidate degree permits local recomputation. The semantic representation reduces exact move-evaluation work; it does not decompose away the global budget or combinatorial search.

The earlier mixed whole-optimizer slowdown identifies a boundary: once semantic control replay becomes rare, numerical aggregation and broader implementation overhead can dominate, so less replay work alone does not guarantee whole-optimizer acceleration. Under the final controlled operation contract, however, exact incremental Replay is faster than full Replay in every tested move/scope cell and on the fixed Census trajectory. DMV confirms this direction with smaller gains under dense incidence, but two workloads do not define a universal scaling law.

### 8.4 Maintenance proxy and semantic utility

The Census resource replaces bytes with mechanism-weighted counts fitted to aggregate `ANALYZE`. This calibrated first-order proxy is environment-specific, not a PostgreSQL constant or per-object latency predictor. DMV's calibration misses its preregistered stability criterion, so no DMV budgeted-design result is reported; the general additive formulation is not falsified.

Changing resource semantics changes the physical-design problem: on Census it materially changes composition and frozen loss. A budget is a capacity constraint, not a target; a local optimum may leave capacity unused when no feasible neighborhood move improves the contextual objective.

### 8.5 Frozen hypothetical state and fresh payload realization

The optimizer is conditional on a frozen payload repository, while deployment generates a fresh payload realization. Replay/native fidelity within one matched payload state and frozen-to-fresh payload drift answer different questions. Repeated Census `ANALYZE` demonstrates payload and objective variability without semantic mismatch. It does not establish frequent design-ranking reversal or regret; that would require paired multi-design payload realizations.

Future objectives could optimize expected, risk-sensitive, or worst-case loss over payload realizations. Efficient acquisition of hypothetical candidate payloads is another open systems problem. Just-in-time, piggyback, and modern incremental statistics maintenance demonstrate complementary ways to reduce collection or refresh work [@elhelw2007jits; @zhu2004piggyback; @pfeil2026redshift]. CE-Replay does not implement those techniques: its offline acquisition boundary is distinct from the recurring maintenance cost of the selected deployment.

### 8.6 Extending CE-Replay

The implementation is source-informed and mechanism-specific rather than an automatic compiler. Supporting another predicate family, mechanism, version, or DBMS requires extracting applicability and control rules, defining payload schemas, implementing state transitions, validating native behavior, and exposing dependencies. The ScalarArray extension demonstrates this deliberate process. MCV-to-FD composition suggests an architectural principle—mechanisms should expose explicit state inputs, outputs, and dependency boundaries—but the principle has not been validated across DBMSs.

PostgreSQL-specific elements include GreedyCover, effective precedence induced by OID-sorted statistics lists, payload formats, MCV-to-FD ordering, and `ANALYZE` payload-realization behavior. The contribution is the bounded executable estimator-semantic representation and its validated interfaces; workload specialization, configuration parametrization, dependency-aware recomputation, and maintenance-constrained design are established foundations.

### 8.7 Limitations

The validated semantic scope is PostgreSQL 16.14 conjunctive base-relation restrictions with supported scalar and constant `IN`/`= ANY` predicates, MCV, FD, and their directed composition. It excludes joins, planner/path search, arbitrary expressions/operators or Boolean trees, other mechanisms, and other versions. The semantics were manually engineered and validated, not automatically compiled.

Optimization assumes an offline frozen payload repository and returns an ADD/DROP/SWAP neighborhood local optimum under fixed precedence; it has no full-instance global or approximation guarantee. The maintenance model is environment-specific and first-order. The objective is q-error, not plan quality, latency, throughput, or a causal runtime improvement.

Fresh `ANALYZE` can change payloads or availability, and the optimizer is not payload-robust. DMV excludes two zero-truth queries from q-error but retains all 1,965 for semantic validation. Its fixed physical state supports fidelity and positive-truth drift, not a budgeted-design result.

Finally, Census and DMV provide complementary sparse and dense evidence but do not establish universal workload generality. The target workload is supplied; unseen-workload generalization is outside the core problem.

## 9. Related Work

### 9.1 Statistics management and multivariate-statistics discovery

Automatic statistics management predates CE-Replay. Chaudhuri and Narasayya select optimizer-relevant statistics, explicitly note dependencies among statistics, and show in MNSA/D that a statistic irrelevant under one set can matter after another statistic is added [@chaudhuri2001statistics]. CORDS discovers correlations and soft functional dependencies for joint statistics, while JITS selects and collects query-specific statistics using sensitivity and prior information [@ilyas2004cords; @elhelw2007jits]. Thus workload-aware selection, contextual statistics relevance, correlation discovery, and selective acquisition are established.

Their MNSA analysis uses a cost-monotonicity assumption over predicate selectivities, while also acknowledging pathological violations in which adding a histogram can worsen the chosen plan [@chaudhuri2001statistics]. Our non-monotonicity evidence concerns PostgreSQL q-error under physically realized extended-statistics objects; it is systematic evidence for semantics-aware selection in this mechanism and setting, not a claim that harmful additions are historically new.

CE-Replay does not contribute candidate discovery, acquisition, or statistics interaction in general. Given definitions and frozen payloads, it represents the native estimator transitions producing those interactions---applicability, precedence, clause consumption, numerical updates, and downstream reachability---and uses them for hypothetical CE and move invalidation.

Statistics collection and refresh are also established concerns. Piggyback collection gathers statistics during query execution [@zhu2004piggyback], while JITS considers materialization and maintenance of selectively collected statistics [@elhelw2007jits]. Recent Redshift work updates optimizer statistics incrementally from modified data rather than repeatedly scanning full tables [@pfeil2026redshift]. These techniques ask how to acquire or refresh a chosen statistical state efficiently. CE-Replay asks which state to choose under a recurring maintenance constraint; combining the two directions is future systems work.

### 9.2 What-if and configuration-parametric physical design

Hypothetical evaluation, constrained design, and contextual design-object interaction are established foundations. AutoAdmin evaluates hypothetical indexes without materializing every configuration; constrained tuning optimizes under storage and richer constraints; and Index Interactions formalizes configuration-dependent positive and negative index interactions, including objects that become useful together [@chaudhuri1998whatif; @bruno2008constrained; @schnaitter2009interactions]. CE-Replay claims none of these general principles.

INUM reuses optimizer-derived template plans while plugging in access costs for each index design [@papadomanolakis2007inum]. C-PQO specializes optimizer computation into a compact MEMO/APR representation, retaining alternatives needed to produce plans for arbitrary configurations [@bruno2008cpqo]. They establish reusable configuration-parametric optimizer representations and latent configuration alternatives, not just final-plan caching.

The distinction is the represented computation and the interface it exposes. INUM and C-PQO represent optimizer plan/cost behavior over hypothetical physical-design configurations. CE-Replay specializes the supported statistics-sensitive estimator computation itself, leaving applicability, winner selection, clause consumption, payload-dependent numerical updates, and downstream mechanism reachability executable. Those state transitions expose the statistics-semantic dependencies needed both to evaluate the CE objective and to invalidate incremental statistics-design moves safely. This is not a claim that prior physical-design tools are black boxes, lack response reuse, or cannot expose dependencies; the methodological point is that this represented computation supplies the dependency structure required by the present statistics-design problem.

### 9.3 Incremental optimization

Dependency tracking and exact incremental recomputation are established principles. Incremental query re-optimization retains optimizer search/pruning state, propagates changed cardinality or cost information, and can rederive pruned alternatives while matching full reoptimization [@liu2016incremental]. CE-Replay's narrower contribution is to identify and expose the estimator-semantic state affected by a statistics-design move---including precedence, consumption, and downstream reachability---before optimizer search. We therefore use **semantic dependency oracle** as a domain-specific interface, not a claim to generic incremental computation.

### 9.4 Cardinality estimation

Learned and data-driven CE systems construct alternative estimation models. MSCN learns from query features and executed-query cardinalities [@kipf2019learned]; DeepDB learns a data-driven probabilistic model rather than requiring executed-query workload training [@hilprecht2020deepdb]; FactorJoin combines learned single-table conditional distributions through a factor graph for join estimation [@wu2023factorjoin]. This variety prevents a simple learning-versus-no-learning dichotomy.

CE-Replay does not learn a replacement cardinality estimator or a surrogate mapping from statistics designs to q-error. It executes the supported statistics-sensitive semantics of PostgreSQL's native estimator while varying the physical statistics state. PostgreSQL documentation and source define the native MCV/FD mechanisms [@postgresql16docs; @postgresql16source]; this paper contributes their bounded extraction, executable encoding, composition, and validation for physical-design evaluation, not the mechanisms themselves.

### 9.5 Positioning of CE-Replay

Prior work establishes statistics dependencies and contextual interactions among design objects, hypothetical and configuration-parametric optimizer evaluation, and dependency-aware exact recomputation. CE-Replay's bounded systems specialization is to preserve the supported native statistics-estimator state transitions as executable design parameters, using that state for both workload CE evaluation and statistics-semantic, counterfactual-safe move invalidation.

This positioning is deliberately bounded. The literature categories overlap, and the current search does not justify a priority claim. CE-Replay is neither a complete advisor pipeline nor a full PostgreSQL estimator: candidate-payload acquisition remains external, search remains replaceable and neighborhood-local, and semantic coverage remains the validated PostgreSQL 16.14 fragment.

## 10. Conclusion

This paper studies extended-statistics design for a supplied target workload under a recurring maintenance constraint. In the evaluated realizations, subset selection remains useful both because deployed objects consume maintenance capacity and because native estimator control makes candidate utility contextual and non-monotone.

CE-Replay exposes the supported statistics-sensitive semantics as a workload-specialized, design-parametric executable representation. Workload-fixed context is specialized, while applicability, winner selection, clause consumption, MCV-to-FD composition, and numerical payload behavior remain executable. The resulting objective and dependency oracles allow a replaceable optimizer to evaluate hypothetical states and safely restrict recomputation.

For the supported PostgreSQL 16.14 base-restriction fragment, both workloads establish matched-payload fidelity and exact incremental evaluation across sparse and dense regimes. Census supplies the mixed design under a calibrated maintenance-capacity proxy, local-optimum certificate, and deployment closure; DMV supplies cross-workload semantic, non-monotonicity, physical-fidelity, and replay-performance validation without a budgeted-design result. Controlled incremental Replay is faster than full Replay in every tested cell, while full Replay versus isolated native CE is workload-dependent and fresh payload drift remains distinct from semantic replay error.

The current results remain conditional on a supplied workload, a frozen payload repository, manually supported MCV+FD semantics, and neighborhood-local search. Extending executable semantic representations to broader CE mechanisms, cheaper payload acquisition, payload-robust objectives, and additional DBMSs offers a path toward physical-design tools that use native estimator behavior as both an objective evaluator and a source of optimization structure.

## Artifact and Reproducibility Statement

The public repository contains experiment scripts, frozen results, and claim/evidence audits. The immutable `research-freeze-v0` tag identifies the experimental baseline used by this draft; later commits contain paper-construction artifacts. The reproducibility index maps each main claim to its scripts and outputs. No archival DOI is claimed in this draft.
