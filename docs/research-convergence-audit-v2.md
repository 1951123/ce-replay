# Research-Convergence-Audit-v2

## 1. Frozen problem and audit verdict

The paper studies **resource-constrained statistics physical design for a supplied target workload**:

> Given a database, a fixed target workload, a candidate space of extended statistics, and a recurring statistics-maintenance budget, choose a physical statistical state that minimizes cardinality-estimation loss on the supplied target workload.

The workload is an input, not a training set. The project does not need unseen-workload generalization to establish its primary result.

The evidence now supports all four frozen RQs within an explicit PostgreSQL 16.14 base-restriction boundary. DMV materially closes the second-workload gap identified by v1: it repeats the semantic, non-monotonicity, maintenance-model, optimization, incremental-evaluation, composition, physical-realization, and fresh-native-validation chain in a workload that differs in size, incidence density, predicate form, data type, and fitted maintenance coefficients. The DMV frozen-to-fresh per-query drift distribution remains unavailable because of artifact/provenance incompleteness; this does not invalidate its fresh semantic comparison.

No blocking core experiment remains. Census and DMV database experimentation should remain frozen, and a third workload is not required before paper drafting.

## 2. Two independent motivations

### Motivation A — semantic necessity of selection

The defensible claim is empirical and mechanism-specific:

> Native extended-statistics consumption semantics can make target-workload CE loss non-monotone in statistics-set inclusion.

- **Census:** empty loss 11,808.960379; all-statistics loss 10,932.295550; optimized strict-subset loss 805.316472 in the frozen non-monotonicity realization. Of 3,011 singleton additions to empty, 1,444 improve, 7 are neutral, and 1,560 worsen loss. Removing 317 individual objects from the all-statistics design improves loss. The strongest harmful addition, `MCV:671`, raises loss by 1,917.260269.
- **DMV baseline realization:** empty/all-MCV/all-FD/all-mixed losses are 87,276.581132 / 92,850.151303 / 95,404.855146 / 92,850.151303. Of 70 usable singleton additions, 25 improve and 45 worsen. Seventeen removals from all improve loss. All MCVs consume, while all 34 usable FDs are suppressed.

These are concrete witnesses, not a theorem that PostgreSQL statistics are universally non-monotone.

### Motivation B — resource necessity

Extended statistics impose recurring collection/refresh work during `ANALYZE`; the core resource is therefore **recurring statistics maintenance cost**.

- **Census:** pure first-order slopes are 1.874997 ms/MCV and 2.717261 ms/FD, giving normalized FD/MCV ratio 1.449. The mechanism-specific fit has R² 0.994751 and median relative error 2.82%.
- **DMV:** the combined fit is 3.903845 ms/MCV and 5.907345 ms/FD, normalized ratio 1.51321194083715, R² 0.974868, RMSE 12.605940 ms. Full-MCV, full-FD, and full-mixed prediction errors are 4.3540%, 2.0676%, and 3.7133%. The final deployment prediction error is 21.4295%.

Thus mechanism-weighted object count is a useful first-order resource proxy in the measured environments, not a portable high-precision latency model. Serialized payload bytes are retained only as an earlier controlled proxy.

## 3. Technical thesis, decomposed

| Element | Verdict | Evidence boundary |
|---|---|---|
| Semantic representation | Supported | Source-guided, workload-specialized executable representation of supported PostgreSQL 16.14 statistics-sensitive base restrictions. |
| Numerical fidelity | Supported | Native raw comparisons on Census, synthetic ScalarArray/FD cases, real DMV, and both fresh deployments. |
| Design-parametric execution | Supported | Eligibility, GreedyCover, consumption, precedence, and payload availability remain design-dependent. |
| Compositional MCV+FD semantics | Supported | MCV-consumed clauses feed FD applicability; independent optimization can select suppressed FDs. |
| Objective evaluation | Supported | Replay evaluates complete fixed-workload q-error objectives without a learned response predictor. |
| Dependency-aware incremental moves | Supported | Exact audited move values/trajectories with reduced control replay on sparse Census and dense DMV. |
| Resource-constrained optimization | Supported | Exhaustive small cases, restricted exact DMV audits, and workload-scale local optimization. |
| Physical deployment | Supported with asymmetric limitation | Both designs physically realized and fresh-native validated; only Census has complete paired numerical drift evidence. |

## 4. Complete experiment inventory

