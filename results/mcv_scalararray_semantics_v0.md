# MCV-ScalarArray-Semantics-v0

## PostgreSQL 16.14 source-derived semantics

`extended_stats.c:statext_is_compatible_clause_internal()` (lines 1324–1506) recognizes `Var/Expr op ANY/ALL (Const)` ScalarArray clauses. `choose_best_statistics()` (1225–1321) is unchanged: maximize covered attributes, prefer fewer statistic keys, then retain the first stats-list entry on a tie. `statext_mcv_clauselist_selectivity()` (1696–2013) attaches all covered clauses to the winner, marks their indexes in `estimatedclauses`, resets them for later rounds, and multiplies the winner's selectivity into the result.

`mcv.c:mcv_get_match_bitmap()` (1584–1972) directly evaluates each MCV item's dimension value against each deconstructed constant-array element using the operator function. `useOr=true` (`IN`/`= ANY`) merges elements with OR; `useOr=false` (`ALL`) merges with AND. NULL elements merge false. Duplicate values may repeat operator calls but cannot count an MCV item more than once.

`mcv_clauselist_selectivity()` (2035–2087) sums `frequency` and `base_frequency` once for every matched item and sums every item frequency for total coverage. `mcv_combine_selectivities()` (1977–2030) computes `other=min(clamp(simple-base),1-total)` and returns `clamp(mcv+other)`.

Therefore PostgreSQL evaluates ScalarArray predicates **directly against MCV items**, not by expanding them into independent equality alternatives.

## Supported boundary

- Supported: conjunctive base-relation `a IN (Const...)` and `a = ANY(Const text[])`, including duplicates and NULL elements.
- Recognized but outside this experiment: `<> ALL`, other native-supported comparison ScalarArrays, and OR/NOT trees.
- Unsupported: nonconstant arrays, reversed Var position, arbitrary operators, joins, and parameterized clauses.

## Fixture and test matrix

The isolated deterministic fixture has 2,400 rows and four categorical text columns, target 10. Six configurations cover one pair, one triple, two overlapping orderings, disjoint pairs, and three competing pairs. Payloads and the exact generation SQL are preserved in JSON.

| Metric | Result |
|---|---:|
| Synthetic cases | 29 |
| Strict numerical + trace matches | 29 |
| Selected-stat trace matches | 29 |
| Max pre-clamp row relative error | 4.38e-15 |
| Max native-node field relative error | 4.44e-15 |
| Max absolute row error | 6.82e-13 |

The matrix contains scalar equality, standalone arrays, equality+array in both directions, two/three arrays, duplicates, NULL elements, non-MCV values, overlapping statistics, disjoint composition, three-way competition, and reversed creation order. Standalone one-column cases correctly select no multivariate statistic.

### Correctness layers

- Clause semantic correctness: **established** from native vs replay `mcv/base/total/stat` fields.
- Control semantic correctness: **established** from selected-stat traces and source-derived consumed clause indexes.
- End-to-end CE correctness: **established** against native pre-clamp raw rows.

Reversing overlapping `ab,bc` creation order changed the winner trace in 2/2 paired cases. Replay reproduced both orders. ScalarArray introduces no new precedence rule.

## Regression and DMV re-audit

Existing Census scalar MCV fixtures: 128/128 pass at 1e-12; maximum relative error 5.55e-16. No Census optimization or ANALYZE was rerun.

DMV full semantic coverage changes from **52/1,965 (2.65%)** to **1,965/1,965 (100%)**. The canonical file contains only AND-conjoined text equality and equality-IN predicates, so no partially supported or unsupported DMV semantics remain within the audited query file.

## Required final verdict

1. **What exact PostgreSQL 16.14 source path implements MCV ScalarArray evaluation?** Compatibility in `extended_stats.c:statext_is_compatible_clause_internal` (1324–1506); GreedyCover/consumption in `choose_best_statistics` and `statext_mcv_clauselist_selectivity` (1225–1321, 1696–2013); item evaluation in `mcv.c:mcv_get_match_bitmap` (1584–1972); aggregation in `mcv_clauselist_selectivity` (2035–2087); combination in `mcv_combine_selectivities` (1977–2030).
2. **How does PostgreSQL evaluate `IN` / `= ANY` against an MCV item?** It deconstructs the constant array and directly calls the equality operator for the item's dimension value against each non-NULL element, OR-merging the results.
3. **How are multiple ScalarArray values combined?** `ANY` uses OR with short-circuit; `ALL` uses AND. Duplicates do not multiply frequency, and NULL elements contribute false to the bitmap merge.
4. **How are matched MCV frequency and base frequency computed?** Each item whose final bitmap is true contributes its stored frequency and base_frequency once; total is the frequency sum of the entire MCV list.
5. **Does ScalarArray change existing MCV GreedyCover selection semantics?** No.
6. **Does it change estimated-clause consumption semantics?** No; all compatible clauses fully covered by the chosen statistic are marked and removed from later rounds.
7. **Does OID/creation-order precedence behave as before?** Yes; tied objects retain stats-list/OID order, and replay matched both tested physical orders.
8. **How many synthetic cases were tested?** 29.
9. **How many matched native PostgreSQL within the strict tolerance?** 29/29 including trace and native-node fields.
10. **What was the maximum numerical error?** Row relative 4.38e-15; native-node field relative 4.44e-15; absolute rows 6.82e-13.
11. **Did any existing scalar MCV regression test fail?** No; 128/128 passed.
12. **What was DMV full-support coverage before the extension?** 52/1,965 (2.65%).
13. **What is DMV full-support coverage after the extension?** 1,965/1,965 (100%).
14. **What unsupported DMV semantics remain?** None in the canonical DMV SQL; broader ScalarArray operators and nonconjunctive/parameterized forms remain outside the project boundary.
15. **Is the semantic boundary now sufficient to begin `DMV-Fixed-Workload-Replication-v0`?** Yes.

## Final gate

READY FOR DMV REPLICATION
