#!/usr/bin/env python3
"""CE-Replay-IR-v0 for PG16 base restrictions plus two-column MCV GreedyCover.

The instrument phase performs one ANALYZE with all probe MCVs, then extracts
same-sample baseline and singleton cardinality responses by masking catalog
payloads.  Replay is pure Python: it reruns GreedyCover for a hypothetical
selected subset and composes selected atomic responses in cardinality space.
Fresh PostgreSQL EXPLAIN calls are used only as a validation oracle.
"""

from __future__ import annotations

import argparse
import itertools
import json
import statistics
from pathlib import Path

import psycopg


TABLE = "climate"
QUERY_ID = "query.184"
ACTUAL = 13
WHERE = (
    "ddepart>=0 AND ddepart<=2 AND idisabl1=0 AND ienglish=0 AND iimmigr=0 "
    "AND ilooking=0 AND imay75880=0 AND irelat2=0 AND drpincome>=2 "
    "AND drpincome<=4 AND irspouse=1 AND dtravtime>=0 AND dtravtime<=4"
)
PREDICATE_COLUMNS = {
    "ddepart", "idisabl1", "ienglish", "iimmigr", "ilooking", "imay75880",
    "irelat2", "drpincome", "irspouse", "dtravtime",
}

# Creation order is the physical OID order.  The first three conflict through
# idisabl1; the last two form independent clause groups.
CANDIDATES = [
    ("good", ("idisabl1", "irspouse")),
    ("middle", ("drpincome", "idisabl1")),
    ("bad", ("ddepart", "idisabl1")),
    ("independent_1", ("ienglish", "iimmigr")),
    ("independent_2", ("ilooking", "imay75880")),
]


def greedy_cover(selected: set[str], candidates: list[dict], predicate_columns: set[str]):
    """Replay PG16 choose_best_statistics for simple non-expression clauses."""
    remaining = set(predicate_columns)
    sequence = []
    while True:
        choices = []
        for candidate in candidates:
            if candidate["id"] not in selected:
                continue
            covered = remaining & set(candidate["columns"])
            if len(covered) < 2:
                continue
            # max coverage, min total keys, then min OID rank
            score = (len(covered), -len(candidate["columns"]), -candidate["oid_rank"])
            choices.append((score, candidate, covered))
        if not choices:
            break
        _, winner, covered = max(choices, key=lambda item: item[0])
        sequence.append(winner["id"])
        remaining -= covered
    return sequence