The machine-readable inventory is in [`research-evidence-matrix-v2.json`](../results/research-evidence-matrix-v2.json). It contains **39 experiments/audits**: the 28 v1 entries plus 11 subsequent entries. No historical experiment was deleted.

| # | Experiment | Workload | Role | Paper placement |
|---:|---|---|---|---|
| 1 | Census locality analysis | Census | NEGATIVE RESULT | Appendix |
| 2 | Creation/OID-order probe | Census | SUPPORTING | Main-text short result |
| 3 | First-applicable pilot | Census | NEGATIVE RESULT | Appendix |
| 4 | MCV consumption/composition | Census | SUPPORTING | Appendix |
| 5 | CE-Replay-IR-v0 | Census | SUPERSEDED | Omit |
| 6 | CE-Replay-IR-v1-A | Census | SUPERSEDED | Appendix/history |
| 7 | CE-Replay-IR-v1-B | Census | CORE | Main table |
| 8 | CE-Replay-Optimize-v0 | Census | CORE | Main short result |
| 9 | CE-Replay-Optimize-v1 | Census | CORE | Main table |
| 10 | CE-Replay-Optimize-v2 | Census | NEGATIVE RESULT | Appendix |
| 11 | CE-Replay-Optimize-v3 | Census | SUPPORTING | Appendix |
| 12 | MCV-Deploy-v0 | Census | SUPPORTING | Appendix |
| 13 | FD-Semantics-v0 | Synthetic/Census | CORE | Main table |
| 14 | CE-Replay-Optimize-v4 | Census | CORE | Main table |
| 15 | CE-Semantic-State-v0 | Census | NEGATIVE RESULT | Appendix |
| 16 | MCV-Commutativity-v0 | Synthetic/Census | NEGATIVE RESULT | Appendix |
| 17 | MCV-Semantic-Factorization-v0 | Synthetic/Census | NEGATIVE RESULT | Appendix |
| 18 | Semantic-Move-Pruning-v0 | Census | SUPPORTING | Appendix |
| 19 | Semantic-Optimizer-v0 | Census | CORE | Main table |
| 20 | Compositional-Semantic-Optimizer-v0 | Census | CORE | Main table |
| 21 | Mixed-Deploy-v0 | Census | SUPPORTING | Appendix |
| 22 | Research-Synthesis-v0 | Project | ENGINEERING / PROVENANCE | Omit |
| 23 | Repeated-Analyze-Robustness-v0 | Census | ROBUSTNESS | Appendix |
| 24 | Workload-Generalization-v0 | Census | FUTURE-WORK ARCHIVE | Omit |
| 25 | Generalization-Mechanism-Analysis-v0 | Census | FUTURE-WORK ARCHIVE | Omit |
| 26 | Budget-Generalization-Curve-v0 | Census | FUTURE-WORK ARCHIVE | Omit |
| 27 | Census structural-group audit | Census | FUTURE-WORK ARCHIVE | Omit |
| 28 | Structural-Distance-Generalization-v0 | Census | FUTURE-WORK ARCHIVE | Omit |
| 29 | Statistics-Nonmonotonicity-v0 | Census | CORE | Main figure/table |
| 30 | Analyze-Cost-Model-v0 | Census | CORE | Main figure |
| 31 | Maintenance-Budget-Optimize-v0 | Census | CORE | Main table |
| 32 | Maintenance-Design-Deploy-v0 | Census | CORE | Main table |
| 33 | DMV-Fit-Audit-v0 | DMV | SUPPORTING | Main short result |
| 34 | MCV-ScalarArray-Semantics-v0 | Synthetic/Census/DMV | CORE | Main table |
| 35 | DMV-Baseline-and-Nonmonotonicity-v0 | DMV | CORE | Main figure/table |
| 36 | DMV-Analyze-Cost-Model-v0 | DMV | CORE | Main figure |
| 37 | DMV-Maintenance-Budget-Optimize-v0 | DMV | CORE | Main table |
| 38 | DMV-Deploy-v0 | DMV | CORE | Main table, limitation footnote |
| 39 | DMV-Frozen-Provenance-Recovery-v0 | DMV | ENGINEERING / PROVENANCE | Appendix |

Each record in the JSON includes purpose, semantic scope, result type, strongest supported claim, strongest unsupported overclaim, role, placement, and status.

## 5. Claim × workload evidence matrix

