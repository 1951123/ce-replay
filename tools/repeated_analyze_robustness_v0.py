#!/usr/bin/env python3
"""Repeated ANALYZE variability for one fixed deployed mixed MCV+FD design."""
from __future__ import annotations
import argparse,csv,json,math,re,statistics,struct,time
from collections import Counter,defaultdict
from pathlib import Path
import psycopg
from ce_replay_optimize_v1 import combine,item_matches,load_queries,qerror
from ce_replay_optimize_v4 import parse_binary_payload,replay_mcv_stage,replay_fd_stage
from mixed_deploy_v0 import final_design,pct,text
RAW_RE=re.compile(r"CE_REPLAY_RAW_ROWS .* rows=([^ ]+) selectivity=([^ ]+)")

def mean(xs):return statistics.fmean(xs)
def cv(xs):
 m=mean(xs);return statistics.pstdev(xs)/abs(m) if m else 0.0
def ranks(xs):
 order=sorted(range(len(xs)),key=xs.__getitem__);out=[0.0]*len(xs);i=0
 while i<len(xs):
  j=i+1
  while j<len(xs) and xs[order[j]]==xs[order[i]]:j+=1
  v=(i+j-1)/2+1
  for k in range(i,j):out[order[k]]=v
  i=j
 return out
def pearson(x,y):
 mx,my=mean(x),mean(y);dx=[a-mx for a in x];dy=[b-my for b in y];den=math.sqrt(sum(a*a for a in dx)*sum(b*b for b in dy));return sum(a*b for a,b in zip(dx,dy))/den if den else 0.0

