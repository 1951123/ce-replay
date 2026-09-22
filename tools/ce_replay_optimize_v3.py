#!/usr/bin/env python3
"""Joint selection--precedence alternating refinement over a frozen CE IR."""

from __future__ import annotations

import argparse
import itertools
import json
import time
from pathlib import Path

from ce_replay_optimize_v1 import qerror
from ce_replay_optimize_v2 import interaction_graph, reachable_ties, replay_with_ranks


class JointState:
    def __init__(self, workload, selected, ranks):
        self.workload = workload
        self.candidates = workload["candidates"]
        self.selected = set(selected)
        self.ranks = dict(ranks)
        self.losses = [self.query_loss(qidx, self.selected, self.ranks)
                       for qidx in range(len(workload["queries"]))]
        self.total = sum(self.losses)
        self.query_replays = len(self.losses)

    def query_loss(self, qidx, selected, ranks):
        query = self.workload["queries"][qidx]
        return qerror(replay_with_ranks(query, selected, self.candidates, ranks),
                      query["truth"])

    def evaluate_change(self, selected, ranks, affected):
        changes = {}; delta = 0.0
        for qidx in affected:
            self.query_replays += 1
            loss = self.query_loss(qidx, selected, ranks)
            changes[qidx] = loss; delta += loss-self.losses[qidx]
        return delta, changes

    def commit(self, selected, ranks, delta, changes):
        self.selected = set(selected); self.ranks = dict(ranks)
        for qidx, loss in changes.items(): self.losses[qidx] = loss
        self.total += delta


def selection_refine(state, budget, neighbors, budget_shortlist=32, max_moves=100):
    candidates = state.candidates
    used = sum(candidates[cid]["cost_bytes"] for cid in state.selected)
    history = []; evaluated = 0; started = time.perf_counter()
    for _ in range(max_moves):
        unselected = set(range(len(candidates))) - state.selected
        # Recompute a small global exchange channel under the current (Y, pi).
        add_deltas = []
        for added in unselected:
            selected = state.selected | {added}
            delta, _ = state.evaluate_change(selected, state.ranks,
                                              set(candidates[added]["query_indexes"]))
            add_deltas.append((delta, added)); evaluated += 1
        cheapest = sorted(unselected, key=lambda cid: candidates[cid]["cost_bytes"])
        budget_pool = {cid for _, cid in sorted(add_deltas)[:budget_shortlist]} | \
                      set(cheapest[:budget_shortlist])

        best = (0.0, None)
        # ADD / DROP.
        for cid in range(len(candidates)):
            if cid in state.selected:
                selected = state.selected - {cid}; new_used = used-candidates[cid]["cost_bytes"]
            else:
                new_used = used+candidates[cid]["cost_bytes"]
                if new_used > budget: continue
                selected = state.selected | {cid}
            delta, changes = state.evaluate_change(
                selected, state.ranks, set(candidates[cid]["query_indexes"]))
            evaluated += 1
            if delta < best[0]-1e-12:
                best = (delta, ("toggle", cid, None, selected, new_used, changes))

        # Local semantic swaps plus a small global budget-exchange channel.
        for removed in state.selected:
            incoming = (neighbors[removed] | budget_pool) & unselected
            for added in incoming:
                new_used = used-candidates[removed]["cost_bytes"]+candidates[added]["cost_bytes"]
                if new_used > budget: continue
                selected = (state.selected-{removed}) | {added}
                affected = set(candidates[removed]["query_indexes"]) | \
                           set(candidates[added]["query_indexes"])
                delta, changes = state.evaluate_change(selected, state.ranks, affected)
                evaluated += 1
                if delta < best[0]-1e-12:
                    best = (delta, ("swap", removed, added, selected, new_used, changes))
        if best[1] is None: break
        operation, first, second, selected, used, changes = best[1]
        state.commit(selected, state.ranks, best[0], changes)
        history.append({"operation": operation, "removed_or_toggled": first,
                        "added": second, "delta": best[0], "loss": state.total})
    return {"loss": state.total, "moves": history, "move_evaluations": evaluated,
            "runtime_seconds": time.perf_counter()-started}


def order_refine(state, max_moves=25):
    history = []; evaluated = 0; started = time.perf_counter()
    for _ in range(max_moves):
        tie_edges, _, _, _ = reachable_ties(
            state.workload, state.selected, state.ranks)
        edges = [(left, right) for left, others in tie_edges.items()
                 for right in others if left < right]
        best = (0.0, None)
        for left, right in edges:
            ranks = dict(state.ranks); ranks[left], ranks[right] = ranks[right], ranks[left]
            affected = set(state.candidates[left]["query_indexes"]) | \
                       set(state.candidates[right]["query_indexes"])
            delta, changes = state.evaluate_change(state.selected, ranks, affected)
            evaluated += 1
            if delta < best[0]-1e-12:
                best = (delta, (left, right, ranks, changes))
        if best[1] is None: break
        left, right, ranks, changes = best[1]
        state.commit(state.selected, ranks, best[0], changes)
        history.append({"left": left, "right": right, "delta": best[0],
                        "loss": state.total})
    return {"loss": state.total, "moves": history, "edge_evaluations": evaluated,
            "runtime_seconds": time.perf_counter()-started}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--rounds", type=int, default=5)
    parser.add_argument("--order-moves", type=int, default=25)
    parser.add_argument("--selection-moves", type=int, default=100)
    parser.add_argument("--relative-tolerance", type=float, default=1e-4)
    args = parser.parse_args()
    source = json.loads(args.input.read_text()); workload = source["workload_ir"]
    scale = source["scales"][-1]; budget = scale["budget_bytes"]
    selected = scale["algorithms"]["marginal_greedy"]["selected"]
    ranks = {cid: candidate["oid_rank"] for cid, candidate in enumerate(workload["candidates"])}
    neighbors, _, _ = interaction_graph(workload)
    state = JointState(workload, selected, ranks)
    initial = state.total; rounds = []
    for iteration in range(args.rounds):
        before = state.total
        order = order_refine(state, args.order_moves)
        after_order = state.total
        selection = selection_refine(state, budget, neighbors,
                                     max_moves=args.selection_moves)
        after_selection = state.total
        rounds.append({"iteration": iteration+1, "before": before,
                       "after_order": after_order, "after_selection": after_selection,
                       "order": order, "selection": selection,
                       "selected_count": len(state.selected)})
        if (before-after_selection)/before < args.relative_tolerance: break
    result = {"experiment": "CE-Replay-Optimize-v3-joint",
              "source": str(args.input), "budget_bytes": budget,
              "initial_loss": initial, "final_loss": state.total,
              "relative_improvement": (initial-state.total)/initial,
              "rounds": rounds, "final_selected": sorted(state.selected),
              "final_precedence": sorted(state.ranks, key=state.ranks.get),
              "total_query_replays": state.query_replays}
    args.output.write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps({k: result[k] for k in ("initial_loss", "final_loss",
                                             "relative_improvement", "rounds",
                                             "total_query_replays")}, indent=2))


if __name__ == "__main__":
    main()
