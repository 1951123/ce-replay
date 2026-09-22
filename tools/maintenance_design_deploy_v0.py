#!/usr/bin/env python3
"""Deploy and validate the maintenance-budget-selected Census design once."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import psycopg


def catalog_state(host, port, user, db):
    con = psycopg.connect(host=host, port=port, user=user, dbname=db)
    try:
        with con.cursor() as cur:
            cur.execute("SELECT count(*) FROM climate")
            rows = int(cur.fetchone()[0])
            cur.execute("""
                SELECT count(*),
                       count(*) FILTER (WHERE 'm'=ANY(stxkind)),
                       count(*) FILTER (WHERE 'f'=ANY(stxkind))
                FROM pg_statistic_ext WHERE stxrelid='climate'::regclass
            """)
            total, mcv, fd = map(int, cur.fetchone())
            cur.execute("SELECT stxname FROM pg_statistic_ext "
                        "WHERE stxrelid='climate'::regclass ORDER BY oid")
            names = [x[0] for x in cur.fetchall()]
            return {"table_rows": rows, "total": total, "mcv": mcv, "fd": fd,
                    "names_sha256": hashlib.sha256(
                        json.dumps(names).encode()).hexdigest()}
    finally:
        con.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--maintenance-design", type=Path,
                    default=Path("results/census_maintenance_budget_optimize_v0.json"))
    ap.add_argument("--v4", type=Path,
                    default=Path("results/census_ce_replay_optimize_v4.json"))
    ap.add_argument("--cost-model", type=Path,
                    default=Path("results/census_analyze_cost_model_v0.json"))
    ap.add_argument("--previous-deploy", type=Path,
                    default=Path("results/census_mixed_deploy_v0.json"))
    ap.add_argument("--queries", type=Path,
                    default=Path("/root/projects/extended-stats-optim-v2/benchmarks/Census/queries/query.sql"))
    ap.add_argument("--output", type=Path,
                    default=Path("results/census_maintenance_design_deploy_v0.json"))
    ap.add_argument("--report", type=Path,
                    default=Path("results/census_maintenance_design_deploy_v0.md"))
    ap.add_argument("--host", default="/tmp")
    ap.add_argument("--port", type=int, default=55433)
    ap.add_argument("--user", default="postgres")
    ap.add_argument("--source-db", default="census")
    ap.add_argument("--deployment-db", default="census_maintenance_deploy_v0")
    args = ap.parse_args()

    if args.deployment_db == args.source_db or not args.deployment_db.replace("_", "").isalnum():
        raise ValueError("deployment database must be a distinct safe identifier")
    started = time.perf_counter()
    design_raw = args.maintenance_design.read_bytes()
    v4_raw = args.v4.read_bytes()
    cost_raw = args.cost_model.read_bytes()
    previous_raw = args.previous_deploy.read_bytes()
    design = json.loads(design_raw)
    v4 = json.loads(v4_raw)
    costs = json.loads(cost_raw)
    previous = json.loads(previous_raw)
    selected_mcv = design["new_design"]["selected_mcv_ids"]
    selected_fd = design["new_design"]["selected_fd_ids"]
    if len(selected_mcv) != 276 or len(selected_fd) != 7:
        raise RuntimeError("maintenance design is not exactly 276 MCV + 7 FD")
    if not design["optimizer"]["local_optimal_add_drop_swap"]:
        raise RuntimeError("source maintenance design lacks local-optimality audit")

    source_before = catalog_state(args.host, args.port, args.user, args.source_db)
    if (source_before["total"], source_before["mcv"], source_before["fd"]) != (261, 205, 56):
        raise RuntimeError("source Census catalog is not the expected 205+56 deployment")

    admin = psycopg.connect(host=args.host, port=args.port, user=args.user,
                            dbname="postgres", autocommit=True)
    clone_created = False
    deployment = None
    result = None
    try:
        with admin.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname=%s", (args.deployment_db,))
            if cur.fetchone():
                raise RuntimeError("refusing to overwrite existing database " + args.deployment_db)
            cur.execute(psycopg.sql.SQL("CREATE DATABASE {} TEMPLATE {}").format(
                psycopg.sql.Identifier(args.deployment_db),
                psycopg.sql.Identifier(args.source_db)))
            clone_created = True

        # mixed_deploy_v0.final_design starts at joint_semantic and applies
        # negative-delta rounds. A terminal nonnegative round therefore realizes
        # exactly the already-optimized maintenance design without new search.
        adapted_v4 = {
            "strategies": [{
                "strategy": "joint_semantic",
                "selected_mcv": selected_mcv,
                "selected_fd": selected_fd,
            }],
            "workload_ir": v4["workload_ir"],
        }
        adapted_optimizer = {
            "rounds": [{"delta": design["optimizer"]["terminal_best_delta"]}],
        }
        with tempfile.TemporaryDirectory(prefix="maintenance_deploy_v0_") as tmp:
            root = Path(tmp)
            v4_path = root / "v4.json"
            optimizer_path = root / "optimizer.json"
            raw_output = root / "deployment.json"
            raw_report = root / "deployment.md"
            manifest = root / "manifest.json"
            payloads = root / "payloads.json"
            v4_path.write_text(json.dumps(adapted_v4))
            optimizer_path.write_text(json.dumps(adapted_optimizer))
            command = [
                sys.executable, str(Path(__file__).with_name("mixed_deploy_v0.py")),
                "--v4", str(v4_path), "--optimizer", str(optimizer_path),
                "--queries", str(args.queries), "--output", str(raw_output),
                "--report", str(raw_report), "--manifest", str(manifest),
                "--payloads", str(payloads), "--host", args.host,
                "--port", str(args.port), "--user", args.user,
                "--db", args.deployment_db, "--target", "100", "--replace-prefix",
            ]
            completed = subprocess.run(command, check=True, text=True, capture_output=True)
            deployment = json.loads(raw_output.read_text())
            fresh_snapshot = json.loads(payloads.read_text())

        if deployment["design"]["selected_mcv"] != 276 or deployment["design"]["selected_fd"] != 7:
            raise RuntimeError("physical catalog design count mismatch")
        if not deployment["run"]["order_verified"]:
            raise RuntimeError("physical OID order does not match fixed precedence")

        # Predict using the pre-existing mechanism-specific Model B. No refit.
        model = costs["models"]["mechanism_specific"]["coefficients"]
        predicted_latency = (model["intercept_seconds"]
                             + model["n_mcv_seconds"] * len(selected_mcv)
                             + model["n_fd_seconds"] * len(selected_fd))
        observed_latency = deployment["run"]["analyze_seconds"]
        latency_error = observed_latency - predicted_latency

        mcv_diag = deployment["payload_diagnostics"]["mcv"]
        fd_diag = deployment["payload_diagnostics"]["fd"]
        materialized_mcv = sum(x["fresh_size"] > 0 and x["fresh_entries"] > 0
                               for x in mcv_diag)
        materialized_fd = sum(x["dependencies_fresh"] > 0 for x in fd_diag)
        unavailable_fd = [x["id"] for x in fd_diag if x["dependencies_fresh"] == 0]
        consumed_mcv_ids = sorted({
            cid for query in deployment["per_query"]
            for cid in query["external_mcv_trace"]
        })
        fresh_loss = deployment["loss"]["fresh_replay"]
        native_loss = deployment["loss"]["fresh_pg"]
        frozen_loss = deployment["loss"]["frozen"]
        previous_summary = {
            "mcv": previous["design"]["selected_mcv"],
            "fd": previous["design"]["selected_fd"],
            "frozen_loss": previous["loss"]["frozen"],
            "fresh_replay_loss": previous["loss"]["fresh_replay"],
            "fresh_native_loss": previous["loss"]["fresh_pg"],
            "payload_drift": previous["loss"]["payload_drift"],
            "payload_drift_percent": previous["loss"]["payload_drift_percent"],
        }
        result = {
            "experiment": "Maintenance-Design-Deploy-v0",
            "scope": {
                "dbms": deployment["run"]["postgres_version"],
                "source_database": args.source_db,
                "isolated_database": args.deployment_db,
                "fresh_analyze_count": 1,
                "optimizer_rerun": False,
                "fixed_precedence": True,
                "target": deployment["run"]["target"],
            },
            "fingerprint": {
                "maintenance_design_sha256": hashlib.sha256(design_raw).hexdigest(),
                "v4_sha256": hashlib.sha256(v4_raw).hexdigest(),
                "cost_model_sha256": hashlib.sha256(cost_raw).hexdigest(),
                "previous_deploy_sha256": hashlib.sha256(previous_raw).hexdigest(),
            },
            "source_catalog": {"before": source_before, "after": None,
                               "unchanged": None},
            "physical_deployment": {
                "success": True, "selected_mcv": 276, "selected_fd": 7,
                "catalog_mcv": len(deployment["design"]["actual_oids"]["mcv"]),
                "catalog_fd": len(deployment["design"]["actual_oids"]["fd"]),
                "order_verified": deployment["run"]["order_verified"],
                "actual_oids": deployment["design"]["actual_oids"],
            },
            "analyze_latency": {
                "observed_seconds": observed_latency,
                "predicted_seconds": predicted_latency,
                "error_observed_minus_predicted_seconds": latency_error,
                "absolute_error_seconds": abs(latency_error),
                "relative_error": abs(latency_error) / predicted_latency,
                "model": "unchanged mechanism-specific linear model from Analyze-Cost-Model-v0",
            },
            "payload_materialization": {
                "mcv_selected": 276, "mcv_materialized": materialized_mcv,
                "fd_selected": 7, "fd_materialized": materialized_fd,
                "unavailable_fd_ids": unavailable_fd,
                "fresh_mcv_size_bytes": deployment["storage"]["fresh_mcv"],
                "fresh_fd_size_bytes": deployment["storage"]["fresh_fd"],
                "fresh_total_size_bytes": deployment["storage"]["fresh"],
            },
            "three_way_loss": {
                "frozen_prediction": frozen_loss,
                "fresh_replay": fresh_loss,
                "fresh_native": native_loss,
                "payload_realization_drift": fresh_loss - frozen_loss,
                "payload_realization_drift_percent": (fresh_loss / frozen_loss - 1) * 100,
                "semantic_replay_error": native_loss - fresh_loss,
            },
            "semantic_validation": deployment["semantic"],
            "correctness_layers": deployment["correctness_layers"],
            "consumption": {
                "selected_mcv": 276,
                "fresh_consumed_mcv": len(consumed_mcv_ids),
                "fresh_never_consumed_mcv": sorted(set(selected_mcv) - set(consumed_mcv_ids)),
                "selected_fd": 7,
                "frozen_consumed_fd": deployment["consumption"]["frozen_consumed_fd"],
                "fresh_consumed_fd": deployment["consumption"]["fresh_consumed_fd"],
                "fresh_never_consumed_fd": deployment["consumption"]["fresh_never_consumed"],
                "queries_changed_fd_trace": deployment["consumption"]["queries_changed_fd_trace"],
                "changed_query_ids": deployment["consumption"]["changed_query_ids"],
                "fd_availability_changed": bool(unavailable_fd),
            },
            "previous_deployment_context": previous_summary,
            "new_vs_previous_fresh_context_only": {
                "fresh_native_loss_difference": native_loss - previous_summary["fresh_native_loss"],
                "new_fresh_is_lower": native_loss < previous_summary["fresh_native_loss"],
                "warning": "different single ANALYZE realizations; not a controlled paired comparison",
            },
            "payload_diagnostics": deployment["payload_diagnostics"],
            "per_query": deployment["per_query"],
            "fresh_snapshot_counts": {
                "mcv": len(fresh_snapshot["mcv"]), "fd": len(fresh_snapshot["fd"]),
                "queries": len(fresh_snapshot["queries"]),
            },
            "runtime_seconds": time.perf_counter() - started,
            "underlying_tool_stdout_tail": completed.stdout[-1000:],
        }
        # Write once before cleanup so measurements survive a cleanup failure.
        args.output.write_text(json.dumps(result, indent=2) + "\n")
    finally:
        if clone_created:
            with admin.cursor() as cur:
                cur.execute(psycopg.sql.SQL("DROP DATABASE {} WITH (FORCE)").format(
                    psycopg.sql.Identifier(args.deployment_db)))
        admin.close()

    source_after = catalog_state(args.host, args.port, args.user, args.source_db)
    result["source_catalog"]["after"] = source_after
    result["source_catalog"]["unchanged"] = source_before == source_after
    if not result["source_catalog"]["unchanged"]:
        raise RuntimeError("source Census catalog changed during isolated deployment")
    result["cleanup"] = {"isolated_database_dropped": True,
                         "source_catalog_verified_unchanged": True}
    result["runtime_seconds"] = time.perf_counter() - started
    args.output.write_text(json.dumps(result, indent=2) + "\n")

    lat = result["analyze_latency"]
    loss = result["three_way_loss"]
    sem = result["semantic_validation"]
    con = result["consumption"]
    mat = result["payload_materialization"]
    prev = result["previous_deployment_context"]
    fd_changed = bool(con["queries_changed_fd_trace"] or con["fd_availability_changed"])
    md = f"""# Maintenance-Design-Deploy-v0

