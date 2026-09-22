#!/usr/bin/env python3
"""Payload-driven CE-Replay-IR-v1 for Census query.184.

Unlike v0, this does not measure the response of a query with each extended
statistic enabled.  It serializes pg_mcv_list_items, computes PostgreSQL's MCV
selectivity correction from the payload, and replays every candidate subset.
PostgreSQL EXPLAIN is used for design-independent simple-selectivity context
during instrumentation and as the final validation oracle only.
"""

from __future__ import annotations

import argparse
import itertools
import json
import re
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
PREDICATES = {
    "ddepart": {"sql": "ddepart>=0 AND ddepart<=2", "lo": 0, "hi": 2},
    "drpincome": {"sql": "drpincome>=2 AND drpincome<=4", "lo": 2, "hi": 4},
    "dtravtime": {"sql": "dtravtime>=0 AND dtravtime<=4", "lo": 0, "hi": 4},
    "idisabl1": {"sql": "idisabl1=0", "eq": 0},
    "ienglish": {"sql": "ienglish=0", "eq": 0},
    "iimmigr": {"sql": "iimmigr=0", "eq": 0},
    "ilooking": {"sql": "ilooking=0", "eq": 0},
    "imay75880": {"sql": "imay75880=0", "eq": 0},
    "irelat2": {"sql": "irelat2=0", "eq": 0},
    "irspouse": {"sql": "irspouse=1", "eq": 1},
}
CANDIDATES = [
    ("good", ("idisabl1", "irspouse")),
    ("middle", ("drpincome", "idisabl1")),
    ("bad", ("ddepart", "idisabl1")),
    ("independent_1", ("ienglish", "iimmigr")),
    ("independent_2", ("ilooking", "imay75880")),
]


def as_text(value):
    return value.decode("ascii") if isinstance(value, bytes) else value


def greedy_cover(selected: set[str], candidates: list[dict]) -> list[str]:
    remaining = set(PREDICATES)
    sequence = []
    while True:
        choices = []
        for candidate in candidates:
            if candidate["id"] not in selected:
                continue
            covered = remaining & set(candidate["columns"])
            if len(covered) >= 2:
                score = (len(covered), -len(candidate["columns"]), -candidate["oid_rank"])
                choices.append((score, candidate, covered))
        if not choices:
            return sequence
        _, winner, covered = max(choices, key=lambda item: item[0])
        sequence.append(winner["id"])
        remaining -= covered


def matches(value: str | None, is_null: bool, predicate: dict) -> bool:
    if is_null:
        return False
    number = int(value)
    if "eq" in predicate:
        return number == predicate["eq"]
    return predicate["lo"] <= number <= predicate["hi"]


def combine(simple_sel: float, mcv_sel: float, mcv_base_sel: float,
            mcv_total_sel: float) -> float:
    # PostgreSQL src/backend/statistics/mcv.c:mcv_combine_selectivities.
    other_sel = min(1.0, max(0.0, simple_sel - mcv_base_sel))
    other_sel = min(other_sel, 1.0 - mcv_total_sel)
    return min(1.0, max(0.0, mcv_sel + other_sel))