def main():
 ap=argparse.ArgumentParser();ap.add_argument("--v4",type=Path,required=True);ap.add_argument("--optimizer",type=Path,required=True);ap.add_argument("--manifest",type=Path,required=True);ap.add_argument("--mixed",type=Path,required=True);ap.add_argument("--queries",type=Path,required=True);ap.add_argument("--runs",type=int,default=30);ap.add_argument("--output",type=Path,required=True);ap.add_argument("--report",type=Path,required=True);ap.add_argument("--runs-csv",type=Path,required=True);ap.add_argument("--host",default="/tmp");ap.add_argument("--port",type=int,default=55433);ap.add_argument("--user",default="postgres");ap.add_argument("--db",default="census");a=ap.parse_args()
 v4=json.loads(a.v4.read_text());opt=json.loads(a.optimizer.read_text());manifest=json.loads(a.manifest.read_text());oldmixed=json.loads(a.mixed.read_text());w=v4["workload_ir"];rawq=load_queries(a.queries);sm,sf,_=final_design(opt,v4);assert sorted(sm)==manifest["selected_mcv"] and sorted(sf)==manifest["selected_fd"]
 con=psycopg.connect(host=a.host,port=a.port,user=a.user,dbname=a.db,autocommit=True);cur=con.cursor();notices=[];con.add_notice_handler(lambda d:notices.append(d.message_primary));prefix="mixed_deploy_"
 def native(where):
  notices.clear();cur.execute(f"EXPLAIN SELECT * FROM climate WHERE {where}");m=[x for x in notices if x.startswith("CE_REPLAY_RAW_ROWS")]
  if len(m)!=1:raise RuntimeError((where,m))
  z=RAW_RE.match(m[0]);return float(z.group(1))
 try:
  cur.execute("SELECT s.oid,s.stxname,s.stxkind,s.stxstattarget FROM pg_statistic_ext s WHERE s.stxrelid='climate'::regclass ORDER BY s.oid");cat=cur.fetchall()
  if len(cat)!=261 or sum('m' in x[2] for x in cat)!=205 or sum('f' in x[2] for x in cat)!=56 or any(not text(x[1]).startswith(prefix) for x in cat):raise RuntimeError("deployed catalog is not the fixed 205+56 design")
  if any(int(x[3])!=manifest["target"] for x in cat):raise RuntimeError("statistics target changed")
  mrows=[x for x in cat if 'm' in x[2]];frows=[x for x in cat if 'f' in x[2]];mids=[x["id"] for x in manifest["mcv"]];fids=[x["id"] for x in manifest["fd"]]
  if len(mids)!=len(mrows) or len(fids)!=len(frows):raise RuntimeError("manifest/catalog mismatch")
  mdeploy=[{"id":i,"oid":int(row[0]),"rank":rank} for rank,(i,row) in enumerate(zip(mids,mrows))];fdeploy=[{"id":i,"oid":int(row[0]),"rank":rank} for rank,(i,row) in enumerate(zip(fids,frows))]
  cur.execute("SELECT count(*),md5(string_agg(md5(t::text),'' ORDER BY ctid)) FROM climate t");table_count,table_hash=cur.fetchone()
  cur.execute("SELECT attnum,attname FROM pg_attribute WHERE attrelid='climate'::regclass AND attnum>0");att={int(n):text(s).lower() for n,s in cur.fetchall()}
  mcols={d["id"]:w["mcv_candidates"][d["id"]]["columns"] for d in mdeploy};mpayloadcols={}
  for d in mdeploy:
   cur.execute("SELECT a.attname FROM pg_statistic_ext s CROSS JOIN LATERAL unnest(s.stxkeys::smallint[]) WITH ORDINALITY k(attnum,ord) JOIN pg_attribute a ON a.attrelid=s.stxrelid AND a.attnum=k.attnum WHERE s.oid=%s ORDER BY k.ord",(d["oid"],));mpayloadcols[d["id"]]=[text(x[0]).lower() for x in cur.fetchall()]
  runrows=[];all_est=[[] for _ in rawq];all_qerr=[[] for _ in rawq];all_mt=[[] for _ in rawq];all_ft=[[] for _ in rawq];semantic_rel=[];semantic_abs=[];bitwise=0
  mcand={i:{"sizes":[],"total_frequency":[],"relevant_frequency":[],"relevant_base_frequency":[],"consumed":[]} for i in sm};fcand={i:{"sizes":[],"available":[],"degree_vectors":[],"consumed":[]} for i in sf}
  started=time.perf_counter()
  for run in range(1,a.runs+1):
   t=time.perf_counter();cur.execute("ANALYZE climate");analyze_s=time.perf_counter()-t;alloids=[d["oid"] for d in mdeploy+fdeploy]
   freshm={};freshf={}
   for d in mdeploy:
    cur.execute("SELECT pg_column_size(stxdmcv) FROM pg_statistic_ext_data WHERE stxoid=%s AND NOT stxdinherit",(d["oid"],));size=cur.fetchone()[0]
    cur.execute("SELECT values,nulls,frequency,base_frequency FROM pg_statistic_ext_data CROSS JOIN LATERAL pg_mcv_list_items(stxdmcv) WHERE stxoid=%s AND NOT stxdinherit",(d["oid"],));items=[{"values":[text(v) if v is not None else None for v in vals],"nulls":nulls,"frequency":float(fr),"base_frequency":float(ba)} for vals,nulls,fr,ba in cur.fetchall()]
    freshm[d["id"]]={"size":int(size or 0),"items":items,"total":sum(x["frequency"] for x in items)};mcand[d["id"]]["sizes"].append(int(size or 0));mcand[d["id"]]["total_frequency"].append(freshm[d["id"]]["total"])
   for d in fdeploy:
    cur.execute("SELECT pg_column_size(stxddependencies),pg_dependencies_send(stxddependencies) FROM pg_statistic_ext_data WHERE stxoid=%s AND NOT stxdinherit",(d["oid"],));size,b=cur.fetchone()
    payload=[] if b is None else parse_binary_payload(b,att)
    freshf[d["id"]]={"size":int(size or 0),"payload":payload};fcand[d["id"]]["sizes"].append(int(size or 0));fcand[d["id"]]["available"].append(bool(payload));fcand[d["id"]]["degree_vectors"].append({','.join(x["attributes"]):x["degree"] for x in payload})
   # Preserve this realization while temporarily disabling extstats to refresh base context.
   cur.execute("CREATE TEMP TABLE repeat_backup AS SELECT stxoid,stxdmcv,stxddependencies FROM pg_statistic_ext_data WHERE stxoid=ANY(%s)",(alloids,));cur.execute("UPDATE pg_statistic_ext_data SET stxdmcv=NULL,stxddependencies=NULL WHERE stxoid=ANY(%s)",(alloids,));relation=native("TRUE")
   fq=[];relevant=defaultdict(lambda:[0.0,0.0])
   for old,rq in zip(w["queries"],rawq):
    base=native(rq["where"]);simple={}
    for col in old["fd_columns"]:simple[col]=native(" AND ".join(f"{col}{op}{val}" for op,val in rq["predicates"][col]))/relation
    ratios={}
    for cid in old["mcv_ids"]:
     if cid not in sm:continue
     simp=native(" AND ".join(f"{col}{op}{val}" for col in mcols[cid] for op,val in rq["predicates"][col]))/relation;mv=bv=tot=0.0
     for it in freshm[cid]["items"]:
      tot+=it["frequency"]
      if all(item_matches(it["values"][j],it["nulls"][j],rq["predicates"][col]) for j,col in enumerate(mpayloadcols[cid])):mv+=it["frequency"];bv+=it["base_frequency"]
     relevant[cid][0]+=mv;relevant[cid][1]+=bv;ratios[str(cid)]=combine(simp,mv,bv,tot)/simp
    fq.append({"truth":old["truth"],"predicates":old["predicates"],"baseline_rows":base,"mcv_ids":[i for i in old["mcv_ids"] if i in sm],"mcv_ratios":ratios,"fd_columns":old["fd_columns"],"simple_selectivities":simple,"fd_ids":[i for i in old["fd_ids"] if i in sf]})
   cur.execute("UPDATE pg_statistic_ext_data d SET stxdmcv=b.stxdmcv,stxddependencies=b.stxddependencies FROM repeat_backup b WHERE d.stxoid=b.stxoid");cur.execute("DROP TABLE repeat_backup")
   fm=[dict(x) for x in w["mcv_candidates"]];ff=[dict(x) for x in w["fd_candidates"]]
   for d in mdeploy:fm[d["id"]]["oid_rank"]=d["rank"]
   for d in fdeploy:ff[d["id"]].update({"oid_rank":d["rank"],"payload":freshf[d["id"]]["payload"]})
   erows=[];mt=[];ft=[];cm=set();cf=set()
   for qi,q in enumerate(fq):
    b=replay_mcv_stage(q,sm,fm,{d["id"]:d["rank"] for d in mdeploy});nr,tr,_=replay_fd_stage(q,b[0],b[1],sf,ff,detailed=True);erows.append(nr);mt.append(tuple(b[2]));ft.append(tuple(x["fid"] for x in tr));cm.update(b[2]);cf.update(x["fid"] for x in tr)
   nrows=[native(q["where"]) for q in rawq];loss=sum(qerror(r,q["truth"]) for r,q in zip(erows,fq));storage=sum(x["size"] for x in freshm.values())+sum(x["size"] for x in freshf.values());rels=[]
   for qi,(e,n,q) in enumerate(zip(erows,nrows,fq)):
    rr=abs(e-n)/max(abs(n),1e-300);rels.append(rr);semantic_rel.append(rr);semantic_abs.append(abs(e-n));bitwise+=struct.pack('!d',e)==struct.pack('!d',n);all_est[qi].append(e);all_qerr[qi].append(qerror(e,q["truth"]));all_mt[qi].append(mt[qi]);all_ft[qi].append(ft[qi])
   for cid in sm:mcand[cid]["relevant_frequency"].append(relevant[cid][0]);mcand[cid]["relevant_base_frequency"].append(relevant[cid][1]);mcand[cid]["consumed"].append(cid in cm)
   for cid in sf:fcand[cid]["consumed"].append(cid in cf)
   runrows.append({"run":run,"loss":loss,"frozen_relative_drift":loss/manifest["frozen_loss"]-1,"storage":storage,"mcv_storage":sum(x["size"] for x in freshm.values()),"fd_storage":sum(x["size"] for x in freshf.values()),"consumed_mcv":len(cm),"consumed_fd":len(cf),"available_fd":sum(bool(x["payload"]) for x in freshf.values()),"semantic_matches_1e_12":sum(x<=1e-12 for x in rels),"semantic_max_relative_error":max(rels),"analyze_seconds":analyze_s,"total_seconds":time.perf_counter()-t})
  losses=[x["loss"] for x in runrows];drifts=[x["frozen_relative_drift"] for x in runrows];stores=[x["storage"] for x in runrows]
  qsum=[];cats=Counter()
  for i,(est,qe,mts,fts) in enumerate(zip(all_est,all_qerr,all_mt,all_ft)):
   mv=len(set(mts))>1;fv=len(set(fts))>1;vary=len(set(struct.pack('!d',x) for x in est))>1
   cat=("both_mcv_fd_control_vary" if mv and fv else "mcv_control_varies" if mv else "fd_control_varies" if fv else "stable_control_numerical_varies" if vary else "stable_control_stable_estimate");cats[cat]+=1
   qsum.append({"query":i+1,"estimate_min":min(est),"estimate_median":statistics.median(est),"estimate_max":max(est),"estimate_cv":cv(est),"qerror_mean":mean(qe),"qerror_std":statistics.pstdev(qe),"qerror_max":max(qe),"mcv_trace_variants":len(set(mts)),"fd_trace_variants":len(set(fts)),"class":cat,"consumed_mcv":sorted(set(x for t in mts for x in t)),"consumed_fd":sorted(set(x for t in fts for x in t))})
  top=sorted(qsum,key=lambda x:(x["estimate_cv"],x["qerror_std"]),reverse=True)[:20]
  ms=[]
  for cid,v in mcand.items():ms.append({"id":cid,"size_min":min(v["sizes"]),"size_max":max(v["sizes"]),"size_changes":len(set(v["sizes"]))>1,"total_frequency_cv":cv(v["total_frequency"]),"relevant_frequency_cv":cv(v["relevant_frequency"]),"relevant_base_frequency_cv":cv(v["relevant_base_frequency"]),"consumption_frequency":mean(v["consumed"])})
  fs=[]
  for cid,v in fcand.items():
   keys=set(k for d in v["degree_vectors"] for k in d);degree_values=[d.get(k,0.0) for d in v["degree_vectors"] for k in keys]
   fs.append({"id":cid,"availability_frequency":mean(v["available"]),"availability_count":sum(v["available"]),"size_min":min(v["sizes"]),"size_max":max(v["sizes"]),"degree_range_max":max((max(d.get(k,0) for d in v["degree_vectors"])-min(d.get(k,0) for d in v["degree_vectors"]) for k in keys),default=0),"consumption_frequency":mean(v["consumed"])})
  oldloss=oldmixed["loss"]["fresh_pg"];oldrank=sum(x<=oldloss for x in losses);oldpct=100*oldrank/len(losses)
  result={"experiment":"Repeated-Analyze-Robustness-v0","fixed_design":{"mcv":205,"fd":56,"target":manifest["target"],"table_rows":int(table_count),"table_hash":table_hash,"catalog_verified":True,"oid_order_unchanged":True},"runs":len(runrows),"semantic":{"comparisons":468*len(runrows),"bitwise":bitwise,"matches_1e_12":sum(x<=1e-12 for x in semantic_rel),"max_absolute_error":max(semantic_abs),"max_relative_error":max(semantic_rel)},"loss":{"frozen":manifest["frozen_loss"],"min":min(losses),"p05":pct(losses,.05),"p25":pct(losses,.25),"mean":mean(losses),"median":statistics.median(losses),"p75":pct(losses,.75),"p95":pct(losses,.95),"max":max(losses),"std":statistics.pstdev(losses),"cv":cv(losses)},"drift":{"min":min(drifts),"median":statistics.median(drifts),"mean":mean(drifts),"p95":pct(drifts,.95),"max":max(drifts),"below_frozen":sum(x<manifest["frozen_loss"] for x in losses),"above_frozen":sum(x>manifest["frozen_loss"] for x in losses)},"storage":{"frozen":manifest["frozen_storage"],"min":min(stores),"mean":mean(stores),"median":statistics.median(stores),"max":max(stores),"std":statistics.pstdev(stores),"exceeds_frozen":sum(x>manifest["frozen_storage"] for x in stores)},"loss_storage_correlation":{"pearson":pearson(losses,stores),"spearman":pearson(ranks(losses),ranks(stores))},"trace_classes":dict(cats),"old_mixed_deploy":{"loss":oldloss,"empirical_rank_le":oldrank,"empirical_percentile_le":oldpct},"fd_availability":{"always":sum(x["availability_frequency"]==1 for x in fs),"intermittent":sum(0<x["availability_frequency"]<1 for x in fs),"never":sum(x["availability_frequency"]==0 for x in fs),"fd97":next(x for x in fs if x["id"]==97),"fd683":next(x for x in fs if x["id"]==683)},"candidate_consumption":{"mcv_always":sum(x["consumption_frequency"]==1 for x in ms),"mcv_sometimes":sum(0<x["consumption_frequency"]<1 for x in ms),"mcv_never":sum(x["consumption_frequency"]==0 for x in ms),"fd_always":sum(x["consumption_frequency"]==1 for x in fs),"fd_sometimes":sum(0<x["consumption_frequency"]<1 for x in fs),"fd_never":sum(x["consumption_frequency"]==0 for x in fs)},"mcv_payload":{"size_never_changes":sum(not x["size_changes"] for x in ms),"size_changes":sum(x["size_changes"] for x in ms),"most_variable_relevant_frequency":sorted(ms,key=lambda x:x["relevant_frequency_cv"],reverse=True)[:20]},"query_summary":qsum,"top_unstable_queries":top,"mcv_candidates":ms,"fd_candidates":fs,"per_run":runrows,"runtime_seconds":time.perf_counter()-started}
  a.output.write_text(json.dumps(result,indent=2)+"\n")
  with a.runs_csv.open('w',newline='') as f:wr=csv.DictWriter(f,fieldnames=list(runrows[0]));wr.writeheader();wr.writerows(runrows)
  L=result["loss"];S=result["storage"];sem=result["semantic"];inv=cats["stable_control_stable_estimate"]+cats["stable_control_numerical_varies"]
  md=f"""# Repeated-Analyze-Robustness-v0

| Metric | Value |
|---|---:|
| ANALYZE realizations | {a.runs} |
| query-realization semantic comparisons | {sem['comparisons']:,} |
| replay/native strict matches | {sem['matches_1e_12']:,} |
| max semantic relative error | {sem['max_relative_error']:.3g} |
| workload loss mean | {L['mean']:.6f} |
| workload loss std | {L['std']:.6f} |
| workload loss min | {L['min']:.6f} |
| workload loss median | {L['median']:.6f} |
| workload loss max | {L['max']:.6f} |
| mean frozen-relative drift | {result['drift']['mean']:.4%} |
| p95 frozen-relative drift | {result['drift']['p95']:.4%} |
| total storage mean | {S['mean']:.1f} bytes |
| total storage min | {S['min']} bytes |
| total storage max | {S['max']} bytes |
| queries with invariant control trace | {inv} / 468 |
| queries with varying MCV trace | {cats['mcv_control_varies']+cats['both_mcv_fd_control_vary']} |
| queries with varying FD trace | {cats['fd_control_varies']+cats['both_mcv_fd_control_vary']} |
| intermittently unavailable FD objects | {result['fd_availability']['intermittent']} |

All realizations use the same 205 MCV and 56 FD catalog objects, targets and
OID order. Full raw measurements and candidate/query summaries are in JSON.

## Final verdict

1. **{'Yes' if sem['matches_1e_12']==sem['comparisons'] else 'No'}.** CE-Replay matched {sem['matches_1e_12']}/{sem['comparisons']} query-realization pairs within 1e-12.
2. Loss ranged `{L['min']:.6f}–{L['max']:.6f}`, mean `{L['mean']:.6f}`, median `{L['median']:.6f}`, std `{L['std']:.6f}`.
3. The original loss `{oldloss:.6f}` is at empirical percentile `{oldpct:.1f}%` (rank {oldrank}/{a.runs} by `<=`).
4. Control classification: `{dict(cats)}`. The balance determines whether variability is numerical or structural.
5. MCV payload size changed for `{result['mcv_payload']['size_changes']}/205` objects; frequency variability is detailed in JSON.
6. FD availability: `{result['fd_availability']['always']}` always, `{result['fd_availability']['intermittent']}` intermittent, `{result['fd_availability']['never']}` never. FD 97 availability is `{result['fd_availability']['fd97']['availability_frequency']:.1%}` and FD 683 `{result['fd_availability']['fd683']['availability_frequency']:.1%}`.
7. Storage ranged `{S['min']}–{S['max']}` bytes (mean `{S['mean']:.1f}`, std `{S['std']:.1f}`); it exceeded frozen storage in `{S['exceeds_frozen']}/{a.runs}` runs.
8. The top unstable queries and associated consumed MCV/FD objects are listed in `top_unstable_queries`; the most variable workload-relevant MCV objects are listed separately.
9. Frozen-payload risk is assessed from loss CV `{L['cv']:.4%}`, drift range `{result['drift']['min']:.4%}–{result['drift']['max']:.4%}`, and trace/availability instability—not semantic replay error.
10. Robust optimization should be immediate follow-up only if the measured loss and structural variability are material; otherwise it remains future work. The measured classification above is the evidence for that decision.
""";a.report.write_text(md);print(json.dumps({"runs":a.runs,"semantic":result["semantic"],"loss":result["loss"],"storage":result["storage"],"trace_classes":result["trace_classes"],"fd_availability":result["fd_availability"]},indent=2))
 finally:con.close()
if __name__=='__main__':main()