| Claim | Census evidence | DMV evidence | Status | Safe wording | Forbidden wording |
|---|---|---|---|---|---|
| C1 Native replay fidelity | v1-B, FD, deployments | ScalarArray, 27,510 comparisons, fresh 1,965 | Both supported | Matches native inside supported fragment | Replays all PostgreSQL CE |
| C2 Set non-monotonicity | 1,560 harmful additions; 317 improving removals | 45 harmful additions; 17 improving removals | Both supported | Can be non-monotone | Always non-monotone |
| C3 Selection without scarcity | All worse than strict subset | Same 50/75/100% solution leaves capacity unused | Both supported | May reject statistics with nonbinding budget | More budget always helps |
| C4 ANALYZE maintenance model | First-order mechanism fit | Independent first-order fit | Both supported | Useful measured proxy | Precise universal model |
| C5 Coefficients environment-specific | Ratio 1.449 | Ratio 1.5132 | Both supported | Form transfers; coefficients differ | Portable coefficient |
| C6 Resource model changes design | Direct byte-versus-maintenance comparison | No direct proxy comparison | Census only | Material change on Census | Demonstrated on DMV |
| C7 MCV→FD composition | Joint versus independent | All-MCV suppresses FD | Both supported | MCV consumption affects FD applicability | Mechanisms independent |
| C8 Restore useful FD consumption | Joint/maintenance subsets consume selected FD | 0 all-design FD vs 12 optimized, 11 fresh | Both supported | Subsets restore FD reachability | Every selected object always consumes |
| C9 Incremental evaluation | Exact trajectories; large replay reductions | 67.91% query replay avoided | Both supported | Less control work with exact audited moves | Always wall-clock faster |
| C10 Sparse locality | Mean degree 4.44 | Mean degree ≈497 | Census-specific | Census incidence is sparse | Locality universally sparse |
| C11 Dense utility | N/A | Dense optimization/incremental audit | DMV-specific | Useful in dense small universe | Proves Census-scale scalability |
| C12 Search optimality | Small exhaustive; workload local optimum | 4/4 restricted exact; workload local optimum | Both supported | Local optimum under audited neighborhood | Full global optimum |
| C13 Physical deployment | Realized; fresh 468/468 | Realized; fresh 1,965/1,965 | Both supported | Physical/fresh semantic closure | Symmetric drift evidence |
| C14 Payload drift | Paired and repeated numerical evidence | Aggregate/structural only | Partial/asymmetric | DMV paired distribution unavailable | DMV paired drift distribution exists |
| C15 ScalarArray extensibility | 128/128 regression | 29/29 synthetic; coverage 100% | DMV extension supported | Bounded source-derived extension | Arbitrary predicates automatic |
| C16 General CE coverage | Unsupported | Unsupported | Unsupported | Supported PG16.14 fragment only | Full PostgreSQL CE |

The corresponding machine-readable claim matrix is [`paper-claim-matrix-v0.json`](../results/paper-claim-matrix-v0.json).

## 6. Final Census evidence summary

### Semantic fidelity

MCV v1-B evaluated four targets × 32 designs with maximum relative error (5.55\times10^{-16}). FD node/workload validation and mixed composition extended this boundary. The maintenance-budget fresh deployment matched 468/468 native estimates within (10^{-12}), maximum relative error (6.92\times10^{-16}), with identical fresh replay/native aggregate loss.

### Non-monotonicity

Within the non-monotonicity frozen realization: empty 11,808.960379; all 10,932.295550; existing optimized mixed subset 805.316472. Singleton counts are 1,444 beneficial, 7 neutral, 1,560 harmful; 317 all-design removals improve. These figures are paired only within that realization.

### Maintenance and optimization

The current-environment slopes are approximately 1.875 ms/MCV and 2.717 ms/FD, normalized ratio 1.449. The matched old-design capacity is (B=286.144). The maintenance-budget search selects **276 MCV + 7 FD**, modeled cost 286.143, frozen loss **787.809381**. Against the old 205+56 byte-budget design, typed Jaccard is 42.7822%, with 120 additions and 98 removals; loss improves 2.1739% in the shared frozen context. All seven selected FDs consume. Terminal audit covers 565,031 feasible moves and establishes tested-neighborhood local optimality, not global optimality.

### Deployment and incremental evaluation

The 276+7 design was created in verified order and analyzed once. Predicted/observed ANALYZE latency was 0.773682/0.829417 s (7.20% error). Frozen/fresh replay/native loss was 787.809381/811.553725/811.553725; paired payload drift was 3.0140%, while semantic error was zero at aggregate precision. All 276 MCV and 7 FD payloads materialized and consumed.

