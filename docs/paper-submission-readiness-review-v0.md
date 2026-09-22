# Submission Readiness Review v0

## Baseline and scope

This narrow revision starts from `561b9da55c6b988a89bb98fd3b26ccf0d5d74341`, including the page-budget and final-figure work already on `main`. The new authoritative manuscript is `docs/paper-full-draft-v5-submission-ready.md`. No experiment, frozen result, figure, title, abstract, citation, section structure, or contribution was changed.

## Exact manuscript changes

### Representation clarification

- Section 5's opening contract now explicitly joins workload specialization, design parametricity, executable estimator state transitions, and the two interfaces derived from those transitions.
- Section 5.3 now says the dependency oracle is derived from executable state transitions rather than attached as post hoc metadata, and preserves the realized versus structural/counterfactual distinction.

This answers the handwritten-reimplementation objection: matching one cardinality calculation is insufficient for the stated abstraction because the representation must retain counterfactual control and state structure across hypothetical statistics designs.

### Prior-art distinction clarification

- Section 10.2 retains the established role of INUM/C-PQO and adds the causal link from the represented estimator computation to the statistics-semantic dependencies required for objective evaluation and safe move invalidation.
- Section 10.5 states the same distinction compactly without a priority claim.

No new literature evidence is required because the revision narrows and explains the already cited comparison rather than adding a factual claim about prior systems.

### Objective-boundary clarification

- Section 3 now explains that CE loss directly evaluates the statistics-sensitive information-state computation represented by CE-Replay.
- It explicitly states that plan/runtime objectives would introduce planner search, cost-model, and execution effects outside the representation; q-error is not claimed as a latency surrogate.

### DMV presentation clarification

- Table 3 retains the exact raw DMV value and marks it `[ZT]`.
- Its caption immediately explains that the preserved raw objective is dominated by two zero-truth queries, was still used for optimization, and that nonzero-truth loss is diagnostic only.
- The surrounding methodology statement still prohibits raw Census/DMV loss comparison.

### Optional RQ wording synchronization

- RQ2 is narrowed from “Does replay drive useful resource-constrained design?” to “Can replay drive resource-constrained statistics design?”
- RQ4 is narrowed from “Do interacting mechanisms survive deployment?” to “Does replay preserve interacting semantics after physical deployment?”

Their scientific questions, answers, evidence, and numbering are unchanged.

## Inherent scoped limitations

The strongest remaining objections are limitations rather than wording defects: semantics are manually engineered for a bounded PostgreSQL 16.14 fragment, candidate-payload acquisition is external, search is neighborhood-local, and the study does not establish query-runtime improvement or universal workload generality. The manuscript now makes each boundary explicit and does not claim to solve it.

## Readiness verdict

All four targeted reviewer-facing ambiguities are answered without new evidence or stronger claims. The manuscript is ready for the next venue-format/submission pass, subject to completing real author and venue metadata.
