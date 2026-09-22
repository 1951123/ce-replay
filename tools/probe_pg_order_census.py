#!/usr/bin/env python3
"""Probe PostgreSQL creation/OID-order behavior on Census query.184.

The two MCV statistics were selected because isolated v2 measurements give
radically different estimates for the query while both column sets apply.
Every regime rebuilds statistics with one ANALYZE.  Probe-owned objects are
removed in a finally block; the script refuses to start if the table already
has extended statistics, preventing accidental interference with a deployment.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import psycopg


QUERY_ID = "query.184"
TABLE = "climate"
WHERE = (
    "dDepart >= 0 AND dDepart <= 2 AND iDisabl1 = 0 AND iEnglish = 0 "
    "AND iImmigr = 0 AND iLooking = 0 AND iMay75880 = 0 AND iRelat2 = 0 "
    "AND dRpincome >= 2 AND dRpincome <= 4 AND iRspouse = 1 "
    "AND dTravtime >= 0 AND dTravtime <= 4"
)
SELECT_SQL = f"SELECT * FROM {TABLE} WHERE {WHERE}"
COUNT_SQL = f"SELECT count(*) FROM {TABLE} WHERE {WHERE}"

STATS = {
    # PostgreSQL folds the Census loader's unquoted identifiers to lowercase.
    "good": ("idisabl1", "irspouse"),
    "bad": ("ddepart", "idisabl1"),
}
NAMES = {label: f"v3_order_probe_{label}" for label in STATS}


def qerror(estimate: int, actual: int) -> float:
    return max(estimate / actual, actual / max(estimate, 1))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=5432)
    parser.add_argument("--user", default="postgres")
    parser.add_argument("--password", default=None)
    parser.add_argument("--db", default="census")
    parser.add_argument("--target", type=int, default=1000)
    parser.add_argument("--repeats", type=int, default=3, help="coexistence trials per order")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    conn = psycopg.connect(
        host=args.host, port=args.port, user=args.user,
        password=args.password, dbname=args.db, autocommit=True,
    )
    cur = conn.cursor()

    def drop_probe_stats() -> None:
        for name in NAMES.values():
            cur.execute(f'DROP STATISTICS IF EXISTS "{name}"')

    def estimate() -> int:
        cur.execute(f"EXPLAIN (FORMAT JSON) {SELECT_SQL}")
        return int(cur.fetchone()[0][0]["Plan"]["Plan Rows"])

    def catalog() -> list[dict[str, object]]:
        cur.execute(
            "SELECT stxname, oid, ARRAY("
            " SELECT attname FROM pg_attribute"
            " WHERE attrelid=stxrelid AND attnum=ANY(stxkeys) ORDER BY attname"
            ") FROM pg_statistic_ext WHERE stxrelid=%s::regclass ORDER BY oid",
            (TABLE,),
        )
        return [
            {"name": name, "oid": oid, "columns": columns}
            for name, oid, columns in cur.fetchall()
        ]

    def create(label: str) -> None:
        name = NAMES[label]
        left, right = STATS[label]
        cur.execute(
            f'CREATE STATISTICS "{name}" (mcv) ON {left}, {right} FROM {TABLE}'
        )
        cur.execute(f'ALTER STATISTICS "{name}" SET STATISTICS {args.target}')

    def regime(name: str, order: tuple[str, ...], trial: int = 1) -> dict[str, object]:
        drop_probe_stats()
        for label in order:
            create(label)
        cur.execute(f"ANALYZE {TABLE}")
        value = estimate()
        return {
            "regime": name,
            "trial": trial,
            "creation_order": list(order),
            "estimate": value,
            "qerror": qerror(value, actual),
            "catalog_oid_order": catalog(),
        }

    try:
        existing = catalog()
        if existing:
            raise RuntimeError(
                "refusing to run: climate already has extended statistics: "
                + ", ".join(row["name"] for row in existing)
            )
        cur.execute(COUNT_SQL)
        actual = int(cur.fetchone()[0])

        # One natural baseline and two singleton controls establish each object's
        # isolated response under the same target used by coexistence regimes.
        cur.execute(f"ANALYZE {TABLE}")
        baseline_estimate = estimate()
        observations = [
            {
                "regime": "baseline",
                "trial": 1,
                "creation_order": [],
                "estimate": baseline_estimate,
                "qerror": qerror(baseline_estimate, actual),
                "catalog_oid_order": [],
            },
            regime("good_only", ("good",)),
            regime("bad_only", ("bad",)),
        ]
        for trial in range(1, args.repeats + 1):
            observations.append(regime("good_then_bad", ("good", "bad"), trial))
            observations.append(regime("bad_then_good", ("bad", "good"), trial))
        result = {
            "postgres_version": conn.info.server_version,
            "query_id": QUERY_ID,
            "sql": COUNT_SQL,
            "actual": actual,
            "statistics_target": args.target,
            "coexistence_repeats": args.repeats,
            "statistics": {key: list(value) for key, value in STATS.items()},
            "observations": observations,
        }
        rendered = json.dumps(result, indent=2)
        print(rendered)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered + "\n", encoding="utf-8")
    finally:
        drop_probe_stats()
        conn.close()


if __name__ == "__main__":
    main()
