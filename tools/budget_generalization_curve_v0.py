#!/usr/bin/env python3
"""Frozen-payload capacity/generalization curves over the existing IID splits."""
from __future__ import annotations
import argparse,csv,json,math,statistics,sys,types
from collections import Counter,defaultdict
from pathlib import Path
try: import psycopg  # noqa
except ModuleNotFoundError:sys.modules['psycopg']=types.ModuleType('psycopg')
from compositional_semantic_optimizer_v0 import Model
from workload_generalization_v0 import optimize,subset_workload,evaluate,summary
from generalization_mechanism_analysis_v0 import trace,loo

EPS=1e-12
GRID=[0,10,20,40,60,80,100]
def ckey(c):return f'{c[0]}:{c[1]}'
def dset(sm,sf):return {*(('mcv',i) for i in sm),*(('fd',i) for i in sf)}
def qmean(xs):return statistics.mean(xs) if xs else 0.0

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--generalization',type=Path,required=True);ap.add_argument('--replay',type=Path,required=True);ap.add_argument('--mechanisms',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--report',type=Path,required=True);ap.add_argument('--csv',type=Path,required=True);ap.add_argument('--max-rounds',type=int,default=100);a=ap.parse_args()
 g=json.loads(a.generalization.read_text());src=json.loads(a.replay.read_text());mech=json.loads(a.mechanisms.read_text());w=src['workload_ir'];model=Model(w);full_budget=g['budget_bytes'];budgets={p:math.floor(full_budget*p/100) for p in GRID};budgets[100]=full_budget
 # Universal 100%-budget core from the prior experiment.
 counts=Counter()
 for sp in g['per_split']:
  counts.update(f'mcv:{i}' for i in sp['design']['selected_mcv']);counts.update(f'fd:{i}' for i in sp['design']['selected_fd'])
 core={k for k,v in counts.items() if v==10};allq=range(len(model.q));empty={q:trace(model,q,set(),set()) for q in allq}
 runs=[];candidate=defaultdict(lambda:{'selected_splits':0,'train_consumers':0,'test_consumers':0,'test_positive':0,'test_negative':0,'train_benefit':0.0,'test_benefit':0.0})
 for p in GRID:
  B=budgets[p]
  for sp in g['per_split']:
   seed=sp['seed'];train=sp['train_query_indexes'];test=sp['test_query_indexes'];trset=set(train);teset=set(test)
   if p==0:sm=sf=set();runtime=0.0;traj=[]
   elif p==100:
    sm=set(sp['design']['selected_mcv']);sf=set(sp['design']['selected_fd']);runtime=0.0;traj=sp['design']['optimizer']['trajectory']
   else:
    op=optimize(subset_workload(w,train),B,a.max_rounds);sm,sf=op['mcv'],op['fd'];runtime=op['runtime_seconds'];traj=op['trajectory']
   selected=dset(sm,sf);te={q:trace(model,q,sm,sf) for q in test};tr={q:trace(model,q,sm,sf) for q in train}
   train_loss=sum(x['qerror'] for x in tr.values());test_loss=sum(x['qerror'] for x in te.values());train_empty=sum(empty[q]['qerror'] for q in train);test_empty=sum(empty[q]['qerror'] for q in test)
   used_m=sum(model.mc[i]['cost_bytes'] for i in sm);used_f=sum(model.fc[i]['cost_bytes'] for i in sf);used=used_m+used_f
   negmag=repair=0.0;reg_harm=0;query_diag=[]
   for q in test:
    neg=max(0.0,te[q]['qerror']-empty[q]['qerror']);negmag+=neg;cons=[*[("mcv",i) for i in te[q]['mcv']['used']],*[("fd",i) for i in te[q]['fd']['used']]];attrs=[loo(model,q,sm,sf,c,te[q]) for c in cons]
    harmful=[x for x in attrs if x['attribution'] < -EPS]
    if neg>0 and harmful:reg_harm+=1
    best=min((x['qerror_without'] for x in attrs),default=te[q]['qerror']);repair+=min(neg,max(0.0,te[q]['qerror']-best))
    if model.q[q]['id'] in {'query.62','query.274','query.361','query.161'}:
     query_diag.append({'query_id':model.q[q]['id'],'empty_qerror':empty[q]['qerror'],'design_qerror':te[q]['qerror'],'delta':empty[q]['qerror']-te[q]['qerror'],'mcv':te[q]['mcv']['used'],'fd':te[q]['fd']['used'],'fd552_selected':552 in sf,'mcv990_selected':990 in sm})
   # Candidate consumption and contextual diagnostics at this capacity.
   for c in selected:
    z=candidate[(p,ckey(c))];z['selected_splits']+=1
    for side,indexes,traces in [('train',train,tr),('test',test,te)]:
     for q in indexes:
      if c[1] not in traces[q][c[0]]['used']:continue
      x=loo(model,q,sm,sf,c,traces[q]);v=x['attribution'];z[side+'_consumers']+=1;z[side+'_benefit']+=v
      if side=='test' and v>EPS:z['test_positive']+=1
      if side=='test' and v<-EPS:z['test_negative']+=1
   # Reduced oracle protocol: all existing 100%; splits 0-2 at 20/60.
   oracle=None
   if p==100:
    osm=set(sp['test_oracle_design']['selected_mcv']);osf=set(sp['test_oracle_design']['selected_fd']);oracle_source='reused_v0'
   elif p in (20,60) and seed<3:
    oo=optimize(subset_workload(w,test),B,a.max_rounds);osm,osf=oo['mcv'],oo['fd'];oracle_source='optimized_reduced_protocol'
   else:osm=osf=None
   if osm is not None:
    otr={q:trace(model,q,osm,osf) for q in test};oloss=sum(x['qerror'] for x in otr.values());gain=test_empty-test_loss;ogain=test_empty-oloss
    missing_useful=no_signal=budget_pressure=0
    for q in test:
     oc=[*[("mcv",i) for i in otr[q]['mcv']['used']],*[("fd",i) for i in otr[q]['fd']['used']]]
     best=None
     for c in oc:
      if c in selected:continue
      sm1,sf1=set(sm),set(sf);(sm1 if c[0]=='mcv' else sf1).add(c[1]);nt=trace(model,q,sm1,sf1);gg=te[q]['qerror']-nt['qerror']
      if gg>EPS and (best is None or gg>best[0]):best=(gg,c)
     if best:
      missing_useful+=1;c=best[1];sm1,sf1=set(sm),set(sf);(sm1 if c[0]=='mcv' else sf1).add(c[1]);td=sum(trace(model,z,sm1,sf1)['qerror']-tr[z]['qerror'] for z in model.cq[c]&trset)
      if td>=-EPS:no_signal+=1
      elif used+model.cands[c]['cost_bytes']>B:budget_pressure+=1
    oracle={'source':oracle_source,'loss':oloss,'mean':oloss/len(test),'recovery':gain/ogain if ogain>0 else None,'missing_useful_queries':missing_useful,'no_training_signal':no_signal,'budget_pressure':budget_pressure}
   run={'budget_percent':p,'budget_bytes':B,'seed':seed,'selected':len(selected),'mcv':len(sm),'fd':len(sf),'mcv_bytes':used_m,'fd_bytes':used_f,'storage':used,'utilization':used/B if B else 0.0,'train_mean':train_loss/len(train),'test_mean':test_loss/len(test),'train_empty_mean':train_empty/len(train),'test_empty_mean':test_empty/len(test),'train_improvement':(train_empty-train_loss)/len(train),'test_improvement':(test_empty-test_loss)/len(test),'test_relative_improvement':(test_empty-test_loss)/test_empty,'gap':test_loss/len(test)-train_loss/len(train),'negative_magnitude':negmag,'harmful_regressions':reg_harm,'single_removal_repair':repair,'repair_fraction':repair/negmag if negmag else 1.0,'core_survival':len({ckey(c) for c in selected}&core),'core_survival_fraction':len({ckey(c) for c in selected}&core)/len(core),'runtime_seconds':runtime,'rounds':len(traj),'oracle':oracle,'query_diagnostics':query_diag,'selected_mcv':sorted(sm),'selected_fd':sorted(sf)};runs.append(run);print(json.dumps({'budget':p,'seed':seed,'train':run['train_mean'],'test':run['test_mean'],'selected':run['selected'],'seconds':runtime}),flush=True)
 # Curves and adjacent transitions.
 curves=[]
 for p in GRID:
  rr=[x for x in runs if x['budget_percent']==p]
  curves.append({'budget_percent':p,'budget_bytes':budgets[p],**{k:summary([x[k] for x in rr]) for k in ['train_mean','test_mean','gap','test_improvement','test_relative_improvement','selected','storage','utilization','mcv','fd','mcv_bytes','fd_bytes','negative_magnitude','harmful_regressions','repair_fraction','core_survival_fraction']},'positive_splits':sum(x['test_improvement']>EPS for x in rr),'positive_split_fraction':sum(x['test_improvement']>EPS for x in rr)/10})
 transitions=[];classes=Counter();overfit_splits=set()
 for sp in g['per_split']:
  seed=sp['seed'];rr={x['budget_percent']:x for x in runs if x['seed']==seed}
  for p0,p1 in zip(GRID,GRID[1:]):
   dt=rr[p0]['train_mean']-rr[p1]['train_mean'];dv=rr[p0]['test_mean']-rr[p1]['test_mean']
   cls='train_positive_test_positive' if dt>EPS and dv>EPS else ('train_positive_test_neutral' if dt>EPS and abs(dv)<=EPS else ('train_positive_test_negative' if dt>EPS and dv< -EPS else 'other'))
   classes[cls]+=1
   if cls=='train_positive_test_negative':overfit_splits.add(seed)
   transitions.append({'seed':seed,'from_percent':p0,'to_percent':p1,'train_improvement':dt,'test_improvement':dv,'class':cls})
 best=Counter()
 for seed in range(10):
  rr=[x for x in runs if x['seed']==seed];b=min(rr,key=lambda x:(x['test_mean'],x['budget_percent']));best[b['budget_percent']]+=1
 crows=[]
 for (p,k),v in candidate.items():
  typ,sid=k.split(':');c=(typ,int(sid));crows.append({'budget_percent':p,'candidate':k,'mechanism':typ,'cost':model.cands[c]['cost_bytes'],'universal_core':k in core,**v})
 # First-entry late candidates.
 first={}
 for r in crows:first[r['candidate']]=min(first.get(r['candidate'],101),r['budget_percent'])
 late={p:{'candidates':sum(v==p for v in first.values()),'mcv':sum(v==p and k.startswith('mcv:') for k,v in first.items()),'fd':sum(v==p and k.startswith('fd:') for k,v in first.items())} for p in GRID if p}
 result={'experiment':'Budget-Generalization-Curve-v0','protocol':{'grid_percent':GRID,'budgets_bytes':budgets,'splits':'exact Workload-Generalization-v0 splits','frozen_payload':True,'fresh_analyze':False,'optimizer_changed':False,'oracle_reduced_protocol':'100% all splits reused; 20% and 60% splits 0-2 optimized'},'runs':runs,'curves':curves,'transitions':transitions,'transition_classes':dict(classes),'overfitting_transitions':classes['train_positive_test_negative'],'splits_with_overfitting_transition':sorted(overfit_splits),'best_test_budget_distribution':dict(best),'candidate_budget':crows,'late_entry':late,'universal_core':sorted(core)}
 a.output.write_text(json.dumps(result,indent=2)+'\n')
 fields=[k for k in runs[0] if k not in ('oracle','query_diagnostics','selected_mcv','selected_fd')]
 with a.csv.open('w',newline='') as f:wr=csv.DictWriter(f,fieldnames=fields);wr.writeheader();wr.writerows({k:r[k] for k in fields} for r in runs)
 a.report.write_text('# Budget-Generalization-Curve-v0\n\nGenerated results are in JSON and CSV; validated interpretation follows.\n')
 print(json.dumps({'transition_classes':dict(classes),'overfitting_splits':sorted(overfit_splits),'best_test_budget_distribution':dict(best)},indent=2))
if __name__=='__main__':main()
