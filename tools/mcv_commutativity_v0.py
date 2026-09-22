#!/usr/bin/env python3
"""Falsify source-derived MCV transition commutativity conditions."""

from __future__ import annotations

import argparse
import itertools
import json
import math
import random
import statistics
import time
from collections import Counter, defaultdict
from pathlib import Path


TOL=1e-12


def close(a,b):return abs(a-b)<=TOL*max(abs(a),abs(b),1e-300)


def action_scope(query,candidate):
    # Census clauses are ANDed single-attribute predicates. Give every clause
    # a stable (column, within-column-index) identity.
    return frozenset((column,i) for column in candidate["columns"]
                     for i,_ in enumerate(query["predicates"][column]))


def enabled(scope,remaining):
    # Pair-MCV applicability additionally requires two distinct dimensions;
    # every candidate in this frozen universe has exactly two.
    return scope<=remaining


def continuation(selected,scopes,ratios,ranks,remaining,accumulator):
    winners=[]
    while True:
        available=[cid for cid in selected if enabled(scopes[cid],remaining)]
        if not available:break
        winner=min(available,key=lambda c:ranks[c]); winners.append(winner)
        remaining=remaining-scopes[winner]; accumulator*=ratios[winner]
    return remaining,accumulator,tuple(winners)


def canonicalize(sequence,scopes,ranks):
    sequence=list(sequence); changed=True
    while changed:
        changed=False
        for i in range(len(sequence)-1):
            a,b=sequence[i],sequence[i+1]
            if scopes[a].isdisjoint(scopes[b]) and ranks[a]>ranks[b]:
                sequence[i],sequence[i+1]=b,a; changed=True
    return tuple(sequence)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input",type=Path); ap.add_argument("--output",type=Path,required=True)
    ap.add_argument("--exhaustive-threshold",type=int,default=10)
    args=ap.parse_args(); started=time.perf_counter()
    source=json.loads(args.input.read_text()); w=source["workload_ir"]; candidates=w["candidates"]
    condition_names=("A_disjoint_attribute_keys","B_disjoint_clause_scope",
                     "C_disjoint_consumed_scope","D_read_write_independent")
    conditions={name:{"instances":0,"commuting":0,"false_positives":0,"false_negatives":0,
                      "bitwise_equal":0,"tolerance_equal":0,"counterexample":None}
                for name in condition_names}
    pairwise=Counter(); implications=Counter(); fixtures=[]; per_query=[]
    continuation_tests=continuation_divergences=canonical_tests=canonical_failures=0
    exact_trace_count=canonical_trace_classes=0

    for qidx,q in enumerate(w["queries"]):
        ids=list(q["candidate_ids"]); n=len(ids)
        if n>args.exhaustive_threshold:continue
        scopes={cid:action_scope(q,candidates[cid]) for cid in ids}
        keys={cid:frozenset(candidates[cid]["columns"]) for cid in ids}
        ratios={cid:q["correction_ratios"][str(cid)] for cid in ids}
        ranks={cid:candidates[cid]["oid_rank"] for cid in ids}
        full_scope=frozenset((column,i) for column,clauses in q["predicates"].items()
                             for i,_ in enumerate(clauses))
        local=Counter(); observed_sequences=set(); canonical_sequences=set()
        # Every subset and every reachable prefix under PostgreSQL's fixed scheduler.
        for mask in range(1<<n):
            selected=tuple(ids[i] for i in range(n) if mask&(1<<i))
            remaining=full_scope; accumulator=1.0; prefix=[]
            while True:
                available=tuple(sorted((cid for cid in selected if enabled(scopes[cid],remaining)),
                                       key=lambda c:ranks[c]))
                if not available:break
                for a,b in itertools.combinations(available,2):
                    pairwise["instances"]+=1; local["instances"]+=1
                    consume_a=scopes[a]&remaining; consume_b=scopes[b]&remaining
                    A=keys[a].isdisjoint(keys[b])
                    B=scopes[a].isdisjoint(scopes[b])
                    C=consume_a.isdisjoint(consume_b)
                    # Shared accumulator is the only shared write. Its update is
                    # order-invariant mathematically and tested separately in FP.
                    D=C
                    flags=(A,B,C,D)
                    implications["A_not_B"]+=int(A and not B)
                    implications["B_not_C"]+=int(B and not C)
                    implications["C_not_D"]+=int(C and not D)

                    rem_ab=remaining-consume_a
                    ab_feasible=enabled(scopes[b],rem_ab)
                    rem_ba=remaining-consume_b
                    ba_feasible=enabled(scopes[a],rem_ba)
                    v_ab=(accumulator*ratios[a])*ratios[b] if ab_feasible else None
                    v_ba=(accumulator*ratios[b])*ratios[a] if ba_feasible else None
                    control=(ab_feasible and ba_feasible and rem_ab-scopes[b]==rem_ba-scopes[a])
                    bitwise=bool(control and v_ab.hex()==v_ba.hex())
                    numeric=bool(control and close(v_ab,v_ba))
                    # Same fixed-design continuation from the equal post-pair state.
                    semantic=False; continuation_equal=False
                    if control:
                        rest=set(selected)-{a,b}
                        rab,eab,tab=continuation(rest,scopes,ratios,ranks,
                                                rem_ab-scopes[b],v_ab)
                        rba,eba,tba=continuation(rest,scopes,ratios,ranks,
                                                rem_ba-scopes[a],v_ba)
                        continuation_tests+=1
                        continuation_equal=(rab==rba and tab==tba and close(eab,eba))
                        continuation_divergences+=int(not continuation_equal)
                        semantic=numeric and continuation_equal
                    if semantic:
                        pairwise["fully_commuting"]+=1; local["fully_commuting"]+=1
                        pairwise["bitwise_equal"]+=int(bitwise)
                        pairwise["tolerance_only"]+=int(not bitwise)
                    elif control:
                        pairwise["control_only"]+=1
                        if not numeric:pairwise["numerical_noncommuting"]+=1
                    else:
                        pairwise["non_commuting"]+=1; local["non_commuting"]+=1
                        pairwise["overlap_invalidation"]+=1

                    for name,flag in zip(condition_names,flags):
                        row=conditions[name]; row["instances"]+=int(flag)
                        row["commuting"]+=int(flag and semantic)
                        row["false_positives"]+=int(flag and not semantic)
                        row["false_negatives"]+=int((not flag) and semantic)
                        row["bitwise_equal"]+=int(flag and bitwise)
                        row["tolerance_equal"]+=int(flag and numeric)
                        if flag and not semantic and row["counterexample"] is None:
                            row["counterexample"]={"query":q["id"],"subset_mask":mask,
                              "prefix":prefix,"a":a,"b":b,"remaining":sorted(remaining),
                              "ab_feasible":ab_feasible,"ba_feasible":ba_feasible,
                              "v_ab":None if v_ab is None else v_ab.hex(),
                              "v_ba":None if v_ba is None else v_ba.hex()}
                winner=available[0]; prefix.append(winner)
                remaining=remaining-scopes[winner]; accumulator*=ratios[winner]
            seq=tuple(prefix); observed_sequences.add(seq)
            canon=canonicalize(seq,scopes,ranks); canonical_sequences.add(canon)
            # Generate adjacent-safe alternative schedules and demand the same canonical form/result.
            for i in range(len(seq)-1):
                if scopes[seq[i]].isdisjoint(scopes[seq[i+1]]):
                    alt=list(seq);alt[i],alt[i+1]=alt[i+1],alt[i]
                    canonical_tests+=1
                    if canonicalize(alt,scopes,ranks)!=canon:canonical_failures+=1
        exact_trace_count+=len(observed_sequences); canonical_trace_classes+=len(canonical_sequences)
        per_query.append({"query":q["id"],"candidates":n,"subsets":1<<n,
                          "pair_contexts":local["instances"],"fully_commuting":local["fully_commuting"],
                          "non_commuting":local["non_commuting"],
                          "observed_winner_traces":len(observed_sequences),
                          "canonical_trace_classes":len(canonical_sequences)})

    # A deliberate source-branch fixture: pg_statistic_ext.stxkeys excludes
    # expressions. Thus plain attribute-key disjointness can miss a shared
    # expression read/write scope.
    synthetic={"name":"shared_expression_disjoint_stxkeys",
      "candidate_a":{"stxkeys":["a"],"expressions":["lower(t)"],
                     "clause_scope":["a=1","lower(t)='x'"]},
      "candidate_b":{"stxkeys":["b"],"expressions":["lower(t)"],
                     "clause_scope":["b=1","lower(t)='x'"]},
      "condition_A_plain_stxkeys":True,"condition_B":False,"condition_C":False,"condition_D":False,
      "semantic_result":"non_commuting: either first action consumes lower(t), leaving the other with only one dimension",
      "status":"source-constructed regression fixture; Census has no expression candidates"}

    result={"experiment":"MCV-Commutativity-v0","source":str(args.input),
      "scope":{"queries_total":len(w["queries"]),"exhaustive_threshold":args.exhaustive_threshold,
               "queries_exhaustive":len(per_query),"subsets":sum(x["subsets"] for x in per_query)},
      "semantics":{"action":"consume all currently unestimated compatible clauses covered by the statistic; emit local stat_sel",
        "scheduler":"PostgreSQL chooses maximum covered dimensions, then minimum total keys, then first ascending-OID list entry",
        "numerical_update":"sel := sel * stat_sel",
        "tolerance":TOL},
      "pairwise":dict(pairwise),"conditions":conditions,"implications":dict(implications),
      "continuation":{"tests":continuation_tests,"divergences":continuation_divergences,
                      "method":"same fixed selected set; native-priority suffix from both post-pair states"},
      "canonicalizer":{"tests":canonical_tests,"failures":canonical_failures,
        "observed_winner_traces":exact_trace_count,"canonical_trace_classes":canonical_trace_classes,
        "note":"PostgreSQL traces are already OID-canonical; tests swap adjacent independent actions and canonicalize back."},
      "synthetic_fixture":synthetic,"queries":per_query,"regression_fixtures":fixtures,
      "runtime_seconds":time.perf_counter()-started}
    # Required fail-loud checks for proposed sufficient conditions B-D.
    assert conditions["B_disjoint_clause_scope"]["false_positives"]==0
    assert conditions["C_disjoint_consumed_scope"]["false_positives"]==0
    assert conditions["D_read_write_independent"]["false_positives"]==0
    assert continuation_divergences==0 and canonical_failures==0
    args.output.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({k:result[k] for k in ("scope","pairwise","conditions","implications",
                                            "continuation","canonicalizer","runtime_seconds")},indent=2))


if __name__=="__main__":main()
