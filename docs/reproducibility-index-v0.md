# Reproducibility Index v0

This index maps the paper's major claims and evaluation stages to their primary executable and frozen evidence artifacts. It is a navigation aid; the complete 39-experiment inventory remains in `results/research-evidence-matrix-v2.json`.

## Core experimental chain

| Stage | Purpose | Primary script | Primary result JSON | Primary report | Status |
|---|---|---|---|---|---|
| Census semantic validation | Validate workload-specialized MCV replay against native raw/pre-clamp estimates | `tools/ce_replay_ir_v1.py` | `results/census_ce_replay_ir_v1b_instrumented_target100.json` and target variants | `results/census_ce_replay_v1b_optimize_v0.md` | Complete; supported fragment only |
| FD semantic validation | Validate FD applicability, selection, numerical update, and MCV-first composition | `tools/fd_semantics_v0.py` | `results/fd_semantics_v0.json` | `results/fd_semantics_v0.md` | Complete |
| Census non-monotonicity | Establish harmful additions and improving removals | `tools/statistics_nonmonotonicity_v0.py` | `results/census_statistics_nonmonotonicity_v0.json` | `results/census_statistics_nonmonotonicity_v0.md` | Complete |
| Census maintenance calibration | Fit the first-order mechanism-aware recurring `ANALYZE` proxy | `tools/analyze_cost_model_v0.py` | `results/census_analyze_cost_model_v0.json` | `results/census_analyze_cost_model_v0.md` | Complete; environment-specific |
| Census maintenance optimization | Optimize the frozen workload under the calibrated maintenance budget | `tools/maintenance_budget_optimize_v0.py` | `results/census_maintenance_budget_optimize_v0.json` | `results/census_maintenance_budget_optimize_v0.md` | Complete; ADD/DROP/SWAP local optimum |
| Census deployment | Deploy the maintenance-budget design and compare fresh replay with native CE | `tools/maintenance_design_deploy_v0.py` | `results/census_maintenance_design_deploy_v0.json` | `results/census_maintenance_design_deploy_v0.md` | Complete; paired frozen/fresh evidence available |
| Repeated Census ANALYZE | Quantify payload realization variability while auditing same-realization replay fidelity | `tools/repeated_analyze_robustness_v0.py` | `results/census_repeated_analyze_robustness_v0.json` | `results/census_repeated_analyze_robustness_v0.md` | Complete; one fixed design across 30 realizations |
| ScalarArray semantic validation | Add and validate constant `IN`/`= ANY` MCV semantics | `tools/mcv_scalararray_semantics_v0.py` | `results/mcv_scalararray_semantics_v0.json` | `results/mcv_scalararray_semantics_v0.md` | Complete; bounded predicate extension |
| DMV baseline/non-monotonicity | Validate real IN-heavy replay and replicate statistics-set non-monotonicity | `tools/dmv_baseline_nonmonotonicity_v0.py` | `results/dmv_baseline_nonmonotonicity_v0.json` | `results/dmv_baseline_nonmonotonicity_v0.md` | Complete; baseline realization |
| DMV maintenance calibration | Independently fit the DMV first-order maintenance proxy | `tools/dmv_analyze_cost_model_v0.py` | `results/dmv_analyze_cost_model_v0.json` | `results/dmv_analyze_cost_model_v0.md` | Complete; environment-specific |
| DMV maintenance optimization | Optimize a new internally consistent frozen DMV realization | `tools/dmv_maintenance_budget_optimize_v0.py` | `results/dmv_maintenance_budget_optimize_v0.json` | `results/dmv_maintenance_budget_optimize_v0.md` | Complete; local optimum plus restricted exhaustive audits |
| DMV deployment | Deploy the authoritative selected definitions and validate fresh semantics | `tools/dmv_deploy_v0.py` | `results/dmv_deploy_v0.json` | `results/dmv_deploy_v0.md` | Fresh physical/semantic validation complete |
| DMV provenance limitation | Audit whether the missing frozen per-query baseline can be recovered | `tools/dmv_frozen_provenance_recovery_v0.py` | `results/dmv_frozen_provenance_recovery_v0.json` | `results/dmv_frozen_provenance_recovery_v0.md` | Frozen per-query baseline unrecoverable |

