# PVLDB supplemental manifest

This manifest points to secondary evidence at the immutable `research-freeze-v0` baseline where applicable. It does not replace evidence visible in the main paper.

| Intended supplemental item | Source artifact | Connected main-paper claim | Why secondary | Reproducibility location | Frozen |
|---|---|---|---|---|---|
| Extended semantic fixtures | Native replay, FD, and ScalarArray experiment results | Replay fidelity in the supported fragment | Main paper retains aggregate comparisons and maximum errors | `results/` semantic-validation artifacts | Yes |
| Complete search and terminal audit traces | Census and DMV optimizer outputs | Neighborhood-local termination and restricted exact recovery | Full move traces are too detailed for the paper | `results/` optimizer and move-audit artifacts | Yes |
| Maintenance-fit diagnostics | Census and DMV ANALYZE cost-model outputs | Mechanism-weighted maintenance constraint | Main paper retains coefficients, scope, and prediction errors | `results/` analyze-cost artifacts | Yes |
| Repeated-ANALYZE distributions | Census robustness outputs | Same-realization replay fidelity under payload variation | Main paper retains 14,040/14,040 and the drift qualification | `results/` repeated-analyze artifacts | Yes |
| Locality and per-query dependency traces | Locality and semantic-move-pruning outputs | Safe local invalidation despite global connectivity | Main paper retains giant-component and global-budget limits | `results/` locality/incremental artifacts | Yes |
| Payload schemas and per-query replay traces | Frozen payload repositories and replay outputs | Executable semantics and realization boundary | Detailed schemas/traces support reproduction rather than argument comprehension | repository tools/results at `research-freeze-v0` | Yes |
| Extended deployment diagnostics | Census/DMV deployment outputs | Fresh native/replay fidelity and payload drift distinction | Main paper retains materialization, consumption, fidelity, and provenance limitations | `results/` deployment artifacts | Yes |

No main-paper claim depends solely on this supplemental material. No large frozen artifact is duplicated here.
