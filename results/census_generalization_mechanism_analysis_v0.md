# Generalization-Mechanism-Analysis-v0

## 1. Experimental scope

This is an offline mechanism analysis of the exact ten frozen-payload splits
from `Workload-Generalization-v0`. It creates no splits, runs no `ANALYZE`, and
does not rerun or change optimization. The unit is `(split, held-out query)`:
940 instances. Every instance has complete no-extstats, train-design and
test-oracle MCV/FD traces plus contextual remove-one and missing-oracle add-one
counterfactuals.

All attributions are contextual. Candidate effects interact and must not be
summed as an exact decomposition of design value.

## 2. Reproduction of v0 transfer totals

The analysis independently reproduces 412 positive, 216 neutral and 312
negative instances. Positive q-error-change magnitude is `10223.960956`;
negative magnitude is `160.315083`. Regression concentration is also exactly
reproduced: top one query `44.70%`, top four `70.85%`, top ten `80.02%`.

Positive transfer is even more concentrated: top one query contributes
`41.28%`, top four `94.12%`, and top ten `98.51%` of positive magnitude.

## 3. Positive-transfer mechanism decomposition

| Supported mechanism | Instances | Positive magnitude | Share |
|---|---:|---:|---:|
| MCV-only | 310 | 3581.329 | 35.03% |
| FD-only | 24 | 0.556 | 0.01% |
| MCV+FD composed | 78 | 6642.077 | 64.97% |

Thus most positive *magnitude* is mediated by composed MCV+FD behavior, while
MCV-only dominates the count. Eighty-nine positive instances exhibit an
MCV-to-FD control difference relative to applying the same FD set without MCV.
This is direct behavioral evidence of transferable native CE structure, not an
inference from physical selection overlap.

## 4. Negative-transfer mechanism decomposition

| Supported mechanism | Instances | Negative magnitude | Share |
|---|---:|---:|---:|
| MCV-only | 243 | 76.059 | 47.44% |
| FD-only | 29 | 72.198 | 45.04% |
| MCV+FD composed | 40 | 12.058 | 7.52% |

MCV dominates regression count, but a small number of FD-only regressions carry
nearly equal magnitude. Multi-label trace/counterfactual diagnosis finds 162
harmful MCV corrections, 87 MCV winner replacements, 47 harmful FD
corrections, 42 MCV-to-FD suppression cases, and 102 cases whose complete
regression cannot be eliminated by every individual attribution equally.

## 5. Harmful presence versus missing benefit

Among 312 negative instances, 188 have both a harmful consumed candidate and a
useful missing-oracle candidate, 91 have harmful presence only, 24 have missing
benefit without an individually harmful consumed candidate, and nine remain
unresolved. Negative transfer itself is therefore primarily harmful presence;
coverage failure frequently co-occurs but is conceptually distinct.

Across all held-out instances, the positive train-design-to-test-oracle gap is
`11278.004914`. Adding only the best individually useful missing oracle
candidate, ignoring budget, recovers `10135.678089` (`89.87%`) diagnostically.
This is missed opportunity, not negative transfer relative to no extstats.

## 6. `query.62` deep case study

`query.62` is held out in seeds 1 and 6.

In seed 1 the train design consumes no relevant statistic. Its estimate stays
at `94191.9795` rows and q-error `2093.1551`, equal to no extstats. The test
oracle consumes MCV 840 and 990 and reaches `124.3768` rows, q-error `2.7639`.
Adding missing MCV 990 alone to the train design yields q-error `2.7674`.

In seed 6, train-selected FD 552 (`irvetserv → ivietnam`, degree `1.0`, cost 27
bytes) is consumed. It raises the estimate from `94191.9795` to `97416.4654`
and q-error from `2093.1551` to `2164.8103`, producing the entire `71.6552`
regression. Removing FD 552 restores the no-extstats result exactly. The test
oracle again uses MCV 840/990 and reaches q-error `2.7639`; adding MCV 990 to
the train design would yield `2.8622`.

