# Adversarial Novelty Boundary Audit v0

## 1. Executive verdict

**Outcome B: general primitives are known; the CE-Replay combination/layer remains defensible.** The current work is not fairly reduced to a PostgreSQL CE emulator plus local search. Its defensible contribution is narrower than a new principle of specialization or incremental computation: it is a systems representation specialization that makes native statistics-sensitive estimator control state the object of physical design, and uses that representation both to evaluate hypothetical designs and to derive counterfactual-safe move invalidation.

The adverse case is substantial. INUM and C-PQO already specialize optimizer computation and retain configuration-parametric alternatives; Liu--Ives--Loo and self-adjusting computation already derive exact incremental updates from represented computation and dependencies; *Automating Statistics Management* already discusses dependent statistics, a monotonicity caveat, and a `g`/`h` counterexample in which current behavior is insufficient to infer counterfactual irrelevance; *Index Interactions in Physical Design Tuning* formalizes contextual positive and negative object interactions. Thus none of those general ideas is novel here.

Within the literature and citation neighborhoods searched through 2026-09-23, however, no work inspected combines native statistics-estimator semantics, hypothetical CE/objective evaluation, and exact counterfactual-safe invalidation of statistics-design moves in one workload-specialized executable representation. This is an absence result, not proof of priority. The manuscript needs a Related Work correction because the index-interactions paper is a strong missing comparator and the current treatment of automatic statistics management understates its interaction and latent-alternative content.

Repository baseline: `HEAD = main = origin/main = dc03ea11fe2903ed0a5d82882a47c3dd3fd76724`. This differs from the task's expected `1f045652...` because the authoritative branch had advanced. The annotated tag `research-freeze-v0` still dereferences to `22cf494f954cffff86080236473ca847064dca74`. The worktree was clean before these five audit outputs were added. The current bibliography has 15 entries. Existing Related Work passages on automatic statistics selection, CORDS, JITS, What-If, INUM, C-PQO, constrained design, incremental reoptimization, learned CE, and PostgreSQL semantics were inspected and not edited.

## 2. Current manuscript novelty claim

The following freezes the strongest claims already present; it does not improve them.

- **C1, problem structure.** Statistics objects affect CE through configuration-dependent applicability, winner selection and precedence, clause consumption, residual state, mechanism reachability, MCV-to-FD suppression/re-enablement, and numerical composition—not context-independent additive benefits. PostgreSQL's mechanisms are not claimed as novel.
- **C2, representation.** CE-Replay preserves workload-fixed context while leaving statistics-design-sensitive estimator semantics executable. It is workload-specialized, design-parametric, and faithful within a bounded fragment. Generic partial evaluation is not claimed.
- **C3, dual interface.** The same representation supplies hypothetical objective evaluation and semantic dependency/invalidation information. Whether this combination is novel is the audit target.
- **C4, counterfactual dependencies.** Exact moves can depend on unused candidates, alternative winners, changed consumption, and re-enabled downstream mechanisms. A current trace or equal current output can therefore be insufficient.
- **C5, physical-design use.** The representation evaluates resource-constrained statistics-design moves exactly within the supported boundary. Local search and maintenance budgeting are not novelty claims.

## 3. Adversarial methodology

The search attempted to falsify N1--N6 rather than confirm project terminology. It used original papers wherever available, mapped source facts to CE-Replay only after reading the mechanism, and separated three levels:

- **SOURCE FACT:** what a paper explicitly represents or executes.
- **MAPPING:** its closest CE-Replay analogue.
- **JUDGMENT:** whether that overlap anticipates the claimed combination.

YES/PARTIAL cells in the matrix report implemented or exploited properties, not hypothetical extensions. Search snippets were used only for discovery. A negative result is stated only for the searched corpus and date.

## 4. Search coverage

The audit covered ACM/IEEE records, official VLDB/PVLDB PDFs, Microsoft Research and author copies, PMC, DBLP, Crossref, and publisher pages. It followed the mandatory seed neighborhoods: AutoAdmin What-If; INUM and descendants; C-PQO and PQO; automatic statistics management, CORDS, JITS, and synopsis tuning; Liu--Ives--Loo; constrained/online physical design and index interactions; and self-adjusting computation/Adapton. Concept queries and saturation evidence are recorded in `results/adversarial-novelty-search-log-v0.md`.

