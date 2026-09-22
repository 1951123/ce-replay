# 7. Experimental Methodology

The evaluation is organized around the four research questions rather than experiment chronology. We test semantic fidelity, maintenance-constrained design, exact incremental evaluation, and mixed-mechanism deployment on PostgreSQL 16.14. Census and DMV provide complementary candidate-query topologies and predicate semantics.

## 7.1 PostgreSQL and semantic reference

All final semantic claims target PostgreSQL 16.14. Native instrumentation exposes the statistics-sensitive estimator at the relevant raw or pre-clamp boundary, avoiding integer `EXPLAIN Plan Rows` rounding as a source of apparent semantic error. CE-Replay and native PostgreSQL are compared using the same query, statistics state, physical precedence, and payload realization. Exact source-function mappings and instrumentation details are deferred to the reproducibility appendix.

Native PostgreSQL serves as the semantic reference, not as the final inner-loop hypothetical-design evaluator. CE-Replay evaluates candidate states during optimization; native execution validates controlled cases and deployed fresh realizations.

## 7.2 Complementary workloads

Table T1 summarizes the structural dimensions relevant to the method.

**Table T1: Complementary workload and candidate structure.** Candidate degree is the number of target queries incident to one structural pair candidate. The two workloads stress different aspects of CE-Replay rather than representing a quality ranking.

| Workload | Queries | Rows | Predicate columns | Predicate character | Structural pairs | Candidate degree | Incidence | Main stress dimension |
|---|---:|---:|---:|---|---:|---|---|---|
| Census | 468 | 2,458,285 | 68 | Numeric equality/range | 2,253 | Mean 4.44; max 13 | Sparse, with a giant component | Large candidate space and sparse incremental evaluation |
| DMV | 1,965 | 11,591,877 | 9 | Categorical equality and constant `IN`/`= ANY` | 36 | Mean 497.08; median 498; max 546 | Dense/high reuse | ScalarArray semantics and dense incremental evaluation |

Census has a much larger structural pair universe and low candidate-query degree. It stresses workload-scale candidate search, sparse affected-query evaluation, mixed MCV+FD selection, and payload-realization analysis. Sparse degree does not imply global decomposition: nearly the entire Census query-candidate graph belongs to one giant component.

DMV contains more queries but only nine predicate columns and all 36 possible structural pairs among them. Its 11 table columns are text-valued, and 1,913 of 1,965 queries contain `IN`. DMV therefore stresses constant ScalarArray semantics, dense candidate reuse, independent maintenance calibration, and second-workload deployment. Its small pair universe does not provide independent evidence of Census-scale candidate-space scalability.

## 7.3 Candidates and payload realizations

For each workload, structural column pairs induce mechanism-specific MCV and FD definitions. Candidate definition count, usable payload count, and selected object count are reported separately. Census contains 2,253 pair MCV definitions; its mixed realization contains 758 usable query-applicable FD payloads. DMV contains 36 structural pairs and therefore 72 typed definitions before payload filtering. In the DMV optimization realization, all 36 MCV and 34 FD payloads are usable.

Payloads are acquired offline and frozen for hypothetical evaluation. Each reported objective comparison is tied to its payload realization. This is especially important for DMV: the baseline/non-monotonicity realization, the later internally consistent optimization realization, and the fresh deployment realization are distinct. We use their absolute objectives only within the originating realization.

The final workload-scale optimizer keeps recorded physical precedence fixed. Physical deployment creates the selected definitions in that order and runs one fresh `ANALYZE`, producing a new payload realization for same-realization replay/native validation.

## 7.4 Ground truth and objective

Ground-truth query cardinalities are supplied to the offline design process. CE-Replay does not consume them while reproducing the native estimate; the design layer uses them to compute the q-error objective defined in Section 3.

Two DMV queries have true cardinality zero. The frozen implementation retains its documented positive numerical floor, causing those two queries to dominate the raw aggregate DMV objective. We preserve that objective for optimization and deployment consistency, report nonzero-truth aggregates only as diagnostics, and do not compare raw Census and DMV objective magnitudes. No completed DMV objective is retroactively redefined.

## 7.5 Recurring-maintenance calibration

The abstract resource remains recurring statistics-maintenance cost. We instantiate it using mechanism-weighted object counts fitted independently to aggregate `ANALYZE` latency after candidate definitions exist. Object creation, candidate acquisition, replay, and optimization time are outside the measured recurring cost.

For Census, 36 configurations contribute 360 timed executions. The empty mean is 0.236111 s. Pure-mechanism first-order slopes are 1.874997 ms per MCV and 2.717261 ms per FD, with corresponding coefficients of determination 0.994936 and 0.996367. The normalized FD weight is 1.449 MCV units.

For DMV, 35 configurations contribute 245 timed executions after per-configuration warm-up. The empty mean is 0.114857189 s. Pure-mechanism slopes are 4.101326 ms per MCV and 5.759152 ms per FD. The combined mechanism-aware model estimates 3.903845 ms per MCV and 5.907345 ms per FD, has coefficient of determination 0.974868, and yields a normalized FD weight of 1.51321194083715. Its RMSE is 44.8187% lower than the uniform-count model.

These fits are first-order resource proxies in their measured environments. They neither define PostgreSQL's universal `ANALYZE` cost function nor estimate candidate-specific latency.

## 7.6 Figure F3 data specification

**Figure F3: Mechanism-aware recurring ANALYZE cost.** Plot Census and DMV in separate panels using `results/census_analyze_cost_model_v0.csv` and `results/dmv_analyze_cost_model_v0.csv`. The horizontal axis shows deployed mechanism counts/composition; the vertical axis shows aggregate `ANALYZE` latency. Each panel has separate MCV and FD fits and reports its own coefficients and fit quality. No regression line is shared across workloads.

**Intended takeaway.** Aggregate `ANALYZE` latency is approximately first-order in mechanism counts in both measured environments, but mechanism prices and absolute coefficients differ; the generic formulation should therefore expose maintenance cost rather than hard-code a portable coefficient.

## 7.7 Correctness and search audits

Semantic comparisons use the experiment's documented strict relative tolerance and report maximum relative error. Search correctness is calibrated in two ways: exhaustive enumeration on a five-candidate Census instance, and four restricted exhaustive DMV instances. Workload-scale searches additionally audit every feasible terminal ADD/DROP/SWAP move. These audits establish small-instance global agreement and full-instance neighborhood local optimality, respectively; they do not establish full-workload global optimality.

Incremental-evaluation experiments compare move values, accepted trajectories, and terminal states with broader control evaluation. Query replay counts, control replay counts, mechanism replay counts, evaluator latency, and complete optimizer wall time remain separate metrics.
