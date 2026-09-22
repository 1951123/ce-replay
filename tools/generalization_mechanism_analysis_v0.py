#!/usr/bin/env python3
"""Explain held-out transfer mechanisms without changing designs or payloads."""
from __future__ import annotations

import argparse, csv, hashlib, itertools, json, math, statistics, sys, types
from collections import Counter, defaultdict
from pathlib import Path

try: import psycopg  # noqa
except ModuleNotFoundError: sys.modules["psycopg"] = types.ModuleType("psycopg")

from ce_replay_optimize_v1 import qerror
from compositional_semantic_optimizer_v0 import Model

EPS = 1e-12

def mean(xs): return statistics.mean(xs) if xs else 0.0
def design(sm,sf): return {*(('mcv',i) for i in sm),*(('fd',i) for i in sf)}
def key(c): return f"{c[0]}:{c[1]}"

def trace(model, qi, sm, sf):
 q=model.q[qi]; remaining=set(q["predicates"]); estimate=q["baseline_rows"]; mr=[]
 while True:
  eligible=sorted((i for i in q["mcv_ids"] if i in sm and set(model.mc[i]["columns"])<=remaining),key=lambda i:model.ranks[i])
  if not eligible: break
  winner=eligible[0]; before=estimate; ratio=q["mcv_ratios"][str(winner)]; cols=list(model.mc[winner]["columns"])
  estimate*=ratio; remaining-=set(cols)
  mr.append({"eligible":eligible,"eligible_ranks":[model.ranks[i] for i in eligible],"winner":winner,"winner_rank":model.ranks[winner],"consumed_columns":cols,"ratio":ratio,"estimate_before":before,"estimate_after":estimate,"remaining":sorted(remaining)})
 mcv_est=estimate; mcv_remaining=sorted(remaining); available=set(q["fd_columns"])&remaining; payloads=[]
 available_objects=[]
 for fid in q["fd_ids"]:
  if fid in sf and set(model.fc[fid]["columns"])<=available:
   payloads.append((model.fc[fid]["oid_rank"],fid,model.fc[fid]["payload"]));available_objects.append(fid)
 payloads.sort(); chosen=[]; fr=[]
 while True:
  winner=None; applicable=[]
  for rank,fid,payload in payloads:
   for dep_idx,dep in enumerate(payload):
    attrs=dep["attributes"]
    if not set(attrs)<=available: continue
    applicable.append({"fid":fid,"rank":rank,"payload_index":dep_idx,"attributes":attrs,"degree":dep["degree"]})
    candidate=(len(attrs),dep["degree"],fid,dep_idx,dep)
    if winner is None or candidate[:2]>=winner[:2]: winner=candidate
  if winner is None: break
  _,degree,fid,dep_idx,dep=winner; implied=dep["attributes"][-1]
  chosen.append((fid,dep));available.remove(implied)
  fr.append({"applicable":applicable,"winner_fid":fid,"payload_index":dep_idx,"attributes":dep["attributes"],"degree":degree,"implied_attribute":implied,"available_after":sorted(available)})
 used_attrs={a for _,dep in chosen for a in dep["attributes"]}; sels={a:q["simple_selectivities"][a] for a in used_attrs}
 original=math.prod(sels.values()) if sels else 1.0; adjusted=dict(sels)
 adjustments=[]
 for fid,dep in reversed(chosen):
  s1=math.prod(adjusted[a] for a in dep["attributes"][:-1]); implied=dep["attributes"][-1]; s2=adjusted[implied]; f=dep["degree"]
  new=(f+(1-f)*s2) if s1<=s2 else (f*s2/s1+(1-f)*s2)
  adjustments.append({"fid":fid,"implied_attribute":implied,"s1":s1,"s2_before":s2,"degree":f,"s2_after":new});adjusted[implied]=new
 fd_sel=math.prod(adjusted.values()) if adjusted else 1.0; multiplier=fd_sel/original if chosen else 1.0; estimate*=multiplier
 return {"query_index":qi,"query_id":q["id"],"baseline_rows":q["baseline_rows"],"mcv":{"applicable_selected":[i for i in q["mcv_ids"] if i in sm],"rounds":mr,"used":[x["winner"] for x in mr],"estimate":mcv_est,"remaining":mcv_remaining},"fd":{"available_selected_objects":available_objects,"rounds":fr,"used":[x[0] for x in chosen],"adjustments":adjustments,"original_selectivity_product":original,"adjusted_selectivity_product":fd_sel,"multiplier":multiplier,"available_final":sorted(available)},"raw_selectivity":estimate/model.w["relation_rows"],"rows":estimate,"truth":q["truth"],"qerror":qerror(estimate,q["truth"])}

