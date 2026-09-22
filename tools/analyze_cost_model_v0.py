#!/usr/bin/env python3
"""Empirical PostgreSQL ANALYZE maintenance-cost model for Census extstats."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import platform
import random
import re
import statistics
import time
from collections import defaultdict
from pathlib import Path

import psycopg


IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def mean(xs):
    return statistics.fmean(xs)


def cv(xs):
    m = mean(xs)
    return statistics.pstdev(xs) / m if m else 0.0


def transpose(a):
    return [list(x) for x in zip(*a)]


def matmul(a, b):
    bt = transpose(b)
    return [[sum(x * y for x, y in zip(row, col)) for col in bt] for row in a]


def inverse(a):
    n = len(a)
    z = [list(map(float, row)) + [float(i == j) for j in range(n)]
         for i, row in enumerate(a)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(z[r][col]))
        if abs(z[pivot][col]) < 1e-20:
            raise ValueError("singular design matrix")
        z[col], z[pivot] = z[pivot], z[col]
        scale = z[col][col]
        z[col] = [v / scale for v in z[col]]
        for row in range(n):
            if row == col:
                continue
            scale = z[row][col]
            z[row] = [x - scale * y for x, y in zip(z[row], z[col])]
    return [row[n:] for row in z]


def ols(rows, predictors, name):
    x = [[1.0] + [float(r[p]) for p in predictors] for r in rows]
    y = [[float(r["seconds"])] for r in rows]
    xt = transpose(x)
    xtx_inv = inverse(matmul(xt, x))
    coef = [v[0] for v in matmul(matmul(xtx_inv, xt), y)]
    pred = [sum(c * v for c, v in zip(coef, row)) for row in x]
    resid = [yy[0] - pp for yy, pp in zip(y, pred)]
    ymean = mean([v[0] for v in y])
    sse = sum(v * v for v in resid)
    sst = sum((v[0] - ymean) ** 2 for v in y)
    dof = len(rows) - len(coef)
    sigma2 = sse / dof
    se = [math.sqrt(max(0.0, sigma2 * xtx_inv[i][i])) for i in range(len(coef))]
    # With this many observations, 1.96 is an adequate normal approximation.
    ci = [[c - 1.96 * s, c + 1.96 * s] for c, s in zip(coef, se)]
    rel = [abs(e) / max(abs(yy[0]), 1e-12) for e, yy in zip(resid, y)]
    names = ["intercept_seconds"] + [p + "_seconds" for p in predictors]
    return {
        "name": name,
        "observations": len(rows),
        "predictors": predictors,
        "coefficients": dict(zip(names, coef)),
        "standard_errors": dict(zip(names, se)),
        "confidence_intervals_95_normal": dict(zip(names, ci)),
        "r_squared": 1.0 - sse / sst if sst else 1.0,
        "rmse_seconds": math.sqrt(sse / len(rows)),
        "mae_seconds": mean([abs(v) for v in resid]),
        "median_relative_error": statistics.median(rel),
        "p95_relative_error": percentile(rel, 0.95),
        "max_relative_error": max(rel),
        "residual_mean_seconds": mean(resid),
        "residual_std_seconds": statistics.pstdev(resid),
    }, pred, resid


def percentile(xs, p):
    ys = sorted(xs)
    pos = (len(ys) - 1) * p
    lo = int(pos)
    hi = min(lo + 1, len(ys) - 1)
    return ys[lo] + (ys[hi] - ys[lo]) * (pos - lo)


def deterministic_subset(candidates, count, seed, kind):
    if count >= len(candidates):
        return list(range(len(candidates)))
    scored = []
    for cid, candidate in enumerate(candidates):
        token = f"Analyze-Cost-Model-v0:{kind}:{seed}:{candidate['id']}:{candidate['name']}"
        scored.append((hashlib.sha256(token.encode()).digest(), cid))
    return [cid for _, cid in sorted(scored)[:count]]


def stats(xs):
    return {
        "values_seconds": xs,
        "mean_seconds": mean(xs),
        "median_seconds": statistics.median(xs),
        "std_seconds": statistics.pstdev(xs),
        "cv": cv(xs),
        "min_seconds": min(xs),
        "max_seconds": max(xs),
    }


def validate_columns(candidates):
    for c in candidates:
        if len(c["columns"]) != 2 or not all(IDENT.fullmatch(x) for x in c["columns"]):
            raise ValueError((c["id"], c["columns"]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=Path,
                    default=Path("results/census_ce_replay_optimize_v4.json"))
    ap.add_argument("--output", type=Path,
                    default=Path("results/census_analyze_cost_model_v0.json"))
    ap.add_argument("--csv", type=Path,
                    default=Path("results/census_analyze_cost_model_v0.csv"))
    ap.add_argument("--report", type=Path,
                    default=Path("results/census_analyze_cost_model_v0.md"))
    ap.add_argument("--host", default="/tmp")
    ap.add_argument("--port", type=int, default=55433)
    ap.add_argument("--user", default="postgres")
    ap.add_argument("--db", default="census")
    ap.add_argument("--measurement-db", default="census_analyze_cost_v0")
    ap.add_argument("--runs", type=int, default=10)
    ap.add_argument("--subsets", type=int, default=3)
    ap.add_argument("--target", type=int, default=100)
    args = ap.parse_args()
    if not 3 <= args.runs <= 30:
        raise ValueError("runs must be between 3 and 30")

    raw = args.source.read_bytes()
    source = json.loads(raw)
    workload = source["workload_ir"]
    mcv = workload["mcv_candidates"]
    fd = workload["fd_candidates"]
    validate_columns(mcv)
    validate_columns(fd)

    if not IDENT.fullmatch(args.measurement_db) or args.measurement_db == args.db:
        raise ValueError("measurement database must be a distinct safe identifier")
    admin = psycopg.connect(host=args.host, port=args.port, user=args.user,
                            dbname="postgres", autocommit=True)
    with admin.cursor() as acur:
        acur.execute("SELECT 1 FROM pg_database WHERE datname=%s", (args.measurement_db,))
        if acur.fetchone():
            raise RuntimeError("refusing to overwrite existing database: " + args.measurement_db)
        acur.execute(psycopg.sql.SQL("CREATE DATABASE {} TEMPLATE {}").format(
            psycopg.sql.Identifier(args.measurement_db), psycopg.sql.Identifier(args.db)))
    con = psycopg.connect(host=args.host, port=args.port, user=args.user,
                          dbname=args.measurement_db, autocommit=True)
    cur = con.cursor()
    measurements = []
    config_summaries = []
    prefix = "analyze_cost_v0_"
    started = time.perf_counter()

    try:
        cur.execute("SELECT version()")
        version = cur.fetchone()[0]
        if "PostgreSQL 16.14" not in version:
            raise RuntimeError("expected PostgreSQL 16.14: " + version)
        cur.execute("SELECT count(*) FROM climate")
        table_rows = int(cur.fetchone()[0])
        cur.execute("""
            SELECT current_setting('default_statistics_target'),
                   current_setting('maintenance_work_mem'),
                   current_setting('max_parallel_maintenance_workers'),
                   current_setting('max_parallel_workers_per_gather'),
                   current_setting('track_counts')
        """)
        setting_values = cur.fetchone()
        settings = dict(zip([
            "default_statistics_target", "maintenance_work_mem",
            "max_parallel_maintenance_workers", "max_parallel_workers_per_gather",
            "track_counts"], map(str, setting_values)))
        cur.execute("""
            SELECT count(*),
                   count(*) FILTER (WHERE 'm'=ANY(stxkind)),
                   count(*) FILTER (WHERE 'f'=ANY(stxkind))
            FROM pg_statistic_ext WHERE stxrelid='climate'::regclass
        """)
        original_catalog = tuple(map(int, cur.fetchone()))
        cur.execute("SELECT stxname FROM pg_statistic_ext WHERE stxrelid='climate'::regclass")
        original_names = [r[0] for r in cur.fetchall()]

        # Mutations occur only in an isolated snapshot database. Autocommit is
        # intentional so thousands of DDL locks don't accumulate across curves.
        for name in original_names:
            cur.execute("DROP STATISTICS " + psycopg.sql.Identifier(name).as_string(con))

        mcv_counts = sorted(set([50, 100, 200, 500, 1000, 2000, len(mcv)]))
        mcv_counts = [n for n in mcv_counts if n <= len(mcv)]
        fd_counts = sorted(set([50, 100, 200, 500, len(fd)]))
        fd_counts = [n for n in fd_counts if n <= len(fd)]
        configs = [{"label": "EMPTY", "kind": "empty", "mcv": [], "fd": [],
                    "subset": 0, "n_mcv": 0, "n_fd": 0}]
        for kind, candidates, counts in (("mcv", mcv, mcv_counts), ("fd", fd, fd_counts)):
            for n in counts:
                seeds = [0] if n == len(candidates) else list(range(args.subsets))
                for seed in seeds:
                    ids = deterministic_subset(candidates, n, seed, kind)
                    configs.append({
                        "label": f"{kind.upper()}_{n}_S{seed}", "kind": kind,
                        "mcv": ids if kind == "mcv" else [],
                        "fd": ids if kind == "fd" else [], "subset": seed,
                        "n_mcv": n if kind == "mcv" else 0,
                        "n_fd": n if kind == "fd" else 0,
                    })
        # Three small mixed points identify/check additive mechanism effects
        # without introducing a factorial experiment.
        for seed, (nm, nf) in enumerate(((50, 50), (250, 250), (750, 750))):
            configs.append({
                "label": f"MIXED_{nm}_{nf}_S{seed}", "kind": "mixed",
                "mcv": deterministic_subset(mcv, nm, seed, "mixed_mcv"),
                "fd": deterministic_subset(fd, nf, seed, "mixed_fd"),
                "subset": seed, "n_mcv": nm, "n_fd": nf,
            })

        empty = configs.pop(0)
        rng = random.Random(20260921)
        rng.shuffle(configs)
        configs.insert(0, empty)
        active_names = []
        for config_index, config in enumerate(configs):
            for name in active_names:
                cur.execute("DROP STATISTICS " + psycopg.sql.Identifier(name).as_string(con))
            active_names = []
            for kind, candidates, ids in (("mcv", mcv, config["mcv"]),
                                           ("fd", fd, config["fd"])):
                statkind = "mcv" if kind == "mcv" else "dependencies"
                for pos, cid in enumerate(ids):
                    c = candidates[cid]
                    name = f"{prefix}{config_index:03d}_{kind}_{pos:04d}"
                    cols = psycopg.sql.SQL(", ").join(
                        psycopg.sql.Identifier(x) for x in c["columns"])
                    cur.execute(psycopg.sql.SQL(
                        "CREATE STATISTICS {} ({}) ON {} FROM climate").format(
                            psycopg.sql.Identifier(name), psycopg.sql.SQL(statkind), cols))
                    cur.execute(psycopg.sql.SQL(
                        "ALTER STATISTICS {} SET STATISTICS {}").format(
                            psycopg.sql.Identifier(name), psycopg.sql.Literal(args.target)))
                    active_names.append(name)
            values = []
            for repetition in range(1, args.runs + 1):
                t0 = time.perf_counter()
                cur.execute("ANALYZE climate")
                seconds = time.perf_counter() - t0
                values.append(seconds)
                measurements.append({
                    "configuration_order": config_index,
                    "configuration": config["label"], "kind": config["kind"],
                    "subset": config["subset"], "n_mcv": config["n_mcv"],
                    "n_fd": config["n_fd"], "n_total": config["n_mcv"] + config["n_fd"],
                    "repetition": repetition, "seconds": seconds,
                })
            summary = {k: config[k] for k in
                       ("label", "kind", "subset", "n_mcv", "n_fd")}
            summary.update(stats(values))
            config_summaries.append(summary)
            print(f"[{config_index + 1}/{len(configs)}] {config['label']}: "
                  f"mean={mean(values):.6f}s cv={cv(values):.2%}", flush=True)

        empty_rows = [r for r in measurements if r["kind"] == "empty"]
        mcv_rows = empty_rows + [r for r in measurements if r["kind"] == "mcv"]
        fd_rows = empty_rows + [r for r in measurements if r["kind"] == "fd"]
        all_rows = measurements
        mcv_model, _, _ = ols(mcv_rows, ["n_mcv"], "MCV-only")
        fd_model, _, _ = ols(fd_rows, ["n_fd"], "FD-only")
        uniform_model, _, _ = ols(all_rows, ["n_total"], "Uniform object cost")
        separate_model, predictions, residuals = ols(
            all_rows, ["n_mcv", "n_fd"], "Mechanism-specific object cost")

        by_config = defaultdict(list)
        for r in measurements:
            by_config[r["configuration"]].append(r["seconds"])
        within_cvs = [cv(v) for v in by_config.values()]
        subset_means = defaultdict(list)
        for c in config_summaries:
            if c["kind"] in ("mcv", "fd"):
                subset_means[(c["kind"], c["n_mcv"] + c["n_fd"])].append(c["mean_seconds"])
        subset_rows = []
        for (kind, count), values in sorted(subset_means.items()):
            subset_rows.append({
                "kind": kind, "count": count, "subsets": len(values),
                "mean_of_subset_means_seconds": mean(values),
                "std_of_subset_means_seconds": statistics.pstdev(values),
                "cv_of_subset_means": cv(values),
                "range_seconds": max(values) - min(values),
            })
        multi_subset = [r for r in subset_rows if r["subsets"] > 1]
        model_improvement = (
            (uniform_model["rmse_seconds"] - separate_model["rmse_seconds"])
            / uniform_model["rmse_seconds"]
        )
        bm = mcv_model["coefficients"]["n_mcv_seconds"]
        bf = fd_model["coefficients"]["n_fd_seconds"]
        slope_ratio = max(abs(bm), abs(bf)) / max(min(abs(bm), abs(bf)), 1e-20)
        linear_adequate = (
            mcv_model["r_squared"] >= 0.90 and fd_model["r_squared"] >= 0.90
            and separate_model["median_relative_error"] <= 0.10
        )
        separate_warranted = model_improvement >= 0.10 or slope_ratio >= 1.25

        observed_predicted = []
        for row, pred, resid in zip(measurements, predictions, residuals):
            observed_predicted.append({
                "configuration": row["configuration"], "repetition": row["repetition"],
                "n_mcv": row["n_mcv"], "n_fd": row["n_fd"],
                "observed_seconds": row["seconds"], "predicted_seconds": pred,
                "residual_seconds": resid,
                "relative_error": abs(resid) / row["seconds"],
            })
        baseline = stats([r["seconds"] for r in empty_rows])
        result = {
            "experiment": "Analyze-Cost-Model-v0",
            "scope": {
                "postgres_version": version, "table": "climate",
                "table_rows": table_rows, "settings": settings,
                "available_mcv_candidates": len(mcv),
                "available_fd_candidates": len(fd),
                "statistics_target_for_created_objects": args.target,
                "runs_per_configuration": args.runs,
                "subsets_per_non_all_count": args.subsets,
                "measurement_order": "EMPTY first; remaining configurations shuffled with seed 20260921",
                "transactional_rollback": False,
                "isolation": {
                    "source_database": args.db,
                    "measurement_database": args.measurement_db,
                    "created_from_template": True,
                    "dropped_after_measurement": True,
                },
                "original_catalog": {
                    "total": original_catalog[0], "mcv": original_catalog[1],
                    "fd": original_catalog[2],
                },
                "source_sha256": hashlib.sha256(raw).hexdigest(),
                "machine": {
                    "platform": platform.platform(), "python": platform.python_version(),
                    "cpu_count": os.cpu_count(),
                },
            },
            "baseline": baseline,
            "configurations": config_summaries,
            "models": {
                "mcv_only": mcv_model, "fd_only": fd_model,
                "uniform": uniform_model, "mechanism_specific": separate_model,
                "mechanism_specific_rmse_improvement_over_uniform": model_improvement,
                "pure_curve_slope_ratio": slope_ratio,
            },
            "noise": {
                "within_configuration_cv_median": statistics.median(within_cvs),
                "within_configuration_cv_max": max(within_cvs),
                "subset_variation": subset_rows,
                "multi_subset_cv_median": statistics.median(
                    [r["cv_of_subset_means"] for r in multi_subset]),
                "multi_subset_cv_max": max(r["cv_of_subset_means"] for r in multi_subset),
            },
            "observed_vs_predicted_mechanism_specific": observed_predicted,
            "decision": {
                "linear_first_order_adequate": linear_adequate,
                "separate_mechanism_costs_warranted": separate_warranted,
                "criteria": {
                    "linear": "both pure-curve R2 >= 0.90 and combined median relative error <= 10%",
                    "separate": "combined RMSE improves >=10% or pure MCV/FD slope ratio >=1.25",
                },
                "recommended_budget": (
                    "mechanism-weighted object-count budget" if separate_warranted
                    else "uniform object-count budget"
                ),
            },
            "runtime_seconds": time.perf_counter() - started,
        }
        args.output.write_text(json.dumps(result, indent=2) + "\n")
        with args.csv.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(measurements[0]))
            writer.writeheader()
            writer.writerows(measurements)

        bm_ms = 1000 * bm
        bf_ms = 1000 * bf
        aggregate_effect = max(c["mean_seconds"] for c in config_summaries) - baseline["mean_seconds"]
        subset_cv_med = result["noise"]["multi_subset_cv_median"]
        subset_cv_max = result["noise"]["multi_subset_cv_max"]
        md = f"""# Analyze-Cost-Model-v0

