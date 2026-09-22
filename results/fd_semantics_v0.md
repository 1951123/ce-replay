# FD-Semantics-v0 (PostgreSQL 16.14)

## Result

The FD node has now been reproduced externally for 13 subset/order scenarios
(all `2^3` subsets plus all six full-set creation orders). The maximum relative
error against the new native oracle was **0.0**.

The three adversarial objects were:

| object | columns | representative payload |
|---|---|---|
| `ab` | `(a,b)` | `a => b: 0.90` |
| `abc` | `(a,b,c)` | includes `a,c => b: 1.0`, `a,b => c: 0.90` |
| `cd` | `(c,d)` | `c => d: 0.64`, `d => c: 0.10` |

All six full-set creation orders produced the same choices and selectivity for
this non-tied effective case: first `a,c => b` (width 3, degree 1), then
`a => c` (degree 0.8), for FD selectivity `0.008023999820858241`.
This also shows that “all matching objects contribute” does not mean that each
object necessarily survives consumption: selecting the nested `abc`
dependencies consumes `b` and then `c`, making `cd` unavailable.

## Exact semantics extracted from source

1. Compatible clauses are equality-to-pseudoconstant clauses, `IN/ANY`, ORs
   whose arms all refer to the same attribute/expression, boolean clauses, and
   exact matches to statistics expressions. Plain columns must be Vars of the
   target relation/current query level; system columns are rejected.
2. Already-estimated clauses are excluded. At least two distinct compatible
   attributes/expressions are required. A statistics object is loaded only if
   at least two of its dimensions match.
3. PostgreSQL merges the dependencies from **all** matching FD objects. It
   repeatedly chooses a fully covered dependency by lexicographic priority:
   widest first, then highest degree. It then removes the chosen dependency's
   implied (last) attribute from the available set.
4. Exact priority ties replace the previous winner while scanning. Thus the
   implementation has a last-seen tie-break, although all tested creation
   orders were invariant because their effective winners were not tied.
5. For determinant selectivity `s1`, implied-column selectivity `s2`, and
   dependency degree `f`, the implied column is replaced by

       f + (1-f)*s2                    if s1 <= s2
       f*s2/s1 + (1-f)*s2             otherwise

   Chosen dependencies are applied in reverse selection order, and all final
   per-attribute selectivities are multiplied.

## Applicability falsification

Native instrumentation confirmed FD use for `a=7 AND b=7`, reversed equality,
`IN`, and same-attribute OR. It rejected range, inequality, and a single
attribute. An exact expression-statistics match (`lower(txt)`) worked, while
`upper(txt)` did not. `a=b AND b=7` did use FD, but this is due to planner
equivalence propagation producing constant restrictions; it is not evidence
that a raw Var-to-Var clause is directly compatible. With both a compatible
equality and an incompatible range on `a`, the equality participates in FD and
the range remains for ordinary estimation.

## MCV + FD composition

The pipeline is strictly **MCV first, FD second**, sharing the same
`estimatedclauses` bitmap. In the mixed experiment, MCV on `(a,b)` consumed
those clauses (`stat=0.01`); the nested FD `(a,b,c)` could no longer match, but
the remaining disjoint FD `(c,d)` applied (`FD=0.007757760064085723`). The
combined selectivity was their product, giving 7.757760064 estimated rows out
of 100,000.

This means the joint design interaction is not symmetric: MCV changes the
clause set visible to FD, while FD never changes MCV selection in the same
call. A suitable IR edge is therefore

`MCV node -> estimated-clause state -> FD node`, not two independent
correction factors.

Machine-readable traces and payloads are in `fd_semantics_v0.json`; the
reproducible experiment is `tools/fd_semantics_v0.py`. Native oracle notices
are implemented in PostgreSQL's `src/backend/statistics/dependencies.c`.

