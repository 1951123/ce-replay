#!/usr/bin/env python3
"""Observational structural-distance analysis over the existing 940 instances."""
from __future__ import annotations
import argparse,csv,itertools,json,math,statistics,sys,types
from collections import Counter,defaultdict
from pathlib import Path
try:import psycopg  # noqa
except ModuleNotFoundError:sys.modules['psycopg']=types.ModuleType('psycopg')
from compositional_semantic_optimizer_v0 import Model

EPS=1e-12
def tkey(t,i):return f'{t}:{i}'
def jac(a,b):return len(a&b)/len(a|b) if a|b else 1.0
def safe_mean(x):return statistics.mean(x) if x else None
def ranks(xs):
 order=sorted(range(len(xs)),key=lambda i:xs[i]);out=[0.0]*len(xs);i=0
 while i<len(order):
  j=i+1
  while j<len(order) and xs[order[j]]==xs[order[i]]:j+=1
  v=(i+j-1)/2
  for k in order[i:j]:out[k]=v
  i=j
 return out
def pearson(x,y):
 if len(x)<2:return None
 mx,my=statistics.mean(x),statistics.mean(y);dx=sum((a-mx)**2 for a in x);dy=sum((b-my)**2 for b in y)
 return sum((a-mx)*(b-my) for a,b in zip(x,y))/math.sqrt(dx*dy) if dx and dy else None
def corr(x,y):return {'pearson':pearson(x,y),'spearman':pearson(ranks(x),ranks(y))}
def op_sig(q,col):
 def cls(op):return 'eq' if op=='=' else ('lower' if op in ('>','>=') else ('upper' if op in ('<','<=') else op))
 return tuple(sorted(Counter(cls(op) for op,_ in q['predicates'][col]).items()))

