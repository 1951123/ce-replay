#!/usr/bin/env python3
"""Falsification pilot for PostgreSQL first-applicable singleton reconstruction.

For each scenario, measure every candidate alone, then create the same candidate
set in several orders.  The parameter-free prediction is the singleton estimate
of the first-created candidate.  Results include multiplicative deviation.
"""

from __future__ import annotations

import argparse
import itertools
import json
import statistics
from pathlib import Path

import psycopg


TABLE = "climate"
SCENARIOS = [
    {
        "id": "q184_shared_anchor_3",
        "qid": "query.184",
        "actual": 13,
        "where": (
            "ddepart>=0 AND ddepart<=2 AND idisabl1=0 AND ienglish=0 AND iimmigr=0 "
            "AND ilooking=0 AND imay75880=0 AND irelat2=0 AND drpincome>=2 "
            "AND drpincome<=4 AND irspouse=1 AND dtravtime>=0 AND dtravtime<=4"
        ),
        # All three overlap on idisabl1; singleton responses span four orders of magnitude.
        "stats": [
            ("good", ("idisabl1", "irspouse")),
            ("middle", ("drpincome", "idisabl1")),
            ("bad", ("ddepart", "idisabl1")),
        ],
        "orders": "all",
    },
    {
        "id": "q221_triangle_3",
        "qid": "query.221",
        "actual": 1744,
        "where": "drearning=0 AND irelat1>=0 AND irelat1<=1 AND dweek89=2",
        # Pairwise-overlapping triangle, but no column is shared by all three stats.
        "stats": [
            ("ab", ("drearning", "dweek89")),
            ("ac", ("drearning", "irelat1")),
            ("bc", ("dweek89", "irelat1")),
        ],
        "orders": "all",
    },
    {
        "id": "q274_disjoint_2",
        "qid": "query.274",
        "actual": 470,
        "where": (
            "dage>=1 AND dage<=7 AND iclass>=0 AND iclass<=1 AND dhour89>=1 "
            "AND dhour89<=3 AND imeans=0 AND doccup>=0 AND doccup<=5 AND drearning=0 "
            "AND iremplpar>=0 AND iremplpar<=223 AND iriders>=0 AND iriders<=1 "
            "AND irownchld=0 AND irspouse>=0 AND irspouse<=6 AND ivietnam=0 "
            "AND dweek89>=1 AND dweek89<=2 AND iwork89>=0 AND iwork89<=1"
        ),
        # Deliberately disjoint column sets: tests whether PG can combine objects.
        "stats": [
            ("left", ("drearning", "dweek89")),
            ("right", ("dhour89", "imeans")),
        ],
        "orders": "all",
    },
]


def factor(left: int, right: int) -> float:
    return max(left / max(right, 1), right / max(left, 1))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=5432)
    parser.add_argument("--user", default="postgres")
    parser.add_argument("--password", default=None)
    parser.add_argument("--db", default="census")
    parser.add_argument("--target", type=int, default=1000)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    conn = psycopg.connect(
        host=args.host, port=args.port, user=args.user,
        password=args.password, dbname=args.db, autocommit=True,
    )
    cur = conn.cursor()
    prefix = "v3_first_probe_"

    def clean() -> None:
        cur.execute(
            "SELECT stxname FROM pg_statistic_ext "
            "WHERE stxrelid=%s::regclass AND stxname LIKE %s",
            (TABLE, prefix + "%"),
        )
        for (name,) in cur.fetchall():
            cur.execute(f'DROP STATISTICS IF EXISTS "{name}"')

    def estimate(where: str) -> int:
        cur.execute(f"EXPLAIN (FORMAT JSON) SELECT * FROM {TABLE} WHERE {where}")
        return int(cur.fetchone()[0][0]["Plan"]["Plan Rows"])

    def create(scenario_id: str, label: str, columns: tuple[str, ...]) -> str:
        name = prefix + scenario_id + "_" + label
        cur.execute(
            f'CREATE STATISTICS "{name}" (mcv) ON {", ".join(columns)} FROM {TABLE}'
        )
        cur.execute(f'ALTER STATISTICS "{name}" SET STATISTICS {args.target}')
        return name

    def oids(names: list[str]) -> list[dict[str, object]]:
        cur.execute(
            "SELECT stxname, oid FROM pg_statistic_ext WHERE stxname=ANY(%s) ORDER BY oid",
            (names,),
        )
        return [{"name": name, "oid": oid} for name, oid in cur.fetchall()]

    try:
        cur.execute(
            "SELECT stxname FROM pg_statistic_ext WHERE stxrelid=%s::regclass",
            (TABLE,),
        )
        existing = [row[0] for row in cur.fetchall()]
        if existing:
            raise RuntimeError("refusing to run with existing climate extstats: " + ", ".join(existing))

        results = []
        for scenario in SCENARIOS:
            where = scenario["where"]
            cur.execute(f"SELECT count(*) FROM {TABLE} WHERE {where}")
            actual = int(cur.fetchone()[0])
            if actual != scenario["actual"]:
                raise RuntimeError(
                    f"{scenario['qid']} truth mismatch: expected {scenario['actual']}, got {actual}"
                )

            clean()
            cur.execute(f"ANALYZE {TABLE}")
            baseline = estimate(where)
            singleton = {}
            for label, columns in scenario["stats"]:
                clean()
                create(scenario["id"], label, columns)
                cur.execute(f"ANALYZE {TABLE}")
                singleton[label] = estimate(where)

            labels = [label for label, _ in scenario["stats"]]
            columns_by_label = dict(scenario["stats"])
            observations = []
            for order in itertools.permutations(labels):
                clean()
                names = [create(scenario["id"], label, columns_by_label[label]) for label in order]
                cur.execute(f"ANALYZE {TABLE}")
                observed = estimate(where)
                predicted = singleton[order[0]]
                observations.append({
                    "creation_order": list(order),
                    "predicted_first_singleton": predicted,
                    "observed": observed,
                    "deviation_factor": factor(observed, predicted),
                    "within_20_percent": abs(observed - predicted) / max(predicted, 1) <= 0.20,
                    "within_2x": factor(observed, predicted) <= 2.0,
                    "catalog_oid_order": oids(names),
                })
            results.append({
                "scenario": scenario["id"],
                "qid": scenario["qid"],
                "overlap_structure": (
                    "shared_anchor" if "shared_anchor" in scenario["id"] else
                    "pairwise_triangle" if "triangle" in scenario["id"] else "disjoint"
                ),
                "actual": actual,
                "baseline": baseline,
                "statistics": {label: list(columns) for label, columns in scenario["stats"]},
                "singleton_estimates": singleton,
                "permutations": observations,
            })

        flat = [obs for result in results for obs in result["permutations"]]
        output = {
            "postgres_version": conn.info.server_version,
            "statistics_target": args.target,
            "hypothesis": "coexistence estimate equals first-created applicable singleton estimate",
            "summary": {
                "permutations": len(flat),
                "within_20_percent": sum(obs["within_20_percent"] for obs in flat),
                "within_2x": sum(obs["within_2x"] for obs in flat),
                "median_deviation_factor": statistics.median(
                    obs["deviation_factor"] for obs in flat
                ),
                "max_deviation_factor": max(obs["deviation_factor"] for obs in flat),
            },
            "scenarios": results,
        }
        rendered = json.dumps(output, indent=2)
        print(rendered)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered + "\n", encoding="utf-8")
    finally:
        clean()
        conn.close()


if __name__ == "__main__":
    main()