## Optimization and incremental evaluation

| Stage | Purpose | Primary script | Primary result JSON | Primary report | Status |
|---|---|---|---|---|---|
| Small exact optimization | Compare replay and native exhaustive optima over five candidates | `tools/ce_replay_optimize_v0.py` | `results/census_ce_replay_optimize_v0.json` | `results/census_ce_replay_v1b_optimize_v0.md` | Complete; small-instance global evidence |
| Census affected-query evaluation | Measure sparse query-local MCV evaluation | `tools/ce_replay_optimize_v1.py` | `results/census_ce_replay_optimize_v1_runtime.json` | `results/census_ce_replay_optimize_v1.md` | Complete; evaluator-specific performance |
| MCV semantic optimizer | Preserve complete current-neighborhood trajectory using exact incremental evaluation | `tools/semantic_optimizer_v0.py` | `results/census_semantic_optimizer_v0.json` | `results/census_semantic_optimizer_v0.md` | Complete |
| Mixed semantic optimizer | Validate compositional MCV+FD invalidation and exact trajectory | `tools/compositional_semantic_optimizer_v0.py` | `results/census_compositional_semantic_optimizer_v0.json` | `results/census_compositional_semantic_optimizer_v0.md` | Complete; control work reduced, wall time not improved |

## Research and paper audits

| Artifact | Purpose | Status |
|---|---|---|
| `docs/research-convergence-audit-v2.md` | Final evidence synthesis, RQ verdicts, limitations, and experimental freeze gate | Frozen |
| `results/research-evidence-matrix-v2.json` | Machine-readable 39-experiment inventory | Frozen |
| `results/paper-claim-matrix-v0.json` | Safe and prohibited wording for paper claims | Frozen |
| `docs/paper-architecture-v0.md` | Logical paper structure, terminology, notation, and figure/table budget | Frozen |
| `results/paper-evidence-map-v0.json` | Section/claim/experiment/file traceability | Frozen |
| `docs/paper-section-3-problem-formulation-v0.md` through `docs/paper-section-6-physical-design-v0.md` | Technical Core | Frozen |
| `results/paper-technical-notation-audit-v0.json` and `results/paper-technical-claim-audit-v0.json` | Technical consistency audits | Pass |
| `docs/paper-section-7-methodology-v0.md` and `docs/paper-section-8-evaluation-v0.md` | Methodology and RQ-driven Evaluation | Frozen |
| `results/paper-evaluation-number-audit-v0.json` | Evaluation number provenance | Pass |
| `results/paper-evaluation-realization-audit-v0.json` | Frozen/fresh and cross-realization comparison audit | Pass |
| `results/paper-evaluation-claim-audit-v0.json` | Evaluation claim guardrails | Pass |

## Provenance notice

Candidate definitions, frozen hypothetical payloads, physical realization, and fresh deployed payloads are distinct. Absolute objective comparisons are valid only when the originating artifact preserves a compatible realization or explicitly defines a paired frozen/fresh comparison.

The DMV baseline/non-monotonicity experiment and later maintenance optimization use different target-100 realizations. Their absolute losses must not be combined as a paired trajectory. The final DMV deployment preserves fresh replay/native comparisons and structural consumption evidence, but the original optimization run did not persist its per-query frozen estimates, baseline rows, or clause-level simple selectivities. Exact paired frozen-to-fresh per-query drift is therefore unavailable. The provenance audit classifies this as artifact incompleteness rather than replay semantic failure.

## External inputs and local paths

The snapshot does not vendor the full Census/DMV datasets or PostgreSQL source/build tree. Some scripts retain original-machine default paths for provenance and convenience; use their CLI options to point to local workload SQL, CSV data, and PostgreSQL installations. Result artifacts containing absolute paths are historical records and should not be rewritten merely for portability.
