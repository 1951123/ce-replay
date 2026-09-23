# Novelty Boundary Correction Plan v0

## 1. Provenance result

**PROVENANCE PASS — INTERVENING COMMITS UNDERSTOOD.**

- Current `HEAD`, `main`, and `origin/main`: `dc03ea11fe2903ed0a5d82882a47c3dd3fd76724`.
- Expected earlier baseline: `1f0456521ae01173d41503e1f7e0884cc33d36ea`.
- One intervening commit exists: `dc03ea11fe2903ed0a5d82882a47c3dd3fd76724`, author `1951123 <19511238172@163.com>`, authored/committed `2026-09-22T22:26:41+08:00`, message `paper: correct constrained-design DOI`.
- That commit changes the DOI for *Constrained Physical Design Tuning* from `10.14778/1453856.1453857` to `10.14778/1453856.1453863` in the two bibliography copies and the literature pack; updates bibliography/link/PDF/package audit metadata; and rebuilds the two submission PDFs. It does not change manuscript prose, experiments, empirical values, frozen research artifacts, author metadata, figures, tables, or scientific claims.
- Explicit `1f045652...HEAD` diff: 10 files, 13 insertions, 12 deletions; all text changes are the DOI and dependent audit hashes/counts/status. Binary PDF changes are explained by rebuilding with the corrected reference URL.
- `research-freeze-v0^{}` remains exactly `22cf494f954cffff86080236473ca847064dca74`.
- Before this task, the only working-tree additions were the five uncommitted outputs of `Adversarial-Novelty-Boundary-Audit-v0`; there were no tracked modifications.

The authoritative scientific source remains `docs/paper-full-draft-v6-evaluation-hierarchy.md`, as stated in `paper/pvldb2027/README.md`; the typeset source remains `paper/pvldb2027/main.tex`, generated mechanically by `paper/pvldb2027/convert_from_markdown.py`. Pre-edit SHA-256 values are:

- Markdown: `2340f0c4c650d20366a282ea794b68a6f3e2524b47a2a752d832a580400ffa5f`.
- LaTeX: `f7d035ccecabd7ecf2af80879b121398e7ab9c8ee07aec24a1a973021a2f109e`.

The texts are synchronized before editing: the abstract, ten top-level sections, four RQs, four contributions, empirical values, and Related Work claims agree; Markdown production notes are intentionally converted to LaTeX figures/tables.

## 2. Primary-source evidence

### 2.1 Automatic Statistics Management

**Source.** Surajit Chaudhuri and Vivek R. Narasayya, “Automating Statistics Management for Query Optimizers,” *IEEE TKDE* 13(1):7--20, 2001, DOI `10.1109/69.908978`. Inspected Sections 3.2--5.2, especially pp. 10--15 in the journal pagination.

**SOURCE FACT.** The paper selects a statistics set for a workload using optimizer plan/cost sensitivity. Section 3.3 introduces a cost-monotonicity assumption but explicitly notes a pathological violation in which a selectivity “magic number” can happen to give a better estimate/plan than a histogram. Section 4 states that dependencies among statistics can exist (including paired join statistics). Section 5's MNSA/D discussion gives the counterexample `Plan(Q,S)=Plan(Q,S∪{g})` while `Plan(Q,S∪{h})` differs from `Plan(Q,S∪{g,h})`: `g` may appear dispensable in the current context yet matter after `h` is present. The algorithms use repeated optimizer calls/plan comparisons; they do not materialize executable estimator control state.

**MAPPING TO CE-REPLAY.** Statistics value is contextual; current-output equivalence is insufficient to establish counterfactual irrelevance. This anticipates the motivation behind semantic dependencies and prevents presenting “more statistics can hurt” or latent interaction as historically unique.

**NOVELTY IMPLICATION.** The manuscript must credit statistics dependencies/interactions and the monotonicity caveat. A verified remaining distinction is that CE-Replay represents bounded estimator applicability, precedence, consumption, numerical state, and MCV-to-FD reachability and derives move invalidation from that representation.

