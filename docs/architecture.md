# System Architecture

## 1. Purpose

This document defines the software architecture for the extended-statistics selection system.

The architecture implements the model defined in `model.md`.

The dependency direction is:

$$
\texttt{model.md}
\rightarrow
\texttt{architecture.md}
\rightarrow
\text{implementation}
\rightarrow
\text{experiments}
\rightarrow
\text{results}.
$$

`model.md` is the authoritative source for:

- mathematical objects;
- optimization semantics;
- measurement semantics;
- resource constraints;
- DBMS-neutral versus DBMS-specific boundaries;
- assumptions and scope.

`architecture.md` does not redefine those semantics.

Its purpose is to map the model into:

- system components;
- component responsibilities;
- data artifacts;
- execution stages;
- backend interfaces;
- optimization interfaces;
- validation interfaces.

If an implementation decision conflicts with `model.md`, the implementation must be changed rather than silently changing the model semantics.

---

# 2. Architectural Principles

## 2.1 Model-first Architecture

Every core system object must correspond to a concept defined in `model.md`.

Examples include:

$$
q,
$$

$$
t,
$$

$$
\rho,
$$

$$
s=(t_s,C_s,p_s),
$$

$$
e_{q\rho}^{0},
$$

$$
e_{qs\rho},
$$

$$
\Delta_{qs\rho},
$$

$$
\lambda_{q\rho},
$$

$$
f_{q\rho},
$$

$$
z_{t\rho},
$$

$$
y_{s\rho},
$$

and

$$
x_{qs\rho}.
$$

The implementation may introduce identifiers, classes, tables, files, caches, or helper structures, but those structures must preserve the semantics of the corresponding model objects.

---

## 2.2 DBMS-neutral Core

The following responsibilities belong to the DBMS-neutral core:

- workload representation;
- table and query metadata;
- abstract sampling-rate candidate space;
- physical-statistic representation;
- measurement orchestration;
- measurement result storage;
- coefficient construction;
- fidelity adjustment;
- optimization;
- resource-budget enforcement;
- selected-design representation;
- validation orchestration;
- result reporting.

The core must not hard-code PostgreSQL-, Oracle-, or other DBMS-specific relationships.

In particular, the core must not assume a universal relationship such as

$$
p_s=f(\rho).
$$

---

## 2.3 DBMS-specific Backends

DBMS-specific behavior is isolated behind backend interfaces.

A backend is responsible for realizing:

$$
\rho
\rightarrow
B_t(\rho),
$$

$$
p_s
\rightarrow
P_s(p_s),
$$

and

$$
(\rho,s)
\rightarrow
\text{feasible or infeasible}.
$$

A backend also performs the physical DBMS operations required for:

- base-statistics configuration;
- statistics collection;
- extended-statistic creation;
- extended-statistic removal;
- statistics refresh;
- cardinality-estimate extraction;
- storage measurement;
- maintenance-cost measurement or estimation;
- realized sampling measurement.

The optimizer must not directly issue DBMS-specific commands.

---

## 2.4 Measurement before Optimization

The optimizer must operate on premeasured or precomputed coefficients.

The intended dependency is:

$$
\text{candidate generation}
\rightarrow
\text{physical measurement}
\rightarrow
\text{coefficient construction}
\rightarrow
\text{optimization}.
$$

The optimizer must not perform DBMS measurements while solving the MILP.

Quantities such as

$$
e_{q\rho}^{0},
$$

$$
e_{qs\rho},
$$

$$
\Delta_{qs\rho},
$$

$$
\lambda_{q\rho},
$$

and

$$
f_{q\rho}
$$

are optimization inputs.

---

## 2.5 Physical Validation after Optimization

A low surrogate objective value is not sufficient evidence that the selected design is good.

The selected solution must be mapped back to a physical design

$$
D^*
=
(\{\rho_t^*\},Y^*)
$$

and deployed in the DBMS.

The final evaluation measures

$$
E_q(Y^*,\{\rho_t^*\})
$$

using the complete deployed statistics set.

Therefore, the architecture separates:

$$
\text{surrogate optimization}
$$

from

$$
\text{physical validation}.
$$

---

## 2.6 Reproducible Intermediate Artifacts

Major pipeline stages should produce persistent artifacts rather than passing important experimental state only through process memory.

Conceptually,

$$
\text{input}
\rightarrow
\text{artifact}
\rightarrow
\text{next stage}.
$$

This enables:

- reproducibility;
- debugging;
- experiment inspection;
- partial reruns;
- consistency checks;
- comparison across DBMS backends;
- comparison across model variants.

The exact file format is an implementation concern, but the semantic contract of each artifact must remain stable.

---

# 3. High-level System Structure

The system is organized into the following logical layers:

1. workload layer;
2. candidate-generation layer;
3. DBMS backend layer;
4. measurement layer;
5. coefficient layer;
6. optimization layer;
7. deployment layer;
8. validation layer;
9. experiment/result layer.