The training chain is concrete: FD 552 is also incident to training
`query.386`, which consumes it after MCV 32 together with FDs 326/322/325.
Its final-design leave-one-out training benefit is small but positive
(`0.004686` q-error). Hence:

`query.386 benefit → FD 552 selected → degree-1 FD correction on query.62 → negative transfer`.

Both missing MCVs have no positive final-design training marginal (`S1`), so
their absence is supervision/coverage failure, not observed local-search
failure. The seed-6 outcome contains both harmful presence and missing benefit.

## 7. Top regression-query analysis

- `query.62`: two held-out appearances, one regression, `71.6552` magnitude;
  uniquely caused by FD 552 in seed 6.
- `query.274`: two appearances and two regressions, `19.4984` total. Seed 3 is
  dominated by MCV 691; seed 4 by MCV 2/190. This is split-specific winner
  replacement, not one recurring candidate.
- `query.361`: five appearances, three regressions, `12.5186` total. MCV 1099
  recurs in all three negative cases; two other splits are positive. The
  failure is candidate-recurring but design-context dependent.
- `query.161`: three appearances, two regressions, `9.9046` total. MCV 835
  recurs in both, with MCV 529 joining once; the third split is strongly
  positive through a different MCV path.

Overall concentration comes from a mixture: a few recurring candidates
(especially MCV 1099 and 835) plus large split-specific failures (FD 552 and
the alternative `query.274` winners). Context, not candidate identity alone,
determines the sign.

## 8. Candidate-level train-to-test transfer

The candidate CSV reports cost, structural incidence, consumers, positive and
negative contextual effects, aggregate diagnostic benefit, and selection
frequency. Diagnostic harmful leave-one-out magnitude is concentrated: MCV 188
accounts for `29.71%` and the top five candidates (MCV 188/691/2/79 and FD 552)
for `78.34%`. This concentration is informative but non-additive.

The largest positive diagnostics are MCV 833, 530, 880, 29 and 826. These are
the main paths by which a modest number of shared distributions dominate the
aggregate held-out gain.

## 9. Counterfactual repair analysis

Allowing each negative query instance to independently remove its single best
harmful consumed statistic eliminates `150.488658 / 160.315083`, or **93.87%**,
of negative-transfer magnitude. Negative transfer is therefore overwhelmingly
low-order and locally repairable in diagnostic terms. This is not a feasible
global design: different queries can demand conflicting removals.

## 10. Missing-oracle and budget displacement

Best single missing-candidate additions recover **89.87%** of the positive
train-to-oracle gap when budget is ignored. Among 692 important best-missing
diagnostics, 619 are `S1` (no positive training signal) and 73 are `S2`
(positive signal but budget pressure). Twenty-five negative instances receive
an N7 budget-displacement label after a useful missing candidate has positive
training marginal but cannot be added within the final budget.

This shows that missing coverage is principally absent training signal, with a
smaller real budget component. Candidate difference alone was not treated as
budget displacement.

## 11. Solver failure versus supervision failure

No `S3` case was found: there is no important best-missing candidate with a
positive feasible ADD, nor a positive feasible SWAP after checking all selected
objects that free enough space. The observed categories are 619 `S1` and 73
`S2`. Within the tested neighborhood, evidence points to supervision/coverage
and budget pressure, not local-search termination failure. Interaction-dependent
higher-order alternatives remain untested.

## 12. Behavior-space versus design-space stability

Across 45 pairs, mean physical-design Jaccard is `37.04%`, but only `32.23%` of
queries have identical complete MCV+FD control traces and `32.78%` have rows
identical within `1e-12`. Mean row relative difference is `8.51%`; mean absolute
q-error difference is `4.621`.

Physical overlap strongly tracks behavior: Pearson correlation between design
Jaccard and identical control is `0.811` (Spearman `0.819`). FD traces alone
match `76.15%`, partly because FD consumption is frequently empty; MCV traces
match only `36.98%`. The physically different designs therefore do **not**
exhibit broadly redundant CE behavior over the 468 observed queries.

