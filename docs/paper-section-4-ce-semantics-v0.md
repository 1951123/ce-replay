# 4. Statistics-Sensitive CE Semantics

Extended statistics do not add a physical plan operator. They change the information consumed while the estimator computes selectivity and cardinality. The resulting estimate depends not only on which statistics exist, but also on how the DBMS determines applicability, selects among overlapping objects, consumes clauses or semantic dimensions, composes mechanisms, and applies payload-dependent numerical corrections. These decisions form design-sensitive control flow.

This section describes the PostgreSQL 16.14 semantics represented by CE-Replay. It focuses on validated behavior rather than internal source-function names. Exact source mappings and instrumentation belong in the reproducibility appendix.

## 4.1 A running interaction example

Consider a conjunctive query with predicates on attributes `a`, `b`, `c`, and `d`. A hypothetical design may contain:

- `MCV-A`, defined over `a,b,c`;
- `MCV-B`, defined over `b,c`;
- `MCV-C`, defined over a disjoint pair including `d`; and
- `FD-D`, whose determinant and implied attribute are among the query's predicate dimensions.

Suppose `MCV-A` and `MCV-B` are both applicable at the start of the MCV stage. `MCV-A` covers more currently unestimated semantic dimensions, so GreedyCover selects it. The clauses it covers become estimated and are unavailable to later MCV rounds. `MCV-B` may consequently cease to be applicable, even though its candidate definition remains present. If `MCV-C` covers disjoint unestimated dimensions, it may remain applicable and contribute in a later round.

The same consumed-clause state is then passed to the FD stage. If `MCV-A` consumed a predicate dimension required by `FD-D`, the dependency no longer applies. Under another selected subset, `MCV-B` or neither overlapping MCV may win, leaving the FD opportunity reachable. The example is schematic: it illustrates native state transitions without assigning empirical values from any workload realization.

This behavior explains why independent singleton scores are insufficient. Candidate utility depends on which other objects are present and on the semantic state produced before the candidate is considered.

## 4.2 MCV applicability and semantic dimensions

Within the supported fragment, a multicolumn MCV object is applicable when the query provides compatible clauses for enough of the semantic dimensions represented by that statistic. The validated workload predicates include supported scalar clauses and constant ScalarArray forms, specifically `IN` and `= ANY` in the validated MCV boundary.

Applicability is defined over estimator semantics rather than raw textual overlap alone. A statistic's keys and a query's columns often coincide with semantic dimensions for the evaluated pair-column workloads, but this is not a general representation rule. Expression identity, operator compatibility, variable position, and payload schema can affect whether a clause represents the required dimension. CE-Replay therefore records semantic dimensions and predicate compatibility rather than treating column-set overlap as universally sufficient.

The current boundary does not include arbitrary ScalarArray operators, nonconstant arrays, general OR/NOT trees, arbitrary expressions, joins, or parameterized clauses.

## 4.3 GreedyCover selection and consumption

PostgreSQL's validated MCV behavior proceeds in rounds. At each round, it considers MCV objects applicable to the currently unestimated clauses and orders them by the following rules:

1. maximize coverage of currently unestimated semantic dimensions;
2. among equal coverage, prefer the statistic with fewer total keys;
3. retain the relevant PostgreSQL statistics-list/catalog order for a remaining tie, which is tied to creation/OID precedence in the evaluated setting.

The selected statistic evaluates all compatible clauses it covers. Those clauses are marked as estimated and removed from consideration by subsequent MCV rounds. Selection then repeats over the residual state.

The third rule is part of PostgreSQL-specific physical realization. It does not imply that arbitrary precedence is a generic variable of statistics physical design, nor that the final solver globally optimizes precedence. It does imply that replaying a PostgreSQL design must preserve relevant recorded precedence.

This program is not “the first applicable statistic wins.” Applicability is necessary but does not determine the winner; coverage, key count, and physical tie order are evaluated against the current semantic state.

## 4.4 Overlap and disjoint composition