MCV incremental search preserved a 17-move trajectory and terminal round, with 171.31× fewer control replays and 3.51× phase speedup. Mixed incremental evaluation preserved 19 moves and reduced control work, but took 145.68 s versus 45.05 s for the control implementation. Therefore the contribution is exact dependency-aware move evaluation and control-work reduction, not universal end-to-end speedup; numerical aggregation remains an implementation bottleneck.

## 7. Final DMV evidence summary

### Structural difference and semantic extension

DMV has **1,965 queries**, nine predicate columns, all 36 possible structural pairs, and an IN-heavy categorical workload: 1,913 queries contain `IN`. Candidate degree min/median/mean/max is 461/498/497.08/546, versus Census mean 4.44. The universe is much smaller but far denser and more reused.

The source-derived ScalarArray extension validates constant `IN`/`= ANY` evaluation directly over MCV items. It passes 29/29 synthetic cases (maximum row relative error (4.38\times10^{-15})), preserves 128/128 scalar regressions, and raises canonical DMV coverage from 52/1,965 to 1,965/1,965. This does not cover arbitrary operators, nonconstant arrays, OR/NOT, joins, or parameterized clauses.

### Fidelity and non-monotonicity

In the baseline realization, native/replay passed 27,510/27,510 comparisons, maximum relative error (1.40286\times10^{-14}). Empty/all-MCV/all-FD/all-mixed losses are 87,276.581132 / 92,850.151303 / 95,404.855146 / 92,850.151303. Singleton MCV counts are 19 beneficial and 17 harmful; FD counts are 6 beneficial and 28 harmful. Seventeen removals from all improve. All 36 MCVs consume; zero of 34 usable FDs consume.

The later optimization uses a **new internally consistent realization** because the baseline artifact lacked clause-level simple selectivities. Its absolute losses must not be paired with the baseline values.

### Maintenance model and optimization

The independent combined model fits 3.903845 ms/MCV and 5.907345 ms/FD, ratio 1.51321194083715, R² 0.974868. The final deployment prediction error of 21.4295% limits this to a first-order resource proxy.

The optimization realization has 36 usable MCV and 34 usable FD objects, full cost 87.449206, and primary 50% budget 43.724603. The selected design is **11 MCV + 12 FD**, cost 29.158543, unused budget 14.566060. The same design/loss persists at 75% and 100%, demonstrating that added capacity does not force harmful/unhelpful objects. At 25%, it selects 11+7. Four restricted audits recover 4/4 exact optima within (10^{-12}) relative tolerance. The full result is locally optimal under 47 ADD, 23 DROP, and 1,081 SWAP terminal moves; it is not globally proven.

The optimized objective is approximately (7.84\times10^{298}) because `dmv.173` and `dmv.943` have zero truth and the unchanged (10^{-300}) floor dominates. Raw aggregate DMV q-error must not be compared to Census. The nonzero-truth aggregate is a diagnostic, not the optimized objective.

### Dense incremental evaluation and deployment

Candidate degree mean/median/p90/max is 497.13/498/520/546. Exact dependency-aware evaluation avoids 67.91% of full-workload query replay operations. This demonstrates usefulness under dense incidence, not Census-scale search scalability or wall-clock speedup.

The authoritative 11+12 design and recorded order were physically realized; exactly one fresh ANALYZE ran. All 11 MCV payloads and 11/12 FD payloads materialized; all materialized objects consumed, and 389 queries consumed FD. Fresh replay/native passed 1,965/1,965, maximum relative error (2.43422\times10^{-14}); fresh nonzero-truth diagnostic loss is 85,014.808346. The cost-model prediction/observation was 0.238646/0.303735 s.

The original optimization artifact did not persist frozen per-query estimates, baseline rows, clause selectivities, q-errors, or sufficient inputs to reconstruct them. Consequently no paired frozen-to-fresh per-query estimate-drift distribution, frozen zero-query contribution, or frozen nonzero-truth diagnostic can be claimed. This is **artifact/provenance incompleteness**, not semantic correctness failure. The exact deployment, fresh payload materialization/consumption, structural trace changes, and fresh replay/native comparisons remain independently supported.

## 8. Cross-workload replication table

