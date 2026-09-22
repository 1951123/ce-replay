# MCV-Commutativity-v0

## Verdict

For the supported PostgreSQL 16.14 base-relation MCV fragment, the smallest
source-justified condition found is:

> Two enabled actions commute when their **state-specific consumed compatible
> clause sets are disjoint**, neither action otherwise changes an input read by
> the other, and the two numerical updates of the shared selectivity
> accumulator are equal under the chosen numerical semantics.

In the frozen Census pair-MCV fragment, contribution computation is
candidate-local once the consumed clauses are fixed. Thus the condition reduces
to disjoint consumed-clause scopes plus the checked accumulator property. All
248,352 satisfying exhaustive instances were fully semantic-commutative, with
zero control, numerical, continuation, or canonicalization counterexamples.

This is a sufficient condition for transitions of a fixed physical design. It
does not repair the restart-under-design-extension counterexample found by
`CE-Semantic-State-v0`.

## Source read/write audit

| component | read | written | monotone | locality | role |
|---|:---:|:---:|:---:|---|---|
| compatible clause representation | yes | no | n/a | query-fixed | control |
| `estimatedclauses` | yes | yes | grows | shared | control |
| `list_attnums` / `list_exprs` | yes | yes (nulled) | information only removed | shared | control |
| remaining compatible-clause scope | yes | yes (consumed) | shrinks | shared | control |
| selected statistics availability | yes | no | n/a | design-fixed | control |
| candidate keys and expressions | yes | no | n/a | candidate-local | control |
| statistics list and OID order | scheduler reads | no | n/a | candidate-fixed | winner selection |
| MCV payload | yes | no | n/a | candidate-local | numerical |
| simple/MCV/base/total selectivities | yes/derived | no shared write | n/a | candidate plus consumed clauses | numerical |
| accumulated MCV selectivity `sel` | yes | yes | multiplied by probability | shared | numerical |

`choose_best_statistics()` maximizes covered, still-unestimated dimensions,
then minimizes total statistic dimensions. Exact ties retain the first object
in the statistics list. `RelationGetStatExtList()` sorts that list by OID. Once
a winner is selected, all compatible clauses covered by it are marked
estimated and their `list_attnums`/`list_exprs` entries are nulled.

For implicit AND, `mcv_clauselist_selectivity()` and
`mcv_combine_selectivities()` produce one local `stat_sel`, after which the
shared update is:

```text
sel = sel * stat_sel
```

## Action and commutativity definitions

At state `X`, action `T_s` reads the still-unestimated compatible clauses
covered by statistic `s`, consumes exactly those clauses, and emits its raw
`stat_sel`. Control commutativity requires equal remaining clauses,
`estimatedclauses`, and later applicability after both orders. Full semantic
commutativity additionally requires equivalent accumulator values and equal
behavior under the identical fixed-design continuation.

The alternative scheduler orders are an analysis device. PostgreSQL itself
continues to execute only its GreedyCover/OID-determined order.

Four conditions were tested:

- **A:** disjoint plain attribute key sets;
- **B:** disjoint compatible-clause scopes;
- **C:** disjoint state-specific consumed-clause scopes;
- **D:** source read/write independence, including an order-invariant shared
  numerical update.

In Census, A–D coincide because every candidate is a two-attribute statistic,
there are no statistics expressions or multi-attribute clauses, and both
attributes must remain for an action to be enabled. This equivalence is not
claimed for general PostgreSQL statistics.

## Exhaustive falsification

All 158 Census queries with at most 10 relevant candidates were exhaustively
enumerated: 69,245 physical subsets and every reachable prefix where two
selected candidates were simultaneously enabled.

| measurement | count | fraction |
|---|---:|---:|
| enabled pair/context instances | 791,640 | 100% |
| fully semantic-commutative | 248,352 | 31.37% |
| control-only commuting | 0 | 0% |
| numerical non-commuting | 0 | 0% |
| non-commuting | 543,288 | 68.63% |
| overlap/invalidation reason | 543,288 | 68.63% |

The 31.37% is a fraction of tested enabled transition instances. It is not a
physical-design-space reduction or a predicted optimizer speedup. It differs
from the earlier 56.17% measurement because this experiment weights reachable
fixed-design subset/prefix contexts and uses the stricter source-derived
action model.

### Conditions A–D in the Census fragment

| condition | satisfying instances | commuting | false positives | false negatives |
|---|---:|---:|---:|---:|
| A: disjoint attribute keys | 248,352 | 248,352 | 0 | 0 |
| B: disjoint compatible clauses | 248,352 | 248,352 | 0 | 0 |
| C: disjoint consumed clauses | 248,352 | 248,352 | 0 | 0 |
| D: read/write independent | 248,352 | 248,352 | 0 | 0 |

No Census instance violated `A => B`, `B => C`, or `C => D`. This is an
empirical implication only for this restricted candidate and clause shape.

## Expression counterexample to plain `stxkeys` condition A

Census does not contain expression candidates, while PostgreSQL stores
statistics expressions separately from `pg_statistic_ext.stxkeys`. A minimal
source-derived PostgreSQL fixture uses:

```sql
CREATE STATISTICS expr_a (mcv) ON a, lower(t) FROM expr_probe;
CREATE STATISTICS expr_b (mcv) ON b, lower(t) FROM expr_probe;
```

