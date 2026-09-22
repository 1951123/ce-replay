# Manuscript-Polish Adversarial Review

1. **Can the core problem be stated after the first three Introduction paragraphs?** Yes. They identify extended-statistics physical design, semantic harm from interactions, and recurring maintenance capacity.
2. **Are semantic and resource necessity distinct?** Yes. The second and third paragraphs give separate causal arguments, and Section 9.1 preserves the distinction.
3. **Is it obvious why independent scores are insufficient?** Yes. Sections 1, 2.3, and 4 connect overlapping selection, clause consumption, and directed MCV-to-FD state to contextual candidate effects.
4. **Is CE-Replay distinguishable from PostgreSQL itself?** Yes. Section 5 contrasts one concrete native catalog/statistics execution with a bounded design-parametric representation across hypothetical states.
5. **Is it distinguishable from INUM/C-PQO without weakening them?** Yes. Section 10.2 distinguishes positively documented computation layers: optimizer plan/cost behavior over physical configurations versus supported statistics-sensitive estimator state transitions.
6. **Is the dependency oracle distinguishable from incremental re-optimization?** Yes. Section 10.3 places it upstream inside estimator semantics and limits the claim to statistics-design moves.
7. **Is the optimizer presented as a consumer?** Yes. Section 6 now opens by calling it a replaceable consumer and keeps the guarantees neighborhood-local.
8. **Can each RQ answer be found quickly?** Yes. Every subsection starts with its question and ends with a bold answer; question-first artifact transitions were strengthened.
9. **Are negative results visible?** Yes. Harmful additions, giant-component failure, global budget exchange, mixed-evaluator slowdown, environment-specific costs, fresh drift, DMV provenance loss and zero-truth distortion, external acquisition, and local-only guarantees remain in the main text.
10. **Is fresh-payload drift distinct from semantic replay error?** Yes. Figure F1, Section 5.4, Table T5, and Section 9.5 maintain the distinction.
11. **Is candidate-payload acquisition outside the boundary?** Yes. Sections 3, 6.3, 9.5, 9.7, 10.5, and 11 state or rely on that boundary.
12. **Does any paragraph still read like a research log?** Some detailed result paragraphs in Sections 7 and 8 retain artifact-like density. They remain because the next appendix pass, not this pass, should decide what moves after typesetting.
13. **Is any conceptual explanation purposelessly repeated?** No material instance remains. Repetition persists where local validity or interpretation requires it, especially realization boundaries and local-optimum scope.
14. **Is any claim stronger than v2?** No. Claim-strength, number, and citation audits pass with zero regressions.
15. **Single weakest remaining presentation issue.** Section 8 still carries high numerical and caption density. The argument is navigable, but final readability depends on rendering the four figures and five tables and migrating secondary fixtures, distributions, and traces after the page budget is known.

## Verdict

The manuscript now reads as an argument rather than experiment chronology: semantic and resource motivations lead to an executable representation, its two interfaces, a modest optimizer consumer, four question-driven evaluations, and bounded interpretation. The scientific density was deliberately not reduced by dropping negative or qualifying evidence.