| Dimension | Census | DMV |
|---|---|---|
| Workload structure | SUPPORTED: 468-query sparse numeric regime | SUPPORTED: 1,965-query dense categorical regime |
| Predicate semantics | SUPPORTED: scalar equality/range fragment used by workload | SUPPORTED: equality plus constant IN/=ANY |
| Candidate topology | SUPPORTED: 2,253 sparse pair MCV candidates plus FD universe | SUPPORTED: 36 dense structural pairs, 70 usable typed objects in optimization realization |
| Replay fidelity | SUPPORTED | SUPPORTED |
| Non-monotonicity | SUPPORTED | SUPPORTED |
| Maintenance model | SUPPORTED | SUPPORTED, first-order only |
| Maintenance-aware optimization | SUPPORTED | SUPPORTED |
| MCV+FD composition | SUPPORTED | SUPPORTED |
| Incremental evaluation | SUPPORTED | SUPPORTED, weaker savings |
| Exhaustive audit | SUPPORTED on 5-candidate instance | SUPPORTED on four restricted instances |
| Physical deployment | SUPPORTED | SUPPORTED |
| Fresh native validation | SUPPORTED, 468/468 | SUPPORTED, 1,965/1,965 |
| Paired payload-drift audit | SUPPORTED | BLOCKED BY PROVENANCE |

DMV constitutes meaningful external replication because it changes multiple causal dimensions—not merely the dataset name—while preserving the architecture. It does not reproduce Census-scale candidate-space size and therefore does not independently validate that scalability dimension.

## 9. Four RQ verdicts

- **RQ1 — SUPPORTED WITHIN CURRENT BOUNDARY.** Census MCV/FD, ScalarArray fixtures, and real DMV reproduce native raw estimates to reported floating-point tolerances inside the explicit fragment.
- **RQ2 — SUPPORTED WITHIN CURRENT BOUNDARY.** Replay drives resource-constrained fixed-workload design without a learned q-error response model. Small/restricted exact audits validate correctness; workload-scale results are local optima.
- **RQ3 — SUPPORTED WITHIN CURRENT BOUNDARY.** Source-derived dependency/state supports exact audited incremental moves in sparse Census and dense DMV. This is a control-work claim, not a universal runtime-speedup claim.
- **RQ4 — SUPPORTED WITHIN CURRENT BOUNDARY.** Both workloads demonstrate interacting MCV+FD semantics, physical realization, and fresh replay/native fidelity. DMV's missing paired frozen per-query vector limits realization-stability analysis, not fresh semantic validation.

## 10. Negative results retained

| Finding | Placement | Why retain |
|---|---|---|
| Census giant component / no component decomposition | Appendix | Prevents interpreting sparse degree as objective decomposition. |
| Locality-only search incomplete under budget exchange | Main short result or appendix | Explains why locality accelerates evaluation rather than restricting the neighborhood. |
| Restart-safe state compression failure | Appendix | Justifies retaining extension-relevant state. |
| Commutativity does not shrink outer design space | Appendix | Rules out an obvious partial-order-reduction claim. |
| No nontrivial Census semantic factorization | Appendix | Bounds factorization claims. |
| Mixed evaluator reduces control work without wall-clock gain | Main limitations | Directly bounds RQ3 performance wording. |
| DMV dense incidence weakens locality savings | Main comparison | Strengthens the sparse/dense external-validity argument. |
| DMV provenance failure | Appendix plus main limitation | Prevents an incorrect paired-drift claim. |
| First-applicable proxy failure | Appendix | Documents why executable control semantics are needed. |

Detailed chronological prototypes, generalization exploration, and duplicated early deployment results should be omitted from the main paper.

## 11. Generalization and positioning

All workload-generalization experiments remain future/supporting archive. Existing Census held-out analyses were repeatedly inspected and must not be presented as an untouched final test set for a newly introduced generalization-aware method. The core vocabulary is target workload/input, not train/test.

Learned CE changes or learns an estimator; this project optimizes the physical statistical state consumed by a fixed native DBMS estimator. CE-Replay is not learned CE.

The work is physical design: indexes alter optimizer action/plan space, whereas statistics alter optimizer beliefs/cardinality estimates. The related-work analogy is that what-if/INUM-style methods specialize optimizer plan/cost response, while CE-Replay specializes statistics-sensitive CE response. This is positioning, not experimental proof.

## 12. Exact supported boundaries

### Semantic boundary

> The system replays the supported statistics-sensitive base-restriction CE fragment of PostgreSQL 16.14 for conjunctive workloads, covering validated scalar predicates and constant ScalarArray `IN`/`= ANY`, multicolumn MCV, equality-eligible functional dependencies, MCV-first clause consumption feeding FD applicability, and PostgreSQL-specific creation/OID precedence where relevant, for a supplied payload snapshot.

