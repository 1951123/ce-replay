#!/usr/bin/env python3
"""Deploy and semantically validate a fixed DMV state.

The input state came from a diagnostic optimization whose maintenance-cost
interpretation is retired; deployment does not validate that cost model.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import time
from pathlib import Path

import psycopg

from dmv_baseline_nonmonotonicity_v0 import (
    RAW_RE, TOL, parse_binary_dependencies, qerror, relerr, replay, text,
)


def percentile(values, p):
    values = sorted(values); pos = (len(values)-1)*p
    lo = int(pos); hi = min(lo+1, len(values)-1)
    return values[lo] + (values[hi]-values[lo])*(pos-lo)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--optimization", type=Path, required=True)
    ap.add_argument("--database", default="dmv_nonzero_baseline_v0")
    ap.add_argument("--host", default="/tmp"); ap.add_argument("--port", type=int, default=55433)
    ap.add_argument("--user", default="postgres"); ap.add_argument("--target", type=int, default=100)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args(); started = time.perf_counter()
    frozen = json.loads(args.optimization.read_text())
    queries = frozen["replay_inputs"]["queries"]
    cm = frozen["candidate_universe"]["mcv_candidates"]
    cf = frozen["candidate_universe"]["fd_candidates"]
    selected = frozen["optimization"]["selected_indexes"]
    definitions = ([{"mechanism":"mcv", **cm[i]} for i in selected["mcv"]] +
                   [{"mechanism":"fd", **cf[i]} for i in selected["fd"]])
    definitions.sort(key=lambda x: (x["mechanism"] != "mcv", x["oid_rank"]))

    con = psycopg.connect(host=args.host, port=args.port, user=args.user,
                          dbname=args.database, autocommit=True)
    cur = con.cursor(); notices = []
    con.add_notice_handler(lambda d: notices.append(d.message_primary))
    def native(where):
        notices.clear(); cur.execute("EXPLAIN SELECT * FROM dmv WHERE " + where)
        rows = [RAW_RE.match(x) for x in notices if RAW_RE.match(x)]
        if len(rows) != 1: raise RuntimeError((where, notices[-10:]))
        return float(rows[0].group(1))

    cur.execute("SELECT stxname FROM pg_statistic_ext WHERE stxrelid='dmv'::regclass")
    for (name,) in cur.fetchall():
        cur.execute(psycopg.sql.SQL("DROP STATISTICS {}").format(psycopg.sql.Identifier(text(name))))
    deployed = []
    for rank, item in enumerate(definitions):
        kind = "mcv" if item["mechanism"] == "mcv" else "dependencies"
        name = f"dmv_nonzero_deploy_v0_{rank:02d}_{item['mechanism']}"
        cur.execute(psycopg.sql.SQL("CREATE STATISTICS {} ({}) ON {},{} FROM dmv").format(
            psycopg.sql.Identifier(name), psycopg.sql.SQL(kind),
            psycopg.sql.Identifier(item["columns"][0]), psycopg.sql.Identifier(item["columns"][1])))
        cur.execute(psycopg.sql.SQL("ALTER STATISTICS {} SET STATISTICS {}").format(
            psycopg.sql.Identifier(name), psycopg.sql.Literal(args.target)))
        cur.execute("SELECT oid FROM pg_statistic_ext WHERE stxname=%s", (name,))
        deployed.append({"id":item["id"], "mechanism":item["mechanism"],
                         "columns":item["columns"], "semantic_rank":item["oid_rank"],
                         "creation_rank":rank, "name":name, "oid":int(cur.fetchone()[0])})
    analyze_start = time.perf_counter(); cur.execute("ANALYZE dmv")
    analyze_seconds = time.perf_counter()-analyze_start
    cur.execute("SELECT attnum,attname FROM pg_attribute WHERE attrelid='dmv'::regclass AND attnum>0")
    attnames = {int(n):text(a).lower() for n,a in cur.fetchall()}
    mcv = []; fd = []
    for item in deployed:
        if item["mechanism"] == "mcv":
            cur.execute("SELECT a.attname FROM pg_statistic_ext x CROSS JOIN LATERAL unnest(x.stxkeys::smallint[]) WITH ORDINALITY k(attnum,ord) JOIN pg_attribute a ON a.attrelid=x.stxrelid AND a.attnum=k.attnum WHERE x.oid=%s ORDER BY k.ord", (item["oid"],))
            columns = [text(x[0]).lower() for x in cur.fetchall()]
            cur.execute("SELECT values,nulls,frequency,base_frequency FROM pg_statistic_ext_data CROSS JOIN LATERAL pg_mcv_list_items(stxdmcv) WHERE stxoid=%s", (item["oid"],))
            payload = [{"values":[text(v) if v is not None else None for v in vals],
                        "nulls":nulls,"frequency":float(fr),"base_frequency":float(ba)}
                       for vals,nulls,fr,ba in cur.fetchall()]
            mcv.append({**item,"index":len(mcv),"oid_rank":item["semantic_rank"],
                        "payload_columns":columns,"payload":payload,
                        "total_frequency":sum(x["frequency"] for x in payload)})
        else:
            cur.execute("SELECT pg_dependencies_send(stxddependencies) FROM pg_statistic_ext_data WHERE stxoid=%s", (item["oid"],))
            raw = cur.fetchone()[0]
            payload = parse_binary_dependencies(raw,attnames) if raw is not None else []
            fd.append({**item,"index":len(fd),"oid_rank":item["semantic_rank"],"payload":payload})

    oids = [x["oid"] for x in deployed]
    cur.execute("DROP TABLE IF EXISTS dmv_nonzero_deploy_backup")
    cur.execute("CREATE TABLE dmv_nonzero_deploy_backup AS SELECT stxoid,stxdmcv,stxddependencies FROM pg_statistic_ext_data WHERE stxoid=ANY(%s)", (oids,))
    cur.execute("UPDATE pg_statistic_ext_data SET stxdmcv=NULL,stxddependencies=NULL WHERE stxoid=ANY(%s)", (oids,))
    relation_rows = native("TRUE"); cache = {}
    for q in queries:
        sels=[]; columns={}
        for clause in q["clauses"]:
            key=clause["sql"]
            if key not in cache: cache[key]=native(key)/relation_rows
            sels.append(cache[key]); columns[clause["column"]]=cache[key]
        q["clause_selectivities"]=sels; q["column_selectivities"]=columns
        q["baseline_rows"]=native(q["where"])
    cur.execute("UPDATE pg_statistic_ext_data d SET stxdmcv=b.stxdmcv,stxddependencies=b.stxddependencies FROM dmv_nonzero_deploy_backup b WHERE d.stxoid=b.stxoid")

    frozen_rows={x["query"]:x for x in frozen["frozen_per_query"]}
    rows=[]; errors=[]; abs_errors=[]; paired=[]; mcv_changes=fd_changes=0
    for q in queries:
        estimate,mt,ft=replay(q,set(range(len(mcv))),set(range(len(fd))),mcv,fd,True)
        native_est=native(q["where"]); err=relerr(estimate,native_est)
        old=frozen_rows[q["id"]]; old_est=old["estimate"]
        drift=max(max(estimate,1e-300)/max(old_est,1e-300),max(old_est,1e-300)/max(estimate,1e-300))
        if q["truth"]>0: paired.append(drift)
        old_mt=[x["id"] for x in old["mcv_trace"]]; old_ft=[x["id"] for x in old["fd_trace"]]
        new_mt=[x["id"] for x in mt]; new_ft=[x["id"] for x in ft]
        mcv_changes += old_mt != new_mt; fd_changes += old_ft != new_ft
        errors.append(err); abs_errors.append(abs(estimate-native_est))
        rows.append({"query":q["id"],"truth":q["truth"],"zero_truth":q["truth"]==0,
                     "frozen_estimate":old_est,"fresh_replay_estimate":estimate,
                     "fresh_native_estimate":native_est,"fresh_qerror_contribution":qerror(estimate,q["truth"]),
                     "semantic_relative_error":err,"estimate_drift_qerror":drift,
                     "frozen_mcv_trace":old_mt,"fresh_mcv_trace":new_mt,
                     "frozen_fd_trace":old_ft,"fresh_fd_trace":new_ft})
    con.close()
    frozen_loss=sum(x["qerror_contribution"] for x in frozen["frozen_per_query"])
    fresh_loss=sum(x["fresh_qerror_contribution"] for x in rows)
    result={"experiment":"DMV-Nonzero-Truth-Rebuild-v0 deployment",
      "deployment":{"database":args.database,"same_database_realization":True,"objects":deployed,
                    "selected_mcv":len(mcv),"selected_fd":len(fd),"analyze_seconds":analyze_seconds,
                    "mcv_materialized":sum(bool(x["payload"]) for x in mcv),
                    "fd_materialized":sum(bool(x["payload"]) for x in fd),
                    "unmaterialized_ids":[x["id"] for x in mcv+fd if not x["payload"]]},
      "semantic":{"comparisons":len(rows),"matches":sum(x<=TOL for x in errors),"tolerance":TOL,
                  "max_relative_error":max(errors),"max_absolute_error":max(abs_errors),
                  "mismatch_ids":[x["query"] for x in rows if x["semantic_relative_error"]>TOL]},
      "objective":{"domain":"truth > 0","frozen":frozen_loss,"fresh":fresh_loss,
                   "relative_drift":(fresh_loss-frozen_loss)/frozen_loss},
      "paired_positive_truth_estimate_drift":{"median":statistics.median(paired),"mean":statistics.fmean(paired),
                   "p90":percentile(paired,.9),"p95":percentile(paired,.95),
                   "p99":percentile(paired,.99),"maximum":max(paired)},
      "control":{"mcv_trace_changed_queries":mcv_changes,"fd_trace_changed_queries":fd_changes},
      "zero_truth":{"ids":[x["query"] for x in rows if x["zero_truth"]],
                    "semantic_matches":sum(x["semantic_relative_error"]<=TOL for x in rows if x["zero_truth"]),
                    "objective_contribution":sum(x["fresh_qerror_contribution"] for x in rows if x["zero_truth"])},
      "per_query":rows,"runtime_seconds":time.perf_counter()-started}
    result["gate"]=("DEPLOYMENT COMPLETE" if result["semantic"]["matches"]==len(rows)
                    and result["zero_truth"]["objective_contribution"]==0 else "DEPLOYMENT/CORRECTNESS BLOCKER")
    args.output.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({k:result[k] for k in ("gate","deployment","semantic","objective","paired_positive_truth_estimate_drift","control","zero_truth")}),flush=True)


if __name__ == "__main__": main()