Repeated searches converged on four neighborhoods: configuration-parametric optimizer response; statistics acquisition/selection; exact incremental optimizer/computation maintenance; and contextual physical-design interaction. Citation chaining found descendants and applications but no closer merger of all four. This establishes search saturation for this audit, not historical exhaustiveness.

## 5. Prior-art family analysis

### A. Automatic statistics management

Chaudhuri and Narasayya's 2001 system is the strongest statistics-specific threat. **SOURCE FACT:** it optimizes subsets of statistics through optimizer sensitivity; acknowledges dependencies among statistics; assumes monotonic plan-quality benefit while explicitly allowing pathological violations; and gives an MNSA/D example where `g` is dispensable under `S` but not under `S ∪ {h}`. **MAPPING:** statistic value is contextual, and current behavior does not prove safe counterfactual removal. **JUDGMENT:** N1 and the general intuition behind N4 were anticipated. It does not retain executable estimator control state or expose an exact dependency oracle; it repeatedly interrogates the optimizer.

CORDS discovers correlations/soft FDs and JITS acquires/maintains sensitive statistics. Synopsis-tuning work jointly chooses summaries and memory. These address candidate/payload acquisition or resource allocation, not the audited dual-interface representation.

### B. What-if physical design

AutoAdmin What-If makes a configuration explicit and returns optimizer plan/cost response without building indexes. Index-selection, materialized-view, and constrained-design systems use that interface. Their principal abstraction is an optimizer response oracle, not a preserved estimator-semantic computation exposing exact invalidation. Index-interaction work nevertheless proves that context-dependent, positive, and negative object interactions are a known physical-design principle.

### C. INUM and descendants

INUM preprocesses a query into an INUM space of optimizer-derived plans/subplans; configuration-specific access costs are plugged into a formula. It reuses query-fixed optimizer work and retains alternatives relevant under other configurations. This substantially anticipates C2 at the architectural level. The inspected work does not derive a semantic candidate dependency interface from the same structure or use it for exact move-local recomputation.

### D. C-PQO and PQO

C-PQO uses a specialized optimizer call to build compact MEMO/APR state that returns plans for arbitrary configurations. Configuration-independent computation is fixed while access-path leaves remain configuration-dependent. Classical PQO similarly retains optimal alternatives over parameter regions. These works defeat any broad claim to configuration-parametric executable/reusable representation; they do not model statistics consumption/reachability or expose an exact design-delta dependency oracle.

### E. Incremental query optimization/reoptimization

Liu--Ives--Loo retain optimizer search and pruning state in a relational/Datalog representation and incrementally update it after cost/cardinality changes, including reintroducing alternatives previously pruned. That is a strong structural analogue to C3/C4: one representation supplies output and dependencies, and inactive alternatives can return. The exogenous delta is changed estimates/costs; the work does not represent how a statistics design generates those estimates through estimator semantics.

### F. Incremental/self-adjusting computation

Dynamic dependence graphs, memoization, change propagation, and Adapton establish the general abstraction “executable computation plus dependencies gives from-scratch-consistent incremental recomputation.” Control-flow changes are routine concerns. Consequently the abstract dependency principle and exact incremental recomputation are not CE-Replay novelty. What remains potentially distinct is identifying the conservative statistics-semantic dependency closure needed before a design move, including candidates absent from the current realized estimator path.

### G. Cardinality-estimation systems

Traditional, learned, and factorized CE systems estimate cardinality, often via reusable models, but the inspected systems do not preserve native estimator behavior as a statistics-configuration-parametric executable representation used for exact physical-design invalidation. The distinction is native semantic/design state, not simply “trained versus untrained.”

### H. Other physical-design objects

Indexes provide the closest analogy. Index interactions establish contextual design value, while INUM/C-PQO preserve configuration-dependent optimizer alternatives. Online tuning incrementally maintains approximate benefit information. No inspected partitioning, view, synopsis, sampling, or settings work supplied the full executable-semantic plus exact dependency-oracle combination. This is a bounded search conclusion.

