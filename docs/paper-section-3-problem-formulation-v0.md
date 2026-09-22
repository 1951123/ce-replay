# 3. Problem Formulation

This paper considers offline physical design of extended statistics for a supplied target workload. The design process receives a fixed database instance, queries with ground-truth cardinalities, candidate statistics and their hypothetical payloads, and a recurring maintenance budget. Its output is a realizable physical statistical state that minimizes cardinality-estimation loss on that workload. The workload is an input to physical design, not a training set for a learned estimator.

## 3.1 Database and target workload

Let the supplied target workload be denoted by

$$
Q.
$$

Each query is denoted by

$$
q \in Q,
$$

and its ground-truth cardinality by

$$
N_q.
$$

Ground truth is available to the offline design process so that alternative statistics states can be scored. It is not an input to the native estimator or to CE-Replay. CE-Replay reproduces the DBMS estimate under a hypothetical physical statistics state; the design layer subsequently compares that estimate with ground truth.

For each query, the design process also retains workload-fixed context, denoted by

$$
W_q.
$$

This context contains the design-independent information required by the supported estimator fragment, such as query clauses, relation context, ordinary selectivities, baseline relation information, supported predicate semantics, and semantic dimensions. The mathematical formulation does not require a particular serialization of this context.

## 3.2 Candidates, selection, and physical realization

Let the candidate-statistic universe be denoted by

$$
S.
$$

A candidate identifies a possible extended-statistics definition and its mechanism type. The abstract universe is mechanism-agnostic. The current PostgreSQL implementation instantiates it with multicolumn most-common-values statistics and functional-dependency statistics, but the formulation does not define all candidates to be one of these two types.

The selected candidate subset is denoted by

$$
Y \subseteq S.
$$

Selection alone need not fully determine the state observed by a DBMS. Let the DBMS-specific physical realization be denoted by

$$
\rho.
$$

A physical realization records any implementation-specific property needed to interpret the selected state. For PostgreSQL, creation and catalog/OID precedence can affect which overlapping MCV object wins a semantic tie. This is a PostgreSQL-specific realization property, not a universal claim that every statistics design is a selected set plus a permutation.

**Definition 1 (physical statistics design and realization).** A physical statistics design selects a subset of candidate definitions. A realization is the DBMS-specific state in which that selection is represented and consumed. A realizable design is a pair consisting of a selected subset and an admissible physical realization for that subset.

## 3.3 Candidate definitions and payloads

A candidate definition states what may be created; a statistics payload stores the data-dependent information consumed by the estimator. These are different objects. The same definition may yield different sampled values, frequencies, dependency degrees, or even payload availability after separate executions of statistics collection.

Let the frozen candidate-payload repository used during hypothetical evaluation be denoted by

$$
P.
$$

The repository contains both payload values and the schema needed to interpret them. For example, an MCV payload's semantic key ordering determines how stored dimensions map to query predicates. Payload state therefore cannot be hidden inside candidate identity or reduced to one precomputed response value.

The current prototype assumes that an offline acquisition process has populated the candidate repository. This one-time acquisition process is distinct from recurring maintenance of the selected deployed objects. A fresh deployment followed by `ANALYZE` may produce a new payload realization; the frozen repository conditions the hypothetical optimization but does not assert that candidate definitions uniquely determine future payloads.

## 3.4 Design-parametric cardinality replay

Let CE-Replay's executable semantics be denoted by

$$
F.
$$

For a query, CE-Replay maps workload-fixed context, a selected design, its physical realization, and the frozen payload repository to the DBMS cardinality estimate:

$$
\widehat{N}_q(Y,\rho;P)=F(W_q,Y,\rho,P).
$$

The estimate is denoted by

$$
\widehat{N}_q.
$$

The function is not a learned predictor and is not a table of responses precomputed for complete designs. Eligibility, winner selection, clause consumption, mechanism composition, and numerical updates remain executable functions of the hypothetical state.

**Definition 2 (CE-Replay).** CE-Replay is a workload-specialized, design-parametric executable representation of a supported statistics-sensitive native cardinality-estimation fragment. It freezes query and design-independent estimator context while retaining statistics-design-dependent control and numerical semantics as executable operations.

## 3.5 Query and workload loss

Let a generic per-query cardinality-estimation loss be denoted by

$$
\ell.
$$

The experiments instantiate it with q-error:

$$
\ell(\widehat{N},N)
=
\max\!\left(
\frac{\widehat{N}}{N},
\frac{N}{\widehat{N}}
\right).
$$

The implementation applies its documented small positive numerical floor when a true or estimated cardinality is zero. This definition is preserved here; the physical-design problem does not retroactively replace the completed objective to change zero-cardinality behavior.

Let the aggregate target-workload loss be denoted by

$$
L.
$$

For the fixed unweighted workload used in the experiments, the objective is

$$
L(Y,\rho;P)
=
\sum_{q\in Q}
\ell\!\left(
\widehat{N}_q(Y,\rho;P),
N_q
\right).
$$

Query estimates, per-query losses, and aggregate workload loss remain distinct: CE-Replay produces the estimate, the loss function scores it, and aggregation produces the physical-design objective. Fixed weights could be incorporated as workload context, but no additional weight symbol is introduced because it is absent from the frozen notation table and is unnecessary for the evaluated objective.

**Definition 3 (target-workload CE objective).** The target-workload objective is the aggregate loss between CE-Replay's DBMS estimates and the supplied ground-truth cardinalities, evaluated for one selected design, physical realization, and payload repository.

## 3.6 Recurring maintenance constraint

Let recurring statistics-maintenance cost be represented by the general function

$$
C(Y,\rho),
$$

and let the available maintenance budget be

$$
B.
$$

The function represents design-dependent collection or refresh work. It is not defined mathematically as serialized payload bytes or as one universal coefficient. The empirical PostgreSQL instantiation later uses mechanism-weighted object counts calibrated from aggregate `ANALYZE` latency in each measured environment. A fixed table-level `ANALYZE` baseline is common to designs over the same table and may cancel when comparing their design-dependent maintenance demand.

**Definition 4 (maintenance-feasible design).** A realizable physical statistics design is maintenance-feasible when

$$
C(Y,\rho) \le B.
$$

## 3.7 Constrained physical-design problem

The mathematical design problem is

$$
\min_{Y,\rho}
L(Y,\rho;P)
\quad
\text{subject to}
\quad
C(Y,\rho)\le B,
$$

where the physical realization must be admissible for the selected set. The notation defines the mathematical optimum; it does not assert that the evaluated workload-scale solver obtains it. The evaluated solver searches selection under a fixed recorded precedence and terminates at a local optimum of an audited ADD/DROP/SWAP neighborhood. Exhaustive global evidence is restricted to small or explicitly restricted instances.

Statistics-set inclusion need not monotonically reduce the objective. Adding one object can change which statistic wins, which clauses are consumed, which downstream mechanism remains applicable, and which numerical correction is applied. The same candidate can therefore be beneficial in one context, inert in another, and harmful in a third. The problem is not reducible to filling the budget with independently scored objects.

Finally, the objective concerns cardinality-estimation loss. It does not directly optimize query execution time, plan quality, latency, or throughput, and an improvement in aggregate q-error is not asserted to imply an execution-time improvement.
