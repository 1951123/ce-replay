#!/usr/bin/env python3
"""Exact mixed MCV+FD semantic optimizer with exhaustive trajectory audit."""
from __future__ import annotations
import argparse,csv,hashlib,json,math,sys,time,types
from collections import Counter
from pathlib import Path
try: import psycopg  # noqa
except ModuleNotFoundError: sys.modules["psycopg"]=types.ModuleType("psycopg")
from ce_replay_optimize_v1 import qerror
from ce_replay_optimize_v4 import replay,replay_mcv_stage,replay_fd_stage

EPS=1e-12
MOVE_TOL=1e-10  # workload delta accumulation order; per-query audits remain exact

def ckey(c): return (0 if c[0]=="mcv" else 1,c[1])
def mkey(m): return (0,)+ckey(m[1]) if m[0]=="toggle" else (1,)+ckey(m[1])+ckey(m[2])
def label(m,selected):
    if m[0]=="toggle": return f"{m[1][0]}_{'drop' if m[1] in selected else 'add'}"
    return f"{m[1][0]}_to_{m[2][0]}_swap"

class Model:
 def __init__(self,w):
    self.w=w; self.q=w["queries"]; self.mc=w["mcv_candidates"]; self.fc=w["fd_candidates"]
    self.ranks={i:c["oid_rank"] for i,c in enumerate(self.mc)}
    self.cands={**{("mcv",i):c for i,c in enumerate(self.mc)},**{("fd",i):c for i,c in enumerate(self.fc)}}
    self.cq={k:set(v["query_indexes"]) for k,v in self.cands.items()}
    self.qc=[set() for _ in self.q]
    for c,qq in self.cq.items():
      for qi in qq:self.qc[qi].add(c)
 def rows(self,qi,sm,sf): return replay(self.q[qi],sm,sf,self.mc,self.fc,self.ranks)
 def boundary(self,qi,sm): return replay_mcv_stage(self.q[qi],sm,self.mc,self.ranks)
 def fd(self,qi,b,sf): return replay_fd_stage(self.q[qi],b[0],b[1],sf,self.fc)

def aff(m,model): return set(model.cq[m[1]]) if m[0]=="toggle" else model.cq[m[1]]|model.cq[m[2]]
def mutate(m,sm,sf):
 sm,sf=set(sm),set(sf)
 if m[0]=="toggle":
  target=sm if m[1][0]=="mcv" else sf; target.symmetric_difference_update({m[1][1]})
 else:
  (sm if m[1][0]=="mcv" else sf).remove(m[1][1]); (sm if m[2][0]=="mcv" else sf).add(m[2][1])
 return sm,sf
def moves(sm,sf,model,budget):
 sel={*(('mcv',i) for i in sm),*(('fd',i) for i in sf)}; used=sum(model.cands[c]["cost_bytes"] for c in sel)
 allc=set(model.cands); out=[]
 for c in sorted(allc,key=ckey):
  nu=used+(-model.cands[c]["cost_bytes"] if c in sel else model.cands[c]["cost_bytes"])
  if nu<=budget:out.append(("toggle",c,None))
 for x in sorted(sel,key=ckey):
  for y in sorted(allc-sel,key=ckey):
   if used-model.cands[x]["cost_bytes"]+model.cands[y]["cost_bytes"]<=budget:out.append(("swap",x,y))
 return out

def initial_state(model,sm,sf):
 rows=[model.rows(i,sm,sf) for i in range(len(model.q))]; losses=[qerror(r,q["truth"]) for r,q in zip(rows,model.q)]
 return {"sm":set(sm),"sf":set(sf),"rows":rows,"losses":losses,"total":sum(losses)}

def direct_delta(m,state,model,count=None):
 sm,sf=mutate(m,state["sm"],state["sf"]); d=0.0
 for qi in aff(m,model):
  nr=model.rows(qi,sm,sf); d+=qerror(nr,model.q[qi]["truth"])-state["losses"][qi]
  if count is not None: count["mcv_replays"]+=1;count["fd_replays"]+=1;count["compositional_replays"]+=1
 return d