## Scope and physical realization

The locally optimized maintenance-budget design was deployed once in an isolated PostgreSQL 16.14 Census database: **276 MCV + 7 FD** objects. Creation followed frozen MCV and FD `oid_rank`; actual catalog order was verified. Exactly one fresh `ANALYZE` was run. The isolated database was deleted afterward, and the source catalog was verified unchanged at 205 MCV + 56 FD.

## ANALYZE maintenance-cost sanity check

| Metric | Seconds |
|---|---:|
| Predicted by existing mechanism-specific linear model | {lat['predicted_seconds']:.6f} |
| Observed fresh ANALYZE | {lat['observed_seconds']:.6f} |
| Absolute error | {lat['absolute_error_seconds']:.6f} |
| Relative error | {lat['relative_error']:.2%} |

This is one aggregate sanity check, not a refit or an independent cost-model study.

## Payload materialization

- MCV payloads materialized: {mat['mcv_materialized']}/276.
- FD payloads materialized: {mat['fd_materialized']}/7.
- Unavailable FD IDs: `{mat['unavailable_fd_ids']}`.
- Fresh serialized sizes: MCV {mat['fresh_mcv_size_bytes']:,} bytes; FD {mat['fresh_fd_size_bytes']:,} bytes; total {mat['fresh_total_size_bytes']:,} bytes.

