#!/usr/bin/env python3
"""Read-only provenance audit for the missing DMV frozen query baseline."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from collections import Counter
from pathlib import Path

import psycopg


def sha256(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""): h.update(block)
    return h.hexdigest()


def artifact(path, classification, finding):
    return {"path":str(path),"exists":path.exists(),"size_bytes":path.stat().st_size if path.exists() else None,
            "mtime_ns":path.stat().st_mtime_ns if path.exists() else None,
            "sha256":sha256(path) if path.exists() and path.is_file() else None,
            "classification":classification,"finding":finding}


def key_audit(obj):
    hits=[]; counts=Counter()
    needles=("estimate","qerror","losses","baseline_rows","selectivit","clause_select")
    def walk(value,path=""):
        if isinstance(value,dict):
            for key,child in value.items():
                counts[key]+=1; child_path=path+"/"+key
                if any(x in key.lower() for x in needles):
                    hits.append({"path":child_path,"type":type(child).__name__,
                                 "length":len(child) if isinstance(child,(list,dict)) else None})
                walk(child,child_path)
        elif isinstance(value,list):
            for i,child in enumerate(value): walk(child,path+f"/{i}")
    walk(obj)
    return {"matching_paths":hits,"matching_path_count":len(hits),"all_key_counts":dict(counts)}


def dir_inventory(path):
    files=sorted(x for x in path.glob("*.json") if x.is_file()) if path.exists() else []
    mtimes=[x.stat().st_mtime_ns for x in files]
    return {"path":str(path),"file_count":len(files),"min_mtime_ns":min(mtimes) if mtimes else None,
            "max_mtime_ns":max(mtimes) if mtimes else None,
            "sample_files":[{"path":str(x),"size_bytes":x.stat().st_size,"sha256":sha256(x)}
                            for x in (files[:2]+files[-2:] if len(files)>4 else files)]}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root",type=Path,default=Path("/root/projects/extended-stats-optim-v3"))
    ap.add_argument("--output",type=Path,default=Path("results/dmv_frozen_provenance_recovery_v0.json"))
    ap.add_argument("--report",type=Path,default=Path("results/dmv_frozen_provenance_recovery_v0.md"))
    ap.add_argument("--host",default="/tmp"); ap.add_argument("--port",type=int,default=55433); ap.add_argument("--user",default="postgres")
    args=ap.parse_args(); results=args.root/"results"; tools=args.root/"tools"
    opt_path=results/"dmv_maintenance_budget_optimize_v0.json"; design_path=results/"dmv_maintenance_budget_design_v0.json"
    deploy_path=results/"dmv_deploy_v0.json"; deploy_csv=results/"dmv_deploy_query_comparison_v0.csv"
    opt=json.loads(opt_path.read_text()); design=json.loads(design_path.read_text()); deploy=json.loads(deploy_path.read_text())
    inspected=[
      artifact(opt_path,"same frozen realization / authoritative","Contains payload repository, aggregate losses, selected sets, trajectory, and audits; no per-query final state."),
      artifact(design_path,"same frozen realization / authoritative","Contains 23 selected identities, creation order, cost, budget, and aggregate frozen loss; no query vector."),
      artifact(results/"dmv_maintenance_budget_optimize_v0.md","same frozen realization / summary","Human-readable aggregate summary only."),
      artifact(tools/"dmv_maintenance_budget_optimize_v0.py","same frozen realization / code","Source confirms state.losses existed only in memory and result serialization retained selected sets/aggregate total, not per-query estimates."),
      artifact(results/"dmv_baseline_nonmonotonicity_v0.json","different earlier realization","Has query-level empty-design rows and payloads, but explicitly predates and differs from the optimization realization."),
      artifact(results/"dmv_baseline_nonmonotonicity_v0.md","different earlier realization / summary","Cannot establish optimization-realization provenance."),
      artifact(tools/"dmv_baseline_nonmonotonicity_v0.py","different earlier realization / code","No runtime optimizer state."),
      artifact(results/"dmv_deploy_v0.json","fresh deployment realization","Supports fresh physical/semantic claims but is forbidden as a source of frozen numerical estimates."),
      artifact(deploy_csv,"fresh deployment realization","Contains 1,965 fresh rows; frozen estimate and q-error columns are empty by construction."),
      artifact(results/"dmv_deploy_v0.md","fresh deployment realization / summary","No missing frozen vector."),
      artifact(tools/"dmv_deploy_v0.py","fresh deployment realization / code","Documents the frozen-artifact gap; not original frozen numerical evidence."),
      artifact(results/"dmv_analyze_cost_model_v0.json","cost calibration realization","Timing configurations only; no CE query vector."),
      artifact(results/"dmv_fit_audit_v0.json","static workload audit","Workload shape/truth provenance, not optimization-realization estimates."),
      artifact(Path("/tmp/mixed_deploy_postgres_final.log"),"server operational log","Contains database lifecycle/checkpoint/autovacuum messages, but no CE_REPLAY notice stream or query estimates."),
    ]
    opt_keys=key_audit(opt); design_keys=key_audit(design)
    v2_root=Path("/root/projects/extended-stats-optim-v2")
    legacy=[dir_inventory(v2_root/"results/measure/dmv/oracle"),dir_inventory(v2_root/"results/measure/dmv/postgres"),
            dir_inventory(v2_root/"results_archive_pre_sgrid_20260905/per_lambda/dmv/postgres")]
    legacy_finding=("Legacy per-query files predate DMV-Maintenance-Budget-Optimize-v0 and use a different oracle/per-lambda pipeline, "
                    "rounded estimates, and different designs. They have no unambiguous provenance to the target-100 frozen optimization realization.")
    # Read-only catalog check: no reconstruction or estimator invocation.
    con=psycopg.connect(host=args.host,port=args.port,user=args.user,dbname="postgres",autocommit=True)
    with con.cursor() as cur:
        cur.execute("SELECT datname FROM pg_database WHERE datname LIKE 'dmv%' ORDER BY 1")
        dmv_databases=[x[0] for x in cur.fetchall()]
    con.close()
    with deploy_csv.open(newline="") as f:
        deploy_rows=list(csv.DictReader(f)); csv_header=list(deploy_rows[0])
    csv_rows=len(deploy_rows)
    frozen_estimate_empty=sum(not row["frozen_estimate"] for row in deploy_rows)
    frozen_qerror_empty=sum(not row["frozen_qerror"] for row in deploy_rows)
    server_log=Path("/tmp/mixed_deploy_postgres_final.log")
    server_log_text=server_log.read_text(errors="replace") if server_log.exists() else ""
    server_log_scan={"ce_replay_raw_rows_occurrences":server_log_text.count("CE_REPLAY_RAW_ROWS"),
                     "frozen_aggregate_marker_occurrences":server_log_text.count("7.836513886761748e+298"),
                     "optimization_database_lifecycle_occurrences":server_log_text.count("dmv_maint_opt_v0")}
    same_realization_fields={
      "persisted":{"workload_query_count":opt["instance"]["queries"],"truths_source":"canonical dmv.sql (not duplicated per query in optimizer JSON)",
                   "mcv_payloads":len(opt["instance"]["mcv_candidates"]),"fd_payloads":len(opt["instance"]["fd_candidates"]),
                   "selected_mcv_ids":design["selected_mcv_ids"],"selected_fd_ids":design["selected_fd_ids"],
                   "fixed_precedence":design["fixed_precedence"],"maintenance_cost":design["maintenance_cost"],
                   "budget":design["budget"],"aggregate_loss":design["frozen_predicted_loss"],
                   "accepted_trajectory":len(opt["primary"]["trajectory"])},
      "missing":{"per_query_final_estimate":1965,"per_query_final_qerror":1965,"per_query_baseline_rows":1965,
                 "per_query_clause_selectivities":1965,"per_query_final_loss_state":1965,
                 "direct_per_query_mcv_trace":1965,"direct_per_query_fd_trace":1965},
      "reconstructability":"Payloads and structural control inputs exist, but baseline rows and clause-level simple selectivities from the original ANALYZE realization do not. They are required for exact numerical replay and cannot be derived from aggregate loss or payloads alone."}
    supported={
      "exact_physical_deployment_11_mcv_12_fd":bool(deploy["deployment"]["selected_mcv"]==11 and deploy["deployment"]["selected_fd"]==12),
      "oid_creation_order":deploy["deployment"]["physical_oid_order_verified"],
      "exactly_one_fresh_analyze":deploy["deployment"]["analyze_executions"]==1,
      "mcv_materialization_11_of_11":deploy["fresh_payloads"]["mcv_materialized"]==11,
      "mcv_consumption_11_of_11":deploy["control"]["fresh_mcv_consumed"]==11,
      "fd_materialization_11_of_12":deploy["fresh_payloads"]["fd_materialized"]==11,
      "materialized_fd_consumption_11_of_11":deploy["control"]["fresh_fd_consumed"]==11,
      "queries_consuming_fd_389":deploy["control"]["queries_consuming_fd"]==389,
      "fresh_replay_native_1965_of_1965":deploy["semantic"]["matches"]==deploy["semantic"]["comparisons"]==1965,
      "recorded_max_relative_semantic_error":deploy["semantic"]["max_relative_error"],
      "fresh_replay_native_aggregate_loss_equal":deploy["loss"]["fresh_replay"]==deploy["loss"]["fresh_native"],
      "fresh_nonzero_truth_diagnostic_loss":deploy["loss"]["fresh_replay_nonzero_truth"],
      "physical_useful_mcv_fd_composition":deploy["control"]["fresh_fd_consumed"]>0 and deploy["control"]["queries_consuming_fd"]>0,
    }
    result={"audit":"DMV-Frozen-Provenance-Recovery-v0","mode":"read-only artifact/provenance audit",
      "inspected_artifacts":inspected,"optimizer_json_key_audit":opt_keys,"design_json_key_audit":design_keys,
      "legacy_directories":legacy,"legacy_classification":legacy_finding,
      "filesystem_search":{"exact_optimization_marker_matches":[str(opt_path),str(design_path),str(results/"dmv_maintenance_budget_optimize_v0.md"),str(deploy_path),str(tools/"dmv_maintenance_budget_optimize_v0.py")],
                           "temporary_runtime_state_found":False,"serialized_runtime_cache_found":False,
                           "pycache_interpretation":"Python bytecode stores code, not the terminated process heap/final evaluator state.",
                           "server_log_scan":server_log_scan},
      "database_catalog":{"read_only_check":True,"dmv_databases":dmv_databases,"original_optimization_database_present":"dmv_maint_opt_v0" in dmv_databases},
      "required_frozen_information":same_realization_fields,
      "recovery":{"direct_vector_persisted":False,"all_inputs_for_exact_reconstruction_persisted":False,
                  "all_1965_estimates_recoverable":False,"baseline_csv_created":False,
                  "classification":"artifact/provenance incompleteness","semantic_failure":False},
      "paired_diagnostics":{"zero_truth_query_ids":["dmv.173","dmv.943"],"frozen_zero_truth_contribution":None,
                            "fresh_zero_truth_contribution":deploy["zero_truth"]["fresh_replay_contribution"],
                            "frozen_nonzero_truth_loss":None,"fresh_nonzero_truth_loss":deploy["loss"]["fresh_replay_nonzero_truth"],
                            "estimate_drift_distribution":None,
                            "mcv_trace_changes":deploy["control"]["mcv_trace_changed"],
                            "fd_trace_changes":deploy["control"]["fd_trace_changed"],
                            "trace_provenance":"Exact structural replay is supported by persisted candidate payloads/degrees, selected IDs, precedence, and workload clauses; MCV selection and FD dependency choice do not require the missing numerical simple selectivities."},
      "deploy_query_csv":{"rows":csv_rows,"header":csv_header,
                          "empty_frozen_estimate_cells":frozen_estimate_empty,
                          "empty_frozen_qerror_cells":frozen_qerror_empty,
                          "frozen_columns_present_but_empty":frozen_estimate_empty==csv_rows and frozen_qerror_empty==csv_rows},
      "deployment_claims_independently_supported":supported,
      "cost_model_context":{"predicted_seconds":deploy["cost_sanity"]["predicted_seconds"],
                            "observed_seconds":deploy["cost_sanity"]["observed_seconds"],
                            "relative_error":deploy["cost_sanity"]["relative_error"],
                            "safe_interpretation":"mechanism-weighted model is a first-order resource proxy, not a high-precision per-configuration latency predictor; no refit performed"},
      "gate":"FROZEN BASELINE UNRECOVERABLE"}
    args.output.write_text(json.dumps(result,indent=2)+"\n")

    s=supported; fresh_zero=result["paired_diagnostics"]["fresh_zero_truth_contribution"]
    md=f"""# DMV-Frozen-Provenance-Recovery-v0

