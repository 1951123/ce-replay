#!/usr/bin/env python3
"""Joint MCV+FD optimization and cross-mechanism Census for Census."""

from __future__ import annotations

import argparse
import json
import re
import statistics
import struct
import time
from collections import defaultdict
from pathlib import Path

import psycopg

from ce_replay_optimize_v1 import load_queries, qerror


RAW_RE = re.compile(r" rows=([^ ]+)")


def text(value):
    return value.decode("utf-8") if isinstance(value, bytes) else value


def parse_payload(value, attnames):
    obj = json.loads(text(value))
    out = []
    for key, degree in obj.items():
        left, right = key.split(" => ")
        nums = [int(x.strip()) for x in left.split(",")] + [int(right)]
        out.append({"attributes": [attnames[n] for n in nums],
                    "degree": float(degree)})
    return out


def parse_binary_payload(value, attnames):
    data = bytes(value); offset = 0
    _, _, count = struct.unpack_from("=III", data, offset); offset += 12
    out = []
    for _ in range(count):
        degree = struct.unpack_from("=d", data, offset)[0]; offset += 8
        count_attrs = struct.unpack_from("=h", data, offset)[0]; offset += 2
        nums = list(struct.unpack_from("=" + "h"*count_attrs, data, offset))
        offset += 2*count_attrs
        out.append({"attributes": [attnames[n] for n in nums], "degree": degree})
    if offset != len(data): raise ValueError((offset, len(data)))
    return out


def replay_mcv_stage(query, selected_mcv, mcv, ranks):
    remaining = set(query["predicates"])
    estimate = query["baseline_rows"]
    used_mcv = []
    while True:
        eligible = [cid for cid in query["mcv_ids"] if cid in selected_mcv
                    and set(mcv[cid]["columns"]) <= remaining]
        if not eligible:
            break
        winner = min(eligible, key=lambda cid: ranks[cid])
        estimate *= query["mcv_ratios"][str(winner)]
        remaining -= set(mcv[winner]["columns"])
        used_mcv.append(winner)
    return estimate, remaining, used_mcv


def replay_fd_stage(query, estimate, remaining, selected_fd, fd, detailed=False):
    available = set(query["fd_columns"]) & remaining
    payloads = []
    for fid in query["fd_ids"]:
        if fid in selected_fd and set(fd[fid]["columns"]) <= available:
            payloads.append((fd[fid]["oid_rank"], fid, fd[fid]["payload"]))
    payloads.sort()
    chosen = []
    while True:
        winner = None
        for _, fid, payload in payloads:
            for dep in payload:
                attrs = dep["attributes"]
                if not set(attrs) <= available:
                    continue
                candidate = (len(attrs), dep["degree"], fid, dep)
                # Native code replaces on an exact strength tie (last seen).
                if winner is None or candidate[:2] >= winner[:2]:
                    winner = candidate
        if winner is None:
            break
        dep = winner[3]
        chosen.append((winner[2], dep))
        available.remove(dep["attributes"][-1])

    used_attrs = {a for _, dep in chosen for a in dep["attributes"]}
    sels = {a: query["simple_selectivities"][a] for a in used_attrs}
    original_product = 1.0
    for value in sels.values():
        original_product *= value
    for _, dep in reversed(chosen):
        s1 = 1.0
        for attr in dep["attributes"][:-1]:
            s1 *= sels[attr]
        implied = dep["attributes"][-1]
        s2, f = sels[implied], dep["degree"]
        sels[implied] = (f + (1-f)*s2) if s1 <= s2 else (f*s2/s1 + (1-f)*s2)
    fd_sel = 1.0
    for value in sels.values():
        fd_sel *= value
    if chosen:
        estimate *= fd_sel / original_product
    used = ([{"fid": fid, "attributes": dep["attributes"], "degree": dep["degree"]}
             for fid, dep in chosen] if detailed else [fid for fid, _ in chosen])
    return estimate, used, available


def replay(query, selected_mcv, selected_fd, mcv, fd, ranks, trace=False):
    estimate, remaining, used_mcv = replay_mcv_stage(query, selected_mcv, mcv, ranks)
    estimate, used_fd, _ = replay_fd_stage(query, estimate, remaining, selected_fd, fd)
    if trace:
        return estimate, used_mcv, used_fd
    return estimate