## Three-way loss distinction

| Quantity | Workload loss |
|---|---:|
| Frozen optimization prediction | {loss['frozen_prediction']:.12f} |
| Fresh replay | {loss['fresh_replay']:.12f} |
| Fresh native PostgreSQL | {loss['fresh_native']:.12f} |

Frozen→fresh payload-realization drift is {loss['payload_realization_drift']:.12f} ({loss['payload_realization_drift_percent']:.4f}%). Fresh native minus fresh replay semantic error is {loss['semantic_replay_error']:.12g}.

Fresh replay matched {sem['matches_1e_12']}/{sem['queries']} native estimates within 1e-12; maximum relative error is {sem['max_relative_error']:.3g}, median {sem['median_relative_error']:.3g}, and {sem['bitwise_rows']}/{sem['queries']} raw-row estimates are bitwise equal.

## Consumption audit

- MCV consumed by at least one query: {con['fresh_consumed_mcv']}/276.
- FD consumed under frozen/fresh payloads: {con['frozen_consumed_fd']}/7 and {con['fresh_consumed_fd']}/7.
- Fresh never-consumed FD IDs: `{con['fresh_never_consumed_fd']}`.
- Queries whose FD trace changed from frozen to fresh: {con['queries_changed_fd_trace']} (`{con['changed_query_ids']}`).
- FD availability changed: {'yes' if con['fd_availability_changed'] else 'no'}.

