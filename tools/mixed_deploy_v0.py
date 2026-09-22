#!/usr/bin/env python3
"""Deploy a frozen mixed MCV+FD design and separate payload drift from replay error."""
from __future__ import annotations
import argparse,hashlib,json,re,statistics,struct,time
from pathlib import Path
import psycopg
from ce_replay_optimize_v1 import combine,item_matches,load_queries,qerror
from ce_replay_optimize_v4 import parse_binary_payload,replay,replay_mcv_stage,replay_fd_stage

RAW_RE=re.compile(r"CE_REPLAY_RAW_ROWS .* rows=([^ ]+) selectivity=([^ ]+)")
MCV_RE=re.compile(r"CE_REPLAY_MCV oid=(\d+)")
FD_RE=re.compile(r"CE_REPLAY_FD_CHOOSE step=(\d+) nattrs=(\d+) implied=(\d+) degree=([^ ]+)")
def text(x):return x.decode() if isinstance(x,bytes) else x
def pct(xs,p):
 y=sorted(xs);z=(len(y)-1)*p;i=int(z);j=min(i+1,len(y)-1);return y[i]+(y[j]-y[i])*(z-i)

def final_design(opt,v4):
 seed=next(s for s in v4["strategies"] if s["strategy"]=="joint_semantic");sm=set(seed["selected_mcv"]);sf=set(seed["selected_fd"])
 sensitive=[]
 for r in opt["rounds"]:
  if r["delta"]>=-1e-12:break
  m=json.loads(r["best_move"])
  if m[0]=="toggle":
   t=sm if m[1][0]=="mcv" else sf;c=m[1][1];t.remove(c) if c in t else t.add(c)
  else:
   (sm if m[1][0]=="mcv" else sf).remove(m[1][1]);(sm if m[2][0]=="mcv" else sf).add(m[2][1])
  if r["mcv_boundary_changed"] or r["fd_trace_changed"]:sensitive.append({"round":r["round"],"move":m,"mcv_boundary_changed":r["mcv_boundary_changed"],"fd_trace_changed":r["fd_trace_changed"]})
 return sm,sf,sensitive