### 2.2 Index Interactions

**Source.** Karl Schnaitter, Neoklis Polyzotis, and Lise Getoor, “Index Interactions in Physical Design Tuning: Modeling, Analysis, and Applications,” *PVLDB* 2(1):1234--1245, 2009, DOI `10.14778/1687627.1687766`. Inspected Sections 1--4, especially Definitions 2.1--2.3 and Section 3.

**SOURCE FACT.** The objects are indexes. The paper defines contextual benefit using the cost of `optplan_q(X)` and defines degree of interaction for indexes `a,b` relative to a background configuration `X`. Positive and negative interactions occur: an index can increase another's benefit or make it redundant; objects unused alone can be valuable together. The optimizer plan is explicitly treated as an opaque object with cost and used-index properties. A well-behaved-optimizer monotonicity property is used for query cost. The algorithms identify/approximate interaction information for visualization, partitioning, and materialization scheduling; they do not retain optimizer/estimator execution or derive an exact semantic invalidation set for each move. The `g/h` notation belongs to the automatic-statistics paper, not this paper.

**MAPPING TO CE-REPLAY.** Contextual and latent configuration interaction among physical-design objects is established prior art.

**NOVELTY IMPLICATION.** CE-Replay cannot claim novelty because candidate value is contextual. The narrower distinction is representation of the estimator-semantic transitions producing statistics interactions and their use for hypothetical CE and exact move evaluation.

### 2.3 INUM

**Source.** Stratos Papadomanolakis, Debabrata Dash, and Anastasia Ailamaki, “Efficient Use of the Query Optimizer for Automated Physical Design,” *VLDB 2007*, pp. 1093--1104, official proceedings PDF `https://www.vldb.org/conf/2007/papers/research/p1093-papadomanolakis.pdf`. Inspected Sections 1--4.

**SOURCE FACT.** INUM preprocesses each query using optimizer invocations, caches a finite INUM Space of template plans, and separates fixed internal plan structure from configuration-dependent slot access methods/costs. It estimates optimizer-equivalent query cost for many index configurations and accelerates index-selection algorithms. Alternative templates cover behavior under configurations. The paper does not expose a candidate-to-internal-state dependency oracle or use the representation for exact incremental invalidation after a configuration move; estimator-internal statistics state is outside its representation.

**MAPPING TO CE-REPLAY.** Workload/query specialization, reusable configuration-parametric representation, hypothetical response evaluation, and retained alternatives are prior art.

**NOVELTY IMPLICATION.** “Avoid repeated optimizer calls,” specialization, and design parametrization are not CE-Replay novelty. The remaining distinction must name estimator-semantic control state and its invalidation consequence.

### 2.4 C-PQO

**Source.** Nicolas Bruno and Rimma V. Nehme, “Configuration-Parametric Query Optimization for Physical Design Tuning,” *SIGMOD 2008*, pp. 941--952, DOI `10.1145/1376616.1376710`. Inspected Sections 2--4, especially Section 2.2 and Sections 3.1--3.3.

**SOURCE FACT.** C-PQO modifies a Cascades optimizer to create one compact MEMO/APR representation after a specialized optimization call. Configuration-independent optimizer structure is reused; access-path requests remain dependent on arbitrary physical configurations. Configuration-sensitive pruning is relaxed so alternatives needed under other configurations are not lost, and the structure can infer a plan for an input configuration.

**MAPPING TO CE-REPLAY.** It is not final-plan caching: it is a strong configuration-parametric internal optimizer representation with latent alternatives.

**NOVELTY IMPLICATION.** CE-Replay's distinction cannot be “one reusable representation over configurations.” C-PQO does not represent statistics-estimator applicability, clause consumption, residual state, or cross-mechanism reachability, nor expose their exact move-dependency closure.

### 2.5 Incremental query re-optimization

**Source.** Mengmeng Liu, Zachary G. Ives, and Boon Thau Loo, “Enabling Incremental Query Re-Optimization,” *SIGMOD 2016*, pp. 1705--1720, DOI `10.1145/2882903.2915212`. Inspected Sections 2--5, especially Sections 3, 4, and 5.1--5.4.

