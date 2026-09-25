# DMV-Candidate-Maintenance-Cost-v0

## Outcome

The preregistered candidate repeatability gate failed. All 71 authoritative candidate definitions were measured in an isolated calibration database using one warmup pair and 21 measured alternating-order pairs. Of 3,124 recorded `ANALYZE` executions, none was invalid. Only 27/71 candidates passed: 9/36 MCV and 18/35 FD. One FD point estimate was negative and was retained without clipping.

Because the complete cost vector was not repeatable, the preregistered protocol skipped multi-candidate validation. Candidate-specific additivity, normalization, and budget translation are therefore not established. No optimizer or deployment was run.

## Descriptive candidate estimates

All values below are paired marginal milliseconds.

| Mechanism | n | Min | p10 | p25 | Median | Mean | p75 | p90 | Max | SD | CV |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| MCV | 36 | 0.685 | 1.366 | 2.805 | 4.030 | 4.164 | 5.334 | 6.735 | 9.594 | 2.127 | 51.07% |
| FD | 35 | -1.461 | 2.688 | 3.944 | 5.205 | 5.843 | 7.674 | 9.741 | 15.636 | 3.462 | 59.25% |

Median 95% CI half-width was 2.427 ms for MCV and 2.973 ms for FD; overall p90 was approximately 5.65 ms and maximum 14.74 ms. The failed vector cannot be used for budget accounting.

## Classification and next action

**BLOCKED — Measurement model cannot be established.** The exact single-candidate subtraction is too small relative to paired timing variability for most candidates under this protocol.

Recommended next action: stop this path and obtain Author/PI approval for a separately preregistered higher-signal measurement design (for example, replicated-candidate or differential batching with an independently justified estimator) before attempting candidate-level costs again.