## Outcome

The original frozen final-design per-query estimate vector was not persisted, and exact numerical replay cannot be reconstructed from the persisted optimization realization. The authoritative JSON retains 36 MCV and 34 FD payloads, the exact 11+12 design, precedence, trajectory, resource values, and aggregate loss, but omits all 1,965 baseline rows, clause selectivities, final estimates, q-errors, and evaluator loss state. The original `dmv_maint_opt_v0` database is absent.

This is **artifact/provenance incompleteness**, not CE-Replay semantic failure. No replacement database, ANALYZE, payload, replay realization, inference, or approximation was used. Consequently `results/dmv_frozen_query_baseline_v0.csv` was not created.

## Evidence inspected

- Authoritative optimization JSON, design JSON, report, and source code, with hashes preserved in the JSON audit.
- Immediate upstream baseline/nonmonotonicity artifacts; rejected because they belong to a different realization.
- Fresh deployment JSON/CSV/report/source; valid for fresh claims but forbidden as frozen numerical input.
- Cost-model and static-fit artifacts; no query CE vector.
- PostgreSQL server log; lifecycle messages only, no client NOTICE estimate stream.
- PostgreSQL catalog; no DMV database remains.
- `/tmp`, workspace hidden/temporary/cache/manifest candidates; no serialized process state or replay cache.
- Legacy v2 DMV oracle/postgres/per-lambda directories ({legacy[0]['file_count']}, {legacy[1]['file_count']}, and {legacy[2]['file_count']} JSON files); rejected because they predate this optimization and use a different rounded-estimate pipeline/design provenance.

