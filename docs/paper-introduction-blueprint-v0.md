# Introduction Blueprint v0

This is a paragraph plan, not final Introduction prose. The target Introduction has nine paragraphs followed by exactly four contribution bullets.

## Paragraph plan

1. **Problem.** Explain that cost-based optimizers depend on cardinality estimates, that extended statistics expose multivariate information when ordinary assumptions are inadequate, and that choosing which statistics to maintain is itself physical design. Promise only a supplied target workload and CE-loss objective. Discharged by Sections 2–3 and evaluated in Section 8.2.

2. **Semantic necessity for selection.** Explain that overlapping statistics are chosen and consumed contextually, disjoint statistics can compose, and upstream mechanisms can suppress downstream mechanisms. State that more statistics need not improve target-workload CE loss, with one qualitative cross-workload teaser rather than a number dump. Discharged by Section 4 and Figure F2.

3. **Resource necessity.** Explain that deployed statistics incur recurring `ANALYZE` collection/refresh work. State explicitly that maintenance demand and semantic utility are independent dimensions. Discharged by Sections 3 and 7 and Figure F3.

4. **Hypothetical-evaluation challenge.** Explain that combinatorial selection requires repeated evaluation of statistics sets; independent candidate scores cannot represent stateful interaction. Native calls can evaluate configurations, but repeated full native evaluation does not itself expose the dependencies needed for exact incremental recomputation. Avoid caricaturing prior what-if systems. Discharged by Sections 4–6.

5. **Key idea.** Introduce CE-Replay as workload-specialized, design-parametric executable semantics. Freeze workload-fixed context and payload schema while leaving eligibility, selection, consumption, composition, and numerical decisions executable. A hypothetical physical state yields a native-style estimate, and ground truth is used only afterward to compute loss. Discharged by Sections 3–5.

6. **Dual interface.** Present CE-Replay as an objective oracle and a dependency oracle. The objective oracle eliminates the need for a separate learned design-to-q-error response model inside the supported fragment; the dependency oracle identifies what a move can affect and supports exact incremental evaluation. Discharged by Sections 5–6 and evaluated in Sections 8.1–8.3.

7. **PostgreSQL instantiation.** State the explicit boundary: PostgreSQL 16.14 conjunctive base-relation restrictions, supported scalar predicates, constant `IN`/`= ANY` MCV semantics, FD, and directed MCV-to-FD composition. Say source-informed and validated, not full PostgreSQL CE or automatic source compilation. Discharged by Sections 4–5 and Table T2.

8. **Evidence preview.** Summarize four evidence classes: floating-point-level same-realization native fidelity; non-monotone maintenance-constrained design in sparse Census and dense IN-heavy DMV; exact dependency-aware evaluation with a topology- and implementation-dependent runtime opportunity; and mixed physical deployment followed by fresh native validation. If numbers are used, use only the audited 468/468 and 1,965/1,965 fresh comparisons. Discharged by Section 8 and Tables T2–T5.

9. **Contributions transition.** State that the paper contributes a bounded representation and physical-design method rather than a new estimator, complete DBMS, globally optimal workload-scale solver, or runtime optimizer. Follow with exactly four bullets.

## Four contribution statements

1. **Problem and representation.** We formulate extended-statistics physical design for a supplied target workload under recurring maintenance cost and introduce workload-specialized, design-parametric executable CE semantics. Sections 3 and 5 define the method; Section 8.2 supplies cross-workload non-monotonicity and maintenance evidence. Scope: the supported PostgreSQL 16.14 base-restriction setting.

2. **PostgreSQL CE-Replay.** We implement and validate CE-Replay for interacting PostgreSQL 16.14 base-restriction MCV and FD semantics, including bounded constant ScalarArray predicates and directed MCV-to-FD composition. Sections 4–5 describe it; Sections 8.1 and 8.4 validate it. Scope: the explicit conjunctive fragment, not arbitrary PostgreSQL CE.

3. **Semantics-guided optimization.** We use CE-Replay as both an exact-within-scope objective oracle and a semantic dependency oracle for deterministic maintenance-constrained ADD/DROP/SWAP search and exact incremental move evaluation. Section 6 gives the method; Sections 8.2–8.3 provide exhaustive/restricted audits and trajectory evidence. Scope: workload-scale neighborhood local optimality, not global optimality or universal speedup.

4. **Cross-workload physical validation.** We demonstrate contextual non-monotonicity, maintenance-aware mixed designs, dependency-aware evaluation, and fresh physical deployment on sparse Census and dense IN-heavy DMV. Sections 7–8 provide evidence. Scope: two workloads, one PostgreSQL version, and no execution-time improvement claim.

