#!/usr/bin/env python3
"""Physically deploy the final joint MCV design and measure sampling drift."""

from __future__ import annotations

import argparse
import json
import re
import statistics
import time
from pathlib import Path

import psycopg

from ce_replay_optimize_v1 import combine, item_matches, load_queries, qerror
from ce_replay_optimize_v2 import replay_with_ranks

RAW_RE = re.compile(r" rows=([^ ]+)")


def as_text(value):
    return value.decode("ascii") if isinstance(value, bytes) else value


def percentile(values, fraction):
    values = sorted(values)
    position = (len(values)-1)*fraction
    lo = int(position); hi = min(lo+1, len(values)-1)
    return values[lo] + (values[hi]-values[lo])*(position-lo)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workload", type=Path, required=True)
    parser.add_argument("--joint", type=Path, required=True)
    parser.add_argument("--queries", type=Path, required=True)
    parser.add_argument("--host", default="/tmp")
    parser.add_argument("--port", type=int, default=55432)
    parser.add_argument("--user", default="postgres")
    parser.add_argument("--db", default="census")
    parser.add_argument("--target", type=int, default=100)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    old = json.loads(args.workload.read_text())["workload_ir"]
    joint = json.loads(args.joint.read_text())
    queries = load_queries(args.queries)
    selected = set(joint["final_selected"])
    precedence = [cid for cid in joint["final_precedence"] if cid in selected]
    old_ranks = {cid: rank for rank, cid in enumerate(joint["final_precedence"])}
    frozen_rows = [replay_with_ranks(q, selected, old["candidates"], old_ranks)
                   for q in old["queries"]]
    frozen_losses = [qerror(rows, q["truth"]) for rows, q in zip(frozen_rows, old["queries"])]

    conn = psycopg.connect(host=args.host, port=args.port, user=args.user,
                           dbname=args.db, autocommit=True)
    cur = conn.cursor(); notices = []
    conn.add_notice_handler(lambda diagnostic: notices.append(diagnostic.message_primary))
    prefix = "v3_deploy_"

    def clean():
        cur.execute("SELECT stxname FROM pg_statistic_ext WHERE stxname LIKE %s", (prefix+"%",))
        for (name,) in cur.fetchall(): cur.execute(f'DROP STATISTICS IF EXISTS "{as_text(name)}"')

    def raw_rows(where):
        notices.clear(); cur.execute(f"EXPLAIN SELECT * FROM climate WHERE {where}")
        rows = [message for message in notices if message.startswith("CE_REPLAY_RAW_ROWS")]
        if len(rows) != 1: raise RuntimeError(rows)
        return float(RAW_RE.search(rows[0]).group(1))

    started = time.perf_counter()
    try:
        cur.execute("SELECT stxname FROM pg_statistic_ext WHERE stxrelid='climate'::regclass")
        existing = [as_text(row[0]) for row in cur.fetchall()]
        if existing: raise RuntimeError("existing climate extstats: "+", ".join(existing))
        deployed = []
        for rank, old_cid in enumerate(precedence):
            columns = old["candidates"][old_cid]["columns"]
            name = f"{prefix}{rank:04d}_c{old_cid}"
            cur.execute(f'CREATE STATISTICS "{name}" (mcv) ON {columns[0]}, {columns[1]} FROM climate')
            cur.execute(f'ALTER STATISTICS "{name}" SET STATISTICS {args.target}')
            cur.execute("SELECT oid FROM pg_statistic_ext WHERE stxname=%s", (name,))
            deployed.append({"id": old_cid, "oid": int(cur.fetchone()[0]),
                             "oid_rank": rank, "columns": columns})
        create_seconds = time.perf_counter()-started
        cur.execute("ANALYZE climate")
        analyze_seconds = time.perf_counter()-started-create_seconds
        cur.execute("CREATE TEMP TABLE v3_deploy_backup AS SELECT stxoid,stxdmcv "
                    "FROM pg_statistic_ext_data WHERE stxoid=ANY(%s)",
                    ([candidate["oid"] for candidate in deployed],))
        cur.execute("UPDATE pg_statistic_ext_data SET stxdmcv=NULL WHERE stxoid=ANY(%s)",
                    ([candidate["oid"] for candidate in deployed],))
        relation_rows = raw_rows("TRUE")

        new_queries = []
        by_old_id = {candidate["id"]: candidate for candidate in deployed}
        for candidate in deployed:
            cur.execute("SELECT a.attname FROM pg_statistic_ext s CROSS JOIN LATERAL "
                        "unnest(s.stxkeys::smallint[]) WITH ORDINALITY k(attnum,ord) "
                        "JOIN pg_attribute a ON a.attrelid=s.stxrelid AND a.attnum=k.attnum "
                        "WHERE s.oid=%s ORDER BY k.ord", (candidate["oid"],))
            candidate["payload_columns"] = [as_text(row[0]).lower() for row in cur.fetchall()]
            cur.execute("SELECT values,nulls,frequency,base_frequency FROM pg_mcv_list_items("
                        "(SELECT stxdmcv FROM v3_deploy_backup WHERE stxoid=%s))", (candidate["oid"],))
            candidate["payload"] = [{"values": [as_text(v) if v is not None else None for v in vals],
                                      "nulls": nulls, "frequency": float(freq),
                                      "base_frequency": float(base)}
                                     for vals,nulls,freq,base in cur.fetchall()]

        for qidx, source_query in enumerate(queries):
            baseline = raw_rows(source_query["where"])
            ids = [cid for cid in old["queries"][qidx]["candidate_ids"] if cid in selected]
            ratios = {}
            for cid in ids:
                candidate = by_old_id[cid]
                group_where = " AND ".join(
                    f"{column}{operator}{value}" for column in candidate["columns"]
                    for operator,value in source_query["predicates"][column])
                simple = raw_rows(group_where)/relation_rows
                mcv = base = total = 0.0
                for item in candidate["payload"]:
                    total += item["frequency"]
                    match = all(item_matches(item["values"][i],item["nulls"][i],
                                             source_query["predicates"][column])
                                for i,column in enumerate(candidate["payload_columns"]))
                    if match: mcv += item["frequency"]; base += item["base_frequency"]
                ratios[str(cid)] = combine(simple,mcv,base,total)/simple
            new_queries.append({"predicates": source_query["predicates"],
                                "truth": source_query["truth"], "baseline_rows": baseline,
                                "candidate_ids": ids, "correction_ratios": ratios})

        new_candidates = [dict(candidate) for candidate in old["candidates"]]
        for candidate in deployed:
            new_candidates[candidate["id"]]["oid_rank"] = candidate["oid_rank"]
        new_ranks = {candidate["id"]: candidate["oid_rank"] for candidate in deployed}
        replay_rows = [replay_with_ranks(q, selected, new_candidates, new_ranks)
                       for q in new_queries]

        # Fresh native PG with all physically deployed payloads active.
        cur.execute("UPDATE pg_statistic_ext_data d SET stxdmcv=b.stxdmcv "
                    "FROM v3_deploy_backup b WHERE d.stxoid=b.stxoid")
        native_rows = [raw_rows(query["where"]) for query in queries]
        replay_losses = [qerror(rows,q["truth"]) for rows,q in zip(replay_rows,new_queries)]
        native_losses = [qerror(rows,q["truth"]) for rows,q in zip(native_rows,new_queries)]
        semantic_errors = [abs(left-right)/max(abs(right),1e-300)
                           for left,right in zip(replay_rows,native_rows)]
        drift_factors = [max(new/old_row,old_row/new) for old_row,new in zip(frozen_rows,replay_rows)]
        qerror_deltas = [new-old_loss for new,old_loss in zip(replay_losses,frozen_losses)]
        result = {
            "experiment": "MCV-Deploy-v0", "selected_count": len(selected),
            "target": args.target,
            "timing": {"create_seconds": create_seconds, "analyze_seconds": analyze_seconds,
                       "total_seconds": time.perf_counter()-started},
            "loss": {"frozen_predicted": sum(frozen_losses),
                     "new_payload_replay": sum(replay_losses),
                     "fresh_native_pg": sum(native_losses),
                     "sampling_drift_absolute": sum(replay_losses)-sum(frozen_losses),
                     "sampling_drift_relative": sum(replay_losses)/sum(frozen_losses)-1},
            "semantic_fidelity": {"queries": len(semantic_errors),
                                  "matches_1e_12": sum(e<=1e-12 for e in semantic_errors),
                                  "max_relative_error": max(semantic_errors),
                                  "median_relative_error": statistics.median(semantic_errors)},
            "sampling_stability": {"estimate_factor_median": statistics.median(drift_factors),
                                   "estimate_factor_p90": percentile(drift_factors,.9),
                                   "estimate_factor_p99": percentile(drift_factors,.99),
                                   "estimate_factor_max": max(drift_factors),
                                   "qerror_delta_median": statistics.median(qerror_deltas),
                                   "queries_qerror_improved": sum(d<0 for d in qerror_deltas),
                                   "queries_qerror_worsened": sum(d>0 for d in qerror_deltas)},
            "physical_precedence": precedence,
        }
        args.output.write_text(json.dumps(result,indent=2)+"\n")
        print(json.dumps({k:result[k] for k in ("selected_count","timing","loss",
                                                "semantic_fidelity","sampling_stability")},indent=2))
    finally:
        clean(); conn.close()


if __name__ == "__main__": main()
