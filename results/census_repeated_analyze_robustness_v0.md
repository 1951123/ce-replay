# Repeated-Analyze-Robustness-v0

| Metric | Value |
|---|---:|
| ANALYZE realizations | 30 |
| query-realization semantic comparisons | 14,040 |
| replay/native strict matches | 14,040 |
| max semantic relative error | 1.31e-14 |
| workload loss mean | 797.632243 |
| workload loss std | 14.636349 |
| workload loss min | 764.982678 |
| workload loss median | 797.058419 |
| workload loss max | 828.581271 |
| mean frozen-relative drift | -0.9542% |
| p95 frozen-relative drift | 2.0623% |
| total storage mean | 104762.8 bytes |
| total storage min | 104199 bytes |
| total storage max | 105198 bytes |
| queries with invariant control trace | 462 / 468 |
| queries with varying MCV trace | 0 |
| queries with varying FD trace | 6 |
| intermittently unavailable FD objects | 4 |

All realizations use the same 205 MCV and 56 FD catalog objects, targets and
OID order. Full raw measurements and candidate/query summaries are in JSON.

## Interpretation

The replay semantics remain exact under fresh statistics samples: all 14,040
query-realization comparisons agree with PostgreSQL native estimates within
`1e-12` (maximum relative error `1.31e-14`). Repeated `ANALYZE` therefore does
not expose a replay-semantics defect.

The observed variation is primarily **numerical payload variability**, not a
change in which statistics PostgreSQL consumes. The complete MCV control trace
is invariant for every query. Overall, 462/468 queries retain the same MCV and
FD control decisions while their numerical estimates change; only six queries
change FD consumption because an FD object is intermittently unavailable.

This numerical variation is material at workload level. Loss has CV `1.835%`
and spans `-5.008%` to `+2.889%` relative to the frozen realization. Its
standard deviation (`14.636`) is much larger than the approximately `1.127`
loss-unit improvement from the preceding mixed-design optimization
(`806.444` to `805.316`). Consequently, the frozen payload is a valid semantic
test fixture but a weak point prediction of the deployed design's expected
loss. The original Mixed-Deploy observation (`819.191`) lies at the empirical
90th percentile: relatively high, but still inside the ordinary observed
range rather than an extreme outlier.

MCV payload size changes in 128/205 objects. Among workload-relevant objects,
the largest frequency CV is `2.100%` (MCV 1885); other leading cases include
MCV 2201 (`1.486%`), 1946 (`1.193%`), and 2174 (`1.166%`). All 205 selected MCV
objects remain consumed in every realization, so this is payload-value and
payload-size variation rather than MCV eligibility variation.

FD availability is mostly stable: 52/56 objects are always available and four
are intermittent—FD 0 (`66.7%` of runs), 97 (`60.0%`), 683 (`16.7%`), and 736
(`86.7%`). Their availability changes directly explain the six varying FD
traces: q101, q224, q303, q353, q424, and q464.

The most estimate-unstable queries are q184 (CV `63.27%`, MCV 530/1860), q62
(`63.18%`, MCV 990), q465 (`28.85%`, MCV 32/532/2210), q61 (`28.34%`, MCV
29/107/1000), q59 (`19.50%`, MCV 588/826), and q221 (`19.42%`, MCV 826).
Their control traces are stable, reinforcing the numerical-payload diagnosis.
The intermittent-FD queries above are a small, separate structural effect.

Storage is comparatively stable: mean `104762.8` bytes, standard deviation
`267.1` bytes (CV about `0.255%`), and range `104199–105198`. Four of 30 runs
exceed the frozen `105060`-byte size. Loss and storage have essentially no
association (Pearson `-0.070`, Spearman `-0.092`).

## Final verdict

1. **Yes.** CE-Replay matched 14040/14040 query-realization pairs within 1e-12.
2. Loss is a distribution, not a single deterministic outcome: `764.982678–828.581271`, mean `797.632243`, median `797.058419`, and std `14.636349`.
3. The original loss `819.191023` is at empirical percentile `90.0%` (rank 27/30 by `<=`): high and somewhat unusual, but not extreme.
4. Variability is primarily numerical: 462 queries have stable control with changing numerical estimates, six have varying FD control, and none has varying MCV control.
5. MCV payload size changes for `128/205` objects; all MCV objects remain consumed, and the largest workload-relevant frequency CV is about `2.10%` (MCV 1885).
6. FD availability is `52` always, `4` intermittent, and `0` never. The intermittent objects are 0 (`66.7%`), 97 (`60.0%`), 683 (`16.7%`), and 736 (`86.7%`).
7. Storage is much less variable than loss: `104199–105198` bytes (mean `104762.8`, std `267.1`, CV about `0.255%`), exceeding frozen storage in `4/30` runs.
8. Instability concentrates in q184, q62, q465, q61, q59, and q221 through numerically varying MCV payloads; q101, q224, q303, q353, q424, and q464 form the smaller intermittent-FD group.
9. **Yes.** The result materially weakens a frozen payload as a predictive point estimate because realization noise exceeds the preceding incremental design gain. It does not weaken replay-semantic correctness.
10. **Yes.** A robustness follow-up is scientifically justified now: evaluate designs across repeated payload realizations and study an expected/worst-tail objective. This experiment deliberately does not implement or alter the optimizer.