**SOURCE FACT.** The optimizer is expressed as recursive Datalog; retained memoized search/cost/pruning state is incrementally maintained as runtime cost/cardinality information changes. Incremental view-maintenance and pruning rules propagate changes and reproduce the plan selected by full optimization. Because pruning state must be maintained, previously pruned alternatives can be rederived/reintroduced. Cardinality estimation is described as an external component; statistics-design changes and estimator internal state are not represented.

**MAPPING TO CE-REPLAY.** One executable retained representation providing output and affected-state determination, exact change propagation, and reactivation of inactive alternatives are established optimizer principles.

**NOVELTY IMPLICATION.** Generic dependency-aware exact recomputation and latent alternatives cannot be claimed. CE-Replay's narrower systems work is identifying statistics-estimator semantic dependencies for statistics-design moves.

### 2.6 Representative self-adjusting computation

**Source.** Umut A. Acar, Guy E. Blelloch, Matthias Blume, Robert Harper, and Kanat Tangwongsan, “A Library for Self-Adjusting Computation,” *ENTCS* 148(2):127--154, 2006, DOI `10.1016/j.entcs.2005.11.043`; corroborated by Acar's official CMU 2005 thesis, report CMU-CS-05-129. Inspected paper Sections 1--3 and the official thesis description.

**SOURCE FACT.** Modifiable references, selective memoization, dynamic dependence graphs/traces, and change propagation update outputs after input changes. Dependence tracking includes data/control behavior; re-execution can alter the dynamic trace. The general correctness goal is consistency with from-scratch computation. A currently untaken branch need not be a current dynamic dependency; when control changes, re-execution creates the new trace. The work is not a physical-design or CE system and does not prescribe a precomputed conservative candidate closure for arbitrary statistics moves.

**MAPPING TO CE-REPLAY.** “Executable computation plus dependency information enables exact change propagation” is an established general principle.

**NOVELTY IMPLICATION.** The paper should not claim generic dependency tracking, structural dependency, or change propagation. A PL citation in the main manuscript is not necessary: the existing Liu citation is the closer database comparator, and page budget favors acknowledging the general principle in prose.

### 2.7 Non-monotonicity and cross-mechanism classification

The conservative classification is **previously known possibility with new scale/mechanism evidence**. Automatic Statistics Management explicitly permits pathological harm; Index Interactions formalizes context-dependent positive/negative effects, though for indexes and plan cost. CE-Replay's Census/DMV results remain systematic evidence for a PostgreSQL extended-statistics q-error objective and justify semantics-aware selection; they are not a historical-priority claim.

No inspected prior statistics-design paper represents an upstream statistics mechanism consuming estimator state and thereby disabling/re-enabling a downstream mechanism, then uses that reachability for exact move invalidation. PostgreSQL's MCV-to-FD behavior itself is not novel. The bounded contribution is representing this state transition inside the evaluator/dependency structure.

## 3. Phase A overlap table

Every YES/PARTIAL below is grounded in the sections identified above.

