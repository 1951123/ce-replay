# 9. Discussion and Limitations

## 9.1 Statistics as semantic physical design

Extended statistics are physical-design objects because they change the information state on which the optimizer acts. Unlike structures whose primary role is to expose additional physical access alternatives, an extended statistic changes the estimate produced for an existing query expression. Its value therefore depends not only on what correlations it captures, but also on the estimator's rules for choosing statistics, consuming clauses, and composing mechanisms.

This semantic dependence makes selection necessary for a reason independent of scarcity. In both Census and DMV, adding an available statistic can worsen target-workload cardinality-estimation loss, and removing a statistic from the complete design can improve it. More statistics is therefore not a generally valid target for the supported PostgreSQL setting. The evidence establishes non-monotone behavior in two workloads; it does not imply that every statistic, workload, or DBMS behaves this way.

There are consequently two independent reasons to select a subset. The **semantic reason** is that a candidate's marginal effect is contextual: another selected statistic may win native selection, consume clauses, or suppress a downstream mechanism. Selection can remain meaningful even when capacity is nonbinding. The **resource reason** is that deployed statistics impose recurring collection and refresh work during `ANALYZE`. A practical design must satisfy a maintenance constraint even when every selected object is beneficial. Reducing the problem to “build as many useful statistics as the budget permits” misses the first reason.

## 9.2 CE-Replay as an optimization representation

CE-Replay is useful beyond reproducing an estimate. Within the supported semantic fragment and for a fixed payload realization, one executable representation supplies two interfaces. Its **objective oracle** maps a hypothetical physical statistics state through native-style consumption semantics to a cardinality estimate and then to target-workload loss. Its **dependency oracle** exposes which control and numerical state may change after a design move. The former tells the optimizer what a design does; the latter tells the evaluator what must be recomputed when the design changes.

This dual role follows from keeping statistics-design-dependent decisions executable. Workload-fixed context and a frozen payload repository can be specialized once, but eligibility, winner selection, clause consumption, mechanism composition, and numerical combination cannot be replaced by decisions observed under one design. For the validated fragment, the causal path is therefore statistics state, native semantic replay, DBMS estimate, and finally q-error. A separately learned mapping from a statistics subset directly to q-error is unnecessary inside that boundary. This is not a claim that learned or approximate components are unnecessary outside it.

The distinction from a generic what-if interface is one of representation, not a claim that prior physical-design systems lack hypothetical evaluation. CE-Replay specializes the statistics-sensitive estimator semantics into a workload-specific executable form that exposes both response and dependencies. Detailed comparisons with optimizer calls, cached-response methods, and specialized cost models require literature support and belong in Related Work.

An important state-design lesson follows. A representation sufficient to continue the current execution need not be safe for arbitrary future design extensions, and two states with the same current output need not respond equally to a later toggle. Current-output equivalence is not counterfactual equivalence. The dependency oracle therefore distinguishes realized dependencies from structural or counterfactual dependencies.

## 9.3 What semantics buy: evaluation locality, not global decomposition

The Census evidence separates two notions that are easy to conflate. Its query-candidate graph contains a giant connected component, and the tested semantic factorization does not yield useful independent global subproblems. Commuting transitions and compact execution state likewise do not remove the outer selection problem. The current evidence therefore does not support decomposing Census into independent optimizations or obtaining a free dynamic program from the CE semantics.

Local incremental evaluation remains available because global connectivity does not imply that every move affects every query. Census has sparse candidate-query incidence, and most moves invalidate only a small query neighborhood or require only a numerical update. The exact incremental MCV evaluation preserves the audited search trajectory while substantially reducing control replay. This is locality of recomputation, not decomposition of the feasible design space; candidates that affect disjoint query neighborhoods can still exchange a shared maintenance budget through a swap.