class JointEvaluator:
    def __init__(self, workload, allowed_mcv=None, allowed_fd=None):
        self.w = workload
        self.mcv = workload["mcv_candidates"]
        self.fd = workload["fd_candidates"]
        self.ranks = {i: c["oid_rank"] for i, c in enumerate(self.mcv)}
        self.allowed_mcv = set(range(len(self.mcv))) if allowed_mcv is None else set(allowed_mcv)
        self.allowed_fd = set(range(len(self.fd))) if allowed_fd is None else set(allowed_fd)

    def loss(self, qidx, sm, sf):
        q = self.w["queries"][qidx]
        return qerror(replay(q, sm, sf, self.mcv, self.fd, self.ranks), q["truth"])

    def state(self):
        losses = [self.loss(i, set(), set()) for i in range(len(self.w["queries"]))]
        return {"mcv": set(), "fd": set(), "losses": losses, "total": sum(losses), "used": 0}

    def state_from(self, sm, sf):
        state = {"mcv": set(sm), "fd": set(sf)}
        state["losses"] = [self.loss(i, state["mcv"], state["fd"])
                           for i in range(len(self.w["queries"]))]
        state["total"] = sum(state["losses"])
        state["used"] = (sum(self.mcv[i]["cost_bytes"] for i in state["mcv"]) +
                         sum(self.fd[i]["cost_bytes"] for i in state["fd"]))
        return state

    def delta(self, state, kind, cid, commit=False):
        sm, sf = set(state["mcv"]), set(state["fd"])
        target = sm if kind == "mcv" else sf
        if cid in target: target.remove(cid)
        else: target.add(cid)
        candidate = self.mcv[cid] if kind == "mcv" else self.fd[cid]
        changes = {}; delta = 0.0
        for qidx in candidate["query_indexes"]:
            value = self.loss(qidx, sm, sf)
            changes[qidx] = value
            delta += value-state["losses"][qidx]
        if commit:
            state["mcv"], state["fd"] = sm, sf
            state["used"] += candidate["cost_bytes"] if cid in target else -candidate["cost_bytes"]
            for qidx, value in changes.items(): state["losses"][qidx] = value
            state["total"] += delta
        return delta


def marginal_greedy(evaluator, budget, initial=None):
    state = evaluator.state() if initial is None else evaluator.state_from(initial[0], initial[1])
    iterations = 0; evaluations = 0
    started = time.perf_counter()
    while True:
        best = None
        for kind, candidates, allowed, selected in (
                ("mcv", evaluator.mcv, evaluator.allowed_mcv, state["mcv"]),
                ("fd", evaluator.fd, evaluator.allowed_fd, state["fd"])):
            for cid in allowed-selected:
                candidate = candidates[cid]
                if state["used"] + candidate["cost_bytes"] > budget: continue
                delta = evaluator.delta(state, kind, cid); evaluations += 1
                score = -delta/candidate["cost_bytes"]
                key = (score, -delta, kind == "mcv", -cid)
                if delta < -1e-12 and (best is None or key > best[0]):
                    best = (key, kind, cid, delta)
        if best is None: break
        _, kind, cid, _ = best
        evaluator.delta(state, kind, cid, commit=True); iterations += 1
    return state, {"iterations": iterations, "candidate_evaluations": evaluations,
                   "runtime_seconds": time.perf_counter()-started}


def joint_refine(workload, budget, initial, rounds=5):
    evaluator = JointEvaluator(workload)
    state = evaluator.state_from(initial[0], initial[1])
    dropped=[]; fills=[]; started=time.perf_counter()
    for _ in range(rounds):
        changed=False
        # Remove harmful or exactly redundant choices under actual composition.
        while True:
            best=None
            for kind,candidates,selected in (("mcv",evaluator.mcv,state["mcv"]),
                                               ("fd",evaluator.fd,state["fd"])):
                for cid in selected:
                    delta=evaluator.delta(state,kind,cid)
                    if delta <= 1e-12 and (best is None or delta < best[0]):
                        best=(delta,kind,cid)
            if best is None: break
            delta,kind,cid=best; evaluator.delta(state,kind,cid,commit=True)
            dropped.append({"kind":kind,"id":cid,"delta":delta}); changed=True
        before=state["total"]
        state,meta=marginal_greedy(evaluator,budget,(state["mcv"],state["fd"]))
        fills.append(meta)
        if meta["iterations"]: changed=True
        if not changed or abs(before-state["total"]) <= 1e-12: break
    return state,{"runtime_seconds":time.perf_counter()-started,"dropped":dropped,"fills":fills}


