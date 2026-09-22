# Structural-Distance-Generalization-v0

## Scope and definitions

This is an observational analysis of the existing 940 held-out instances. It
does not create splits, rerun optimization, run `ANALYZE`, or implement an
embargo. It reproduces 412 positive, 216 neutral and 312 negative outcomes,
with positive/negative magnitudes `10223.960956/160.315083`.

For each query, `C` is its predicate-column set; `P2` contains every unordered
predicate-column pair; `N_MCV` and `N_FD` contain typed candidates structurally
relevant under the optimizer's existing dependency mapping; and `N` is their
union. Neighborhoods do not depend on selection or consumption.

Operator compatibility gives a shared column credit only when its
equality/lower/upper operator-class multiplicities match, divided by the union
column count. Candidate support is the number of train queries whose structural
neighborhood contains that candidate.

## Structural-distance distributions

| Metric | Minimum | Mean | Median | Maximum |
|---|---:|---:|---:|---:|
| Nearest column Jaccard | 0.231 | 0.339 | 0.333 | 0.500 |
| Nearest candidate Jaccard | 0.000 | 0.115 | 0.111 | 0.333 |
| Maximum test-pair containment | 0.000 | 0.291 | 0.278 | 1.000 |
| Column union coverage | 1.000 | 1.000 | 1.000 | 1.000 |
| Pair/MCV union coverage | 0.000 | 0.968 | 1.000 | 1.000 |
| FD union coverage | 0.000 | 0.980 | 1.000 | 1.000 |
| Typed candidate union coverage | 0.000 | 0.970 | 1.000 | 1.000 |
| Selected candidate coverage | 0.000 | 0.098 | 0.093 | 1.000 |

The train workload therefore covers essentially the entire structural support
universe: every test column, and about 97% of pair/candidate scopes on average.
The optimizer selects only about 9.8% of each held-out neighborhood. This
separates structural availability from deployed information capacity.

## Metric audit

| Metric | Transfer Pearson / Spearman | Consumption Pearson / Spearman | Oracle-gap Pearson / Spearman |
|---|---:|---:|---:|
| Nearest column Jaccard | -0.000 / -0.003 | -0.074 / -0.063 | -0.004 / -0.127 |
| Nearest candidate Jaccard | 0.040 / 0.052 | 0.104 / 0.114 | 0.014 / 0.026 |
| Pair union coverage | -0.004 / 0.014 | 0.082 / -0.057 | -0.011 / -0.159 |
| Candidate union coverage | 0.005 / 0.016 | 0.101 / -0.053 | -0.008 / -0.163 |
| Mean candidate support | 0.018 / 0.063 | 0.155 / 0.151 | -0.024 / -0.046 |
| Selected candidate coverage | 0.008 / 0.076 | **0.544 / 0.644** | -0.044 / 0.058 |

No pre-selection structural metric has a meaningful monotonic association with
transfer. Nearest-query similarity and union coverage are both weak. The one
strong relationship is post-optimization selected coverage with consumption,
which identifies where the chain actually filters information but is not a
valid pre-split embargo metric.

Maximum pair containment has a moderate negative Spearman association with
oracle gap (`-0.378`), but almost none with transfer (`-0.019`) and its binned
behavior is non-monotonic. It is evidence worth retaining, not enough to choose
a controlled embargo threshold.

## Coverage bins and the coverage–selection–consumption chain

Candidate-union coverage is too concentrated for a clean dose-response curve.
The four unique-value bins have coverage ranges `0–0.920`,
`0.921–0.951`, `0.951–0.970`, and `0.971–1.0`. Their consumption probabilities
are `64.2%, 85.7%, 91.5%, 76.6%`, while relative aggregate improvements are
`64.2%, -1.3%, 84.5%, 34.1%`. Neither sequence is monotonic.

By contrast, higher selected-neighborhood coverage strongly predicts actual
consumption. The chain is therefore:

