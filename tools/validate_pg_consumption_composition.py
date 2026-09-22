#!/usr/bin/env python3
"""Orthogonal PG MCV validation: consumption by payload ablation, composition by ratios."""

from __future__ import annotations

import argparse
import itertools
import json
import statistics
from pathlib import Path

import psycopg


TABLE = "climate"
QUERIES = {
    "q184": {
        "qid": "query.184", "actual": 13,
        "where": (
            "ddepart>=0 AND ddepart<=2 AND idisabl1=0 AND ienglish=0 AND iimmigr=0 "
            "AND ilooking=0 AND imay75880=0 AND irelat2=0 AND drpincome>=2 "
            "AND drpincome<=4 AND irspouse=1 AND dtravtime>=0 AND dtravtime<=4"
        ),
    },
    "q62": {
        "qid": "query.62", "actual": 45,
        "where": (
            "iclass>=0 AND iclass<=1 AND dincome3=0 AND irelat2>=0 AND irelat2<=1 "
            "AND irspouse=1 AND irvetserv=0 AND dtravtime=0 AND ivietnam=0 AND iwork89=0"
        ),
    },
    "q274": {
        "qid": "query.274", "actual": 470,
        "where": (
            "dage>=1 AND dage<=7 AND iclass>=0 AND iclass<=1 AND dhour89>=1 "
            "AND dhour89<=3 AND imeans=0 AND doccup>=0 AND doccup<=5 AND drearning=0 "
            "AND iremplpar>=0 AND iremplpar<=223 AND iriders>=0 AND iriders<=1 "
            "AND irownchld=0 AND irspouse>=0 AND irspouse<=6 AND ivietnam=0 "
            "AND dweek89>=1 AND dweek89<=2 AND iwork89>=0 AND iwork89<=1"
        ),
    },
}

# Experiment A: one fully overlapping chain and one disjoint pair.
CONSUMPTION = [
    ("q184_overlap", "q184", [
        ("good", ("idisabl1", "irspouse")),
        ("middle", ("drpincome", "idisabl1")),
        ("bad", ("ddepart", "idisabl1")),
    ]),
    ("q274_disjoint", "q274", [
        ("left", ("drearning", "dweek89")),
        ("right", ("dhour89", "imeans")),
    ]),
]

# Experiment B: three disjoint pairs with very different singleton responses.
COMPOSITION = [
    ("q184_disjoint", "q184", [
        ("a", ("idisabl1", "irspouse")),
        ("b", ("ienglish", "iimmigr")),
    ]),
    ("q62_disjoint", "q62", [
        ("a", ("irspouse", "iwork89")),
        ("b", ("dtravtime", "iclass")),
    ]),
    ("q274_disjoint", "q274", [
        ("a", ("drearning", "dweek89")),
        ("b", ("dhour89", "imeans")),
    ]),
]


def deviation(observed: float, predicted: float) -> float:
    return max(observed / max(predicted, 1e-12), predicted / max(observed, 1e-12))


