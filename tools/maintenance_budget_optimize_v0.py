#!/usr/bin/env python3
"""Re-run the frozen mixed optimizer with mechanism-weighted maintenance cost."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from ce_replay_optimize_v4 import (
    JointEvaluator,
    independent_greedy,
    joint_refine,
    marginal_greedy,
    render,
    replay,
)
from mixed_deploy_v0 import final_design


MCV_COST = 1.0
FD_COST = 1.449
EPS = 1e-12


def typed(sm, sf):
    return {*(('mcv', i) for i in sm), *(('fd', i) for i in sf)}


def maintenance_cost(sm, sf):
    return MCV_COST * len(sm) + FD_COST * len(sf)


def construct_seed(workload, budget):
    """The unchanged Optimize-v4 four-strategy construction."""
    strategies = []
    ev = JointEvaluator(workload, allowed_fd=set())
    state, meta = marginal_greedy(ev, budget)
    strategies.append(render("mcv_only", state, meta, workload))

    ev = JointEvaluator(workload, allowed_mcv=set())
    state, meta = marginal_greedy(ev, budget)
    strategies.append(render("fd_only", state, meta, workload))

    independent_state, meta = independent_greedy(workload, budget)
    strategies.append(render("independent", independent_state, meta, workload))

    ev = JointEvaluator(workload)
    empty_state, empty_meta = marginal_greedy(ev, budget)
    mcv_seed = next(x for x in strategies if x["strategy"] == "mcv_only")
    refined_ind, meta_ind = joint_refine(
        workload, budget, (independent_state["mcv"], independent_state["fd"]))
    refined_mcv, meta_mcv = joint_refine(
        workload, budget, (set(mcv_seed["selected_mcv"]), set()))
    options = [
        ("empty", empty_state, empty_meta),
        ("independent", refined_ind, meta_ind),
        ("mcv_only", refined_mcv, meta_mcv),
    ]
    seed_name, state, meta = min(options, key=lambda x: x[1]["total"])
    meta = {
        "winning_seed": seed_name,
        "alternatives": {name: candidate["total"] for name, candidate, _ in options},
        "detail": meta,
    }
    strategies.append(render("joint_semantic", state, meta, workload))
    return strategies


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--v4", type=Path,
                    default=Path("results/census_ce_replay_optimize_v4.json"))
    ap.add_argument("--old-design", type=Path,
                    default=Path("results/census_mixed_deploy_v0_design.json"))
    ap.add_argument("--output", type=Path,
                    default=Path("results/census_maintenance_budget_optimize_v0.json"))
    ap.add_argument("--report", type=Path,
                    default=Path("results/census_maintenance_budget_optimize_v0.md"))
    args = ap.parse_args()

    started = time.perf_counter()
    v4_raw = args.v4.read_bytes()
    old_raw = args.old_design.read_bytes()
    source = json.loads(v4_raw)
    old = json.loads(old_raw)
    workload = copy.deepcopy(source["workload_ir"])
    for candidate in workload["mcv_candidates"]:
        candidate["cost_bytes"] = MCV_COST
    for candidate in workload["fd_candidates"]:
        candidate["cost_bytes"] = FD_COST

    old_sm = set(old["selected_mcv"])
    old_sf = set(old["selected_fd"])
    budget = maintenance_cost(old_sm, old_sf)
    if len(old_sm) != 205 or len(old_sf) != 56:
        raise RuntimeError("old final design is not the expected 205 MCV + 56 FD design")

    t0 = time.perf_counter()
    strategies = construct_seed(workload, budget)
    construction_seconds = time.perf_counter() - t0
    adapted = {
        "experiment": "Maintenance-Budget-Optimize-v0-adapted-input",
        "budget_bytes": budget,
        "strategies": strategies,
        "workload_ir": workload,
    }

    # Invoke the existing compositional optimizer unchanged. Only its input
    # candidate costs and budget differ from the byte-budget experiment.
    with tempfile.TemporaryDirectory(prefix="maintenance_budget_v0_") as tmp:
        root = Path(tmp)
        input_path = root / "input.json"
        opt_path = root / "optimizer.json"
        report_path = root / "optimizer.md"
        rounds_path = root / "rounds.csv"
        input_path.write_text(json.dumps(adapted))
        command = [
            sys.executable, str(Path(__file__).with_name("compositional_semantic_optimizer_v0.py")),
            str(input_path), "--output", str(opt_path), "--report", str(report_path),
            "--rounds", str(rounds_path),
        ]
        t0 = time.perf_counter()
        completed = subprocess.run(command, check=True, text=True, capture_output=True)
        local_seconds = time.perf_counter() - t0
        optimization = json.loads(opt_path.read_text())

    new_sm, new_sf, _ = final_design(optimization, adapted)
    evaluator = JointEvaluator(workload)
    new_state = evaluator.state_from(new_sm, new_sf)
    old_state = evaluator.state_from(old_sm, old_sf)
    if abs(new_state["total"] - optimization["optimization"]["final_loss"]) > 1e-9:
        raise RuntimeError("final design reconstruction does not match optimizer loss")

    ranks = {i: c["oid_rank"] for i, c in enumerate(workload["mcv_candidates"])}
    consumed_fd = set()
    for query in workload["queries"]:
        _, _, used_fd = replay(query, new_sm, new_sf,
                               workload["mcv_candidates"], workload["fd_candidates"],
                               ranks, trace=True)
        consumed_fd.update(used_fd)

    old_typed = typed(old_sm, old_sf)
    new_typed = typed(new_sm, new_sf)
    added = new_typed - old_typed
    removed = old_typed - new_typed
    union = old_typed | new_typed
    intersection = old_typed & new_typed
    final_round = optimization["rounds"][-1]
    local_optimal = (
        final_round["delta"] >= -EPS
        and optimization["correctness"]["trajectory_identical"]
        and optimization["correctness"]["final_design_identical"]
        and optimization["correctness"]["final_loss_identical"]
    )
    new_cost = maintenance_cost(new_sm, new_sf)
    result = {
        "experiment": "Maintenance-Budget-Optimize-v0",
        "scope": {
            "workload": "Census fixed workload (468 queries)",
            "frozen_payload": True,
            "fixed_precedence": True,
            "candidate_universe": {
                "mcv": len(workload["mcv_candidates"]),
                "fd": len(workload["fd_candidates"]),
            },
            "semantics_changed": False,
            "search_algorithm_changed": False,
            "analyze_run": False,
        },
        "fingerprint": {
            "v4_sha256": hashlib.sha256(v4_raw).hexdigest(),
            "old_design_sha256": hashlib.sha256(old_raw).hexdigest(),
        },
        "cost_model": {
            "normalized_mcv_cost": MCV_COST,
            "normalized_fd_cost": FD_COST,
            "physical_mcv_ms_per_analyze": 1.875,
            "physical_fd_ms_per_analyze": 2.717,
            "environment_specific": True,
            "budget": budget,
        },
        "old_design_under_maintenance_model": {
            "loss": old_state["total"],
            "selected_mcv": len(old_sm), "selected_fd": len(old_sf),
            "selected_total": len(old_typed), "maintenance_cost": budget,
            "feasible": maintenance_cost(old_sm, old_sf) <= budget + EPS,
        },
        "new_design": {
            "loss": new_state["total"],
            "selected_mcv": len(new_sm), "selected_fd": len(new_sf),
            "selected_total": len(new_typed), "maintenance_cost": new_cost,
            "budget_slack": budget - new_cost,
            "selected_mcv_ids": sorted(new_sm), "selected_fd_ids": sorted(new_sf),
            "consumed_fd": len(consumed_fd),
            "never_consumed_fd": sorted(new_sf - consumed_fd),
            "all_selected_fd_consumed": new_sf <= consumed_fd,
        },
        "comparison": {
            "loss_change_new_minus_old": new_state["total"] - old_state["total"],
            "loss_relative_change": new_state["total"] / old_state["total"] - 1,
            "design_jaccard": len(intersection) / len(union),
            "intersection": len(intersection), "union": len(union),
            "added_count": len(added), "removed_count": len(removed),
            "added": [{"mechanism": kind, "id": cid}
                      for kind, cid in sorted(added)],
            "removed": [{"mechanism": kind, "id": cid}
                        for kind, cid in sorted(removed)],
            "mcv_count_change": len(new_sm) - len(old_sm),
            "fd_count_change": len(new_sf) - len(old_sf),
        },
        "optimizer": {
            "pipeline": "unchanged Optimize-v4 construction followed by unchanged Compositional-Semantic-Optimizer-v0",
            "construction_seconds": construction_seconds,
            "local_optimization_seconds": local_seconds,
            "total_experiment_seconds": time.perf_counter() - started,
            "seed_strategies": [{k: s[k] for k in (
                "strategy", "loss", "used_bytes", "selected_mcv_count",
                "selected_fd_count", "consumed_fd_count", "never_consumed_fd_count")}
                for s in strategies],
            "rounds_including_terminal": optimization["optimization"]["rounds"],
            "accepted_moves": optimization["optimization"]["accepted"],
            "final_neighborhood_size": final_round["feasible"],
            "terminal_best_delta": final_round["delta"],
            "local_optimal_add_drop_swap": local_optimal,
            "correctness": optimization["correctness"],
            "rounds": optimization["rounds"],
        },
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n")

    nd = result["new_design"]
    cmp = result["comparison"]
    opt = result["optimizer"]
    material_design = cmp["design_jaccard"] < 0.8 or (
        cmp["added_count"] + cmp["removed_count"] >= 0.2 * len(old_typed))
    material_loss = abs(cmp["loss_relative_change"]) >= 0.01
    md = rf"""# Maintenance-Budget-Optimize-v0

