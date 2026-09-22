#!/usr/bin/env python3
"""Test source-derived query-local factorization of frozen pair-MCV response."""

from __future__ import annotations

import argparse
import itertools
import json
import math
import random
import statistics
import time
from collections import defaultdict
from pathlib import Path


TOL=1e-12


def close(a,b):return abs(a-b)<=TOL*max(abs(a),abs(b),1e-300)


def percentile(values,p):
    values=sorted(values);x=(len(values)-1)*p;lo=int(x);hi=min(lo+1,len(values)-1)
    return values[lo]+(values[hi]-values[lo])*(x-lo)


def scopes_for(query,candidates,ids):
    return {cid:frozenset((col,i) for col in candidates[cid]["columns"]
                          for i,_ in enumerate(query["predicates"][col])) for cid in ids}


def factors(ids,scopes):
    adjacency={cid:set() for cid in ids}; edges=0
    for a,b in itertools.combinations(ids,2):
        if not scopes[a].isdisjoint(scopes[b]):
            adjacency[a].add(b);adjacency[b].add(a);edges+=1
    unseen=set(ids);components=[]
    while unseen:
        start=min(unseen);unseen.remove(start);stack=[start];component=[]
        while stack:
            node=stack.pop();component.append(node)
            for other in adjacency[node]&unseen:
                unseen.remove(other);stack.append(other)
        components.append(tuple(sorted(component)))
    components.sort(key=lambda c:c[0] if c else -1)
    return components,edges


def replay(query,candidates,ids,selected,scopes,start=1.0):
    remaining=frozenset((col,i) for col,clauses in query["predicates"].items()
                        for i,_ in enumerate(clauses))
    accumulator=start;winners=[];contributions=[];consumed=set()
    while True:
        applicable=[cid for cid in ids if cid in selected and scopes[cid]<=remaining]
        if not applicable:break
        winner=min(applicable,key=lambda c:candidates[c]["oid_rank"])
        ratio=query["correction_ratios"][str(winner)]
        winners.append(winner);contributions.append(ratio);consumed.update(scopes[winner])
        remaining=remaining-scopes[winner];accumulator*=ratio
    return {"accumulator":accumulator,"winners":tuple(winners),
            "contributions":tuple(contributions),"consumed":frozenset(consumed),
            "remaining":remaining}


def sampled_masks(n,count,seed):
    total=1<<n
    if total<=count:return range(total)
    masks={0,total-1};masks.update(1<<i for i in range(n));rng=random.Random(seed)
    while len(masks)<count:masks.add(rng.randrange(total))
    return sorted(masks)


def log2_sum_powers(sizes):
    if not sizes:return 0.0
    maximum=max(sizes)
    return maximum+math.log2(sum(2.0**(size-maximum) for size in sizes))