| Prior work | Config-parametric rep. | Query specialization | Physical-design input | Contextual interaction | Latent alternatives | Executable internal computation | Optimizer state | Estimator state | Dependency rep. | Exact incremental | Counterfactual config. | Stats selection | Hypothetical CE | Same rep. response+deps | Cross-mechanism reachability | Strongest overlap | Strongest difference | Primary evidence |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Automatic Statistics Management | PARTIAL | PARTIAL | YES | YES | YES | NO | NO | PARTIAL | PARTIAL | NO | YES | YES | PARTIAL | NO | NO | Contextual/latent statistics relevance | Repeated optimizer comparisons; no retained estimator semantics/invalidation oracle | §§3.2--5.2; §3.3 caveat; MNSA/D `g/h` example |
| Index Interactions | PARTIAL | PARTIAL | YES | YES | YES | NO | NO | NO | PARTIAL | NO | YES | NO | NO | NO | NO | Contextual positive/negative physical-object interaction | Opaque plan/cost response; no semantic exact invalidation | §§1--4; Defs. 2.1--2.3 |
| INUM | YES | YES | YES | YES | YES | PARTIAL | PARTIAL | NO | NO | NO | YES | NO | NO | NO | NO | Reusable configuration-parametric hypothetical response | No dependency interface or estimator control state | §§1--4 |
| C-PQO | YES | YES | YES | YES | YES | YES | YES | NO | NO | NO | YES | NO | NO | NO | NO | Specialized MEMO/APR for arbitrary configurations | No statistics-semantic invalidation | §§2--4 |
| Liu/Ives/Loo | PARTIAL | YES | PARTIAL | PARTIAL | YES | YES | YES | NO | YES | YES | YES | NO | NO | YES | NO | Exact retained-state update and reintroduced alternatives | Estimate/cost changes are inputs, not produced by statistics semantics | §§2--5 |
| Self-adjusting computation | YES | YES | NO | NO | PARTIAL | YES | NO | NO | YES | YES | YES | NO | NO | YES | NO | General result-plus-dependency change propagation | No physical design, CE, or statistics candidate closure | Paper §§1--3; CMU-CS-05-129 description |

## 4. Current-text audit

| Location | Current claim | Classification | Reason |
|---|---|---|---|
| Abstract | “workload-specialized, design-parametric representation ... exposes both ... oracles” | ACCURATE but attribution-sensitive | A bounded system description, not an explicit priority claim; no abstract change needed if Related Work and Introduction subtraction are explicit. |
| Introduction prior-work paragraph | History of automatic management and reusable optimizer response | UNDER-CREDITS PRIOR ART | Omits statistics dependencies and index-interaction precedent. |
| Introduction “key idea”/dual interfaces | Specializes estimator semantics; two interfaces | ACCURATE | Describes implementation; should be bounded by one sentence conceding generic specialization/change propagation. |
| Contribution 1 | Connects maintenance design to workload-specialized design-parametric CE | POTENTIALLY MISLEADING | “Problem and representation” may be read broadly; minimally specify the represented state transitions, not generic parametrization. |
| Contribution 3 | Objective/dependency oracle and exact audited moves | ACCURATE | Domain-specific wording and bounded result; preserve architecture and RQ3. |
| Section 8.2 | “value is representational”; current-output divergence | TOO BROAD | Could imply dual-interface/counterfactual principle is novel generally. Add explicit scope sentence. |
| Section 8.6 | Calls workload specialization/design parametrization/dual oracles “broader abstractions” | POTENTIALLY MISLEADING | Should distinguish established abstractions from CE-Replay's specialization. |
| Section 9.1 first paragraph | AutoStats described as selection/reduction | UNDER-CREDITS PRIOR ART | Must acknowledge dependencies and MNSA/D latent interaction. |
| Section 9.1 monotonicity paragraph | Contrasts MNSA cost-monotonicity and CE q-error | POTENTIALLY MISLEADING | Omits the paper's own caveat; could imply non-monotonicity is absent from prior work. |
| Section 9.1 focus paragraph | Focuses on interactions among proposed definitions | TOO BROAD | Interaction in general is prior art; must state estimator-semantic mechanism. |
| Section 9.2 first paragraph | What-if/constrained design established | ALREADY SUFFICIENT | Add Index Interactions and contextual interaction explicitly. |
| Section 9.2 INUM/C-PQO paragraphs | Strongly credits parametric representations | ALREADY SUFFICIENT, minor sharpening | Already avoids strawman; add latent-alternative credit and tighten distinction. |
| Section 9.3 | Says dependency-aware recomputation is not new | ALREADY SUFFICIENT, minor sharpening | Explicitly concede exact change propagation/inactive alternatives and state domain remainder. |
| Section 9.4 | Native mechanisms not claimed | ALREADY SUFFICIENT | No change needed. |
| Section 9.5 | Bounded positioning/no priority | ACCURATE, minor sharpening | Add explicit subtraction of interactions/parametric reuse/incremental recomputation. |
| Conclusion | Describes system/results without “first” | ACCURATE | No change expected unless final synchronization exposes ambiguity. |