## Scope

The frozen 468-query Census MCV+FD evaluator, candidate universe, payloads, q-error objective, fixed precedence, deterministic construction, and exhaustive best-improvement ADD/DROP/SWAP search are unchanged. Only candidate resource costs and budget feasibility use the empirical maintenance model. PostgreSQL and `ANALYZE` were not invoked.

## Maintenance model and budget

\[
C(Y)=|Y_{{MCV}}|+1.449|Y_{{FD}}|,
\qquad B_0=205+1.449(56)=\mathbf{{{budget:.3f}}}.
\]

One MCV unit corresponds to approximately 1.875 ms/ANALYZE; one FD object to approximately 2.717 ms/ANALYZE in the measured environment. These are average, environment-specific coefficients.

## Result at B0

| Metric | Old byte-budget final design | Maintenance-budget design |
|---|---:|---:|
| Workload loss | {old_state['total']:.12f} | {new_state['total']:.12f} |
| MCV objects | {len(old_sm)} | {len(new_sm)} |
| FD objects | {len(old_sf)} | {len(new_sf)} |
| Total objects | {len(old_typed)} | {len(new_typed)} |
| Maintenance cost | {budget:.3f} | {new_cost:.3f} |
| Selected FD consumed | — | {len(consumed_fd)}/{len(new_sf)} |