def independent_greedy(workload, budget):
    em = JointEvaluator(workload, allowed_fd=set())
    ef = JointEvaluator(workload, allowed_mcv=set())
    sm, sf = em.state(), ef.state(); used = 0; evaluations = iterations = 0
    started = time.perf_counter()
    while True:
        best = None
        for kind, ev, state, candidates, selected in (
                ("mcv", em, sm, em.mcv, sm["mcv"]),
                ("fd", ef, sf, ef.fd, sf["fd"])):
            allowed = ev.allowed_mcv if kind == "mcv" else ev.allowed_fd
            for cid in allowed-selected:
                if used+candidates[cid]["cost_bytes"] > budget: continue
                delta = ev.delta(state, kind, cid); evaluations += 1
                key = (-delta/candidates[cid]["cost_bytes"], -delta, kind == "mcv", -cid)
                if delta < -1e-12 and (best is None or key > best[0]):
                    best = (key, kind, cid, delta)
        if best is None: break
        _, kind, cid, _ = best
        ev, state = (em, sm) if kind == "mcv" else (ef, sf)
        ev.delta(state, kind, cid, commit=True)
        used += (em.mcv if kind == "mcv" else ef.fd)[cid]["cost_bytes"]
        iterations += 1
    joint = JointEvaluator(workload); state = joint.state()
    state["mcv"], state["fd"], state["used"] = set(sm["mcv"]), set(sf["fd"]), used
    state["losses"] = [joint.loss(i,state["mcv"],state["fd"])
                       for i in range(len(workload["queries"]))]
    state["total"] = sum(state["losses"])
    return state, {"iterations": iterations, "candidate_evaluations": evaluations,
                   "runtime_seconds": time.perf_counter()-started,
                   "isolated_mcv_loss": sm["total"], "isolated_fd_loss": sf["total"]}


