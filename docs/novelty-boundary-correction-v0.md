# Novelty Boundary Correction v0

## 1. Provenance result

**PROVENANCE PASS — INTERVENING COMMITS UNDERSTOOD.** Current `HEAD = main = origin/main = dc03ea11fe2903ed0a5d82882a47c3dd3fd76724`. The only commit after the requested `1f0456521ae01173d41503e1f7e0884cc33d36ea` baseline is `dc03ea11...` (`paper: correct constrained-design DOI`, 1951123, 2026-09-22T22:26:41+08:00). It corrects one DOI, updates dependent bibliography/link/package audit metadata, and rebuilds PDFs. It changes no manuscript prose, author metadata, scientific result, experiment, or frozen artifact. `research-freeze-v0^{}` remains `22cf494f954cffff86080236473ca847064dca74`.

The authoritative sources remain `docs/paper-full-draft-v6-evaluation-hierarchy.md` and generated `paper/pvldb2027/main.tex`. Their pre-edit SHA-256 hashes were `2340f0c4...fa5f` and `f7d035cc...09e`, respectively. The five untracked adversarial-audit outputs were understood pre-existing work from the immediately preceding task.

## 2. Phase A evidence summary

Primary sources were checked directly, with source facts separated from mapping and novelty judgment in `docs/novelty-boundary-correction-plan-v0.md`.

- **Automatic Statistics Management (TKDE 2001):** Sections 3.3--5.2 explicitly discuss statistics dependencies, acknowledge a pathological violation of the monotonicity assumption, and give an MNSA/D `g/h` case where current irrelevance does not imply counterfactual irrelevance. It uses optimizer calls/plan comparisons rather than retained executable estimator semantics.
- **Index Interactions (PVLDB 2009):** Sections 1--4 formalize configuration-dependent positive and negative index interaction, including objects useful together. `optplan_q(X)` is treated as an opaque plan/cost source; no estimator execution or exact semantic move-invalidation representation is retained.
- **INUM (VLDB 2007):** Sections 1--4 reuse template plans and configuration-dependent access costs across index designs. It establishes query specialization and configuration-parametric hypothetical response, not a statistics-semantic dependency oracle.
- **C-PQO (SIGMOD 2008):** Sections 2--4 preserve a compact MEMO/APR representation and alternatives required for arbitrary configurations. It is substantially more than final-plan caching, but does not expose statistics-estimator state or move invalidation.
- **Liu--Ives--Loo (SIGMOD 2016):** Sections 2--5 retain optimizer search/pruning state, propagate cost/cardinality changes exactly, and can rederive pruned alternatives. Statistics-design changes and estimator internals are outside the represented boundary.
- **Self-adjusting computation (ENTCS 2006 / CMU-CS-05-129):** dynamic dependence tracking, memoization, and exact change propagation establish the generic result-plus-dependency principle. No PL citation was added because Liu is the closer database comparator and the generic principle is conceded in prose.

The strongest newly verified fact is that the 2001 statistics paper already contains both an explicit monotonicity caveat and a latent `g/h` interaction example. The strongest overlap is the composite of INUM/C-PQO configuration-parametric reuse, Liu/self-adjusting exact dependency propagation, and AutoStats/Index Interactions contextual and latent interactions. The remaining distinction is the bounded executable representation of native statistics-estimator state transitions used for both hypothetical CE and statistics-semantic exact move invalidation.

Phase A concluded:

`PHASE A PASS — MINIMAL NOVELTY CORRECTION JUSTIFIED`

## 3. Exact manuscript changes

The manuscript changes are limited to permitted novelty-positioning prose:

- **Introduction:** now concedes statistics dependencies, contextual physical-design interaction, configuration-parametric optimizer representations, and dependency-aware exact recomputation before stating the narrower estimator-semantic challenge.
- **Contribution 1:** preserves four contributions but replaces broad specialization-centered wording with the bounded native CE state transitions retained: applicability, consumption, precedence, and downstream reachability.
- **Section 8.2:** explicitly states that configuration-parametric representation and dependency-aware recomputation are established principles.
- **Section 8.6:** distinguishes established foundations from the reusable bounded estimator-semantic specialization.
- **Section 9.1:** credits AutoStats dependencies, MNSA/D latent interaction, and its monotonicity caveat; classifies this paper's non-monotonicity as systematic mechanism/setting evidence, not a historically new phenomenon; disclaims statistics interaction in general.
- **Section 9.2:** adds Index Interactions; gives stronger credit to INUM template-plan reuse and C-PQO MEMO/APR plus latent alternatives.
- **Section 9.3:** concedes dependency tracking, exact recomputation, and pruned-alternative rederivation; limits “semantic dependency oracle” to a domain-specific interface.
- **Section 9.5:** states the remainder as a bounded systems specialization after subtracting established primitives.

The Abstract, Sections 3--7, RQ wording/results, Section 10, figures, and tables were not edited. LaTeX was regenerated mechanically from the authoritative Markdown.

## 4. Citation changes

Bibliography count changed from 15 to 16. Added:

- Karl Schnaitter, Neoklis Polyzotis, and Lise Getoor. “Index Interactions in Physical Design Tuning: Modeling, Analysis, and Applications.” *PVLDB* 2(1):1234--1245, 2009. DOI `10.14778/1687627.1687766`.