## 5. Conceptual subtraction list

CE-Replay does **not** claim as novel: automatic statistics selection; statistics interactions in general; contextual or non-monotone physical-design benefit in general; workload/query specialization; partial evaluation; configuration-parametric representation; hypothetical physical-design evaluation; reusable optimizer representations; latent alternatives in configuration space; dependency tracking; exact incremental recomputation; generic change propagation; generic counterfactual/hidden-state principles; native MCV semantics; native FD semantics; PostgreSQL extended-statistics semantics; local search; or budget-constrained physical design.

## 6. Remaining novelty statement

The narrowest supported statement is:

> CE-Replay specializes a bounded native estimator fragment to a supplied workload while preserving statistics-dependent estimator control/state as executable design parameters. The representation is used both to evaluate hypothetical CE objectives and to identify the statistics-semantic state that must be reconsidered under design moves, including precedence, clause consumption, and cross-mechanism reachability.

Classification: **systems representation specialization / nontrivial domain specialization**, not a distinct general representation principle.

## 7. Citations

Add exactly one citation:

- `schnaitter2009interactions`: Karl Schnaitter, Neoklis Polyzotis, and Lise Getoor, “Index Interactions in Physical Design Tuning: Modeling, Analysis, and Applications,” *Proceedings of the VLDB Endowment* 2(1):1234--1245, 2009, DOI `10.14778/1687627.1687766`.

Modify the description, not metadata, of existing citations `chaudhuri2001statistics`, `papadomanolakis2007inum`, `bruno2008cpqo`, and `liu2016incremental`. Add no generic PL citation because it would lengthen the paper without improving the closest-database comparison.

Bibliography count: 15 before, 16 expected after. Removed entries: 0. Metadata corrections: 0.

## 8. Exact patch plan

### Change 1 — Introduction prior-art boundary

**CURRENT**

> Automatic statistics management and workload-driven selection have a substantial history, as do what-if physical-design interfaces and reusable representations of optimizer response [@chaudhuri2001statistics; @chaudhuri1998whatif; @papadomanolakis2007inum; @bruno2008cpqo]. Combinatorial statistics design nevertheless requires evaluating many hypothetical states whose effects are generated inside the estimator. Efficient move evaluation in this setting benefits from tracking how a statistics-design change can alter estimator applicability, clause consumption, numerical contribution, and downstream mechanism state. The challenge addressed here is therefore not hypothetical evaluation in general, but retaining the relevant native estimator computation and its design-relevant dependencies across hypothetical statistics states.

**PROBLEM**

It does not credit contextual/latent statistics and index interactions, and does not explicitly subtract generic dependency-aware recomputation.

**PROPOSED**

> Automatic statistics management already considers dependencies among statistics, while physical-design research establishes contextual interactions among design objects; what-if interfaces and reusable configuration-parametric optimizer representations are also established [@chaudhuri2001statistics; @schnaitter2009interactions; @chaudhuri1998whatif; @papadomanolakis2007inum; @bruno2008cpqo]. Dependency-aware exact recomputation is likewise a general and database precedent [@liu2016incremental]. The challenge addressed here is narrower: preserve the native estimator state transitions through which a statistics design changes applicability, clause consumption, numerical contribution, and downstream mechanism reachability, then use that state both for hypothetical CE and statistics-semantic move invalidation.

**WHY THIS IS REQUIRED BY PRIMARY SOURCE**

AutoStats §4/MNSA-D and Index Interactions §§1--2 establish dependencies/contextual interaction; INUM/C-PQO establish parametric reuse; Liu establishes exact incremental retained-state maintenance.

**CLAIM STRENGTH BEFORE:** Could be read as making the internal dependency combination broadly novel.

