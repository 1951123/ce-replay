# Appendix Migration Plan

This plan classifies material for the next figure/appendix/format pass. No evidence has been moved from the polished manuscript.

## Must stay in the main paper

- The two independent reasons for selection: semantic interaction and recurring maintenance capacity.
- The supported PostgreSQL fragment and the design-parametric CE-Replay definition.
- The objective and statistics-semantic dependency interfaces.
- MCV selection/consumption and directed MCV-to-FD composition.
- The mathematical objective and neighborhood-local search guarantee.
- One clear result and qualification for each RQ.
- Cross-workload non-monotonicity, the mixed-evaluator slowdown, deployment fidelity, and the semantic-error/payload-drift distinction.
- The candidate-payload acquisition and realization-robustness boundaries.

## Should stay in the main paper

- Figure F1 and Figures F2–F4.
- Tables T1 and T3–T5.
- A compact version of Table T2 covering every semantic family and both deployments.
- The Census giant-component result, because it prevents interpreting locality as decomposition.
- Environment-specific maintenance-model wording and visible prediction error.
- DMV zero-truth and missing frozen-provenance caveats.

## Appendix candidates

- Full controlled MCV, FD, and ScalarArray fixture inventory behind Table T2.
- Exhaustive five-candidate Census and four restricted DMV search traces.
- Full terminal ADD/DROP/SWAP neighborhood audits.
- Extended maintenance-model configurations, fit diagnostics, and budget curves.
- Detailed repeated-`ANALYZE` payload and objective distributions.
- Supplementary candidate-degree, connectivity, and locality statistics.
- Additional semantic traces illustrating realized versus structural/counterfactual dependencies.
- Implementation-specific payload schemas and catalog precedence examples.
- Full incremental trajectory comparisons and per-phase timing breakdowns.

Negative findings must remain summarized in the main text even when their supporting distributions or traces move.

## Reproducibility/artifact only

- Raw command transcripts and environment setup logs.
- Complete machine-readable candidate/payload repositories.
- Per-query replay traces not selected as explanatory examples.
- Intermediate exploratory experiment outputs superseded by frozen artifacts.
- Claim/evidence audit machinery and full terminal move enumerations after their headline checks are reported.

## Recommended next pass

Keep all nine main artifacts provisionally. Typeset first, then migrate supporting rows, traces, and distributions only where page pressure is demonstrated. Do not estimate a final page count from Markdown word count alone.
