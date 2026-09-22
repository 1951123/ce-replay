# Census query--candidate locality

## Definition

The graph uses one node per Census query and one node per distinct physical
candidate column set `(table, unordered columns)`.  An edge means that the
candidate was generated from the query's predicate columns.  Representation
parameters are not expanded because doing so only duplicates neighborhoods and
does not change query connectivity.

The primary setting is arity 2, matching the v2 Census measurement pipeline.
Arity 2+3 is included as a sensitivity check.  Counts were independently
checked against v2's `sqlglot` candidate generator.

## Results

| metric | arity 2 | arity 2+3 |
|---|---:|---:|
| queries | 468 | 468 |
| candidate-bearing queries | 467 | 467 |
| distinct candidates | 2,253 | 19,245 |
| edges | 9,998 | 30,856 |
| connected components | 2 | 2 |
| giant component queries | 467 (99.79%) | 467 (99.79%) |
| giant component candidates | 2,253 (100%) | 19,245 (100%) |
| bipartite density | 0.9482% | 0.3426% |
| query degree, mean / median / max | 21.36 / 21 / 91 | 65.93 / 56 / 455 |
| candidate degree, mean / median / max | 4.44 / 4 / 13 | 1.60 / 1 / 13 |
| candidates used by one query only | 130 (5.77%) | 13,801 (71.71%) |

The second component is a single query with only one predicate column, so it
has no candidate and no edge under either candidate definition.

## Interpretation

Census has almost no useful **strict component locality**.  All physical
candidate variables belong to one component containing 467 of 468 queries, so
component-local optimization followed by global budget allocation cannot split
the substantive workload.

It nevertheless has strong **degree/sparsity locality**.  Under the primary
arity-2 definition, a query touches 21.36 of 2,253 candidates on average and a
candidate touches 4.44 of 468 queries; only 0.9482% of all possible bipartite
edges exist.  Thus the right follow-up for Census is decomposition or local
search *inside* the giant sparse component, rather than connected-component
factorization.

Adding triples does not alter connectivity because every shared triple also
contains shared pairs.  It mainly adds query-private variables: 71.71% of the
arity-2+3 candidates have degree one.  This makes the graph still sparser but
does not break the giant component.

## Candidate-degree histogram

| candidate degree | arity 2 count (ratio) | arity 2+3 count (ratio) |
|---:|---:|---:|
| 1 | 130 (5.77%) | 13,801 (71.71%) |
| 2 | 287 (12.74%) | 3,126 (16.24%) |
| 3 | 372 (16.51%) | 797 (4.14%) |
| 4--5 | 837 (37.15%) | 894 (4.65%) |
| 6--10 | 615 (27.30%) | 615 (3.20%) |
| >10 | 12 (0.53%) | 12 (0.06%) |
| >50 | 0 | 0 |

The maximum degree is only 13.  The 2+3 graph therefore does not have an
extreme hub tail: after the private candidates, most of the remaining mass is
degree 2 or 3.  This favors the "many low-degree stitches" hypothesis over the
"few global hubs" hypothesis.

## Static high-degree peeling

For each threshold `k`, the experiment removes all candidates whose degree in
the original graph is greater than `k`.  Query nodes, including newly isolated
ones, remain in the denominator.

### Arity 2+3

| retain degree <= k | candidates removed | components | giant-query ratio |
|---:|---:|---:|---:|
| 13 | 0% | 2 | 99.79% |
| 8 | 0.45% | 2 | 99.79% |
| 7 | 0.98% | 4 | 99.36% |
| 5 | 3.26% | 10 | 98.08% |
| 4 | 5.25% | 14 | 97.22% |
| 3 | 7.90% | 21 | 95.73% |
| 2 | 12.04% | 33 | 93.16% |
| 1 | 28.29% | 468 | 0.21% |

Removing roughly the highest-degree 1%, 5%, or even 12% of candidates does not
collapse the giant component.  It collapses only when all shared candidates,
including degree-2 candidates, are removed.  Census therefore does **not** have
a small high-degree coupling backbone.  Global connectivity is accumulated
through many low-degree candidate links.

There is also an arity-sensitive detail: after retaining only degree <=2,
arity 2 alone has a 48.29% giant, whereas arity 2+3 retains a 93.16% giant.
Degree-2 triples can preserve links whose constituent pairs have higher global
degree and were peeled.  Thus candidate arity does not change the original
components, but it can materially change the low-degree residual graph.

## Candidate interaction neighborhood

For candidate `s`, define

\[
N(s)=\bigcup_{q\in Q(s)} A_q.
\]

The reported size includes `s` itself.  Thus `|N(s)|-1` is the number of other
candidate marginal values that may need invalidation after moving `s`.

| metric | arity 2 | arity 2+3 |
|---|---:|---:|
| mean | 128.30 | 206.62 |
| median | 124 | 165 |
| p90 | 214 | 438 |
| p95 | 243 | 555 |
| p99 | 303.96 | 879 |
| maximum | 409 | 1,796 |
| mean as fraction of all candidates | 5.69% | 1.07% |
| median as fraction of all candidates | 5.50% | 0.86% |
| p99 as fraction of all candidates | 13.49% | 4.57% |
| maximum as fraction of all candidates | 18.15% | 9.33% |

For the main arity-2+3 space, a move invalidates about 207 of 19,245 candidate
marginals on average, rather than all 19,245.  This is approximately a 93x
reduction in structural invalidation scope.  At the median it is about 117x;
even p99 touches only 4.57% of the candidate space.

The candidate interaction graph has 1,978,615 edges and density 1.07% for
arity 2+3.  For arity 2 it has 143,400 edges and density 5.65%.  Therefore the
interaction graph is connected but its one-hop update neighborhoods remain
small relative to the full decision space.

Conditioning on candidate degree shows the expected growth: arity-2+3
degree-1 candidates have mean `|N(s)|=140.65`, degree-2 candidates 269.53, and
degree-3 candidates 367.05.  The degree-1 mean exceeds the unweighted mean
query degree (65.93) because selecting a candidate samples queries in
proportion to how many such candidates they own; high-arity queries are
therefore overrepresented.

This result directly supports dependency-aware priority invalidation:

\[
19{,}245\ \text{global marginal recomputations}
\quad\longrightarrow\quad
206.62\ \text{on average per move}.
\]

## Reproduction

```bash
python3 tools/analyze_locality.py \
  ../extended-stats-optim-v2/benchmarks/Census/queries/query.sql \
  --arities 2 --json results/census_locality_arity2.json \
  --csv-prefix results/census_locality_arity2

python3 tools/analyze_locality.py \
  ../extended-stats-optim-v2/benchmarks/Census/queries/query.sql \
  --arities 2,3 --json results/census_locality_arity2_3.json \
  --csv-prefix results/census_locality_arity2_3
```