**CLAIM STRENGTH AFTER:** Explicitly claims only the estimator-semantic specialization and its dual use.

### Change 2 — Contribution 1 narrowing

**CURRENT**

> **Problem and representation.** We connect maintenance-constrained statistics design with workload-specialized, design-parametric execution of the supported native CE semantics. The formulation separates selected definitions, DBMS-specific physical realization, frozen payloads, and fresh realization.

**PROBLEM**

The first sentence centers established specialization/parametrization rather than the bounded semantic state retained.

**PROPOSED**

> **Problem and representation.** We formulate maintenance-constrained statistics design over the supported native CE state transitions, preserving applicability, consumption, precedence, and cross-mechanism reachability as executable design-dependent semantics. The formulation separates selected definitions, DBMS-specific physical realization, frozen payloads, and fresh realization.

**WHY THIS IS REQUIRED BY PRIMARY SOURCE**

INUM/C-PQO establish workload-specialized configuration-parametric representation; the proposed wording names the verified remaining computational distinction.

**CLAIM STRENGTH BEFORE:** Broad representation combination.

**CLAIM STRENGTH AFTER:** Bounded estimator-semantic representation.

### Change 3 — Discussion scope

**CURRENT**

> CE-Replay's value is representational rather than merely computational. Its executable state transitions provide both the hypothetical objective and the information needed to invalidate that objective safely after a move.

**PROBLEM**

Without a concession, this may imply that response-plus-dependency representation is novel in general.

**PROPOSED**

> CE-Replay's value is representational rather than merely computational. Configuration-parametric representation and dependency-aware recomputation are established principles; CE-Replay specializes them to estimator state transitions that provide both the hypothetical objective and the statistics-semantic information needed to invalidate that objective safely after a move.

**WHY THIS IS REQUIRED BY PRIMARY SOURCE**

C-PQO and Liu/self-adjusting computation directly establish the subtracted principles.

**CLAIM STRENGTH BEFORE:** Potentially general dual-interface claim.

**CLAIM STRENGTH AFTER:** Explicit specialization claim.

### Change 4 — Discussion abstraction sentence

**CURRENT**

> The broader abstractions are workload specialization, design-parametric executable semantics, dual oracles, realization boundaries, and maintenance-constrained design.

**PROBLEM**

It groups established primitives with the manuscript's remaining contribution without attribution.

**PROPOSED**

> The reusable contribution is the bounded estimator-semantic specialization and its validated interfaces; workload specialization, configuration parametrization, dependency-aware recomputation, and maintenance-constrained design are established foundations.

**WHY THIS IS REQUIRED BY PRIMARY SOURCE**

INUM/C-PQO, Liu, and constrained-design work establish the listed foundations.

**CLAIM STRENGTH BEFORE:** Broad abstraction package.

**CLAIM STRENGTH AFTER:** Domain-specific reusable mechanism.

### Change 5 — Automatic Statistics Management paragraphs

**CURRENT**

> Automatic statistics management predates CE-Replay. Chaudhuri and Narasayya identify optimizer-relevant statistics and reduce the set that must be created for a workload [@chaudhuri2001statistics]. CORDS discovers correlations and soft functional dependencies and recommends column groups for joint statistics [@ilyas2004cords]. JITS selects and collects query-specific statistics during compilation using sensitivity and previously collected information [@elhelw2007jits]. These works establish workload-aware statistics selection, correlation discovery, and selective acquisition as existing problem classes.
>
> Within their MNSA formulation for SPJ queries, Chaudhuri and Narasayya use a cost-monotonicity assumption over predicate selectivity variables to bound optimizer-cost sensitivity [@chaudhuri2001statistics]. The non-monotonicity evaluated here instead concerns PostgreSQL q-error under inclusion of physically realized extended-statistics objects. The DBMS, objective, varied state, and estimator semantics differ, so this is a contrast between problem structures rather than a contradiction of the earlier assumption.
>
> CE-Replay does not claim candidate discovery or acquisition as a contribution. It assumes candidate definitions and a frozen payload repository, then evaluates complete candidate subsets through the supported native consumption semantics. Its focus is the interaction among already proposed statistics definitions: which objects become applicable, which win, which clauses they consume, and which downstream mechanisms remain reachable.

