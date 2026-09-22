# PVLDB Final Figure Plan v0

All roles below were recovered from the v4 manuscript, current captions, `results/paper-figure-table-role-audit-v0.json`, `docs/paper-figure-1-spec-v0.md`, and `results/paper-evaluation-figure-table-data-v0.json`. No role conflict was found.

## F1 — CE-Replay physical-design pipeline

- **Section:** 5, CE-Replay.
- **Current caption:** CE-Replay physical-design pipeline; frozen hypothetical evaluation is separated from fresh deployment and validation.
- **Question:** How do the frozen hypothetical-design loop and fresh deployment/validation loop differ, and what does CE-Replay expose?
- **Argumentative role:** Define CE-Replay as the central executable representation, distinct from the replaceable search and native PostgreSQL.
- **Claims supported:** supported native CE semantics remain design-parametric; one representation exposes objective and dependency interfaces; fresh same-realization validation is separate from frozen-to-fresh drift.
- **Frozen sources:** `docs/paper-figure-1-spec-v0.md`; manuscript Sections 3–6; role audit F1.
- **Required concepts:** fixed workload/context, offline candidate payload repository, candidate definitions, hypothetical design, MCV selection/consumption/numerical update, FD applicability/composition, objective, semantic dependencies, ADD/DROP/SWAP search, selected state, physical creation/order/ANALYZE, fresh payload, replay/native comparison, payload drift boundary.
- **Type / placement:** conceptual, double column.
- **Placeholder / target:** 6.6 × 2.20 in; target 6.6 × 2.20 in.
- **Forbidden interpretations:** automatic source compilation; full PostgreSQL/planner replay; learned q-error model; solved payload acquisition; global optimizer; equality of frozen and fresh payloads; general DBMS support.
- **Why a figure:** the two loops, feedback interfaces, and realization boundary are relational and harder to recover from linear prose.

## F2 — Cross-workload non-monotonicity

- **Section:** 8.2, RQ2.
- **Current caption:** independently scaled Census and DMV panels compare empty and complete states and annotate harmful additions/removals.
- **Question:** Can adding statistics worsen target-workload CE loss even apart from binding capacity?
- **Argumentative role:** Make non-monotone set inclusion visible in two frozen realizations without comparing raw loss across workloads.
- **Claims supported:** all-statistics is not a safe default; harmful singleton additions and improving removals exist in both workloads.
- **Frozen sources / fields:** `results/paper-evaluation-figure-table-data-v0.json`, F2 panel fields; underlying Census and DMV nonmonotonicity JSON artifacts.
- **Type / placement:** empirical, double column.
- **Placeholder / target:** 6.6 × 2.05 in; target 6.6 × 2.05 in.
- **Transformations:** source loss values become bar heights; category order is empty, mechanism-complete states, and reported optimized subset where available; source counts are direct annotations; panels retain independent y axes.
- **Forbidden interpretations:** every statistic is harmful; cross-workload loss comparison; global optimality; universal workload behavior.
- **Why a figure:** direction reversals and the contrast among empty, complete, and selected states are read faster visually than from scalar prose.

## F3 — Mechanism-aware recurring ANALYZE cost

- **Section:** 7, Experimental Methodology.
- **Current caption:** separate panels connect deployed mechanism composition to aggregate `ANALYZE` latency with environment-specific coefficients.
- **Question:** Does aggregate measured latency support a useful first-order, mechanism-aware maintenance proxy in each environment?
- **Argumentative role:** Ground the resource constraint while making non-portability explicit.
- **Claims supported:** MCV and FD have different fitted slopes; coefficients differ between Census and DMV; the proxy is first-order and environment-specific.
- **Frozen sources / fields:** `results/census_analyze_cost_model_v0.csv`; `results/dmv_analyze_cost_model_v0.csv`; F3 coefficient/R² fields in `results/paper-evaluation-figure-table-data-v0.json`.
- **Type / placement:** empirical, double column.
- **Placeholder / target:** 6.6 × 2.05 in; target 6.6 × 2.05 in.
- **Transformations:** measured repetitions are averaged by frozen configuration; latency is displayed in milliseconds; pure-mechanism families are sorted by object count; fitted slopes are annotations/lines.
- **Forbidden interpretations:** universal PostgreSQL constants; per-candidate accuracy; storage-byte cost; causal portability across environments.
- **Why a figure:** points and fit lines expose the approximation and between-environment coefficient difference without hiding dispersion behind one number.

## F4 — Directed MCV-to-FD composition and consumption

- **Section:** 8.4, RQ4.
- **Current caption:** MCV consumption changes FD residual state; independent/all states suppress FDs while composition-aware states restore consumption.
- **Question:** Does upstream MCV consumption govern downstream FD reachability, and does joint selection avoid suppressed FDs?
- **Argumentative role:** Join the semantic direction with observed Census/DMV consumption evidence, including fresh DMV deployment.
- **Claims supported:** MCV precedes and can suppress FD; independent/all designs waste selected FDs; selected mixed designs restore consumption; the interaction survives fresh deployment.
- **Frozen sources / fields:** F4 data in `results/paper-evaluation-figure-table-data-v0.json`; underlying Census optimizer, DMV baseline/optimizer/deploy artifacts.
- **Type / placement:** hybrid conceptual/empirical, double column.
- **Placeholder / target:** 6.6 × 2.15 in; target 6.6 × 2.15 in.
- **Transformations:** selected FD counts are partitioned into consumed and suppressed counts; Census independent consumed count is exactly 97−72; all other values are direct frozen fields.
- **Forbidden interpretations:** independent optimization is globally optimal; all FDs are intrinsically useful; fresh DMV frozen-to-fresh numerical drift is available; general PostgreSQL mechanism coverage.
- **Why a figure:** the directed state transition explains why the consumption-count comparison occurs; neither a table nor prose links mechanism and outcome as directly.

## Shared visual policy

- PDF and SVG are generated deterministically by one Matplotlib script.
- Blue/solid/circle denotes MCV or frozen/hypothetical context where applicable; orange/hatched/square denotes FD or suppressed state; fresh deployment uses an outlined diamond or distinct neutral fill. Labels and patterns make color non-essential.
- Minimum intended text is 6.5 pt at final 6.6-inch width; captions remain in LaTeX.
- No randomness, interpolation, favorable filtering, or cross-workload shared loss axis is used.