## 6. Decision-critical papers

No individual paper is classified `DECISION-CRITICAL`; the following `CLOSE` papers form the strongest composite challenge.

### Chaudhuri and Narasayya, “Automating Statistics Management for Query Optimizers,” TKDE 2001

- **Problem/configuration:** select a useful statistics subset; variables are statistics presence.
- **Frozen/executable state:** query workload and optimizer sensitivity experiments are reused conceptually, but no estimator program/state is retained as a design-parametric executable artifact.
- **Dependencies/invalidation:** dependencies are acknowledged; MNSA/D guards against a statistic becoming useful with another statistic. It uses repeated optimizer/sensitivity analysis, not a dependency-derived exact delta evaluator.
- **Inactive alternatives/design/CE:** the `g`/`h` example explicitly captures dormant relevance under another configuration. It is statistics physical design and is mediated by CE/optimization, but estimator internals are not represented.
- **Dual interface:** no; optimizer response and dependency evidence are not derived from one retained semantic representation.
- **Overlap/non-overlap:** strongest overlap is contextual statistics value, latent interaction, and the monotonicity caveat. Missing are native MCV/FD semantics, consumption/reachability state, and exact incremental move evaluation.
- **Reviewer argument:** CE-Replay rediscovers that statistics are dependent and current optimizer output is unsafe for elimination.
- **Fair rebuttal:** CE-Replay does not claim that observation; it operationalizes a different evaluator/invalidation representation beneath the optimizer calls used by this work.
- **Classification:** `CLOSE`; strong narrowing evidence, not the same intellectual combination. Evidence: Sections 3.2--5.2, especially 3.3 and the MNSA/D counterexample.

### Papadomanolakis, Dash, and Ailamaki, “Efficient Use of the Query Optimizer for Automated Physical Design” (INUM), VLDB 2007

- **Problem/configuration:** accelerate what-if costing across physical configurations, principally indexes.
- **Frozen/executable state:** query-fixed optimizer work and template plans/subplans form INUM Space; access costs remain configuration inputs.
- **Dependencies/invalidation:** latent plans are retained, but the inspected mechanism does not expose a move-dependency oracle or exact incremental invalidation derived from INUM Space.
- **Physical design/statistics:** directly supports physical design, not native statistics-estimator semantics.
- **Dual interface:** response yes; dependency interface no.
- **Overlap/non-overlap:** it strongly overlaps workload specialization, design parametrization, interactions, and hypothetical response. It lacks statistics control-state transitions and their counterfactual dependency closure.
- **Reviewer argument:** CE-Replay is INUM at the estimator layer.
- **Fair rebuttal:** that is a useful architectural analogy, but INUM's representation need not decide applicability, consumption, or downstream mechanism reachability to determine which estimator computation must be invalidated.
- **Classification:** `CLOSE`, a strong structural analogue. Evidence: Sections 3--4 of the VLDB paper.

### Reddy and Haritsa, “Configuration-Parametric Query Optimization for Physical Design Tuning,” SIGMOD 2008

- **Problem/configuration:** produce optimizer plans for arbitrary physical configurations after one specialized optimization.
- **Frozen/executable state:** configuration-independent MEMO computation is frozen; APR leaves and alternatives encode configuration sensitivity.
- **Dependencies/invalidation:** alternatives can activate under new configurations, but no explicit exact design-move dependency/invalidation interface is supplied.
- **Physical design/statistics:** physical design yes; estimator/statistics semantics no.
- **Dual interface:** the structure yields response, not the audited dependency oracle.
- **Overlap/non-overlap:** it is the closest prior representation for C2 and latent alternatives. CE-Replay's residual distinction is the represented computation and the dependency consequence, not merely its lower layer.
- **Reviewer argument:** both partially evaluate native optimizer computation by design and preserve dormant configuration alternatives.
- **Fair rebuttal:** C-PQO does not identify statistics-semantic state whose transitions determine both CE response and safe move-local invalidation.
- **Classification:** `CLOSE`, strong structural analogue. Evidence: Sections 2--4.

