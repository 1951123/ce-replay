#!/usr/bin/env python3
"""Exact five-candidate optimization over a frozen CE-Replay-IR-v1 result."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def qerror(estimate: float, truth: float) -> float:
    return max(estimate / truth, truth / estimate)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--truth", type=float, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    experiment = json.loads(args.input.read_text())
    costs = {candidate["id"]: candidate["storage_cost_bytes"]
             for candidate in experiment["ir"]["candidates"]}
    designs = []
    for row in experiment["validations"]:
        selected = tuple(row["selected"])
        cost = sum(costs[candidate] for candidate in selected)
        designs.append({
            "selected": list(selected),
            "cost_bytes": cost,
            "predicted_rows": row["replayed_estimate"],
            "native_pg_rows": row["fresh_pg_estimate"],
            "predicted_qerror": qerror(row["replayed_estimate"], args.truth),
            "native_pg_qerror": qerror(row["fresh_pg_estimate"], args.truth),
        })

    budgets = sorted({0, *(design["cost_bytes"] for design in designs)})
    solutions = []
    for budget in budgets:
        feasible = [design for design in designs if design["cost_bytes"] <= budget]
        predicted_best = min(feasible, key=lambda design: (
            design["predicted_qerror"], design["cost_bytes"], design["selected"]))
        native_best = min(feasible, key=lambda design: (
            design["native_pg_qerror"], design["cost_bytes"], design["selected"]))
        solutions.append({
            "budget_bytes": budget,
            "selected": predicted_best["selected"],
            "used_bytes": predicted_best["cost_bytes"],
            "predicted_rows": predicted_best["predicted_rows"],
            "deployed_native_pg_rows": predicted_best["native_pg_rows"],
            "predicted_qerror": predicted_best["predicted_qerror"],
            "deployed_native_pg_qerror": predicted_best["native_pg_qerror"],
            "same_design_as_native_exact_optimum": (
                predicted_best["selected"] == native_best["selected"]),
            "native_exact_optimum": native_best["selected"],
        })

    # Compress budgets into the points at which the chosen design changes.
    frontier = []
    for solution in solutions:
        if not frontier or solution["selected"] != frontier[-1]["selected"]:
            frontier.append(solution)

    result = {
        "experiment": "CE-Replay-Optimize-v0",
        "source_ir": str(args.input),
        "truth_rows": args.truth,
        "cost_unit": "pg_column_size(stxdmcv) bytes",
        "candidate_costs": costs,
        "designs_enumerated": len(designs),
        "budget_thresholds_checked": len(budgets),
        "all_optimizer_choices_match_native_exact_optimum": all(
            solution["same_design_as_native_exact_optimum"] for solution in solutions),
        "max_selected_prediction_relative_error": max(
            abs(solution["predicted_rows"] - solution["deployed_native_pg_rows"])
            / solution["deployed_native_pg_rows"] for solution in solutions),
        "optimal_frontier": frontier,
        "all_budget_solutions": solutions,
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: result[key] for key in (
        "candidate_costs", "designs_enumerated", "budget_thresholds_checked",
        "all_optimizer_choices_match_native_exact_optimum",
        "max_selected_prediction_relative_error", "optimal_frontier")}, indent=2))


if __name__ == "__main__":
    main()