The mixed MCV+FD result provides the necessary runtime qualification. It preserves the full audited trajectory and sharply reduces semantic/control work, but its measured implementation is slower than the already factorized algebraic control evaluator because numerical aggregation and move-loop overhead dominate. Once semantic replay ceases to be the bottleneck, optimization must target the new bottleneck. Executable semantics can substantially reduce exact semantic/control replay; CE-Replay does not always accelerate end-to-end optimization.

DMV tests a complementary regime: a small candidate universe with dense, high-reuse incidence. Dependency-aware evaluation still avoids some full-workload replay, but the opportunity is smaller than in sparse Census. Correctness does not require a disconnected or sparse graph, while performance opportunity depends on topology. Two workloads do not establish a universal scaling law.

## 9.4 Maintenance cost versus semantic utility

Payload bytes were useful as an early controlled resource proxy, but serialized representation size is not the operational resource targeted by the final formulation. Deployed extended statistics incur recurring collection and refresh work. The final problem therefore exposes a generic recurring maintenance-cost function and instantiates it with a mechanism-weighted object-count model calibrated from aggregate `ANALYZE` latency.

The calibration is empirical, first-order, and environment-specific. Census and DMV produce different MCV and FD coefficients, and deployment prediction error remains visible. The coefficients are neither PostgreSQL constants nor candidate-specific latency predictions. The transferable abstraction is a configurable maintenance resource; its measured coefficients must be calibrated for the deployment setting.

Changing resource semantics is part of changing the physical-design problem. On Census, replacing the byte-oriented proxy with the maintenance-oriented model materially changes the selected MCV/FD composition and the resulting frozen-workload loss. This comparison motivates alignment between the operational resource and the optimization constraint; it does not establish that the same magnitude of change occurs universally.

A maintenance budget is a capacity limit, not a utilization target. Because semantic utility is non-monotone, a locally optimal design may leave capacity unused when every feasible ADD is non-improving and no improving exchange exists in the audited neighborhood. Unused capacity is therefore compatible with neighborhood local optimality, but does not prove global optimality.

## 9.5 Frozen hypothetical state versus fresh realization

Optimization and deployment operate on related but distinct objects. The optimizer evaluates candidate definitions against a frozen repository of hypothetical payloads. Physical deployment followed by `ANALYZE` generates a fresh payload realization, and some selected definitions may not materialize an available payload. These phases must not be conflated.

This distinction separates **semantic fidelity** from **realization uncertainty**. Semantic fidelity asks whether CE-Replay and native PostgreSQL agree for the same physical state and payload realization. Realization uncertainty asks how a future `ANALYZE` changes payload values, availability, estimates, and loss relative to the frozen repository. The experiments show floating-point-level same-realization agreement within the supported fragment while fresh realization can change objective values and FD availability.

Repeated Census `ANALYZE` runs strengthen this separation. Payloads and workload loss vary, and a small number of FD control paths change with availability, while every same-realization replay/native comparison remains within the audited tolerance. This evidence does not establish that the selected design is unstable against alternatives, that rankings frequently reverse, or that observed loss variance equals optimization regret. Those questions require paired multi-design realizations.

A natural extension is to optimize expected, risk-sensitive, or worst-case loss across payload realizations, or to measure design-ranking stability under repeated `ANALYZE`. The present optimizer is conditional on one frozen realization and does not implement those robust objectives.

The frozen candidate-payload repository is also a systems boundary. Acquiring payloads for a large hypothetical universe may be expensive, but that one-time offline acquisition cost is distinct from the recurring maintenance cost of the deployed design. The present contribution addresses hypothetical evaluation and selection given payloads; efficient general hypothetical payload acquisition remains future work.

## 9.6 Extending CE-Replay

The prototype is source-informed and mechanism-specific, not an automatic compiler from PostgreSQL source to an intermediate representation. Extending the supported boundary requires identifying native applicability and control semantics, defining the payload schema, implementing executable state transitions, validating them against native instrumentation, and exposing safe dependencies.

Constant `IN` and `= ANY` MCV semantics illustrate this process. The original scalar boundary did not cover the IN-heavy DMV workload. A bounded, source-derived ScalarArray extension was implemented, tested with synthetic semantic cases and scalar regressions, and then validated across the canonical DMV workload. This demonstrates deliberate extensibility, not arbitrary predicate support or automatic extensibility.

