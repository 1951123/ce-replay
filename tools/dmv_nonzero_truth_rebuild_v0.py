#!/usr/bin/env python3
"""Optimize and preserve one positive-truth DMV replay realization."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
from collections import Counter
from pathlib import Path

import psycopg

import dmv_maintenance_budget_optimize_v0 as opt
from dmv_baseline_nonmonotonicity_v0 import RAW_RE, parse_queries, qerror, replay


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def detailed_terminal(ev, budget, state):
    best = {"ADD": math.inf, "DROP": math.inf, "SWAP": math.inf}
    counts = Counter()
    additions = list(opt.candidate_iter(ev, state))
    selected = ([('mcv', i) for i in sorted(state['mcv'])] +
                [('fd', i) for i in sorted(state['fd'])])
    for add in additions:
        c = 1.0 if add[0] == "mcv" else opt.FD_WEIGHT
        if state["cost"] + c <= budget + 1e-12:
            delta, _, _ = ev.move(state, add=add, count=False)
            counts["ADD"] += 1; best["ADD"] = min(best["ADD"], delta)
    for rem in selected:
        delta, _, _ = ev.move(state, remove=rem, count=False)
        counts["DROP"] += 1; best["DROP"] = min(best["DROP"], delta)
    for rem in selected:
        rc = 1.0 if rem[0] == "mcv" else opt.FD_WEIGHT
        for add in additions:
            ac = 1.0 if add[0] == "mcv" else opt.FD_WEIGHT
            if state["cost"] - rc + ac <= budget + 1e-12:
                delta, _, _ = ev.move(state, remove=rem, add=add, count=False)
                counts["SWAP"] += 1; best["SWAP"] = min(best["SWAP"], delta)
    finite = [x for x in best.values() if math.isfinite(x)]
    return {"feasible_add": counts["ADD"], "feasible_drop": counts["DROP"],
            "feasible_swap": counts["SWAP"], "total": sum(counts.values()),
            "best_add_delta": None if not math.isfinite(best["ADD"]) else best["ADD"],
            "best_drop_delta": None if not math.isfinite(best["DROP"]) else best["DROP"],
            "best_swap_delta": None if not math.isfinite(best["SWAP"]) else best["SWAP"],
            "best_overall_delta": min(finite),
            "tolerance": 1e-12, "local_optimum": min(finite) >= -1e-12}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--baseline", type=Path, required=True)
    ap.add_argument("--cost-model", type=Path, required=True)
    ap.add_argument("--queries", type=Path, default=Path("/root/projects/extended-stats-optim-v2/benchmarks/DMV/queries/dmv.sql"))
    ap.add_argument("--csv", type=Path, default=Path("/root/projects/extended-stats-optim-v2/benchmarks/DMV/data/original.csv"))
    ap.add_argument("--database", default="dmv_nonzero_baseline_v0")
    ap.add_argument("--host", default="/tmp"); ap.add_argument("--port", type=int, default=55433)
    ap.add_argument("--user", default="postgres")
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args(); started = time.perf_counter()

    baseline = json.loads(args.baseline.read_text())
    cost_model = json.loads(args.cost_model.read_text())
    opt.FD_WEIGHT = float(cost_model["normalized_maintenance_cost"]["fd_weight"])
    parsed_queries = parse_queries(args.queries)
    queries = baseline["replay_inputs"]["queries"]
    mcv = baseline["candidate_universe"]["mcv"]
    fd = [x for x in baseline["candidate_universe"]["fd"] if x["payload"]]
    for i, stat in enumerate(fd): stat["index"] = i
    if len(parsed_queries) != 1965 or [q["id"] for q in queries if q["truth"] == 0] != ["dmv.173", "dmv.943"]:
        raise RuntimeError("workload-domain mismatch")
    relation_rows = baseline["payload_acquisition"]["relation_rows"]
    cache = baseline["replay_inputs"]["simple_selectivity_cache"]

    full_cost = len(mcv) + opt.FD_WEIGHT * len(fd)
    budget = 0.5 * full_cost
    ev = opt.Evaluator(queries, mcv, fd)
    start_state = ev.state()
    greedy, trajectory, greedy_metrics = opt.marginal_greedy(ev, budget)
    greedy_snapshot = opt.render(greedy, queries, mcv, fd)
    final_state, trajectory, local_metrics = opt.local_search(ev, budget, greedy, trajectory)
    final = opt.render(final_state, queries, mcv, fd)
    audit = detailed_terminal(ev, budget, final_state)
    if not audit["local_optimum"]:
        raise RuntimeError({"terminal_local_optimum_failed": audit})

    per_query = []
    consumed_fd = set()
    for q in queries:
        estimate, mt, ft = replay(q, final_state["mcv"], final_state["fd"], mcv, fd, True)
        consumed_fd.update(x["id"] for x in ft)
        per_query.append({"query": q["id"], "where": q["where"], "truth": q["truth"],
                          "zero_truth": q["zero_truth"], "objective_member": q["objective_member"],
                          "estimate": estimate,
                          "qerror_contribution": qerror(estimate, q["truth"]),
                          "mcv_trace": mt, "fd_trace": ft})
    result = {
        "experiment": "DMV-Nonzero-Truth-Rebuild-v0",
        "realization": {"database": args.database, "relation_rows": relation_rows,
            "query_sha256": sha256(args.queries), "dataset_sha256": sha256(args.csv),
            "baseline_sha256": sha256(args.baseline), "cost_model_sha256": sha256(args.cost_model),
            "fixed_precedence": "lexicographic pair creation/OID order from frozen baseline"},
        "workload": {"total": len(queries), "positive_truth": sum(q["truth"] > 0 for q in queries),
                     "zero_truth": sum(q["truth"] == 0 for q in queries),
                     "zero_truth_ids": [q["id"] for q in queries if q["truth"] == 0]},
        "candidate_universe": {"mcv": len(mcv), "fd": len(fd), "total": len(mcv)+len(fd),
                               "mcv_candidates": mcv, "fd_candidates": fd},
        "maintenance": {"mcv_weight": 1.0, "fd_weight": opt.FD_WEIGHT,
                        "budget_rule": "50% of complete usable candidate-universe cost",
                        "full_cost": full_cost, "budget": budget},
        "replay_inputs": {"queries": queries, "simple_selectivity_cache": cache},
        "optimization": {"starting_design": {"mcv": [], "fd": []},
                         "starting_objective": start_state["total"],
                         "greedy_terminal": greedy_snapshot,
                         "final": final,
                         "selected_indexes": {"mcv": sorted(final_state["mcv"]), "fd": sorted(final_state["fd"])},
                         "trajectory": trajectory,
                         "accepted_moves": len(trajectory),
                         "runtime": {"greedy": greedy_metrics, "local": local_metrics,
                                     "total_seconds": time.perf_counter()-started},
                         "evaluation_metrics": dict(ev.metrics), "terminal_audit": audit,
                         "selected_fd_consumed": sorted(consumed_fd),
                         "all_selected_fd_consumed": set(final["selected_fd_ids"]) <= consumed_fd},
        "frozen_per_query": per_query,
        "gate": "READY FOR PHYSICAL DEPLOYMENT"
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"gate": result["gate"], "budget": budget, "greedy": greedy_snapshot,
                      "final": final, "terminal": audit}, default=str), flush=True)


if __name__ == "__main__": main()
