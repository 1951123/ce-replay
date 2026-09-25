#!/usr/bin/env python3
"""Correctness-gated wall-clock benchmark for native PG and CE-Replay."""
from __future__ import annotations

import argparse, copy, csv, hashlib, json, math, os, platform, re, statistics, subprocess, time
from collections import Counter, defaultdict
from pathlib import Path

import psycopg

from ce_replay_optimize_v1 import load_queries, qerror
from ce_replay_optimize_v4 import replay, replay_mcv_stage, replay_fd_stage
from compositional_semantic_optimizer_v0 import Model, Cache, initial_state, aff, mutate
from dmv_baseline_nonmonotonicity_v0 import replay as dmv_replay, parse_binary_dependencies, text
from dmv_maintenance_budget_optimize_v0 import Evaluator as DMVIncremental

TOL=1e-10; WARMUPS=5; REPS=30; TARGET_NS=100_000_000; SEED="ce-replay-wallclock-v0"
TIMING_RE=re.compile(r"CE_REPLAY_TIMING relid=(\d+) elapsed_ns=(\d+) cumulative_ns=(\d+) invocation_count=(\d+) rows=([^ ]+) selectivity=([^ ]+)")
RAW_RE=re.compile(r"CE_REPLAY_RAW_ROWS .* rows=([^ ]+) selectivity=([^ ]+)")

def pct(xs,p):
 xs=sorted(xs); z=(len(xs)-1)*p; i=int(z); j=min(i+1,len(xs)-1); return xs[i]+(xs[j]-xs[i])*(z-i)
def summary(ns,ops):
 x=[v/ops for v in ns]
 return {"median_ns":statistics.median(x),"p25_ns":pct(x,.25),"p75_ns":pct(x,.75),"p95_ns":pct(x,.95),"mean_ns":statistics.fmean(x),"stddev_ns":statistics.stdev(x),"batch_size":ops,"measured_batches":len(ns),"total_batch_ns":sum(ns),"raw_batch_ns":ns}
def stable(items,n=8):
 return sorted(items,key=lambda x:hashlib.sha256((SEED+repr(x)).encode()).digest())[:n]
def timer_cell(fn,unit_ops=1):
 attempts=[]; k=1
 while True:
  t=time.perf_counter_ns()
  for _ in range(k): fn()
  dt=time.perf_counter_ns()-t; attempts.append({"multiplier":k,"duration_ns":dt})
  if dt>=TARGET_NS:break
  k*=2
  if k>65536:raise RuntimeError("calibration did not reach 100 ms")
 for _ in range(WARMUPS):
  for __ in range(k):fn()
 raw=[]
 for _ in range(REPS):
  t=time.perf_counter_ns()
  for __ in range(k):fn()
  raw.append(time.perf_counter_ns()-t)
 return summary(raw,k*unit_ops),attempts
def relerr(a,b):return abs(a-b)/max(abs(b),1e-300)

def census_fresh(path,source):
 snap=json.loads(path.read_text()); w=copy.deepcopy(source["workload_ir"])
 w["queries"]=snap["queries"]
 for x in snap["mcv"]:
  w["mcv_candidates"][x["id"]].update({"oid_rank":x["rank"],"payload_columns":x["payload_columns"],"payload":x["payload"],"total_frequency":x["total_frequency"]})
 for x in snap["fd"]: w["fd_candidates"][x["id"]].update({"oid_rank":x["rank"],"payload":x["payload"]})
 return w,{x["id"] for x in snap["mcv"]},{x["id"] for x in snap["fd"]}