**PROBLEM**

The text omits dependencies, MNSA/D's latent interaction, and the monotonicity caveat; “focus is interaction” is too broad.

**PROPOSED**

> Automatic statistics management predates CE-Replay. Chaudhuri and Narasayya select optimizer-relevant statistics, explicitly note dependencies among statistics, and show in MNSA/D that a statistic irrelevant under one set can matter after another statistic is added [@chaudhuri2001statistics]. CORDS discovers correlations and soft functional dependencies for joint statistics, while JITS selects and collects query-specific statistics using sensitivity and prior information [@ilyas2004cords; @elhelw2007jits]. Thus workload-aware selection, contextual statistics relevance, correlation discovery, and selective acquisition are established.
>
> Their MNSA analysis uses a cost-monotonicity assumption over predicate selectivities, while also acknowledging pathological violations in which adding a histogram can worsen the chosen plan [@chaudhuri2001statistics]. Our non-monotonicity evidence concerns PostgreSQL q-error under physically realized extended-statistics objects; it is systematic evidence for semantics-aware selection in this mechanism/setting, not a claim that harmful additions are historically new.
>
> CE-Replay does not contribute candidate discovery, acquisition, or statistics interaction in general. Given definitions and frozen payloads, it represents the native estimator transitions producing those interactions—applicability, precedence, clause consumption, numerical updates, and downstream reachability—and uses them for hypothetical CE and move invalidation.

**WHY THIS IS REQUIRED BY PRIMARY SOURCE**

AutoStats Sections 3.3--5 explicitly support every added acknowledgment.

**CLAIM STRENGTH BEFORE:** Under-credits prior interaction/non-monotonicity work.

**CLAIM STRENGTH AFTER:** Credits known phenomena and claims only the semantic representation/evaluation mechanism.

### Change 6 — Index Interactions and INUM/C-PQO

**CURRENT**

> Hypothetical evaluation and constrained design are established foundations. AutoAdmin's What-If utility evaluates hypothetical indexes without materializing every configuration [@chaudhuri1998whatif]. Constrained physical-design tuning formulates workload optimization under storage and richer design constraints [@bruno2008constrained]. CE-Replay therefore does not claim novelty for resource-constrained physical design or hypothetical evaluation in isolation.
>
> INUM caches and reuses optimizer-derived plan information to estimate query cost across index configurations with far fewer optimizer calls [@papadomanolakis2007inum]. C-PQO constructs a compact representation of optimizer behavior that can produce plans for arbitrary physical configurations after a specialized optimizer invocation [@bruno2008cpqo]. These systems are close conceptual neighbors: they show that avoiding repeated optimizer calls and constructing configuration-parametric representations are established ideas.

**PROBLEM**

It omits the closest contextual-interaction comparator and can credit INUM/C-PQO more precisely for retained alternatives.

**PROPOSED**

> Hypothetical evaluation, constrained design, and contextual design-object interaction are established foundations. AutoAdmin evaluates hypothetical indexes without materializing every configuration; constrained tuning optimizes under storage and richer constraints; and Index Interactions formalizes configuration-dependent positive and negative index interactions, including objects that become useful together [@chaudhuri1998whatif; @bruno2008constrained; @schnaitter2009interactions]. CE-Replay claims none of these general principles.
>
> INUM reuses optimizer-derived template plans and configuration-dependent access costs across index designs [@papadomanolakis2007inum]. C-PQO specializes optimizer computation into a compact MEMO/APR representation, retaining alternatives needed to produce plans for arbitrary configurations [@bruno2008cpqo]. They establish reusable configuration-parametric optimizer representations and latent configuration alternatives, not just final-plan caching.

**WHY THIS IS REQUIRED BY PRIMARY SOURCE**

Index Interactions Definitions 2.1--2.3, INUM §§2--4, and C-PQO §§2--4 support the stronger acknowledgments.