Typed-candidate Jaccard similarity is **{cmp['design_jaccard']:.4%}** ({cmp['intersection']} intersection / {cmp['union']} union). The new design adds {cmp['added_count']} and removes {cmp['removed_count']} candidates relative to the old design. Loss changes by {cmp['loss_change_new_minus_old']:.12f} ({cmp['loss_relative_change']:.4%}).

## Optimizer audit

The unchanged v4 construction took {construction_seconds:.3f}s; the unchanged compositional local optimizer took {local_seconds:.3f}s; total experiment time was {result['optimizer']['total_experiment_seconds']:.3f}s. It accepted {opt['accepted_moves']} moves and then audited {opt['final_neighborhood_size']:,} feasible terminal ADD/DROP/SWAP moves. Terminal best delta is {opt['terminal_best_delta']:.12g}; local optimality under this neighborhood is **{'yes' if local_optimal else 'no'}**. This is not a global-optimality claim.

All {len(new_sf)} selected FDs are {'consumed by at least one query' if nd['all_selected_fd_consumed'] else 'not consumed; see JSON for IDs'}.

## Interpretation

This is a resource-model alignment experiment, not a new optimization algorithm. Under explicit practical thresholds (Jaccard below 0.8 or symmetric change at least 20% of the old design), the selected design changes **{'materially' if material_design else 'modestly'}**. Under a 1% relative-loss threshold, workload loss changes **{'materially' if material_loss else 'modestly'}**. The coefficients are not universal PostgreSQL costs and do not estimate individual-candidate maintenance latency.

