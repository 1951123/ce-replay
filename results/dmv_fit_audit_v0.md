# DMV-Fit-Audit-v0

## Decision gate

**SEMANTIC EXTENSION REQUIRED**

DMV is a meaningful, structurally different second workload, but it cannot cover the current workload without adding executable MCV `IN`/ScalarArray semantics: 1,913/1,965 queries (97.35%) contain `IN`. This is not merely SQL parsing because MCV item matching and native numerical combination for ScalarArray clauses must be represented and validated. FD `IN/ANY` applicability has already been validated separately.

## Dataset basics

- Table: single table `dmv`.
- Rows: **11,591,877**, obtained by counting 11,591,878 CSV lines including the header; no database/profile scan was run.
- Columns: **11**, all declared `text` by `init_dmv.sh`: `record_type, registration_class, state, county, body_type, fuel_type, reg_valid_date, color, scofflaw_indicator, suspension_indicator, revocation_indicator`.
- Existing DMV database/catalog: unavailable in the active PostgreSQL cluster. Per-column distinct cardinalities and the effective inherited statistics target are therefore unavailable. The setup script does not set a target; it loads the CSV, trims categorical text, and runs `ANALYZE`.
- Source/setup: `/root/projects/extended-stats-optim-v2/benchmarks/DMV/data/original.csv`, `/root/projects/extended-stats-optim-v2/benchmarks/DMV/init_dmv.sh`, canonical `/root/projects/extended-stats-optim-v2/benchmarks/DMV/queries/dmv.sql`, and original DSL `query.sql`.

## Workload basics

- Entries / syntactically valid / carrying truth: **1,965 / 1,965 / 1,965**.
- Encoding was checked on every line: exactly one trailing `||integer` after PostgreSQL SQL.
- Truth min/median/mean/max: **0 / 2,322,570 / 4,422,658.62 / 11,590,343**; zero-cardinality queries: **2**.
- Duplicate SQL: 27 groups, 43 extra occurrences (70 entries in duplicate groups), maximum multiplicity 5; no truth conflicts.

## Query shape

All 1,965 queries are single-table `COUNT(*)` selections with an AND conjunction. Joins, GROUP BY, HAVING, subqueries, expressions, OR, ranges, inequalities, NULL tests, and other predicate forms are all zero.

- Queries with equality / IN: 1,800 / 1,913.
- Equality / IN clauses: 3,783 / 5,104.
- Predicate columns/query min/median/mean/p90/p95/max: 1/5/4.52/7/7/9.
- Queries with at least 2/3/4/5 columns: 1,926/1,794/1,467/995.

## Predicate columns

| Column | Queries | Workload | Operators | Used in multicolumn query |
|---|---:|---:|---|---:|
| `record_type` | 1,024 | 52.11% | {'IN': 524, '=': 500} | 1,018 |
| `revocation_indicator` | 1,003 | 51.04% | {'=': 1003} | 1,000 |
| `fuel_type` | 993 | 50.53% | {'IN': 765, '=': 228} | 987 |
| `county` | 986 | 50.18% | {'IN': 964, '=': 22} | 977 |
| `suspension_indicator` | 983 | 50.03% | {'=': 983} | 979 |
| `scofflaw_indicator` | 978 | 49.77% | {'=': 978} | 976 |
| `state` | 978 | 49.77% | {'IN': 965, '=': 13} | 975 |
| `registration_class` | 972 | 49.47% | {'IN': 946, '=': 26} | 969 |
| `body_type` | 970 | 49.36% | {'IN': 940, '=': 30} | 967 |

The top pairs are `[(('record_type', 'revocation_indicator'), 546), (('record_type', 'suspension_indicator'), 529), (('record_type', 'scofflaw_indicator'), 524), (('record_type', 'state'), 520), (('body_type', 'revocation_indicator'), 518), (('fuel_type', 'record_type'), 516), (('registration_class', 'scofflaw_indicator'), 512), (('fuel_type', 'revocation_indicator'), 508), (('revocation_indicator', 'state'), 507), (('scofflaw_indicator', 'state'), 505)]`. All nine predicate columns are categorical; `reg_valid_date` and `color` never appear.

## Candidate universe

MCV and FD share the same structural unordered-pair universe before mechanism-specific payload availability. Nine predicate columns give 36 theoretical pairs, and the workload generates **all 36**.

- Degree-one candidates: 0.
- Candidate query-degree min/median/mean/p90/p95/max: 461/498/497.08/519/525.25/546.
- Per-query candidate count min/median/mean/p90/p95/max: 0/10/9.11/21/21/36.

The universe is small but nontrivial and extremely dense/high-reuse. A typed MCV+FD formulation may expose up to 72 mechanism-specific objects, but payload availability must be measured later.

## Semantic coverage and relevance