**CLAIM STRENGTH BEFORE:** Correct but incomplete prior-art credit.

**CLAIM STRENGTH AFTER:** Full credit; novelty rests on computational consequence at estimator layer.

### Change 7 — Incremental optimization

**CURRENT**

> Dependency-aware incremental recomputation is not new in general. Incremental query re-optimization maintains search and pruning state as cardinality or cost information changes [@liu2016incremental]. CE-Replay operates at a different layer: a statistics-design move propagates through estimator semantics and changes CE and workload loss before downstream optimizer search. We therefore use the narrower term **semantic dependency oracle** rather than claim generic incremental optimization as a contribution.

**PROBLEM**

It should concede exactness, shared retained state, and reactivation of pruned alternatives rather than rely on “different layer.”

**PROPOSED**

> Dependency tracking and exact incremental recomputation are established principles. Incremental query re-optimization retains optimizer search/pruning state, propagates changed cardinality or cost information, and can rederive pruned alternatives while matching full reoptimization [@liu2016incremental]. CE-Replay's narrower contribution is to identify and expose the estimator-semantic state affected by a statistics-design move—including precedence, consumption, and downstream reachability—before optimizer search. We therefore use **semantic dependency oracle** as a domain-specific interface, not a claim to generic incremental computation.

**WHY THIS IS REQUIRED BY PRIMARY SOURCE**

Liu Sections 3--5 establish exact incremental maintenance and pruned-alternative reintroduction.

**CLAIM STRENGTH BEFORE:** Correct concession but potentially understates Liu.

**CLAIM STRENGTH AFTER:** Full concession plus precise domain remainder.

### Change 8 — Final Related Work positioning

**CURRENT**

> Prior work addresses statistics discovery and management, hypothetical and configuration-parametric physical-design evaluation, incremental optimizer maintenance, and alternative cardinality estimators. CE-Replay focuses on the interface between statistics physical design and the supported statistics-sensitive native CE computation. Keeping its internal state transitions executable under hypothetical statistics states is what lets one representation provide both workload CE evaluation and safe design-move invalidation.

**PROBLEM**

It should explicitly subtract statistics interactions and generic response-plus-dependency principles.

**PROPOSED**

> Prior work establishes statistics dependencies and contextual physical-design interactions, hypothetical and configuration-parametric optimizer evaluation, and dependency-aware exact recomputation. CE-Replay's bounded systems specialization is to preserve the supported native statistics-estimator state transitions as executable design parameters, using that state for both workload CE evaluation and statistics-semantic, counterfactual-safe move invalidation.

**WHY THIS IS REQUIRED BY PRIMARY SOURCE**

It is the direct synthesis of the six verified sources.

**CLAIM STRENGTH BEFORE:** Broad combination could obscure established components.

**CLAIM STRENGTH AFTER:** Explicitly bounded systems specialization.

## 9. Budget and risk

- Expected manuscript net word delta: approximately +15 to +45 words after replacing/compressing paragraphs, not additive expansion.
- Expected page effect: neutral or less than 0.1 page; References gains one entry and may increase page-12 occupancy. A clean build and visual inspection are mandatory.
- Expected bibliography delta: +1 entry, 0 removals, 0 metadata corrections.
- Files expected to change in Phase B: authoritative Markdown; generated `main.tex`; two bibliography copies; rebuilt PDFs and build-derived audit outputs required by this task; two new correction audit outputs. Existing experiments/results remain untouched.
- Principal risk: the added reference could produce page overflow or a bad column break. Mitigation is prose-neutral replacement, never typography/template changes.
- Scientific risk: wording could overstate AutoStats or understate the CE-Replay remainder. Mitigation is exact source-grounded phrasing and the six novelty regression tests.
- Synchronization risk: manual LaTeX drift. Mitigation is regenerate with the repository converter and compare section/RQ/contribution/citation structure.

PHASE A PASS — MINIMAL NOVELTY CORRECTION JUSTIFIED
