# DMV corrected deployment provenance

## Classification

- `optimization.json`: **diagnostic / non-authoritative for RQ2**.
- `deployment.json`: **fixed-state physical semantic validation for RQ4**.

The deployed 12-MCV + 4-FD state originates from a diagnostic optimization
performed before the DMV maintenance-cost model failed its preregistered
stability gate. The optimization and budget interpretation are retired. The
physical realization is retained only as a fixed-state semantic-fidelity test;
its replay/native equality does not depend on the validity of the selection
cost model.

Specifically, `tools/dmv_nonzero_truth_rebuild_v0.py` read the provisional
maintenance-cost model, set its FD weight, derived a budget equal to 50% of the
complete usable-universe modeled cost, and selected the state recorded in
`optimization.json`. Then `tools/dmv_nonzero_truth_deploy_v0.py` read those
selected indexes, physically created the 12 MCV and four FD objects, refreshed
their payloads, and recorded matched fresh replay/native estimates in
`deployment.json`.

Consequently, this package provides no evidence that the state is
maintenance-optimal, that the DMV cost model is valid, or that DMV has a
corrected maintenance-budget design. Census remains the sole authoritative
corrected RQ2 maintenance-constrained case. The unchanged DMV deployment
measurements remain evidence only for RQ4 semantic fidelity of the realized
fixed state.