## Scope and method

PostgreSQL 16.14, Census `climate` ({table_rows:,} rows), {len(mcv):,} available MCV candidates and {len(fd):,} available FD candidates. Each configuration was measured with {args.runs} wall-clock `ANALYZE` repetitions after definitions existed. Non-all pure-mechanism counts use {args.subsets} deterministic subsets. Configuration order after `EMPTY` was deterministically shuffled. CREATE/DROP time is excluded.

All catalog and payload mutations ran in an isolated database snapshot cloned from `census`. The snapshot was dropped after measurement; the source database's original {original_catalog[1]} MCV + {original_catalog[2]} FD deployment was never modified.

## Baseline

`EMPTY` mean/median/std/CV: **{baseline['mean_seconds']:.6f}s / {baseline['median_seconds']:.6f}s / {baseline['std_seconds']:.6f}s / {baseline['cv']:.2%}**.

Individual times: `{[round(x, 6) for x in baseline['values_seconds']]}`.

## Fitted first-order models

| Model | Intercept (s) | MCV/object (ms) | FD/object (ms) | R² | RMSE (s) | Median relative error |
|---|---:|---:|---:|---:|---:|---:|
| MCV-only | {mcv_model['coefficients']['intercept_seconds']:.6f} | {bm_ms:.6f} | — | {mcv_model['r_squared']:.6f} | {mcv_model['rmse_seconds']:.6f} | {mcv_model['median_relative_error']:.2%} |
| FD-only | {fd_model['coefficients']['intercept_seconds']:.6f} | — | {bf_ms:.6f} | {fd_model['r_squared']:.6f} | {fd_model['rmse_seconds']:.6f} | {fd_model['median_relative_error']:.2%} |
| Uniform | {uniform_model['coefficients']['intercept_seconds']:.6f} | {1000*uniform_model['coefficients']['n_total_seconds']:.6f} (uniform) | {1000*uniform_model['coefficients']['n_total_seconds']:.6f} (uniform) | {uniform_model['r_squared']:.6f} | {uniform_model['rmse_seconds']:.6f} | {uniform_model['median_relative_error']:.2%} |
| Mechanism-specific | {separate_model['coefficients']['intercept_seconds']:.6f} | {1000*separate_model['coefficients']['n_mcv_seconds']:.6f} | {1000*separate_model['coefficients']['n_fd_seconds']:.6f} | {separate_model['r_squared']:.6f} | {separate_model['rmse_seconds']:.6f} | {separate_model['median_relative_error']:.2%} |