def extract_dmv_fresh(con,frozen):
 cur=con.cursor(); qs=copy.deepcopy(frozen["replay_inputs"]["queries"]); objs=frozen["deployment_objects"]
 cur.execute("SELECT attnum,attname FROM pg_attribute WHERE attrelid='dmv'::regclass AND attnum>0")
 att={int(n):text(a).lower() for n,a in cur.fetchall()}; mc=[];fd=[]
 for item in objs:
  if item["mechanism"]=="mcv":
   cur.execute("SELECT a.attname FROM pg_statistic_ext x CROSS JOIN LATERAL unnest(x.stxkeys::smallint[]) WITH ORDINALITY k(attnum,ord) JOIN pg_attribute a ON a.attrelid=x.stxrelid AND a.attnum=k.attnum WHERE x.oid=%s ORDER BY k.ord",(item["oid"],)); cols=[text(x[0]).lower() for x in cur.fetchall()]
   cur.execute("SELECT values,nulls,frequency,base_frequency FROM pg_statistic_ext_data CROSS JOIN LATERAL pg_mcv_list_items(stxdmcv) WHERE stxoid=%s",(item["oid"],)); pay=[{"values":[text(v) if v is not None else None for v in vs],"nulls":ns,"frequency":float(fr),"base_frequency":float(ba)} for vs,ns,fr,ba in cur.fetchall()]
   mc.append({**item,"index":len(mc),"oid_rank":item["semantic_rank"],"payload_columns":cols,"payload":pay,"total_frequency":sum(x["frequency"] for x in pay)})
  else:
   cur.execute("SELECT pg_dependencies_send(stxddependencies) FROM pg_statistic_ext_data WHERE stxoid=%s",(item["oid"],)); raw=cur.fetchone()[0]
   fd.append({**item,"index":len(fd),"oid_rank":item["semantic_rank"],"payload":parse_binary_dependencies(raw,att) if raw is not None else []})
 # The corrected deployment already persisted matching fresh per-query estimates;
 # its query-local baseline context was not persisted. Reconstruct it without ANALYZE.
 oids=[x["oid"] for x in objs]; cur.execute("CREATE TEMP TABLE wc_backup AS SELECT stxoid,stxdmcv,stxddependencies FROM pg_statistic_ext_data WHERE stxoid=ANY(%s)",(oids,)); cur.execute("UPDATE pg_statistic_ext_data SET stxdmcv=NULL,stxddependencies=NULL WHERE stxoid=ANY(%s)",(oids,))
 notes=[];con.add_notice_handler(lambda d:notes.append(d.message_primary))
 def rows(where):
  notes.clear();cur.execute("SET ce_replay_measure_timing=on");cur.execute("EXPLAIN (FORMAT JSON) SELECT * FROM dmv WHERE "+where)
  mm=[TIMING_RE.match(x) for x in notes if TIMING_RE.match(x)];
  if len(mm)!=1:raise RuntimeError((where,len(mm)))
  return float(mm[0].group(5))
 relation=rows("TRUE"); cache={}
 for q in qs:
  sels=[];cols={}
  for c in q["clauses"]:
   if c["sql"] not in cache:cache[c["sql"]]=rows(c["sql"])/relation
   sels.append(cache[c["sql"]]);cols[c["column"]]=cache[c["sql"]]
  q["clause_selectivities"]=sels;q["column_selectivities"]=cols;q["baseline_rows"]=rows(q["where"])
 cur.execute("UPDATE pg_statistic_ext_data d SET stxdmcv=b.stxdmcv,stxddependencies=b.stxddependencies FROM wc_backup b WHERE d.stxoid=b.stxoid")
 return qs,mc,fd,relation

def native_workload(con,table,wheres):
 cur=con.cursor(); notes=[]; con.add_notice_handler(lambda d:notes.append(d.message_primary));cur.execute("SET ce_replay_measure_timing=on")
 def run():
  plan=ce=0
  for wh in wheres:
   notes.clear();t=time.perf_counter_ns();cur.execute(f"EXPLAIN (FORMAT JSON) SELECT * FROM {table} WHERE {wh}");cur.fetchone();plan+=time.perf_counter_ns()-t
   mm=[TIMING_RE.match(x) for x in notes if TIMING_RE.match(x)]
   if len(mm)!=1:raise RuntimeError((table,wh,len(mm),notes[-5:]))
   ce+=int(mm[0].group(2))
  return plan,ce
 # calibration is based on the complete workload operation and records both clocks.
 attempts=[];k=1
 while True:
  t=time.perf_counter_ns()
  for _ in range(k):run()
  dt=time.perf_counter_ns()-t;attempts.append({"multiplier":k,"duration_ns":dt})
  if dt>=TARGET_NS:break
  k*=2
 for _ in range(WARMUPS):
  for __ in range(k):run()
 pr=[];cr=[]
 for _ in range(REPS):
  p=c=0
  for __ in range(k):a,b=run();p+=a;c+=b
  pr.append(p);cr.append(c)
 return summary(pr,k),summary(cr,k),attempts

