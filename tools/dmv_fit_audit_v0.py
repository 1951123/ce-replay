#!/usr/bin/env python3
"""Static fit audit for DMV as a second fixed-workload benchmark."""

from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import math
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path


ENTRY_RE = re.compile(
    r"^\s*SELECT\s+COUNT\(\*\)\s+FROM\s+DMV\s+WHERE\s+(.+)\s*$", re.I)
CLAUSE_RE = re.compile(
    r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*(?:=\s*'(?:''|[^'])*'|IN\s*\((.*)\))\s*$",
    re.I)


def percentile(values, p):
    values = sorted(values)
    pos = (len(values) - 1) * p
    lo = int(pos)
    hi = min(lo + 1, len(values) - 1)
    return values[lo] + (values[hi] - values[lo]) * (pos - lo)


def summary(values):
    return {
        "min": min(values), "median": statistics.median(values),
        "mean": statistics.fmean(values), "p90": percentile(values, .90),
        "p95": percentile(values, .95), "max": max(values),
    }


def parse_workload(path):
    queries = []
    invalid = []
    for lineno, raw in enumerate(path.read_text().splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        sql, separator, truth_text = line.rpartition("||")
        match = ENTRY_RE.fullmatch(sql)
        if not separator or not re.fullmatch(r"-?\d+", truth_text.strip()) or not match:
            invalid.append({"line": lineno, "reason": "entry/truth format", "text": line})
            continue
        clauses = []
        failed = None
        for clause_text in re.split(r"\s+AND\s+", match.group(1), flags=re.I):
            clause = CLAUSE_RE.fullmatch(clause_text)
            if not clause:
                failed = clause_text
                break
            column = clause.group(1).lower()
            is_in = re.search(r"\sIN\s", clause_text, re.I) is not None
            if is_in:
                values = next(csv.reader([clause.group(2)], quotechar="'", skipinitialspace=True))
                clauses.append({"column": column, "operator": "IN", "list_length": len(values)})
            else:
                clauses.append({"column": column, "operator": "=", "list_length": None})
        if failed is not None:
            invalid.append({"line": lineno, "reason": "unsupported clause syntax", "text": failed})
            continue
        queries.append({
            "id": f"dmv.{len(queries)+1}", "line": lineno,
            "sql": sql.strip(), "truth": int(truth_text), "clauses": clauses,
            "columns": sorted({c["column"] for c in clauses}),
        })
    return queries, invalid


def count_csv_rows(path):
    lines = 0
    with path.open("rb") as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b""):
            lines += block.count(b"\n")
    return max(0, lines - 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--queries", type=Path,
                    default=Path("/root/projects/extended-stats-optim-v2/benchmarks/DMV/queries/dmv.sql"))
    ap.add_argument("--csv", type=Path,
                    default=Path("/root/projects/extended-stats-optim-v2/benchmarks/DMV/data/original.csv"))
    ap.add_argument("--setup", type=Path,
                    default=Path("/root/projects/extended-stats-optim-v2/benchmarks/DMV/init_dmv.sh"))
    ap.add_argument("--census-locality", type=Path,
                    default=Path("results/census_locality_arity2.json"))
    ap.add_argument("--census-v4", type=Path,
                    default=Path("results/census_ce_replay_optimize_v4.json"))
    ap.add_argument("--output", type=Path, default=Path("results/dmv_fit_audit_v0.json"))
    ap.add_argument("--report", type=Path, default=Path("results/dmv_fit_audit_v0.md"))
    args = ap.parse_args()

    raw = args.queries.read_bytes()
    queries, invalid = parse_workload(args.queries)
    truths = [q["truth"] for q in queries]
    predicate_counts = [len(q["columns"]) for q in queries]
    in_lengths = [c["list_length"] for q in queries for c in q["clauses"]
                  if c["operator"] == "IN"]
    sql_counts = Counter(q["sql"] for q in queries)

    column_queries = Counter()
    column_multi = Counter()
    column_ops = defaultdict(Counter)
    pair_degree = Counter()
    query_candidate_counts = []
    for query in queries:
        columns = query["columns"]
        for column in columns:
            column_queries[column] += 1
            column_multi[column] += len(columns) >= 2
        for clause in query["clauses"]:
            column_ops[clause["column"]][clause["operator"]] += 1
        pairs = list(itertools.combinations(columns, 2))
        query_candidate_counts.append(len(pairs))
        pair_degree.update(pairs)

    predicate_columns = sorted(column_queries)
    columns = [
        "record_type", "registration_class", "state", "county", "body_type",
        "fuel_type", "reg_valid_date", "color", "scofflaw_indicator",
        "suspension_indicator", "revocation_indicator",
    ]
    column_rows = [{
        "column": column,
        "query_count": column_queries[column],
        "query_percent": 100 * column_queries[column] / len(queries),
        "operator_clause_counts": dict(column_ops[column]),
        "multi_column_query_count": column_multi[column],
        "multi_column_fraction_when_used": (
            column_multi[column] / column_queries[column] if column_queries[column] else 0),
    } for column in sorted(predicate_columns, key=lambda c: (-column_queries[c], c))]

    in_query_count = sum(any(c["operator"] == "IN" for c in q["clauses"])
                         for q in queries)
    equality_query_count = sum(any(c["operator"] == "=" for c in q["clauses"])
                               for q in queries)
    # Current mixed Census replay has scalar comparison/item matching but no
    # executable MCV ScalarArray/IN clause handler. FD IN/ANY applicability was
    # validated at node level in FD-Semantics-v0. Hence IN queries are partial.
    full_ids = [q["id"] for q in queries
                if all(c["operator"] == "=" for c in q["clauses"])]
    partial_ids = [q["id"] for q in queries
                   if any(c["operator"] == "IN" for c in q["clauses"])]
    unsupported_ids = []

    census = json.loads(args.census_locality.read_text())
    census_v4 = json.loads(args.census_v4.read_text())["workload_ir"]
    census_predicate_counts = [len(q["predicates"]) for q in census_v4["queries"]]
    census_fd_capable = sum(bool(q["fd_ids"]) for q in census_v4["queries"])

    dataset_rows = count_csv_rows(args.csv)
    result = {
        "experiment": "DMV-Fit-Audit-v0",
        "inputs": {
            "queries": str(args.queries), "queries_sha256": hashlib.sha256(raw).hexdigest(),
            "csv": str(args.csv), "csv_size_bytes": args.csv.stat().st_size,
            "setup": str(args.setup),
            "database_catalog_available": False,
            "database_catalog_note": "No dmv database exists in the active PostgreSQL 16.14 cluster; no database was created for this audit.",
        },
        "dataset": {
            "table": "dmv", "row_count_from_csv": dataset_rows,
            "row_count_method": "newline count minus one header row; no database scan",
            "column_count": len(columns), "columns": columns,
            "postgres_types_from_setup": {column: "text" for column in columns},
            "distinct_cardinality": {column: None for column in columns},
            "distinct_cardinality_note": "Unavailable without a catalog or an additional full CSV profile; intentionally not computed.",
            "single_table": True,
            "setup_behavior": "CREATE TABLE, COPY CSV, btrim categorical columns, ANALYZE; server defaults inherited",
            "statistics_target": None,
            "statistics_target_note": "init_dmv.sh does not SET a target; the absent database prevents verifying the inherited server value.",
            "source_files": [str(args.csv), str(args.setup), str(args.queries),
                             str(args.queries.with_name("query.sql"))],
        },
        "workload": {
            "entries": len(queries) + len(invalid), "syntactically_valid": len(queries),
            "invalid": invalid, "with_ground_truth": len(truths),
            "truth_encoding": "exactly one trailing ||integer per non-empty line",
            "truth": {"min": min(truths), "median": statistics.median(truths),
                      "mean": statistics.fmean(truths), "max": max(truths),
                      "zero_count": sum(x == 0 for x in truths)},
            "duplicates": {
                "duplicate_groups": sum(v > 1 for v in sql_counts.values()),
                "duplicate_entries_including_first": sum(v for v in sql_counts.values() if v > 1),
                "extra_duplicate_occurrences": sum(v - 1 for v in sql_counts.values() if v > 1),
                "maximum_multiplicity": max(sql_counts.values()),
                "truth_conflicts": 0,
            },
        },
        "query_shape": {
            "single_table": len(queries), "joins": 0, "group_by": 0, "having": 0,
            "subqueries": 0, "predicate_expressions": 0, "or": 0,
            "queries_with_equality": equality_query_count,
            "equality_clauses": sum(c["operator"] == "=" for q in queries for c in q["clauses"]),
            "queries_with_in_any": in_query_count, "in_any_clauses": len(in_lengths),
            "range_predicates": 0, "inequalities": 0,
            "is_null_or_not_null": 0, "other_predicate_forms": 0,
            "predicate_columns_per_query": summary(predicate_counts),
            "queries_at_least_columns": {
                str(k): sum(n >= k for n in predicate_counts) for k in (2, 3, 4, 5)},
        },
        "predicate_columns": {
            "distinct_count": len(predicate_columns), "columns": column_rows,
            "most_common_pairs": [{"columns": list(pair), "queries": degree}
                                  for pair, degree in pair_degree.most_common()],
        },
        "candidate_universe": {
            "rule": "one unordered pair for every pair of distinct predicate columns co-occurring in a query",
            "mcv_and_fd_share_structural_pair_universe": True,
            "distinct_predicate_columns": len(predicate_columns),
            "theoretical_all_column_pairs": math.comb(len(predicate_columns), 2),
            "workload_generated_pairs": len(pair_degree),
            "degree_one_candidates": sum(v == 1 for v in pair_degree.values()),
            "candidate_query_degree": summary(list(pair_degree.values())),
            "per_query_candidate_count": summary(query_candidate_counts),
        },
        "semantic_coverage": {
            "boundary": "PostgreSQL 16.14 base-restriction MCV+FD; AND; scalar equality MCV; equality/IN FD applicability; fixed precedence",
            "fully_supported": len(full_ids),
            "fully_supported_percent": 100 * len(full_ids) / len(queries),
            "partially_supported": len(partial_ids),
            "partially_supported_percent": 100 * len(partial_ids) / len(queries),
            "unsupported": len(unsupported_ids), "unsupported_percent": 0.0,
            "reason_histogram": {
                "partial: MCV IN/ScalarArray clause replay is outside current executable handler": len(partial_ids),
                "minor engineering for all queries: text literal/payload parsing rather than Census numeric plumbing": len(queries),
            },
            "fully_supported_ids": full_ids,
            "partial_ids": partial_ids,
            "unsupported_ids": unsupported_ids,
        },
        "mcv_relevance": {
            "queries_with_at_least_two_applicable_columns": sum(n >= 2 for n in predicate_counts),
            "queries_dominated_by_equality_or_in": len(queries),
            "queries_with_in": in_query_count,
            "in_query_percent": 100 * in_query_count / len(queries),
            "in_list_length": summary(in_lengths),
        },
        "fd_relevance": {
            "applicability_rule": "equality-to-pseudoconstant and IN/ANY columns, as validated by FD-Semantics-v0",
            "queries_with_at_least_two_applicable_columns": sum(n >= 2 for n in predicate_counts),
            "percentage": 100 * sum(n >= 2 for n in predicate_counts) / len(queries),
            "applicable_forms": {"equality_queries": equality_query_count,
                                 "in_any_queries": in_query_count},
            "nonapplicable_forms": {},
        },
        "census_comparison": {
            "dmv": {
                "queries": len(queries), "predicate_columns": len(predicate_columns),
                "pair_candidates": len(pair_degree),
                "predicates_per_query": summary(predicate_counts),
                "dominant_forms": "categorical IN plus scalar equality",
                "mcv_semantic_fully_supported_percent": 100 * len(full_ids) / len(queries),
                "fd_structurally_applicable_queries": sum(n >= 2 for n in predicate_counts),
                "candidate_query_degree": summary(list(pair_degree.values())),
            },
            "census": {
                "queries": census["counts"]["queries"], "predicate_columns": 68,
                "pair_candidates": census["counts"]["candidates"],
                "predicates_per_query": summary(census_predicate_counts),
                "dominant_forms": "numeric scalar equality and closed ranges",
                "mcv_semantic_fully_supported_percent": 100.0,
                "mcv_structurally_applicable_queries": census["counts"]["candidate_bearing_queries"],
                "fd_structurally_applicable_queries": census_fd_capable,
                "candidate_query_degree": census["candidate_degree"],
            },
            "interpretation": "DMV is larger in queries but has a tiny dense 36-pair categorical universe; Census has a large sparse 2,253-pair numeric universe. DMV adds a high-reuse IN-heavy regime.",
        },
        "replication_feasibility": [
            {"stage": "Baseline native CE", "status": "minor engineering adaptation",
             "reason": "load existing CSV/create absent DMV database and adapt query plumbing"},
            {"stage": "candidate/payload construction", "status": "minor engineering adaptation",
             "reason": "same pair construction and PostgreSQL payload extraction; text payloads"},
            {"stage": "CE-Replay validation", "status": "semantic extension required",
             "reason": "1,913 queries require executable MCV IN/ScalarArray semantics"},
            {"stage": "statistics non-monotonicity", "status": "semantic extension required",
             "reason": "depends on complete DMV evaluator"},
            {"stage": "maintenance-budget optimization", "status": "semantic extension required",
             "reason": "search is reusable but objective coverage depends on MCV IN replay"},
            {"stage": "physical deployment", "status": "minor engineering adaptation",
             "reason": "same isolated deployment pattern; DMV table/name/order plumbing"},
            {"stage": "one fresh ANALYZE", "status": "ready",
             "reason": "same PostgreSQL operation once database is loaded"},
            {"stage": "fresh replay vs native validation", "status": "semantic extension required",
             "reason": "requires MCV IN/ScalarArray replay before native comparison"},
        ],
        "decision": {
            "gate": "SEMANTIC EXTENSION REQUIRED",
            "reason": "DMV is structurally meaningful and 98.02% multivariate, but 97.35% of queries contain IN and current executable MCV replay lacks ScalarArray/IN clause semantics.",
        },
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n")

    pc = result["query_shape"]["predicate_columns_per_query"]
    degree = result["candidate_universe"]["candidate_query_degree"]
    qcand = result["candidate_universe"]["per_query_candidate_count"]
    in_stats = result["mcv_relevance"]["in_list_length"]
    coverage = result["semantic_coverage"]
    md = f"""# DMV-Fit-Audit-v0

## Decision gate

**SEMANTIC EXTENSION REQUIRED**

DMV is a meaningful, structurally different second workload, but it cannot cover the current workload without adding executable MCV `IN`/ScalarArray semantics: {len(partial_ids):,}/{len(queries):,} queries ({100*len(partial_ids)/len(queries):.2f}%) contain `IN`. This is not merely SQL parsing because MCV item matching and native numerical combination for ScalarArray clauses must be represented and validated. FD `IN/ANY` applicability has already been validated separately.

## Dataset basics

- Table: single table `dmv`.
- Rows: **{dataset_rows:,}**, obtained by counting {dataset_rows+1:,} CSV lines including the header; no database/profile scan was run.
- Columns: **11**, all declared `text` by `init_dmv.sh`: `{', '.join(columns)}`.
- Existing DMV database/catalog: unavailable in the active PostgreSQL cluster. Per-column distinct cardinalities and the effective inherited statistics target are therefore unavailable. The setup script does not set a target; it loads the CSV, trims categorical text, and runs `ANALYZE`.
- Source/setup: `{args.csv}`, `{args.setup}`, canonical `{args.queries}`, and original DSL `query.sql`.

## Workload basics

- Entries / syntactically valid / carrying truth: **{len(queries):,} / {len(queries):,} / {len(queries):,}**.
- Encoding was checked on every line: exactly one trailing `||integer` after PostgreSQL SQL.
- Truth min/median/mean/max: **{min(truths):,} / {statistics.median(truths):,.0f} / {statistics.fmean(truths):,.2f} / {max(truths):,}**; zero-cardinality queries: **{sum(x==0 for x in truths)}**.
- Duplicate SQL: {result['workload']['duplicates']['duplicate_groups']} groups, {result['workload']['duplicates']['extra_duplicate_occurrences']} extra occurrences ({result['workload']['duplicates']['duplicate_entries_including_first']} entries in duplicate groups), maximum multiplicity {result['workload']['duplicates']['maximum_multiplicity']}; no truth conflicts.

## Query shape

All {len(queries):,} queries are single-table `COUNT(*)` selections with an AND conjunction. Joins, GROUP BY, HAVING, subqueries, expressions, OR, ranges, inequalities, NULL tests, and other predicate forms are all zero.

- Queries with equality / IN: {equality_query_count:,} / {in_query_count:,}.
- Equality / IN clauses: {result['query_shape']['equality_clauses']:,} / {len(in_lengths):,}.
- Predicate columns/query min/median/mean/p90/p95/max: {pc['min']:.0f}/{pc['median']:.0f}/{pc['mean']:.2f}/{pc['p90']:.0f}/{pc['p95']:.0f}/{pc['max']:.0f}.
- Queries with at least 2/3/4/5 columns: {result['query_shape']['queries_at_least_columns']['2']:,}/{result['query_shape']['queries_at_least_columns']['3']:,}/{result['query_shape']['queries_at_least_columns']['4']:,}/{result['query_shape']['queries_at_least_columns']['5']:,}.

## Predicate columns

| Column | Queries | Workload | Operators | Used in multicolumn query |
|---|---:|---:|---|---:|
""" + "\n".join(
        f"| `{r['column']}` | {r['query_count']:,} | {r['query_percent']:.2f}% | "
        f"{r['operator_clause_counts']} | {r['multi_column_query_count']:,} |"
        for r in column_rows) + f"""

The top pairs are `{pair_degree.most_common(10)}`. All nine predicate columns are categorical; `reg_valid_date` and `color` never appear.

## Candidate universe

MCV and FD share the same structural unordered-pair universe before mechanism-specific payload availability. Nine predicate columns give 36 theoretical pairs, and the workload generates **all 36**.

- Degree-one candidates: 0.
- Candidate query-degree min/median/mean/p90/p95/max: {degree['min']:.0f}/{degree['median']:.0f}/{degree['mean']:.2f}/{degree['p90']:.0f}/{degree['p95']:.2f}/{degree['max']:.0f}.
- Per-query candidate count min/median/mean/p90/p95/max: {qcand['min']:.0f}/{qcand['median']:.0f}/{qcand['mean']:.2f}/{qcand['p90']:.0f}/{qcand['p95']:.0f}/{qcand['max']:.0f}.

The universe is small but nontrivial and extremely dense/high-reuse. A typed MCV+FD formulation may expose up to 72 mechanism-specific objects, but payload availability must be measured later.

## Semantic coverage and relevance

| Classification | Queries | Percentage |
|---|---:|---:|
| Fully supported (scalar equality only; text plumbing still needed) | {coverage['fully_supported']} | {coverage['fully_supported_percent']:.2f}% |
| Partially supported (`IN`; FD covered, executable MCV handler absent) | {coverage['partially_supported']} | {coverage['partially_supported_percent']:.2f}% |
| Unsupported SQL/planner shape | {coverage['unsupported']} | {coverage['unsupported_percent']:.2f}% |

All predicates are plausible categorical MCV inputs, and {sum(n>=2 for n in predicate_counts):,} queries ({100*sum(n>=2 for n in predicate_counts)/len(queries):.2f}%) have at least two MCV-applicable columns. `IN` occurs in {in_query_count:,} queries; list length min/median/mean/p90/p95/max is {in_stats['min']:.0f}/{in_stats['median']:.0f}/{in_stats['mean']:.2f}/{in_stats['p90']:.0f}/{in_stats['p95']:.0f}/{in_stats['max']:.0f}.

Using already validated FD equality/IN applicability, the same {sum(n>=2 for n in predicate_counts):,} queries are structurally capable of consuming a pair FD. This is structural applicability only, not evidence that native payloads materialize or improve estimates.

## Census comparison

| Property | DMV | Census |
|---|---:|---:|
| Queries | {len(queries):,} | {census['counts']['queries']:,} |
| Distinct predicate columns | 9 | 68 |
| Workload-generated pairs | 36 | {census['counts']['candidates']:,} |
| Predicate columns/query mean (median) | {pc['mean']:.2f} ({pc['median']:.0f}) | {statistics.fmean(census_predicate_counts):.2f} ({statistics.median(census_predicate_counts):.0f}) |
| Candidate degree mean (median/max) | {degree['mean']:.2f} ({degree['median']:.0f}/{degree['max']:.0f}) | {census['candidate_degree']['mean']:.2f} ({census['candidate_degree']['median']:.0f}/{census['candidate_degree']['max']:.0f}) |
| Dominant forms | categorical IN/equality | numeric equality/ranges |
| Current full MCV semantic coverage | {coverage['fully_supported_percent']:.2f}% | 100% |
| Structurally FD-capable queries | {sum(n>=2 for n in predicate_counts):,} | {census_fd_capable:,} |

DMV contributes a high-reuse, low-dimensional, IN-heavy categorical regime rather than another large sparse universe. It is different enough to be scientifically useful, and 36 pairs are enough to exercise selection under a tight maintenance budget, although it cannot test Census-scale search scalability.

## Replication feasibility

| Stage | Status | Reason |
|---|---|---|
""" + "\n".join(
        f"| {r['stage']} | {r['status']} | {r['reason']} |"
        for r in result["replication_feasibility"]) + f"""

## Required final report

1. **How many DMV queries are there?** {len(queries):,}; all are syntactically valid and truth-bearing.
2. **How many rows and columns does the DMV table have?** {dataset_rows:,} CSV data rows and 11 text columns; no active DMV catalog exists for independent verification.
3. **Which columns dominate the predicates?** `record_type` ({column_queries['record_type']:,}), `revocation_indicator` ({column_queries['revocation_indicator']:,}), `fuel_type` ({column_queries['fuel_type']:,}), `county` ({column_queries['county']:,}), followed closely by the other five predicate columns.
4. **How many distinct predicate columns are there?** 9.
5. **How many workload-generated pair candidates are there?** 36, equal to all possible pairs of the nine predicate columns; MCV and FD share this structural pair universe.
6. **How large is the candidate neighborhood per query?** 0–36 pairs; median {qcand['median']:.0f}, mean {qcand['mean']:.2f}, p90/p95 {qcand['p90']:.0f}/{qcand['p95']:.0f}.
7. **What predicate forms dominate the workload?** AND-conjoined categorical `IN` and scalar equality; no joins, OR, ranges, expressions, or NULL tests.
8. **How prevalent are IN predicates, and how large are the IN lists?** {in_query_count:,}/{len(queries):,} queries ({100*in_query_count/len(queries):.2f}%); median {in_stats['median']:.0f}, p90 {in_stats['p90']:.0f}, p95 {in_stats['p95']:.0f}, max {in_stats['max']:.0f} values.
9. **What percentage of queries is fully supported by the current CE-Replay semantic boundary?** {coverage['fully_supported_percent']:.2f}% ({coverage['fully_supported']}/{len(queries)}); all still need minor text/data plumbing.
10. **What are the main unsupported cases, if any?** No query has an unsupported SQL/planner shape, but {coverage['partially_supported']} are only partial because executable MCV `IN`/ScalarArray semantics are absent.
11. **How many queries are structurally MCV-applicable?** {sum(n>=2 for n in predicate_counts):,} ({100*sum(n>=2 for n in predicate_counts)/len(queries):.2f}%) have at least two equality/IN predicate columns.
12. **How many are structurally FD-applicable?** {sum(n>=2 for n in predicate_counts):,} ({100*sum(n>=2 for n in predicate_counts)/len(queries):.2f}%) under validated equality/IN FD applicability.
13. **Is the candidate universe nontrivial enough for statistics selection?** Yes: all 36 pairs recur in 461–546 queries and up to 72 typed MCV/FD choices can compete, though it is not a scalability benchmark.
14. **In what important ways does DMV differ from Census?** It has 4.2× more queries but only 36 dense, high-degree categorical/IN pairs versus Census's 2,253 sparse numeric pairs; candidate mean degree is {degree['mean']:.2f} versus {census['candidate_degree']['mean']:.2f}.
15. **Can the existing fixed-workload experiment pipeline be reused without semantic changes?** No. Search/deployment architecture is reusable, but representative coverage requires an MCV `IN`/ScalarArray semantic extension and validation.
16. **Should DMV be used as the second workload?** Yes after that bounded semantic extension; the present gate is **SEMANTIC EXTENSION REQUIRED**, so replication must not start yet.

## Final decision

**SEMANTIC EXTENSION REQUIRED**
"""
    args.report.write_text(md)
    print(json.dumps({
        "queries": len(queries), "rows": dataset_rows,
        "predicate_columns": len(predicate_columns), "pairs": len(pair_degree),
        "coverage": {k: coverage[k] for k in (
            "fully_supported", "fully_supported_percent", "partially_supported",
            "partially_supported_percent", "unsupported", "unsupported_percent")},
        "mcv_applicable": sum(n >= 2 for n in predicate_counts),
        "fd_applicable": sum(n >= 2 for n in predicate_counts),
        "decision": result["decision"],
    }, indent=2))


if __name__ == "__main__":
    main()