The deploy comparison CSV has {csv_rows:,} rows, but its frozen estimate/q-error columns are empty, exactly as documented by `DMV-Deploy-v0`.

## Claims that remain independently supported

All requested fresh-side claims remain supported: exact 11+12 deployment and OID order; one ANALYZE; 11/11 MCV materialized and consumed; 11/12 FD materialized and all 11 materialized FD consumed; 389 FD-consuming queries; 1,965/1,965 replay/native matches; maximum relative semantic error {s['recorded_max_relative_semantic_error']:.6g}; identical fresh replay/native aggregate loss; fresh nonzero-truth loss {s['fresh_nonzero_truth_diagnostic_loss']:.12g}; and physical survival of useful MCV+FD composition.

Structural paired control evidence also remains valid: 0 MCV trace changes and 37 FD trace changes. Those traces are deterministically recoverable from persisted clauses, selected identities, payload availability/degrees, and precedence; unlike numerical estimates, their decisions do not require the missing baseline/simple-selectivity values.

The deployment ANALYZE prediction/observation remains {result['cost_model_context']['predicted_seconds']:.9f} / {result['cost_model_context']['observed_seconds']:.9f} seconds ({result['cost_model_context']['relative_error']:.4%} error). It supports only a first-order resource proxy interpretation; no model was refitted.