`near-universal train structural coverage → strong optimizer filtering → consumption → context-dependent sign`.

Structural coverage rarely breaks. Selection is the primary bottleneck;
consumption then creates both positive and harmful native CE behavior.

## Coverage, oracle gap, and no-training-signal failures

No-training-signal cases have mean candidate coverage `0.9694`; other cases
have `0.9702`. Pair coverage and nearest candidate similarity are likewise
nearly identical. They are not concentrated in low structural coverage.

Their selected coverage differs: `0.0829` versus `0.1285`. Thus “no training
signal” usually means that widely existing scopes did not improve the train
objective enough to be selected—not that their columns/candidates were absent
from the train workload. Binary structural coverage is too coarse to capture
payload usefulness and objective alignment.

## Harmful presence

Instances with harmful consumed candidates have slightly *higher* mean
candidate coverage (`0.9727` versus `0.9672`) and much higher selected coverage
(`0.1212` versus `0.0795`). Harmful presence is not a low-coverage phenomenon.
It is concentrated after selection, especially in intermediate coverage bins,
and remains highly non-monotonic because a few queries dominate magnitude.

## MCV versus FD

MCV and FD structural coverage are both saturated. Their correlations with
mechanism-specific consumption are negligible: MCV Pearson/Spearman
`0.081/-0.048`, FD `0.016/-0.069`. Mean MCV/FD coverage differs little across
MCV-only, FD-only, and composed executions.

The mechanisms nevertheless differ after selection: MCV-only paths contribute
net transfer `+3505.27`, MCV+FD composed paths `+6630.02`, and FD-only paths
`-71.64`, the latter dominated by `query.62`. Structural coverage cannot
predict these control/numerical outcomes.

## Candidate support multiplicity

| Train support | Selection probability | Consumption events | Positive / negative probability per consumption |
|---:|---:|---:|---:|
| 0 | 0.00% | 0 | — |
| 1 | 4.48% | 49 | 61.22% / 38.78% |
| 2–3 | 9.25% | 427 | 55.50% / 42.62% |
| 4+ | 11.59% | 830 | 53.86% / 43.98% |

Repeated support makes a candidate more likely to be selected and consumed,
but not more reliably beneficial. The positive-effect fraction declines and
the negative fraction rises slightly with support. Support is an exposure or
confidence-of-use signal, not a confidence-of-correctness signal.

## `query.62` and major regressions

`query.62` is not especially distant: nearest column/candidate Jaccards are
`0.364/0.127`. It has 100% column coverage, 92.86% pair coverage and 93.18%
candidate coverage. Yet selected coverage is 0% in seed 1 and only 2.27% in
seed 6. Seed 6 consumes harmful FD 552; both splits miss MCV 990 with no train
signal. It is therefore **structurally well covered but incorrectly adapted**:
coverage exists, selection/payload semantics fail.

The other major regressions tell the same story. `query.274`, `query.361`, and
`query.161` have candidate coverage around 94–99%, but regress through selected
MCV winner paths. High structural coverage does not prevent harmful semantic
adaptation.

## Low-similarity successes

There are genuine low-nearest-similarity transfers with high union coverage:

- seed 0 `query.374`: nearest candidate Jaccard `0.074`, union coverage
  `0.986`, transfer `+4.944`, consuming MCV 158/1493 and FD 404/85;
- seed 9 `query.468`: `0.083`, coverage `1.0`, transfer `+4.038`, consuming MCV
  4/68;
- `query.81`: `0.081`, coverage `0.90–0.967`, transfer `+3.884`, consuming MCV
  126/633.

These show that no close query analogue is required when useful scopes are
collectively exposed by the workload. They do not establish that union
coverage generally predicts magnitude.

Low-coverage success also exists, but is generally modest: e.g. seed 6
`query.313` has candidate coverage `0.667` and transfer `+0.303` through one
selected MCV. This demonstrates that equally weighting all relevant candidates
understates the value of a small useful subset.

## High-coverage failures