def render(name, state, meta, workload):
    consumed_fd = set(); suppression_events = 0
    ranks = {i:c["oid_rank"] for i,c in enumerate(workload["mcv_candidates"])}
    for q in workload["queries"]:
        _, _, used_fd = replay(q,state["mcv"],state["fd"],workload["mcv_candidates"],
                               workload["fd_candidates"],ranks,trace=True)
        consumed_fd.update(used_fd)
        _, _, without_mcv = replay(q,set(),state["fd"],workload["mcv_candidates"],
                                   workload["fd_candidates"],ranks,trace=True)
        suppression_events += len(set(without_mcv)-set(used_fd))
    wasted = state["fd"]-consumed_fd
    return {"strategy": name, "loss": state["total"], "used_bytes": state["used"],
            "selected_mcv": sorted(state["mcv"]), "selected_fd": sorted(state["fd"]),
            "selected_mcv_count": len(state["mcv"]), "selected_fd_count": len(state["fd"]),
            "consumed_fd_count": len(consumed_fd), "never_consumed_fd_count": len(wasted),
            "never_consumed_fd_bytes": sum(workload["fd_candidates"][i]["cost_bytes"] for i in wasted),
            "suppression_events": suppression_events, "optimization": meta}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, required=True)
    ap.add_argument("--queries", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--host", default="/tmp"); ap.add_argument("--port", type=int, default=55432)
    ap.add_argument("--user", default="postgres"); ap.add_argument("--db", default="census")
    ap.add_argument("--target", type=int, default=100)
    args = ap.parse_args()
    source = json.loads(args.input.read_text()); base = source["workload_ir"]
    raw_queries = load_queries(args.queries)
    budget = source["scales"][-1]["budget_bytes"]
    conn = psycopg.connect(host=args.host,port=args.port,user=args.user,dbname=args.db,autocommit=True)
    cur=conn.cursor(); notices=[]; conn.add_notice_handler(lambda d:notices.append(d.message_primary))
    prefix="v4_fd_"
    def clean():
        cur.execute("SELECT stxname FROM pg_statistic_ext WHERE stxname LIKE %s",(prefix+"%",))
        for (name,) in cur.fetchall(): cur.execute(f'DROP STATISTICS IF EXISTS "{text(name)}"')
    def raw_rows(where):
        notices.clear(); cur.execute(f"EXPLAIN SELECT * FROM climate WHERE {where}")
        rows=[m for m in notices if m.startswith("CE_REPLAY_RAW_ROWS")]
        if len(rows)!=1: raise RuntimeError((where,rows))
        return float(RAW_RE.search(rows[0]).group(1))
    started=time.perf_counter()
    try:
        cur.execute("SELECT stxname FROM pg_statistic_ext WHERE stxrelid='climate'::regclass")
        existing=[text(x[0]) for x in cur.fetchall()]
        if existing: raise RuntimeError("existing climate extstats: "+", ".join(existing))
        eligible=[]; fd_incident=defaultdict(list)
        for qidx,q in enumerate(base["queries"]):
            eq={c for c,ps in q["predicates"].items() if any(op=="=" for op,_ in ps)}
            for cid in q["candidate_ids"]:
                if set(base["candidates"][cid]["columns"]) <= eq:
                    fd_incident[cid].append(qidx)
        eligible=sorted(fd_incident)
        fd=[]
        for fid,old in enumerate(eligible):
            columns=base["candidates"][old]["columns"]; name=f"{prefix}{fid:04d}"
            cur.execute(f'CREATE STATISTICS "{name}" (dependencies) ON {columns[0]},{columns[1]} FROM climate')
            cur.execute(f'ALTER STATISTICS "{name}" SET STATISTICS {args.target}')
            cur.execute("SELECT oid FROM pg_statistic_ext WHERE stxname=%s",(name,)); oid=int(cur.fetchone()[0])
            fd.append({"id":fid,"source_pair_id":old,"name":name,"oid":oid,"oid_rank":fid,
                       "columns":columns,"query_indexes":fd_incident[old]})
        cur.execute("ANALYZE climate"); analyze_done=time.perf_counter()
        cur.execute("CREATE TEMP TABLE v4_fd_backup AS SELECT stxoid,stxddependencies "
                    "FROM pg_statistic_ext_data WHERE stxoid=ANY(%s) AND NOT stxdinherit",
                    ([c["oid"] for c in fd],))
        cur.execute("SELECT attnum,attname FROM pg_attribute WHERE attrelid='climate'::regclass AND attnum>0")
        attnames={int(a):text(n).lower() for a,n in cur.fetchall()}
        for c in fd:
            cur.execute("SELECT pg_column_size(stxddependencies),"
                        "pg_dependencies_send(stxddependencies) "
                        "FROM v4_fd_backup WHERE stxoid=%s",(c["oid"],))
            size,payload=cur.fetchone()
            if size is not None:
                c["cost_bytes"]=int(size); c["payload"]=parse_binary_payload(payload,attnames)
        fd=[c for c in fd if "payload" in c]
        for fid,c in enumerate(fd): c["id"]=fid; c["oid_rank"]=fid
        old_to_fd={c["source_pair_id"]:c["id"] for c in fd}
        cur.execute("UPDATE pg_statistic_ext_data SET stxddependencies=NULL WHERE stxoid=ANY(%s)",
                    ([c["oid"] for c in fd],))
        current_relation_rows=raw_rows("TRUE")
        queries=[]
        for qidx,(q,raw) in enumerate(zip(base["queries"],raw_queries)):
            eqcols={c for c,ps in q["predicates"].items() if any(op=="=" for op,_ in ps)}
            simple={}
            for col in eqcols:
                clauses=" AND ".join(f"{col}{op}{val}" for op,val in q["predicates"][col])
                simple[col]=raw_rows(clauses)/current_relation_rows
            queries.append({"id":q["id"],"truth":q["truth"],"predicates":q["predicates"],
                            "baseline_rows":raw_rows(raw["where"]),"mcv_ids":q["candidate_ids"],
                            "mcv_ratios":q["correction_ratios"],"fd_columns":sorted(eqcols),
                            "simple_selectivities":simple,
                            "fd_ids":[old_to_fd[c] for c in q["candidate_ids"] if c in old_to_fd]})
        workload={"relation_rows":current_relation_rows,"queries":queries,
                  "mcv_candidates":base["candidates"],"fd_candidates":fd}
        specialize_done=time.perf_counter()

        # Typed cross-mechanism interaction graph (potential suppression edges).
        edges=set(); mdeg=defaultdict(set); fdeg=defaultdict(set); per_query=[]
        for qidx,q in enumerate(queries):
            local=set()
            for mid in q["mcv_ids"]:
                mc=set(base["candidates"][mid]["columns"])
                for fid in q["fd_ids"]:
                    if mc & set(fd[fid]["columns"]):
                        edge=(mid,fid); edges.add(edge); local.add(edge)
                        mdeg[mid].add(fid); fdeg[fid].add(mid)
            per_query.append(len(local))
        census={"potential_cross_edges":len(edges),"mcv_nodes":len(mdeg),"fd_nodes":len(fdeg),
                "mcv_to_fd_degree":{"mean":statistics.mean(map(len,mdeg.values())) if mdeg else 0,
                    "median":statistics.median(map(len,mdeg.values())) if mdeg else 0,
                    "max":max(map(len,mdeg.values())) if mdeg else 0},
                "fd_from_mcv_degree":{"mean":statistics.mean(map(len,fdeg.values())) if fdeg else 0,
                    "median":statistics.median(map(len,fdeg.values())) if fdeg else 0,
                    "max":max(map(len,fdeg.values())) if fdeg else 0},
                "edges_per_query":{"mean":statistics.mean(per_query),"median":statistics.median(per_query),
                    "max":max(per_query),"queries_nonzero":sum(x>0 for x in per_query)}}

        strategies=[]
        ev=JointEvaluator(workload,allowed_fd=set()); s,m=marginal_greedy(ev,budget); strategies.append(render("mcv_only",s,m,workload))
        ev=JointEvaluator(workload,allowed_mcv=set()); s,m=marginal_greedy(ev,budget); strategies.append(render("fd_only",s,m,workload))
        independent_state,m=independent_greedy(workload,budget)
        strategies.append(render("independent",independent_state,m,workload))
        ev=JointEvaluator(workload); empty_state,empty_meta=marginal_greedy(ev,budget)
        mcv_seed=next(x for x in strategies if x["strategy"]=="mcv_only")
        refined_ind,meta_ind=joint_refine(workload,budget,(independent_state["mcv"],independent_state["fd"]))
        refined_mcv,meta_mcv=joint_refine(workload,budget,(set(mcv_seed["selected_mcv"]),set()))
        options=[("empty",empty_state,empty_meta),("independent",refined_ind,meta_ind),
                 ("mcv_only",refined_mcv,meta_mcv)]
        seed,s,m=min(options,key=lambda x:x[1]["total"])
        m={"winning_seed":seed,"alternatives":{n:st["total"] for n,st,_ in options},"detail":m}
        strategies.append(render("joint_semantic",s,m,workload))

        # Native FD-only validation for the chosen FD-only design.
        fd_design=next(x for x in strategies if x["strategy"]=="fd_only")["selected_fd"]
        selected_oids=[fd[i]["oid"] for i in fd_design]
        cur.execute("UPDATE pg_statistic_ext_data d SET stxddependencies=b.stxddependencies "
                    "FROM v4_fd_backup b WHERE d.stxoid=b.stxoid AND d.stxoid=ANY(%s)",(selected_oids,))
        ranks={i:c["oid_rank"] for i,c in enumerate(base["candidates"])}; errors=[]
        for q,raw in zip(queries,raw_queries):
            predicted=replay(q,set(),set(fd_design),base["candidates"],fd,ranks)
            native=raw_rows(raw["where"]); errors.append(abs(predicted-native)/max(abs(native),1e-300))
        validation={"design":"fd_only","queries":len(errors),"matches_1e_12":sum(e<=1e-12 for e in errors),
                    "median_relative_error":statistics.median(errors),"max_relative_error":max(errors)}
        result={"experiment":"CE-Replay-Optimize-v4","source":str(args.input),"budget_bytes":budget,
                "query_count":len(queries),"mcv_candidate_count":len(base["candidates"]),
                "fd_candidate_count":len(fd),"timing":{"create_analyze_seconds":analyze_done-started,
                    "specialize_seconds":specialize_done-analyze_done,"total_seconds":time.perf_counter()-started},
                "cross_mechanism_census":census,"strategies":strategies,
                "native_validation":validation,"workload_ir":workload}
        args.output.write_text(json.dumps(result,indent=2)+"\n")
        print(json.dumps({k:result[k] for k in ("budget_bytes","query_count","mcv_candidate_count",
              "fd_candidate_count","timing","cross_mechanism_census","strategies","native_validation")},indent=2))
    finally:
        clean(); conn.close()


if __name__=="__main__": main()