### Liu, Ives, and Loo, “Enabling Incremental Query Re-Optimization,” SIGMOD 2016

- **Problem/configuration:** update optimized plans after cost/cardinality facts change.
- **Frozen/executable state:** optimizer search/pruning state is retained relationally; rules remain executable.
- **Dependencies/invalidation:** incremental view maintenance propagates exact deltas; previously pruned plans can be rederived/reintroduced.
- **Physical design/statistics:** not a physical-statistics design evaluator; changed estimates are inputs rather than consequences of candidate statistics.
- **Dual interface:** yes at optimizer-state level: the representation computes the result and supports incremental maintenance.
- **Overlap/non-overlap:** strongly anticipates C3/C4 structurally. It stops at the CE boundary and does not expose statistics applicability, precedence, consumption, or MCV-to-FD reachability.
- **Reviewer argument:** CE-Replay's dependency oracle is ordinary incremental maintenance of a lower-level optimizer subprogram.
- **Fair rebuttal:** the general method is known; the contribution can only be the domain-specific semantic dependency identification and its use in statistics design.
- **Classification:** `CLOSE`, strong structural analogue. Evidence: Sections 3--5.

### Schnaitter, Polyzotis, and Getoor, “Index Interactions in Physical Design Tuning,” PVLDB 2009

- **Problem/configuration:** quantify and exploit context-dependent index interactions for tuning, visualization, partitioning, and scheduling.
- **Frozen/executable state:** configurations are passed to an opaque what-if `optplan_q(X)`/cost response; internal optimizer computation is not retained.
- **Dependencies/invalidation:** exact pair interaction is defined from contextual benefits, but no semantic dependency graph drives exact incremental move recomputation.
- **Inactive alternatives/design:** indexes may be useless alone and useful jointly; this is explicit latent relevance in physical design.
- **Statistics/dual interface:** no estimator-statistics semantics and no shared response/dependency representation.
- **Overlap/non-overlap:** directly anticipates non-additive object value and output-equivalence insufficiency, but not CE-Replay's mechanism.
- **Reviewer argument:** contextual design-object interactions were already formalized and exploited.
- **Fair rebuttal:** accepted; CE-Replay's claim must be how exact native estimator-state transitions are represented and invalidated, not discovery of interaction.
- **Classification:** `CLOSE`; missing and material Related Work. Evidence: Sections 1--4 and Definitions 2.2--2.3.

### Acar et al., “A Library for Self-Adjusting Computation,” ENTCS 2006

- **Problem/configuration:** update program results efficiently after input changes.
- **Frozen/executable state:** stable computation is reused; dynamic dependence graphs and memoized traces retain computation state.
- **Dependencies/invalidation:** change propagation maintains data/control dependencies and aims at from-scratch-equivalent results as paths change.
- **Inactive alternatives/design/statistics:** branch changes are supported by re-execution and new dependencies, but no physical design or estimator-specific conservative candidate closure exists.
- **Dual interface:** executable traces drive both result and dependency maintenance.
- **Overlap/non-overlap:** it substantially anticipates N3's abstract principle and exact incremental recomputation; it does not solve which native statistics-semantic dependencies must be exposed for arbitrary design moves.
- **Reviewer argument:** the oracle is a standard dynamic dependence graph.
- **Fair rebuttal:** dependency tracking is standard; mapping PostgreSQL estimator semantics into a safe physical-design dependency boundary remains a domain-specific systems mechanism.
- **Classification:** `CLOSE` as a conceptual analogue, not database prior art. Evidence: Sections 1--3.

## 7. Claim-by-claim overlap matrix

The complete A--O matrix is in `results/adversarial-novelty-overlap-matrix-v0.csv`. Its important pattern is disjunctive: INUM/C-PQO cover A--G and J/K/L; Liu and self-adjusting computation cover D/E/G--K/O; automatic statistics management and index interactions cover A/F/G/J--L/O. Only CE-Replay's row has explicit support across M (estimator/statistics semantics), N (cross-mechanism reachability), H/I (same-representation exact invalidation), and physical-design search simultaneously.

## 8. Could CE-Replay be described as INUM/C-PQO one layer lower?

