#!/usr/bin/env python3
"""IID held-out-query generalization for the frozen mixed MCV+FD optimizer."""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
import random
import statistics
import sys
import time
import types
from collections import Counter, defaultdict
from pathlib import Path

try:
    import psycopg  # noqa: F401
except ModuleNotFoundError:
    sys.modules["psycopg"] = types.ModuleType("psycopg")

from ce_replay_optimize_v1 import qerror
from ce_replay_optimize_v4 import JointEvaluator, marginal_greedy
from compositional_semantic_optimizer_v0 import (
    EPS,
    Model,
    aff,
    ckey,
    initial_state,
    mkey,
    mutate,
)


def quantile(values, p):
    xs = sorted(values)
    if not xs:
        return None
    x = (len(xs) - 1) * p
    lo, hi = math.floor(x), math.ceil(x)
    return xs[lo] if lo == hi else xs[lo] * (hi - x) + xs[hi] * (x - lo)


def summary(values):
    xs = list(values)
    return {
        "count": len(xs), "min": min(xs), "p05": quantile(xs, .05),
        "p25": quantile(xs, .25), "mean": statistics.mean(xs),
        "median": statistics.median(xs), "p75": quantile(xs, .75),
        "p95": quantile(xs, .95), "max": max(xs),
        "std": statistics.pstdev(xs),
    }


def subset_workload(workload, indexes):
    """Preserve global candidate IDs while remapping query incidence locally."""
    old_to_new = {old: new for new, old in enumerate(indexes)}
    mcv = []
    for c in workload["mcv_candidates"]:
        x = dict(c)
        x["query_indexes"] = [old_to_new[q] for q in c["query_indexes"] if q in old_to_new]
        mcv.append(x)
    fd = []
    for c in workload["fd_candidates"]:
        x = dict(c)
        x["query_indexes"] = [old_to_new[q] for q in c["query_indexes"] if q in old_to_new]
        fd.append(x)
    return {
        "relation_rows": workload["relation_rows"],
        "queries": [workload["queries"][i] for i in indexes],
        "mcv_candidates": mcv,
        "fd_candidates": fd,
    }