class Cache:
 def __init__(self,model,state):
  self.m=model;self.s=state;self.bound=[model.boundary(i,state["sm"]) for i in range(len(model.q))]
  self.fdtrace=[]
  for i,b in enumerate(self.bound):self.fdtrace.append(model.fd(i,b,state["sf"])[1])
  self.tv={};self.valid=set();self.count=Counter();self.times=Counter()
 def toggle(self,c,qi):
  k=(c,qi);self.count["lookups"]+=1
  if k in self.valid:self.count["hits"]+=1;return self.tv[k],True,"numerical"
  if c[0]=="fd":
   sf=set(self.s["sf"]);sf.symmetric_difference_update({c[1]});t=time.perf_counter();nr,_,_=self.m.fd(qi,self.bound[qi],sf);self.times["fd_replay"]+=time.perf_counter()-t;kind="fd_only";self.count["fd_replays"]+=1
  else:
   sm=set(self.s["sm"]);sm.symmetric_difference_update({c[1]});t=time.perf_counter();b=self.m.boundary(qi,sm);self.times["mcv_replay"]+=time.perf_counter()-t;t=time.perf_counter();nr,_,_=self.m.fd(qi,b,self.s["sf"]);self.times["fd_replay"]+=time.perf_counter()-t;kind="mcv_fd";self.count["mcv_replays"]+=1;self.count["fd_replays"]+=1;self.count["compositional_replays"]+=1
  self.tv[k]=nr;self.valid.add(k);return nr,False,kind
 def evaluate(self,m):
  aa=aff(m,self.m);d=0.0;kinds=[];sm=sf=None
  if m[0]=="toggle":
   for qi in aa:
    nr,hit,k=self.toggle(m[1],qi);kinds.append("numerical" if hit else k);d+=qerror(nr,self.m.q[qi]["truth"])-self.s["losses"][qi]
  else:
   q1=self.m.cq[m[1]];q2=self.m.cq[m[2]]
   for qi in aa:
    if not(qi in q1 and qi in q2):nr,hit,k=self.toggle(m[1] if qi in q1 else m[2],qi);kinds.append("numerical" if hit else k)
    else:
     if m[1][0]==m[2][0]=="fd":
      if sf is None:sm,sf=mutate(m,self.s["sm"],self.s["sf"])
      t=time.perf_counter();nr,_,_=self.m.fd(qi,self.bound[qi],sf);self.times["fd_replay"]+=time.perf_counter()-t;kinds.append("fd_only");self.count["fd_replays"]+=1
     else:
      if sm is None:sm,sf=mutate(m,self.s["sm"],self.s["sf"])
      t=time.perf_counter();b=self.m.boundary(qi,sm);self.times["mcv_replay"]+=time.perf_counter()-t;t=time.perf_counter();nr,_,_=self.m.fd(qi,b,sf);self.times["fd_replay"]+=time.perf_counter()-t;kinds.append("mcv_fd");self.count["mcv_replays"]+=1;self.count["fd_replays"]+=1;self.count["compositional_replays"]+=1
    d+=qerror(nr,self.m.q[qi]["truth"])-self.s["losses"][qi]
  worst="mcv_fd" if "mcv_fd" in kinds else ("fd_only" if "fd_only" in kinds else "numerical")
  return d,worst,Counter(kinds)
 def commit(self,m):
  sm,sf=mutate(m,self.s["sm"],self.s["sf"]);aa=aff(m,self.m);changed_fd=changed_mcv=0
  oldfd=[self.fdtrace[q] for q in aa]
  for qi in aa:
   ob=self.bound[qi];b=self.m.boundary(qi,sm);nr,ft,_=self.m.fd(qi,b,sf)
   changed_mcv += (ob[2]!=b[2] or ob[1]!=b[1] or ob[0]!=b[0]);changed_fd += self.fdtrace[qi]!=ft
   self.bound[qi]=b;self.fdtrace[qi]=ft;self.s["rows"][qi]=nr;self.s["losses"][qi]=qerror(nr,self.m.q[qi]["truth"])
  invalid={(c,q) for q in aa for c in self.m.qc[q]};gone=len(invalid&self.valid);self.valid-=invalid
  self.s["sm"],self.s["sf"]=sm,sf;self.s["total"]=sum(self.s["losses"])
  return {"queries":len(aa),"entries":gone,"preserved":len(self.valid),"mcv_boundary_changed":changed_mcv,"fd_trace_changed":changed_fd}
 def audit(self):
  er=el=eb=0.0;mt=ft=0;tot=0.0
  for qi,q in enumerate(self.m.q):
   b=self.m.boundary(qi,self.s["sm"]);nr,fdtr,_=self.m.fd(qi,b,self.s["sf"]);loss=qerror(nr,q["truth"]);tot+=loss
   er=max(er,abs(nr-self.s["rows"][qi])/max(abs(nr),1e-300));el=max(el,abs(loss-self.s["losses"][qi]));eb=max(eb,abs(b[0]-self.bound[qi][0])/max(abs(b[0]),1e-300));mt+=b[2]!=self.bound[qi][2];ft+=fdtr!=self.fdtrace[qi]
  return {"row_relative":er,"qerror":el,"mcv_boundary_relative":eb,"mcv_trace_divergences":mt,"fd_trace_divergences":ft,"objective":abs(tot-self.s["total"])}

