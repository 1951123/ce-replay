# Adversarial Novelty Search Log v0

## Boundary and date

Searches were performed on 2026-09-23. Conclusions apply only to peer-reviewed and openly discoverable literature available by that date. Search absence is not historical-priority proof.

## Sources and databases

- ACM Digital Library and DOI records
- IEEE Xplore/DOI records
- official PVLDB/VLDB proceedings PDFs
- Microsoft Research and author-hosted primary PDFs
- PMC full text for Liu--Ives--Loo
- DBLP for metadata and citation-neighborhood discovery
- Crossref for metadata checking
- publisher pages for DKE/ENTCS/PLDI work
- Google-style web search for discovery only; overlap judgments used primary papers

## Query families

Queries were repeatedly varied across these concept groups:

- `configuration parametric query optimization`, `C-PQO`, `INUM`, `optimizer memo reuse`, `arbitrary physical configurations`;
- `incremental query re-optimization`, `pruned plans reintroduced`, `optimizer state change propagation`, `cost/cardinality delta`;
- `automatic statistics management`, `statistics dependency`, `statistics interactions`, `statistics subset`, `same plan additional statistics`;
- `index interactions physical design`, `context-dependent index benefit`, `online physical design incremental benefit`;
- `self-adjusting computation`, `dynamic dependence graph`, `control dependency`, `from-scratch consistency`, `demanded computation graph`;
- `synopsis selection resource constraint`, `histogram selection`, `hypothetical statistics payload`;
- `more statistics worse estimate`, `non-monotone statistics selection`, `multicolumn statistics interaction`;
- `parametric query optimization selectivity`, `plan diagram`, `latent alternative plan`;
- `learned cardinality estimation`, `factorized CE`, `statistics-aware CE`;
- `partitioning/materialized view/index configuration interaction dependency invalidation`.

## Mandatory seed chains inspected

- AutoAdmin What-If → automatic index selection, INUM, C-PQO, constrained physical design.
- INUM → PQO, optimizer plan-space reuse, physical designer descendants including PARINDA.
- C-PQO → original PQO, MEMO/APR representation, later parametric-plan work.
- Automatic Statistics Management → MNSA, MNSA/D, Shrinking Set, CORDS, JITS, synopsis tuning.
- CORDS → multivariate/correlation discovery literature.
- JITS → sensitivity-guided acquisition, piggyback and incremental maintenance.
- Liu/Ives/Loo → recursive Datalog optimizer, incremental view maintenance, optimizer memo/pruning state.
- Constrained physical design → index interactions, online tuning and configuration scheduling.
- Self-adjusting computation → DDGs, memoized change propagation, Adapton and from-scratch consistency.

## Primary-paper mechanisms checked

The full text was inspected for C-PQO, Liu/Ives/Loo, Automatic Statistics Management, and Index Interactions. INUM was inspected through the official proceedings/author copy exposed by search, including its INUM Space and cost formula sections. Foundational self-adjusting-computation and Adapton claims were checked against publisher/author copies.

## Saturation evidence

After multiple terminology variants, searches repeatedly converged on four neighborhoods: (1) What-If/INUM/C-PQO/PQO for configuration-parametric response; (2) Automatic Statistics Management/CORDS/JITS/synopsis tuning for statistics choice/acquisition; (3) Liu/Ives/Loo and self-adjusting computation for exact dependency-driven recomputation and latent alternatives; and (4) index-interaction/online-tuning work for contextual physical-design benefit. Citation chaining produced no paper that combined all four into a native statistics-estimator semantic representation supplying both hypothetical CE response and counterfactual-safe design-move invalidation.

The strongest near misses are C-PQO, Liu/Ives/Loo, Automatic Statistics Management, and Index Interactions. Further searches returned descendants applying or approximating these ideas rather than a closer combined mechanism. This satisfies search saturation for this audit, not proof that no closer work exists.