The high-level flow is:

$$
\text{Workload}
$$

$$
\downarrow
$$

$$
\text{Candidate Generation}
$$

$$
\downarrow
$$

$$
\text{DBMS Feasibility Realization}
$$

$$
\downarrow
$$

$$
\text{Measurement}
$$

$$
\downarrow
$$

$$
\text{Coefficient Construction}
$$

$$
\downarrow
$$

$$
\text{Optimization}
$$

$$
\downarrow
$$

$$
\text{Physical Deployment}
$$

$$
\downarrow
$$

$$
\text{End-to-End Validation}
$$

$$
\downarrow
$$

$$
\text{Experiment Results}.
$$

---

# 4. Core Domain Objects

## 4.1 Table

A table object represents

$$
t\in T.
$$

It must have a stable logical identifier.

Relevant metadata may include:

- table name;
- schema name;
- true row count $N_t$;
- columns;
- DBMS backend identifier;
- candidate sampling-rate set $\mathcal R_t$.

DBMS-specific configuration should not be embedded directly into the DBMS-neutral table identity.

---

## 4.2 Query

A query object represents

$$
q\in Q.
$$

In the current model, every query maps to exactly one table:

$$
q\rightarrow t(q).
$$

A query must have a stable identifier independent of execution order.

Relevant information includes:

- query identifier;
- SQL or equivalent query representation;
- table identifier;
- true result cardinality $A_q$ when available to the experimental pipeline;
- candidate-compatible statistics.

$A_q$ is experimental ground truth.

It must not be interpreted as information available to the production DBMS optimizer.

---

## 4.3 Sampling Candidate

A sampling candidate represents

$$
\rho\in\mathcal R_t.
$$

The candidate stores the requested DBMS-neutral sampling rate.

The requested rate must remain distinct from the realized rate:

$$
\rho
\neq
\rho_{t,\rho}^{\mathrm{realized}}
$$

in general.

The backend is responsible for realizing the requested rate.

---

## 4.4 Physical Statistic

A physical extended statistic is always represented as

$$
s=(t_s,C_s,p_s).
$$

Its identity contains:

- table;
- column set;
- representation parameter.

Its identity does not contain the sampling rate.

Therefore,

$$
s\neq(t_s,C_s,p_s,\rho).
$$

The same physical statistic may be measured under multiple candidate sampling configurations.

---

## 4.5 Rate-specific Candidate Context

Although $\rho$ is not part of the physical-statistic identity, many experimental and optimization quantities are defined for a pair

$$
(s,\rho).
$$

Examples include:

$$
e_{qs\rho},
$$

$$
c_{s\rho},
$$

and

$$
m_{s\rho}^{\mathrm{ext}}.
$$

The implementation may use an internal composite key for $(s,\rho)$.

Such a key is an implementation convenience.

It must not redefine the physical statistic itself.

---

# 5. Workload Layer

## 5.1 Responsibilities

The workload layer is responsible for:

- loading workload definitions;
- assigning stable query identifiers;
- associating each query with $t(q)$;
- obtaining or loading $A_q$ for experiments;
- exposing query metadata to measurement and validation;
- preserving workload identity across experimental runs.

---

## 5.2 Workload Contract

The workload layer must expose enough information to reconstruct:

$$
Q,
$$

$$
T,
$$

$$
t(q),
$$

and, for experimental measurement,

$$
A_q.
$$

The workload layer must not contain optimizer decisions such as

$$
z_{t\rho}
$$

or

$$
y_{s\rho}.
$$

Those belong to later stages.

---

# 6. Candidate-generation Layer

## 6.1 Sampling Candidate Generation

For each table $t$, the candidate generator produces

$$
\mathcal R_t.
$$

The candidate set is finite.

Sampling candidate generation is DBMS-neutral at the model level.

The actual ability of a backend to realize a candidate is determined separately.

---

## 6.2 Physical-statistic Candidate Generation

The candidate generator constructs physical-statistic candidates

$$
s=(t_s,C_s,p_s).
$$

Candidate generation may use:

- workload predicates;
- referenced columns;
- column combinations;
- configured candidate representation values;
- explicit experiment configuration.

Candidate generation must not attach a sampling rate to the identity of $s$.

---

## 6.3 Backend Feasibility Filtering

After abstract candidates are generated, the backend determines feasibility.

For each pair

$$
(\rho,s),
$$

the backend evaluates whether

$$
(\rho,s)\in\mathcal F_{\mathrm{DBMS}}.
$$

The resulting feasible set is

$$
\mathcal S_{t,\rho}.
$$

Only feasible pairs proceed to measurement and optimization.

---

## 6.4 Candidate-space Artifact

Candidate generation should produce a persistent artifact representing at least:

- table identifier;
- requested sampling rate;
- statistic identifier;
- statistic table;
- statistic column set;
- representation parameter;
- backend feasibility.

