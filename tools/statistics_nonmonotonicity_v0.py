#!/usr/bin/env python3
"""Audit statistics-set non-monotonicity in the frozen Census MCV+FD model."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import sys
import types
from pathlib import Path

try:
    import psycopg  # noqa: F401
except ModuleNotFoundError:
    sys.modules["psycopg"] = types.ModuleType("psycopg")

from ce_replay_optimize_v4 import JointEvaluator, replay


EPS = 1e-12


def summarize(evaluator, sm, sf):
    state = evaluator.state_from(sm, sf)
    losses = state["losses"]
    return state, {
        "mcv_count": len(sm),
        "fd_count": len(sf),
        "total_candidate_count": len(sm) + len(sf),
        "workload_aggregate_qerror": state["total"],
        "mean_per_query_qerror": statistics.mean(losses),
        "median_per_query_qerror": statistics.median(losses),
    }


def candidate_ref(kind, cid, evaluator):
    c = evaluator.mcv[cid] if kind == "mcv" else evaluator.fd[cid]
    return {
        "candidate_id": cid,
        "candidate_name": c["name"],
        "mechanism": kind.upper(),
        "columns": c["columns"],
        "cost_bytes": c["cost_bytes"],
        "structurally_affected_queries": [q + 1 for q in c["query_indexes"]],
    }


def addition_rows(evaluator, state, budget, enforce_budget):
    rows = []
    for kind, candidates, selected in (
        ("mcv", evaluator.mcv, state["mcv"]),
        ("fd", evaluator.fd, state["fd"]),
    ):
        for cid, candidate in enumerate(candidates):
            if cid in selected:
                continue
            if enforce_budget and state["used"] + candidate["cost_bytes"] > budget:
                continue
            delta = evaluator.delta(state, kind, cid)
            row = candidate_ref(kind, cid, evaluator)
            row.update({
                "loss_before": state["total"],
                "loss_after": state["total"] + delta,
                "absolute_change": delta,
                "relative_change": delta / state["total"],
            })
            rows.append(row)
    return rows


def classify(rows):
    return {
        "tested": len(rows),
        "improve": sum(r["absolute_change"] < -EPS for r in rows),
        "unchanged": sum(abs(r["absolute_change"]) <= EPS for r in rows),
        "worsen": sum(r["absolute_change"] > EPS for r in rows),
    }


def explain_addition(evaluator, state, row):
    kind = row["mechanism"].lower()
    cid = row["candidate_id"]
    sm0, sf0 = set(state["mcv"]), set(state["fd"])
    sm1, sf1 = set(sm0), set(sf0)
    (sm1 if kind == "mcv" else sf1).add(cid)
    per_query = []
    for qi in (evaluator.mcv[cid] if kind == "mcv" else evaluator.fd[cid])["query_indexes"]:
        q = evaluator.w["queries"][qi]
        before_rows, before_mcv, before_fd = replay(
            q, sm0, sf0, evaluator.mcv, evaluator.fd, evaluator.ranks, trace=True)
        after_rows, after_mcv, after_fd = replay(
            q, sm1, sf1, evaluator.mcv, evaluator.fd, evaluator.ranks, trace=True)
        before_loss, after_loss = state["losses"][qi], evaluator.loss(qi, sm1, sf1)
        if abs(after_loss - before_loss) <= EPS and before_mcv == after_mcv and before_fd == after_fd:
            continue
        per_query.append({
            "query": qi + 1,
            "truth": q["truth"],
            "rows_before": before_rows,
            "rows_after": after_rows,
            "qerror_before": before_loss,
            "qerror_after": after_loss,
            "qerror_change": after_loss - before_loss,
            "mcv_trace_before": before_mcv,
            "mcv_trace_after": after_mcv,
            "fd_trace_before": before_fd,
            "fd_trace_after": after_fd,
        })
    per_query.sort(key=lambda x: x["qerror_change"], reverse=True)
    changed_mcv = any(x["mcv_trace_before"] != x["mcv_trace_after"] for x in per_query)
    changed_fd = any(x["fd_trace_before"] != x["fd_trace_after"] for x in per_query)
    if kind == "mcv" and changed_mcv and changed_fd:
        cause = "MCV-to-FD suppression/composition"
    elif changed_mcv:
        cause = "MCV winner/GreedyCover change"
    elif changed_fd:
        cause = "FD consumption change"
    else:
        cause = "numerical estimate change without control change"
    return {
        "classification": cause,
        "causal_chain": "add statistic -> consumption/control or numerical response changes -> estimated rows change -> aggregate q-error increases",
        "changed_query_count": len(per_query),
        "top_query_traces": per_query[:5],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workload", type=Path,
                        default=Path("results/census_ce_replay_optimize_v4.json"))
    parser.add_argument("--design", type=Path,
                        default=Path("results/census_mixed_deploy_v0_design.json"))
    parser.add_argument("--output", type=Path,
                        default=Path("results/census_statistics_nonmonotonicity_v0.json"))
    parser.add_argument("--report", type=Path,
                        default=Path("results/census_statistics_nonmonotonicity_v0.md"))
    args = parser.parse_args()

    workload_raw = args.workload.read_bytes()
    design_raw = args.design.read_bytes()
    source = json.loads(workload_raw)
    design = json.loads(design_raw)
    evaluator = JointEvaluator(source["workload_ir"])
    budget = source["budget_bytes"]

    empty_mcv, empty_fd = set(), set()
    opt_mcv, opt_fd = set(design["selected_mcv"]), set(design["selected_fd"])
    all_mcv, all_fd = set(range(len(evaluator.mcv))), set(range(len(evaluator.fd)))

    empty_state, empty_summary = summarize(evaluator, empty_mcv, empty_fd)
    opt_state, opt_summary = summarize(evaluator, opt_mcv, opt_fd)
    all_state, all_summary = summarize(evaluator, all_mcv, all_fd)

    empty_additions = addition_rows(evaluator, empty_state, budget, True)
    optimized_additions = addition_rows(evaluator, opt_state, budget, True)
    all_additions = empty_additions + optimized_additions
    harmful = [r for r in all_additions if r["absolute_change"] > EPS]
    worst = max(harmful, key=lambda r: r["absolute_change"]) if harmful else None
    if worst is not None:
        source_state = empty_state if worst["loss_before"] == empty_state["total"] else opt_state
        worst = dict(worst)
        worst["source_design"] = "empty" if source_state is empty_state else "optimized"
        worst["semantic_explanation"] = explain_addition(evaluator, source_state, worst)

    removals = []
    for kind, candidates in (("mcv", evaluator.mcv), ("fd", evaluator.fd)):
        for cid in range(len(candidates)):
            delta = evaluator.delta(all_state, kind, cid)
            row = candidate_ref(kind, cid, evaluator)
            row.update({
                "loss_before": all_state["total"],
                "loss_after": all_state["total"] + delta,
                "absolute_change": delta,
                "relative_change": delta / all_state["total"],
            })
            removals.append(row)
    best_removal = min(removals, key=lambda r: r["absolute_change"])

    all_vs_opt = {
        "absolute_difference": all_state["total"] - opt_state["total"],
        "relative_difference": all_state["total"] / opt_state["total"] - 1,
        "all_is_worse": all_state["total"] > opt_state["total"] + EPS,
        "optimized_is_strict_subset": (opt_mcv < all_mcv and opt_fd < all_fd),
    }
    result = {
        "experiment": "Statistics-Nonmonotonicity-v0",
        "scope": {
            "dbms": "PostgreSQL 16.14",
            "workload": "Census fixed workload (468 queries)",
            "semantics": "frozen-payload base-restriction MCV+FD replay",
            "precedence": "fixed precedence used by the mixed optimizer",
            "budget_bytes": budget,
            "resource_proxy": "serialized statistics payload size; not a complete maintenance-cost model",
        },
        "fingerprint": {
            "workload_sha256": hashlib.sha256(workload_raw).hexdigest(),
            "design_sha256": hashlib.sha256(design_raw).hexdigest(),
        },
        "designs": {"empty": empty_summary, "optimized": opt_summary, "all": all_summary},
        "all_vs_optimized": all_vs_opt,
        "additions": {
            "empty": classify(empty_additions),
            "optimized_budget_feasible": classify(optimized_additions),
            "combined": classify(all_additions),
            "worst_harmful": worst,
        },
        "removal_from_all": {
            "tested": len(removals),
            "improving": sum(r["absolute_change"] < -EPS for r in removals),
            "best": best_removal,
        },
        "verdict": {
            "empirically_nonmonotone": bool(harmful),
            "selection_meaningful_without_budget": all_vs_opt["all_is_worse"],
        },
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n")

    e, o, a = empty_summary, opt_summary, all_summary
    wa = worst
    br = best_removal
    ex = wa["semantic_explanation"] if wa else None
    trace = ex["top_query_traces"][0] if ex and ex["top_query_traces"] else None
    md = f"""# Statistics-Nonmonotonicity-v0

