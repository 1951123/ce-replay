# PostgreSQL first-applicable reconstruction pilot

## Question

Test the parameter-free hypothesis

\[
\widehat e_q(\pi)=e_{q,\operatorname{first}_\pi(A_q)}
\]

on PostgreSQL 16.15 using singleton measurements made in the same run and
freshly materialized statistics for every permutation.  All objects are MCV
statistics with target 1000.

## Results

### Three statistics sharing one anchor column (`query.184`)

Singleton estimates:

| Stat | Columns | Estimate |
|---|---|---:|
| good | `(idisabl1, irspouse)` | 61 |
| middle | `(drpincome, idisabl1)` | 1,292 |
| bad | `(ddepart, idisabl1)` | 78,393 |

| First-created stat | Two suffix orders, observed estimates | Predicted singleton |
|---|---:|---:|
| good | 48, 63 | 61 |
| middle | 1,219, 1,274 | 1,292 |
| bad | 78,024, 78,433 | 78,393 |

All 6 permutations are within 2x of the first singleton; 5/6 are within 20%.
The maximum deviation is 1.27x.

### Three pairwise-overlapping statistics (`query.221`)

The three column pairs form a triangle: every pair of statistics overlaps, but
there is no column common to all three.

| First-created stat | Two suffix orders, observed estimates | Predicted singleton |
|---|---:|---:|
| `ab` | 1,275, 1,271 | 1,149 |
| `ac` | 130,826, 130,107 | 128,897 |
| `bc` | 291,119, 289,237 | 289,731 |

All 6 permutations are within 20% of the first singleton.  The maximum
deviation is 1.11x.

### Two disjoint statistics (`query.274`)

| Stat | Columns | Singleton estimate |
|---|---|---:|
| left | `(drearning, dweek89)` | 520 |
| right | `(dhour89, imeans)` | 18,002 |

| Creation order | First-singleton prediction | Observed | Deviation |
|---|---:|---:|---:|
| left -> right | 520 | 178 | 2.92x |
| right -> left | 18,002 | 182 | 98.91x |

The coexistence response is nearly order-independent and substantially better
than either singleton.  PostgreSQL therefore used information from both
disjoint statistics; global `ChooseOne` is falsified.

## Interpretation

Across the two mutually conflicting/overlapping scenarios, singleton
reconstruction succeeds for all 12 permutations within 2x and for 11/12 within
20%.  In those cases, changing the suffix order while keeping the first object
fixed has little effect.  This is strong evidence for first/lower-OID precedence
inside an overlap-conflict group.

The disjoint scenario establishes that a query is not restricted to one
extended-statistics object.  A better hypothesis is:

\[
(Y,\pi)
\longrightarrow
\text{an ordered, mutually compatible subset of applicable stats}
\longrightarrow
F_q.
\]

One concrete candidate semantics is an OID-ordered greedy selection: an early
stat blocks overlapping competitors, while non-overlapping stats may both be
consumed.  The current experiment supports this shape but does not establish
the exact PostgreSQL compatibility predicate or selection algorithm.

Consequently, the first PG response IR should likely be richer than global
`ChooseOne + Precedence`.  It needs at least:

- applicability of a statistic to query clauses;
- precedence among conflicting statistics;
- compatibility/composability between non-conflicting statistics;
- selection of a compatible winner set rather than one global winner.

The probe cleaned all temporary objects.  A post-run catalog check found zero
extended statistics on `climate` and zero probe-prefixed objects.

## Reproduction

```bash
../extended-stats-optim-v2/.venv/bin/python \
  tools/probe_pg_first_applicable.py \
  --output results/census_pg_first_applicable_pilot.json
```