It does not cover joins, parameterized paths, arbitrary expressions/operators, OR/NOT trees, complete planner search, other extended-statistics mechanisms, arbitrary PostgreSQL versions, or all PostgreSQL CE.

### Optimization guarantee

The workload-scale solver provides deterministic resource-constrained search, exact objective evaluation within the replay boundary, exact audited move evaluation, and a local optimum under the tested ADD/DROP/SWAP neighborhood when terminal audit is performed, for fixed payload and precedence. Only the five-candidate Census instance and restricted DMV subproblems have exhaustive global-optimum evidence. There is no full Census/DMV global-optimality or arbitrary-precedence guarantee.

### Resource-model boundary

The abstract resource is recurring statistics maintenance cost. The empirical instantiation is a mechanism-weighted count model fitted to aggregate ANALYZE latency. Census and DMV have distinct coefficients. It is not a payload-byte identity, candidate-specific marginal latency model, or portable precise predictor; DMV's 21.4295% deployment error must be reported.

### Deployment boundary

- **Census:** physical realization, fresh semantic fidelity, and paired frozen-to-fresh numerical stability are supported for the maintenance-budget deployment.
- **DMV:** physical realization and fresh semantic fidelity are supported; paired frozen-to-fresh per-query numerical stability is unavailable because required frozen provenance was not persisted.

### Candidate acquisition and objective boundaries

The optimizer assumes payloads from an offline candidate-acquisition process; it does not provide a zero-cost hypothetical payload generator. One-time acquisition is distinct from recurring deployed maintenance.

DMV's two zero-truth queries make the (10^{-300})-floor q-error aggregate numerically dominant. This belongs in the main limitations section. Completed objectives must not be retroactively changed, and diagnostic nonzero-truth aggregates must be labeled diagnostic.

## 13. Minimum sufficient evidence chain

The minimum paper chain is:

1. **E1 Selection exists:** cross-workload non-monotonicity.
2. **E2 Resource constraint exists:** independent Census and DMV ANALYZE calibration.
3. **E3 Native semantics can be replayed:** v1-B, FD, ScalarArray, and real-workload fidelity.
4. **E4 Replay drives correct optimization:** five-candidate Census exhaustive agreement and four restricted DMV exact recoveries.
5. **E5 Workload-scale design:** Census large sparse and DMV small dense maintenance-budget optimization.
6. **E6 Semantic dependencies help:** exact incremental evaluation across sparse and dense incidence.
7. **E7 Composition matters:** MCV→FD suppression/restoration evidence.
8. **E8 Designs survive deployment:** Census and DMV physical realization plus fresh-native validation, with asymmetric drift evidence stated.

Early IR versions, MCV-only deployments, intermediate search refinements, and generalization experiments are not necessary to the core narrative.

## 14. Proposed compact figures and tables

| Item | Purpose | Sources | Axes/columns | Core claim |
|---|---|---|---|---|
| Fig. 1 System pipeline | Explain architecture | IR docs, optimizer/deploy artifacts | Workload/payload → replay → dependency oracle → search → deploy | Separation of semantics and search |
| Table 1 Workload contrast | Establish external validity | locality, DMV fit audit | queries, columns, pairs, degree, predicates, types | Sparse Census versus dense IN-heavy DMV |
| Fig. 2 Non-monotonicity | Motivate selection | two non-monotonicity experiments | design/context and loss/count outcomes | Adding statistics can worsen loss |
| Table 2 Replay fidelity | Establish RQ1 | v1-B, FD, ScalarArray, deployments | cases, comparisons, max error, trace matches | Native fidelity within boundary |
| Fig. 3 Maintenance calibration | Motivate budget | two cost models | object counts vs ANALYZE latency by mechanism | First-order mechanism-aware cost |
| Table 3 Optimization | Establish RQ2/RQ4 | two maintenance optimizers | budget, chosen counts/cost/loss, audits, FD consumption | Resource-aware compositional selection |
| Table 4 Incremental evaluation | Establish RQ3 | semantic optimizers, DMV optimizer | density, avoided replay, trajectory, wall time | Exact control-work reduction; timing caveat |
| Table 5 Deployment | Close loop | two final deployments | realization, materialization, fresh matches, drift availability, latency error | Physical and fresh-semantic closure |

## 15. Strongest defensible contributions