## 13. Stable statistical core

The 26 universal candidates (19 MCV, 7 FD) have per-selection test positive and
negative frequencies `0.308` and `0.188`, with net aggregate contextual test
benefit `+261.97`. Rare 1–4/10 candidates reverse this balance (`0.237`
positive, `0.298` negative; net `-529.67`). Thus the universal set is a genuine
transferable core relative to rare selections.

It is not the sole or strongest value-bearing group: 8–9/10 and 5–7/10 groups
have larger per-selection diagnostic benefits (`5.01` and `6.08`, versus
`1.01` for 10/10), driven by major query-specific gains. Universality indicates
reliable positive tendency, not exclusive importance.

## 14. Limitations

This is frozen-payload, Census-specific, random-query analysis. It does not
establish template-disjoint, distribution-shift, cross-database,
cross-PostgreSQL-version, fresh-`ANALYZE`, or globally optimal behavior.
Leave-one-out/add-one effects are contextual; the budget diagnosis checks the
existing ADD/SWAP neighborhood, not higher-order redesigns. The global
candidate universe still exposes held-out predicate structure.

## 15. Final verdict

1. **What semantic mechanisms produce most positive held-out transfer?**  
   By magnitude, MCV+FD composition produces **64.97%** and MCV-only **35.03%**; FD-only is negligible. By count, MCV-only dominates (310/412).

2. **What semantic mechanisms produce most negative held-out transfer?**  
   MCV-only and FD-only contribute **47.44%** and **45.04%** of magnitude; composed paths contribute 7.52%. MCV winner/correction effects dominate count.

3. **Is negative transfer primarily harmful presence, missing useful statistics, or both?**  
   Primarily harmful presence for the regression itself: 279/312 negative instances have an individually harmful consumed candidate. Both occur in 188; missing-only occurs in 24. Missing benefit primarily explains the oracle gap.

4. **Why does `query.62` regress so strongly?**  
   In seed 6, degree-1 FD 552, selected through a small benefit on training `query.386`, raises `query.62` q-error by `71.6552`. Missing MCV 990 simultaneously leaves a roughly three-orders-of-magnitude coverage failure.

5. **Is concentration caused by recurring statistics or split-specific designs?**  
   **Both.** MCV 1099 and 835 recur, while FD 552 and `query.274`'s alternative MCV winners are split-specific. The sign changes with design context.

6. **How much negative-transfer magnitude can one removal repair?**  
   **93.87%** diagnostically (`150.4887/160.3151`).

7. **How much of the train-test gap is attributable to missing test-oracle statistics?**  
   Best single missing additions recover **89.87%** of the positive train-to-oracle q-error gap when budget is ignored. This is a contextual upper diagnostic, not an additive causal decomposition.

8. **Why are important missing statistics absent?**  
   Mostly no training signal: 619 `S1` versus 73 budget-pressure `S2`; no positive feasible ADD/SWAP `S3` was observed. There is no current evidence of ordinary local-search termination failure.

9. **Do physically different train designs exhibit similar CE behavior?**  
   **Not broadly.** Only 32.23% of full-workload control traces and 32.78% of row outputs match; physical overlap and behavioral match are strongly correlated.

10. **Do the 26 universal candidates form a transferable core?**  
    **Yes, descriptively:** they have positive net transfer and a better positive/negative balance than rare candidates. They are not uniquely responsible for the largest benefits.

11. **Does the optimizer learn transferable data-distribution structure?**  
    **Yes, moderately.** Actual held-out MCV/FD consumption—especially composed paths—produces large benefits. The same semantics also create concentrated negative transfer, and missing training coverage remains substantial.

12. **What remains unexplained?**  
    How budget changes the S2/negative-transfer frontier; whether latent-template separation removes much of the observed transfer; whether higher-order swaps repair unresolved interactions; and whether these mechanisms survive fresh payloads, distribution shift, or other databases.