## Scope

PostgreSQL 16.14, current Census workload, frozen MCV+FD payloads, and the fixed precedence used by the mixed optimizer. No PostgreSQL execution, new optimization, repeated `ANALYZE`, or train/test split is involved.

## Three fixed designs

| Design | MCV | FD | Total | Aggregate q-error | Mean q-error | Median q-error |
|---|---:|---:|---:|---:|---:|---:|
| Empty | {e['mcv_count']} | {e['fd_count']} | {e['total_candidate_count']} | {e['workload_aggregate_qerror']:.12f} | {e['mean_per_query_qerror']:.12f} | {e['median_per_query_qerror']:.12f} |
| Existing optimized mixed | {o['mcv_count']} | {o['fd_count']} | {o['total_candidate_count']} | {o['workload_aggregate_qerror']:.12f} | {o['mean_per_query_qerror']:.12f} | {o['median_per_query_qerror']:.12f} |
| All candidates | {a['mcv_count']} | {a['fd_count']} | {a['total_candidate_count']} | {a['workload_aggregate_qerror']:.12f} | {a['mean_per_query_qerror']:.12f} | {a['median_per_query_qerror']:.12f} |

All candidates are **{'worse' if all_vs_opt['all_is_worse'] else 'not worse'}** than the optimized strict subset by {all_vs_opt['absolute_difference']:.12f} aggregate q-error ({all_vs_opt['relative_difference']:.6%}). The all-candidate design is evaluated as a semantic comparison and is not required to satisfy the experiment's resource budget.