def simulate_greedy(stats, predicate_columns):
    """PG16 MCV simplification for ordinary single-column Census clauses."""
    remaining = set(predicate_columns)
    available = list(enumerate(stats))  # list order is OID order
    sequence = []
    while True:
        matches = []
        for oid_order, (label, columns) in available:
            covered = remaining & set(columns)
            if len(covered) >= 2:
                matches.append((len(covered), -len(columns), -oid_order, label, covered))
        if not matches:
            break
        _, _, _, label, covered = max(matches)
        sequence.append(label)
        remaining -= covered
    return sequence


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
    prefix = "v3_orth_probe_"

    def clean():
        cur.execute("SELECT stxname FROM pg_statistic_ext WHERE stxname LIKE %s", (prefix + "%",))
        for (name,) in cur.fetchall():
            cur.execute(f'DROP STATISTICS IF EXISTS "{name}"')

    def create(tag, label, columns):
        name = prefix + tag + "_" + label
        cur.execute(f'CREATE STATISTICS "{name}" (mcv) ON {", ".join(columns)} FROM {TABLE}')
        cur.execute(f'ALTER STATISTICS "{name}" SET STATISTICS {args.target}')
        cur.execute("SELECT oid FROM pg_statistic_ext WHERE stxname=%s", (name,))
        return name, int(cur.fetchone()[0])

    def estimate(query):
        cur.execute(f"EXPLAIN (FORMAT JSON) SELECT * FROM {TABLE} WHERE {query['where']}")
        return int(cur.fetchone()[0][0]["Plan"]["Plan Rows"])

    try:
        cur.execute("SELECT stxname FROM pg_statistic_ext WHERE stxrelid=%s::regclass", (TABLE,))
        existing = [x[0] for x in cur.fetchall()]
        if existing:
            raise RuntimeError("refusing to run with existing extstats: " + ", ".join(existing))

        # A: build once, then mask/restore payloads without another ANALYZE.
        consumption_results = []
        for tag, qkey, stats in CONSUMPTION:
            query = QUERIES[qkey]
            clean()
            objects = [(*create(tag, label, columns), label, columns) for label, columns in stats]
            cur.execute(f"ANALYZE {TABLE}")
            cur.execute("DROP TABLE IF EXISTS v3_orth_payload_backup")
            cur.execute(
                "CREATE TEMP TABLE v3_orth_payload_backup AS "
                "SELECT stxoid, stxdmcv FROM pg_statistic_ext_data WHERE stxoid=ANY(%s)",
                ([obj[1] for obj in objects],),
            )

            def restore():
                cur.execute(
                    "UPDATE pg_statistic_ext_data d SET stxdmcv=b.stxdmcv "
                    "FROM v3_orth_payload_backup b WHERE d.stxoid=b.stxoid"
                )

            restore()
            full = estimate(query)
            ablations = []
            for name, oid, label, _ in objects:
                restore()
                cur.execute("UPDATE pg_statistic_ext_data SET stxdmcv=NULL WHERE stxoid=%s", (oid,))
                ablated = estimate(query)
                ablations.append({
                    "masked": label, "estimate": ablated,
                    "changed_from_full": ablated != full,
                    "deviation_from_full": deviation(ablated, full),
                })
            restore()
            predicate_columns = set().union(*(set(columns) for _, columns in stats))
            predicted_sequence = simulate_greedy(stats, predicate_columns)
            consumption_results.append({
                "scenario": tag, "qid": query["qid"],
                "oid_order": [label for label, _ in stats],
                "predicted_sequence": predicted_sequence,
                "full_estimate": full, "payload_ablations": ablations,
            })

        # B: same-sample baseline/singleton/coexistence via payload masks.
        composition_results = []
        for tag, qkey, stats in COMPOSITION:
            query = QUERIES[qkey]
            trials = []
            for order in itertools.permutations(stats):
                clean()
                objects = []
                for label, columns in order:
                    name, oid = create(tag, label, columns)
                    objects.append((name, oid, label))
                cur.execute(f"ANALYZE {TABLE}")
                cur.execute("DROP TABLE IF EXISTS v3_orth_payload_backup_b")
                cur.execute(
                    "CREATE TEMP TABLE v3_orth_payload_backup_b AS "
                    "SELECT stxoid, stxdmcv FROM pg_statistic_ext_data WHERE stxoid=ANY(%s)",
                    ([obj[1] for obj in objects],),
                )

                def set_payloads(keep_labels):
                    cur.execute(
                        "UPDATE pg_statistic_ext_data d SET stxdmcv=b.stxdmcv "
                        "FROM v3_orth_payload_backup_b b WHERE d.stxoid=b.stxoid"
                    )
                    for _, oid, label in objects:
                        if label not in keep_labels:
                            cur.execute(
                                "UPDATE pg_statistic_ext_data SET stxdmcv=NULL WHERE stxoid=%s",
                                (oid,),
                            )
                    return estimate(query)

                baseline = set_payloads(set())
                singleton = {label: set_payloads({label}) for label, _ in stats}
                observed = set_payloads({label for label, _ in stats})
                ratio_prediction = singleton["a"] * singleton["b"] / baseline
                trials.append({
                    "order": [label for label, _ in order],
                    "same_sample_baseline": baseline,
                    "same_sample_singletons": singleton,
                    "observed": observed,
                    "ratio_prediction": ratio_prediction,
                    "deviation_factor": deviation(observed, ratio_prediction),
                    "relative_error": abs(observed - ratio_prediction) / observed,
                })
            composition_results.append({
                "scenario": tag, "qid": query["qid"], "actual": query["actual"],
                "trials": trials,
            })

        deviations = [x["deviation_factor"] for r in composition_results for x in r["trials"]]
        result = {
            "postgres_version": conn.info.server_version,
            "statistics_target": args.target,
            "experiment_a_consumption": consumption_results,
            "experiment_b_composition": composition_results,
            "composition_summary": {
                "observations": len(deviations),
                "median_deviation_factor": statistics.median(deviations),
                "max_deviation_factor": max(deviations),
                "within_10_percent_factor": sum(value <= 1.1 for value in deviations),
                "within_20_percent_factor": sum(value <= 1.2 for value in deviations),
            },
        }
        rendered = json.dumps(result, indent=2)
        print(rendered)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered + "\n", encoding="utf-8")
    finally:
        clean()
        conn.close()


if __name__ == "__main__":
    main()