Coverage is plainly insufficient. Examples with 100% candidate coverage
include a `query.61` instance with a `977.61` oracle gap, `query.123` with
negative transfer `-1.887`, and multiple `query.159`/`query.405` harmful MCV/FD
paths. Their failures arise from missing objective signal, candidate
competition and harmful selected semantics rather than missing structure.

## Decision gate

The proposed similarity embargo is **not justified yet**. No nearest-query or
union-coverage metric meaningfully tracks held-out transfer, and the strongest
structural association (pair containment with oracle gap) is non-monotonic and
does not track transfer itself. Choosing a threshold now would be arbitrary.

A better next controlled experiment would first need a richer pre-selection
distance that weights candidates by potential payload relevance or train-side
objective evidence, followed by an audit that it remains label-free. Selected
coverage must not be used for the embargo because it is design-dependent.

## Limitations

This is observational, frozen-payload, Census-specific analysis over random
IID splits. Coverage is nearly saturated, limiting identifiability. Candidate
counts weight all scopes equally despite very different value. Correlation
does not establish causality, and no conclusions extend to templates,
distribution shift, other databases, fresh `ANALYZE`, or unseen candidate
generation.

## Final verdict

1. **Does held-out transfer decrease as queries become structurally farther from the training workload?**  
   **Not measurably under these metrics.** All nearest/union measures have transfer correlations close to zero and non-monotonic bins.

2. **Which is more informative: nearest-query similarity or whole-workload semantic coverage?**  
   Neither explains transfer well. Union coverage better documents that structure is almost universally available; nearest similarity adds little.

3. **Is column overlap sufficient, or is candidate-neighborhood coverage more informative?**  
   Column coverage is completely saturated at 100%. Candidate coverage is richer but still saturated and weakly associated with outcomes; it is more informative descriptively, not predictively.

4. **Does higher semantic coverage increase consumption probability?**  
   Not monotonically for structural coverage. Higher **selected** coverage strongly does (Spearman `0.644`), locating the bottleneck at optimizer selection.

5. **Does higher coverage improve oracle-gap recovery?**  
   Not consistently. Candidate/pair coverage Spearman correlations with oracle gap are only about `-0.16`, with strongly non-monotonic bins.

6. **Are no-training-signal failures concentrated in low-coverage regions?**  
   **No.** Their mean candidate coverage is `96.94%`, essentially identical to other cases.

7. **Where is harmful presence concentrated?**  
   Not at low coverage. It is slightly more common under high structural coverage and substantially associated with higher selected coverage; magnitude is non-monotonic.

8. **Do MCV and FD exhibit different coverage/generalization relationships?**  
   Their structural-coverage relationships are equally weak. Their post-selection effects differ sharply: MCV/composed paths are net positive, while a few FD-only paths create large regressions.

9. **Are highly supported candidates more reliably transferable?**  
   **No.** They are more often selected/consumed, but their positive-effect probability does not improve and their negative-effect probability rises slightly.

10. **Where does `query.62` lie?**  
    It is moderately near and highly covered (100% columns, 93.18% candidates), but almost nothing relevant is selected. It combines harmful FD 552 with missing no-signal MCV 990.

11. **Are there low-similarity but high-transfer queries explained by union coverage?**  
    **Yes**, including `query.374`, `query.468`, and `query.81`; each has low nearest-candidate similarity but 90–100% union coverage and consumes useful shared statistics.

12. **Are there high-coverage failures?**  
    **Yes.** Several 100%-covered instances have large oracle gaps or harmful MCV/FD paths, proving coverage alone is insufficient.

13. **Which metric should define a future similarity embargo?**  
    **None of the tested metrics yet.** Maximum pair containment is the best weak lead for oracle-gap analysis, but it does not track transfer well enough to set a threshold.

14. **Does the evidence justify a controlled similarity-embargo experiment?**  
    **No, not with the current distance definitions.** A richer, label-free semantic relevance metric should be developed and audited first.
