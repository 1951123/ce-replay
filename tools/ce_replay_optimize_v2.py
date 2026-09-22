#!/usr/bin/env python3
"""Interaction-aware move and reachable-order analysis over a workload IR."""

from __future__ import annotations

import argparse
import copy
import itertools
import json
import statistics
import time
from collections import defaultdict, deque
from pathlib import Path

from ce_replay_optimize_v1 import Evaluator, replay_query


def interaction_graph(workload):
    neighbors = [set() for _ in workload["candidates"]]
    dependency = [set() for _ in workload["candidates"]]
    for query in workload["queries"]:
        ids = query["candidate_ids"]
        for left, right in itertools.combinations(ids, 2):
            dependency[left].add(right); dependency[right].add(left)
            if set(workload["candidates"][left]["columns"]) & \
                    set(workload["candidates"][right]["columns"]):
                neighbors[left].add(right); neighbors[right].add(left)
    two_hop = []
    for cid, direct in enumerate(neighbors):
        reach = set(direct)
        for other in direct: reach.update(neighbors[other])
        reach.discard(cid)
        two_hop.append(reach)
    return neighbors, two_hop, dependency


def delta_swap(evaluator, state, removed, added):
    return evaluator.delta_swap(state, removed, added)


def enumerate_swaps(evaluator, state, budget, incoming_by_removed=None):
    used = sum(evaluator.candidates[cid]["cost_bytes"] for cid in state["selected"])
    rows = []
    unselected = set(range(len(evaluator.candidates))) - state["selected"]
    for removed in state["selected"]:
        incoming = unselected if incoming_by_removed is None else incoming_by_removed(removed, unselected)
        for added in incoming:
            new_cost = used - evaluator.candidates[removed]["cost_bytes"] + \
                       evaluator.candidates[added]["cost_bytes"]
            if new_cost > budget: continue
            rows.append((delta_swap(evaluator, state, removed, added), removed, added))
    return rows


def restricted_search(evaluator, initial, budget, incoming_factory, max_rounds=100):
    state = evaluator.state(initial); history = []; total_moves = 0
    started = time.perf_counter()
    for _ in range(max_rounds):
        moves = enumerate_swaps(evaluator, state, budget, incoming_factory)
        total_moves += len(moves)
        improving = [move for move in moves if move[0] < -1e-12]
        if not improving: break
        delta, removed, added = min(improving)
        evaluator.delta_swap(state, removed, added, commit=True)
        history.append({"removed": removed, "added": added, "delta": delta,
                        "loss": state["total"]})
    return {"loss": state["total"], "selected": sorted(state["selected"]),
            "runtime_seconds": time.perf_counter()-started,
            "moves_enumerated": total_moves, "accepted_moves": history}


def connected_components(edges, nodes):
    unseen = set(nodes); sizes = []
    while unseen:
        start = unseen.pop(); size = 1; queue = [start]
        while queue:
            node = queue.pop()
            for other in edges.get(node, ()):
                if other in unseen:
                    unseen.remove(other); queue.append(other); size += 1
        sizes.append(size)
    return sorted(sizes, reverse=True)


def reachable_ties(workload, selected, ranks):
    edges = defaultdict(set); rounds = conflicts = 0; affected_queries = set()
    for qidx, query in enumerate(workload["queries"]):
        remaining = set(query["predicates"])
        while True:
            eligible = [cid for cid in query["candidate_ids"] if cid in selected
                        and set(workload["candidates"][cid]["columns"]) <= remaining]
            if not eligible: break
            rounds += 1; winner = min(eligible, key=lambda cid: ranks[cid])
            conflicting = [cid for cid in eligible if cid != winner and
                           set(workload["candidates"][cid]["columns"]) &
                           set(workload["candidates"][winner]["columns"])]
            if conflicting:
                conflicts += 1; affected_queries.add(qidx)
            # All equal-arity eligible objects reach the OID tie-break. Record
            # pairs whose relative order can alter a later eligibility state.
            for left, right in itertools.combinations(eligible, 2):
                if set(workload["candidates"][left]["columns"]) & \
                        set(workload["candidates"][right]["columns"]):
                    edges[left].add(right); edges[right].add(left)
            remaining -= set(workload["candidates"][winner]["columns"])
    return edges, rounds, conflicts, affected_queries


def replay_with_ranks(query, selected, candidates, ranks):
    remaining = set(query["predicates"]); estimate = query["baseline_rows"]
    while True:
        eligible = [cid for cid in query["candidate_ids"] if cid in selected
                    and set(candidates[cid]["columns"]) <= remaining]
        if not eligible: return estimate
        winner = min(eligible, key=lambda cid: ranks[cid])
        estimate *= query["correction_ratios"][str(winner)]
        remaining -= set(candidates[winner]["columns"])