1. **Executable semantic specialization.** A source-guided, workload-specialized executable program represents the supported PostgreSQL 16.14 statistics-sensitive base-restriction fragment and matches native estimates at reported floating-point tolerance. Evidence: v1-B, FD, ScalarArray, real DMV, both deployments. Prohibited upgrade: all PostgreSQL CE or automatic source-to-IR generation.
2. **Semantic physical-design formulation.** Replay serves as objective evaluator for recurring-maintenance-constrained statistics design on a supplied workload, without a learned q-error response model. Evidence: controlled exact and both workload-scale optimizations. Prohibited upgrade: unseen-workload generalization or execution-time optimization.
3. **Exact dependency-aware move evaluation.** Source-derived semantic dependencies preserve audited ADD/DROP/SWAP move results and trajectories while reducing control replay in sparse and dense regimes. Prohibited upgrade: guaranteed end-to-end speedup.
4. **Compositional MCV+FD optimization.** MCV consumption changes FD applicability; joint subsets restore useful FD consumption that all/independent designs suppress. Prohibited upgrade: arbitrary mechanism composition.
5. **Empirical maintenance-aware resource model.** Independent mechanism-weighted aggregate ANALYZE fits provide first-order resource constraints, with different coefficients across workloads. Prohibited upgrade: universal or per-candidate costs.
6. **Cross-workload physical closure.** The architecture survives a large sparse Census universe and a smaller dense IN-heavy DMV universe through physical deployment and fresh native validation. Prohibited upgrade: DMV proves Census-scale candidate scalability or complete paired drift evidence.

## 16. Strongest limitations

- **Semantic scope:** PostgreSQL 16.14 only; conjunctive base-relation restrictions; MCV and FD only; no join CE, full planner replay, arbitrary expressions/operators, or other statistics mechanisms.
- **Optimization:** fixed payload/precedence at workload scale; local search, not full global optimization; no approximation guarantee.
- **Payloads:** offline candidate payload acquisition is assumed; no general hypothetical payload generator.
- **Resource model:** empirical, aggregate, first-order, environment-specific; DMV deployment error 21.4295%; no candidate-specific latency claim.
- **Objective:** two DMV zero-cardinality queries dominate the chosen q-error-floor objective; nonzero-truth aggregates are diagnostic only.
- **Deployment/provenance:** DMV lacks frozen per-query state needed for a paired numerical drift distribution; Census has it.
- **Outcome:** optimizes CE q-error, not execution time, plan quality, or end-user latency.
- **External validity:** two real workloads and one PostgreSQL version; DMV does not repeat Census-scale candidate-space size.
- **Generalization:** not part of the core formulation; inspected held-out Census analyses are not an untouched test set.

## 17. Claims prohibited in paper drafting

- CE-Replay exactly reproduces all PostgreSQL CE.
- The system automatically derives replay semantics from arbitrary DBMS source.
- The optimizer finds the global optimum on full Census or DMV.
- Extended statistics are always non-monotone or harmful.
- FD costs 1.449× or 1.513× MCV in PostgreSQL generally.
- Payload size equals maintenance cost.
- The maintenance model predicts every ANALYZE latency precisely or gives per-candidate cost.
- Semantic incremental evaluation always speeds up end-to-end optimization.
- DMV proves Census-scale optimizer scalability.
- DMV has a paired frozen-to-fresh per-query drift distribution.
- The system optimizes execution time or plan quality.
- The method generalizes to unseen workloads.
- All selected statistics always materialize or consume.
- More budget always improves the optimized objective.
- Candidate payload acquisition is solved.
- Candidate definitions uniquely determine payloads or estimates after fresh ANALYZE.
- OID precedence is a DBMS-generic variable or arbitrary precedence is globally optimized.
- The problem has been formally proved NP-hard.
- Raw DMV and Census aggregate q-error magnitudes are directly comparable.

## 18. Paper readiness