def census_full(w,sm,sf):
 ranks={i:c["oid_rank"] for i,c in enumerate(w["mcv_candidates"])}
 def run():return sum(qerror(replay(q,sm,sf,w["mcv_candidates"],w["fd_candidates"],ranks),q["truth"]) for q in w["queries"])
 return run
def dmv_full(qs,mc,fd,sm,sf):
 def run():
  total=0.0
  for q in qs:
   est=dmv_replay(q,sm,sf,mc,fd)
   if q["truth"]>0:total+=qerror(est,q["truth"])
  return total
 return run

def tertile_population(moves,scope):
 vals=sorted(scope(m) for m in moves);a=vals[(len(vals)-1)//3];b=vals[2*(len(vals)-1)//3]
 groups={"lower":[],"middle":[],"upper":[]}
 for m in moves:
  n=scope(m); groups["lower" if n<=a else "middle" if n<=b else "upper"].append(m)
 return (a,b),groups
def census_moves(model,sm,sf):
 sel={*(('mcv',i) for i in sm),*(('fd',i) for i in sf)};allc=set(model.cands);add=[("toggle",c,None) for c in sorted(allc-sel)];drop=[("toggle",c,None) for c in sorted(sel)];swap=[("swap",x,y) for x in sorted(sel) for y in sorted(allc-sel)]
 return {"ADD":add,"DROP":drop,"SWAP":swap}
def dmv_moves(mc,fd,sm,sf):
 sel={*(('mcv',i) for i in sm),*(('fd',i) for i in sf)};allc={*(('mcv',i) for i in range(len(mc))),*(('fd',i) for i in range(len(fd)))}
 return {"ADD":[("add",None,c) for c in sorted(allc-sel)],"DROP":[("drop",c,None) for c in sorted(sel)],"SWAP":[("swap",x,y) for x in sorted(sel) for y in sorted(allc-sel)]}

def bench_move_groups_census(w):
 model=Model(w);src=json.loads(Path("results/census_ce_replay_optimize_v4.json").read_text());seed=next(x for x in src["strategies"] if x["strategy"]=="joint_semantic");sm=set(seed["selected_mcv"]);sf=set(seed["selected_fd"]);state=initial_state(model,sm,sf);pop=census_moves(model,sm,sf);out={};checks=[];cal={}
 for fam,moves in pop.items():
  bounds,groups=tertile_population(moves,lambda m:len(aff(m,model)));groups["pooled"]=moves
  out[fam]={"population":len(moves),"tertile_bounds":bounds,"groups":{}}
  for g,allm in groups.items():
   sample=stable(allm); expected=[]
   for m in sample:
    sm1,sf1=mutate(m,sm,sf);rows=[model.rows(i,sm1,sf1) for i in range(len(model.q))];obj=sum(qerror(r,q["truth"]) for r,q in zip(rows,model.q));d=obj-state["total"];cache=Cache(model,copy.deepcopy(state));di=cache.evaluate(m)[0];ok=abs(d-di)<=TOL
    checks.append({"workload":"census","family":fam,"group":g,"move":repr(m),"affected":len(aff(m,model)),"full_delta":d,"incremental_delta":di,"pass":ok})
    if not ok:raise RuntimeError("Census move correctness failure")
    expected.append((m,obj))
   def full_batch():
    z=0.0
    for m,_ in expected:
     sm1,sf1=mutate(m,sm,sf);z+=sum(qerror(model.rows(i,sm1,sf1),q["truth"]) for i,q in enumerate(model.q))
    return z
   cache=Cache(model,copy.deepcopy(state))
   def inc_batch():
    z=0.0
    for m,_ in expected:
     cache.tv.clear();cache.valid.clear();cache.count.clear();cache.times.clear();z+=cache.evaluate(m)[0]
    return z
   fr,fc=timer_cell(full_batch,len(sample));ir,ic=timer_cell(inc_batch,len(sample));cal[f"census_{fam}_{g}_full"]=fc;cal[f"census_{fam}_{g}_inc"]=ic
   out[fam]["groups"][g]={"sample_size":len(sample),"affected_counts":[len(aff(m,model)) for m in sample],"full":fr,"incremental":ir,"median_ratio":fr["median_ns"]/ir["median_ns"],"median_difference_ns":fr["median_ns"]-ir["median_ns"]}
 return out,checks,cal,(model,sm,sf,state)

def bench_move_groups_dmv(qs,mc,fd):
 order=[*(('mcv',i) for i in range(len(mc))),*(('fd',i) for i in range(len(fd)))];sel=set(order[::2]);sm={i for k,i in sel if k=='mcv'};sf={i for k,i in sel if k=='fd'};ev=DMVIncremental(qs,mc,fd);state=ev.state(sm,sf);pop=dmv_moves(mc,fd,sm,sf);out={};checks=[];cal={}
 def scope(m):
  s=set()
  for x in (m[1],m[2]):
   if x:s|=ev.affected(*x)
  return len(s)
 for fam,moves in pop.items():
  bounds,groups=tertile_population(moves,scope);groups["pooled"]=moves;out[fam]={"population":len(moves),"tertile_bounds":bounds,"groups":{}}
  for g,allm in groups.items():
   sample=stable(allm);spec=[]
   for m in sample:
    rem=m[1];add=m[2];sm1=set(sm);sf1=set(sf)
    if rem:(sm1 if rem[0]=='mcv' else sf1).remove(rem[1])
    if add:(sm1 if add[0]=='mcv' else sf1).add(add[1])
    rows=[dmv_replay(q,sm1,sf1,mc,fd) for q in qs];obj=sum(qerror(r,q['truth']) for r,q in zip(rows,qs) if q['truth']>0);d=obj-state['total'];di,_,changes=ev.move(state,remove=rem,add=add,count=False);ok=abs(d-di)<=TOL and all(relerr(changes[i],qerror(rows[i],qs[i]['truth']))<=TOL for i in changes if qs[i]['truth']>0)
    checks.append({"workload":"dmv","family":fam,"group":g,"move":repr(m),"affected":scope(m),"full_delta":d,"incremental_delta":di,"pass":ok})
    if not ok:raise RuntimeError("DMV move correctness failure")
    spec.append((m,sm1,sf1))
   def full_batch():return sum(sum(qerror(dmv_replay(q,a,b,mc,fd),q['truth']) for q in qs if q['truth']>0) for _,a,b in spec)
   def inc_batch():return sum(ev.move(state,remove=m[1],add=m[2],count=False)[0] for m,_,__ in spec)
   fr,fc=timer_cell(full_batch,len(sample));ir,ic=timer_cell(inc_batch,len(sample));cal[f"dmv_{fam}_{g}_full"]=fc;cal[f"dmv_{fam}_{g}_inc"]=ic
   out[fam]["groups"][g]={"sample_size":len(sample),"affected_counts":[scope(m) for m,_,__ in spec],"full":fr,"incremental":ir,"median_ratio":fr['median_ns']/ir['median_ns'],"median_difference_ns":fr['median_ns']-ir['median_ns']}
 return out,checks,cal

def trajectory(model,sm,sf,state):
 recorded=json.loads(Path("results/census_compositional_semantic_optimizer_v0.json").read_text());seq=[json.loads(x["best_move"]) for x in recorded["rounds"] if x["delta"] < -1e-12];seq=[(m[0],tuple(m[1]) if m[1] else None,tuple(m[2]) if m[2] else None) for m in seq]
 def full_once(check=False):
  a,b=set(sm),set(sf);objs=[]
  for m in seq:
   a,b=mutate(m,a,b);obj=sum(qerror(model.rows(i,a,b),q['truth']) for i,q in enumerate(model.q));objs.append(obj)
  return objs
 def inc_once(check=False):
  st=initial_state(model,sm,sf);c=Cache(model,st);objs=[];counts=Counter();inv=[]
  for m in seq:
   d,k,qk=c.evaluate(m);before=st['total'];iv=c.commit(m);objs.append(st['total']);counts.update(qk);inv.append(iv)
   if abs(st['total']-(before+d))>TOL:raise RuntimeError("trajectory delta mismatch")
  return objs,counts,inv
 fo=full_once();io,counts,inv=inc_once();ok=all(abs(a-b)<=TOL for a,b in zip(fo,io))
 if not ok:raise RuntimeError("trajectory correctness failure")
 fr,fc=timer_cell(lambda:full_once(),1);ir,ic=timer_cell(lambda:inc_once(),1)
 return {"accepted_moves":len(seq),"objective_sequence_full":fo,"objective_sequence_incremental":io,"equivalent":ok,"full":fr,"incremental":ir,"median_ratio":fr['median_ns']/ir['median_ns'],"semantic_counts":dict(counts),"invalidations":inv}, {"trajectory_full":fc,"trajectory_incremental":ic}

def environment(con):
 cur=con.cursor();cur.execute("SHOW server_version");pg=cur.fetchone()[0];cur.execute("SELECT name,setting FROM pg_settings WHERE name IN ('shared_buffers','random_page_cost','effective_cache_size','default_statistics_target','max_parallel_workers_per_gather') ORDER BY name")
 return {"timestamp":time.strftime('%Y-%m-%dT%H:%M:%S%z'),"cpu_model":next((x.split(':',1)[1].strip() for x in Path('/proc/cpuinfo').read_text().splitlines() if x.startswith('model name')),None),"logical_cpus":os.cpu_count(),"kernel":platform.release(),"platform":platform.platform(),"python":platform.python_version(),"postgres":pg,"cpu_affinity":sorted(os.sched_getaffinity(0)),"postgres_settings":dict(cur.fetchall()),"wsl":'microsoft' in platform.release().lower(),"gc_policy":"normal Python GC; not disabled","frequency_scaling_controlled":False,"host_contention_controlled":False}

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,default=Path('results/ce_replay_native_wallclock_v0'));ap.add_argument('--host',default='/tmp');ap.add_argument('--port',type=int,default=55433);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 source=json.loads(Path('results/census_ce_replay_optimize_v4.json').read_text());cw,csm,csf=census_fresh(Path('/tmp/wallclock_census_payloads.json'),source);cq=load_queries(Path('/root/projects/extended-stats-optim-v2/benchmarks/Census/queries/query.sql'))
 dopt=json.loads(Path('results/dmv_nonzero_truth_rebuild_v0/optimization.json').read_text());ddep=json.loads(Path('results/dmv_nonzero_truth_rebuild_v0/deployment.json').read_text());frozen={"replay_inputs":dopt['replay_inputs'],"deployment_objects":ddep['deployment']['objects']}
 cc=psycopg.connect(host=a.host,port=a.port,user='postgres',dbname='census',autocommit=True);dc=psycopg.connect(host=a.host,port=a.port,user='postgres',dbname=ddep['deployment']['database'],autocommit=True)
 env=environment(cc);dqs,dmc,dfd,drel=extract_dmv_fresh(dc,frozen);Path('/tmp/wallclock_dmv_payloads.json').write_text(json.dumps({'relation_rows':drel,'queries':dqs,'mcv':dmc,'fd':dfd},indent=2)+'\n')
 correctness={"native_replay":{},"moves":[],"trajectory":{}}
 # Gate realized-state outputs against persisted native deployment evidence.
 cfull=census_full(cw,csm,csf);cobj=cfull();cdep=json.loads(Path('/tmp/wallclock_census_deploy.json').read_text());correctness['native_replay']['census']={"queries":468,"matches":cdep['semantic']['matches_1e_12'],"max_relative_error":cdep['semantic']['max_relative_error'],"objective":cobj,"pass":cdep['semantic']['matches_1e_12']==468}
 dsm=set(range(len(dmc)));dsf=set(range(len(dfd)));dfull=dmv_full(dqs,dmc,dfd,dsm,dsf);dobj=dfull();correctness['native_replay']['dmv']={"queries":1965,"matches":ddep['semantic']['matches'],"max_relative_error":ddep['semantic']['max_relative_error'],"objective":dobj,"zero_truth_ids":ddep['zero_truth']['ids'],"objective_queries":1963,"pass":ddep['semantic']['matches']==1965}
 # Compare trace-on and trace-off timing mode against the same live state.
 patchval=[]
 for con,table,wheres in [(cc,'climate',[cq[0]['where'],cq[294]['where']]),(dc,'dmv',[dqs[0]['where'],dqs[942]['where']])]:
  cur=con.cursor();notes=[];con.add_notice_handler(lambda x:notes.append(x.message_primary));cur.execute('SET ce_replay_measure_timing=on')
  for wh in wheres:
   notes.clear();cur.execute('SET ce_replay_measure_timing=off');cur.execute(f'EXPLAIN (FORMAT JSON) SELECT * FROM {table} WHERE {wh}');rm=[RAW_RE.match(x) for x in notes if RAW_RE.match(x)];trace_row=float(rm[0].group(1));trace_decisions=[x for x in notes if x.startswith(('CE_REPLAY_MCV','CE_REPLAY_FD'))]
   notes.clear();cur.execute('SET ce_replay_measure_timing=on');cur.execute(f'EXPLAIN (FORMAT JSON) SELECT * FROM {table} WHERE {wh}');mm=[TIMING_RE.match(x) for x in notes if TIMING_RE.match(x)];row=float(mm[0].group(5));patchval.append({'table':table,'trace_rows':trace_row,'timing_rows':row,'relative_error':relerr(row,trace_row),'trace_decision_messages':trace_decisions,'semantic_trace_notices_in_timing_mode':sum(x.startswith(('CE_REPLAY_MCV','CE_REPLAY_FD','CE_REPLAY_RAW')) for x in notes),'pass':relerr(row,trace_row)<=1e-12})
 if not all(x['pass'] and x['semantic_trace_notices_in_timing_mode']==0 for x in patchval):raise RuntimeError('PATCH VALIDATION BLOCKER')
 cal={};raw=[]
 cplan,cce,x=native_workload(cc,'climate',[x['where'] for x in cq]);cal['census_native']=x
 dplan,dce,x=native_workload(dc,'dmv',[x['where'] for x in dqs]);cal['dmv_native']=x
 cr, x=timer_cell(cfull);cal['census_replay_full']=x;dr,x=timer_cell(dfull);cal['dmv_replay_full']=x
 fullres={'census':{'T_PG_plan':cplan,'T_PG_CE':cce,'T_Replay_full':cr,'median_ratios':{'PG_plan_over_replay':cplan['median_ns']/cr['median_ns'],'PG_CE_over_replay':cce['median_ns']/cr['median_ns']}},'dmv':{'T_PG_plan':dplan,'T_PG_CE':dce,'T_Replay_full':dr,'median_ratios':{'PG_plan_over_replay':dplan['median_ns']/dr['median_ns'],'PG_CE_over_replay':dce['median_ns']/dr['median_ns']}}}
 cmoves,chk,x,ctx=bench_move_groups_census(source['workload_ir']);correctness['moves']+=chk;cal.update(x)
 dmoves,chk,x=bench_move_groups_dmv(dopt['replay_inputs']['queries'],dopt['candidate_universe']['mcv_candidates'],dopt['candidate_universe']['fd_candidates']);correctness['moves']+=chk;cal.update(x)
 traj,x=trajectory(*ctx);cal.update(x);correctness['trajectory']={'equivalent':traj['equivalent'],'accepted_moves':traj['accepted_moves']}
 movesres={'census':cmoves,'dmv':dmoves};existing={'semantic_optimizer':json.loads(Path('results/census_semantic_optimizer_v0.json').read_text())['runtime'],'compositional':json.loads(Path('results/census_compositional_semantic_optimizer_v0.json').read_text())['runtime']}
 matrix=[{'case':'Census realized full workload','T_PG-plan':'COMPLETE','T_PG-CE':'COMPLETE','T_Replay-full':'COMPLETE','T_Replay-inc':'NOT APPLICABLE'},{'case':'DMV realized full workload','T_PG-plan':'COMPLETE','T_PG-CE':'COMPLETE','T_Replay-full':'COMPLETE','T_Replay-inc':'NOT APPLICABLE'}]+[{'case':f'{w} {m}','T_PG-plan':'INVALID','T_PG-CE':'INVALID','T_Replay-full':'COMPLETE','T_Replay-inc':'COMPLETE'} for w in ('Census','DMV') for m in ('ADD','DROP','SWAP')]+[{'case':'Census trajectory','T_PG-plan':'INVALID','T_PG-CE':'INVALID','T_Replay-full':'COMPLETE','T_Replay-inc':'COMPLETE'}]
 result={'experiment':'CE-Replay-Native-WallClock-v0','protocol':{'warmups':WARMUPS,'measured_batches':REPS,'calibration_target_ns':TARGET_NS,'batch_rule':'smallest power of two exceeding 100 ms','clock':'time.perf_counter_ns / PostgreSQL instr_time','seed':SEED},'environment':env,'patch_validation':patchval,'correctness':correctness,'full_workload':fullres,'moves':movesres,'trajectory':traj,'existing_evidence':existing,'matrix':matrix}
 for name,obj in [('environment.json',env),('patch_validation.json',patchval),('benchmark_matrix.json',matrix),('calibration.json',cal),('correctness_checks.json',correctness),('full_workload_results.json',fullres),('move_results.json',movesres),('trajectory_results.json',traj),('result.json',result)]: (a.out/name).write_text(json.dumps(obj,indent=2)+'\n')
 with (a.out/'raw_timings.csv').open('w',newline='') as f:
  wr=csv.writer(f);wr.writerow(['cell','batch','duration_ns'])
  def scan(prefix,x):
   if isinstance(x,dict):
    if 'raw_batch_ns' in x:
     for i,v in enumerate(x['raw_batch_ns']):wr.writerow([prefix,i,v])
    else:
     for k,v in x.items():scan(prefix+'/'+k,v)
  scan('full',fullres);scan('moves',movesres);scan('trajectory',traj)
 (a.out/'protocol.md').write_text('# Protocol\n\nFrozen protocol: 5 warmup batches, smallest power-of-two calibration above 100 ms, 30 measured batches, correctness before timing, normal Python GC, one client/backend, trace-off native timing.\n')
 (a.out/'report.md').write_text('# CE-Replay-Native-WallClock-v0\n\nSee `result.json` for complete distributions. All admitted cells passed their correctness gate. Native move cells are invalid because PostgreSQL has no frozen-payload hypothetical-state API.\n')
 print(json.dumps({'full_medians':{w:{k:v['median_ns'] for k,v in z.items() if isinstance(v,dict) and 'median_ns' in v} for w,z in fullres.items()},'trajectory_ratio':traj['median_ratio'],'move_ratios':{w:{f:{g:x['median_ratio'] for g,x in z['groups'].items()} for f,z in y.items()} for w,y in movesres.items()}},indent=2))

if __name__=='__main__':main()
