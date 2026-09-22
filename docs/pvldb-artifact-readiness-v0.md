# PVLDB Artifact Readiness Audit

| Area | Status | Evidence / gap |
|---|---|---|
| Public accessibility | READY | Public GitHub repository: `https://github.com/1951123/ce-replay`. |
| Frozen evidence tag | READY | `research-freeze-v0` resolves to `22cf494f954cffff86080236473ca847064dca74`. |
| README entry point | PARTIAL | Root README explains scope and links the reproducibility index, but its status section predates the completed manuscript. |
| Reproducibility instructions | PARTIAL | Claim-to-script index exists; there is no single clean-room, end-to-end reproduction guide. |
| Experiment organization | READY | `tools/`, `results/`, `docs/`, `tests/`, and native extension sources are separated and extensively indexed. |
| Dependency/environment documentation | PARTIAL | PostgreSQL boundary is documented, but machine dependencies and Python/package setup are not consolidated. |
| Expected runtime | MISSING | No unified per-stage or end-to-end runtime budget for artifact reviewers. |
| Storage requirements | MISSING | No consolidated download, database, payload, and result storage estimate. |
| PostgreSQL version requirements | READY | PostgreSQL 16.14 and supported semantic boundary are explicit. |
| Census availability/reconstruction | PARTIAL | Workload/results are documented, but benchmark SQL/data are external and paths must be supplied. |
| DMV availability/reconstruction | PARTIAL | Workload location and results are documented; data/workload reconstruction is not packaged end to end. |
| Frozen result artifacts | READY | Machine-readable JSON/CSV/Markdown evidence is committed and frozen. |
| Deployment artifacts | READY | Census and DMV deployment/fresh-validation outputs and scripts are retained. |
| Provenance caveats | READY | Frozen/fresh boundary and unrecoverable DMV paired drift are explicit. |

## Overall status

**PARTIAL.** The repository is public, evidence-rich, and frozen, but artifact-review readiness still requires a current top-level status, consolidated environment/setup instructions, runtime/storage expectations, and explicit workload acquisition or reconstruction steps. This audit does not start that engineering work.