**Strongest YES.** Both approaches specialize native optimizer computation to a workload, freeze configuration-independent work, leave physical design as an input, retain alternatives that different configurations can activate, and evaluate many hypothetical configurations without full native optimization. At that abstraction level CE-Replay follows an established intellectual move, and “a different layer” alone is not novelty.

**Strongest NO.** In statistics design, the represented state transitions are not only a response surface. Applicability, precedence, winner choice, clause consumption, and residual state determine which mechanism executes next and therefore which candidates can affect the response after a move. That state is also the information required to invalidate a move safely. INUM/C-PQO retain alternative plans/access paths to return a configuration response, but the inspected work does not expose from that representation the conservative statistics-candidate closure needed for exact move-local evaluation.

**Decision: PARTIALLY.** INUM/C-PQO substantially anticipate the representation pattern and hypothetical interface. They do not substantially anticipate the specific same-representation dependency consequence at the statistics-estimator layer. The remainder is a specialization/combination, not a wholly new representation principle.

## 9. Is the dependency oracle merely ordinary incremental computation?

**Strongest YES.** Dynamic dependency graphs and incremental view maintenance already show that executable computation can expose dependencies and support exact updates despite control-flow changes. Liu applies this directly to optimizer state. Calling the output a “dependency oracle” does not create a new abstraction.

**Strongest NO.** An ordinary realized trace is not automatically sufficient for an arbitrary statistics addition/removal: an absent object may become the winner, altered consumption may re-enable FD, and equal current estimates may conceal different future states. The domain work is to encode a conservative semantic closure over candidate applicability and mechanism reachability while retaining executable native semantics.

**Decision: plausible but domain-specific, and defensibly distinct as a systems mechanism.** The abstract incremental-computation principle is established; novelty must be limited to discovering/exposing the correct statistics-semantic dependency structure and integrating it with the design evaluator.

## 10. Latent/counterfactual dependency analysis

The general distinction between realized and potential dependencies is established. Self-adjusting computation handles changing control paths; C-PQO retains access alternatives for configurations; Liu can reintroduce pruned plans; automatic statistics management's `g`/`h` example shows current irrelevance does not imply counterfactual irrelevance; index interactions show an object can be useless alone but useful jointly.

CE-Replay therefore cannot claim latent dependency as a new principle. What is materially specialized is the exact structural closure for statistics candidates and downstream estimator mechanisms. Its “realized versus structural/counterfactual” split is best characterized as a known principle made explicit and operational in a statistics-estimator representation.

## 11. Statistics-specific prior art

Prior systems did not uniformly assume independent benefits: automatic statistics management acknowledges dependencies, and synopsis selection jointly allocates resources. They commonly use repeated optimizer calls, sensitivity, sampling, or constructed synopses rather than preserve native estimator execution. The inspected papers do not model PostgreSQL-style precedence order, clause consumption, MCV suppression of FD, or derive exact incremental move invalidation from those semantics. Thus contextual statistics value is prior art; executable stateful multi-mechanism evaluation plus dependency extraction is the narrower remainder.

## 12. Non-monotonicity prior art

**Classification: KNOWN POSSIBILITY, NEW MAGNITUDE/SETTING.** The 2001 automatic-statistics paper explicitly assumes monotonic benefit for tractability but notes pathological violations (an existing “magic number” can accidentally be more accurate than a histogram), and contextual index interaction permits negative benefit. CE-Replay's Census/DMV results provide systematic evidence under native PostgreSQL MCV/FD design and its objective. They support the need for semantic evaluation; they are not a historically new phenomenon.

## 13. Cross-mechanism composition prior art

MCV-to-FD suppression/re-enablement is PostgreSQL behavior, not an invented mechanism. More broadly, sequential/stateful estimator composition is a known kind of systems problem. Yet the searched statistics-design work did not represent mechanism A's clause consumption as changing mechanism B's reachability and then exploit that relation for exact design-move invalidation. The result is therefore both a representative instance of a broader composition issue and, within this search, a previously unrepresented physical-design interaction. Historical priority remains uncertain.

## 14. Hypothetical-payload boundary

