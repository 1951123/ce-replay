# DMV-Candidate-Maintenance-Cost-v0 preregistration

Frozen before any candidate-specific timing on 2026-09-24.

- Isolation: create `dmv_candidate_cost_v0` in the dedicated instrumented PostgreSQL 16.14 cluster and independently load the same DMV CSV. Never connect to or modify authoritative `dmv_nonzero_rebuild_v0` during timing.
- Universe: exactly the 36 payload-bearing MCV and 35 payload-bearing FD definitions recorded in `results/dmv_nonzero_truth_rebuild_v0/baseline.json`.
- Target and command: statistics target 100; time complete `ANALYZE dmv` with `time.perf_counter_ns()`.
- Candidate order: ascending SHA-256 of `DMV-Candidate-Maintenance-Cost-v0|candidate|<candidate-id>`, candidate ID as tie-break.
- Per candidate: one unmeasured warmup pair, then 21 measured pairs. Even pairs execute baseline then candidate; odd pairs execute candidate then baseline. Candidate CREATE/DROP time is excluded. Every execution is recorded.
- Baseline state: no extended-statistics definition. Candidate state: exactly one candidate definition. Ordinary column statistics are refreshed by every ANALYZE; no cache flushing or database reset is performed.
- Invalid run: only a PostgreSQL/process/timer failure, recorded with its reason. An invalid complete pair is replaced once at the end of that same candidate block; timings are never invalidated by magnitude.
- Estimator: paired difference `candidate_seconds - baseline_seconds`; cost is its arithmetic mean. Report median, sample SD, SE, min, max, and two-sided 95% t interval using predeclared `t(20)=2.085963`.
- Repeatability gate: every candidate must have a positive point estimate and 95% CI half-width no larger than `max(1 ms, 50% of its point estimate)`. Because all 71 costs are required, any candidate failure blocks an authoritative cost vector and skips validation timing.
- Validation candidate order: within each mechanism, ascending SHA-256 of `DMV-Candidate-Maintenance-Cost-v0|<mechanism>|<candidate-id>`.
- Validation designs: prefixes of that fixed order: MCV sizes 4, 12, 24, 32; FD sizes 4, 12, 24, 32; mixed sizes 4, 12, 24, 48 split equally by mechanism; and all 36 MCV + 35 FD. These sets are fixed before costs are observed.
- Validation timing, only if the repeatability gate passes: one warmup pair and 11 measured alternating-order pairs per design, using the same estimator (`t(10)=2.228139`).
- Additivity gate: at least 80% of designs must have absolute error no larger than `max(5 ms, 20% of measured marginal cost)`; overall MAPE must be at most 15%; and MAPE for each of MCV-only, FD-only, and mixed families must be at most 20%. No design may be removed.
- Uniform comparator: current frozen calibration's joint slopes, 4.036683651225859 ms/MCV and 6.103952995018044 ms/FD.
- C1 normalization: divide every positive candidate mean by the median MCV candidate mean. Translate the historical budget rule as 50% of the complete usable-universe normalized cost. No optimization is run.