MCV and FD also show why mechanisms cannot always be attached as independent correction factors. MCV changes the residual clause state consumed by FD, producing a directed MCV-to-FD composition. A useful extension principle is therefore to model mechanisms as executable state transitions with explicit inputs, outputs, and dependency boundaries. This principle is suggested by the PostgreSQL implementation; the evidence does not establish that every DBMS estimator mechanism admits the same decomposition.

Several details are PostgreSQL-specific: GreedyCover, catalog/OID precedence, MCV and FD payload formats, MCV-before-FD ordering, `ANALYZE` realization behavior, and the PostgreSQL 16.14 predicate boundary. The architectural layer is broader: workload specialization, design-parametric executable semantics, objective and dependency oracles, separation of candidate definition from payload realization, realized versus counterfactual dependencies, frozen versus fresh realization, and maintenance-constrained physical design. These are DBMS-independent abstractions suggested—but not cross-DBMS validated—by this implementation.

## 9.7 Limitations

**Semantic scope.** Validation covers PostgreSQL 16.14 conjunctive base-relation restrictions for the supported scalar predicates, constant `IN`/`= ANY` MCV semantics, MCV, FD, and their directed composition. It does not cover joins, full planner/path search, arbitrary expressions or operators, general `OR`/`NOT` trees, other statistics mechanisms, or arbitrary PostgreSQL versions.

**Implementation method.** The prototype was manually derived from source semantics and native instrumentation. It is not an automatic source-to-IR compiler. Each additional mechanism, predicate family, PostgreSQL version, or DBMS requires engineering and semantic validation.

**Payload acquisition.** Optimization assumes an offline frozen repository of hypothetical candidate payloads. The system does not solve efficient general hypothetical payload generation.

**Optimization guarantee.** The workload-scale solver guarantees only termination at a local optimum under the audited maintenance-feasible ADD/DROP/SWAP neighborhood, fixed payload, and fixed precedence. Exhaustive agreement on a five-candidate Census case and restricted DMV subproblems does not establish full-instance global optimality or an approximation guarantee.

**Maintenance model.** Mechanism-weighted object count is a first-order empirical proxy calibrated independently in the measured environments. It is not a universal PostgreSQL `ANALYZE` cost function or a per-candidate latency model; deployment prediction errors remain part of the evidence.

**Objective.** The evaluated objective is cardinality-estimation q-error for the supplied workload. The system does not directly optimize execution latency, plan quality, or throughput, and the experiments establish no causal query-runtime improvement.

**Realization uncertainty.** Optimization is conditional on frozen payloads. Fresh `ANALYZE` can change numerical payloads or payload availability, and the current optimizer is not realization-robust.

**DMV objective pathology.** Two DMV queries have zero true cardinality. The frozen positive-floor q-error definition makes the raw aggregate loss numerically dominated by these cases. It was retained for experimental consistency; nonzero-truth loss is diagnostic only.

**DMV provenance.** The original DMV optimization artifact did not persist sufficient per-query state for exact paired frozen-to-fresh drift reconstruction. DMV deployment supports physical MCV/FD composition and fresh same-realization replay/native fidelity, but not the complete paired drift analysis available for Census. This is artifact-provenance incompleteness, not semantic mismatch.

**Evidence breadth.** The final core evidence uses Census and DMV. Their sparse/large-universe and dense/IN-heavy structures provide complementary replication, but two workloads do not establish universal workload generality. The supplied target workload is an input; unknown-future-workload generalization is outside the core problem.

Future work follows directly from these boundaries: support joins and additional CE mechanisms; reduce or automate semantic-extraction effort; acquire hypothetical payloads more efficiently; optimize across payload realizations; develop stronger search methods over the same oracle interfaces; connect the objective to plan/runtime outcomes; and evaluate additional DBMSs and workloads.