This artifact represents the finite design space used by later stages.

---

# 7. DBMS Backend Layer

## 7.1 Backend Interface

Every supported DBMS implements a common logical backend interface.

The interface must support the operations required by:

- candidate feasibility;
- baseline realization;
- candidate-statistic deployment;
- measurement;
- resource estimation;
- final deployment;
- cleanup.

The core must invoke backend operations through this interface rather than directly issuing backend-specific commands.

---

## 7.2 Sampling Realization

The backend implements

$$
\rho
\rightarrow
B_t(\rho).
$$

The result $B_t(\rho)$ is the complete backend-specific baseline configuration required to realize the requested sampling behavior.

The backend must also expose or measure

$$
S_{t,\rho}^{\mathrm{realized}}
$$

when possible.

The core then derives

$$
\rho_{t,\rho}^{\mathrm{realized}}
=
\frac{
S_{t,\rho}^{\mathrm{realized}}
}{
N_t
}.
$$

---

## 7.3 Baseline Statistics

The backend baseline contains:

$$
\text{DBMS-native base statistics}
+
\text{no candidate extended statistic}.
$$

The backend must not interpret baseline as a statistics-free database state.

For DBMSs where ordinary statistics configuration participates in sampling realization, that configuration belongs to

$$
B_t(\rho).
$$

---

## 7.4 Extended-statistic Deployment

For physical statistic

$$
s=(t_s,C_s,p_s),
$$

the backend implements the DBMS-specific representation mapping

$$
p_s
\rightarrow
P_s(p_s).
$$

The backend must provide operations equivalent to:

- create statistic;
- configure representation;
- refresh or analyze statistics;
- remove statistic.

The exact commands are backend-specific.

---

## 7.5 Cardinality-estimate Extraction

The backend must provide a method for obtaining the DBMS cardinality estimate for query $q$ under the currently deployed configuration.

The measurement layer uses this estimate together with true cardinality $A_q$ to calculate q-error.

The extraction mechanism may differ between DBMSs.

The core measurement semantics must remain unchanged.

---

## 7.6 Resource Measurement

The backend provides or estimates:

$$
c_{s\rho},
$$

$$
m_{t\rho}^{\mathrm{base}},
$$

and

$$
m_{s\rho}^{\mathrm{ext}}.
$$

The backend must preserve the semantic distinction between:

$$
m_{t\rho}^{\mathrm{base}}
$$

and

$$
m_{s\rho}^{\mathrm{ext}}.
$$

The same physical work must not be intentionally charged to both terms.

---

## 7.7 Backend State Isolation

Measurement correctness depends on controlled DBMS state.

The backend must provide sufficient cleanup and reset operations to prevent one measurement from unintentionally contaminating another.

In particular, single-statistic measurement must not accidentally retain another candidate extended statistic.

The required invariant is:

$$
\text{candidate measurement for }s
\Rightarrow
\text{only intended candidate }s\text{ is present}.
$$

---

# 8. Measurement Layer

## 8.1 Responsibilities

The measurement layer is responsible for producing empirical evidence required by the surrogate model.

Its principal outputs are:

$$
e_{q\rho}^{0},
$$

$$
e_{qs\rho},
$$

$$
\rho_{t,\rho}^{\mathrm{realized}},
$$

and resource measurements or estimates.

The measurement layer does not select the final design.

---

## 8.2 Baseline Measurement

For every relevant pair

$$
(q,\rho),
$$

the measurement layer asks the backend to realize

$$
B_{t(q)}(\rho).
$$

No candidate extended statistic is deployed.

The resulting q-error is recorded as

$$
e_{q\rho}^{0}.
$$

---

## 8.3 Single-statistic Measurement

For every feasible tuple

$$
(q,s,\rho),
$$

the measurement layer:

1. realizes the same baseline configuration $B_{t(q)}(\rho)$;
2. deploys only candidate statistic $s$;
3. refreshes statistics as required;
4. obtains the DBMS cardinality estimate;
5. calculates q-error;
6. records the result as $e_{qs\rho}$.

The required comparison invariant is:

$$
e_{q\rho}^{0}
\quad\text{and}\quad
e_{qs\rho}
$$

must use the same baseline/sampling configuration.

---

## 8.4 Measurement Isolation

Single-statistic measurements must not be performed with an arbitrary previously deployed statistics set.

For measurement of $s$,

$$
Y_{\mathrm{measurement}}
=
\{s\}.
$$

For baseline measurement,

$$
Y_{\mathrm{measurement}}
=
\varnothing.
$$

This preserves the isolation interpretation of

$$
\Delta_{qs\rho}.
$$

---

## 8.5 q-error Calculation

Given true cardinality

$$
A_q
$$

and DBMS estimate

$$
\widehat A_q,
$$

the measurement layer computes q-error using the project's canonical q-error definition.

The same q-error implementation must be used for:

- baseline measurement;
- candidate measurement;
- final physical validation.

The definition must not change between pipeline stages.

---

## 8.6 Measurement Artifact

The measurement layer should persist raw evidence rather than only derived benefits.

At minimum, the artifact should allow reconstruction of:

$$
e_{q\rho}^{0}
$$

and

$$
e_{qs\rho}.
$$

Derived quantities such as

$$
\Delta_{qs\rho}
$$

should be reproducible from raw measurement data.

This prevents derived optimization coefficients from becoming the only surviving experimental evidence.

---

# 9. Coefficient Layer

## 9.1 Responsibilities

The coefficient layer transforms measurement evidence into optimizer-ready coefficients.

It does not perform physical DBMS operations.

Its inputs are measurement artifacts and model configuration.

Its outputs are deterministic optimizer inputs.

---

## 9.2 Raw Benefit

For every feasible tuple,

$$
\Delta_{qs\rho}
=
e_{q\rho}^{0}
-
e_{qs\rho}.
$$

Negative values must be preserved unless a later explicitly documented preprocessing policy removes them.

---

## 9.3 Sampling-Fidelity Proxy

Using experimental ground truth and realized sampling rate,

$$
\lambda_{q\rho}
=
A_q
\rho_{t(q),\rho}^{\mathrm{realized}}.
$$

This value is derived before optimization.

---

## 9.4 Fidelity-adjustment Weight

Given model hyperparameter

$$
k>0,
$$

the coefficient layer computes

$$
f_{q\rho}
=
\min
\left(
1,
\frac{\lambda_{q\rho}}{k}
\right).
$$

If fidelity adjustment is disabled,

$$
f_{q\rho}=1.
$$

---

## 9.5 Linear Credit

The coefficient layer computes

$$
\widetilde{\Delta}_{qs\rho}
=
f_{q\rho}
\Delta_{qs\rho}.
$$

This is an optimization coefficient.

It must not overwrite the raw measurement

$$
\Delta_{qs\rho}.
$$

---

## 9.6 Multiplicative Coefficients

For the multiplicative regime, compute

$$
w_{qs\rho}
=
\log
\left(
\frac{e_{qs\rho}}
{e_{q\rho}^{0}}
\right),
$$

and

$$
\widetilde w_{qs\rho}
=
f_{q\rho}w_{qs\rho}.
$$

Also compute

$$
b_{q\rho}
=
\log e_{q\rho}^{0}.
$$

These quantities are fixed optimizer coefficients.

---

## 9.7 Coefficient Artifact

The coefficient artifact should be sufficient to reconstruct the optimizer input without reconnecting to the DBMS.

Conceptually, it contains:

$$
(q,\rho,s)
$$

together with relevant values such as

$$
e_{q\rho}^{0},
$$

$$
e_{qs\rho},
$$

$$
\Delta_{qs\rho},
$$

$$
\lambda_{q\rho},
$$

$$
f_{q\rho},
$$

$$
\widetilde{\Delta}_{qs\rho},
$$

$$
w_{qs\rho},
$$

and

$$
\widetilde w_{qs\rho}.
$$

Resource coefficients are included or referenced by the same optimizer-input artifact.

---

# 10. Optimization Layer

## 10.1 Responsibilities

The optimization layer:

- loads finite candidate sets;
- loads measurement-derived coefficients;
- loads resource coefficients;
- constructs the MILP;
- invokes the solver;
- records the solver solution;
- projects the solver solution into a physical design.

The optimization layer must not perform DBMS measurement.

---

## 10.2 Decision Variables

The optimizer uses

$$
z_{t\rho}
$$

for sampling selection,

$$
y_{s\rho}
$$

for statistic selection,

and

$$
x_{qs\rho}
$$

for query-level surrogate credit.

These variables must preserve the semantics defined in `model.md`.

---

## 10.3 Sampling Constraint

For every table,

$$
\sum_{\rho\in\mathcal R_t}
z_{t\rho}
=
1.
$$

---

## 10.4 Statistic Compatibility

For every feasible statistic-rate pair,

$$
y_{s\rho}
\le
z_{t_s\rho}.
$$

---

## 10.5 Credit Compatibility

For every feasible query-statistic-rate tuple,

$$
x_{qs\rho}
\le
y_{s\rho}.
$$

---

## 10.6 Per-query Credit Limit

The optimizer enforces

$$
\sum_{\rho}
\sum_s
x_{qs\rho}
\le
K_q.
$$

The exact summation domain contains only feasible and query-compatible tuples.

---

## 10.7 Linear Regime

The linear surrogate is

$$
\widehat e_q^{\mathrm{lin}}
=
\sum_{\rho}
e_{q\rho}^{0}
z_{t(q)\rho}
-
\sum_{\rho,s}
\widetilde{\Delta}_{qs\rho}
x_{qs\rho}.
$$

The objective is