## Single-statistic additions

| Source design | Feasible tested | Improve | Unchanged | Worsen |
|---|---:|---:|---:|---:|
| Empty | {classify(empty_additions)['tested']} | {classify(empty_additions)['improve']} | {classify(empty_additions)['unchanged']} | {classify(empty_additions)['worsen']} |
| Existing optimized mixed | {classify(optimized_additions)['tested']} | {classify(optimized_additions)['improve']} | {classify(optimized_additions)['unchanged']} | {classify(optimized_additions)['worsen']} |
| Combined | {classify(all_additions)['tested']} | {classify(all_additions)['improve']} | {classify(all_additions)['unchanged']} | {classify(all_additions)['worsen']} |

The strongest harmful addition is `{wa['mechanism']}:{wa['candidate_id']}` (`{wa['candidate_name']}`) from the {wa['source_design']} design. Loss changes from {wa['loss_before']:.12f} to {wa['loss_after']:.12f}: +{wa['absolute_change']:.12f} ({wa['relative_change']:.6%}). Its structurally affected queries are {wa['structurally_affected_queries']}.

## Semantic explanation

Classification: **{ex['classification']}**.

The causal chain is: add `{wa['mechanism']}:{wa['candidate_id']}` → native-supported replay control/response changes → estimated rows change → aggregate q-error increases.

The clearest affected query is query {trace['query']}: rows {trace['rows_before']:.12g} → {trace['rows_after']:.12g}, truth {trace['truth']}, and q-error {trace['qerror_before']:.12f} → {trace['qerror_after']:.12f}. Its MCV trace changes from `{trace['mcv_trace_before']}` to `{trace['mcv_trace_after']}` and its FD trace from `{trace['fd_trace_before']}` to `{trace['fd_trace_after']}`. Only the top five changed query traces are retained in the JSON artifact.

## Removal from all statistics

All {len(removals)} single removals were tested. {sum(r['absolute_change'] < -EPS for r in removals)} improve the objective. The best removes `{br['mechanism']}:{br['candidate_id']}` (`{br['candidate_name']}`), changing loss from {br['loss_before']:.12f} to {br['loss_after']:.12f} ({br['absolute_change']:.12f}, {br['relative_change']:.6%}).

## Interpretation

Within the tested setting, set inclusion is empirically non-monotone: at least one tested `Y, s` has `L(Y union {{s}}) > L(Y)`, and the all-statistics design is worse than an optimized strict subset. Statistics selection therefore remains semantically meaningful even without a storage budget. The budget adds a separate resource tradeoff; serialized payload size is only a controlled additive proxy, not a complete PostgreSQL collection or maintenance-cost model.

This does not claim that extended statistics are universally harmful or that PostgreSQL always becomes worse when more statistics are installed.

## Required verdict

1. **What is the workload loss with no extended statistics?** {e['workload_aggregate_qerror']:.12f}.
2. **What is the workload loss of the existing optimized mixed design?** {o['workload_aggregate_qerror']:.12f}.
3. **What is the workload loss with all MCV+FD candidates?** {a['workload_aggregate_qerror']:.12f}.
4. **Is the all-statistics design worse than the optimized strict subset?** {'Yes' if all_vs_opt['all_is_worse'] else 'No'}; the absolute/relative difference is {all_vs_opt['absolute_difference']:.12f} / {all_vs_opt['relative_difference']:.6%}.
5. **How many tested single-statistic additions worsen the workload objective?** {classify(all_additions)['worsen']} of {classify(all_additions)['tested']} budget-feasible additions.
6. **What is the strongest harmful-addition example?** Add `{wa['mechanism']}:{wa['candidate_id']}` to the {wa['source_design']} design: {wa['loss_before']:.12f} → {wa['loss_after']:.12f}, +{wa['absolute_change']:.12f} ({wa['relative_change']:.6%}).
7. **What native CE semantic mechanism causes that example?** {ex['classification']}.
8. **Does removing any statistic from the all-statistics design improve the objective?** {'Yes' if br['absolute_change'] < -EPS else 'No'}; best removal `{br['mechanism']}:{br['candidate_id']}` changes loss by {br['absolute_change']:.12f}.
9. **Does the evidence establish empirical non-monotonicity of the fixed-workload objective?** {'Yes' if harmful else 'No'}, within the stated frozen Census/PostgreSQL semantic boundary.
10. **Does statistics selection remain meaningful even without a storage/resource budget?** {'Yes' if all_vs_opt['all_is_worse'] else 'Not established'}: the all-statistics design is worse than a strict subset, independently of budget feasibility.
"""
    args.report.write_text(md)


if __name__ == "__main__":
    main()