def replay(ir: dict, selected: set[str]) -> dict:
    sequence = greedy_cover(selected, ir["candidates"])
    estimate = float(ir["baseline_estimate"])
    by_id = {candidate["id"]: candidate for candidate in ir["candidates"]}
    for candidate_id in sequence:
        candidate = by_id[candidate_id]
        estimate *= candidate["native_stat_selectivity"] / candidate["simple_selectivity"]
    return {"selected_sequence": sequence, "estimate": estimate}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=5432)
    parser.add_argument("--user", default="postgres")
    parser.add_argument("--password", default=None)
    parser.add_argument("--db", default="census")
    parser.add_argument("--target", type=int, default=1000)
    parser.add_argument("--native", action="store_true",
                        help="use ce_replay_native's unrounded Plan.plan_rows oracle")
    parser.add_argument("--instrumented-native", action="store_true",
                        help="read pre-clamp rows and MCV-node values from patched PG notices")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    conn = psycopg.connect(host=args.host, port=args.port, user=args.user,
                           password=args.password, dbname=args.db, autocommit=True)
    cur = conn.cursor()
    prefix = "v3_replay_v1_"
    native_notices = []
    last_native_trace = []
    if args.instrumented_native:
        conn.add_notice_handler(lambda diagnostic: native_notices.append(
            diagnostic.message_primary))

    def clean():
        cur.execute("SELECT stxname FROM pg_statistic_ext WHERE stxname LIKE %s", (prefix + "%",))
        for (name,) in cur.fetchall():
            name = as_text(name)
            cur.execute(f'DROP STATISTICS IF EXISTS "{name}"')

    if args.native:
        cur.execute(
            "CREATE FUNCTION pg_temp.ce_native_plan_rows(text) RETURNS double precision "
            "AS '$libdir/ce_replay_native', 'ce_native_plan_rows' "
            "LANGUAGE C STRICT VOLATILE PARALLEL UNSAFE"
        )

    def estimate(where: str = WHERE) -> float:
        nonlocal last_native_trace
        query = f"SELECT * FROM {TABLE} WHERE {where}"
        if args.native:
            cur.execute("SELECT pg_temp.ce_native_plan_rows(%s)", (query,))
            return float(cur.fetchone()[0])
        if args.instrumented_native:
            native_notices.clear()
            cur.execute("EXPLAIN (FORMAT JSON) " + query)
            cur.fetchone()
            last_native_trace = list(native_notices)
            raw = [message for message in native_notices
                   if message.startswith("CE_REPLAY_RAW_ROWS")]
            if len(raw) != 1:
                raise RuntimeError(f"expected one raw-row notice, got: {raw}")
            match = re.search(r" rows=([^ ]+)", raw[0])
            return float(match.group(1))
        cur.execute("EXPLAIN (FORMAT JSON) " + query)
        return float(cur.fetchone()[0][0]["Plan"]["Plan Rows"])

    try:
        cur.execute("SELECT stxname FROM pg_statistic_ext WHERE stxrelid=%s::regclass", (TABLE,))
        existing = [as_text(row[0]) for row in cur.fetchall()]
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
            oid = int(cur.fetchone()[0])
            # pg_mcv_list_items values follow stxkeys/attribute-number order,
            # which need not match the textual CREATE STATISTICS order.
            cur.execute(
                "SELECT a.attname FROM pg_statistic_ext s "
                "CROSS JOIN LATERAL unnest(s.stxkeys::smallint[]) WITH ORDINALITY k(attnum, ord) "
                "JOIN pg_attribute a ON a.attrelid=s.stxrelid AND a.attnum=k.attnum "
                "WHERE s.oid=%s ORDER BY k.ord",
                (oid,),
            )
            payload_columns = [as_text(row[0]) for row in cur.fetchall()]
            objects.append({"id": candidate_id, "name": name,
                            "oid": oid, "oid_rank": rank,
                            "columns": list(columns),
                            "payload_columns": payload_columns})
        cur.execute(f"ANALYZE {TABLE}")
        cur.execute(
            "CREATE TEMP TABLE v3_replay_v1_backup AS "
            "SELECT stxoid, stxdmcv FROM pg_statistic_ext_data WHERE stxoid=ANY(%s)",
            ([obj["oid"] for obj in objects],),
        )

        def set_keep(keep: set[str]) -> int:
            cur.execute(
                "UPDATE pg_statistic_ext_data d SET stxdmcv=b.stxdmcv "
                "FROM v3_replay_v1_backup b WHERE d.stxoid=b.stxoid"
            )
            for obj in objects:
                if obj["id"] not in keep:
                    cur.execute("UPDATE pg_statistic_ext_data SET stxdmcv=NULL WHERE stxoid=%s",
                                (obj["oid"],))
            return estimate()

        # Design-independent context: no extended-statistics payload is active.
        baseline = set_keep(set())
        if args.instrumented_native:
            relation_rows = estimate("TRUE")
        elif args.native:
            cur.execute("SELECT pg_temp.ce_native_plan_rows(%s)",
                        (f"SELECT * FROM {TABLE}",))
            relation_rows = float(cur.fetchone()[0])
        else:
            cur.execute(f"EXPLAIN (FORMAT JSON) SELECT * FROM {TABLE}")
            relation_rows = float(cur.fetchone()[0][0]["Plan"]["Plan Rows"])

        for obj in objects:
            group_where = " AND ".join(PREDICATES[column]["sql"] for column in obj["columns"])
            simple_rows = estimate(group_where)
            obj["simple_selectivity"] = simple_rows / relation_rows

            cur.execute(
                "SELECT pg_column_size(stxdmcv) FROM v3_replay_v1_backup WHERE stxoid=%s",
                (obj["oid"],),
            )
            obj["storage_cost_bytes"] = int(cur.fetchone()[0])
            cur.execute(
                "SELECT values, nulls, frequency, base_frequency "
                "FROM pg_mcv_list_items((SELECT stxdmcv FROM v3_replay_v1_backup WHERE stxoid=%s))",
                (obj["oid"],),
            )
            payload = []
            mcv_sel = mcv_base_sel = mcv_total_sel = 0.0
            for values, nulls, frequency, base_frequency in cur.fetchall():
                values = [as_text(value) if value is not None else None
                          for value in values]
                frequency = float(frequency)
                base_frequency = float(base_frequency)
                item_matches = all(
                    matches(values[i], nulls[i], PREDICATES[column])
                    for i, column in enumerate(obj["payload_columns"])
                )
                payload.append({"values": values, "nulls": nulls,
                                "frequency": frequency,
                                "base_frequency": base_frequency})
                mcv_total_sel += frequency
                if item_matches:
                    mcv_sel += frequency
                    mcv_base_sel += base_frequency
            obj["mcv_payload"] = payload
            obj["mcv_selectivity"] = mcv_sel
            obj["mcv_base_selectivity"] = mcv_base_sel
            obj["mcv_total_selectivity"] = mcv_total_sel
            obj["native_stat_selectivity"] = combine(
                obj["simple_selectivity"], mcv_sel, mcv_base_sel, mcv_total_sel)
            obj["correction_ratio"] = (
                obj["native_stat_selectivity"] / obj["simple_selectivity"])

        ir = {
            "ir_version": "CE-Replay-IR-v1-A",
            "scope": "PG16 single-table AND restrictions; integer two-column MCV",
            "postgres_version": conn.info.server_version,
            "query_id": QUERY_ID,
            "table": TABLE,
            "where": WHERE,
            "predicate_context": PREDICATES,
            "statistics_target": args.target,
            "relation_rows": relation_rows,
            "baseline_estimate": baseline,
            "consumption_operation": "PG16 GreedyCover",
            "numeric_operation": "PG16 mcv_combine_selectivities over serialized payload",
            "uses_singleton_extstat_measurements": False,
            "oracle": ("instrumented_pre_clamp_rows" if args.instrumented_native
                       else "native_plan_rows" if args.native
                       else "explain_integer_plan_rows"),
            "candidates": objects,
        }

        validations = []
        ids = [candidate_id for candidate_id, _ in CANDIDATES]
        for size in range(len(ids) + 1):
            for subset_tuple in itertools.combinations(ids, size):
                selected = set(subset_tuple)
                predicted = replay(ir, selected)
                observed = set_keep(selected)
                observed_native_trace = (list(last_native_trace)
                                         if args.instrumented_native else [])
                error = abs(predicted["estimate"] - observed) / max(observed, 1)
                validations.append({
                    "selected": list(subset_tuple),
                    "replayed_sequence": predicted["selected_sequence"],
                    "replayed_estimate": predicted["estimate"],
                    "fresh_pg_estimate": observed,
                    "native_trace": observed_native_trace,
                    "rounded_exact": round(predicted["estimate"]) == round(observed),
                    "floating_point_match": error <= 1e-12,
                    "relative_error": error,
                    "deviation_factor": max(predicted["estimate"] / max(observed, 1),
                                            observed / max(predicted["estimate"], 1e-12)),
                })
        errors = [row["relative_error"] for row in validations]
        result = {
            "ir": ir,
            "validation_summary": {
                "designs": len(validations),
                "rounded_exact": sum(row["rounded_exact"] for row in validations),
                "floating_point_matches": sum(row["floating_point_match"] for row in validations),
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