$$
\min
\sum_q
\widehat e_q^{\mathrm{lin}}.
$$

The implementation must not drop the rate-specific baseline term.

---

## 10.8 Multiplicative Regime

Define

$$
L_q
=
\sum_{\rho}
b_{q\rho}
z_{t(q)\rho}
+
\sum_{\rho,s}
\widetilde w_{qs\rho}
x_{qs\rho}.
$$

The optimizer minimizes

$$
\sum_qL_q
$$

subject to

$$
L_q\ge0.
$$

The implementation must preserve the distinction between the multiplicative surrogate objective and the original arithmetic-mean physical objective.

---

## 10.9 Resource Constraints

The storage constraint is

$$
\sum_{t,\rho}
\sum_{s\in\mathcal S_{t,\rho}}
c_{s\rho}
y_{s\rho}
\le
C_{\max}.
$$

The maintenance constraint is

$$
\sum_{t,\rho}
m_{t\rho}^{\mathrm{base}}
z_{t\rho}
+
\sum_{t,\rho}
\sum_{s\in\mathcal S_{t,\rho}}
m_{s\rho}^{\mathrm{ext}}
y_{s\rho}
\le
M_{\max}.
$$

---

## 10.10 Optimization Result Artifact

The raw optimization result should preserve:

- solver status;
- objective value;
- selected $z_{t\rho}$ variables;
- selected $y_{s\rho}$ variables;
- selected $x_{qs\rho}$ variables;
- resource usage;
- optimization regime;
- model hyperparameters;
- solver metadata required for reproducibility.

The raw solution should not be discarded after producing the final physical design.

---

# 11. Design Projection Layer

## 11.1 Purpose

MILP variables are not themselves the final DBMS deployment specification.

The design projection layer maps the optimization result back to the physical model.

---

## 11.2 Sampling Projection

For every table,

$$
\rho_t^*
=
\rho
\quad
\text{such that}
\quad
z_{t\rho}^*=1.
$$

---

## 11.3 Statistic Projection

The physical deployed set is

$$
Y^*
=
\left\{
s:
\exists\rho,\,
y_{s\rho}^*=1
\right\}.
$$

The sampling-rate index is removed from the identity of the physical statistic during projection because

$$
s=(t_s,C_s,p_s).
$$

---

## 11.4 Physical Design Artifact

The projected design artifact represents

$$
D^*
=
(\{\rho_t^*\},Y^*).
$$

It should contain enough information for a backend to deploy the complete design without rerunning the optimizer.

---

# 12. Deployment Layer

## 12.1 Responsibilities

The deployment layer physically realizes

$$
D^*
$$

in the target DBMS.

It uses the backend interface rather than DBMS-specific logic in the core.

---

## 12.2 Sampling Deployment

For every table,

$$
\rho_t^*
\rightarrow
B_t(\rho_t^*).
$$

The backend applies the required native configuration.

---

## 12.3 Extended-statistics Deployment

For every

$$
s\in Y^*,
$$

the backend creates the physical extended statistic and applies the representation mapping associated with $p_s$.

---

## 12.4 Statistics Refresh

After the complete design is configured, the backend performs whatever statistics collection or refresh operations are required for that DBMS.

Validation must not begin before the intended physical design is fully realized.

---

## 12.5 Deployment Verification

Before validation, the deployment layer should verify that the active DBMS state corresponds to the intended design.

The verification should detect obvious mismatches such as:

- missing selected statistics;
- unexpected leftover candidate statistics;
- incorrect representation configuration;
- incorrect table-level statistics configuration.

This protects validation from stale experimental state.

---

# 13. Validation Layer

## 13.1 Responsibilities

The validation layer measures the true behavior of the complete selected design.

Unlike the measurement layer, it does not isolate candidate statistics.

It intentionally measures the complete deployed set

$$
Y^*.
$$

---

## 13.2 Realized Query Error

For each query,

$$
E_q^{\mathrm{real}}
=
E_q(Y^*,\{\rho_t^*\}).
$$

This measurement includes real DBMS interactions among all selected statistics.

---

## 13.3 Primary Workload Metric

The primary workload metric is

$$
\overline E^{\mathrm{real}}
=
\frac1{|Q|}
\sum_{q\in Q}
E_q^{\mathrm{real}}.
$$

This returns evaluation to the original physical objective.

---

## 13.4 Same-rate Baseline

The validation layer must support deployment and measurement of

$$
(\{\rho_t^*\},\varnothing).
$$

This produces the same-rate no-extended-statistics baseline.

It isolates the value contributed by the selected extended statistics.

---

## 13.5 Sampling-policy Baselines

The validation layer must support alternative sampling policies such as:

- uniform sampling;
- fixed sampling;
- DBMS-default sampling configuration.

These baselines evaluate the value of per-table sampling allocation.

Resource usage must be controlled or reported so that comparisons remain interpretable.

---