Overlapping statistics compete through consumption. If the selected object estimates dimensions required by another applicable object, the latter may no longer qualify in a later round. Adding an overlapping object can therefore replace a previous winner and change both the selected trace and the final numerical estimate.

The MCV stage is not restricted to one global winner. Objects covering disjoint residual dimensions can remain applicable after earlier consumption and contribute in later rounds. A faithful evaluator must execute repeated selection and state update rather than choosing one object for the whole query.

## 4.5 Numerical MCV update

For each selected object, PostgreSQL evaluates query clauses directly against the MCV payload. Matching entries contribute their stored frequencies and corresponding base frequencies; the remaining simple-selectivity mass is bounded by the part of the distribution outside the MCV list. The native combination rule produces the selected object's multivariate selectivity contribution, which is then composed with later disjoint rounds and residual selectivity state.

CE-Replay executes this payload-dependent numerical update from the serialized MCV values, frequencies, base frequencies, and schema metadata. It does not substitute a learned correction factor, a singleton response, or a cleaner surrogate formula. Detailed native equations and node-field comparisons are reserved for the semantic-validation appendix.

## 4.6 Constant ScalarArray predicates

For the supported constant ScalarArray forms, PostgreSQL evaluates each MCV item's relevant dimension directly against the array predicate. For `IN` and `= ANY`, comparisons across non-null array elements are combined with OR semantics. Duplicate array values may repeat operator calls but do not count one matched MCV item multiple times; null elements do not create a match. Multiple query clauses are then combined as required by the conjunctive MCV-item bitmap evaluation.

The semantics are not modeled by expanding the array into independently estimated scalar equalities. Direct evaluation against the MCV item preserves PostgreSQL's item-match and frequency aggregation behavior. This bounded, source-derived extension covers the canonical DMV workload's constant equality/IN predicates. It is evidence that CE-Replay can be extended deliberately by predicate family, not evidence of automatic arbitrary-predicate support.

## 4.7 Functional-dependency semantics

Functional dependencies execute a different semantic program. They are not another instance of MCV GreedyCover. Within the validated fragment, PostgreSQL identifies dependency payload entries compatible with the residual equality-eligible predicate state, aggregates the applicable dependency information, and adjusts selectivity according to the stored dependency degrees. Applying a dependency accounts for an implied attribute so that its ordinary selectivity is not independently applied again in the same way.

Multiple dependency entries may participate. Their applicability depends on supported predicate forms, exact semantic dimensions, payload availability, and the clause state entering the FD stage. Single-attribute dependencies and unsupported range contexts are not promoted into the validated boundary merely because their columns overlap a query.

## 4.8 Directed MCV-to-FD composition

PostgreSQL evaluates the supported mechanisms in a directed order:

`MCV evaluation → estimated-clause state → FD evaluation`.

The FD stage receives the state produced by MCV evaluation. An MCV winner can consume clauses that otherwise make a functional dependency applicable. Conversely, omitting or replacing an MCV object may preserve an FD opportunity. MCV and FD are therefore not independent numerical correction factors whose candidate scores can be optimized separately.

This directed dependency motivates a compositional state-transition representation. CE-Replay first executes the MCV program, including repeated GreedyCover rounds and numerical updates, and then executes the FD program over the resulting residual clause state. The same state boundary also exposes which downstream FD computation must be revisited after an MCV design change.

## 4.9 Consequence for physical design

A candidate's effect is contextual because changing the selected design can change:

- the set of applicable statistics;
- the winner in an MCV round;
- the clauses and semantic dimensions consumed;
- the later MCV rounds that remain reachable;
- the FD dependencies that remain applicable; and
- the payload-derived numerical contributions.

The response is consequently non-additive and can be non-monotone. A candidate may improve the objective in one design, have no effect in another, or worsen it after changing the native control path. Faithful hypothetical evaluation therefore requires design-parametric execution of the supported native semantics. Section 5 introduces CE-Replay as that executable representation.
