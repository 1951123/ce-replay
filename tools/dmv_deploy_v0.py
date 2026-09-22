#!/usr/bin/env python3
"""Physically deploy the frozen DMV design and validate one fresh realization."""

from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import math
import statistics
import time
from pathlib import Path

import psycopg

from dmv_baseline_nonmonotonicity_v0 import (
    MCV_RE, RAW_RE, TOL, parse_binary_dependencies, parse_queries, qerror,
    relerr, replay, text,
)


def pct(values,p):
    values=sorted(values); pos=(len(values)-1)*p; lo=int(pos); hi=min(lo+1,len(values)-1)
    return values[lo]+(values[hi]-values[lo])*(pos-lo)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--design",type=Path,default=Path("results/dmv_maintenance_budget_design_v0.json"))
    ap.add_argument("--optimization",type=Path,default=Path("results/dmv_maintenance_budget_optimize_v0.json"))
    ap.add_argument("--cost-model",type=Path,default=Path("results/dmv_analyze_cost_model_v0.json"))
    ap.add_argument("--audit",type=Path,default=Path("results/dmv_fit_audit_v0.json"))
    ap.add_argument("--queries",type=Path,default=Path("/root/projects/extended-stats-optim-v2/benchmarks/DMV/queries/dmv.sql"))
    ap.add_argument("--csv",type=Path,default=Path("/root/projects/extended-stats-optim-v2/benchmarks/DMV/data/original.csv"))
    ap.add_argument("--output",type=Path,default=Path("results/dmv_deploy_v0.json"))
    ap.add_argument("--report",type=Path,default=Path("results/dmv_deploy_v0.md"))
    ap.add_argument("--query-csv",type=Path,default=Path("results/dmv_deploy_query_comparison_v0.csv"))
    ap.add_argument("--host",default="/tmp"); ap.add_argument("--port",type=int,default=55433)
    ap.add_argument("--user",default="postgres"); ap.add_argument("--database",default="dmv_deploy_v0")
    ap.add_argument("--target",type=int,default=100); ap.add_argument("--keep-database",action="store_true")
    args=ap.parse_args(); started=time.perf_counter()
    design=json.loads(args.design.read_text()); opt=json.loads(args.optimization.read_text())
    cm=json.loads(args.cost_model.read_text()); audit=json.loads(args.audit.read_text()); queries=parse_queries(args.queries)
    if len(design["selected_mcv_ids"])!=11 or len(design["selected_fd_ids"])!=12: raise RuntimeError("design count mismatch")
    if abs(design["maintenance_cost"]-29.1585432900458)>1e-12 or abs(design["budget"]-43.72460299423155)>1e-12: raise RuntimeError("resource mismatch")
    frozen_mcv_by={x["id"]:x for x in opt["instance"]["mcv_candidates"]}; frozen_fd_by={x["id"]:x for x in opt["instance"]["fd_candidates"]}
    if set(design["selected_mcv_ids"])-frozen_mcv_by.keys() or set(design["selected_fd_ids"])-frozen_fd_by.keys(): raise RuntimeError("unknown design candidate")
    expected_order=design["creation_order"]
    if [x["id"] for x in expected_order if x["mechanism"]=="mcv"]!=design["selected_mcv_ids"]: raise RuntimeError("MCV order mismatch")
    if [x["id"] for x in expected_order if x["mechanism"]=="fd"]!=design["selected_fd_ids"]: raise RuntimeError("FD order mismatch")

    admin=psycopg.connect(host=args.host,port=args.port,user=args.user,dbname="postgres",autocommit=True)
    with admin.cursor() as c:
        c.execute("SELECT 1 FROM pg_database WHERE datname=%s",(args.database,))
        if c.fetchone(): raise RuntimeError("existing deployment database")
        c.execute(psycopg.sql.SQL("CREATE DATABASE {} TEMPLATE template0").format(psycopg.sql.Identifier(args.database)))
    con=psycopg.connect(host=args.host,port=args.port,user=args.user,dbname=args.database,autocommit=True)
    cur=con.cursor(); notices=[]; con.add_notice_handler(lambda d:notices.append(d.message_primary))

    def native(where):
        notices.clear(); cur.execute("EXPLAIN SELECT * FROM dmv WHERE "+where)
        raw=[RAW_RE.match(x) for x in notices if RAW_RE.match(x)]
        if len(raw)!=1: raise RuntimeError((where,notices[-20:]))
        nodes=[MCV_RE.match(x) for x in notices if MCV_RE.match(x)]
        return float(raw[0].group(1)),float(raw[0].group(2)),[int(x.group(1)) for x in nodes]

    try:
        cur.execute("CREATE UNLOGGED TABLE dmv(record_type text,registration_class text,state text,county text,body_type text,fuel_type text,reg_valid_date text,color text,scofflaw_indicator text,suspension_indicator text,revocation_indicator text)")
        with cur.copy("COPY dmv FROM STDIN WITH (FORMAT csv,HEADER true)") as cp:
            with args.csv.open("rb") as f:
                for chunk in iter(lambda:f.read(8*1024*1024),b""): cp.write(chunk)
        cur.execute("UPDATE dmv SET record_type=btrim(record_type),registration_class=btrim(registration_class),state=btrim(state),county=btrim(county),body_type=btrim(body_type),fuel_type=btrim(fuel_type),color=btrim(color),scofflaw_indicator=btrim(scofflaw_indicator),suspension_indicator=btrim(suspension_indicator),revocation_indicator=btrim(revocation_indicator)")
        cur.execute("SELECT count(*) FROM dmv"); row_count=int(cur.fetchone()[0])
        cur.execute("SELECT attname,format_type(atttypid,atttypmod) FROM pg_attribute WHERE attrelid='dmv'::regclass AND attnum>0 AND NOT attisdropped ORDER BY attnum")
        schema=[{"column":text(a).lower(),"type":text(t)} for a,t in cur.fetchall()]
        cur.execute("SELECT version()"); version=text(cur.fetchone()[0])
        if row_count!=audit["dataset"]["row_count_from_csv"] or [x["column"] for x in schema]!=audit["dataset"]["columns"] or len(queries)!=1965: raise RuntimeError("environment mismatch")
        cur.execute("SELECT count(*) FROM pg_statistic_ext WHERE stxrelid='dmv'::regclass")
        if int(cur.fetchone()[0])!=0: raise RuntimeError("unexpected statistics")

        deployed=[]
        for creation_rank,item in enumerate(expected_order):
            mechanism=item["mechanism"]; columns=item["columns"]; kind="mcv" if mechanism=="mcv" else "dependencies"
            name=f"dmv_deploy_v0_{creation_rank:02d}_{mechanism}"
            cur.execute(psycopg.sql.SQL("CREATE STATISTICS {} ({}) ON {},{} FROM dmv").format(psycopg.sql.Identifier(name),psycopg.sql.SQL(kind),psycopg.sql.Identifier(columns[0]),psycopg.sql.Identifier(columns[1])))
            cur.execute(psycopg.sql.SQL("ALTER STATISTICS {} SET STATISTICS {}").format(psycopg.sql.Identifier(name),psycopg.sql.Literal(args.target)))
            cur.execute("SELECT oid FROM pg_statistic_ext WHERE stxname=%s",(name,)); oid=int(cur.fetchone()[0])
            deployed.append({"id":item["id"],"mechanism":mechanism,"columns":columns,"name":name,
                             "oid":oid,"creation_rank":creation_rank,"semantic_rank":item["rank"]})
        physical_order=all(a["oid"]<b["oid"] for a,b in zip(deployed,deployed[1:]))
        if not physical_order: raise RuntimeError("OID order mismatch")
        analyze_start=time.perf_counter(); cur.execute("ANALYZE dmv"); analyze_seconds=time.perf_counter()-analyze_start
        analyze_count=1

        cur.execute("SELECT attnum,attname FROM pg_attribute WHERE attrelid='dmv'::regclass AND attnum>0")
        attnames={int(n):text(a).lower() for n,a in cur.fetchall()}
        mcv=[]; fd=[]
        for d in deployed:
            if d["mechanism"]=="mcv":
                cur.execute("SELECT pg_column_size(stxdmcv) FROM pg_statistic_ext_data WHERE stxoid=%s AND NOT stxdinherit",(d["oid"],)); size=cur.fetchone()[0]
                cur.execute("SELECT a.attname FROM pg_statistic_ext x CROSS JOIN LATERAL unnest(x.stxkeys::smallint[]) WITH ORDINALITY k(attnum,ord) JOIN pg_attribute a ON a.attrelid=x.stxrelid AND a.attnum=k.attnum WHERE x.oid=%s ORDER BY k.ord",(d["oid"],))
                payload_columns=[text(x[0]).lower() for x in cur.fetchall()]
                cur.execute("SELECT values,nulls,frequency,base_frequency FROM pg_statistic_ext_data CROSS JOIN LATERAL pg_mcv_list_items(stxdmcv) WHERE stxoid=%s AND NOT stxdinherit",(d["oid"],))
                payload=[{"values":[text(v) if v is not None else None for v in vals],"nulls":nulls,"frequency":float(fr),"base_frequency":float(ba)} for vals,nulls,fr,ba in cur.fetchall()]
                mcv.append({**d,"index":len(mcv),"oid_rank":d["semantic_rank"],"payload_columns":payload_columns,
                            "payload":payload,"total_frequency":sum(x["frequency"] for x in payload),"serialized_bytes":size,"available":bool(payload)})
            else:
                cur.execute("SELECT pg_column_size(stxddependencies),pg_dependencies_send(stxddependencies) FROM pg_statistic_ext_data WHERE stxoid=%s AND NOT stxdinherit",(d["oid"],)); size,payload=cur.fetchone()
                deps=parse_binary_dependencies(payload,attnames) if payload is not None else []
                fd.append({**d,"index":len(fd),"oid_rank":d["semantic_rank"],"payload":deps,
                           "serialized_bytes":size,"available":bool(deps)})
        fresh_mcv_ids={x["id"]:i for i,x in enumerate(mcv)}; fresh_fd_ids={x["id"]:i for i,x in enumerate(fd)}

        # Preserve fresh payloads, temporarily disable them to obtain the fresh
        # base/simple context, then restore the exact same single-ANALYZE payload.
        cur.execute("CREATE TABLE dmv_deploy_backup AS SELECT stxoid,stxdmcv,stxddependencies FROM pg_statistic_ext_data WHERE stxoid=ANY(%s)",([x["oid"] for x in deployed],))
        cur.execute("UPDATE pg_statistic_ext_data SET stxdmcv=NULL,stxddependencies=NULL WHERE stxoid=ANY(%s)",([x["oid"] for x in deployed],))
        relation_rows=native("TRUE")[0]; clause_cache={}
        for q in queries:
            sels=[]; cols={}
            for clause in q["clauses"]:
                key=clause["sql"]
                if key not in clause_cache: clause_cache[key]=native(key)[0]/relation_rows
                sels.append(clause_cache[key]); cols[clause["column"]]=clause_cache[key]
            q["clause_selectivities"]=sels; q["column_selectivities"]=cols; q["baseline_rows"]=native(q["where"])[0]
        cur.execute("UPDATE pg_statistic_ext_data d SET stxdmcv=b.stxdmcv,stxddependencies=b.stxddependencies FROM dmv_deploy_backup b WHERE d.stxoid=b.stxoid")

        # Frozen control traces remain reconstructable because selection and FD
        # dependency choice don't require the missing frozen numeric base state.
        fm=[dict(frozen_mcv_by[x]) for x in design["selected_mcv_ids"]]
        ff=[dict(frozen_fd_by[x]) for x in design["selected_fd_ids"]]
        for i,x in enumerate(fm): x["index"]=i
        for i,x in enumerate(ff): x["index"]=i
        rows=[]; rels=[]; abses=[]; bitwise=0; fresh_mcv_consumed=set(); fresh_fd_consumed=set()
        frozen_mcv_consumed=set(); frozen_fd_consumed=set(); mcv_changed=fd_changed=0
        for q in queries:
            fresh_est,mt,ft=replay(q,set(range(len(mcv))),set(range(len(fd))),mcv,fd,True)
            native_est,_,native_mcv_oids=native(q["where"])
            _,fmt,fft=replay(q,set(range(len(fm))),set(range(len(ff))),fm,ff,True)
            fresh_mt=[x["id"] for x in mt]; fresh_ft=[x["id"] for x in ft]
            frozen_mt=[x["id"] for x in fmt]; frozen_ft=[x["id"] for x in fft]
            mcv_changed+=fresh_mt!=frozen_mt; fd_changed+=fresh_ft!=frozen_ft
            fresh_mcv_consumed.update(fresh_mt); fresh_fd_consumed.update(fresh_ft)
            frozen_mcv_consumed.update(frozen_mt); frozen_fd_consumed.update(frozen_ft)
            err=relerr(fresh_est,native_est); rels.append(err); abses.append(abs(fresh_est-native_est)); bitwise+=fresh_est.hex()==native_est.hex()
            fresh_q=qerror(fresh_est,q["truth"]); native_q=qerror(native_est,q["truth"])
            rows.append({"query":q["id"],"truth":q["truth"],"zero_truth":q["truth"]==0,
                         "frozen_estimate":None,"frozen_qerror":None,"frozen_numeric_available":False,
                         "fresh_replay_estimate":fresh_est,"fresh_native_estimate":native_est,
                         "fresh_replay_qerror":fresh_q,"fresh_native_qerror":native_q,
                         "semantic_relative_error":err,"frozen_mcv_trace":frozen_mt,"fresh_mcv_trace":fresh_mt,
                         "frozen_fd_trace":frozen_ft,"fresh_fd_trace":fresh_ft,
                         "mcv_trace_changed":fresh_mt!=frozen_mt,"fd_trace_changed":fresh_ft!=frozen_ft,
                         "control_class":("mcv+fd" if fresh_mt!=frozen_mt and fresh_ft!=frozen_ft else "mcv" if fresh_mt!=frozen_mt else "fd" if fresh_ft!=frozen_ft else "unchanged")})

        fresh_loss=sum(x["fresh_replay_qerror"] for x in rows); native_loss=sum(x["fresh_native_qerror"] for x in rows)
        zero=[x for x in rows if x["zero_truth"]]; nonzero=[x for x in rows if not x["zero_truth"]]
        fresh_nonzero=sum(x["fresh_replay_qerror"] for x in nonzero); native_nonzero=sum(x["fresh_native_qerror"] for x in nonzero)
        unchanged=sum(relerr(x["fresh_replay_estimate"],x["fresh_native_estimate"])==0 for x in rows)
        with args.query_csv.open("w",newline="") as f:
            fields=["query","truth","zero_truth","frozen_estimate","fresh_replay_estimate","fresh_native_estimate",
                    "frozen_qerror","fresh_replay_qerror","semantic_relative_error","mcv_trace_changed","fd_trace_changed","control_class"]
            out=csv.DictWriter(f,fieldnames=fields); out.writeheader()
            for x in rows: out.writerow({k:x[k] for k in fields})

        model=cm["models"]["mechanism_aware"]; predicted=(model["intercept_seconds"]+
               model["coefficients_seconds"]["mcv_count"]*11+model["coefficients_seconds"]["fd_count"]*12)
        pred_abs=abs(predicted-analyze_seconds); pred_rel=pred_abs/analyze_seconds
        frozen_numeric_available=False
        blocker_reason="The authoritative frozen artifacts omit per-query baseline rows and clause selectivities, so frozen per-query estimates, zero-truth contributions, nonzero-truth loss, and frozen-to-fresh estimate-drift distribution cannot be reconstructed exactly after cleanup."
        result={"experiment":"DMV-Deploy-v0","deployment":{"database":args.database,"isolated":True,"postgres_version":version,
                 "row_count":row_count,"schema":schema,"statistics_target":args.target,"objects":deployed,
                 "selected_mcv":11,"selected_fd":12,"physical_oid_order_verified":physical_order,
                 "analyze_executions":analyze_count,"analyze_seconds":analyze_seconds,"reoptimized":False},
          "design_verification":{"authoritative_artifact":str(args.design),"maintenance_cost":design["maintenance_cost"],
                 "budget":design["budget"],"frozen_predicted_loss":design["frozen_predicted_loss"],"candidate_ids_match":True},
          "cost_sanity":{"predicted_seconds":predicted,"observed_seconds":analyze_seconds,
                         "absolute_error_seconds":pred_abs,"relative_error":pred_rel,"model_refit":False},
          "fresh_payloads":{"mcv":mcv,"fd":fd,"mcv_materialized":sum(x["available"] for x in mcv),
                            "fd_materialized":sum(x["available"] for x in fd),
                            "fd_unavailable":[x["id"] for x in fd if not x["available"]]},
          "semantic":{"comparisons":len(rows),"matches":sum(x<=TOL for x in rels),"tolerance":TOL,
                      "max_relative_error":max(rels),"max_absolute_error":max(abses),"bitwise_equal":bitwise},
          "loss":{"frozen":design["frozen_predicted_loss"],"fresh_replay":fresh_loss,"fresh_native":native_loss,
                  "frozen_to_fresh_change":fresh_loss-design["frozen_predicted_loss"],
                  "semantic_error":native_loss-fresh_loss,"frozen_nonzero_truth":None,
                  "fresh_replay_nonzero_truth":fresh_nonzero,"fresh_native_nonzero_truth":native_nonzero},
          "zero_truth":{"count":len(zero),"query_ids":[x["query"] for x in zero],
                        "frozen_contribution":None,"fresh_replay_contribution":sum(x["fresh_replay_qerror"] for x in zero),
                        "fresh_native_contribution":sum(x["fresh_native_qerror"] for x in zero),
                        "queries":[{"id":x["query"],"frozen_qerror":None,"fresh_qerror":x["fresh_replay_qerror"],
                                    "fresh_estimate":x["fresh_replay_estimate"]} for x in zero]},
          "estimate_drift":{"available":False,"reason":blocker_reason,"unchanged":None,"meaningfully_changed":None,
                            "median":None,"p90":None,"p95":None,"p99":None,"maximum":None},
          "control":{"mcv_trace_unchanged":len(rows)-mcv_changed,"mcv_trace_changed":mcv_changed,
                     "fd_trace_unchanged":len(rows)-fd_changed,"fd_trace_changed":fd_changed,
                     "fresh_mcv_consumed":len(fresh_mcv_consumed),"fresh_mcv_never_consumed":sorted(set(design["selected_mcv_ids"])-fresh_mcv_consumed),
                     "fresh_fd_consumed":len(fresh_fd_consumed),"fresh_fd_never_consumed":sorted(set(design["selected_fd_ids"])-fresh_fd_consumed),
                     "queries_consuming_fd":sum(bool(x["fresh_fd_trace"]) for x in rows),
                     "frozen_mcv_consumed_structural":len(frozen_mcv_consumed),"frozen_fd_consumed_structural":len(frozen_fd_consumed)},
          "frozen_numeric_artifact":{"available":frozen_numeric_available,"blocker":blocker_reason},
          "query_comparison_artifact":str(args.query_csv),"runtime_seconds":time.perf_counter()-started}
        semantic_ok=result["semantic"]["matches"]==len(rows)
        requirements_complete=semantic_ok and frozen_numeric_available
        result["gate"]="DMV REPLICATION COMPLETE" if requirements_complete else "DEPLOYMENT/CORRECTNESS BLOCKER"
        args.output.write_text(json.dumps(result,indent=2)+"\n")

        c=result["control"]; z=result["zero_truth"]; sem=result["semantic"]
        md=f"""# DMV-Deploy-v0

## Outcome

Exactly 11 MCV and 12 FD objects from the authoritative design artifact were created in its recorded order; physical OIDs were strictly increasing. Exactly one fresh target-{args.target} `ANALYZE` was executed. No reoptimization, design change, precedence optimization, or repeated ANALYZE occurred.

Fresh replay/native semantic validation {'passed' if semantic_ok else 'failed'} {sem['matches']:,}/{sem['comparisons']:,} comparisons at tolerance {TOL:g}; maximum relative error {sem['max_relative_error']:.6g}, maximum absolute error {sem['max_absolute_error']:.6g}, bitwise equal {sem['bitwise_equal']:,}.

The deployment exposed an upstream artifact blocker: {blocker_reason} Fresh semantics and physical composition are validated, but the mandatory frozen numerical drift and frozen zero-truth decomposition cannot be supplied without inventing data or running a new optimization realization. The final gate is therefore a blocker.

## Fresh realization

- Cost-model prediction: {predicted:.9f} s; observed: {analyze_seconds:.9f} s; absolute/relative error {pred_abs:.9f} s / {pred_rel:.4%}.
- Fresh MCV payloads: {result['fresh_payloads']['mcv_materialized']}/11; consumed {c['fresh_mcv_consumed']}/11.
- Fresh FD payloads: {result['fresh_payloads']['fd_materialized']}/12; consumed {c['fresh_fd_consumed']}/12; unavailable {len(result['fresh_payloads']['fd_unavailable'])}.
- Queries consuming FD: {c['queries_consuming_fd']}.
- Fresh replay/native loss: {fresh_loss:.12g} / {native_loss:.12g}; nonzero-truth diagnostic {fresh_nonzero:.12g} / {native_nonzero:.12g}.
- Zero-truth queries: {', '.join(z['query_ids'])}; fresh contribution {z['fresh_replay_contribution']:.12g}; frozen contribution unavailable for the stated artifact reason.
- Frozen/fresh structural MCV trace changes: {mcv_changed}; FD trace changes: {fd_changed}.

## Required final verdict

1. **Were exactly 11 MCV and 12 FD objects deployed?** Yes.
2. **Did physical OID/creation order match the frozen design?** Yes.
3. **Was exactly one fresh ANALYZE executed?** Yes.
4. **What ANALYZE latency did the DMV cost model predict?** {predicted:.9f} seconds.
5. **What latency was observed?** {analyze_seconds:.9f} seconds.
6. **What was the prediction error?** {pred_abs:.9f} seconds ({pred_rel:.4%}).
7. **How many deployed MCV payloads materialized?** {result['fresh_payloads']['mcv_materialized']}/11.
8. **How many deployed FD payloads materialized?** {result['fresh_payloads']['fd_materialized']}/12.
9. **What was the frozen optimization loss?** {design['frozen_predicted_loss']:.12g}.
10. **What was the fresh replay loss?** {fresh_loss:.12g}.
11. **What was the fresh native PostgreSQL loss?** {native_loss:.12g}.
12. **What was the frozen-to-fresh payload-realization drift?** Aggregate change {fresh_loss-design['frozen_predicted_loss']:.12g}; per-query drift distribution is unavailable because the frozen specialization was not preserved.
13. **How many fresh replay/native comparisons were performed?** {len(rows):,}.
14. **How many passed strict tolerance?** {sem['matches']:,}/{len(rows):,}.
15. **What was the maximum relative semantic replay error?** {sem['max_relative_error']:.6g}.
16. **How many queries changed MCV control trace?** {mcv_changed}.
17. **How many changed FD control trace?** {fd_changed}.
18. **How many selected MCV objects were consumed after deployment?** {c['fresh_mcv_consumed']}/11.
19. **How many selected FD objects were consumed after deployment?** {c['fresh_fd_consumed']}/12.
20. **How many fresh queries consumed at least one FD?** {c['queries_consuming_fd']}.
21. **Did the optimized MCV/FD compositional behavior survive physical deployment?** {'Yes' if c['fresh_fd_consumed'] and c['queries_consuming_fd'] else 'No'}.
22. **Which two queries have zero truth?** {', '.join(z['query_ids'])}.
23. **How much of the original aggregate objective is contributed by those two queries?** Fresh replay {z['fresh_replay_contribution']:.12g}; frozen contribution unavailable because the required frozen per-query numbers were not preserved.
24. **What is the frozen nonzero-truth diagnostic loss?** Unavailable for the documented artifact reason.
25. **What is the fresh nonzero-truth diagnostic loss?** {fresh_nonzero:.12g}.
26. **What is the multiplicative estimate-drift distribution?** Unavailable because exact frozen per-query estimates were not preserved.
27. **Is the fresh deployment discrepancy attributable to payload realization rather than semantic replay error?** Fresh replay/native semantic error is bounded by {sem['max_relative_error']:.6g}; aggregate frozen/fresh change is payload/context drift, but its query-level distribution cannot be reconstructed.
28. **Did any correctness issue require changing the frozen design?** No; the design was unchanged.
29. **Does this experiment close the complete DMV fixed-workload physical-design loop?** No: physical deployment and fresh semantic validation succeed, but the required frozen numerical drift audit is incomplete.

## Final gate

{result['gate']}
"""
        args.report.write_text(md)
        print(json.dumps({"gate":result["gate"],"analyze":{"predicted":predicted,"observed":analyze_seconds,"relative_error":pred_rel},
                          "payloads":{"mcv":result['fresh_payloads']['mcv_materialized'],"fd":result['fresh_payloads']['fd_materialized']},
                          "semantic":sem,"loss":result["loss"],"zero_truth":z,"control":c,
                          "blocker":blocker_reason},indent=2),flush=True)
    finally:
        try: cur.close(); con.close()
        finally:
            if not args.keep_database:
                with admin.cursor() as c:
                    c.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname=%s",(args.database,))
                    c.execute(psycopg.sql.SQL("DROP DATABASE IF EXISTS {}").format(psycopg.sql.Identifier(args.database)))
            admin.close()


if __name__=="__main__": main()