| Classification | Queries | Percentage |
|---|---:|---:|
| Fully supported (scalar equality only; text plumbing still needed) | 52 | 2.65% |
| Partially supported (`IN`; FD covered, executable MCV handler absent) | 1913 | 97.35% |
| Unsupported SQL/planner shape | 0 | 0.00% |

All predicates are plausible categorical MCV inputs, and 1,926 queries (98.02%) have at least two MCV-applicable columns. `IN` occurs in 1,913 queries; list length min/median/mean/p90/p95/max is 1/12/14.34/30/35/43.

Using already validated FD equality/IN applicability, the same 1,926 queries are structurally capable of consuming a pair FD. This is structural applicability only, not evidence that native payloads materialize or improve estimates.

## Census comparison

| Property | DMV | Census |
|---|---:|---:|
| Queries | 1,965 | 468 |
| Distinct predicate columns | 9 | 68 |
| Workload-generated pairs | 36 | 2,253 |
| Predicate columns/query mean (median) | 4.52 (5) | 6.63 (7) |
| Candidate degree mean (median/max) | 497.08 (498/546) | 4.44 (4/13) |
| Dominant forms | categorical IN/equality | numeric equality/ranges |
| Current full MCV semantic coverage | 2.65% | 100% |
| Structurally FD-capable queries | 1,926 | 435 |

DMV contributes a high-reuse, low-dimensional, IN-heavy categorical regime rather than another large sparse universe. It is different enough to be scientifically useful, and 36 pairs are enough to exercise selection under a tight maintenance budget, although it cannot test Census-scale search scalability.

## Replication feasibility

| Stage | Status | Reason |
|---|---|---|
| Baseline native CE | minor engineering adaptation | load existing CSV/create absent DMV database and adapt query plumbing |
| candidate/payload construction | minor engineering adaptation | same pair construction and PostgreSQL payload extraction; text payloads |
| CE-Replay validation | semantic extension required | 1,913 queries require executable MCV IN/ScalarArray semantics |
| statistics non-monotonicity | semantic extension required | depends on complete DMV evaluator |
| maintenance-budget optimization | semantic extension required | search is reusable but objective coverage depends on MCV IN replay |
| physical deployment | minor engineering adaptation | same isolated deployment pattern; DMV table/name/order plumbing |
| one fresh ANALYZE | ready | same PostgreSQL operation once database is loaded |
| fresh replay vs native validation | semantic extension required | requires MCV IN/ScalarArray replay before native comparison |

## Required final report

1. **How many DMV queries are there?** 1,965; all are syntactically valid and truth-bearing.
2. **How many rows and columns does the DMV table have?** 11,591,877 CSV data rows and 11 text columns; no active DMV catalog exists for independent verification.
3. **Which columns dominate the predicates?** `record_type` (1,024), `revocation_indicator` (1,003), `fuel_type` (993), `county` (986), followed closely by the other five predicate columns.
4. **How many distinct predicate columns are there?** 9.
5. **How many workload-generated pair candidates are there?** 36, equal to all possible pairs of the nine predicate columns; MCV and FD share this structural pair universe.
6. **How large is the candidate neighborhood per query?** 0–36 pairs; median 10, mean 9.11, p90/p95 21/21.
7. **What predicate forms dominate the workload?** AND-conjoined categorical `IN` and scalar equality; no joins, OR, ranges, expressions, or NULL tests.
8. **How prevalent are IN predicates, and how large are the IN lists?** 1,913/1,965 queries (97.35%); median 12, p90 30, p95 35, max 43 values.
9. **What percentage of queries is fully supported by the current CE-Replay semantic boundary?** 2.65% (52/1965); all still need minor text/data plumbing.
10. **What are the main unsupported cases, if any?** No query has an unsupported SQL/planner shape, but 1913 are only partial because executable MCV `IN`/ScalarArray semantics are absent.
11. **How many queries are structurally MCV-applicable?** 1,926 (98.02%) have at least two equality/IN predicate columns.
12. **How many are structurally FD-applicable?** 1,926 (98.02%) under validated equality/IN FD applicability.
13. **Is the candidate universe nontrivial enough for statistics selection?** Yes: all 36 pairs recur in 461–546 queries and up to 72 typed MCV/FD choices can compete, though it is not a scalability benchmark.
14. **In what important ways does DMV differ from Census?** It has 4.2× more queries but only 36 dense, high-degree categorical/IN pairs versus Census's 2,253 sparse numeric pairs; candidate mean degree is 497.08 versus 4.44.
15. **Can the existing fixed-workload experiment pipeline be reused without semantic changes?** No. Search/deployment architecture is reusable, but representative coverage requires an MCV `IN`/ScalarArray semantic extension and validation.
16. **Should DMV be used as the second workload?** Yes after that bounded semantic extension; the present gate is **SEMANTIC EXTENSION REQUIRED**, so replication must not start yet.

## Final decision

**SEMANTIC EXTENSION REQUIRED**