## 13.6 Fidelity Ablation

The experiment pipeline must support rebuilding and resolving the optimization problem with

$$
f_{q\rho}=1.
$$

This isolates the effect of fidelity adjustment.

---

## 13.7 Surrogate-versus-Physical Comparison

The validation layer should preserve both:

- surrogate predictions or objective values;
- physically realized q-errors.

This enables analysis of the gap

$$
\text{surrogate prediction}
\leftrightarrow
\text{physical outcome}.
$$

That gap is part of the empirical evaluation of the modeling assumptions.

---

# 14. Experiment Orchestration

## 14.1 Purpose

Experiment orchestration coordinates the stages without owning their internal semantics.

A high-level experiment consists of:

1. load workload;
2. construct abstract candidate space;
3. apply backend feasibility;
4. perform measurements;
5. construct coefficients;
6. solve optimization problem;
7. project physical design;
8. deploy physical design;
9. validate physical design;
10. persist results.

---

## 14.2 Stage Independence

Where possible, each stage should be executable independently from persisted upstream artifacts.

For example:

$$
\text{measurement artifact}
\rightarrow
\text{coefficient builder}
$$

should not require rerunning physical measurements.

Similarly,

$$
\text{coefficient artifact}
\rightarrow
\text{optimizer}
$$

should not require a live DBMS connection.

This is important for reproducible experimentation.

---

## 14.3 Experiment Identity

Every experimental run should have a stable run identity.

Artifacts belonging to different runs must not be silently mixed.

An experiment identity should make it possible to associate:

- workload;
- DBMS backend;
- candidate space;
- measurement configuration;
- model hyperparameters;
- budgets;
- optimizer configuration;
- selected design;
- validation results.

---

## 14.4 Configuration Snapshot

Each experiment should preserve the effective configuration used for that run.

This includes values such as:

$$
k,
$$

$$
K_q,
$$

$$
C_{\max},
$$

and

$$
M_{\max}.
$$

It should also identify:

- sampling candidate sets;
- representation candidate sets;
- optimization regime;
- backend;
- workload.

The purpose is to prevent results from becoming detached from the configuration that generated them.

---

# 15. Artifact Flow

The canonical artifact flow is

$$
\text{workload artifact}
$$

$$
\downarrow
$$

$$
\text{candidate-space artifact}
$$

$$
\downarrow
$$

$$
\text{measurement artifact}
$$

$$
\downarrow
$$

$$
\text{coefficient artifact}
$$

$$
\downarrow
$$

$$
\text{optimization-result artifact}
$$

$$
\downarrow
$$

$$
\text{physical-design artifact}
$$

$$
\downarrow
$$

$$
\text{validation artifact}
$$

$$
\downarrow
$$

$$
\text{result/report artifact}.
$$

Each artifact should be traceable to its immediate upstream inputs.

---

# 16. Semantic Data Contracts

## 16.1 Measurement Key

A single-statistic measurement is identified conceptually by

$$
(q,\rho,s).
$$

Since

$$
s=(t_s,C_s,p_s),
$$

the complete semantic key contains:

$$
(q,\rho,t_s,C_s,p_s).
$$

The implementation may replace these values with stable identifiers, but it must preserve this uniqueness.

---

## 16.2 Baseline Key

A baseline measurement is identified by

$$
(q,\rho).
$$

It must not be keyed only by $q$ because

$$
e_{q\rho_1}^{0}
$$

and

$$
e_{q\rho_2}^{0}
$$

may differ.

---

## 16.3 Realized Sampling Key

A realized sampling measurement is identified by

$$
(t,\rho).
$$

It produces

$$
S_{t,\rho}^{\mathrm{realized}}
$$

and

$$
\rho_{t,\rho}^{\mathrm{realized}}.
$$

---

## 16.4 Resource Key

Base maintenance cost is keyed by

$$
(t,\rho).
$$

Extended-statistic resource coefficients are keyed by

$$
(s,\rho).
$$

The implementation must not accidentally collapse rate-specific values into a single coefficient when the backend reports different values.

---

# 17. Consistency Invariants

The implementation must preserve the following invariants.

## 17.1 Statistic Identity Invariant

Every physical statistic is

$$
s=(t_s,C_s,p_s).
$$

No component may redefine the physical statistic as

$$
(t_s,C_s,p_s,\rho).
$$

---

## 17.2 Baseline Invariant

Baseline means

$$
\text{DBMS-native base statistics}
+
\text{no candidate extended statistic}.
$$

It does not mean a statistics-free database.

---

## 17.3 Same-configuration Measurement Invariant

For

$$
\Delta_{qs\rho}
=
e_{q\rho}^{0}
-
e_{qs\rho},
$$

both q-errors must come from the same

$$
B_{t(q)}(\rho).
$$

---

## 17.4 Isolation Invariant

During measurement of

$$
e_{qs\rho},
$$

candidate statistic $s$ is measured in isolation.