def optimize(workload, budget, max_rounds=100):
    """Existing joint greedy initializer plus exact ADD/DROP/SWAP best improvement.

    Move values use the same replay semantics as the canonical incremental
    evaluator.  Algebraic reuse makes a disjoint SWAP equal to the sum of its
    two toggle deltas; only shared-query endpoints need a direct joint replay.
    Candidates with no objective-query incidence are omitted: ADD is zero and
    SWAP-to-invisible is dominated exactly by the corresponding DROP.
    """
    started = time.perf_counter()
    seed_state, seed_meta = marginal_greedy(JointEvaluator(workload), budget)
    model = Model(workload)
    state = initial_state(model, seed_state["mcv"], seed_state["fd"])
    trajectory = []
    for rnd in range(max_rounds):
        selected = {*(('mcv', i) for i in state["sm"]), *(('fd', i) for i in state["sf"])}
        relevant = {c for c in model.cands if model.cq[c]} | selected
        used = sum(model.cands[c]["cost_bytes"] for c in selected)
        mm = []
        for c in sorted(relevant, key=ckey):
            new_used = used + (-model.cands[c]["cost_bytes"] if c in selected else model.cands[c]["cost_bytes"])
            if new_used <= budget:
                mm.append(("toggle", c, None))
        for old in sorted(selected, key=ckey):
            for new in sorted(relevant - selected, key=ckey):
                if used - model.cands[old]["cost_bytes"] + model.cands[new]["cost_bytes"] <= budget:
                    mm.append(("swap", old, new))

        toggle_rows, toggle_delta = {}, {}
        for c in sorted(relevant, key=ckey):
            sm1, sf1 = mutate(("toggle", c, None), state["sm"], state["sf"])
            delta = 0.0
            for qi in model.cq[c]:
                row = model.rows(qi, sm1, sf1)
                toggle_rows[(c, qi)] = row
                delta += qerror(row, model.q[qi]["truth"]) - state["losses"][qi]
            toggle_delta[c] = delta

        values = []
        shared_replays = 0
        for move in mm:
            if move[0] == "toggle":
                delta = toggle_delta[move[1]]
            else:
                old, new = move[1], move[2]
                delta = toggle_delta[old] + toggle_delta[new]
                shared = model.cq[old] & model.cq[new]
                if shared:
                    sm1, sf1 = mutate(move, state["sm"], state["sf"])
                    for qi in shared:
                        da = qerror(toggle_rows[(old, qi)], model.q[qi]["truth"]) - state["losses"][qi]
                        db = qerror(toggle_rows[(new, qi)], model.q[qi]["truth"]) - state["losses"][qi]
                        actual = qerror(model.rows(qi, sm1, sf1), model.q[qi]["truth"]) - state["losses"][qi]
                        delta += actual - da - db
                        shared_replays += 1
            values.append((delta, move))
        incumbent, best = min(values, key=lambda x: (x[0], mkey(x[1])))
        row = {
            "round": rnd, "loss_before": state["total"], "feasible": len(mm),
            "evaluated": len(mm), "pruned": 0, "shared_query_replays": shared_replays,
            "best_move": best,
            "delta": incumbent,
        }
        if best is None or incumbent >= -EPS:
            row["loss_after"] = state["total"]
            trajectory.append(row)
            break
        sm1, sf1 = mutate(best, state["sm"], state["sf"])
        for qi in aff(best, model):
            new_row = model.rows(qi, sm1, sf1)
            state["rows"][qi] = new_row
            state["losses"][qi] = qerror(new_row, model.q[qi]["truth"])
        state["sm"], state["sf"] = sm1, sf1
        state["total"] = sum(state["losses"])
        row["loss_after"] = state["total"]
        trajectory.append(row)
    else:
        raise RuntimeError(f"optimizer did not converge in {max_rounds} rounds")
    used = sum(workload["mcv_candidates"][i]["cost_bytes"] for i in state["sm"])
    used += sum(workload["fd_candidates"][i]["cost_bytes"] for i in state["sf"])
    return {
        "mcv": set(state["sm"]), "fd": set(state["sf"]), "loss": state["total"],
        "storage": used, "seed_loss": sum(seed_state["losses"]),
        "seed_mcv": len(seed_state["mcv"]), "seed_fd": len(seed_state["fd"]),
        "seed_meta": seed_meta, "trajectory": trajectory,
        "runtime_seconds": time.perf_counter() - started,
    }


def design_keys(sm, sf):
    return {*(f"mcv:{i}" for i in sm), *(f"fd:{i}" for i in sf)}


def overlap(a, b):
    inter = a & b
    return {
        "jaccard": len(inter) / len(a | b) if a | b else 1.0,
        "shared": sorted(inter), "left_only": sorted(a - b), "right_only": sorted(b - a),
    }


def evaluate(model, query_indexes, sm, sf):
    rows, losses, mcv_used, fd_used = {}, {}, defaultdict(set), defaultdict(set)
    per_query_traces = {}
    for qi in query_indexes:
        b = model.boundary(qi, sm)
        row, ft, _ = model.fd(qi, b, sf)
        rows[qi] = row
        losses[qi] = qerror(row, model.q[qi]["truth"])
        mt = list(b[2])
        per_query_traces[qi] = {"mcv": mt, "fd": list(ft)}
        for cid in mt:
            mcv_used[cid].add(qi)
        for cid in ft:
            fd_used[cid].add(qi)
    return {
        "rows": rows, "losses": losses, "total": sum(losses.values()),
        "mcv_used": mcv_used, "fd_used": fd_used, "traces": per_query_traces,
    }


def removal_contributions(model, indexes, sm, sf, base_eval):
    out = {}
    for typ, selected in (("mcv", sm), ("fd", sf)):
        for cid in sorted(selected):
            affected = model.cq[(typ, cid)] & set(indexes)
            if not affected:
                out[f"{typ}:{cid}"] = 0.0
                continue
            sm1, sf1 = set(sm), set(sf)
            (sm1 if typ == "mcv" else sf1).remove(cid)
            loss = 0.0
            for qi in affected:
                loss += qerror(model.rows(qi, sm1, sf1), model.q[qi]["truth"])
                loss -= base_eval["losses"][qi]
            out[f"{typ}:{cid}"] = loss
    return out