def control(t): return (tuple(t["mcv"]["used"]),tuple(t["fd"]["used"]))
def mech(t):
 m,f=bool(t["mcv"]["used"]),bool(t["fd"]["used"])
 return "mcv_fd_composed" if m and f else ("mcv_only" if m else ("fd_only" if f else "no_extstat_consumption"))

def loo(model,qi,sm,sf,c,base):
 sm1,sf1=set(sm),set(sf);(sm1 if c[0]=="mcv" else sf1).remove(c[1]);t=trace(model,qi,sm1,sf1)
 if c[0]=="mcv" and t["mcv"]["used"]!=base["mcv"]["used"]:
  old_other=[x for x in base["mcv"]["used"] if x!=c[1]]; new_other=t["mcv"]["used"]
  kind="mcv_winner_replacement" if new_other!=old_other else "mcv_consumption_removal"
 elif t["fd"]["used"]!=base["fd"]["used"]: kind="fd_control_change" if c[0]=="fd" else "mcv_to_fd_boundary_change"
 elif control(t)==control(base): kind="numerical_only"
 else: kind="other_control_change"
 return {"candidate":key(c),"qerror_without":t["qerror"],"attribution":t["qerror"]-base["qerror"],"change_kind":kind,"trace_without":{"mcv":t["mcv"]["used"],"fd":t["fd"]["used"],"rows":t["rows"]}}

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--generalization',type=Path,required=True);ap.add_argument('--replay',type=Path,required=True);ap.add_argument('--full-design',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--report',type=Path,required=True);ap.add_argument('--transfer-csv',type=Path,required=True);ap.add_argument('--candidate-csv',type=Path,required=True);ap.add_argument('--behavior-csv',type=Path);a=ap.parse_args()
 graw=a.generalization.read_bytes();g=json.loads(graw);src=json.loads(a.replay.read_text());w=src['workload_ir'];model=Model(w);budget=g['budget_bytes'];freq={x['candidate']:x['frequency'] for x in g['selection_frequency']}
 allq=range(len(model.q)); empty={qi:trace(model,qi,set(),set()) for qi in allq}; splits=[]; transfer_rows=[]; cand=defaultdict(lambda:{"selected_splits":0,"train_structural":0,"test_structural":0,"train_consumers":0,"test_consumers":0,"train_positive":0,"train_negative":0,"test_positive":0,"test_negative":0,"train_benefit":0.0,"test_benefit":0.0})
 total_neg=repair=missing_gap=missing_best=0.0; missing_class=Counter(); dominant=Counter(); mechanism=defaultdict(lambda:{"count":0,"magnitude":0.0}); qreg=Counter(); qpos=Counter(); case62=[]; top_cases=defaultdict(list)
 for sp in g['per_split']:
  seed=sp['seed'];train=sp['train_query_indexes'];test=sp['test_query_indexes'];trset=set(train);teset=set(test);sm=set(sp['design']['selected_mcv']);sf=set(sp['design']['selected_fd']);osm=set(sp['test_oracle_design']['selected_mcv']);osf=set(sp['test_oracle_design']['selected_fd']);sel=design(sm,sf);oracle=design(osm,osf);usedbytes=sp['design']['storage']
  traces={qi:trace(model,qi,sm,sf) for qi in allq}; otraces={qi:trace(model,qi,osm,osf) for qi in test}; per=[]
  # Candidate transfer map: contextual LOO on every actual consumer.
  for c in sel:
   ck=key(c);d=cand[ck];d['selected_splits']+=1;inc=model.cq[c];d['train_structural']+=len(inc&trset);d['test_structural']+=len(inc&teset)
   for side,indexes in [('train',train),('test',test)]:
    for qi in indexes:
     t=traces[qi]
     if c[1] not in t[c[0]]['used']: continue
     x=loo(model,qi,sm,sf,c,t);val=x['attribution'];d[side+'_consumers']+=1;d[side+'_benefit']+=val
     if val>EPS:d[side+'_positive']+=1
     elif val<-EPS:d[side+'_negative']+=1
  for qi in test:
   e,t,o=empty[qi],traces[qi],otraces[qi];delta=e['qerror']-t['qerror'];out='positive' if delta>EPS else ('negative' if delta<-EPS else 'neutral');m=mech(t);mechanism[(out,m)]['count']+=1;mechanism[(out,m)]['magnitude']+=abs(delta)
   consumed=[*[("mcv",i) for i in t['mcv']['used']],*[("fd",i) for i in t['fd']['used']]];attrs=[loo(model,qi,sm,sf,c,t) for c in consumed]
   harmful=[x for x in attrs if x['attribution']< -EPS]; helpful=[x for x in attrs if x['attribution']>EPS]
   best_remove=min(attrs,key=lambda x:x['qerror_without']) if attrs else None
   removed_repair=max(0.0,t['qerror']-(best_remove['qerror_without'] if best_remove else t['qerror']))
   negmag=max(0.0,-delta);repaired=min(negmag,removed_repair);total_neg+=negmag;repair+=repaired
   missing=[]
   for c in [("mcv",i) for i in o['mcv']['used']]+[("fd",i) for i in o['fd']['used']]:
    if c in sel:continue
    sm1,sf1=set(sm),set(sf);(sm1 if c[0]=='mcv' else sf1).add(c[1]);at=trace(model,qi,sm1,sf1);gain=t['qerror']-at['qerror']
    missing.append({"candidate":key(c),"qerror_with_add":at['qerror'],"gain":gain,"useful":gain>EPS})
   best_add=max(missing,key=lambda x:x['gain']) if missing else None;gap=max(0.0,t['qerror']-o['qerror']);missing_gap+=gap;missing_best+=min(gap,max(0.0,best_add['gain'] if best_add else 0.0))
   labels=[]
   for x in harmful:
    typ=x['candidate'].split(':')[0]
    if typ=='fd':labels.append('N3_fd_harmful_correction')
    elif x['trace_without']['fd']!=t['fd']['used']:labels.append('N4_mcv_to_fd_suppression')
    elif x['change_kind']=='mcv_winner_replacement':labels.append('N1_mcv_winner_replacement')
    else:labels.append('N2_harmful_mcv_correction')
   if negmag and removed_repair+EPS<negmag:labels.append('N5_multi_statistic_interaction')
   if any(x['useful'] for x in missing):labels.append('N6_missing_test_useful')
   # Training marginal / budget diagnosis for the best useful missing candidate.
   supervision=None
   if best_add and best_add['useful']:
    typ,sid=best_add['candidate'].split(':');c=(typ,int(sid));sm1,sf1=set(sm),set(sf);(sm1 if typ=='mcv' else sf1).add(c[1]);td=0.0
    for tq in model.cq[c]&trset:td+=trace(model,tq,sm1,sf1)['qerror']-traces[tq]['qerror']
    cost=model.cands[c]['cost_bytes'];feasible=usedbytes+cost<=budget
    if td>=-EPS:supervision='S1_no_training_signal'
    elif feasible:supervision='S3_positive_feasible_add'
    else:
     bestswap=math.inf
     for old in sel:
      if usedbytes-model.cands[old]['cost_bytes']+cost>budget:continue
      sm2,sf2=set(sm),set(sf);(sm2 if old[0]=='mcv' else sf2).remove(old[1]);(sm2 if typ=='mcv' else sf2).add(c[1]);affected=(model.cq[old]|model.cq[c])&trset;dd=sum(trace(model,z,sm2,sf2)['qerror']-traces[z]['qerror'] for z in affected);bestswap=min(bestswap,dd)
     supervision='S3_positive_feasible_swap' if bestswap < -EPS else 'S2_positive_signal_budget_pressure'
     if supervision.startswith('S2'):labels.append('N7_budget_displacement')
    missing_class[supervision]+=1
   if out=='negative':
    if harmful:dom=min(harmful,key=lambda x:x['qerror_without'])['change_kind']
    elif any(x['useful'] for x in missing):dom='N6_missing_benefit_without_harmful_presence'
    else:dom='N8_unresolved'
    dominant[dom]+=1;qreg[model.q[qi]['id']]+=negmag
   if out=='positive':qpos[model.q[qi]['id']]+=delta
   row={"seed":seed,"query_index":qi,"query_id":model.q[qi]['id'],"outcome":out,"delta":delta,"mechanism":m,"empty_qerror":e['qerror'],"train_qerror":t['qerror'],"oracle_qerror":o['qerror'],"empty_rows":e['rows'],"train_rows":t['rows'],"oracle_rows":o['rows'],"mcv_trace":t['mcv']['used'],"fd_trace":t['fd']['used'],"cross_mechanism":bool(t['mcv']['used']) and trace(model,qi,set(),sf)['fd']['used']!=t['fd']['used'],"attributions":attrs,"best_single_removal":best_remove,"negative_magnitude":negmag,"repairable_single_removal":repaired,"missing_oracle":missing,"best_missing_add":best_add,"oracle_gap":gap,"labels":sorted(set(labels)),"dominant":dom if out=='negative' else None,"missing_class":supervision,"trace":{"empty":e,"train":t,"oracle":o}}
   per.append(row);transfer_rows.append({k:row[k] for k in ('seed','query_index','query_id','outcome','delta','mechanism','empty_qerror','train_qerror','oracle_qerror','cross_mechanism','negative_magnitude','repairable_single_removal','oracle_gap','dominant','missing_class')}|{"mcv_trace":json.dumps(row['mcv_trace']),"fd_trace":json.dumps(row['fd_trace']),"labels":json.dumps(row['labels']),"best_single_removal":json.dumps(best_remove),"best_missing_add":json.dumps(best_add)})
   if model.q[qi]['id']=='query.62':case62.append(row)
   if model.q[qi]['id'] in {'query.62','query.274','query.361','query.161'}:top_cases[model.q[qi]['id']].append(row)
  splits.append({"seed":seed,"train":train,"test":test,"selected_mcv":sorted(sm),"selected_fd":sorted(sf),"instances":per})
 # behavior space on all 45 design pairs
 behavior=[]
 designs=[(set(x['design']['selected_mcv']),set(x['design']['selected_fd'])) for x in g['per_split']];fulltr=[]
 for sm,sf in designs:fulltr.append([trace(model,q,sm,sf) for q in allq])
 for i,j in itertools.combinations(range(len(designs)),2):
  di,dj=design(*designs[i]),design(*designs[j]);pairs=list(zip(fulltr[i],fulltr[j]));rd=[abs(x['rows']-y['rows'])/max(abs(x['rows']),abs(y['rows']),1e-300) for x,y in pairs];qd=[abs(x['qerror']-y['qerror']) for x,y in pairs]
  behavior.append({"split_a":i,"split_b":j,"design_jaccard":len(di&dj)/len(di|dj),"identical_mcv_fraction":mean([x['mcv']['used']==y['mcv']['used'] for x,y in pairs]),"identical_fd_fraction":mean([x['fd']['used']==y['fd']['used'] for x,y in pairs]),"identical_control_fraction":mean([control(x)==control(y) for x,y in pairs]),"identical_rows_1e12_fraction":mean([r<=1e-12 for r in rd]),"mean_row_relative_difference":mean(rd),"max_row_relative_difference":max(rd),"mean_absolute_qerror_difference":mean(qd),"loss_a":sum(x['qerror'] for x in fulltr[i]),"loss_b":sum(x['qerror'] for x in fulltr[j])})
 # Candidate rows and stable-core groups
 crows=[]
 for ck,d in cand.items():
  typ,sid=ck.split(':');c=(typ,int(sid));crows.append({"candidate":ck,"mechanism":typ,"cost":model.cands[c]['cost_bytes'],"selection_frequency":freq[ck],**d})
 groups={"10/10":[],"8-9/10":[],"5-7/10":[],"1-4/10":[]}
 for r in crows:
  n=r['selected_splits'];groups['10/10' if n==10 else ('8-9/10' if n>=8 else ('5-7/10' if n>=5 else '1-4/10'))].append(r)
 core={name:{"candidates":len(rs),"mcv":sum(r['mechanism']=='mcv' for r in rs),"fd":sum(r['mechanism']=='fd' for r in rs),"mean_cost":mean([r['cost'] for r in rs]),"mean_train_consumers_per_selection":mean([r['train_consumers']/r['selected_splits'] for r in rs]),"mean_test_consumers_per_selection":mean([r['test_consumers']/r['selected_splits'] for r in rs]),"positive_test_frequency_per_selection":mean([r['test_positive']/r['selected_splits'] for r in rs]),"negative_test_frequency_per_selection":mean([r['test_negative']/r['selected_splits'] for r in rs])} for name,rs in groups.items()}
 matrix=[{"outcome":o,"mechanism":m,**v} for (o,m),v in sorted(mechanism.items())]
 def concentration(counter):
  vals=sorted(counter.values(),reverse=True);tot=sum(vals);return {"total":tot,"top1_share":sum(vals[:1])/tot if tot else 0,"top4_share":sum(vals[:4])/tot if tot else 0,"top10_share":sum(vals[:10])/tot if tot else 0}
 result={"experiment":"Generalization-Mechanism-Analysis-v0","source":str(a.generalization),"source_sha256":hashlib.sha256(graw).hexdigest(),"scope":{"splits":10,"held_out_instances":940,"frozen_payload":True,"optimization_rerun":False},"reproduction":{"counts":dict(Counter(r['outcome'] for r in transfer_rows)),"positive_magnitude":sum(max(0,float(r['delta'])) for r in transfer_rows),"negative_magnitude":total_neg},"mechanism_matrix":matrix,"negative":{"dominant":dict(dominant),"single_removal_repair":repair,"repair_fraction":repair/total_neg,"missing_oracle_gap":missing_gap,"best_single_missing_add_recovery":missing_best,"missing_recovery_fraction":missing_best/missing_gap if missing_gap else 0,"supervision_classes":dict(missing_class)},"concentration":{"negative_queries":concentration(qreg),"positive_queries":concentration(qpos),"negative_by_query":qreg.most_common(),"positive_by_query":qpos.most_common()},"behavior":{"pairs":behavior,"mean_design_jaccard":mean([x['design_jaccard'] for x in behavior]),"mean_identical_control":mean([x['identical_control_fraction'] for x in behavior]),"mean_identical_rows":mean([x['identical_rows_1e12_fraction'] for x in behavior]),"mean_row_relative_difference":mean([x['mean_row_relative_difference'] for x in behavior]),"mean_absolute_qerror_difference":mean([x['mean_absolute_qerror_difference'] for x in behavior])},"stable_core":core,"query62":case62,"top_regression_cases":dict(top_cases),"candidates":crows,"splits":splits}
 a.output.write_text(json.dumps(result,indent=2)+'\n')
 with a.transfer_csv.open('w',newline='') as f:wr=csv.DictWriter(f,fieldnames=list(transfer_rows[0]));wr.writeheader();wr.writerows(transfer_rows)
 with a.candidate_csv.open('w',newline='') as f:wr=csv.DictWriter(f,fieldnames=list(crows[0]));wr.writeheader();wr.writerows(crows)
 if a.behavior_csv:
  with a.behavior_csv.open('w',newline='') as f:wr=csv.DictWriter(f,fieldnames=list(behavior[0]));wr.writeheader();wr.writerows(behavior)
 # A compact generated report; detailed interpretation is augmented after validation.
 rep=result['reproduction'];neg=result['negative'];beh=result['behavior']
 a.report.write_text(f"""# Generalization-Mechanism-Analysis-v0\n\n## Headline\n\n- Reproduced outcomes: `{rep['counts']}`.\n- Negative magnitude: `{rep['negative_magnitude']:.6f}`; single-removal repair: `{neg['repair_fraction']:.2%}`.\n- Missed-oracle gap: `{neg['missing_oracle_gap']:.6f}`; best missing-add diagnostic recovery: `{neg['missing_recovery_fraction']:.2%}`.\n- Mean design Jaccard: `{beh['mean_design_jaccard']:.2%}`; identical complete control trace: `{beh['mean_identical_control']:.2%}`.\n\nFull traces, attributions, case studies, matrix, stable-core groups and diagnostics are in JSON/CSV.\n""")
 print(json.dumps({"reproduction":rep,"negative":neg,"behavior":{k:v for k,v in beh.items() if k!='pairs'},"stable_core":core},indent=2))
if __name__=='__main__':main()