Other candidate extended statistics must not influence the measurement.

---

## 17.5 Rate-index Invariant

Before a sampling configuration is selected, quantities that depend on the candidate rate retain the $\rho$ index.

Examples include:

$$
e_{q\rho}^{0},
$$

$$
e_{qs\rho},
$$

$$
\lambda_{q\rho},
$$

$$
f_{q\rho},
$$

$$
c_{s\rho},
$$

and

$$
m_{s\rho}^{\mathrm{ext}}.
$$

---

## 17.6 Raw-versus-derived Invariant

Raw measurement values must remain recoverable.

The system must not retain only

$$
\widetilde{\Delta}_{qs\rho}
$$

while discarding

$$
e_{q\rho}^{0}
$$

and

$$
e_{qs\rho}.
$$

---

## 17.7 Optimization-boundary Invariant

The optimizer consumes precomputed coefficients.

It does not alter physical DBMS state during solving.

---

## 17.8 Validation Invariant

Final validation measures the complete physical design

$$
D^*
=
(\{\rho_t^*\},Y^*).
$$

It must not substitute the surrogate objective for actual physical measurement.

---

## 17.9 Resource Double-counting Invariant

The cost represented by

$$
m_{t\rho}^{\mathrm{base}}
$$

must not be charged again as part of every

$$
m_{s\rho}^{\mathrm{ext}}.
$$

---

## 17.10 Ground-truth Boundary Invariant

$A_q$ may be used by experimental measurement, coefficient construction, and validation.

It must not be treated as information available to the production DBMS cardinality estimator.

---

# 18. Failure Handling

## 18.1 Measurement Failure

A failed physical measurement must not silently become:

$$
e_{qs\rho}=0,
$$

$$
\Delta_{qs\rho}=0,
$$

or another valid-looking coefficient.

Measurement failure must remain distinguishable from a successful neutral measurement.

---

## 18.2 Infeasible Candidate

If a backend determines that

$$
(\rho,s)\notin\mathcal F_{\mathrm{DBMS}},
$$

the pair must be excluded from the feasible optimizer candidate space.

It must not be represented as a feasible candidate with an artificial penalty unless an explicit model extension defines such behavior.

---

## 18.3 Missing Coefficients

The optimizer must not silently substitute arbitrary default values for missing required measurements.

A missing

$$
e_{q\rho}^{0}
$$

or required

$$
e_{qs\rho}
$$

should be treated as incomplete optimizer input.

---

## 18.4 Deployment Failure

If the selected physical design cannot be fully deployed, the resulting partial state must not be reported as validation of

$$
D^*.
$$

The run must distinguish:

$$
\text{intended design}
$$

from

$$
\text{actually deployed design}.
$$

---

# 19. PostgreSQL Backend Boundary

The PostgreSQL backend may implement

$$
\rho
\rightarrow
B_t^{\mathrm{PG}}(\rho)
$$

using PostgreSQL-native statistics configuration.

Ordinary single-column statistics configuration may be part of this baseline realization.

The backend may implement

$$
p_s
\rightarrow
P_s^{\mathrm{PG}}(p_s)
$$

using PostgreSQL-native extended-statistics representation controls.

Any PostgreSQL-specific coupling between sampling behavior and representation configuration belongs inside the PostgreSQL backend.

The DBMS-neutral core must not depend on such coupling.

The PostgreSQL backend must expose the same semantic outputs expected from any backend:

$$
\rho_{t,\rho}^{\mathrm{realized}},
$$

$$
e_{q\rho}^{0},
$$

$$
e_{qs\rho},
$$

$$
c_{s\rho},
$$

$$
m_{t\rho}^{\mathrm{base}},
$$

and

$$
m_{s\rho}^{\mathrm{ext}}.
$$

---

# 20. Oracle Backend Boundary

The Oracle backend implements the same logical architecture using Oracle-specific mechanisms.

It provides:

$$
\rho
\rightarrow
B_t^{\mathrm{Oracle}}(\rho),
$$

$$
p_s
\rightarrow
P_s^{\mathrm{Oracle}}(p_s),
$$

and

$$
\mathcal F_{\mathrm{Oracle}}.
$$

The Oracle backend is not required to expose PostgreSQL-equivalent native parameters.

Only the semantic interface to the core must remain consistent.

This allows the same measurement, coefficient, optimization, and validation layers to operate across backends.

---

# 21. Dependency Rules

The intended dependency graph is

$$
\text{workload}
\rightarrow
\text{candidate generation}
\rightarrow
\text{backend}
\rightarrow
\text{measurement}
\rightarrow
\text{coefficients}
\rightarrow
\text{optimization}
\rightarrow
\text{projection}
\rightarrow
\text{deployment}
\rightarrow
\text{validation}.
$$

Dependencies should not point backward across this graph except through explicit artifacts or interfaces.

In particular:

- optimizer code must not contain measurement logic;
- measurement code must not choose the final design;
- DBMS backend code must not implement the MILP;
- validation code must not redefine optimizer coefficients;
- result-reporting code must not mutate experimental measurements.

---

# 22. Implementation Modules

The exact package structure is an implementation decision, but the codebase should preserve the following logical module boundaries:

- `workload`
- `candidates`
- `backends`
- `measurement`
- `coefficients`
- `optimization`
- `deployment`
- `validation`
- `experiments`
- `artifacts`

A possible implementation may subdivide these modules further.

The names themselves are not normative.

The responsibilities and dependency boundaries defined in this document are normative.

---

# 23. Testing Boundaries

## 23.1 Unit Tests

Pure logic should be testable without a live DBMS.

Examples include:

- q-error calculation;
- $\Delta_{qs\rho}$ construction;
- $\lambda_{q\rho}$ construction;
- $f_{q\rho}$ construction;
- $\widetilde{\Delta}_{qs\rho}$ construction;
- log-effect construction;
- optimizer constraint generation;
- solution projection;
- artifact serialization.

---

## 23.2 Backend Integration Tests

Backend integration tests should verify:

- sampling realization;
- baseline reset;
- candidate creation;
- candidate removal;
- statistics refresh;
- estimate extraction;
- realized sampling measurement;
- resource measurement where supported.

---

## 23.3 Measurement Consistency Tests

Tests should verify that candidate and baseline measurements use the same intended

$$
B_t(\rho).
$$

They should also detect leftover candidate statistics that violate measurement isolation.

---

## 23.4 Optimization Sanity Tests

For the linear regime, a basic sanity test is:

if

$$
f_{q\rho}=1
$$

and exactly one statistic receives credit, then

$$
\widehat e_q^{\mathrm{lin}}
=
e_{qs\rho}.
$$

If no statistic receives credit, then

$$
\widehat e_q^{\mathrm{lin}}
=
e_{q\rho}^{0}.
$$

These properties should be covered by deterministic tests.

---

# 24. Reproducibility Requirements

A reported experiment should be reproducible from preserved information describing:

- source workload;
- DBMS backend;
- DBMS version where relevant;
- candidate-generation configuration;
- sampling candidate sets;
- representation candidate sets;
- raw measurement artifacts;
- realized sampling rates;
- resource coefficients;
- $k$;
- $K_q$;
- $C_{\max}$;
- $M_{\max}$;
- surrogate regime;
- solver configuration;
- optimizer output;
- projected physical design;
- physical validation results.

The architecture should avoid workflows where a final result can only be interpreted using transient console output or undocumented runtime state.

---

# 25. Architecture Scope

This architecture supports the current model scope:

- multiple workload tables;
- one table per query;
- discrete per-table sampling rates;
- single-statistic isolation measurement;
- workload-level statistics selection;
- linear single-statistic surrogate;
- multiplicative multi-statistic surrogate;
- storage constraints;
- maintenance constraints;
- DBMS-specific backend realization;
- end-to-end physical validation.

The current architecture does not require support for:

- general join-aware measurement;
- arbitrary multi-table statistics;
- exhaustive measurement of statistic subsets;
- continuous sampling optimization;
- modification of DBMS optimizer internals.

Such extensions should first be reflected in `model.md` before changing the architecture.

---

# 26. End-to-End Architecture Summary

The complete system can be summarized as

$$
(Q,T)
$$

$$
\downarrow
$$

$$
\{\mathcal R_t\},\mathcal S
$$

$$
\downarrow
$$

$$
\mathcal S_{t,\rho}
$$

$$
\downarrow
$$

$$
\left(
e_{q\rho}^{0},
e_{qs\rho},
\rho_{t,\rho}^{\mathrm{realized}},
c_{s\rho},
m_{t\rho}^{\mathrm{base}},
m_{s\rho}^{\mathrm{ext}}
\right)
$$

$$
\downarrow
$$

$$
\left(
\Delta_{qs\rho},
\lambda_{q\rho},
f_{q\rho},
\widetilde{\Delta}_{qs\rho},
\widetilde w_{qs\rho}
\right)
$$

$$
\downarrow
$$

$$
(z_{t\rho},y_{s\rho},x_{qs\rho})
$$

$$
\downarrow
$$

$$
D^*
=
(\{\rho_t^*\},Y^*)
$$

$$
\downarrow
$$

$$
E_q(Y^*,\{\rho_t^*\})
$$

$$
\downarrow
$$

$$
\frac1{|Q|}
\sum_{q\in Q}
E_q(Y^*,\{\rho_t^*\}).
$$

The architecture therefore preserves the complete research path:

$$
\boxed{
\text{model}
\rightarrow
\text{measurement}
\rightarrow
\text{surrogate}
\rightarrow
\text{optimization}
\rightarrow
\text{physical deployment}
\rightarrow
\text{validation}.
}
$$