def bins(rows,metric):
 vals=sorted(set(r[metric] for r in rows));
 if len(vals)<=4:cuts=vals[:-1]
 else:cuts=sorted(set(vals[round((len(vals)-1)*p)] for p in (.25,.5,.75)))
 groups=defaultdict(list)
 for r in rows:
  idx=sum(r[metric]>c for c in cuts);groups[idx].append(r)
 out=[]
 for i,rr in sorted(groups.items()):
  empty=sum(r['empty_qerror'] for r in rr);train=sum(r['train_qerror'] for r in rr);oracle_den=sum(max(0.0,r['empty_qerror']-r['oracle_qerror']) for r in rr);gain=sum(r['delta'] for r in rr)
  neg=sum(r['negative_magnitude'] for r in rr);repair=sum(r['single_removal_repair'] for r in rr);oc=Counter(r['outcome'] for r in rr)
  out.append({'bin':i+1,'value_min':min(r[metric] for r in rr),'value_max':max(r[metric] for r in rr),'count':len(rr),'mean_empty_qerror':empty/len(rr),'mean_train_qerror':train/len(rr),'mean_transfer':gain/len(rr),'median_transfer':statistics.median(r['delta'] for r in rr),'relative_aggregate_improvement':gain/empty if empty else None,'positive':oc['positive'],'neutral':oc['neutral'],'negative':oc['negative'],'consumption_fraction':sum(r['consumed_any'] for r in rr)/len(rr),'mean_selected_coverage':statistics.mean(r['selected_candidate_coverage'] for r in rr),'negative_magnitude':neg,'single_removal_repair_fraction':repair/neg if neg else 1.0,'oracle_gap_recovery':gain/oracle_den if oracle_den>0 else None,'no_training_signal_fraction':sum(r['no_training_signal'] for r in rr)/len(rr),'harmful_presence_fraction':sum(r['harmful_presence'] for r in rr)/len(rr)})
 return {'rule':'quartile cuts over unique observed values; ties remain together','cuts':cuts,'bins':out}

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--generalization',type=Path,required=True);ap.add_argument('--mechanisms',type=Path,required=True);ap.add_argument('--replay',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--report',type=Path,required=True);ap.add_argument('--queries-csv',type=Path,required=True);ap.add_argument('--candidates-csv',type=Path,required=True);a=ap.parse_args()
 g=json.loads(a.generalization.read_text());mec=json.loads(a.mechanisms.read_text());w=json.loads(a.replay.read_text())['workload_ir'];model=Model(w);n=len(model.q)
 C=[];P=[];NM=[];NF=[];N=[]
 for qi,q in enumerate(model.q):
  c=set(q['predicates']);C.append(c);P.append({tuple(sorted(x)) for x in itertools.combinations(c,2)});NM.append({tkey('mcv',i) for i in q['mcv_ids']});NF.append({tkey('fd',i) for i in q['fd_ids']});N.append(NM[-1]|NF[-1])
 instances={(s['seed'],x['query_index']):x for s in mec['splits'] for x in s['instances']};rows=[];crows=[]
 for sp in g['per_split']:
  seed=sp['seed'];train=sp['train_query_indexes'];test=sp['test_query_indexes'];sm=set(sp['design']['selected_mcv']);sf=set(sp['design']['selected_fd']);Y={*(tkey('mcv',i) for i in sm),*(tkey('fd',i) for i in sf)}
  uc=set().union(*(C[i] for i in train));up=set().union(*(P[i] for i in train));unm=set().union(*(NM[i] for i in train));unf=set().union(*(NF[i] for i in train));un=unm|unf
  support=Counter(x for i in train for x in N[i]);candidate_effect=defaultdict(lambda:{'consumed':0,'positive':0,'negative':0,'positive_magnitude':0.0,'negative_magnitude':0.0})
  for qi in test:
   z=instances[(seed,qi)];nearest=[]
   for tj in train:
    shared=C[qi]&C[tj];compat=sum(op_sig(model.q[qi],c)==op_sig(model.q[tj],c) for c in shared)
    nearest.append((jac(C[qi],C[tj]),jac(N[qi],N[tj]),len(P[qi]&P[tj]),len(P[qi]&P[tj])/len(P[qi]) if P[qi] else 1.0,compat/len(C[qi]|C[tj]) if C[qi]|C[tj] else 1.0,compat/len(shared) if shared else 0.0,tj))
   maxcj=max(nearest,key=lambda x:(x[0],-x[6]));maxnj=max(nearest,key=lambda x:(x[1],-x[6]));maxpair=max(nearest,key=lambda x:(x[2],x[3],-x[6]));maxop=max(nearest,key=lambda x:(x[4],-x[6]))
   rel=N[qi];selected=rel&Y;consumed={*(tkey('mcv',i) for i in z['mcv_trace']),*(tkey('fd',i) for i in z['fd_trace'])};attrs=z['attributions'];harm=[x for x in attrs if x['attribution']<-EPS];benef=[x for x in attrs if x['attribution']>EPS]
   consumed_support=[support[x] for x in consumed];harm_support=[support[x['candidate']] for x in harm];benef_support=[support[x['candidate']] for x in benef]
   for x in attrs:
    d=candidate_effect[x['candidate']];d['consumed']+=1
    if x['attribution']>EPS:d['positive']+=1;d['positive_magnitude']+=x['attribution']
    elif x['attribution']<-EPS:d['negative']+=1;d['negative_magnitude']+=-x['attribution']
   oracle_improvement=z['empty_qerror']-z['oracle_qerror'];row={'seed':seed,'query_index':qi,'query_id':z['query_id'],'columns':len(C[qi]),'pairs':len(P[qi]),'mcv_neighborhood':len(NM[qi]),'fd_neighborhood':len(NF[qi]),'candidate_neighborhood':len(rel),'nearest_column_jaccard':maxcj[0],'nearest_column_query':model.q[maxcj[6]]['id'],'nearest_candidate_jaccard':maxnj[1],'nearest_candidate_query':model.q[maxnj[6]]['id'],'max_shared_pairs':maxpair[2],'max_pair_containment':maxpair[3],'operator_compatibility_jaccard':maxop[4],'operator_compatibility_on_shared':maxop[5],'column_coverage':len(C[qi]&uc)/len(C[qi]),'pair_coverage':len(P[qi]&up)/len(P[qi]) if P[qi] else 1.0,'candidate_coverage':len(rel&un)/len(rel) if rel else 1.0,'mcv_coverage':len(NM[qi]&unm)/len(NM[qi]) if NM[qi] else 1.0,'fd_coverage':len(NF[qi]&unf)/len(NF[qi]) if NF[qi] else 1.0,'unseen_columns':len(C[qi]-uc)/len(C[qi]),'unseen_pairs':len(P[qi]-up)/len(P[qi]) if P[qi] else 0.0,'unseen_candidates':len(rel-un)/len(rel) if rel else 0.0,'selected_relevant':len(selected),'selected_candidate_coverage':len(selected)/len(rel) if rel else 0.0,'selected_mcv_coverage':len(NM[qi]&Y)/len(NM[qi]) if NM[qi] else 0.0,'selected_fd_coverage':len(NF[qi]&Y)/len(NF[qi]) if NF[qi] else 0.0,'consumed_mcv':len(z['mcv_trace']),'consumed_fd':len(z['fd_trace']),'consumed_any':bool(consumed),'consumed_both':bool(z['mcv_trace']) and bool(z['fd_trace']),'relevant_support_mean':statistics.mean(support[x] for x in rel) if rel else 0.0,'relevant_support_max':max((support[x] for x in rel),default=0),'consumed_support_mean':safe_mean(consumed_support),'consumed_support_max':max(consumed_support,default=None),'harmful_support_mean':safe_mean(harm_support),'beneficial_support_mean':safe_mean(benef_support),'empty_qerror':z['empty_qerror'],'train_qerror':z['train_qerror'],'oracle_qerror':z['oracle_qerror'],'delta':z['delta'],'relative_improvement':z['delta']/z['empty_qerror'],'outcome':z['outcome'],'oracle_gap':z['oracle_gap'],'oracle_gap_recovery':z['delta']/oracle_improvement if oracle_improvement>EPS else None,'harmful_presence':bool(harm),'harmful_candidates':json.dumps([x['candidate'] for x in harm]),'harmful_candidate_count':len(harm),'negative_magnitude':z['negative_magnitude'],'single_removal_repair':z['repairable_single_removal'],'missing_useful':bool(z['best_missing_add'] and z['best_missing_add']['gain']>EPS),'missing_candidate':z['best_missing_add']['candidate'] if z['best_missing_add'] else None,'no_training_signal':z['missing_class']=='S1_no_training_signal','budget_pressure':z['missing_class']=='S2_positive_signal_budget_pressure','mcv_trace':json.dumps(z['mcv_trace']),'fd_trace':json.dumps(z['fd_trace']),'mechanism':z['mechanism']};rows.append(row)
  # Candidate-split support/risk table, restricted to test-relevant candidates.
  testrel=Counter(x for qi in test for x in N[qi])
  for ck,tcount in testrel.items():
   typ,sid=ck.split(':');c=(typ,int(sid));d=candidate_effect[ck]
   crows.append({'seed':seed,'candidate':ck,'mechanism':typ,'cost':model.cands[c]['cost_bytes'],'train_support':support[ck],'test_relevant_queries':tcount,'selected':ck in Y,**d})
 assert len(rows)==940
 metrics=['nearest_column_jaccard','nearest_candidate_jaccard','max_pair_containment','operator_compatibility_jaccard','column_coverage','pair_coverage','candidate_coverage','mcv_coverage','fd_coverage','selected_candidate_coverage','relevant_support_mean','relevant_support_max']
 associations={}
 for metric in metrics:
  associations[metric]={'transfer':corr([r[metric] for r in rows],[r['delta'] for r in rows]),'consumption':corr([r[metric] for r in rows],[int(r['consumed_any']) for r in rows]),'negative':corr([r[metric] for r in rows],[int(r['outcome']=='negative') for r in rows]),'oracle_gap':corr([r[metric] for r in rows],[r['oracle_gap'] for r in rows])}
 binned={m:bins(rows,m) for m in ['nearest_column_jaccard','nearest_candidate_jaccard','pair_coverage','candidate_coverage','mcv_coverage','fd_coverage','relevant_support_mean']}
 # Candidate support bins.
 sbins=[('0',lambda x:x==0),('1',lambda x:x==1),('2-3',lambda x:2<=x<=3),('4+',lambda x:x>=4)];support_bins=[]
 for label,pred in sbins:
  rr=[r for r in crows if pred(r['train_support'])];sel=[r for r in rr if r['selected']];cons=sum(r['consumed'] for r in sel);support_bins.append({'support_bin':label,'candidate_split_instances':len(rr),'selection_probability':sum(r['selected'] for r in rr)/len(rr) if rr else None,'selected_instances':len(sel),'consumed_events':cons,'positive_effect_probability_per_consumption':sum(r['positive'] for r in sel)/cons if cons else None,'negative_effect_probability_per_consumption':sum(r['negative'] for r in sel)/cons if cons else None,'positive_magnitude':sum(r['positive_magnitude'] for r in sel),'negative_magnitude':sum(r['negative_magnitude'] for r in sel)})
 # Exemplars and required cases.
 low_sim=sorted(rows,key=lambda r:(r['nearest_candidate_jaccard'],-r['delta']))
 positive_low=sorted((r for r in rows if r['outcome']=='positive'),key=lambda r:(r['nearest_candidate_jaccard'],-r['delta']))[:10]
 low_cov_success=sorted((r for r in rows if r['outcome']=='positive'),key=lambda r:(r['candidate_coverage'],-r['delta']))[:10]
 high_cov_fail=sorted((r for r in rows if r['outcome']=='negative' or r['oracle_gap']>0),key=lambda r:(-r['candidate_coverage'],-max(r['negative_magnitude'],r['oracle_gap'])))[:10]
 major={q:[r for r in rows if r['query_id']==q] for q in ['query.62','query.274','query.361','query.161']}
 outcome=Counter(r['outcome'] for r in rows)
 result={'experiment':'Structural-Distance-Generalization-v0','scope':{'instances':len(rows),'splits':10,'optimization_rerun':False,'fresh_analyze':False,'interpretation':'distance / semantic-coverage generalization; not template generalization'},'reproduction':{'outcomes':dict(outcome),'positive_magnitude':sum(max(0,r['delta']) for r in rows),'negative_magnitude':sum(r['negative_magnitude'] for r in rows)},'definitions':{'columns':'predicate dimension names','pairs':'all unordered predicate-column pairs','candidate_neighborhood':'typed global MCV and eligible FD candidate IDs, independent of selection','operator_compatibility':'shared columns receive credit only when equality/lower/upper operator-class multiplicities match; Jaccard denominator is union columns','support':'number of train queries whose structural neighborhood contains candidate'},'metric_distributions':{m:{'min':min(r[m] for r in rows),'mean':statistics.mean(r[m] for r in rows),'median':statistics.median(r[m] for r in rows),'max':max(r[m] for r in rows),'unique':len(set(r[m] for r in rows))} for m in metrics},'associations':associations,'bins':binned,'support_bins':support_bins,'major_queries':major,'exemplars':{'positive_low_nearest_similarity':positive_low,'low_coverage_success':low_cov_success,'high_coverage_failure':high_cov_fail},'rows':rows,'candidate_rows':crows}
 a.output.write_text(json.dumps(result,indent=2)+'\n')
 qfields=[k for k in rows[0] if k not in ('columns',)]
 with a.queries_csv.open('w',newline='') as f:wr=csv.DictWriter(f,fieldnames=qfields);wr.writeheader();wr.writerows({k:r[k] for k in qfields} for r in rows)
 with a.candidates_csv.open('w',newline='') as f:wr=csv.DictWriter(f,fieldnames=list(crows[0]));wr.writeheader();wr.writerows(crows)
 a.report.write_text('# Structural-Distance-Generalization-v0\n\nGenerated metrics are in JSON/CSV; validated interpretation follows.\n')
 print(json.dumps({'reproduction':result['reproduction'],'metric_distributions':result['metric_distributions'],'associations':associations,'support_bins':support_bins},indent=2))
if __name__=='__main__':main()