## Reader-objection stress test

1. **Why not create every statistic?** Native selection and consumption make marginal utility contextual; both workloads contain harmful additions and beneficial removals.
2. **If storage is cheap, why optimize?** Semantic non-monotonicity remains even without a binding maintenance budget.
3. **Why not rank independently?** Overlapping MCVs compete, consumed clauses change later eligibility, and MCV state controls FD reachability.
4. **Why not call PostgreSQL for every design?** Native calls remain the validation oracle, while CE-Replay exposes reusable workload context and dependencies needed for incremental combinatorial evaluation.
5. **Is this just reimplementing PostgreSQL CE?** It is a bounded, workload-specialized representation built to keep design-dependent semantics executable and expose optimization interfaces.
6. **Why specialize to a workload?** Query structure and fixed context can be compiled out while candidate-dependent decisions remain live, reducing repeated work.
7. **Why is this not learned CE?** It follows native estimator semantics and uses truth only to score estimates; it learns neither cardinality nor a design-to-error map.
8. **Why does the dependency oracle matter?** It safely limits recomputation while preserving audited move values and trajectories.
9. **If the graph is connected, where is locality?** A globally connected graph can still have low candidate degree, so individual moves affect small neighborhoods.
10. **Why does commutativity not solve search?** Local transition commutativity does not eliminate canonical PostgreSQL precedence or global subset and budget choices.
11. **Does incremental replay always speed optimization?** No; Census mixed replay reduces control work but numerical and loop overhead make that implementation slower.
12. **Why maintenance rather than bytes?** Recurring `ANALYZE` work is the operational deployed resource; bytes were only an early controlled proxy.
13. **Are coefficients portable?** No; the model form is reusable, while coefficients are environment-specific calibrations.
14. **Why leave budget unused?** Capacity need not be filled when all feasible additions are non-improving under contextual semantics.
15. **What if `ANALYZE` changes payloads?** Report same-realization semantic fidelity separately from frozen-to-fresh payload drift; robust selection remains future work.
16. **Does repeated `ANALYZE` invalidate optimization?** It exposes conditional-realization uncertainty, but same-realization replay remains faithful; ranking stability was not tested.
17. **How expensive is payload acquisition?** It can be substantial and is an offline systems boundary not solved here.
18. **Is the final design globally optimal?** No; full designs are locally optimal under the audited ADD/DROP/SWAP neighborhood.
19. **Why only MCV and FD?** They cover two distinct, interacting base-restriction mechanisms and establish compositional feasibility within a bounded study.
20. **Why only base restrictions?** They isolate statistics-sensitive CE semantics without planner/path-search confounding; joins remain future work.
21. **Does ScalarArray imply arbitrary predicate support?** No; support is bounded to validated constant `IN`/`= ANY` MCV semantics.
22. **Why only PostgreSQL?** PostgreSQL provides the implemented and instrumented case; cross-DBMS validation is future work.
23. **Does lower q-error imply faster queries?** Not necessarily; runtime and plan quality are not optimized or causally evaluated.
24. **What does DMV add?** Dense high-reuse incidence, extensive `IN` predicates, independent maintenance calibration, and a second fresh deployment.
25. **Does DMV's provenance gap invalidate deployment?** No; it limits paired frozen-to-fresh drift, not fresh same-realization fidelity or physical composition.
26. **Why are two workloads enough?** They support complementary replication, not universal representativeness.
27. **Does the paper solve unseen-workload generalization?** No; the target workload is supplied.
28. **What is architectural?** Design-parametric replay, dual oracles, dependency distinctions, realization boundaries, and maintenance-constrained design; PostgreSQL rules are the instantiation.
29. **Could another optimizer use CE-Replay?** Yes; the oracle interfaces do not depend on the current deterministic local search.
30. **Most important limitation?** The validated semantic boundary is narrow and manually engineered; broader mechanisms require additional extraction and validation.

## Claims requiring later literature support

- `RELATED-WORK CITATION REQUIRED`: Physical-design systems commonly use native optimizer or what-if interfaces.
- `RELATED-WORK CITATION REQUIRED`: INUM-style approaches cache or specialize optimizer responses.
- `RELATED-WORK CITATION REQUIRED`: Learned CE methods model cardinalities or estimator behavior rather than replaying native statistics consumption.
- `RELATED-WORK CITATION REQUIRED`: Prior extended-statistics configuration methods and their interaction/resource assumptions.
- `RELATED-WORK CITATION REQUIRED`: Statistics-maintenance work on collection and refresh tradeoffs.