The frozen candidate-payload repository matches the standard factoring used by many physical-design studies: separate candidate construction/materialization from repeated hypothetical evaluation. Earlier statistics work addresses sampling, synopsis construction, sensitivity-guided acquisition, and maintenance; CE-Replay intentionally does not solve those problems. This strengthens semantic isolation but weakens end-to-end practical novelty: payload acquisition cost and uncertainty are assumed away, not solved. That limitation is orthogonal to replay correctness.

## 15. Novelty decomposition

| Component | Classification |
|---|---|
| Workload specialization | ESTABLISHED PRIOR ART |
| Configuration-parametric representation | ESTABLISHED PRIOR ART |
| Executable replay | KNOWN GENERAL PRINCIPLE / NEW REPRESENTATION SPECIALIZATION |
| Objective oracle | KNOWN DATABASE PRINCIPLE |
| Dependency oracle | KNOWN GENERAL PRINCIPLE / NEW SYSTEMS MECHANISM in this semantic boundary |
| Exact incremental recomputation | ESTABLISHED PRIOR ART |
| Structural/counterfactual dependency | KNOWN GENERAL AND DATABASE PRINCIPLE |
| Statistics-semantic state as design representation | NEW REPRESENTATION SPECIALIZATION |
| MCV/FD interaction | native fact; NEW SYSTEMS MECHANISM in represented design evaluation |
| Non-monotonicity evidence | NEW EMPIRICAL EVIDENCE in this magnitude/setting |
| Maintenance-constrained search | ESTABLISHED PRIOR ART |
| Dual-interface representation | NEW COMBINATION, strongly anticipated by incremental computation |
| Physical deployment validation | engineering/evaluation contribution |

### N1--N6 falsification

- **N1.** Counterexample: automatic statistics management and index interactions. They cover contextual dependence, so N1 is a known database principle. Distinct remainder: native estimator control state made explicit. Confidence: high.
- **N2.** Counterexample: INUM/C-PQO/PQO. They cover workload-specialized configuration-parametric execution. Distinct remainder: bounded native CE semantics, an application/specialization. Confidence: high.
- **N3.** Counterexample: Liu and self-adjusting computation. They cover a representation supplying result and dependencies. Distinct remainder: statistics-semantic dependency extraction for design moves. Confidence: high.
- **N4.** Counterexample: C-PQO latent alternatives, Liu's pruned-plan reintroduction, AutoStats `g`/`h`, and index interactions. General claim is prior art. Distinct remainder: conservative candidate/mechanism closure in this estimator. Confidence: high.
- **N5.** Counterexample: contextual physical-object interaction and general estimator composition. The broad principle is known. Distinct remainder: empirical/operational MCV-to-FD reachability in design evaluation. Confidence: medium.
- **N6.** No inspected single work covers the full conjunction. The conjunction remains a new representation specialization/combination, not invention of its primitives. Confidence: medium.

## 16. Strongest Weak-Reject case after literature audit

A skeptical reviewer can say CE-Replay composes three established techniques without a new abstraction: INUM/C-PQO supply workload-specialized configuration-parametric reuse; Liu/self-adjusting computation supply result-plus-dependency exact maintenance; automatic statistics management and index interactions already establish contextual and dormant design-object interactions. PostgreSQL MCV/FD replay is then careful domain engineering, while local search, budget constraints, and deployment validation are conventional. The frozen payload repository also omits candidate acquisition. If the paper implies novelty in any general primitive, this case is persuasive.

## 17. Strongest Accept case after literature audit

Systems contributions can reside in choosing the right represented boundary. Statistics objects modify the estimator's control/state transitions, not only access feasibility or terminal costs. Encoding that bounded native computation so the same artifact both predicts hypothetical CE and identifies a counterfactual-safe affected set makes exact large-neighborhood design evaluation possible without invoking the native optimizer per design. None of the inspected comparators performs this conjunction, and the evaluation demonstrates fidelity, optimization utility, non-monotonic interactions, multi-mechanism composition, and deployment. Framed as a nontrivial representation specialization, it is defensible.

## 18. Final novelty-boundary verdict

