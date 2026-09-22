# PVLDB Supplemental Migration Plan

PVLDB Volume 20 counts in-paper appendices toward the 12-page limit. The classifications below therefore distinguish supplemental material from an in-paper appendix. No material is moved in this baseline.

| Content | Current section | Classification | Claim supported | Claim remains supported if moved? | Main-paper summary that must remain | Destination | Estimated relief | Reviewer risk |
|---|---|---|---|---|---|---|---|---|
| Full controlled MCV, FD, and ScalarArray fixture inventory | 8.1 / T2 | SHOULD MOVE TO SUPPLEMENTAL | Supported-fragment semantic fidelity | Yes, if T2 retains one row per semantic family and both deployments | Comparison counts, all-match result, maximum error, supported scope | Supplemental semantic-validation appendix | 0.25--0.5 page | Low |
| Exhaustive five-candidate Census and four restricted DMV traces | 6.1, 7, 8.2 | SHOULD MOVE TO SUPPLEMENTAL | Small-instance exact recovery | Yes | Exact-recovery statement and instance count | Supplemental optimization audit | 0.15--0.25 page | Low |
| Full terminal ADD/DROP/SWAP move enumerations | 6.1, 8.2 | SHOULD MOVE TO SUPPLEMENTAL | Neighborhood-local optimality | Yes | Neighborhood definition, terminal move totals, and local-only qualification | Supplemental search audit | 0.15--0.25 page | Low |
| Extended maintenance fits, residuals, configurations, and budget curves | 7, 8.2, 9.4 | SHOULD MOVE TO SUPPLEMENTAL | Mechanism-dependent first-order maintenance resource | Yes | F3 core fits, environment-specific warning, selected-design budget/cost, prediction errors | Supplemental maintenance appendix | 0.3--0.5 page | Low--medium |
| Repeated-`ANALYZE` distributions and per-realization payload detail | 8.4, 9.5 | SHOULD MOVE TO SUPPLEMENTAL | Same-realization fidelity under payload variation | Yes | 30-realization/14,040-match result and no ranking-stability claim | Supplemental realization appendix | 0.15--0.3 page | Low |
| Supplementary candidate-degree, connectivity, and locality statistics | 6.2, 7, 8.3 | SHOULD MOVE TO SUPPLEMENTAL | Local invalidation despite Census giant component | Yes | Mean/max degree, giant-component fact, and global budget-exchange channel | Supplemental locality appendix | 0.2--0.4 page | Medium |
| Additional realized versus structural dependency traces | 5.3, 6.2 | SHOULD MOVE TO SUPPLEMENTAL | Counterfactual-safe invalidation | Yes | Definitions and audited move-equivalence result | Supplemental semantic trace appendix | 0.2--0.4 page | Medium |
| Implementation-specific payload schemas and catalog examples | 3, 5, 9.6 | ARTIFACT-ONLY | Reproducible implementation boundary | Yes | Key-order/availability/precedence requirements | Repository documentation | 0.2--0.4 page | Low |
| Full incremental trajectories and timing breakdowns | 8.3 / T4 | SHOULD MOVE TO SUPPLEMENTAL | Exact move preservation and runtime caveat | Yes | Accepted-trajectory equivalence, work reductions, and mixed slowdown | Supplemental performance appendix | 0.25--0.5 page | Medium |
| Raw command transcripts and environment logs | Artifact only | ARTIFACT-ONLY | Reproduction | Yes | Environment summary and link | Public repository | None currently | Low |
| Duplicate prose that repeats complete table rows | 8 | DROP AS DUPLICATIVE | Reader interpretation | Yes | One question/evidence/qualification paragraph per RQ | None | 0.25--0.5 page | Low |

## Must stay in the main paper

- At least one direct fidelity result for each supported semantic family and both fresh deployments.
- Figure F2's non-monotonicity evidence, including harmful additions and improving removals.
- Maintenance-constrained selected designs, loss, feasibility, and neighborhood-local scope.
- T4's separation of exactness, semantic-work reduction, and the mixed wall-clock slowdown.
- Directed MCV-to-FD composition and deployed FD consumption.
- The semantic replay error versus fresh-payload drift distinction.
- Census giant connectivity, the global budget-exchange channel, DMV zero-truth distortion, missing DMV frozen provenance, external payload acquisition, and local-not-global guarantees.

An in-paper appendix is not recommended at the measured baseline: non-reference content already extends approximately a quarter page beyond page 12. Supplemental material is viable only where the core claim remains independently verifiable from the main paper.