def main():
 ap=argparse.ArgumentParser();ap.add_argument("--v4",type=Path,required=True);ap.add_argument("--optimizer",type=Path,required=True);ap.add_argument("--queries",type=Path,required=True);ap.add_argument("--output",type=Path,required=True);ap.add_argument("--report",type=Path,required=True);ap.add_argument("--manifest",type=Path,required=True);ap.add_argument("--payloads",type=Path);ap.add_argument("--host",default="/tmp");ap.add_argument("--port",type=int,default=55432);ap.add_argument("--user",default="postgres");ap.add_argument("--db",default="census");ap.add_argument("--target",type=int,default=100);ap.add_argument("--replace-prefix",action="store_true",help="drop only stale mixed_deploy_* objects from an interrupted run");a=ap.parse_args()
 v4=json.loads(a.v4.read_text());opt=json.loads(a.optimizer.read_text());w=v4["workload_ir"];rawq=load_queries(a.queries);sm,sf,sensitive=final_design(opt,v4)
 frozen_rows=[replay(q,sm,sf,w["mcv_candidates"],w["fd_candidates"],{i:c["oid_rank"] for i,c in enumerate(w["mcv_candidates"])}) for q in w["queries"]];frozen_loss=sum(qerror(r,q["truth"]) for r,q in zip(frozen_rows,w["queries"]))
 frozen_storage=sum(w["mcv_candidates"][i]["cost_bytes"] for i in sm)+sum(w["fd_candidates"][i]["cost_bytes"] for i in sf)
 manifest={"experiment":"Mixed-Deploy-v0-design","source_optimizer":str(a.optimizer),"source_sha256":hashlib.sha256(a.optimizer.read_bytes()).hexdigest(),"selected_mcv":sorted(sm),"selected_fd":sorted(sf),"selected_mcv_count":len(sm),"selected_fd_count":len(sf),"target":a.target,"order_policy":{"mcv":"source oid_rank ascending","fd":"source oid_rank ascending","cross_mechanism":"MCV objects then FD objects; stages consume mechanisms separately"},"mcv":[{"id":i,"columns":w["mcv_candidates"][i]["columns"],"oid_rank":w["mcv_candidates"][i]["oid_rank"],"frozen_cost":w["mcv_candidates"][i]["cost_bytes"]} for i in sorted(sm,key=lambda i:w["mcv_candidates"][i]["oid_rank"])],"fd":[{"id":i,"columns":w["fd_candidates"][i]["columns"],"oid_rank":w["fd_candidates"][i]["oid_rank"],"frozen_cost":w["fd_candidates"][i]["cost_bytes"]} for i in sorted(sf,key=lambda i:w["fd_candidates"][i]["oid_rank"])],"frozen_loss":frozen_loss,"frozen_storage":frozen_storage,"cross_sensitive_accepted_moves":sensitive};a.manifest.write_text(json.dumps(manifest,indent=2)+"\n")
 con=psycopg.connect(host=a.host,port=a.port,user=a.user,dbname=a.db,autocommit=True);cur=con.cursor();notices=[];con.add_notice_handler(lambda d:notices.append(d.message_primary));prefix="mixed_deploy_";started=time.perf_counter()
 def native(where):
  notices.clear();cur.execute(f"EXPLAIN SELECT * FROM climate WHERE {where}");msg=[x for x in notices if x.startswith("CE_REPLAY_RAW_ROWS")]
  if len(msg)!=1:raise RuntimeError((where,msg,notices))
  mm=RAW_RE.match(msg[0]);return float(mm.group(1)),float(mm.group(2)),list(notices)
 try:
  cur.execute("SHOW server_version");version=cur.fetchone()[0];cur.execute("SELECT stxname FROM pg_statistic_ext WHERE stxrelid='climate'::regclass");existing=[text(x[0]) for x in cur.fetchall()]
  stale=[x for x in existing if x.startswith(prefix)]
  foreign=[x for x in existing if not x.startswith(prefix)]
  if foreign:raise RuntimeError("non-experiment climate extstats: "+", ".join(foreign))
  if stale and not a.replace_prefix:raise RuntimeError("stale experiment extstats (use --replace-prefix): "+", ".join(stale))
  for name in stale:cur.execute(f'DROP STATISTICS "{name}"')
  deployed_m=[];deployed_f=[]
  for rank,i in enumerate(sorted(sm,key=lambda i:w["mcv_candidates"][i]["oid_rank"])):
   c=w["mcv_candidates"][i];name=f"{prefix}m_{rank:04d}_c{i}";cur.execute(f'CREATE STATISTICS "{name}" (mcv) ON {c["columns"][0]}, {c["columns"][1]} FROM climate');cur.execute(f'ALTER STATISTICS "{name}" SET STATISTICS {a.target}');cur.execute("SELECT oid FROM pg_statistic_ext WHERE stxname=%s",(name,));deployed_m.append({"id":i,"name":name,"oid":int(cur.fetchone()[0]),"rank":rank,"columns":c["columns"]})
  for rank,i in enumerate(sorted(sf,key=lambda i:w["fd_candidates"][i]["oid_rank"])):
   c=w["fd_candidates"][i];name=f"{prefix}f_{rank:04d}_c{i}";cur.execute(f'CREATE STATISTICS "{name}" (dependencies) ON {c["columns"][0]}, {c["columns"][1]} FROM climate');cur.execute(f'ALTER STATISTICS "{name}" SET STATISTICS {a.target}');cur.execute("SELECT oid FROM pg_statistic_ext WHERE stxname=%s",(name,));deployed_f.append({"id":i,"name":name,"oid":int(cur.fetchone()[0]),"rank":rank,"columns":c["columns"]})
  create_s=time.perf_counter()-started
  # Order must be monotone within each mechanism, exactly as modeled.
  order_ok=all(x["oid"]<y["oid"] for x,y in zip(deployed_m,deployed_m[1:])) and all(x["oid"]<y["oid"] for x,y in zip(deployed_f,deployed_f[1:]))
  if not order_ok:raise RuntimeError("catalog OID order does not match manifest")
  cur.execute("ANALYZE climate");analyze_s=time.perf_counter()-started-create_s
  cur.execute("SELECT reltuples FROM pg_class WHERE oid='climate'::regclass");reltuples=float(cur.fetchone()[0])
  cur.execute("SELECT current_setting('default_statistics_target'), current_setting('effective_cache_size'), current_setting('random_page_cost')");settings=cur.fetchone()
  alloids=[x["oid"] for x in deployed_m+deployed_f]
  cur.execute("CREATE TEMP TABLE mixed_backup AS SELECT stxoid,stxdmcv,stxddependencies,stxdinherit FROM pg_statistic_ext_data WHERE stxoid=ANY(%s)",(alloids,))
  cur.execute("SELECT attnum,attname FROM pg_attribute WHERE attrelid='climate'::regclass AND attnum>0");att={int(n):text(s).lower() for n,s in cur.fetchall()}
  for d in deployed_m:
   cur.execute("SELECT a.attname FROM pg_statistic_ext s CROSS JOIN LATERAL unnest(s.stxkeys::smallint[]) WITH ORDINALITY k(attnum,ord) JOIN pg_attribute a ON a.attrelid=s.stxrelid AND a.attnum=k.attnum WHERE s.oid=%s ORDER BY k.ord",(d["oid"],));d["payload_columns"]=[text(x[0]).lower() for x in cur.fetchall()]
   cur.execute("SELECT pg_column_size(stxdmcv) FROM mixed_backup WHERE stxoid=%s",(d["oid"],));size=cur.fetchone()[0];cur.execute("SELECT values,nulls,frequency,base_frequency FROM mixed_backup CROSS JOIN LATERAL pg_mcv_list_items(stxdmcv) WHERE stxoid=%s",(d["oid"],));rr=cur.fetchall();d["fresh_size"]=int(size or 0);d["payload"]=[{"values":[text(v) if v is not None else None for v in vals],"nulls":nulls,"frequency":float(fr),"base_frequency":float(ba)} for vals,nulls,fr,ba in rr];d["total_frequency"]=sum(x["frequency"] for x in d["payload"])
  for d in deployed_f:
   cur.execute("SELECT pg_column_size(stxddependencies),pg_dependencies_send(stxddependencies) FROM mixed_backup WHERE stxoid=%s",(d["oid"],));size,b=cur.fetchone();d["fresh_size"]=int(size or 0);d["payload"]=[] if b is None else parse_binary_payload(b,att)
  # Disable extended payloads to obtain one internally consistent fresh base context.
  cur.execute("UPDATE pg_statistic_ext_data SET stxdmcv=NULL,stxddependencies=NULL WHERE stxoid=ANY(%s)",(alloids,))
  relation_rows=native("TRUE")[0];mby={d["id"]:d for d in deployed_m};fby={d["id"]:d for d in deployed_f};fresh_queries=[]
  for qi,(old,rq) in enumerate(zip(w["queries"],rawq)):
   base=native(rq["where"])[0];eq=set(old["fd_columns"]);simple={}
   for col in eq:
    wh=" AND ".join(f"{col}{op}{val}" for op,val in rq["predicates"][col]);simple[col]=native(wh)[0]/relation_rows
   ratios={}
   for cid in old["mcv_ids"]:
    if cid not in sm:continue
    d=mby[cid];wh=" AND ".join(f"{col}{op}{val}" for col in d["columns"] for op,val in rq["predicates"][col]);simp=native(wh)[0]/relation_rows;mcv=basef=total=0.0
    for it in d["payload"]:
     total+=it["frequency"]
     if all(item_matches(it["values"][j],it["nulls"][j],rq["predicates"][col]) for j,col in enumerate(d["payload_columns"])):mcv+=it["frequency"];basef+=it["base_frequency"]
    ratios[str(cid)]=combine(simp,mcv,basef,total)/simp
   fresh_queries.append({"id":old["id"],"truth":old["truth"],"predicates":old["predicates"],"baseline_rows":base,"mcv_ids":[i for i in old["mcv_ids"] if i in sm],"mcv_ratios":ratios,"fd_columns":old["fd_columns"],"simple_selectivities":simple,"fd_ids":[i for i in old["fd_ids"] if i in sf]})
  fresh_mc=[dict(x) for x in w["mcv_candidates"]];fresh_fd=[dict(x) for x in w["fd_candidates"]]
  for d in deployed_m:fresh_mc[d["id"]]["oid_rank"]=d["rank"]
  for d in deployed_f:fresh_fd[d["id"]].update({"oid_rank":d["rank"],"payload":d["payload"]})
  ranks={d["id"]:d["rank"] for d in deployed_m};fresh_rows=[];ext_mcv=[];ext_fd=[];boundaries=[]
  for q in fresh_queries:
   b=replay_mcv_stage(q,sm,fresh_mc,ranks);nr,fdtr,_=replay_fd_stage(q,b[0],b[1],sf,fresh_fd,detailed=True);fresh_rows.append(nr);ext_mcv.append(b[2]);ext_fd.append(fdtr);boundaries.append({"post_mcv_rows":b[0],"estimatedclauses":sorted(b[1])})
  cur.execute("UPDATE pg_statistic_ext_data d SET stxdmcv=b.stxdmcv,stxddependencies=b.stxddependencies FROM mixed_backup b WHERE d.stxoid=b.stxoid")
  native_rows=[];native_sel=[];native_traces=[];oidm={d["oid"]:d["id"] for d in deployed_m}
  for rq in rawq:
   nr,ns,msg=native(rq["where"]);native_rows.append(nr);native_sel.append(ns);native_traces.append({"mcv":[oidm[int(x.group(1))] for z in msg if (x:=MCV_RE.match(z)) and int(x.group(1)) in oidm],"fd_choose":[{"step":int(x.group(1)),"nattrs":int(x.group(2)),"implied_attnum":int(x.group(3)),"degree":float(x.group(4))} for z in msg if (x:=FD_RE.match(z))],"raw_messages":[z for z in msg if z.startswith("CE_REPLAY_MCV") or z.startswith("CE_REPLAY_FD")]})
  fresh_losses=[qerror(r,q["truth"]) for r,q in zip(fresh_rows,fresh_queries)];native_losses=[qerror(r,q["truth"]) for r,q in zip(native_rows,fresh_queries)];relerr=[abs(x-y)/max(abs(y),1e-300) for x,y in zip(fresh_rows,native_rows)];abserr=[abs(x-y) for x,y in zip(fresh_rows,native_rows)]
  drift=[max(n/o,o/n) for n,o in zip(fresh_rows,frozen_rows)];qed=[n-o for n,o in zip(fresh_losses,[qerror(r,q["truth"]) for r,q in zip(frozen_rows,fresh_queries)])]
  mcv_trace_match=[ext_mcv[i]==native_traces[i]["mcv"] for i in range(len(fresh_queries))]
  consumed_fd={x["fid"] for tr in ext_fd for x in tr};frozen_consumed=set();frozen_fdtr=[]
  for q in w["queries"]:
   b=replay_mcv_stage(q,sm,w["mcv_candidates"],{i:c["oid_rank"] for i,c in enumerate(w["mcv_candidates"])});_,tr,_=replay_fd_stage(q,b[0],b[1],sf,w["fd_candidates"],detailed=True);frozen_fdtr.append([x["fid"] for x in tr]);frozen_consumed.update(x["fid"] for x in tr)
  fresh_fdtr=[[x["fid"] for x in tr] for tr in ext_fd];changed_fd_queries=[i for i,(x,y) in enumerate(zip(frozen_fdtr,fresh_fdtr)) if x!=y]
  mdiag=[]
  for d in deployed_m:
   old=w["mcv_candidates"][d["id"]];mdiag.append({"id":d["id"],"frozen_size":old["cost_bytes"],"fresh_size":d["fresh_size"],"fresh_total_frequency":d["total_frequency"],"fresh_entries":len(d["payload"])})
  fdiag=[]
  for d in deployed_f:
   old=w["fd_candidates"][d["id"]];omap={(tuple(x["attributes"])):x["degree"] for x in old["payload"]};nmap={tuple(x["attributes"]):x["degree"] for x in d["payload"]};keys=set(omap)|set(nmap);fdiag.append({"id":d["id"],"frozen_size":old["cost_bytes"],"fresh_size":d["fresh_size"],"dependencies_frozen":len(omap),"dependencies_fresh":len(nmap),"max_degree_change":max((abs(omap.get(k,0)-nmap.get(k,0)) for k in keys),default=0)})
  Lf=frozen_loss;Lr=sum(fresh_losses);Lp=sum(native_losses);fresh_storage=sum(d["fresh_size"] for d in deployed_m+deployed_f)
  worst=sorted(range(len(relerr)),key=lambda i:relerr[i],reverse=True)[:10];driftworst=sorted(range(len(drift)),key=lambda i:drift[i],reverse=True)[:10]
  snapshot={"relation_rows":relation_rows,"reltuples":reltuples,"mcv":deployed_m,"fd":deployed_f,"queries":fresh_queries}
  if a.payloads:a.payloads.write_text(json.dumps(snapshot,indent=2)+"\n")
  result={"experiment":"Mixed-Deploy-v0","manifest":str(a.manifest),"run":{"timestamp_epoch":time.time(),"postgres_version":version,"target":a.target,"relation_rows_raw":relation_rows,"reltuples":reltuples,"settings":{"default_statistics_target":settings[0],"effective_cache_size":settings[1],"random_page_cost":settings[2]},"create_seconds":create_s,"analyze_seconds":analyze_s,"order_verified":order_ok},"design":{"selected_mcv":len(sm),"selected_fd":len(sf),"actual_oids":{"mcv":[{"id":d["id"],"oid":d["oid"]} for d in deployed_m],"fd":[{"id":d["id"],"oid":d["oid"]} for d in deployed_f]}},"loss":{"frozen":Lf,"fresh_replay":Lr,"fresh_pg":Lp,"payload_drift":Lr-Lf,"payload_drift_percent":(Lr/Lf-1)*100,"semantic_error":Lp-Lr},"semantic":{"queries":len(relerr),"matches_1e_12":sum(x<=1e-12 for x in relerr),"bitwise_rows":sum(struct.pack('!d',x)==struct.pack('!d',y) for x,y in zip(fresh_rows,native_rows)),"max_relative_error":max(relerr),"median_relative_error":statistics.median(relerr),"max_absolute_error":max(abserr),"worst":[{"query":i+1,"external":fresh_rows[i],"native":native_rows[i],"relative_error":relerr[i]} for i in worst]},"correctness_layers":{"mcv_trace":{"checked":468,"matches":sum(mcv_trace_match),"max_error":0 if all(mcv_trace_match) else 1},"estimatedclauses":{"checked":0,"matches":0,"max_error":None,"note":"native instrumentation does not emit the full set"},"fd_trace":{"checked":0,"matches":0,"max_error":None,"note":"native CHOOSE trace lacks source statistic identity; preserved diagnostically"},"raw_selectivity":{"checked":468,"matches_1e_12":sum(abs(fresh_rows[i]/relation_rows-native_sel[i])/max(abs(native_sel[i]),1e-300)<=1e-12 for i in range(468)),"max_relative_error":max(abs(fresh_rows[i]/relation_rows-native_sel[i])/max(abs(native_sel[i]),1e-300) for i in range(468))},"raw_rows":{"checked":468,"matches_1e_12":sum(x<=1e-12 for x in relerr),"max_relative_error":max(relerr)}},"consumption":{"selected_fd":len(sf),"fresh_consumed_fd":len(consumed_fd),"fresh_never_consumed":sorted(sf-consumed_fd),"frozen_consumed_fd":len(frozen_consumed),"queries_changed_fd_trace":len(changed_fd_queries),"changed_query_ids":[i+1 for i in changed_fd_queries]},"drift":{"estimate_factor":{"median":statistics.median(drift),"p90":pct(drift,.9),"p95":pct(drift,.95),"p99":pct(drift,.99),"max":max(drift)},"qerror_delta":{"median":statistics.median(qed),"p90":pct(qed,.9),"p95":pct(qed,.95),"p99":pct(qed,.99),"max":max(qed)},"worst":[{"query":i+1,"factor":drift[i],"frozen":frozen_rows[i],"fresh":fresh_rows[i]} for i in driftworst]},"storage":{"frozen":frozen_storage,"fresh":fresh_storage,"change":fresh_storage-frozen_storage,"fresh_mcv":sum(d["fresh_size"] for d in deployed_m),"fresh_fd":sum(d["fresh_size"] for d in deployed_f)},"payload_diagnostics":{"mcv":mdiag,"fd":fdiag},"cross_sensitive_moves":sensitive,"per_query":[{"query":i+1,"truth":fresh_queries[i]["truth"],"frozen_rows":frozen_rows[i],"fresh_rows":fresh_rows[i],"native_rows":native_rows[i],"semantic_relative_error":relerr[i],"drift_factor":drift[i],"frozen_fd_trace":frozen_fdtr[i],"fresh_fd_trace":fresh_fdtr[i],"external_mcv_trace":ext_mcv[i],"native_mcv_trace":native_traces[i]["mcv"],"boundary":boundaries[i]} for i in range(468)]}
  a.output.write_text(json.dumps(result,indent=2)+"\n")
  md=f"""# Mixed-Deploy-v0

| Metric | Value |
|---|---:|
| selected MCV | {len(sm)} |
| selected FD | {len(sf)} |
| frozen loss | {Lf:.12f} |
| fresh replay loss | {Lr:.12f} |
| fresh native PG loss | {Lp:.12f} |
| payload drift | {Lr-Lf:.12f} |
| payload drift percent | {(Lr/Lf-1)*100:.4f}% |
| semantic error | {Lp-Lr:.12g} |
| max per-query semantic relative error | {max(relerr):.3g} |
| queries within 1e-12 | {sum(x<=1e-12 for x in relerr)} / 468 |
| frozen storage | {frozen_storage:,} bytes |
| fresh storage | {fresh_storage:,} bytes |
| selected FD consumed after deployment | {len(consumed_fd)} / {len(sf)} |

## Correctness layers

| Layer | Queries checked | Exact/tolerance matches | Max error |
|---|---:|---:|---:|
| MCV trace | 468 | {sum(mcv_trace_match)} | {0 if all(mcv_trace_match) else 1} |
| estimatedclauses | 0 | — | not emitted by native instrumentation |
| FD trace identity | 0 | — | native CHOOSE lacks source-statistic identity |
| raw selectivity | 468 | {result['correctness_layers']['raw_selectivity']['matches_1e_12']} | {result['correctness_layers']['raw_selectivity']['max_relative_error']:.3g} |
| raw rows | 468 | {sum(x<=1e-12 for x in relerr)} | {max(relerr):.3g} |

The deployed OID order matches the frozen intra-mechanism policy. The report
does not claim completeness for intermediate layers absent from instrumentation.
Payload drift and semantic replay error are kept separate.

## Final verdict

1. **Yes.** The selected mixed design and intended fixed intra-mechanism order were physically realized.
2. **{'Yes' if all(x<=1e-12 for x in relerr) else 'No'}.** Fresh replay matches all 468 native raw-row estimates within 1e-12: {sum(x<=1e-12 for x in relerr)}/468.
3. Maximum per-query semantic relative error is `{max(relerr):.3g}`.
4. Fresh native minus fresh replay workload loss is `{Lp-Lr:.12g}`.
5. Frozen-to-fresh deployment drift is `{Lr-Lf:.12f}` (`{(Lr/Lf-1)*100:.4f}%`).
6. MCV→FD consumption changed on {len(changed_fd_queries)} queries relative to the frozen realization; fresh external replay remains the semantic reference for the same snapshot.
7. Selected FD objects never consumed after deployment: `{len(sf-consumed_fd)}`.
8. Payload storage changed by `{fresh_storage-frozen_storage:,}` bytes ({frozen_storage:,} → {fresh_storage:,}).
9. The dominant uncertainty is **{'payload realization' if abs(Lr-Lf)>abs(Lp-Lr) else 'semantic replay'}**.
10. **{'Yes' if order_ok and all(x<=1e-12 for x in relerr) else 'No'}.** This closes the physical loop for the supported PostgreSQL 16 base-restriction MCV+FD fragment only.
""";a.report.write_text(md);print(json.dumps({"loss":result["loss"],"semantic":result["semantic"],"storage":result["storage"],"consumption":result["consumption"]},indent=2))
 finally:con.close()
if __name__=="__main__":main()