No entries were removed and no existing metadata was changed. Descriptions associated with `chaudhuri2001statistics`, `papadomanolakis2007inum`, `bruno2008cpqo`, and `liu2016incremental` were corrected/strengthened in prose. Both bibliography copies contain the same new entry.

## 5. Claim-strength changes

Before correction, the paper correctly cited most close work but under-credited AutoStats interaction/latent-relevance content, omitted Index Interactions, and could be read as assigning broader novelty to the dual representation/invalidation combination. After correction it explicitly does **not** claim novelty for statistics interaction, contextual benefit, workload specialization, configuration-parametric representation, latent alternatives, dependency tracking, or exact incremental recomputation.

The retained statement is:

> CE-Replay specializes a bounded native estimator fragment to a supplied workload while preserving statistics-dependent estimator control/state as executable design parameters. That representation evaluates hypothetical CE objectives and identifies statistics-semantic state requiring reconsideration under design moves, including precedence, clause consumption, and downstream mechanism reachability.

This is labeled by the evidence as a systems representation specialization / nontrivial domain specialization, not a distinct general representation principle.

Net Markdown word delta: **-4 words** (`7015` to `7011`).

## 6. Novelty-boundary before/after

- **Before:** established configuration-parametric and incremental principles were mentioned, but statistics-specific latent interaction and physical-design interaction precedent were incomplete; the remaining boundary relied partly on “different represented layer.”
- **After:** all adverse premises are explicitly granted. The computational remainder is that the estimator state transitions determining response also determine which statistics-semantic computation must be reconsidered after a move.

The strongest residual reviewer objection remains that this is an expected composition of C-PQO-style specialization and Liu/self-adjusting dependency propagation applied below the optimizer. The revised manuscript already grants those premises. It answers only that applicability, consumption, precedence, and downstream reachability make the correct statistics-semantic invalidation boundary a concrete systems representation problem. That remainder is clearly stated without a priority claim.

## 7. Regression results

- Scientific-content changes outside novelty positioning: **0**.
- Empirical-value changes: **0**.
- Top-level sections: **10**, unchanged.
- RQs: **4**; meanings changed: **0**.
- Contributions: **4**; architecture changed: **0**.
- Figure scientific-content changes: **0**.
- Table scientific-content changes: **0**.
- Frozen-artifact changes: **0**.
- Optimizer changes: **0**.
- Experiment changes/reruns: **0**.
- Unsupported novelty uses of “first,” “unprecedented,” “uniquely,” “unlike all prior work,” or “no prior work”: **0**. Ordinary non-novel uses of “first” remain (e.g., algorithm order and “RQ2 first asks”).

## 8. Page-budget and build results

The clean official build completed successfully.

- Total pages: **12**.
- Approximate non-reference body: **11.2 pages**.
- References begin: **page 12**.
- Page size: **US Letter, 612 × 792 pt**.
- PDF version: **1.5**.
- Overfull hboxes: **0**.
- Overfull vboxes: **0**.
- Undefined citations: **0**.
- Undefined references: **0**.
- Fonts embedded: **all**.
- Type 3 fonts: **0**.

The standard pre-existing class/bibliography warnings remain non-fatal: `acmart` warns about an existing `\vspace`, `balance` reports second-column invocation, and BibTeX reports incomplete publisher/address fields for several existing entries. No new unresolved citation or layout warning remains.

Visual inspection covered pages 1, 10, 11, and 12 plus the full page count. There is no clipping, malformed reference, bad column break, citation overflow, heading orphan, or figure/table movement. The reference page's second column remains intentionally sparse; no body overflow occurs.

## 9. Synchronization and novelty tests

Markdown and LaTeX express the same revised claims; the converter-generated LaTeX includes the new citation in the same paragraphs. Bibliography copies agree. Targeted searches found no stale broad prior-art wording.

1. Could the paper claim workload-specialized/configuration-parametric representation itself is novel? **NO**.
2. Could it claim dependency-aware exact incremental recomputation itself is novel? **NO**.
3. Could it claim contextual physical-design interaction itself is novel? **NO**.
4. Could it claim native PostgreSQL MCV/FD semantics are novel? **NO**.
5. Is the remaining CE-Replay distinction clear? **YES**.
6. Is it stated as a bounded systems contribution rather than a universal principle? **YES**.

## 10. Final gate and human action

Tracked Phase B changes are limited to:

- `docs/paper-full-draft-v6-evaluation-hierarchy.md`;
- `paper/pvldb2027/main.tex`;
- `paper/pvldb2027/main.pdf`;
- `paper/pvldb2027/paper.bib`;
- `docs/paper-bibliography-v0.bib`.

New task outputs are this report, the preserved Phase A plan, and `results/novelty-boundary-correction-v0.json`. The earlier five adversarial-audit outputs remain untracked. No submission-candidate PDF or package manifest was overwritten.

Recommended human action: review the eight bounded prose replacements and the single bibliography addition, especially the AutoStats monotonicity sentence and the Section 9.5 remainder. If approved, commit the novelty audit and correction together in a later explicit action. Do not upload or tag yet.

NOVELTY BOUNDARY CORRECTED — READY FOR HUMAN REVIEW