## Required verdict

1. **What maintenance budget corresponds to the old final mixed design?** \(B_0={budget:.3f}\) normalized MCV units.
2. **Under that budget, what design does the optimizer select?** A fixed-precedence design with {len(new_sm)} MCV and {len(new_sf)} FD objects; complete IDs are in the JSON artifact.
3. **What is its workload loss?** {new_state['total']:.12f}.
4. **How many MCV and FD objects are selected?** {len(new_sm)} MCV and {len(new_sf)} FD ({len(new_typed)} total).
5. **How different is it from the previous byte-budget design?** Jaccard {cmp['design_jaccard']:.4%}; {cmp['added_count']} added and {cmp['removed_count']} removed; MCV/FD count changes {cmp['mcv_count_change']:+d}/{cmp['fd_count_change']:+d}.
6. **Does changing the resource model materially change the selected design?** {'Yes' if material_design else 'No'} under the stated design-change threshold.
7. **Does changing the resource model materially change workload loss?** {'Yes' if material_loss else 'No'} under a 1% relative threshold; change is {cmp['loss_change_new_minus_old']:.12f} ({cmp['loss_relative_change']:.4%}).
8. **Are selected FD objects actually consumed?** {'Yes' if nd['all_selected_fd_consumed'] else 'No'}; {len(consumed_fd)}/{len(new_sf)} are consumed.
9. **Is the resulting design locally optimal under the current ADD/DROP/SWAP neighborhood?** {'Yes' if local_optimal else 'No'}; all {opt['final_neighborhood_size']:,} feasible terminal moves were audited and best delta is {opt['terminal_best_delta']:.12g}.
10. **Does the experiment support replacing payload-byte budget with mechanism-weighted maintenance budget in the core formulation?** Yes as an environment-specific first-order recurring-maintenance constraint: it is reproducible, keeps semantics/search unchanged, and directly represents the measured resource. It does not establish universal coefficients or per-candidate cost accuracy.
"""
    args.report.write_text(md)
    print(json.dumps({
        "budget": budget, "old": result["old_design_under_maintenance_model"],
        "new": {k: nd[k] for k in (
            "loss", "selected_mcv", "selected_fd", "maintenance_cost",
            "consumed_fd", "all_selected_fd_consumed")},
        "comparison": {k: cmp[k] for k in (
            "loss_change_new_minus_old", "loss_relative_change", "design_jaccard",
            "added_count", "removed_count", "mcv_count_change", "fd_count_change")},
        "optimizer": {k: opt[k] for k in (
            "construction_seconds", "local_optimization_seconds", "accepted_moves",
            "final_neighborhood_size", "terminal_best_delta", "local_optimal_add_drop_swap")},
        "subprocess_stdout": completed.stdout[-1000:],
    }, indent=2))


if __name__ == "__main__":
    main()