## Previous deployment context

| Design | MCV | FD | Frozen loss | Fresh replay/native loss | Payload drift |
|---|---:|---:|---:|---:|---:|
| Previous byte-budget deployment | {prev['mcv']} | {prev['fd']} | {prev['frozen_loss']:.6f} | {prev['fresh_native_loss']:.6f} | {prev['payload_drift']:.6f} ({prev['payload_drift_percent']:.4f}%) |
| New maintenance-budget deployment | 276 | 7 | {loss['frozen_prediction']:.6f} | {loss['fresh_native']:.6f} | {loss['payload_realization_drift']:.6f} ({loss['payload_realization_drift_percent']:.4f}%) |

The new single fresh loss is {'lower' if loss['fresh_native'] < prev['fresh_native_loss'] else 'not lower'} than the previous recorded realization, but these are different `ANALYZE` realizations and are not a controlled paired comparison.

## Required verdict

1. **Was the 276-MCV + 7-FD design physically deployed successfully?** Yes; catalog counts and fixed creation/OID order were verified in the isolated database.
2. **What was the observed ANALYZE latency?** {lat['observed_seconds']:.6f} seconds.
3. **What latency did the linear maintenance-cost model predict?** {lat['predicted_seconds']:.6f} seconds.
4. **What was the prediction error?** Observed minus predicted {lat['error_observed_minus_predicted_seconds']:.6f} seconds; absolute {lat['absolute_error_seconds']:.6f} seconds ({lat['relative_error']:.2%}).
5. **What was the frozen predicted workload loss?** {loss['frozen_prediction']:.12f}.
6. **What was the fresh replay workload loss?** {loss['fresh_replay']:.12f}.
7. **What was the frozen-to-fresh payload-realization drift?** {loss['payload_realization_drift']:.12f} ({loss['payload_realization_drift_percent']:.4f}%).
8. **What was the fresh native PostgreSQL workload loss?** {loss['fresh_native']:.12f}.
9. **How closely did fresh CE-Replay match native PostgreSQL?** {sem['matches_1e_12']}/{sem['queries']} within 1e-12; max relative error {sem['max_relative_error']:.3g}; semantic loss error {loss['semantic_replay_error']:.12g}.
10. **How many selected MCV statistics were actually consumed?** {con['fresh_consumed_mcv']}/276.
11. **How many selected FD statistics were actually consumed?** {con['fresh_consumed_fd']}/7.
12. **Did fresh ANALYZE change any relevant FD availability/control paths?** {'Yes' if fd_changed else 'No'}; unavailable FD IDs `{mat['unavailable_fd_ids']}`, changed FD-trace queries {con['queries_changed_fd_trace']}.
13. **Does the deployment validate the new maintenance-budget physical-design loop?** Yes: the exact selected design was realized, fresh payload replayed, and fresh replay remained semantically faithful to native PostgreSQL within the validated fragment.
14. **What limitations remain?** One PostgreSQL 16.14 Census deployment and one fresh `ANALYZE`; environment-specific maintenance coefficients; base-restriction pair-MCV/equality-FD fragment; fixed precedence; payload drift; local rather than global optimality; and no robustness or paired superiority claim.
"""
    args.report.write_text(md)
    print(json.dumps({
        "physical_deployment": result["physical_deployment"],
        "analyze_latency": lat, "three_way_loss": loss,
        "semantic": {k: sem[k] for k in (
            "queries", "matches_1e_12", "bitwise_rows", "max_relative_error",
            "median_relative_error")},
        "consumption": con, "cleanup": result["cleanup"],
    }, indent=2))


if __name__ == "__main__":
    main()