| Area | Verdict | Exact reason if limited |
|---|---|---|
| Problem formulation | READY | Fixed-workload maintenance-constrained design is stable and explicit. |
| Semantic correctness | READY WITH EXPLICIT LIMITATION | Exact only inside the stated PostgreSQL 16.14 fragment. |
| Optimization correctness | READY WITH EXPLICIT LIMITATION | Small/restricted exactness plus workload-scale neighborhood local optimality, not global optimality. |
| Scalability/performance evidence | READY WITH EXPLICIT LIMITATION | Census supports large sparse candidate evaluation; DMV supports dense utility; mixed wall-clock speedup is not established. |
| Resource-model evidence | READY WITH EXPLICIT LIMITATION | First-order environment-specific proxy; DMV deployment error is 21.4295%. |
| Cross-workload external validity | READY WITH EXPLICIT LIMITATION | Meaningful structural replication across two workloads, but DMV is not a large candidate-space benchmark. |
| Deployment evidence | READY WITH EXPLICIT LIMITATION | Both have physical/fresh-semantic closure; DMV paired numerical drift is blocked by provenance. |
| Limitations/provenance clarity | READY | Missing DMV state is explicitly classified and bounded. |

## 19. Required final report — 26 answers

1. **How many experiments/audits?** 39.
2. **Minimum core chain?** E1–E8 in Section 13: non-monotonicity, maintenance calibration, semantic fidelity, controlled correctness, workload-scale optimization, incremental evaluation, composition, deployment.
3. **Claims supported by both Census and DMV?** C1–C5, C7–C9, C12–C13; C14 only asymmetrically/partially.
4. **Census-only claims?** Direct byte-budget versus maintenance-budget design change; sparse affected-query locality; complete paired/repeated payload-drift quantification; large candidate-space evidence.
5. **DMV-only claims?** Validated MCV constant ScalarArray/IN extension on an IN-heavy real workload; usefulness under dense high-reuse incidence; zero-truth objective pathology in this benchmark.
6. **Negative results?** Giant component, failed first-applicable proxy, incomplete locality-only search, restart-state failure, no useful outer-space commutativity reduction, no Census factorization, mixed no wall-clock gain, dense DMV weaker locality, and unrecoverable DMV frozen provenance.
7. **Does DMV close the v1 second-workload gap?** Yes materially for the core architecture, because it changes workload size, dimensionality, density, predicate form, type, and coefficients while repeating the core chain. It does not add Census-scale candidate-space replication.
8. **Exact semantic boundary?** The PostgreSQL 16.14 conjunctive statistics-sensitive base-restriction fragment described in Section 12, including supported scalar and constant IN/=ANY MCV semantics, FD, MCV→FD composition, and relevant OID precedence.
9. **Exact optimization guarantee?** Exact objective and audited move evaluation; deterministic fixed-payload/precedence local optimum under tested ADD/DROP/SWAP; global only on small/restricted exhaustive instances.
10. **Exact maintenance claim?** Mechanism-weighted object count is a reproducible first-order aggregate ANALYZE-maintenance proxy in each measured environment; coefficients are not portable or candidate-specific.
11. **Census deployment claim?** Exact 276+7 realization/order, one ANALYZE, complete materialization/consumption, 468/468 fresh matches, and paired 3.0140% frozen→fresh loss drift.
12. **DMV deployment claim?** Exact 11+12 realization/order, one ANALYZE, 11/11 MCV and 11/12 FD payload materialization, all materialized objects consumed, 389 FD-consuming queries, and 1,965/1,965 fresh matches.
13. **What does DMV provenance failure prevent?** A paired frozen→fresh per-query estimate-drift distribution, frozen zero-query contribution, and frozen nonzero-truth diagnostic.
14. **Does it undermine fresh semantic correctness?** No. Fresh replay/native fidelity and physical composition are independently supported.
15. **Main paper results?** The compact E1–E8 chain and the eight items in Section 14.
16. **Appendix?** Order details, locality/giant component, first-applicable, state/commutativity/factorization failures, move-pruning detail, repeated ANALYZE distributions, early MCV deployment, and DMV provenance audit.
17. **Omit?** Superseded prototypes, chronological engineering records, and the generalization archive from the core paper.
18. **Strongest contributions?** The six bounded statements in Section 15.
19. **Strongest limitations?** The semantic, optimization, payload, resource, objective, deployment, outcome, external-validity, and generalization limits in Section 16.
20. **Prohibited claims?** Section 17.
21. **Any new core database experiment necessary?** No.
22. **Freeze Census experimentation?** Yes.
23. **Freeze DMV experimentation?** Yes.
24. **Third workload required?** No, not before paper drafting.
25. **Are all four RQs supported?** Yes, each is `SUPPORTED WITHIN CURRENT BOUNDARY`.
26. **Ready for paper construction?** Yes, with the stated limitations carried into abstract, evaluation, and limitations.

EXPERIMENTAL PHASE COMPLETE — READY FOR PAPER CONSTRUCTION
