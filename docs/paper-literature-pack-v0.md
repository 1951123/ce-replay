# Literature Pack v0

## Scope and conclusion

This pass verified 15 references and integrated them into `paper-full-draft-v1-literature.md`. It found substantial prior work in statistics management and acquisition, multivariate discovery, hypothetical/configuration-parametric design evaluation, constrained physical design, incremental optimizer maintenance, and alternative CE. No verified source examined in this pass directly covered the complete CE-Replay combination, but this is a search-based positioning conclusion, not a priority claim.

Final positive positioning:

> Prior work addresses statistics discovery and management, hypothetical and configuration-parametric physical-design evaluation, incremental optimizer maintenance, and alternative cardinality estimators. CE-Replay focuses on the interface between statistics physical design and the supported statistics-sensitive native CE computation. It makes that computation executable under hypothetical statistics states and uses the same representation both to evaluate workload CE loss and to expose statistics-semantic dependencies for design moves.

## Verification inventory

| Key | Tier | Verified authority | Supported use |
|---|---|---|---|
| `chaudhuri2001statistics` | MUST | IEEE DOI 10.1109/69.908978; Microsoft Research paper | Automatic workload-aware statistics management and smaller relevant subsets |
| `ilyas2004cords` | SHOULD | ACM DOI 10.1145/1007568.1007641; IBM Research | Correlation/soft-FD discovery and column-group recommendation |
| `elhelw2007jits` | MUST | IEEE DOI 10.1109/ICDE.2007.367897; author/IBM publication copy | Query-specific acquisition, sensitivity, materialization, maintenance |
| `chaudhuri1998whatif` | MUST | ACM DOI 10.1145/276304.276337; SIGMOD/MSR publication pages | Hypothetical index evaluation |
| `papadomanolakis2007inum` | MUST | Official VLDB proceedings PDF | Optimizer-information reuse across index configurations |
| `bruno2008cpqo` | MUST | ACM DOI 10.1145/1376616.1376710; Microsoft Research | Compact configuration-parametric optimizer representation |
| `liu2016incremental` | MUST | ACM DOI 10.1145/2882903.2915212; PMC full text | Incremental optimizer/search-state recomputation |
| `bruno2008constrained` | MUST | PVLDB DOI 10.14778/1453856.1453863 | Resource-constrained physical-design formulation |
| `zhu2004piggyback` | SHOULD | Oxford Academic DOI 10.1093/comjnl/47.2.221 | On-the-fly/piggyback statistics collection |
| `pfeil2026redshift` | OPTIONAL | Amazon Science official publication page | Modern incremental statistics refresh; no CE-Replay coefficient support |
| `kipf2019learned` | SHOULD | Official CIDR proceedings PDF/program | Representative query-driven learned CE |
| `hilprecht2020deepdb` | MUST | Official PVLDB paper, DOI 10.14778/3384345.3384349 | Representative data-driven CE; prevents workload-training caricature |
| `wu2023factorjoin` | SHOULD | ACM DOI 10.1145/3588721 | Representative modern learned/statistical join CE |
| `postgresql16docs` | MUST | Official PostgreSQL 16 documentation | Public extended-statistics behavior and MCV payload context |
| `postgresql16source` | MUST | PostgreSQL `REL_16_14` source tree | Exact supported MCV/FD control and numerical authority |

Tier totals: 10 MUST, 4 SHOULD, and 1 OPTIONAL.

The Redshift entry intentionally omits DOI, pages, volume, and issue because the authoritative Amazon Science page used here confirms title, authors, year, and VLDB 2026 status but does not expose those fields. No metadata was inferred from an unofficial index.

## Reviewer-adversarial literature check

1. **Why is this not merely another automatic statistics advisor?** Earlier work selects optimizer-relevant statistics and discovers candidates. CE-Replay assumes candidates/payloads and represents the native semantic computation that evaluates interacting subsets. It can serve an advisor but is not the complete advisor pipeline.
2. **Why is this not INUM for statistics?** INUM reuses optimizer-derived plan information to estimate plan cost across index configurations. CE-Replay executes statistics-sensitive CE control and numerical state and exposes dependencies inside that computation. Both reuse specialized native information; the represented layer differs.
3. **Why is this not C-PQO applied to another physical object?** C-PQO represents optimizer behavior across configurations and produces plans. CE-Replay does not parameterize full plan optimization; it keeps supported estimator selection, consumption, and mechanism state executable and produces CE/objective dependencies. The conceptual proximity is explicit, and no categorical disjointness is claimed.
4. **Why is the dependency oracle not covered by incremental re-optimization?** Incremental re-optimization propagates changed cost/cardinality information through optimizer search/pruning state. CE-Replay propagates a statistics-design change through estimator-semantic state before optimizer search. Generic incremental recomputation is prior art; the paper's claim is statistics-semantic dependency exposure.
5. **Why is this not a new cardinality estimator?** CE-Replay neither learns nor replaces the estimator. It executes a validated fragment of PostgreSQL's existing estimator under hypothetical statistics states.
6. **What PostgreSQL semantics are native?** MCV/FD applicability, GreedyCover and consumption, payload numerical rules, MCV-before-FD composition, and relevant ordering behavior are native. PostgreSQL 16.14 source is the authority.
7. **What is contributed on top?** Workload specialization; design-parametric executable encoding; objective and statistics-semantic dependency interfaces; native validation; and use in maintenance-constrained interacting statistics design.
8. **Does prior work consider statistics maintenance cost?** Yes. JITS, piggyback collection, and incremental Redshift statistics make collection/refresh an established concern.
9. **Why is the maintenance model useful?** It instantiates the resource constraint for the measured PostgreSQL environments and aligns selection with recurring `ANALYZE` demand. Its contribution is not discovering maintenance cost or universal coefficients.
10. **Does candidate-payload acquisition make the approach impractical?** It is a serious unsolved systems boundary. The paper neither hides nor resolves it; selective/incremental acquisition methods are complementary integration directions.
11. **Which claims are PostgreSQL-specific?** The validated semantic rules, ordering, payload schema, mechanism sequence, and measured `ANALYZE` coefficients.
12. **Which ideas may transfer architecturally?** Separating definitions/payloads/realizations, retaining design-dependent estimator semantics, exposing objective/dependency interfaces, and separating frozen optimization from fresh validation. Cross-DBMS validity is not demonstrated.

## Stop-condition assessment

- No verified work in this pass directly covered the full CE-Replay combination.
- No frozen contribution required substantive redefinition; contributions 1 and 3 were narrowed to bind them to native CE execution and statistics-semantic dependencies.
- No verified literature contradicted a frozen empirical claim.
- All central MUST-CITE metadata was verified.
- No frozen evidence was modified.