Approximate 95% normal confidence intervals and all observed-versus-predicted residuals are in the JSON artifact. The intervals treat repeated timings as observations and are descriptive rather than cluster-robust inferential intervals. These are empirical first-order fits, not claims that PostgreSQL's true cost is exactly linear.

## Noise and subset variation

Median/max within-configuration CV is {statistics.median(within_cvs):.2%}/{max(within_cvs):.2%}. Median/max CV across subset means at the same mechanism/count is {subset_cv_med:.2%}/{subset_cv_max:.2%}. The largest observed aggregate count effect over `EMPTY` is {aggregate_effect:.6f}s, compared with baseline run-to-run std {baseline['std_seconds']:.6f}s.

The mechanism-specific model improves RMSE over the uniform model by {model_improvement:.2%}; the pure-curve marginal slope ratio is {slope_ratio:.3f}x. Under the preregistered practical rules in the JSON, linear first-order adequacy is **{'yes' if linear_adequate else 'no'}** and separate mechanism costs are **{'warranted' if separate_warranted else 'not warranted'}**.

## Interpretation

This experiment measures recurring `ANALYZE` wall-clock cost after definitions exist. It excludes CREATE/DROP, candidate generation, replay, and optimization. Object count is {'a defensible' if linear_adequate else 'not an adequate'} first-order proxy in this environment. It is not a complete model of collection/refresh cost across tables, schemas, hardware, targets, PostgreSQL versions, or candidate arities.

