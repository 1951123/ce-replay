#!/usr/bin/env python3
"""Measure query-local semantic-state equivalence for frozen Census pair-MCVs."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import random
import statistics
import time
from collections import defaultdict
from pathlib import Path

from ce_replay_optimize_v1 import qerror


TOL = 1e-12


def close(a, b, tol=TOL):
    return abs(a-b) <= tol * max(abs(a), abs(b), 1e-300)


def percentile(values, p):
    values=sorted(values); pos=(len(values)-1)*p; lo=int(pos); hi=min(lo+1,len(values)-1)
    return values[lo]+(values[hi]-values[lo])*(pos-lo)


def replay(query, candidates, local_ids, mask, with_trace=True):
    remaining=set(query["predicates"]); estimate=query["baseline_rows"]; rounds=[]
    selected=[local_ids[i] for i in range(len(local_ids)) if mask&(1<<i)]
    while True:
        applicable=[cid for cid in selected if set(candidates[cid]["columns"])<=remaining]
        if not applicable: break
        applicable.sort(key=lambda cid:candidates[cid]["oid_rank"])
        winner=applicable[0]; before=tuple(sorted(remaining)); consumed=tuple(candidates[winner]["columns"])
        contribution=query["correction_ratios"][str(winner)]
        remaining-=set(consumed)
        if with_trace:
            rounds.append({"remaining_before":before,"applicable":tuple(applicable),
                           "winner":winner,"precedence_rank":candidates[winner]["oid_rank"],
                           "consumed":consumed,"remaining_after":tuple(sorted(remaining)),
                           "contribution_hex":float(contribution).hex()})
        estimate*=contribution
    trace_key=tuple((r["remaining_before"],r["applicable"],r["winner"],r["precedence_rank"],
                     r["consumed"],r["remaining_after"],r["contribution_hex"]) for r in rounds)
    winner_key=tuple((r["winner"],r["contribution_hex"]) for r in rounds)
    remaining_key=tuple(sorted(remaining))
    return {"mask":mask,"remaining":remaining_key,"trace":trace_key,"winner_trace":winner_key,
            "estimate":estimate,"estimate_hex":float(estimate).hex(),
            "qerror":qerror(estimate,query["truth"]),"rounds":rounds}


def numerical_class_count(values):
    values=sorted(values)
    if not values:return 0
    count=1; representative=values[0]
    for value in values[1:]:
        if not close(value,representative):
            count+=1; representative=value
    return count


def sampled_masks(n, count, seed):
    total=1<<n
    if count>=total:return range(total)
    masks={0,total-1}
    masks.update(1<<i for i in range(n))
    masks.update((total-1)^(1<<i) for i in range(n))
    rng=random.Random(seed)
    while len(masks)<count:masks.add(rng.randrange(total))
    return sorted(masks)


def continuation_counterexample(query,candidates,ids,left,right,results,exhaustive_limit,seed):
    n=len(ids); free=((1<<n)-1)&~(left|right); positions=[i for i in range(n) if free&(1<<i)]
    exhaustive=len(positions)<=exhaustive_limit
    continuations=(range(1<<len(positions)) if exhaustive else sampled_masks(len(positions),256,seed))
    tested=0
    for compact in continuations:
        extension=0
        for j,pos in enumerate(positions):
            if compact&(1<<j):extension|=1<<pos
        lm,rm=left|extension,right|extension
        l=results.get(lm) or replay(query,candidates,ids,lm)
        r=results.get(rm) or replay(query,candidates,ids,rm)
        tested+=1
        if l["remaining"]!=r["remaining"] or not close(l["estimate"],r["estimate"]):
            return {"left_mask":left,"right_mask":right,"continuation_mask":extension,
                    "left_union_mask":lm,"right_union_mask":rm,"left_result":compact_result(l),
                    "right_result":compact_result(r),"continuations_tested":tested,
                    "continuations_exhaustive":exhaustive}
    return None


def compact_result(result):
    return {"remaining":result["remaining"],"estimate_hex":result["estimate_hex"],
            "winner_trace":[x[0] for x in result["winner_trace"]]}


def analyze_query(qidx,query,candidates,exhaustive_threshold,sample_count,continuation_limit):
    ids=list(query["candidate_ids"]); n=len(ids); total=1<<n; exhaustive=n<=exhaustive_threshold
    masks=list(range(total)) if exhaustive else list(sampled_masks(n,min(sample_count,total),20260921+qidx))
    results={}; controls=set(); traces=set(); winner_traces=set(); full=set(); estimates=[]
    deterministic_checks=0
    for mask in masks:
        result=replay(query,candidates,ids,mask); results[mask]=result
        controls.add(result["remaining"]); traces.add(result["trace"]); winner_traces.add(result["winner_trace"])
        full.add((result["remaining"],result["estimate_hex"])); estimates.append(result["estimate"])
    assert len(results)==len(masks), "each evaluated subset must have exactly one oracle result"
    for mask in masks[:min(16,len(masks))]:
        again=replay(query,candidates,ids,mask)
        assert results[mask]["trace"]==again["trace"] and results[mask]["estimate_hex"]==again["estimate_hex"]
        deterministic_checks+=1

    # Search projected full-state merges for failure under arbitrary subset extension.
    classes=defaultdict(list)
    for mask,result in results.items():classes[(result["remaining"],result["estimate_hex"])].append(mask)
    for group in classes.values():
        reference=results[group[0]]["estimate"]
        assert all(close(reference,results[mask]["estimate"]) for mask in group), \
            "projected full state merged materially different current outputs"
    soundness={"merge_classes":sum(len(v)>1 for v in classes.values()),"pairs_tested":0,
               "continuations_tested":0,"exhaustive_continuation_pairs":0,"counterexample":None}
    if exhaustive:
        for group in classes.values():
            if len(group)<2:continue
            # Deterministic bounded pair set; all pairs for small classes.
            pairs=list(itertools.combinations(group,2))
            if len(pairs)>256:pairs=pairs[:256]
            for pair_index,(left,right) in enumerate(pairs):
                soundness["pairs_tested"]+=1
                ce=continuation_counterexample(query,candidates,ids,left,right,results,
                                               continuation_limit,20260921+qidx*1000+pair_index)
                if ce:
                    soundness["continuations_tested"]+=ce["continuations_tested"]
                    soundness["exhaustive_continuation_pairs"]+=int(ce["continuations_exhaustive"])
                    soundness["counterexample"]=ce; break
                free=n-(left|right).bit_count()
                count=(1<<free) if free<=continuation_limit else 256
                soundness["continuations_tested"]+=count
                soundness["exhaustive_continuation_pairs"]+=int(free<=continuation_limit)
            if soundness["counterexample"]:break

    # Transition commutativity at every distinct realized remaining-clause state.
    remaining_states={r["remaining"] for r in results.values()}
    comm={"tested_pairs":0,"control_commutative":0,"fully_semantic_commutative":0,
          "non_commutative":0,"reasons":defaultdict(int)}
    ratios={cid:query["correction_ratios"][str(cid)] for cid in ids}
    for state in remaining_states:
        enabled=[cid for cid in ids if set(candidates[cid]["columns"])<=set(state)]
        for a,b in itertools.combinations(enabled,2):
            comm["tested_pairs"]+=1; ca=set(candidates[a]["columns"]); cb=set(candidates[b]["columns"])
            after_a=set(state)-ca; after_b=set(state)-cb
            ab=cb<=after_a; ba=ca<=after_b
            if not (ab and ba):
                comm["non_commutative"]+=1
                comm["reasons"]["overlap_applicability_change"]+=1
                continue
            comm["control_commutative"]+=1
            e1=(1.0*ratios[a])*ratios[b]; e2=(1.0*ratios[b])*ratios[a]
            if tuple(sorted(after_a-cb))==tuple(sorted(after_b-ca)) and e1.hex()==e2.hex():
                comm["fully_semantic_commutative"]+=1
            else:
                comm["non_commutative"]+=1; comm["reasons"]["numerical_composition"]+=1
    comm["reasons"]=dict(comm["reasons"])

    return {"query":query["id"],"query_index":qidx,"candidates":n,
            "physical_subsets":total,"subsets_evaluated":len(masks),"exhaustive":exhaustive,
            "control_states":len(controls),"traces":len(traces),"winner_only_traces":len(winner_traces),
            "numerical_outcomes":numerical_class_count(estimates),"full_semantic_states":len(full),
            "conservative_merge_safe_states":len(masks),
            "subset_control_compression":len(masks)/len(controls),
            "subset_full_compression":len(masks)/len(full),
            "deterministic_checks":deterministic_checks,"projected_state_soundness":soundness,
            "commutativity":comm},results


def interaction_analysis(rows,all_results,workload,max_n=10):
    tested_queries=tested_contexts=potential_pairs=nondep_pairs=realized_nondep=0; counterexample=None
    candidates=workload["candidates"]
    for row in rows:
        if not row["exhaustive"] or row["candidates"]>max_n:continue
        tested_queries+=1; q=workload["queries"][row["query_index"]]; ids=q["candidate_ids"]; results=all_results[row["query_index"]]
        n=len(ids)
        for ai,bi in itertools.combinations(range(n),2):
            a,b=ids[ai],ids[bi]; dependent=bool(set(candidates[a]["columns"])&set(candidates[b]["columns"]))
            potential_pairs+=int(dependent); nondep_pairs+=int(not dependent)
            other=[i for i in range(n) if i not in (ai,bi)]
            for compact in range(1<<len(other)):
                mask=0
                for j,pos in enumerate(other):
                    if compact&(1<<j):mask|=1<<pos
                ma=mask|(1<<ai); mb=mask|(1<<bi); mab=ma|(1<<bi)
                l0=results[mask]["qerror"]; la=results[ma]["qerror"]
                lb=results[mb]["qerror"]; lab=results[mab]["qerror"]
                delta_b=l0-lb; delta_b_after_a=la-lab; tested_contexts+=1
                realized=not close(delta_b,delta_b_after_a)
                if not dependent and realized:
                    realized_nondep+=1
                    if counterexample is None:
                        counterexample={"query":q["id"],"a":a,"b":b,"background_mask":mask,
                                        "a_columns":candidates[a]["columns"],"b_columns":candidates[b]["columns"],
                                        "delta_b":delta_b,"delta_b_after_a":delta_b_after_a,
                                        "estimates":{"D":results[mask]["estimate_hex"],
                                          "D+a":results[ma]["estimate_hex"],"D+b":results[mb]["estimate_hex"],
                                          "D+a+b":results[mab]["estimate_hex"]},
                                        "explanation":"CE transitions commute, but q-error is nonlinear in the combined estimate."}
    return {"scope":"all exhaustive queries with <=10 candidates","queries":tested_queries,
            "contextual_marginals_tested":tested_contexts,"potential_dependency_pairs":potential_pairs,
            "nondependency_pairs":nondep_pairs,"nondependency_realized_interactions":realized_nondep,
            "implication_holds":realized_nondep==0,"counterexample":counterexample}


def aggregate(rows,key):
    values=[r[key] for r in rows if r["exhaustive"]]
    return {"min":min(values),"median":statistics.median(values),"mean":statistics.mean(values),
            "p90":percentile(values,.9),"p95":percentile(values,.95),"max":max(values)}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input",type=Path); ap.add_argument("--output",type=Path,required=True)
    ap.add_argument("--exhaustive-threshold",type=int,default=15)
    ap.add_argument("--sample-count",type=int,default=4096)
    ap.add_argument("--continuation-exhaustive-limit",type=int,default=10)
    args=ap.parse_args(); started=time.perf_counter()
    source=json.loads(args.input.read_text()); workload=source["workload_ir"]
    rows=[]; all_results={}; counterexamples=[]
    for qidx,q in enumerate(workload["queries"]):
        row,results=analyze_query(qidx,q,workload["candidates"],args.exhaustive_threshold,
                                  args.sample_count,args.continuation_exhaustive_limit)
        rows.append(row)
        if row["exhaustive"] and row["candidates"]<=10:all_results[qidx]=results
        ce=row["projected_state_soundness"]["counterexample"]
        if ce and len(counterexamples)<20:counterexamples.append({"query":q["id"],**ce})
    interactions=interaction_analysis(rows,all_results,workload)
    exhaustive=[r for r in rows if r["exhaustive"]]
    result={"experiment":"CE-Semantic-State-v0","source":str(args.input),
      "scope":{"queries":len(rows),"exhaustive_threshold":args.exhaustive_threshold,
               "sample_count_large_queries":args.sample_count,"exhaustive_queries":len(exhaustive),
               "sampled_queries":len(rows)-len(exhaustive),
               "exhaustive_subsets":sum(r["subsets_evaluated"] for r in exhaustive),
               "sampled_subsets":sum(r["subsets_evaluated"] for r in rows if not r["exhaustive"])},
      "canonical_states":{"projected_control":"final remaining compatible columns",
        "strict_trace":"all rounds including applicable set, winner/rank, consumed columns, and exact contribution",
        "numerical":"raw rows clustered at relative tolerance 1e-12",
        "projected_full":"(final remaining columns, exact IEEE-754 rows hex)",
        "conservative_merge_safe":"projected full state plus physical selected subset"},
      "queries":rows,"aggregate_exhaustive":{"subset_control_compression":aggregate(rows,"subset_control_compression"),
        "subset_full_compression":aggregate(rows,"subset_full_compression")},
      "projected_state_counterexamples":counterexamples,"dependency_vs_interaction":interactions,
      "correctness":{"direct_results":sum(r["subsets_evaluated"] for r in rows),
        "deterministic_replays":sum(r["deterministic_checks"] for r in rows),
        "full_state_current_output_collisions":0,
        "claimed_merge_safe_continuation_divergences":0,
        "note":"Arbitrary-extension safety is claimed only for the conservative key containing the subset; projected-state failures are reported as counterexamples."},
      "runtime_seconds":time.perf_counter()-started}
    args.output.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({"scope":result["scope"],"aggregate":result["aggregate_exhaustive"],
      "projected_counterexamples":len(counterexamples),"dependency_vs_interaction":interactions,
      "runtime_seconds":result["runtime_seconds"]},indent=2))


if __name__=="__main__":main()
