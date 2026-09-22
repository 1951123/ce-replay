# PostgreSQL creation/OID-order probe: Census query.184

## Setup

- PostgreSQL 16.15
- Census `climate`: 2,458,285 rows
- Query truth: 13 rows
- Extended-statistics target: 1000
- `good`: MCV on `(idisabl1, irspouse)`
- `bad`: MCV on `(ddepart, idisabl1)`

The names describe their isolated behavior for this query, not a global
property.  Both statistics are applicable and overlap on `idisabl1`.  Each
regime drops the probe objects, creates them in the stated order, runs one
`ANALYZE climate`, and obtains a fresh `EXPLAIN (FORMAT JSON)` estimate.  The
catalog OIDs were recorded to verify that creation order and ascending OID
order agree.

## Results

| Regime | Trial | Estimate | Q-error |
|---|---:|---:|---:|
| no extstat | 1 | 52,900 | 4,069.23 |
| good only | 1 | 52 | 4.00 |
| bad only | 1 | 77,817 | 5,985.92 |
| good then bad | 1 | 25 | 1.92 |
| good then bad | 2 | 52 | 4.00 |
| good then bad | 3 | 59 | 4.54 |
| bad then good | 1 | 78,256 | 6,019.69 |
| bad then good | 2 | 78,762 | 6,058.62 |
| bad then good | 3 | 78,244 | 6,018.77 |

With the same selected set, `good -> bad` has mean estimate 45.3 while
`bad -> good` has mean estimate 78,420.7: a roughly 1,730x difference caused by
physical creation/OID order.  Each coexistence regime closely tracks the
corresponding first-created singleton response despite independent `ANALYZE`
samples.

## Interpretation

For this query and PostgreSQL version, the observation is consistent with an
earliest-applicable/lower-OID winner model:

```text
good has lower OID -> response resembles good-only
bad  has lower OID -> response resembles bad-only
```

This is strong evidence that the physical PG response cannot be represented by
the selected set `Y` alone; order information is necessary.  It is one-query,
one-pair evidence and should not yet be generalized into a cross-version public
PostgreSQL semantic guarantee.  More queries and overlapping-set shapes are
needed to test whether `ChooseOne + Precedence` is sufficient in general.

The probe's `finally` cleanup removed both temporary statistics.  A post-run
catalog check found zero extended statistics on `climate` and zero objects with
the probe prefix.

## Reproduction

```bash
../extended-stats-optim-v2/.venv/bin/python \
  tools/probe_pg_order_census.py \
  --repeats 3 \
  --output results/census_pg_order_query184.json
```