**GENERAL PRIMITIVES KNOWN, COMBINATION/LAYER DEFENSIBLE.** The work is best judged a **nontrivial domain specialization**—borderline but defensible as a systems representation contribution. The single strongest reason is that the estimator-semantic state needed to calculate a design's response is also made explicit enough to determine conservative, exact move invalidation across precedence, consumption, and downstream mechanism reachability. This is more than an emulator plus search, but less than a new general representation or incremental-computation principle.

## 19. Manuscript implication

**ACTION 2 — RELATED-WORK CORRECTION REQUIRED.** No manuscript edit was made. A future narrow revision should:

1. cite and compare *Index Interactions in Physical Design Tuning*, conceding that contextual positive/negative object interactions and useless-alone/useful-together behavior are established;
2. revise the automatic-statistics discussion to acknowledge its explicit statistics dependencies, `g`/`h` latent-interaction counterexample, and monotonicity caveat;
3. state explicitly that INUM/C-PQO anticipate workload-specialized configuration-parametric representation and that Liu/self-adjusting computation anticipate result-plus-dependency incremental maintenance;
4. locate novelty only in the statistics-estimator semantic specialization/combination and avoid “first,” generic dependency, partial-evaluation, interaction, or non-monotonicity claims.

This is a Related Work/positioning correction, not scientific restructuring.

## 20. Remaining uncertainty

The most important unresolved uncertainty is whether a statistics advisor, optimizer memo-reuse descendant, commercial/internal system, thesis, or non-English/preprint source outside the searched citation neighborhoods already exposes an exact estimator-internal dependency structure for hypothetical statistics configurations. Also uncertain is how a reviewer weights a new represented layer: one may regard the semantic closure as substantial systems design, another as expected specialization of C-PQO plus incremental computation. No negative search can settle that judgment or prove historical priority.

## Explicit answers Q1--Q10

1. **No.** The manuscript contains a coherent estimator-semantic representation and exact incremental design-evaluation mechanism beyond emulation plus local search.
2. **No, not in general.** Workload-specialized design-parametric representation is established by PQO/INUM/C-PQO and program specialization.
3. **No, not in general.** Incremental query optimization and self-adjusting computation already derive results and dependencies from represented computation.
4. **Not materially as a complete combination in the searched work.** Its components are strongly anticipated separately; the statistics-semantic conjunction was not identified.
5. **Partially.** INUM/C-PQO substantially anticipate specialization, configuration parametrization, latent alternatives, and hypothetical response, but not the estimator-semantic dependency/invalidation consequence.
6. **Substantially at the structural level, not at the statistics-design boundary.** Liu anticipates retained executable optimizer state, dependency propagation, exact update, and reactivated alternatives.
7. **Yes.** It substantially anticipates the abstract dependency and exact recomputation principle.
8. **The remainder is** a workload-specialized executable representation of native statistics-estimator control/state that simultaneously evaluates hypothetical CE/objectives and exposes conservative dependencies for exact moves, including precedence, consumption, and cross-mechanism reachability, plus its validated PostgreSQL realization.
9. **Yes, with disciplined scope.** It is a defensible systems representation specialization/combination, best described as nontrivial domain specialization rather than a new general principle.
10. **ACTION 2.** Add the missing index-interactions comparison, accurately credit automatic-statistics latent interactions/non-monotonicity, and narrow positioning against INUM/C-PQO, Liu, and incremental computation.

NOVELTY AUDIT B — GENERAL PRIMITIVES KNOWN, COMBINATION/LAYER DEFENSIBLE

ACTION 2 — RELATED-WORK CORRECTION REQUIRED

- **Strongest prior-art threat:** the composite of C-PQO/INUM, Liu--Ives--Loo/self-adjusting computation, and automatic-statistics/index-interaction work.
- **Strongest remaining distinction:** one native statistics-estimator semantic representation supplies both hypothetical CE response and counterfactual-safe exact design-move invalidation across mechanism reachability.
- **Confidence:** MEDIUM.
- **Most important unresolved uncertainty:** undiscovered advisor/memo-reuse work may already expose estimator-internal configuration dependencies, and reviewer judgment may treat the remaining layer specialization as incremental.