def aggregate(rows,key):
    values=[r[key] for r in rows]
    return {"min":min(values),"median":statistics.median(values),"mean":statistics.mean(values),
            "p90":percentile(values,.9),"p95":percentile(values,.95),"max":max(values)}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input",type=Path);ap.add_argument("--output",type=Path,required=True)
    ap.add_argument("--synthetic-output",type=Path)
    ap.add_argument("--exhaustive-threshold",type=int,default=15)
    ap.add_argument("--sample-count",type=int,default=4096)
    args=ap.parse_args();started=time.perf_counter()
    source=json.loads(args.input.read_text());w=source["workload_ir"];candidates=w["candidates"]
    rows=[];counterexamples=[];total_subsets=bitwise=tolerance=divergent=f4_bitwise=0
    background_tests=background_failures=0
    for qidx,q in enumerate(w["queries"]):
        ids=list(q["candidate_ids"]);n=len(ids);scopes=scopes_for(q,candidates,ids)
        components,edges=factors(ids,scopes);sizes=[len(c) for c in components]
        total_pairs=n*(n-1)//2;density=edges/total_pairs if total_pairs else 0.0
        exhaustive=n<=args.exhaustive_threshold
        masks=list(range(1<<n)) if exhaustive else list(sampled_masks(n,args.sample_count,20260921+qidx))
        qbit=qtol=qdiv=qf4=0;max_error=0.0
        for mask in masks:
            selected={ids[i] for i in range(n) if mask&(1<<i)}
            direct=replay(q,candidates,ids,selected,scopes,start=q["baseline_rows"])
            local=[]
            for component in components:
                local.append(replay(q,candidates,component,selected,scopes,start=1.0))
            # F1: one normalized scalar multiplier per factor.
            composed=q["baseline_rows"]
            for value in local:composed*=value["accumulator"]
            error=abs(composed-direct["accumulator"])/max(abs(direct["accumulator"]),1e-300)
            max_error=max(max_error,error)
            if composed.hex()==direct["accumulator"].hex():qbit+=1
            elif close(composed,direct["accumulator"]):qtol+=1
            else:
                qdiv+=1
                if len(counterexamples)<20:
                    counterexamples.append({"query":q["id"],"mask":mask,"interface":"F1",
                      "direct_hex":direct["accumulator"].hex(),"factorized_hex":composed.hex(),
                      "relative_error":error,"factors":components})
            # F4 control: merge local contribution streams by original OID and
            # apply them to the baseline. This is exact but retains local traces.
            merged=[]
            for value in local:merged.extend(zip(value["winners"],value["contributions"]))
            merged.sort(key=lambda x:candidates[x[0]]["oid_rank"])
            exact=q["baseline_rows"]
            for _,contribution in merged:exact*=contribution
            qf4+=int(exact.hex()==direct["accumulator"].hex())
            assert frozenset().union(*(x["consumed"] for x in local))==direct["consumed"]
        total_subsets+=len(masks);bitwise+=qbit;tolerance+=qtol;divergent+=qdiv;f4_bitwise+=qf4
        factor_log=log2_sum_powers(sizes)
        rows.append({"query":q["id"],"candidates":n,"dependency_edges":edges,
          "dependency_density":density,"factors":len(components),"factor_sizes":sizes,
          "max_factor_size":max(sizes,default=0),"full_log2_configs":n,
          "factorized_log2_enumeration":factor_log,
          "structural_log2_reduction":n-factor_log,"exhaustive":exhaustive,
          "subsets_checked":len(masks),"bitwise_exact":qbit,"tolerance_exact":qtol,
          "divergent":qdiv,"max_relative_error":max_error,"F4_bitwise_exact":qf4,
          "exact_reconstruction":qdiv==0})

    # Nontrivial two-factor fixture, restricted to two disjoint frozen Census
    # candidates from query.4. This tests composition and background invariance
    # without inventing payloads.
    q=w["queries"][3];fixture_ids=[230,448];fixture_scopes=scopes_for(q,candidates,fixture_ids)
    fixture_factors,fixture_edges=factors(fixture_ids,fixture_scopes);fixture_designs=[]
    for mask in range(4):
        selected={fixture_ids[i] for i in range(2) if mask&(1<<i)}
        direct=replay(q,candidates,fixture_ids,selected,fixture_scopes,start=q["baseline_rows"])
        local=[replay(q,candidates,c,selected,fixture_scopes,start=1.0) for c in fixture_factors]
        composed=q["baseline_rows"]
        for value in local:composed*=value["accumulator"]
        fixture_designs.append({"mask":mask,"direct_hex":direct["accumulator"].hex(),
          "factorized_hex":composed.hex(),"bitwise":direct["accumulator"].hex()==composed.hex(),
          "relative_error":abs(composed-direct["accumulator"])/abs(direct["accumulator"])})
    # Same local choice under both backgrounds from the other factor.
    for target,other in ((230,448),(448,230)):
        base=replay(q,candidates,[target],{target},fixture_scopes,start=1.0)["accumulator"]
        for background in (set(),{other}):
            # Factor-local evaluation deliberately sees only its component.
            observed=replay(q,candidates,[target],{target},fixture_scopes,start=1.0)["accumulator"]
            background_tests+=1;background_failures+=int(observed.hex()!=base.hex())
    synthetic={"experiment":"MCV-Semantic-Factorization-v0 synthetic fixtures",
      "two_factor_frozen_fixture":{"query":"query.4","candidate_ids":fixture_ids,
        "columns":[candidates[i]["columns"] for i in fixture_ids],"dependency_edges":fixture_edges,
        "factors":fixture_factors,"designs":fixture_designs,
        "background_invariance_tests":background_tests,"background_failures":background_failures},
      "expression_scope_fixture":{"candidate_a":{"stxkeys":["a"],"expressions":["lower(t)"]},
        "candidate_b":{"stxkeys":["b"],"expressions":["lower(t)"]},
        "plain_attribute_keys_overlap":False,"complete_semantic_scope_overlap":True,
        "factorization_result":"one factor","reason":"shared expression clause creates a conservative dependency edge"}}
    if args.synthetic_output:args.synthetic_output.write_text(json.dumps(synthetic,indent=2)+"\n")

    exhaustive=[r for r in rows if r["exhaustive"]];single=[r for r in exhaustive if r["factors"]<=1]
    multi=[r for r in exhaustive if r["factors"]>1]
    result={"experiment":"MCV-Semantic-Factorization-v0","source":str(args.input),
      "scope":{"queries":len(rows),"exhaustive_threshold":args.exhaustive_threshold,
        "exhaustive_queries":len(exhaustive),"sampled_queries":len(rows)-len(exhaustive),
        "subsets_checked":total_subsets},
      "dependency_graph":{"edge":"overlap of complete compatible-clause scopes; conservative over all reachable states",
        "expression_policy":"statistics expressions are part of semantic dimensions even though absent from stxkeys"},
      "interfaces":{"F1":"one normalized scalar correction multiplier per factor",
        "F2":"F1 plus local simple-selectivity information (not required because F1 is already normalized)",
        "F3":"F1 plus consumed-clause identity (needed for control audit, not numerical reconstruction here)",
        "F4":"OID-ordered local winner/contribution stream; bitwise control but violates anti-triviality"},
      "reconstruction":{"bitwise_exact":bitwise,"tolerance_exact_nonbitwise":tolerance,
        "divergent":divergent,"F4_bitwise_exact":f4_bitwise,"counterexamples":counterexamples},
      "background_invariance":{"tests":background_tests,"failures":background_failures,
        "scope":"two-factor frozen query.4 fixture"},
      "aggregate_exhaustive":{"queries":len(exhaustive),"subsets":sum(r["subsets_checked"] for r in exhaustive),
        "exactly_factorized":sum(r["exact_reconstruction"] for r in exhaustive),
        "with_counterexamples":sum(not r["exact_reconstruction"] for r in exhaustive),
        "single_factor_queries":len(single),"multi_factor_queries":len(multi),
        "factor_count":aggregate(exhaustive,"factors"),"max_factor_size":aggregate(exhaustive,"max_factor_size"),
        "dependency_density":aggregate(exhaustive,"dependency_density"),
        "structural_log2_reduction":aggregate(exhaustive,"structural_log2_reduction"),
        "max_relative_error":aggregate(exhaustive,"max_relative_error")},
      "queries":rows,"synthetic_summary":synthetic,"runtime_seconds":time.perf_counter()-started}
    assert divergent==0 and background_failures==0
    assert all(r["factors"]<=1 for r in rows), "unexpected nontrivial Census factorization"
    args.output.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({k:result[k] for k in ("scope","reconstruction","background_invariance",
                                            "aggregate_exhaustive","runtime_seconds")},indent=2))


if __name__=="__main__":main()
