# Appendix Blueprint v0

The appendix is planned but not drafted. Main-text claims remain understandable without experiment chronology.

## Appendix A — PostgreSQL source and instrumentation mapping

- Native source paths/functions and instrumentation boundary.
- Raw/pre-clamp estimator output versus rounded `EXPLAIN` rows.
- Supports Sections 4, 5.2, and RQ1.

## Appendix B — Complete semantic fixtures

- MCV applicability, GreedyCover, numerical combination, and consumption cases.
- FD selection/application scenarios.
- ScalarArray 29-case fixture matrix and 128 scalar regressions.
- Supports Sections 4.2–4.4 and Table T2.

## Appendix C — Physical precedence witnesses

- Creation/OID-order experiments and tied-winner traces.
- Scope boundary for PostgreSQL-specific realization.
- Supports Sections 3 and 4.2.

## Appendix D — Search correctness details

- Five-candidate Census exhaustive design space.
- Four restricted DMV exhaustive audits.
- Complete terminal ADD/DROP/SWAP checks.
- Supports Section 6.1 and Table T3.

## Appendix E — Rejected semantic shortcuts

- First-applicable proxy failure.
- Restart-safe state counterexample.
- Commutativity without outer-space reduction.
- Semantic factorization and giant-component evidence.
- Locality-only swap restriction under a global budget.
- Supports Sections 5.3, 6.2, and 9.3.

## Appendix F — Incremental-evaluation detail

- Move-category distributions and invalidation classes.
- Control, mechanism, query replay, and numerical aggregation counts.
- Complete accepted trajectories.
- Supports Table T4.

## Appendix G — Maintenance-model diagnostics

- Census and DMV configurations, residuals, fit quality, and deployment prediction errors.
- Byte-budget versus maintenance-budget Census comparison.
- Supports Figure F3, Table T3, and Section 9.4.

## Appendix H — Repeated Census ANALYZE

- Thirty realization summaries and complete loss distribution.
- MCV/FD control-path stability detail.
- Supports Table T5 and Section 9.5 without implying ranking stability.

## Appendix I — DMV provenance audit

- Search for frozen per-query artifacts and unrecoverable fields.
- Supported fresh-deployment claims versus unavailable paired drift claims.
- Supports Table T5 and Section 9.7.

## Appendix J — Reproducibility map

- Script/result mapping for F1–F4 and T1–T5.
- Environment and frozen-tag instructions.
- Complete claim and evidence matrices.
- Supports the Artifact and Reproducibility Statement.

Material classification: all items above are APPENDIX. Superseded IR versions, experiment chronology, and exploratory unseen-workload generalization remain REMOVE from the paper unless specifically requested by reviewers.