The plain `stxkeys` sets `{a}` and `{b}` are disjoint, but both actions consume
the clause `lower(t)='x'`. Whichever executes first leaves the other with only
one dimension, so they do not commute. Therefore:

```text
disjoint plain pg_statistic_ext.stxkeys  is not sufficient
```

Condition A becomes usable only if “keys” means the complete statistics
dimension scope, including expressions. The fixture is serialized separately
and is not counted as a Census runtime instance.

## Numerical proof obligation

Mathematically, independent contributions update the accumulator as
`x*a*b`; multiplication is commutative and associative over real numbers.
IEEE-754 evaluation actually compares `(x*a)*b` with `(x*b)*a`, so mathematical
commutativity alone does not guarantee bitwise equality in general.

In all 248,352 satisfying Census contexts:

- bitwise-equal accumulator results: 248,352;
- tolerance-only equal results: 0;
- differences beyond relative tolerance `1e-12`: 0.

Thus bitwise equality is an exhaustive observation in the tested domains, not
a universal floating-point theorem. The safe general condition D explicitly
includes order invariance of the numerical update. For replay-tolerance
semantics, B/C plus ordinary finite, non-underflowing probability products is
the PostgreSQL-specific corollary supported here.

## Continuation safety

Each commuting pair was followed independently by the same remaining selected
statistics under native priority:

- continuation tests: 248,352;
- divergences in later winners, final control state, or raw accumulator: 0.

Once the two actions have equal control state, selected availability, and
accumulator, later deterministic PostgreSQL execution reads identical inputs.
This continuation statement holds for a fixed design; it does not cover adding
new candidates and restarting execution.

## Canonical trace prototype

The prototype swaps adjacent independent actions toward ascending OID rank.
It performed 55,615 deliberately reversed adjacent-action tests:

- deterministic canonicalization failures: 0;
- non-independent pairs merged: 0;
- raw-result changes: 0.

There were 2,341 distinct observed winner-only PostgreSQL traces and 2,341
canonical classes. PostgreSQL traces are already OID-canonical, so the
prototype does not reduce the observed native trace set. It demonstrates that
alternative safe scheduler linearizations map back to the native
representative. This experiment does not measure search reduction.

## Partial-order interpretation

At state `X`, introduce a dependency edge only when two enabled actions fail
the read/write-independence condition. The tested contextual dependency
density is 68.63%; the safe commuting-pair fraction is 31.37%. A completed
trace can be viewed as one linearization of this state-dependent relation.

Because the independence relation is state-specific in general, a future
partial-order implementation must calculate consumed clause scopes at the
current state. Static disjoint full-dimension or compatible-clause scopes are
stronger sufficient checks and can be used conservatively.

## Layer separation

- **Control layer:** overlapping consumption can disable the second action.
- **Estimation layer:** all control-independent Census pairs were numerically
  order-invariant in the exhaustive domains.
- **Objective layer:** q-error marginals may still differ with background
  estimates. That nonlinear objective effect does not invalidate CE-level
  commutativity.

## Required final answers

1. **Smallest sufficient condition found:** state-specific disjoint consumed
   compatible-clause scopes, local contribution computation, and an
   order-invariant shared numerical update—equivalently the explicit
   read/write-independence condition D.
2. **Are disjoint statistics-key scopes sufficient?** Plain attribute-only
   `stxkeys`: no, because expressions are separate. Complete dimension scopes:
   yes as a conservative condition in the supported fragment.
3. **Are disjoint compatible-clause scopes sufficient?** Yes in all 248,352
   exhaustive Census instances and by the source read/write argument, subject
   to the stated numerical condition.
4. **Are disjoint state-specific consumed scopes sufficient?** Yes; this is
   the weakest condition supported by the current source argument and tests.
5. **Is numerical composition order-invariant?** Mathematically yes. It was
   also bitwise equal in every tested context, but universal bitwise equality
   is not claimed; condition D retains a numerical-order requirement.
6. **Counterexamples?** None for B–D in the exhaustive Census domains. One
   source-derived expression fixture falsifies plain attribute-only A.
7. **Static or state-dependent?** B and complete-dimension disjointness are
   safe static sufficient checks. The weakest condition C/D requires current
   remaining/consumed clause state.
8. **Implement Partial-Order-Reduction-v0 next?** Yes, as a representation
   experiment—not yet as an optimizer. The sufficient condition has zero
   exhaustive false positives, 248,352 continuation-safe instances, and a
   deterministic canonicalizer. The next experiment must measure actual
   equivalence-class/state-space reduction rather than infer it from 31.37%.

## Limitations

- Main measurements cover frozen Census pair-MCVs, fixed precedence, and
  single-attribute AND clauses only.
- The expression fixture is source-constructed because the instrumented
  PostgreSQL installation was unavailable in the current environment; it is
  not presented as a native runtime measurement.
- Queries above 10 candidates were excluded from the exhaustive theorem test.
- Only the native-priority identical suffix was executed per pair; the source
  argument, not enumeration of every possible scheduler suffix, supplies the
  general identical-continuation reasoning.
- No optimizer, POR search, deployment, or global state-space reduction was
  implemented or claimed.

## Artifacts

- `tools/mcv_commutativity_v0.py`
- `results/census_mcv_commutativity_v0.json`
- `results/mcv_commutativity_synthetic_v0.json`