## Required verdict

1. **What is the measured table-level baseline ANALYZE latency?** Mean {baseline['mean_seconds']:.6f}s; median {baseline['median_seconds']:.6f}s; std {baseline['std_seconds']:.6f}s; CV {baseline['cv']:.2%}.
2. **Does ANALYZE latency increase systematically with the number of deployed extended statistics?** {'Yes' if bm > 0 and bf > 0 else 'Not for both mechanisms'}; fitted pure-mechanism slopes are {bm_ms:.6f} ms/MCV and {bf_ms:.6f} ms/FD.
3. **What is the estimated average marginal cost per MCV object?** {bm_ms:.6f} ms/object (MCV-only first-order fit).
4. **What is the estimated average marginal cost per FD object?** {bf_ms:.6f} ms/object (FD-only first-order fit).
5. **How large is run-to-run ANALYZE timing noise relative to the aggregate statistics-count effect?** Baseline std is {baseline['std_seconds']:.6f}s versus a largest observed mean effect of {aggregate_effect:.6f}s; median/max within-configuration CV is {statistics.median(within_cvs):.2%}/{max(within_cvs):.2%}.
6. **How large is variation between different subsets having the same object count?** Median/max CV of subset means is {subset_cv_med:.2%}/{subset_cv_max:.2%}; per-count values are in `noise.subset_variation`.
7. **Is a linear model adequate as a first-order approximation?** {'Yes' if linear_adequate else 'No'} under the stated R² and median-error rule.
8. **Is a single uniform per-object cost adequate?** {'No' if separate_warranted else 'Yes, at this experiment’s resolution'}.
9. **Or should MCV and FD use separate average costs?** {'Yes' if separate_warranted else 'No'}; mechanism-specific RMSE improvement is {model_improvement:.2%} and pure slope ratio is {slope_ratio:.3f}x.
10. **Is statistics-object count a defensible proxy for recurring ANALYZE maintenance cost?** {'Yes, as a first-order proxy in this tested setting' if linear_adequate else 'No, not from this fit'}.
11. **Should the current physical-design formulation use a uniform count budget or a mechanism-weighted count budget?** {result['decision']['recommended_budget']} if this empirical maintenance resource is adopted; the optimizer is not modified here.
12. **What limitations must accompany this cost model?** One table/workload, one PostgreSQL version and machine, pair-column candidates, target {args.target}, warm repeated runs, limited mixed points, average rather than per-object costs, and no CREATE/DROP, payload-size, collection-frequency, concurrency, I/O-regime, higher-arity, or cross-table effects.
"""
        args.report.write_text(md)
        print(json.dumps({
            "baseline": baseline, "models": result["models"],
            "noise": result["noise"], "decision": result["decision"],
            "runtime_seconds": result["runtime_seconds"],
        }, indent=2), flush=True)
    except BaseException:
        raise
    finally:
        con.close()
        try:
            with admin.cursor() as acur:
                acur.execute(psycopg.sql.SQL("DROP DATABASE {} WITH (FORCE)").format(
                    psycopg.sql.Identifier(args.measurement_db)))
        finally:
            admin.close()


if __name__ == "__main__":
    main()