def regression_cause(model, qi, sm, sf, selected_eval):
    tr = selected_eval["traces"][qi]
    if tr["fd"]:
        without_mcv = evaluate(model, [qi], set(), sf)["traces"][qi]["fd"]
        if without_mcv != tr["fd"]:
            return "cross_mechanism_suppression"
        return "fd_interaction"
    if tr["mcv"]:
        return "mcv_winner_or_payload_effect"
    return "no_selected_stat_consumed"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, default=Path("results/census_ce_replay_optimize_v4.json"))
    ap.add_argument("--full-design", type=Path, default=Path("results/census_mixed_deploy_v0_design.json"))
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--report", type=Path, required=True)
    ap.add_argument("--splits", type=Path, required=True)
    ap.add_argument("--queries-output", type=Path)
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--max-rounds", type=int, default=100)
    args = ap.parse_args()

    raw = args.input.read_bytes()
    source = json.loads(raw)
    workload = source["workload_ir"]
    budget = source["budget_bytes"]
    full_design = json.loads(args.full_design.read_text())
    full_sm, full_sf = set(full_design["selected_mcv"]), set(full_design["selected_fd"])
    model = Model(workload)
    n = len(model.q)
    train_n = round(.8 * n)
    all_indexes = list(range(n))
    empty_eval = evaluate(model, all_indexes, set(), set())
    full_eval = evaluate(model, all_indexes, full_sm, full_sf)
    fixed_full_keys = design_keys(full_sm, full_sf)
    per_split, query_rows, selection_counts = [], [], Counter()
    total_started = time.perf_counter()

    for seed in range(args.seeds):
        rng = random.Random(seed)
        shuffled = all_indexes[:]
        rng.shuffle(shuffled)
        train = sorted(shuffled[:train_n])
        test = sorted(shuffled[train_n:])
        train_set, test_set = set(train), set(test)
        train_opt = optimize(subset_workload(workload, train), budget, args.max_rounds)
        test_opt = optimize(subset_workload(workload, test), budget, args.max_rounds)
        train_sm, train_sf = train_opt["mcv"], train_opt["fd"]
        test_sm, test_sf = test_opt["mcv"], test_opt["fd"]
        for k in design_keys(train_sm, train_sf):
            selection_counts[k] += 1

        train_eval = evaluate(model, train, train_sm, train_sf)
        test_eval = evaluate(model, test, train_sm, train_sf)
        test_empty = sum(empty_eval["losses"][q] for q in test)
        test_full = sum(full_eval["losses"][q] for q in test)
        oracle_eval = evaluate(model, test, test_sm, test_sf)
        gain = test_empty - test_eval["total"]
        oracle_gain = test_empty - oracle_eval["total"]
        train_contrib = removal_contributions(model, train, train_sm, train_sf, train_eval)
        test_contrib = removal_contributions(model, test, train_sm, train_sf, test_eval)

        selected = design_keys(train_sm, train_sf)
        test_consumed = {*(f"mcv:{i}" for i in test_eval["mcv_used"]),
                         *(f"fd:{i}" for i in test_eval["fd_used"])}
        train_consumed_eval = evaluate(model, train, train_sm, train_sf)
        train_consumed = {*(f"mcv:{i}" for i in train_consumed_eval["mcv_used"]),
                          *(f"fd:{i}" for i in train_consumed_eval["fd_used"])}
        both_consumed = train_consumed & test_consumed
        scope = {}
        transfers = []
        for key in sorted(selected):
            typ, sid = key.split(":")
            cid = int(sid)
            incident = model.cq[(typ, cid)]
            in_train, in_test = bool(incident & train_set), bool(incident & test_set)
            scope[key] = "both" if in_train and in_test else ("train_only" if in_train else "test_only")
            tc, vc = train_contrib[key], test_contrib[key]
            if key not in test_consumed:
                category = "selected_not_consumed_on_test"
            elif tc > EPS and vc > EPS:
                category = "train_useful_test_useful"
            elif tc > EPS and vc < -EPS:
                category = "train_useful_test_harmful"
            elif tc > EPS:
                category = "train_useful_test_neutral"
            elif vc > EPS:
                category = "weak_train_strong_test"
            else:
                category = "other"
            transfers.append({
                "candidate": key, "scope": scope[key],
                "train_consumers": len(train_consumed_eval[(typ + "_used")].get(cid, set())),
                "test_consumers": len(test_eval[(typ + "_used")].get(cid, set())),
                "train_removal_loss_increase": tc, "test_removal_loss_increase": vc,
                "category": category,
            })

        deltas = []
        tol = 1e-12
        for qi in test:
            delta = empty_eval["losses"][qi] - test_eval["losses"][qi]
            cls = "improved" if delta > tol else ("worsened" if delta < -tol else "unchanged")
            cause = regression_cause(model, qi, train_sm, train_sf, test_eval) if cls == "worsened" else None
            item = {
                "seed": seed, "query_index": qi, "query_id": model.q[qi]["id"],
                "empty_qerror": empty_eval["losses"][qi],
                "train_design_qerror": test_eval["losses"][qi],
                "delta": delta, "classification": cls, "regression_cause": cause,
                "consumed_mcv": test_eval["traces"][qi]["mcv"],
                "consumed_fd": test_eval["traces"][qi]["fd"],
            }
            deltas.append(item)
            query_rows.append(item)
        classes = Counter(x["classification"] for x in deltas)
        sorted_delta = sorted(deltas, key=lambda x: x["delta"])
        scope_counts = Counter(scope.values())
        transfer_counts = Counter(x["category"] for x in transfers)
        train_keys, test_keys = design_keys(train_sm, train_sf), design_keys(test_sm, test_sf)
        per_split.append({
            "seed": seed,
            "train_query_indexes": train, "test_query_indexes": test,
            "train_query_ids": [model.q[i]["id"] for i in train],
            "test_query_ids": [model.q[i]["id"] for i in test],
            "design": {
                "selected_mcv": sorted(train_sm), "selected_fd": sorted(train_sf),
                "selected_mcv_count": len(train_sm), "selected_fd_count": len(train_sf),
                "storage": train_opt["storage"], "scope_counts": dict(scope_counts),
                "optimizer": {k: train_opt[k] for k in ("seed_loss", "seed_mcv", "seed_fd", "runtime_seconds", "trajectory")},
            },
            "test_oracle_design": {
                "selected_mcv": sorted(test_sm), "selected_fd": sorted(test_sf),
                "selected_mcv_count": len(test_sm), "selected_fd_count": len(test_sf),
                "storage": test_opt["storage"],
                "optimizer": {k: test_opt[k] for k in ("seed_loss", "seed_mcv", "seed_fd", "runtime_seconds", "trajectory")},
            },
            "loss": {
                "train_total": train_eval["total"], "train_mean": train_eval["total"] / len(train),
                "test_empty_total": test_empty, "test_empty_mean": test_empty / len(test),
                "test_train_design_total": test_eval["total"], "test_train_design_mean": test_eval["total"] / len(test),
                "test_full_reference_total": test_full, "test_full_reference_mean": test_full / len(test),
                "test_oracle_total": oracle_eval["total"], "test_oracle_mean": oracle_eval["total"] / len(test),
                "generalization_gain": gain, "generalization_gain_mean": gain / len(test),
                "oracle_gain": oracle_gain, "oracle_gain_mean": oracle_gain / len(test),
                "held_out_oracle_gap_recovery": gain / oracle_gain if oracle_gain > 0 else None,
                "generalization_gap": test_eval["total"] / len(test) - train_eval["total"] / len(train),
            },
            "overlap_with_full": overlap(train_keys, fixed_full_keys),
            "overlap_with_test_oracle": overlap(train_keys, test_keys),
            "consumption": {
                "selected_mcv_consumed_on_test": len(set(train_sm) & set(test_eval["mcv_used"])),
                "selected_mcv_consumed_fraction": len(set(train_sm) & set(test_eval["mcv_used"])) / max(1, len(train_sm)),
                "selected_fd_consumed_on_test": len(set(train_sf) & set(test_eval["fd_used"])),
                "selected_fd_consumed_fraction": len(set(train_sf) & set(test_eval["fd_used"])) / max(1, len(train_sf)),
                "test_queries_consuming_selected": sum(bool(test_eval["traces"][q]["mcv"] or test_eval["traces"][q]["fd"]) for q in test),
                "selected_consumed_both_train_test": len(both_consumed),
                "selected_consumed_train_only": len(train_consumed - test_consumed),
                "selected_never_consumed": len(selected - train_consumed - test_consumed),
            },
            "query_level": {
                "counts": dict(classes), "fractions": {k: classes[k] / len(test) for k in ("improved", "unchanged", "worsened")},
                "delta_summary": summary([x["delta"] for x in deltas]),
                "largest_improvements": list(reversed(sorted_delta[-10:])),
                "largest_regressions": sorted_delta[:10],
            },
            "transfer_category_counts": dict(transfer_counts), "transfer_paths": transfers,
        })
        print(json.dumps({"seed": seed, "train_loss": train_eval["total"],
                          "test_loss": test_eval["total"], "test_empty": test_empty,
                          "recovery": gain / oracle_gain if oracle_gain > 0 else None,
                          "seconds": train_opt["runtime_seconds"] + test_opt["runtime_seconds"]}), flush=True)

    gains = [x["loss"]["generalization_gain_mean"] for x in per_split]
    recoveries = [x["loss"]["held_out_oracle_gap_recovery"] for x in per_split
                  if x["loss"]["held_out_oracle_gap_recovery"] is not None]
    gaps = [x["loss"]["generalization_gap"] for x in per_split]
    frequencies = []
    for typ, candidates in (("mcv", workload["mcv_candidates"]), ("fd", workload["fd_candidates"])):
        for cid in range(len(candidates)):
            key = f"{typ}:{cid}"
            frequencies.append({"candidate": key, "selected_splits": selection_counts[key],
                                "frequency": selection_counts[key] / args.seeds})
    result = {
        "experiment": "Workload-Generalization-v0",
        "source": str(args.input), "source_sha256": hashlib.sha256(raw).hexdigest(),
        "full_design": str(args.full_design), "queries": n, "train_queries": train_n,
        "test_queries": n - train_n, "seeds": args.seeds, "budget_bytes": budget,
        "protocol": {
            "split": "deterministic IID random 80/20 without stratification",
            "seed_values": list(range(args.seeds)), "frozen_payload": True,
            "fresh_analyze": False, "candidate_universe": "global 468-query universe",
            "optimizer": "existing joint marginal-greedy initializer plus exact ADD/DROP/SWAP best improvement",
            "leakage": "test SQL/predicate structure contributes to the fixed global candidate universe; test truth/q-error never enters train optimization",
        },
        "aggregate": {
            "positive_splits": sum(g > 0 for g in gains),
            "positive_split_fraction": sum(g > 0 for g in gains) / len(gains),
            "test_gain_per_query": summary(gains),
            "held_out_oracle_gap_recovery": summary(recoveries),
            "generalization_gap": summary(gaps),
            "test_empty_mean_qerror": summary([x["loss"]["test_empty_mean"] for x in per_split]),
            "test_train_design_mean_qerror": summary([x["loss"]["test_train_design_mean"] for x in per_split]),
            "test_full_reference_mean_qerror": summary([x["loss"]["test_full_reference_mean"] for x in per_split]),
            "test_oracle_mean_qerror": summary([x["loss"]["test_oracle_mean"] for x in per_split]),
            "query_class_counts": dict(sum((Counter(x["query_level"]["counts"]) for x in per_split), Counter())),
            "consumption": {k: summary([x["consumption"][k] for x in per_split]) for k in per_split[0]["consumption"]},
            "train_full_jaccard": summary([x["overlap_with_full"]["jaccard"] for x in per_split]),
            "train_oracle_jaccard": summary([x["overlap_with_test_oracle"]["jaccard"] for x in per_split]),
        },
        "selection_frequency": frequencies,
        "per_split": per_split,
        "runtime_seconds": time.perf_counter() - total_started,
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n")

    fields = ["seed", "train_queries", "test_queries", "train_mean", "test_empty_mean",
              "test_train_design_mean", "test_full_reference_mean", "test_oracle_mean",
              "gain_mean", "oracle_gain_mean", "recovery", "generalization_gap",
              "mcv", "fd", "storage", "train_full_jaccard", "train_oracle_jaccard",
              "improved", "unchanged", "worsened", "train_runtime", "oracle_runtime"]
    with args.splits.open("w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=fields)
        wr.writeheader()
        for x in per_split:
            loss, qc = x["loss"], x["query_level"]["counts"]
            wr.writerow({
                "seed": x["seed"], "train_queries": train_n, "test_queries": n-train_n,
                "train_mean": loss["train_mean"], "test_empty_mean": loss["test_empty_mean"],
                "test_train_design_mean": loss["test_train_design_mean"],
                "test_full_reference_mean": loss["test_full_reference_mean"],
                "test_oracle_mean": loss["test_oracle_mean"], "gain_mean": loss["generalization_gain_mean"],
                "oracle_gain_mean": loss["oracle_gain_mean"], "recovery": loss["held_out_oracle_gap_recovery"],
                "generalization_gap": loss["generalization_gap"], "mcv": x["design"]["selected_mcv_count"],
                "fd": x["design"]["selected_fd_count"], "storage": x["design"]["storage"],
                "train_full_jaccard": x["overlap_with_full"]["jaccard"],
                "train_oracle_jaccard": x["overlap_with_test_oracle"]["jaccard"],
                "improved": qc.get("improved", 0), "unchanged": qc.get("unchanged", 0),
                "worsened": qc.get("worsened", 0),
                "train_runtime": x["design"]["optimizer"]["runtime_seconds"],
                "oracle_runtime": x["test_oracle_design"]["optimizer"]["runtime_seconds"],
            })
    if args.queries_output:
        opener = gzip.open if args.queries_output.suffix == ".gz" else open
        with opener(args.queries_output, "wt", newline="") as f:
            wr = csv.DictWriter(f, fieldnames=list(query_rows[0]))
            wr.writeheader()
            for row in query_rows:
                row = dict(row)
                row["consumed_mcv"] = json.dumps(row["consumed_mcv"])
                row["consumed_fd"] = json.dumps(row["consumed_fd"])
                wr.writerow(row)

    ag = result["aggregate"]
    md = f"""# Workload-Generalization-v0

This report is generated after {args.seeds} deterministic IID 80/20 splits.

| Metric | Result |
|---|---:|
| Positive held-out gain splits | {ag['positive_splits']} / {args.seeds} ({ag['positive_split_fraction']:.1%}) |
| Mean held-out gain per query | {ag['test_gain_per_query']['mean']:.6f} |
| Mean no-extstats test q-error | {ag['test_empty_mean_qerror']['mean']:.6f} |
| Mean train-design test q-error | {ag['test_train_design_mean_qerror']['mean']:.6f} |
| Mean test-oracle q-error | {ag['test_oracle_mean_qerror']['mean']:.6f} |
| Mean held-out oracle-gap recovery | {ag['held_out_oracle_gap_recovery']['mean']:.2%} |
| Mean train-test gap | {ag['generalization_gap']['mean']:.6f} |
| Mean train/full-design Jaccard | {ag['train_full_jaccard']['mean']:.2%} |
| Mean train/test-oracle Jaccard | {ag['train_oracle_jaccard']['mean']:.2%} |

The JSON contains exact split membership, trajectories, designs, overlaps,
consumption paths, candidate removal contributions, query-level outcomes and
cross-split selection frequencies. The global candidate universe exposes test
predicate structure, but no test truth, q-error, marginal, stopping signal, or
move rank is used by train optimization.
"""
    args.report.write_text(md)
    print(json.dumps({"aggregate": ag, "runtime_seconds": result["runtime_seconds"]}, indent=2))


if __name__ == "__main__":
    main()