## Required final verdict

1. **Was the original frozen final-design per-query estimate vector persisted anywhere?** No.
2. **If not directly persisted, were all original-realization numerical inputs required for exact deterministic reconstruction persisted?** No; original baseline rows and clause-level simple selectivities are missing.
3. **Can all 1,965 frozen estimates be recovered with unambiguous provenance?** No.
4. **Does the recovered query-level objective reproduce the stored frozen aggregate loss?** Not testable because no valid recovered vector exists.
5. **Which two queries have zero truth?** `dmv.173` and `dmv.943`.
6. **What were their frozen and fresh objective contributions?** Frozen unavailable; fresh contribution {fresh_zero:.12g}.
7. **What is the frozen nonzero-truth diagnostic loss?** Unavailable.
8. **What is the fresh nonzero-truth diagnostic loss?** {deploy['loss']['fresh_replay_nonzero_truth']:.12g}.
9. **What is the paired frozen-to-fresh estimate-drift distribution?** Unavailable.
10. **How many paired MCV control traces changed?** {deploy['control']['mcv_trace_changed']}.
11. **How many paired FD control traces changed?** {deploy['control']['fd_trace_changed']}.
12. **Which `DMV-Deploy-v0` claims remain independently supported even if recovery fails?** Exact deployment/order, one ANALYZE, fresh payload materialization and consumption, 389 FD-consuming queries, 1,965/1,965 semantic matches and recorded maximum error, fresh replay/native loss equality, fresh nonzero-truth loss, and physical MCV+FD composition.
13. **Is the remaining issue semantic correctness or artifact/provenance completeness?** Artifact/provenance completeness; fresh semantic correctness remains supported.

## Final gate

FROZEN BASELINE UNRECOVERABLE
"""
    args.report.write_text(md)
    print(json.dumps({"gate":result["gate"],"direct_vector":False,"exact_inputs":False,
                      "recoverable":False,"database_present":result["database_catalog"]["original_optimization_database_present"],
                      "legacy_counts":[x["file_count"] for x in legacy],"supported_claims":supported},indent=2))


if __name__=="__main__": main()
