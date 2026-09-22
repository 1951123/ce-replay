# Census CE-Replay-IR-v0 validation

## Question

Can a fixed PostgreSQL cardinality-estimation graph be instrumented once and
then replayed outside PostgreSQL for different extended-statistics designs,
without replanning during replay?

This v0 experiment deliberately tests a narrow slice:

- PostgreSQL 16 base-relation `AND` restrictions;
- Census `query.184` on `climate` (actual cardinality: 13);
- five two-column MCV candidates;
- PostgreSQL's greedy statistics-object consumption rule;
- multiplicative composition of independently consumed MCV responses.

## Experimental design

The five candidates are created in a fixed OID order. The first three overlap
on `idisabl1`, so after one is consumed the other two become ineligible:

| ID | Columns | Role |
|---|---|---|
| `good` | `idisabl1, irspouse` | conflicting candidate |
| `middle` | `drpincome, idisabl1` | conflicting candidate |
| `bad` | `ddepart, idisabl1` | conflicting candidate |
| `independent_1` | `ienglish, iimmigr` | independent clause group |
| `independent_2` | `ilooking, imay75880` | independent clause group |

All objects are populated by one `ANALYZE`. Catalog payload masking then
extracts, from that same sample, the no-MCV baseline and each singleton atomic
response. The resulting IR contains candidate columns, physical OID rank,
atomic cardinality ratio, and the following transition semantics:

1. eligible objects cover at least two remaining clauses;
2. choose maximum coverage, then fewer total keys, then lower OID rank;
3. remove the winner's covered columns;
4. repeat.

For a hypothetical design `D`, pure Python reruns this transition and computes

`N(D) = N0 * product(Ns / N0)`

over the replayed consumption sequence. PostgreSQL `EXPLAIN` is invoked for
each design only as an oracle after the external prediction has been formed.
All 32 subsets of the five candidates are tested.

## Result

| Metric | Result |
|---|---:|
| Designs | 32 |
| Exact after rounding | 23 |
| Within 1% | 28 |
| Within 5% | 32 |
| Median relative error | 0.00596% |
| Maximum relative error | 1.08087% |
| Maximum deviation factor | 1.01081x |

The worst case is `{good, independent_1}`: replay predicts 57.616 rows and
fresh PostgreSQL planning reports 57 rows. Adding `middle` and/or `bad` does not
change either the replayed sequence or PostgreSQL's estimate because `good`
has already consumed their shared `idisabl1` clause.

## Interpretation

The experiment validates the proposed architectural seam for this narrow
scope:

`instrument once -> fixed IR -> vary design -> external replay -> PG oracle`

In particular, the IR records transition semantics rather than freezing a
single winning object. Consequently, changing the selected design changes the
winner sequence without rebuilding the graph.

It does **not** yet establish complete source-level replay of PostgreSQL's
numeric estimator. The v0 atomic MCV responses are measured once using
same-sample singleton payload masking, and independent responses are composed
as cardinality ratios. The residual 1.08% worst-case error is consistent with
that approximation plus row rounding. A stronger v1 must serialize MCV
payloads and reproduce `mcv_clauselist_selectivity` and the surrounding base
selectivity arithmetic directly, eliminating singleton measurement as a
numeric oracle.

## Artifacts

- Runner: `tools/ce_replay_ir_v0.py`
- Full IR and all per-design comparisons: `results/census_ce_replay_ir_v0.json`

The runner removes every temporary extended-statistics object in a `finally`
block. A post-run catalog check found zero remaining objects on `climate`.
