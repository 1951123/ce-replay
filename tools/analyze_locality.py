#!/usr/bin/env python3
"""Analyze query--candidate locality for single-table COUNT workloads.

The expected input has one query per line.  Census' ``SQL||cardinality`` form
is supported; the suffix is ignored.  A candidate is identified by
``(table, unordered column set)``.  Consequently, representation parameters
that would only duplicate a candidate's neighborhood are intentionally not
part of this structural analysis.

This script uses only the Python standard library so the analysis can be run
before the rest of the optimizer is bootstrapped.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import statistics
from collections import defaultdict
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
from typing import Iterable


_FROM_RE = re.compile(
    r"\bFROM\s+([A-Za-z_][A-Za-z0-9_$.]*)(?:\s+(?:AS\s+)?[A-Za-z_][A-Za-z0-9_$]*)?",
    re.IGNORECASE,
)
_WHERE_RE = re.compile(r"\bWHERE\b(.*)$", re.IGNORECASE | re.DOTALL)
_PREDICATE_COLUMN_RE = re.compile(
    r"\b((?:[A-Za-z_][A-Za-z0-9_$]*\.)?[A-Za-z_][A-Za-z0-9_$]*)\s*"
    r"(?:=|<>|!=|<=|>=|<|>|\bBETWEEN\b|\bIN\s*\()",
    re.IGNORECASE,
)


@dataclass(frozen=True, order=True)
class Candidate:
    table: str
    columns: tuple[str, ...]


@dataclass(frozen=True)
class Query:
    qid: str
    sql: str
    table: str
    predicate_columns: frozenset[str]


class DisjointSet:
    def __init__(self, size: int) -> None:
        self.parent = list(range(size))
        self.rank = [0] * size

    def find(self, item: int) -> int:
        while self.parent[item] != item:
            self.parent[item] = self.parent[self.parent[item]]
            item = self.parent[item]
        return item

    def union(self, left: int, right: int) -> None:
        left, right = self.find(left), self.find(right)
        if left == right:
            return
        if self.rank[left] < self.rank[right]:
            left, right = right, left
        self.parent[right] = left
        if self.rank[left] == self.rank[right]:
            self.rank[left] += 1


def parse_queries(path: Path) -> list[Query]:
    queries: list[Query] = []
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("--"):
            continue
        sql = line.rpartition("||")[0].strip() if "||" in line else line
        table_match = _FROM_RE.search(sql)
        where_match = _WHERE_RE.search(sql)
        if table_match is None or where_match is None:
            raise ValueError(f"line {line_number}: expected a single-table SELECT with WHERE")
        table = table_match.group(1).lower()
        columns = {
            match.group(1).rpartition(".")[2].lower()
            for match in _PREDICATE_COLUMN_RE.finditer(where_match.group(1))
        }
        queries.append(Query(f"query.{line_number}", sql, table, frozenset(columns)))
    return queries


def candidate_set(query: Query, arities: Iterable[int]) -> set[Candidate]:
    columns = sorted(query.predicate_columns)
    return {
        Candidate(query.table, combo)
        for arity in sorted(set(arities))
        if 2 <= arity <= len(columns)
        for combo in combinations(columns, arity)
    }


def _percentile(values: list[int], fraction: float) -> float:
    """Linearly interpolated percentile (same convention as NumPy's default)."""
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return float(ordered[lower])
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def distribution(values: Iterable[int]) -> dict[str, float | int]:
    values = list(values)
    if not values:
        return {
            "min": 0, "mean": 0.0, "median": 0.0, "p90": 0.0,
            "p95": 0.0, "p99": 0.0, "max": 0,
        }
    return {
        "min": min(values),
        "mean": statistics.fmean(values),
        "median": statistics.median(values),
        "p90": _percentile(values, 0.90),
        "p95": _percentile(values, 0.95),
        "p99": _percentile(values, 0.99),
        "max": max(values),
    }


def component_summary(
    queries: list[Query],
    by_query: list[set[Candidate]],
) -> list[dict[str, object]]:
    """Connected components, retaining isolated query nodes."""
    candidate_queries: dict[Candidate, list[int]] = defaultdict(list)
    for query_index, candidates in enumerate(by_query):
        for candidate in candidates:
            candidate_queries[candidate].append(query_index)

    dsu = DisjointSet(len(queries))
    for incident_queries in candidate_queries.values():
        anchor = incident_queries[0]
        for query_index in incident_queries[1:]:
            dsu.union(anchor, query_index)

    component_queries: dict[int, list[int]] = defaultdict(list)
    for query_index in range(len(queries)):
        component_queries[dsu.find(query_index)].append(query_index)

    components = []
    for query_indexes in component_queries.values():
        candidates = set().union(*(by_query[index] for index in query_indexes))
        components.append({
            "query_count": len(query_indexes),
            "candidate_count": len(candidates),
            "edge_count": sum(len(by_query[index]) for index in query_indexes),
            "query_ids": [queries[index].qid for index in query_indexes],
        })
    components.sort(key=lambda item: (item["query_count"], item["candidate_count"]), reverse=True)
    return components


def peeling_curve(
    queries: list[Query],
    by_query: list[set[Candidate]],
    candidate_queries: dict[Candidate, list[int]],
) -> list[dict[str, object]]:
    """Remove original-degree hubs: retain exactly candidates with degree <= k."""
    total_candidates = len(candidate_queries)
    total_edges = sum(len(candidates) for candidates in by_query)
    max_degree = max((len(indexes) for indexes in candidate_queries.values()), default=0)
    points = []
    # k=0 is the fully peeled baseline; max_degree is the original graph.
    for max_retained_degree in range(max_degree + 1):
        retained = {
            candidate
            for candidate, indexes in candidate_queries.items()
            if len(indexes) <= max_retained_degree
        }
        peeled_by_query = [candidates & retained for candidates in by_query]
        components = component_summary(queries, peeled_by_query)
        giant = components[0] if components else {
            "query_count": 0, "candidate_count": 0, "edge_count": 0
        }
        retained_edges = sum(len(candidates) for candidates in peeled_by_query)
        points.append({
            "max_retained_degree_k": max_retained_degree,
            "removed_candidate_count": total_candidates - len(retained),
            "removed_candidate_ratio": (
                (total_candidates - len(retained)) / total_candidates
                if total_candidates else 0.0
            ),
            "removed_edge_count": total_edges - retained_edges,
            "removed_edge_ratio": (
                (total_edges - retained_edges) / total_edges if total_edges else 0.0
            ),
            "remaining_candidate_count": len(retained),
            "component_count": len(components),
            "nontrivial_component_count": sum(c["query_count"] > 1 for c in components),
            "giant_query_count": giant["query_count"],
            "giant_query_ratio": giant["query_count"] / len(queries) if queries else 0.0,
            "giant_candidate_count": giant["candidate_count"],
            "giant_candidate_ratio_of_remaining": (
                giant["candidate_count"] / len(retained) if retained else 0.0
            ),
            "giant_candidate_ratio_of_original": (
                giant["candidate_count"] / total_candidates if total_candidates else 0.0
            ),
        })
    return points


def analyze(queries: list[Query], arities: Iterable[int]) -> dict[str, object]:
    arities = tuple(sorted(set(arities)))
    by_query = [candidate_set(query, arities) for query in queries]
    candidate_queries: dict[Candidate, list[int]] = defaultdict(list)
    for query_index, candidates in enumerate(by_query):
        for candidate in candidates:
            candidate_queries[candidate].append(query_index)

    components = component_summary(queries, by_query)

    query_degrees = [len(candidates) for candidates in by_query]
    candidate_degrees = [len(indexes) for indexes in candidate_queries.values()]
    edge_count = sum(query_degrees)
    query_count = len(queries)
    candidate_count = len(candidate_queries)
    giant = components[0] if components else {"query_count": 0, "candidate_count": 0, "edge_count": 0}
    top_candidate_hubs = sorted(
        (
            {"table": candidate.table, "columns": list(candidate.columns), "degree": len(indexes)}
            for candidate, indexes in candidate_queries.items()
        ),
        key=lambda item: (-item["degree"], item["table"], item["columns"]),
    )[:10]
    degree_counts: dict[int, int] = defaultdict(int)
    for degree in candidate_degrees:
        degree_counts[degree] += 1
    candidate_degree_histogram = [
        {
            "degree": degree,
            "candidate_count": count,
            "candidate_ratio": count / candidate_count if candidate_count else 0.0,
            "incident_edge_count": degree * count,
            "incident_edge_ratio": degree * count / edge_count if edge_count else 0.0,
        }
        for degree, count in sorted(degree_counts.items())
    ]
    neighborhood_sizes: dict[Candidate, int] = {}
    neighborhood_by_degree: dict[int, list[int]] = defaultdict(list)
    for candidate, incident_queries in candidate_queries.items():
        neighborhood = set().union(*(by_query[index] for index in incident_queries))
        size = len(neighborhood)
        neighborhood_sizes[candidate] = size
        neighborhood_by_degree[len(incident_queries)].append(size)
    neighborhood_size_counts: dict[int, int] = defaultdict(int)
    for size in neighborhood_sizes.values():
        neighborhood_size_counts[size] += 1
    neighborhood_histogram = [
        {
            "neighborhood_size": size,
            "candidate_count": count,
            "candidate_ratio": count / candidate_count if candidate_count else 0.0,
        }
        for size, count in sorted(neighborhood_size_counts.items())
    ]
    interaction_edge_count = sum(size - 1 for size in neighborhood_sizes.values()) // 2

    return {
        "candidate_arities": list(arities),
        "counts": {
            "queries": query_count,
            "candidate_bearing_queries": sum(degree > 0 for degree in query_degrees),
            "candidates": candidate_count,
            "edges": edge_count,
            "components": len(components),
        },
        "query_degree": distribution(query_degrees),
        "candidate_degree": distribution(candidate_degrees),
        "candidate_reuse": {
            "degree_1_count": sum(degree == 1 for degree in candidate_degrees),
            "degree_1_ratio": (
                sum(degree == 1 for degree in candidate_degrees) / candidate_count
                if candidate_count else 0.0
            ),
        },
        "candidate_degree_histogram": candidate_degree_histogram,
        "candidate_interaction_neighborhood": {
            "definition_includes_self": True,
            "size": distribution(neighborhood_sizes.values()),
            "other_candidates_size": distribution(size - 1 for size in neighborhood_sizes.values()),
            "fraction_of_candidate_space": distribution(
                size / candidate_count for size in neighborhood_sizes.values()
            ),
            "by_candidate_degree": [
                {"candidate_degree": degree, **distribution(sizes)}
                for degree, sizes in sorted(neighborhood_by_degree.items())
            ],
            "candidate_interaction_edges": interaction_edge_count,
            "candidate_interaction_density": (
                2 * interaction_edge_count / (candidate_count * (candidate_count - 1))
                if candidate_count > 1 else 0.0
            ),
            "histogram": neighborhood_histogram,
        },
        "high_degree_peeling_curve": peeling_curve(queries, by_query, candidate_queries),
        "top_candidate_hubs": top_candidate_hubs,
        "bipartite_density": (
            edge_count / (query_count * candidate_count)
            if query_count and candidate_count else 0.0
        ),
        "component_query_size": distribution(c["query_count"] for c in components),
        "component_candidate_size": distribution(c["candidate_count"] for c in components),
        "giant_component": {
            "query_count": giant["query_count"],
            "candidate_count": giant["candidate_count"],
            "edge_count": giant["edge_count"],
            "query_ratio": giant["query_count"] / query_count if query_count else 0.0,
            "candidate_ratio": (
                giant["candidate_count"] / candidate_count if candidate_count else 0.0
            ),
            "edge_ratio": giant["edge_count"] / edge_count if edge_count else 0.0,
        },
        "components": components,
    }


def format_report(input_path: Path, report: dict[str, object]) -> str:
    counts = report["counts"]
    giant = report["giant_component"]
    query_degree = report["query_degree"]
    candidate_degree = report["candidate_degree"]
    reuse = report["candidate_reuse"]
    neighborhood = report["candidate_interaction_neighborhood"]
    neighborhood_size = neighborhood["size"]
    lines = [
        f"input: {input_path}",
        f"candidate arities: {report['candidate_arities']}",
        (
            f"graph: |Q|={counts['queries']}, candidate-bearing Q="
            f"{counts['candidate_bearing_queries']}, |S|={counts['candidates']}, "
            f"|E|={counts['edges']}, components={counts['components']}"
        ),
        f"bipartite density: {report['bipartite_density']:.6f}",
        (
            "query degree: "
            f"min={query_degree['min']}, mean={query_degree['mean']:.2f}, "
            f"median={query_degree['median']}, p90={query_degree['p90']:.1f}, "
            f"max={query_degree['max']}"
        ),
        (
            "candidate degree: "
            f"min={candidate_degree['min']}, mean={candidate_degree['mean']:.2f}, "
            f"median={candidate_degree['median']}, p90={candidate_degree['p90']:.1f}, "
            f"max={candidate_degree['max']}"
        ),
        (
            f"candidate degree=1: {reuse['degree_1_count']} "
            f"({reuse['degree_1_ratio']:.2%})"
        ),
        "candidate degree histogram (degree: count/ratio): "
        + ", ".join(
            f"{bucket['degree']}: {bucket['candidate_count']}/{bucket['candidate_ratio']:.2%}"
            for bucket in report["candidate_degree_histogram"]
        ),
        (
            "interaction neighborhood |N(s)| (includes s): "
            f"min={neighborhood_size['min']}, mean={neighborhood_size['mean']:.2f}, "
            f"median={neighborhood_size['median']}, p90={neighborhood_size['p90']:.1f}, "
            f"p95={neighborhood_size['p95']:.1f}, p99={neighborhood_size['p99']:.1f}, "
            f"max={neighborhood_size['max']}"
        ),
        (
            "candidate interaction graph: "
            f"edges={neighborhood['candidate_interaction_edges']}, "
            f"density={neighborhood['candidate_interaction_density']:.6f}"
        ),
        (
            "giant component: "
            f"Q={giant['query_count']} ({giant['query_ratio']:.2%}), "
            f"S={giant['candidate_count']} ({giant['candidate_ratio']:.2%}), "
            f"E={giant['edge_count']} ({giant['edge_ratio']:.2%})"
        ),
        "component sizes (Q, S, E): "
        + ", ".join(
            f"({c['query_count']}, {c['candidate_count']}, {c['edge_count']})"
            for c in report["components"]
        ),
        "top candidate hubs: "
        + ", ".join(
            f"{hub['table']}({','.join(hub['columns'])}):{hub['degree']}"
            for hub in report["top_candidate_hubs"]
        ),
        "high-degree peeling (retain degree <= k; k: removed-S, components, giant-Q):",
        *(
            f"  {point['max_retained_degree_k']}: "
            f"{point['removed_candidate_ratio']:.2%}, "
            f"{point['component_count']}, {point['giant_query_ratio']:.2%}"
            for point in report["high_degree_peeling_curve"]
        ),
    ]
    return "\n".join(lines)


def parse_arities(raw: str) -> tuple[int, ...]:
    try:
        arities = tuple(sorted({int(value) for value in raw.split(",")}))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("arities must be comma-separated integers") from exc
    if not arities or any(arity < 2 for arity in arities):
        raise argparse.ArgumentTypeError("candidate arities must all be at least 2")
    return arities


def write_csv_reports(prefix: Path, report: dict[str, object]) -> None:
    prefix.parent.mkdir(parents=True, exist_ok=True)
    outputs = (
        (prefix.with_name(prefix.name + "_candidate_degree_histogram.csv"),
         report["candidate_degree_histogram"]),
        (prefix.with_name(prefix.name + "_high_degree_peeling.csv"),
         report["high_degree_peeling_curve"]),
        (prefix.with_name(prefix.name + "_interaction_neighborhood_histogram.csv"),
         report["candidate_interaction_neighborhood"]["histogram"]),
        (prefix.with_name(prefix.name + "_interaction_neighborhood_by_degree.csv"),
         report["candidate_interaction_neighborhood"]["by_candidate_degree"]),
    )
    for path, rows in outputs:
        if not rows:
            continue
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="workload SQL file")
    parser.add_argument("--arities", type=parse_arities, default=(2,), help="e.g. 2 or 2,3")
    parser.add_argument("--json", type=Path, help="write the complete report as JSON")
    parser.add_argument(
        "--csv-prefix", type=Path,
        help="write histogram, peeling, and interaction-neighborhood CSV tables",
    )
    args = parser.parse_args()

    report = analyze(parse_queries(args.input), args.arities)
    print(format_report(args.input, report))
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if args.csv_prefix:
        write_csv_reports(args.csv_prefix, report)


if __name__ == "__main__":
    main()