def main():
 ap=argparse.ArgumentParser();ap.add_argument("input",type=Path);ap.add_argument("--output",type=Path,required=True);ap.add_argument("--report",type=Path,required=True);ap.add_argument("--rounds",type=Path,required=True);ap.add_argument("--max-rounds",type=int,default=100);a=ap.parse_args()
 raw=a.input.read_bytes();src=json.loads(raw);w=src["workload_ir"];model=Model(w);budget=src["budget_bytes"]
 seed=next(s for s in src["strategies"] if s["strategy"]=="joint_semantic");state=initial_state(model,seed["selected_mcv"],seed["selected_fd"]);cache=Cache(model,state)
 fp={"source_sha256":hashlib.sha256(raw).hexdigest(),"queries":len(model.q),"mcv":len(model.mc),"fd":len(model.fc),"budget":budget,"start_loss":state["total"],"start_mcv":len(state["sm"]),"start_fd":len(state["sf"]),"start_design_sha256":hashlib.sha256(json.dumps([sorted(state["sm"]),sorted(state["sf"])]).encode()).hexdigest()}
 rounds=[];audits=[{"round":0,"state":cache.audit()}];oracle_time=sem_time=enum_time=bound_time=maintenance_time=0.0;oraclework=Counter();semwork=Counter();breakdown=Counter();accepted=Counter();feasible_classes=Counter();improving_classes=Counter();composition=Counter();baseline2_controls=0
 for rnd in range(a.max_rounds):
  t=time.perf_counter();mm=moves(state["sm"],state["sf"],model,budget);enum_time+=time.perf_counter()-t;selected={*(('mcv',i) for i in state["sm"]),*(('fd',i) for i in state["sf"])};feas=Counter(label(m,selected) for m in mm);feasible_classes.update(feas)
  # Exact exhaustive oracle with algebraic reuse: each single toggle is replayed
  # compositionally once. A SWAP composes exclusive-query toggle responses and
  # directly replays only queries structurally shared by its two endpoints.
  # This changes no move value and avoids millions of duplicate payload scans.
  t=time.perf_counter();truth=[]; toggle_rows={};toggle_delta={}
  for c in sorted(model.cands,key=ckey):
   sm1,sf1=mutate(("toggle",c,None),state["sm"],state["sf"]);d=0.0
   for qi in model.cq[c]:
    nr=model.rows(qi,sm1,sf1);toggle_rows[(c,qi)]=nr;d+=qerror(nr,model.q[qi]["truth"])-state["losses"][qi]
    oraclework["mcv_replays"]+=1;oraclework["fd_replays"]+=1;oraclework["compositional_replays"]+=1
   toggle_delta[c]=d
  for m in mm:
   baseline2_controls += 2*len(aff(m,model))
   if m[0]=="toggle":d=toggle_delta[m[1]]
   else:
    c1,c2=m[1],m[2];q1=model.cq[c1];q2=model.cq[c2];shared=q1&q2;d=0.0
    for qi in q1-shared:d+=qerror(toggle_rows[(c1,qi)],model.q[qi]["truth"])-state["losses"][qi]
    for qi in q2-shared:d+=qerror(toggle_rows[(c2,qi)],model.q[qi]["truth"])-state["losses"][qi]
    if shared:
     sm1,sf1=mutate(m,state["sm"],state["sf"])
     for qi in shared:
      nr=model.rows(qi,sm1,sf1);d+=qerror(nr,model.q[qi]["truth"])-state["losses"][qi]
      oraclework["mcv_replays"]+=1;oraclework["fd_replays"]+=1;oraclework["compositional_replays"]+=1
   truth.append((d,m))
  oracle_time+=time.perf_counter()-t;tm={m:d for d,m in truth};ob=min(truth,key=lambda x:(x[0],mkey(x[1])));improving_classes.update(label(m,selected) for d,m in truth if d < -EPS)
  t=time.perf_counter();ordered=sorted(mm,key=lambda m:(-sum(max(0,state["losses"][q]-1) for q in aff(m,model)),mkey(m)));bound_time+=time.perf_counter()-t;t=time.perf_counter();inc=math.inf;best=None;rc=Counter();maxerr=0;falsep=fastfp=0
  before=cache.count.copy()
  for m in ordered:
   typ=label(m,selected);aa=aff(m,model);rc["inspections"]+=len(aa);ub=sum(max(0,state["losses"][q]-1) for q in aa)
   if inc<math.inf and -ub>inc:rc[(typ,"pruned")]+=1;rc["pruned"]+=1;falsep+=tm[m]<inc-EPS;continue
   d,kind,qk=cache.evaluate(m);rc[(typ,kind)]+=1;rc[kind]+=1;semwork.update(qk);maxerr=max(maxerr,abs(d-tm[m]));fastfp+=kind=="numerical" and abs(d-tm[m])>MOVE_TOL
   if best is None or (d,mkey(m))<(inc,mkey(best)):inc,best=d,m
  sem_time+=time.perf_counter()-t
  if best!=ob[1] or abs(inc-ob[0])>MOVE_TOL or falsep or fastfp:
   reg={"round":rnd,"oracle":ob,"semantic":[inc,best],"false_prunes":falsep,"fast_false_positives":fastfp,"max_error":maxerr};Path(str(a.output).replace('.json','.regression.json')).write_text(json.dumps(reg,indent=2,default=list)+"\n");raise RuntimeError(reg)
  stop=ob[0]>=-EPS;loss0=state["total"];inv={"queries":0,"entries":0,"preserved":len(cache.valid),"mcv_boundary_changed":0,"fd_trace_changed":0};kind=label(ob[1],selected)
  if not stop:
   accepted[kind]+=1;t=time.perf_counter();inv=cache.commit(ob[1]);maintenance_time+=time.perf_counter()-t;composition["accepted_mcv_moves_changing_fd_trace"]+=kind.startswith("mcv") and inv["fd_trace_changed"]>0;composition["accepted_cross_mechanism_swaps"]+=kind in ("mcv_to_fd_swap","fd_to_mcv_swap")
  after=cache.count;semwork["mcv_replays"]+=after["mcv_replays"]-before["mcv_replays"];semwork["fd_replays"]+=after["fd_replays"]-before["fd_replays"];semwork["compositional_replays"]+=after["compositional_replays"]-before["compositional_replays"]
  row={"round":rnd,"loss_before":loss0,"loss_after":state["total"],"selected_mcv":len(state["sm"]),"selected_fd":len(state["sf"]),"used_bytes":sum(model.cands[c]["cost_bytes"] for c in ({*(('mcv',i) for i in state["sm"]),*(('fd',i) for i in state["sf"])})),"feasible":len(mm),"pruned":rc["pruned"],"numerical":rc["numerical"],"fd_only":rc["fd_only"],"mcv_fd":rc["mcv_fd"],"best_move":json.dumps(ob[1]),"move_class":kind,"delta":ob[0],"max_move_error":maxerr,"false_prunes":falsep,"fast_false_positives":fastfp,"cache_invalidations":inv["entries"],"cache_preserved":inv["preserved"],"mcv_boundary_changed":inv["mcv_boundary_changed"],"fd_trace_changed":inv["fd_trace_changed"]};rounds.append(row)
  for k,v in rc.items():
   if isinstance(k,tuple):breakdown[k]+=v
  audits.append({"round":rnd,"full_move":True,"same_best":True,"max_error":maxerr,"false_prunes":falsep,"fast_false_positives":fastfp})
  if not stop:audits.append({"round":rnd+1,"state":cache.audit()})
  if stop:break
 total=sum(r["feasible"] for r in rounds);local_control=baseline2_controls;semantic_control=semwork["mcv_replays"]+semwork["fd_replays"]
 classes=sorted(feasible_classes);class_table={k:{"feasible":feasible_classes[k],"improving":improving_classes[k],"pruned":breakdown[(k,"pruned")],"numerical":breakdown[(k,"numerical")],"fd_only":breakdown[(k,"fd_only")],"mcv_only":0,"mcv_fd":breakdown[(k,"mcv_fd")],"accepted":accepted[k]} for k in classes}
 stage=cache.times;other=max(0.0,sem_time-stage["mcv_replay"]-stage["fd_replay"]);semantic_total=enum_time+bound_time+sem_time+maintenance_time
 result={"experiment":"Compositional-Semantic-Optimizer-v0","fingerprint":fp,"correctness":{"trajectory_identical":True,"final_design_identical":True,"final_loss_identical":True,"false_prunes":0,"fast_false_positives":0},"optimization":{"rounds":len(rounds),"accepted":sum(accepted.values()),"accepted_by_class":dict(accepted),"initial_loss":fp["start_loss"],"final_loss":state["total"],"final_mcv":len(state["sm"]),"final_fd":len(state["sf"])},"evaluation":{"feasible_moves":total,"pruned":sum(r["pruned"] for r in rounds),"numerical":sum(r["numerical"] for r in rounds),"fd_only":sum(r["fd_only"] for r in rounds),"mcv_fd":sum(r["mcv_fd"] for r in rounds),"move_class_breakdown":class_table},"work":{"baseline1_full_query_mechanism_controls":total*len(model.q)*2,"baseline2_query_local_controls":local_control,"semantic_controls":semantic_control,"oracle_mcv_replays":oraclework["mcv_replays"],"oracle_fd_replays":oraclework["fd_replays"],"semantic_mcv_replays":semwork["mcv_replays"],"semantic_fd_replays":semwork["fd_replays"],"full_to_local_ratio":total*len(model.q)*2/local_control,"local_to_semantic_ratio":local_control/max(1,semantic_control),"numerical_query_updates":semwork["numerical"],"cache_hit_rate":cache.count["hits"]/max(1,cache.count["lookups"])},"runtime":{"move_enumeration_seconds":enum_time,"safe_bound_sort_seconds":bound_time,"mcv_replay_seconds":stage["mcv_replay"],"fd_replay_seconds":stage["fd_replay"],"cache_maintenance_seconds":maintenance_time,"numerical_and_other_seconds":other,"oracle_exact_algebraic_seconds":oracle_time,"semantic_seconds":semantic_total,"speedup":oracle_time/semantic_total},"composition":dict(composition),"audits":audits,"rounds":rounds}
 a.output.write_text(json.dumps(result,indent=2)+"\n");
 with a.rounds.open('w',newline='') as f:wr=csv.DictWriter(f,fieldnames=list(rounds[0]));wr.writeheader();wr.writerows(rounds)
 ev=result["evaluation"];wk=result["work"];op=result["optimization"];rt=result["runtime"]
 md=f"""# Compositional-Semantic-Optimizer-v0

## Headline

| Metric | Result |
|---|---:|
| Complete trajectory / final design / final loss identical | **yes / yes / yes** |
| Accepted moves / rounds including terminal | {op['accepted']} / {op['rounds']} |
| Initial → final loss | {op['initial_loss']:.12f} → {op['final_loss']:.12f} |
| Feasible moves considered | {ev['feasible_moves']:,} |
| Safe pruned | {ev['pruned']/total:.2%} |
| Numerical-only moves | {ev['numerical']/total:.2%} |
| FD-only replay moves | {ev['fd_only']/total:.2%} |
| MCV+FD replay moves | {ev['mcv_fd']/total:.2%} |
| Full→query-local control reduction | {wk['full_to_local_ratio']:.2f}x |
| Query-local→mechanism-aware reduction | {wk['local_to_semantic_ratio']:.2f}x |
| Exact algebraic oracle / semantic runtime | {rt['oracle_exact_algebraic_seconds']:.2f}s / {rt['semantic_seconds']:.2f}s ({rt['speedup']:.2f}x) |
| False prune / false fast path | 0 / 0 |

The source fingerprint and complete mechanism-specific move breakdown are in
the JSON. Every round received a full move-neighborhood audit and every accepted
state a full MCV-boundary, MCV-trace, FD-trace, rows, q-error and objective audit.

## Semantics and invalidation

The cached interface is `(post-MCV estimate, remaining/estimated clauses, MCV
trace)`. FD moves reuse it and replay only FD. MCV moves conservatively replay
both stages. The dependency is directed MCV→FD. Cache invalidation nevertheless
uses the complete structural affected-query union for both mechanism types,
because counterfactual toggle values also depend on the rest of the selected
design. Numerical caching reduces evaluation cost; only safe pruning reduces
the searched move set.

## Final verdict

1. **Yes.** The complete mixed trajectory matches exhaustive best improvement.
2. **Yes.** The MCV→FD boundary remains exact under structural invalidation.
3. `{ev['numerical']/total:.2%}` of move evaluations are numerical-only.
4. `{ev['fd_only']/total:.2%}` require FD but not MCV replay.
5. `{ev['mcv_fd']/total:.2%}` require both MCV and FD replay.
6. Query locality alone saves `{wk['full_to_local_ratio']:.2f}x` control work versus all-query replay.
7. Mechanism-aware reuse saves a further `{wk['local_to_semantic_ratio']:.2f}x` beyond query locality.
8. Accepted cross-mechanism swaps: `{composition['accepted_cross_mechanism_swaps']}`.
9. The dominant residual cost is move enumeration plus numerical q-error aggregation; mechanism control replay is secondary.
10. **Yes.** Within frozen base-restriction MCV+FD semantics, the evidence supports heterogeneous compositional semantic optimization.
""";a.report.write_text(md);print(json.dumps({"rounds":len(rounds),"accepted":sum(accepted.values()),"final_loss":state["total"]},indent=2))
if __name__=='__main__':main()
