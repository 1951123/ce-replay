#!/usr/bin/env python3
"""Workload-scale Census CE replay and optimization experiment.

The instrument phase creates a nested, degree-ranked set of pair-MCV objects,
performs one ANALYZE, serializes their payloads, and specializes every Census
query into baseline rows plus candidate correction nodes.  The benchmark phase
compares full and dependency-incremental evaluation and simple optimizers.
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import random
import re
import statistics
import time
from collections import Counter, defaultdict
from pathlib import Path

import psycopg


CLAUSE_RE = re.compile(r"\s*([A-Za-z_]\w*)\s*(<=|>=|=|<|>)\s*(-?\d+(?:\.\d+)?)\s*$")
RAW_RE = re.compile(r" rows=([^ ]+)")


def text(value):
    return value.decode("ascii") if isinstance(value, bytes) else value


def load_queries(path: Path):
    queries = []
    for index, line in enumerate(path.read_text().splitlines(), 1):
        sql, truth = line.rsplit("||", 1)
        where = re.split(r"\bWHERE\b", sql, flags=re.I)[1].strip()
        predicates = defaultdict(list)
        for clause in re.split(r"\s+AND\s+", where, flags=re.I):
            match = CLAUSE_RE.fullmatch(clause)
            if not match:
                raise ValueError(f"unsupported clause in query.{index}: {clause}")
            column, operator, raw_value = match.groups()
            value = float(raw_value) if "." in raw_value else int(raw_value)
            predicates[column.lower()].append((operator, value))
        queries.append({"id": f"query.{index}", "where": where,
                        "truth": int(truth), "predicates": dict(predicates)})
    return queries


def candidate_universe(queries):
    degree = Counter()
    incident = defaultdict(list)
    for qidx, query in enumerate(queries):
        for columns in itertools.combinations(sorted(query["predicates"]), 2):
            degree[columns] += 1
            incident[columns].append(qidx)
    # Nested scale ladder: high-reuse first, deterministic lexicographic ties.
    ordered = sorted(degree, key=lambda candidate: (-degree[candidate], candidate))
    return ordered, degree, incident


def item_matches(value, is_null, clauses):
    if is_null:
        return False
    number = float(value)
    for operator, target in clauses:
        if operator == "=" and not number == target:
            return False
        if operator == ">=" and not number >= target:
            return False
        if operator == "<=" and not number <= target:
            return False
        if operator == ">" and not number > target:
            return False
        if operator == "<" and not number < target:
            return False
    return True


def combine(simple, mcv, base, total):
    other = min(1.0, max(0.0, simple - base))
    other = min(other, 1.0 - total)
    return min(1.0, max(0.0, mcv + other))


def qerror(estimate, truth):
    estimate = max(estimate, 1e-300)
    truth = max(truth, 1e-300)
    return max(estimate / truth, truth / estimate)


def replay_query(query, selected, candidates):
    remaining = set(query["predicates"])
    estimate = query["baseline_rows"]
    while True:
        eligible = [cid for cid in query["candidate_ids"]
                    if cid in selected
                    and set(candidates[cid]["columns"]) <= remaining]
        if not eligible:
            return estimate
        winner = min(eligible, key=lambda cid: candidates[cid]["oid_rank"])
        estimate *= query["correction_ratios"][str(winner)]
        remaining -= set(candidates[winner]["columns"])


class Evaluator:
    def __init__(self, workload):
        self.queries = workload["queries"]
        self.candidates = workload["candidates"]
        self.candidate_queries = [set(candidate["query_indexes"])
                                  for candidate in self.candidates]
        self.query_replays = 0

    def query_loss(self, qidx, selected):
        self.query_replays += 1
        query = self.queries[qidx]
        return qerror(replay_query(query, selected, self.candidates), query["truth"])

    def full(self, selected):
        return sum(self.query_loss(qidx, selected) for qidx in range(len(self.queries)))

    def state(self, selected=None):
        selected = set(selected or ())
        losses = [self.query_loss(qidx, selected) for qidx in range(len(self.queries))]
        return {"selected": selected, "losses": losses, "total": sum(losses)}

    def delta_toggle(self, state, cid, commit=False):
        new_selected = set(state["selected"])
        if cid in new_selected:
            new_selected.remove(cid)
        else:
            new_selected.add(cid)
        changes = {}
        delta = 0.0
        for qidx in self.candidate_queries[cid]:
            new_loss = self.query_loss(qidx, new_selected)
            changes[qidx] = new_loss
            delta += new_loss - state["losses"][qidx]
        if commit:
            state["selected"] = new_selected
            for qidx, loss in changes.items():
                state["losses"][qidx] = loss
            state["total"] += delta
        return delta

    def delta_swap(self, state, removed, added, commit=False):
        new_selected = set(state["selected"])
        new_selected.remove(removed)
        new_selected.add(added)
        affected = self.candidate_queries[removed] | self.candidate_queries[added]
        changes = {}; delta = 0.0
        for qidx in affected:
            new_loss = self.query_loss(qidx, new_selected)
            changes[qidx] = new_loss
            delta += new_loss - state["losses"][qidx]
        if commit:
            state["selected"] = new_selected
            for qidx, loss in changes.items(): state["losses"][qidx] = loss
            state["total"] += delta
        return delta


def feasible_random(evaluator, budget, rng):
    order = list(range(len(evaluator.candidates)))
    rng.shuffle(order)
    selected, used = set(), 0
    for cid in order:
        cost = evaluator.candidates[cid]["cost_bytes"]
        if used + cost <= budget and rng.random() < 0.5:
            selected.add(cid); used += cost
    return selected


def singleton_greedy(evaluator, budget):
    empty = evaluator.state()
    scored = []
    for cid, candidate in enumerate(evaluator.candidates):
        benefit = -evaluator.delta_toggle(empty, cid)
        scored.append((benefit / candidate["cost_bytes"], benefit, cid))
    selected, used = set(), 0
    for _, benefit, cid in sorted(scored, reverse=True):
        cost = evaluator.candidates[cid]["cost_bytes"]
        if benefit > 0 and used + cost <= budget:
            selected.add(cid); used += cost
    return selected


def marginal_greedy(evaluator, budget):
    state = evaluator.state(); used = 0
    while True:
        best = None
        for cid, candidate in enumerate(evaluator.candidates):
            if cid in state["selected"] or used + candidate["cost_bytes"] > budget:
                continue
            benefit = -evaluator.delta_toggle(state, cid)
            score = benefit / candidate["cost_bytes"]
            if benefit > 0 and (best is None or (score, benefit, -cid) > best[:3]):
                best = (score, benefit, -cid, cid)
        if best is None:
            return state["selected"]
        cid = best[3]
        evaluator.delta_toggle(state, cid, commit=True)
        used += evaluator.candidates[cid]["cost_bytes"]


def local_search(evaluator, budget, initial):
    state = evaluator.state(initial)
    used = sum(evaluator.candidates[cid]["cost_bytes"] for cid in initial)
    while True:
        best = (0.0, None)
        # ADD and DROP moves.
        for cid, candidate in enumerate(evaluator.candidates):
            new_used = used + (-candidate["cost_bytes"] if cid in state["selected"]
                               else candidate["cost_bytes"])
            if new_used > budget:
                continue
            delta = evaluator.delta_toggle(state, cid)
            if delta < best[0] - 1e-12:
                best = (delta, ("toggle", cid, None, new_used))
        # SWAP moves must be evaluated jointly because GreedyCover interactions
        # make delta(drop)+delta(add) generally invalid.
        for removed in state["selected"]:
            removed_cost = evaluator.candidates[removed]["cost_bytes"]
            for added, candidate in enumerate(evaluator.candidates):
                if added in state["selected"]:
                    continue
                new_used = used - removed_cost + candidate["cost_bytes"]
                if new_used > budget:
                    continue
                delta = evaluator.delta_swap(state, removed, added)
                if delta < best[0] - 1e-12:
                    best = (delta, ("swap", removed, added, new_used))
        if best[1] is None:
            return state["selected"]
        operation, first, second, used = best[1]
        if operation == "toggle":
            evaluator.delta_toggle(state, first, commit=True)
        else:
            evaluator.delta_swap(state, first, second, commit=True)


def exact_gray(evaluator, budget):
    n = len(evaluator.candidates)
    state = evaluator.state(); best = (state["total"], set()); used = 0; previous = 0
    for i in range(1, 1 << n):
        gray = i ^ (i >> 1); changed = gray ^ previous
        cid = changed.bit_length() - 1
        cost = evaluator.candidates[cid]["cost_bytes"]
        used += cost if gray & changed else -cost
        evaluator.delta_toggle(state, cid, commit=True)
        if used <= budget and state["total"] < best[0]:
            best = (state["total"], set(state["selected"]))
        previous = gray
    return best[1]


def benchmark(workload, scales, exact_limit, seed):
    results = []
    for scale in scales:
        scoped = {
            "queries": [],
            "candidates": workload["candidates"][:scale],
        }
        for query in workload["queries"]:
            ids = [cid for cid in query["candidate_ids"] if cid < scale]
            copied = dict(query)
            copied["candidate_ids"] = ids
            copied["correction_ratios"] = {str(cid): query["correction_ratios"][str(cid)]
                                             for cid in ids}
            scoped["queries"].append(copied)
        for candidate in scoped["candidates"]:
            candidate["query_indexes"] = [qidx for qidx in candidate["query_indexes"]]
        evaluator = Evaluator(scoped)
        total_cost = sum(candidate["cost_bytes"] for candidate in scoped["candidates"])
        budget = max(candidate["cost_bytes"] for candidate in scoped["candidates"])
        budget = max(budget, int(total_cost * 0.10))

        rng = random.Random(seed)
        probe_designs = [feasible_random(evaluator, budget, rng) for _ in range(20)]
        evaluator.query_replays = 0; start = time.perf_counter()
        for design in probe_designs: evaluator.full(design)
        full_seconds = time.perf_counter() - start; full_replays = evaluator.query_replays
        state = evaluator.state(probe_designs[0]); evaluator.query_replays = 0
        toggles = [rng.randrange(scale) for _ in range(200)]
        start = time.perf_counter()
        for cid in toggles: evaluator.delta_toggle(state, cid, commit=True)
        incremental_seconds = time.perf_counter() - start
        incremental_replays = evaluator.query_replays

        algorithms = {}; algorithm_seconds = {}
        algorithm_start = time.perf_counter()
        random_designs = [feasible_random(evaluator, budget, random.Random(seed + i))
                          for i in range(20)]
        algorithms["random_feasible"] = min(random_designs,
                                               key=lambda design: evaluator.full(design))
        algorithm_seconds["random_feasible"] = time.perf_counter() - algorithm_start
        algorithm_start = time.perf_counter()
        algorithms["singleton_greedy"] = singleton_greedy(evaluator, budget)
        algorithm_seconds["singleton_greedy"] = time.perf_counter() - algorithm_start
        algorithm_start = time.perf_counter()
        algorithms["marginal_greedy"] = marginal_greedy(evaluator, budget)
        algorithm_seconds["marginal_greedy"] = time.perf_counter() - algorithm_start
        algorithm_start = time.perf_counter()
        algorithms["local_search"] = local_search(
            evaluator, budget, algorithms["marginal_greedy"])
        algorithm_seconds["local_search"] = time.perf_counter() - algorithm_start
        if scale <= exact_limit:
            algorithm_start = time.perf_counter()
            algorithms["exact"] = exact_gray(evaluator, budget)
            algorithm_seconds["exact"] = time.perf_counter() - algorithm_start

        baseline = evaluator.full(set())
        rendered = {}
        for name, design in algorithms.items():
            loss = evaluator.full(design)
            rendered[name] = {
                "loss": loss, "normalized_to_empty": loss / baseline,
                "runtime_seconds": algorithm_seconds[name],
                "selected_count": len(design),
                "used_bytes": sum(scoped["candidates"][cid]["cost_bytes"] for cid in design),
                "selected": sorted(design),
            }
        exact_loss = rendered.get("exact", {}).get("loss")
        if exact_loss:
            for value in rendered.values(): value["ratio_to_exact"] = value["loss"] / exact_loss
        results.append({
            "scale": scale, "queries": len(scoped["queries"]), "budget_bytes": budget,
            "full_eval": {"seconds_per_eval": full_seconds / len(probe_designs),
                          "query_replays_per_eval": full_replays / len(probe_designs)},
            "incremental_toggle": {"seconds_per_toggle": incremental_seconds / len(toggles),
                                   "query_replays_per_toggle": incremental_replays / len(toggles)},
            "speedup_time": (full_seconds / len(probe_designs)) /
                            (incremental_seconds / len(toggles)),
            "speedup_query_replays": (full_replays / len(probe_designs)) /
                                     (incremental_replays / len(toggles)),
            "algorithms": rendered,
        })
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queries", type=Path, required=True)
    parser.add_argument("--input-ir", type=Path,
                        help="benchmark an already serialized workload_ir without PostgreSQL")
    parser.add_argument("--host", default="/tmp")
    parser.add_argument("--port", type=int, default=55432)
    parser.add_argument("--user", default="postgres")
    parser.add_argument("--db", default="census")
    parser.add_argument("--target", type=int, default=100)
    parser.add_argument("--scales", default="5,10,20,50,100")
    parser.add_argument("--exact-limit", type=int, default=20)
    parser.add_argument("--seed", type=int, default=20260920)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    scales = [int(value) for value in args.scales.split(",")]
    max_scale = max(scales)
    if args.input_ir:
        source = json.loads(args.input_ir.read_text())
        workload = source.get("workload_ir", source)
        result = {"experiment": "CE-Replay-Optimize-v1-offline-benchmark",
                  "source": str(args.input_ir),
                  "scales": benchmark(workload, scales, args.exact_limit, args.seed)}
        args.output.write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result, indent=2))
        return
    queries = load_queries(args.queries)
    ordered, degree, incident = candidate_universe(queries)
    chosen = ordered[:max_scale]

    conn = psycopg.connect(host=args.host, port=args.port, user=args.user,
                           dbname=args.db, autocommit=True)
    cur = conn.cursor(); notices = []
    conn.add_notice_handler(lambda diagnostic: notices.append(diagnostic.message_primary))
    prefix = "v3_scale_"

    def clean():
        cur.execute("SELECT stxname FROM pg_statistic_ext WHERE stxname LIKE %s", (prefix + "%",))
        for (name,) in cur.fetchall():
            cur.execute(f'DROP STATISTICS IF EXISTS "{text(name)}"')

    def raw_rows(where):
        notices.clear()
        cur.execute(f"EXPLAIN SELECT * FROM climate WHERE {where}")
        raw = [message for message in notices if message.startswith("CE_REPLAY_RAW_ROWS")]
        if len(raw) != 1: raise RuntimeError(f"unexpected raw row trace: {raw}")
        return float(RAW_RE.search(raw[0]).group(1))

    started = time.perf_counter()
    try:
        cur.execute("SELECT stxname FROM pg_statistic_ext WHERE stxrelid='climate'::regclass")
        existing = [text(row[0]) for row in cur.fetchall()]
        if existing: raise RuntimeError("existing climate extstats: " + ", ".join(existing))
        candidates = []
        for cid, columns in enumerate(chosen):
            name = f"{prefix}{cid:04d}"
            cur.execute(f'CREATE STATISTICS "{name}" (mcv) ON {columns[0]}, {columns[1]} FROM climate')
            cur.execute(f'ALTER STATISTICS "{name}" SET STATISTICS {args.target}')
            cur.execute("SELECT oid FROM pg_statistic_ext WHERE stxname=%s", (name,))
            candidates.append({"id": cid, "name": name, "oid": int(cur.fetchone()[0]),
                               "oid_rank": cid, "columns": list(columns),
                               "degree": degree[columns], "query_indexes": incident[columns]})
        cur.execute("ANALYZE climate")
        analyze_done = time.perf_counter()
        cur.execute("CREATE TEMP TABLE v3_scale_backup AS SELECT stxoid, stxdmcv "
                    "FROM pg_statistic_ext_data WHERE stxoid=ANY(%s)",
                    ([candidate["oid"] for candidate in candidates],))
        cur.execute("UPDATE pg_statistic_ext_data SET stxdmcv=NULL WHERE stxoid=ANY(%s)",
                    ([candidate["oid"] for candidate in candidates],))
        relation_rows = raw_rows("TRUE")

        for candidate in candidates:
            cur.execute("SELECT pg_column_size(stxdmcv) FROM v3_scale_backup WHERE stxoid=%s",
                        (candidate["oid"],))
            candidate["cost_bytes"] = int(cur.fetchone()[0])
            cur.execute("SELECT a.attname FROM pg_statistic_ext s CROSS JOIN LATERAL "
                        "unnest(s.stxkeys::smallint[]) WITH ORDINALITY k(attnum,ord) "
                        "JOIN pg_attribute a ON a.attrelid=s.stxrelid AND a.attnum=k.attnum "
                        "WHERE s.oid=%s ORDER BY k.ord", (candidate["oid"],))
            candidate["payload_columns"] = [text(row[0]).lower() for row in cur.fetchall()]
            cur.execute("SELECT values,nulls,frequency,base_frequency FROM pg_mcv_list_items("
                        "(SELECT stxdmcv FROM v3_scale_backup WHERE stxoid=%s))",
                        (candidate["oid"],))
            candidate["payload"] = [{"values": [text(v) if v is not None else None for v in values],
                                      "nulls": nulls, "frequency": float(freq),
                                      "base_frequency": float(base)}
                                     for values, nulls, freq, base in cur.fetchall()]

        workload_queries = []
        for qidx, query in enumerate(queries):
            baseline = raw_rows(query["where"])
            ids = [cid for cid, candidate in enumerate(candidates) if qidx in candidate["query_indexes"]]
            ratios = {}
            for cid in ids:
                candidate = candidates[cid]
                group_where = " AND ".join(
                    f"{column}{operator}{value}" for column in candidate["columns"]
                    for operator, value in query["predicates"][column])
                simple = raw_rows(group_where) / relation_rows
                mcv = base = total = 0.0
                for item in candidate["payload"]:
                    total += item["frequency"]
                    ok = all(item_matches(item["values"][i], item["nulls"][i],
                                          query["predicates"][column])
                             for i, column in enumerate(candidate["payload_columns"]))
                    if ok: mcv += item["frequency"]; base += item["base_frequency"]
                ratios[str(cid)] = combine(simple, mcv, base, total) / simple
            workload_queries.append({"id": query["id"], "truth": query["truth"],
                                     "predicates": query["predicates"],
                                     "baseline_rows": baseline, "candidate_ids": ids,
                                     "correction_ratios": ratios})
        instrument_done = time.perf_counter()
        workload = {"semantic_boundary": "PG16 base AND numeric eq/range pair-MCV",
                    "relation_rows": relation_rows, "queries": workload_queries,
                    "candidates": candidates}
        scale_results = benchmark(workload, scales, args.exact_limit, args.seed)

        # Deploy representative optimizer outputs by activating exactly their
        # catalog payloads, then compare every query with native pre-clamp CE.
        validation_designs = {"empty": []}
        for row in scale_results:
            if row["scale"] in {min(scales), 20, 100, max(scales)}:
                for algorithm in ("singleton_greedy", "marginal_greedy", "local_search"):
                    if algorithm in row["algorithms"]:
                        validation_designs[f"n{row['scale']}_{algorithm}"] = \
                            row["algorithms"][algorithm]["selected"]
        native_validation = []
        all_oids = [candidate["oid"] for candidate in candidates]
        for label, selected_ids in validation_designs.items():
            cur.execute("UPDATE pg_statistic_ext_data d SET stxdmcv=b.stxdmcv "
                        "FROM v3_scale_backup b WHERE d.stxoid=b.stxoid")
            selected_oids = [candidates[cid]["oid"] for cid in selected_ids]
            if selected_oids:
                cur.execute("UPDATE pg_statistic_ext_data SET stxdmcv=NULL "
                            "WHERE stxoid=ANY(%s) AND NOT (stxoid=ANY(%s))",
                            (all_oids, selected_oids))
            else:
                cur.execute("UPDATE pg_statistic_ext_data SET stxdmcv=NULL "
                            "WHERE stxoid=ANY(%s)", (all_oids,))
            selected = set(selected_ids); errors = []
            for query, source_query in zip(workload_queries, queries):
                predicted = replay_query(query, selected, candidates)
                native = raw_rows(source_query["where"])
                errors.append(abs(predicted-native) / max(abs(native), 1e-300))
            native_validation.append({
                "label": label, "selected_count": len(selected_ids),
                "queries": len(errors),
                "floating_point_matches": sum(error <= 1e-12 for error in errors),
                "median_relative_error": statistics.median(errors),
                "max_relative_error": max(errors),
            })
        result = {"experiment": "CE-Replay-Optimize-v1", "target": args.target,
                  "candidate_universe": len(ordered), "instrumented_candidates": max_scale,
                  "query_count": len(queries),
                  "timing": {"create_and_analyze_seconds": analyze_done-started,
                             "total_instrument_seconds": instrument_done-started},
                  "scales": scale_results, "native_validation": native_validation,
                  "workload_ir": workload}
        args.output.write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps({k: result[k] for k in ("candidate_universe",
                                                 "instrumented_candidates",
                                                 "query_count", "timing")}, indent=2))
        for row in scale_results:
            print(json.dumps({k: row[k] for k in ("scale", "budget_bytes", "full_eval",
                                                  "incremental_toggle", "speedup_time",
                                                  "speedup_query_replays", "algorithms")}, indent=2))
    finally:
        clean(); conn.close()


if __name__ == "__main__":
    main()
