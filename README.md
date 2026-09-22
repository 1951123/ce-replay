# CE-Replay: Maintenance-Constrained Extended-Statistics Design

This repository studies resource-constrained physical design of extended statistics for a supplied target workload. Given a database, target queries, candidate statistics, hypothetical candidate payloads, and a recurring statistics-maintenance budget, the design procedure selects a physical statistical state that minimizes target-workload cardinality-estimation loss.

CE-Replay is a workload-specialized, design-parametric executable representation of supported native cardinality-estimation semantics. It exposes both an objective oracle for hypothetical statistics states and a semantic dependency oracle for exact incremental move evaluation. CE-Replay is not a learned cardinality estimator, the local-search algorithm, or a complete replay of PostgreSQL planning.

## Supported boundary

The validated boundary is PostgreSQL 16.14 statistics-sensitive base-relation estimation for conjunctive restrictions, including supported scalar predicates, constant `IN`/`= ANY` ScalarArray MCV semantics, multicolumn MCV, equality-eligible functional dependencies, MCV-first clause consumption feeding FD applicability, and relevant PostgreSQL creation/OID precedence. It does not cover joins, full planner search, arbitrary predicates, all extended-statistics mechanisms, or arbitrary PostgreSQL versions.

Workload-scale results are deterministic local optima under the audited ADD/DROP/SWAP neighborhood for fixed payload and precedence. Global-optimum evidence is limited to small or restricted exhaustive audits.

## Repository layout

- `tools/` — semantic probes, replay evaluators, optimizers, maintenance calibration, deployment, and audit scripts.
- `pgext/ce_replay_native/` — source for the native PostgreSQL validation extension; compiled objects are intentionally ignored.
- `tests/` — lightweight analysis tests.
- `results/` — frozen JSON, Markdown, CSV, and compressed evidence artifacts.
- `docs/` — semantic documentation, convergence audits, frozen paper architecture, and paper Sections 3–8.
- `docs/reproducibility-index-v0.md` — navigation from major claims to scripts and evidence.

## Workloads

- **Census:** 468 queries and a large, sparse pair-candidate incidence structure; used to stress candidate-space scale and incremental evaluation.
- **DMV:** 1,965 queries over dense, high-reuse categorical pairs with extensive constant `IN` predicates; used for ScalarArray semantics and complementary second-workload replication.

Benchmark SQL/data are external inputs in the current snapshot. Several historical scripts retain machine-specific default paths from the original environment; use their CLI path options to select local benchmark and PostgreSQL locations.

## Reproduction entry points

Start with the [reproducibility index](docs/reproducibility-index-v0.md). The primary implementation entry points are under `tools/`, while authoritative claims and boundaries are indexed by:

- [Research convergence audit](docs/research-convergence-audit-v2.md)
- [Paper architecture](docs/paper-architecture-v0.md)
- [Paper claim matrix](results/paper-claim-matrix-v0.json)
- [Evidence matrix](results/research-evidence-matrix-v2.json)

The repository preserves experiment outputs as evidence. Reproduction may require PostgreSQL 16.14, the native validation extension, and separately obtained Census/DMV benchmark inputs.

## Status

- Experimental phase: frozen.
- Paper architecture: frozen.
- Technical Core, Sections 3–6: frozen.
- Methodology and Evaluation, Sections 7–8: frozen.
- Introduction, Discussion, Related Work, and final paper assembly: not yet drafted in this snapshot.

## Provenance boundary

Frozen hypothetical payloads and fresh deployed payloads are distinct realizations. Numerical comparisons are paired only where the artifacts preserve compatible provenance. The final DMV optimization did not persist the per-query frozen estimate vector or sufficient simple-selectivity context, so its paired frozen-to-fresh per-query drift distribution is unrecoverable. This is documented artifact/provenance incompleteness, not a failure of same-fresh-realization CE-Replay/native fidelity.
