# Abstract Logic Blueprint v0

This is a six-sentence semantic skeleton, not final Abstract prose.

| Sentence | Role and intended claim | Supporting sections | Evidence IDs | Forbidden overclaim |
|---:|---|---|---|---|
| 1 | **Problem:** Select extended statistics for a supplied target workload under recurring maintenance capacity to reduce cardinality-estimation loss. | 1, 3 | C2, C4 | Do not call the workload training data or claim runtime optimization. |
| 2 | **Challenge:** Native statistics selection and consumption are contextual and compositional, so inclusion can be non-monotone and independent candidate scores are insufficient. | 2, 4, 8.2 | C2, C7; Statistics-Nonmonotonicity-v0; DMV-Baseline-and-Nonmonotonicity-v0 | Do not claim universal non-monotonicity or that all statistics are harmful. |
| 3 | **Key idea:** CE-Replay specializes the supported statistics-sensitive CE semantics to the workload while keeping design-dependent decisions executable, yielding objective and dependency oracles. | 5 | C1, C9, C15 | Do not claim full PostgreSQL CE, automatic compilation, or a learned q-error model. |
| 4 | **Method:** Instantiate CE-Replay for the supported PostgreSQL 16.14 conjunctive base-restriction MCV+FD fragment, including bounded constant ScalarArray semantics, and couple it to deterministic maintenance-constrained local search. | 4–7 | C1, C7, C12, C15 | Do not imply arbitrary predicates, joins, global optimization, or portable maintenance coefficients. |
| 5 | **Evidence:** Across sparse Census and dense IN-heavy DMV, replay matches fresh native estimates on 468/468 and 1,965/1,965 queries, drives mixed designs, and enables exact audited incremental evaluation. | 8.1–8.4 | C1, C8, C9, C13; Maintenance-Design-Deploy-v0; DMV-Deploy-v0 | Do not claim universal speedup, cross-workload comparability of raw loss, or complete DMV frozen-to-fresh drift. |
| 6 | **Scope/conclusion:** Executable native semantics can support maintenance-constrained statistics physical design within a validated fragment, while broader CE coverage, payload acquisition, realization robustness, and runtime objectives remain open. | 9 | C4, C5, C12, C14, C16 | Do not imply universal DBMS support, robustness, full planner replay, or query-runtime improvement. |

The final Abstract must be no stronger than these cells and should retain the same-realization qualifier whenever semantic fidelity is stated.
