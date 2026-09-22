# PostgreSQL MCV: orthogonal consumption and composition validation

## Method

PostgreSQL 16.15 was tested on Census with MCV target 1000.  The consumption
simulator implements the PostgreSQL 16.14 source rule for ordinary Census
clauses: maximize remaining covered attributes, prefer fewer keys, then lower
OID; consume covered clauses and repeat.

The installed server does not expose selected statistics in `EXPLAIN`.  A
separate instrumented 16.14 build was attempted, but the environment has no C
compiler.  Experiment A therefore uses same-materialization payload ablation:
all objects are built by one `ANALYZE`, then individual `stxdmcv` payloads are
masked and restored without resampling.  An object whose removal changes the
estimate was contributing directly or enabling a substitute selection.

Experiment B is independently concerned with estimate composition.  For each
trial, one `ANALYZE` builds both disjoint objects.  Baseline, both singletons,
and coexistence are then measured from that exact materialization by payload
masking.  This prevents ANALYZE sampling variance from being misclassified as
composition error.

## Experiment A: consumption fidelity

### Overlapping chain, query.184

OID order and simulator input:

```text
good(idisabl1, irspouse)
middle(drpincome, idisabl1)
bad(ddepart, idisabl1)
```

Simulator prediction: `[good]`.

| State | Estimate | Change from full |
|---|---:|---:|
| all payloads | 45 | — |
| mask good | 1,280 | 28.44x |
| mask middle | 45 | none |
| mask bad | 45 | none |

Only the predicted winner contributes to the full state.  Masking either
later overlapping competitor is exactly inert.  Masking `good` exposes the
next candidate (`middle`), as expected from greedy clause consumption.

### Disjoint pair, query.274

Simulator prediction: `[left, right]`.

| State | Estimate | Change from full |
|---|---:|---:|
| all payloads | 179 | — |
| mask left | 18,111 | 101.18x |
| mask right | 502 | 2.80x |

Both objects predicted by GreedyCover materially contribute.  Thus the
simulator correctly distinguishes the one-object overlapping case from the
two-object disjoint case.

Consumption-set fidelity is 2/2 on these targeted structures.  Exact sequence
order for the disjoint pair is not behaviorally identifiable because the AND
composition is multiplicative; its order is source-derived rather than
directly observed.  Direct sequence instrumentation remains a useful future
check when a compiler/debug build is available.

## Experiment B: cardinality composition fidelity

For disjoint objects `a,b`, test the first-order ratio reconstruction

\[
\widehat N_{ab}=\frac{\widehat N_a\widehat N_b}{\widehat N_0}.
\]

| Query/order | Baseline | Singleton a | Singleton b | Predicted | Observed | Deviation |
|---|---:|---:|---:|---:|---:|---:|
| q184 a→b | 54,023 | 47 | 57,633 | 50.14 | 50 | 1.0028x |
| q184 b→a | 53,918 | 34 | 57,519 | 36.27 | 36 | 1.0075x |
| q62 a→b | 93,550 | 28 | 105,058 | 31.44 | 31 | 1.0143x |
| q62 b→a | 93,659 | 74 | 105,122 | 83.06 | 83 | 1.0007x |
| q274 a→b | 50,777 | 500 | 18,008 | 177.32 | 177 | 1.0018x |
| q274 b→a | 50,594 | 510 | 17,805 | 179.48 | 179 | 1.0027x |

Across all six trials:

- median multiplicative deviation: **1.00274x**;
- maximum multiplicative deviation: **1.01434x**;
- within 10%: **6/6**;
- within 20%: **6/6**.

The earlier independently-ANALYZEd version produced misleading deviations up
to 2.33x on rare predicates.  Same-sample masking reduces the maximum to 1.014x,
showing that the discrepancy was sampling variance rather than a failure of
cardinality-domain composition.

## Conclusion

On these targeted Census cases, the two layers validate independently:

\[
\text{PG response}
\approx
\text{source-derived GreedyCover consumption}
+
\text{first-order cardinality ratio composition}.
\]

This supports a three-layer implementation boundary:

1. Consumption IR selects the ordered MCV subset from clause state and OID.
2. Estimation IR composes compatible rounds in selectivity/cardinality space.
3. Objective IR converts the resulting cardinality to q-error or another loss.

The evidence is deliberately scoped to MCV statistics, simple single-table
AND predicates, disjoint two-column composition, and PG16.  Dependencies,
expressions, OR clauses, wider statistics, and more than two composed rounds
remain outside the validated domain.

All probe objects were removed; post-run catalog counts were zero.

## Artifacts

- `tools/validate_pg_consumption_composition.py`
- `results/census_pg_consumption_composition.json`
