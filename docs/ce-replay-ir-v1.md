# CE-Replay-IR-v1 contract

Status: frozen for the PostgreSQL 16, single-table `AND`, integer two-column
MCV fragment.

For query `q`, the logical IR is

`Gq = (Wq, Pq, Sq, Fq)`.

## Wq: workload-fixed context

- PostgreSQL major version and estimator fragment;
- relation identity and relation rows;
- normalized clause set and predicate semantics;
- no-MCV query estimate/selectivity;
- simple selectivity for every candidate's covered clause group;
- truth rows and workload weight when the IR is used for optimization.

These fields may be specialized during instrumentation because they do not
change when the statistics design changes.

## Pq: statistics payloads

For every candidate:

- statistics object identity;
- `stxkeys`-derived payload column order;
- MCV item values and null flags;
- item frequency and base frequency;
- total MCV frequency;
- serialized payload size in bytes.

Payload array positions MUST be interpreted using `stxkeys` order, never the
textual `CREATE STATISTICS` column order.

## Sq: design-dependent state

- candidate availability/selection bit;
- candidate key set;
- arity;
- physical OID precedence rank;
- storage cost and global budget;
- remaining uncovered clauses during replay.

Instrumentation MUST NOT freeze the winning candidate or consumed sequence.
Those are derived states recomputed for each design `D`.

## Fq: executable semantics

1. MCV eligibility: candidate covers at least two remaining columns.
2. Greedy priority: maximum covered columns, minimum total keys, minimum OID.
3. Transition: remove clauses covered by the selected object and repeat.
4. Payload matching: evaluate the fixed clauses on each MCV item.
5. Native combine:
   `other = clamp(simple - matching_base)`;
   `other = min(other, 1 - total_mcv)`;
   `stat = clamp(matching_mcv + other)`.
6. Query composition for disjoint consumed clause groups:
   `rows(D) = baseline_rows * product(stat_sel / simple_sel)`.

## Invariant

Any branch, tie-break, applicability decision, or transition whose outcome can
change with `D` belongs in `Sq/Fq` as executable semantics. It must not be
serialized as the result observed for the instrumentation design.

## Reference semantics

The v1-B reference build emits native values immediately after
`mcv_combine_selectivities()` and immediately before `clamp_row_est()`. The
external implementation is conforming for this fragment when its output agrees
with those values to floating-point tolerance for every tested design.