def order_refinement(workload, selected, tie_edges, max_rounds=25):
    from ce_replay_optimize_v1 import qerror
    candidates = workload["candidates"]
    ranks = {cid: candidates[cid]["oid_rank"] for cid in range(len(candidates))}
    losses = [qerror(replay_with_ranks(q, selected, candidates, ranks), q["truth"])
              for q in workload["queries"]]
    total = sum(losses); initial = total; history = []; evaluated = 0
    edge_list = [(left, right) for left, others in tie_edges.items()
                 for right in others if left < right]
    started = time.perf_counter()
    for _ in range(max_rounds):
        best = (0.0, None, None)
        for left, right in edge_list:
            ranks[left], ranks[right] = ranks[right], ranks[left]
            affected = set(candidates[left]["query_indexes"]) | set(candidates[right]["query_indexes"])
            delta = 0.0
            for qidx in affected:
                new = qerror(replay_with_ranks(workload["queries"][qidx], selected,
                                               candidates, ranks),
                             workload["queries"][qidx]["truth"])
                delta += new - losses[qidx]
            ranks[left], ranks[right] = ranks[right], ranks[left]
            evaluated += 1
            if delta < best[0] - 1e-12: best = (delta, left, right)
        if best[1] is None: break
        delta, left, right = best
        ranks[left], ranks[right] = ranks[right], ranks[left]
        affected = set(candidates[left]["query_indexes"]) | set(candidates[right]["query_indexes"])
        for qidx in affected:
            losses[qidx] = qerror(replay_with_ranks(workload["queries"][qidx], selected,
                                                    candidates, ranks),
                                       workload["queries"][qidx]["truth"])
        total = sum(losses)
        history.append({"left": left, "right": right, "delta": delta, "loss": total})
    return {"initial_loss": initial, "final_loss": total,
            "relative_improvement": (initial-total)/initial,
            "accepted_precedence_swaps": history, "edge_evaluations": evaluated,
            "runtime_seconds": time.perf_counter()-started}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--budget-shortlist", type=int, default=32)
    args = parser.parse_args()
    source = json.loads(args.input.read_text()); workload = source["workload_ir"]
    scale = source["scales"][-1]; budget = scale["budget_bytes"]
    marginal = set(scale["algorithms"]["marginal_greedy"]["selected"])
    evaluator = Evaluator(workload); state = evaluator.state(marginal)
    neighbors, two_hop, dependency = interaction_graph(workload)

    started = time.perf_counter()
    full_moves = enumerate_swaps(evaluator, state, budget)
    enumeration_seconds = time.perf_counter()-started
    improving = [move for move in full_moves if move[0] < -1e-12]
    classified = defaultdict(list)
    for delta, removed, added in improving:
        if added in neighbors[removed]: kind = "one_hop_semantic"
        elif added in two_hop[removed]: kind = "two_hop_semantic"
        elif added in dependency[removed]: kind = "same_query_nonconflicting"
        else: kind = "budget_exchange_disconnected"
        classified[kind].append((delta, removed, added))

    # Global budget candidates: strongest current ADD marginals and cheapest.
    unselected = set(range(len(workload["candidates"]))) - marginal
    add_scores = sorted((evaluator.delta_toggle(state, cid), cid) for cid in unselected)
    cheapest = sorted(unselected, key=lambda cid: workload["candidates"][cid]["cost_bytes"])
    budget_pool = {cid for _, cid in add_scores[:args.budget_shortlist]} | \
                  set(cheapest[:args.budget_shortlist])

    search = {}
    search["one_hop"] = restricted_search(
        Evaluator(workload), marginal, budget,
        lambda removed, unselected: neighbors[removed] & unselected)
    search["two_hop"] = restricted_search(
        Evaluator(workload), marginal, budget,
        lambda removed, unselected: two_hop[removed] & unselected)
    search["interaction_plus_budget"] = restricted_search(
        Evaluator(workload), marginal, budget,
        lambda removed, unselected: (neighbors[removed] | budget_pool) & unselected)

    ranks = {cid: candidate["oid_rank"] for cid, candidate in enumerate(workload["candidates"])}
    tie_edges, rounds, conflict_rounds, affected_queries = reachable_ties(workload, marginal, ranks)
    tie_nodes = set(tie_edges)
    tie_edge_count = sum(map(len, tie_edges.values())) // 2
    components = connected_components(tie_edges, tie_nodes)
    order = order_refinement(workload, marginal, tie_edges)

    result = {
        "experiment": "CE-Replay-Optimize-v2",
        "source": str(args.input), "scale": len(workload["candidates"]),
        "budget_bytes": budget, "marginal_loss": state["total"],
        "move_analysis": {
            "feasible_swaps": len(full_moves), "improving_swaps": len(improving),
            "enumeration_seconds": enumeration_seconds,
            "best_full_swap": ({"delta": min(improving)[0],
                                "removed": min(improving)[1], "added": min(improving)[2]}
                               if improving else None),
            "classes": {kind: {"count": len(rows),
                                "best_delta": min(row[0] for row in rows)}
                        for kind, rows in classified.items()},
        },
        "restricted_search": search,
        "order_locality": {
            "consumption_rounds": rounds, "conflicting_rounds": conflict_rounds,
            "affected_queries": len(affected_queries), "tie_nodes": len(tie_nodes),
            "tie_edges": tie_edge_count,
            "tie_degree": ({"mean": statistics.mean(map(len, tie_edges.values())),
                            "median": statistics.median(map(len, tie_edges.values())),
                            "max": max(map(len, tie_edges.values()))} if tie_edges else {}),
            "component_count": len(components), "component_sizes": components,
            "precedence_refinement": order,
        },
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