def replay(ir: dict, selected: set[str]) -> dict:
    sequence = greedy_cover(selected, ir["candidates"], set(ir["predicate_columns"]))
    estimate = float(ir["baseline_estimate"])
    by_id = {candidate["id"]: candidate for candidate in ir["candidates"]}
    for candidate_id in sequence:
        estimate *= by_id[candidate_id]["cardinality_ratio"]
    return {"selected_sequence": sequence, "estimate": estimate}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=5432)
    parser.add_argument("--user", default="postgres")
    parser.add_argument("--password", default=None)
    parser.add_argument("--db", default="census")
    parser.add_argument("--target", type=int, default=1000)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    conn = psycopg.connect(host=args.host, port=args.port, user=args.user,
                           password=args.password, dbname=args.db, autocommit=True)
    cur = conn.cursor()
    prefix = "v3_replay_v0_"

    def clean():
        cur.execute("SELECT stxname FROM pg_statistic_ext WHERE stxname LIKE %s", (prefix + "%",))
        for (name,) in cur.fetchall():
            cur.execute(f'DROP STATISTICS IF EXISTS "{name}"')

    def estimate():
        cur.execute(f"EXPLAIN (FORMAT JSON) SELECT * FROM {TABLE} WHERE {WHERE}")
        return int(cur.fetchone()[0][0]["Plan"]["Plan Rows"])

    try:
        cur.execute("SELECT stxname FROM pg_statistic_ext WHERE stxrelid=%s::regclass", (TABLE,))
        existing = [row[0] for row in cur.fetchall()]
        if existing:
            raise RuntimeError("refusing to run with existing climate extstats: " + ", ".join(existing))
        cur.execute(f"SELECT count(*) FROM {TABLE} WHERE {WHERE}")
        if int(cur.fetchone()[0]) != ACTUAL:
            raise RuntimeError("query truth mismatch")

        objects = []
        for rank, (candidate_id, columns) in enumerate(CANDIDATES):
            name = prefix + candidate_id
            cur.execute(f'CREATE STATISTICS "{name}" (mcv) ON {", ".join(columns)} FROM {TABLE}')
            cur.execute(f'ALTER STATISTICS "{name}" SET STATISTICS {args.target}')
            cur.execute("SELECT oid FROM pg_statistic_ext WHERE stxname=%s", (name,))
            objects.append({
                "id": candidate_id, "name": name, "oid": int(cur.fetchone()[0]),
                "oid_rank": rank, "columns": list(columns),
            })
        cur.execute(f"ANALYZE {TABLE}")
        cur.execute(
            "CREATE TEMP TABLE v3_replay_payload_backup AS "
            "SELECT stxoid, stxdmcv FROM pg_statistic_ext_data WHERE stxoid=ANY(%s)",
            ([obj["oid"] for obj in objects],),
        )

        def set_keep(keep: set[str]):
            cur.execute(
                "UPDATE pg_statistic_ext_data d SET stxdmcv=b.stxdmcv "
                "FROM v3_replay_payload_backup b WHERE d.stxoid=b.stxoid"
            )
            for obj in objects:
                if obj["id"] not in keep:
                    cur.execute(
                        "UPDATE pg_statistic_ext_data SET stxdmcv=NULL WHERE stxoid=%s",
                        (obj["oid"],),
                    )
            return estimate()

        baseline = set_keep(set())
        for obj in objects:
            singleton = set_keep({obj["id"]})
            obj["singleton_estimate"] = singleton
            obj["cardinality_ratio"] = singleton / baseline

        ir = {
            "ir_version": "CE-Replay-IR-v0",
            "scope": "PG16 single-table AND restrictions; two-column MCV",
            "postgres_version": conn.info.server_version,
            "query_id": QUERY_ID,
            "table": TABLE,
            "where": WHERE,
            "predicate_columns": sorted(PREDICATE_COLUMNS),
            "statistics_target": args.target,
            "baseline_estimate": baseline,
            "consumption_semantics": {
                "operation": "GreedyCover",
                "eligibility": "covers_at_least_2_remaining_columns",
                "priority": ["max_covered", "min_total_keys", "min_oid_rank"],
                "transition": "remove_covered_columns",
            },
            "composition_semantics": {
                "operation": "multiply_cardinality_ratios",
                "formula": "N0 * product(Ns/N0 for s in greedy_sequence)",
            },
            "candidates": objects,
        }

        validations = []
        ids = [candidate_id for candidate_id, _ in CANDIDATES]
        for size in range(len(ids) + 1):
            for subset_tuple in itertools.combinations(ids, size):
                selected = set(subset_tuple)
                predicted = replay(ir, selected)
                observed = set_keep(selected)
                predicted_value = predicted["estimate"]
                relative_error = abs(predicted_value - observed) / max(observed, 1)
                validations.append({
                    "selected": list(subset_tuple),
                    "replayed_sequence": predicted["selected_sequence"],
                    "replayed_estimate": predicted_value,
                    "fresh_pg_estimate": observed,
                    "rounded_exact": round(predicted_value) == observed,
                    "relative_error": relative_error,
                    "deviation_factor": max(
                        predicted_value / max(observed, 1),
                        observed / max(predicted_value, 1e-12),
                    ),
                })

        errors = [row["relative_error"] for row in validations]
        result = {
            "ir": ir,
            "validation_summary": {
                "designs": len(validations),
                "rounded_exact": sum(row["rounded_exact"] for row in validations),
                "within_1_percent": sum(error <= 0.01 for error in errors),
                "within_5_percent": sum(error <= 0.05 for error in errors),
                "median_relative_error": statistics.median(errors),
                "max_relative_error": max(errors),
                "max_deviation_factor": max(row["deviation_factor"] for row in validations),
            },
            "validations": validations,
        }
        rendered = json.dumps(result, indent=2)
        print(json.dumps(result["validation_summary"], indent=2))
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered + "\n", encoding="utf-8")
    finally:
        clean()
        conn.close()


if __name__ == "__main__":
    main()
