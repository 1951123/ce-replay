# Budget-Generalization-Curve-v0

## Experimental scope

The experiment reuses the exact ten 374/94 IID splits, global candidate
universe, frozen MCV/FD payloads, cost model, precedence, CE semantics and
optimizer from `Workload-Generalization-v0`. No `ANALYZE` was executed and no
test labels entered training optimization.

The mandatory grid is `{0,10,20,40,60,80,100}%`, corresponding to
`{0,10506,21012,42024,63036,84048,105061}` bytes. The existing validated 100%
designs are reused; all other nonzero designs are independently optimized.
Coverage-oracle analysis uses all existing 100% oracles and a reduced protocol
at 20%/60% for deterministic splits 0–2.

## Aggregate capacity curves

| Budget | Train mean | Test mean | Test median | Test std | Mean relative test improvement | Positive splits | Mean candidates | MCV / FD count | Mean gap |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0% | 25.464 | 24.313 | 22.033 | 20.210 | 0.00% | 0/10 | 0.0 | 0.0 / 0.0 | -1.150 |
| 10% | 2.314 | 15.908 | 4.219 | 17.462 | 34.20% | 9/10 | 38.4 | 24.2 / 14.2 | 13.594 |
| 20% | 2.125 | 16.219 | 4.457 | 17.212 | 24.19% | 8/10 | 70.9 | 39.9 / 31.0 | 14.095 |
| 40% | 2.001 | 17.070 | 10.397 | 15.786 | 24.45% | 10/10 | 141.0 | 84.6 / 56.4 | 15.070 |
| 60% | 1.955 | 14.889 | 4.937 | 15.533 | 28.88% | 9/10 | 189.4 | 120.8 / 68.6 | 12.934 |
| 80% | 1.873 | 14.916 | 4.701 | 15.501 | 29.82% | 8/10 | 245.0 | 162.6 / 82.4 | 13.043 |
| 100% | 1.764 | 13.607 | 4.544 | 15.554 | 37.03% | 9/10 | 298.5 | 202.7 / 95.8 | 11.844 |

Training loss improves monotonically in the cross-split aggregate. At the
individual level 59/60 adjacent transitions improve training; seed 1 has a
small 80→100% regression (`1.5007→1.5112`), consistent with independently
reached local optima rather than a capacity claim.

Held-out performance is non-monotonic and highly split-dependent. Mean test
loss improves sharply at 10%, worsens through 40%, improves at 60%, is flat at
80%, and improves again at 100%. The median follows another shape. Therefore
there is no single saturation threshold shared by the ten splits.

## Marginal budget transitions and operational overfitting

| Transition | Train+/test+ | Train+/test− | Mean train benefit | Mean test benefit |
|---:|---:|---:|---:|---:|
| 0→10% | 9 | 1 | 23.150 | 8.406 |
| 10→20% | 6 | 4 | 0.189 | -0.312 |
| 20→40% | 4 | 6 | 0.124 | -0.851 |
| 40→60% | 7 | 3 | 0.046 | 2.181 |
| 60→80% | 6 | 4 | 0.082 | -0.027 |
| 80→100% | 6 | 3 | 0.109 | 1.309 |

There are 21 train-improving/test-worsening transitions. They improve train
mean q-error by `24.088` in aggregate while worsening test by `35.406`; one is
the 0→10% jump. Restricting to nonzero budgets leaves 20/50 transitions across
9/10 splits. All ten splits exhibit at least one operational overfitting
transition when the zero-budget transition is included.

## Best held-out budget

The diagnostic best-test budgets are: 10% for two splits, 20% for one, 40% for
one, 60% for two, 80% for two, and 100% for two. Full capacity is therefore
best in only 2/10 splits. This uses held-out labels and is not a deployable
budget-selection rule.

## Candidate specialization and stable core

The mean fraction of the 26 universal 100%-budget candidates retained rises
from `28.46%` at 10%, through `45.77/65.38/77.31/91.15%`, to 100%. Lower
budgets do preferentially retain part of the stable core, but not exclusively.

Selected candidate occurrences grow from 384 at 10% to 2,985 at 100%.
Held-out negative contextual effects grow in absolute count from 91 to 566,
while their rate per selected occurrence falls from `23.7%` to `19.0%`.
Test consumers per selected occurrence also decline (`0.583→0.438`). Larger
budgets therefore add more train-specific and absolutely more harmful
candidates, but the marginal pool is not proportionally more harmful.

Candidates first observed at 10/20/40/60/80/100% number
`80/63/178/152/175/200`. The late-entry population contains both MCV and FD;
there is no evidence that it is exclusively one mechanism.

## Harmful-presence curve

| Budget | Mean regression magnitude | Mean harmful regressions | Single-removal repair |
|---:|---:|---:|---:|
| 10% | 123.599 | 7.2 | 91.02% |
| 20% | 129.668 | 11.3 | 93.21% |
| 40% | 14.098 | 17.8 | 92.31% |
| 60% | 8.502 | 22.9 | 85.64% |
| 80% | 9.169 | 25.6 | 90.04% |
| 100% | 16.032 | 27.9 | 90.08% |

Harmful-regression count increases with capacity, but magnitude does not: it
is dominated at 10–20% by a few catastrophic paths, collapses at 40–60%, then
rises modestly. Across budgets, most magnitude remains repairable by one
query-specific removal.

## Coverage failure and oracle recovery

For the comparable reduced-oracle splits 0–2, held-out oracle-gap recovery is
`66.05%` at 20%, `69.41%` at 60%, and `69.27%` at 100%. It effectively
saturates by 60% on this subset.

Mean useful-missing-query counts increase from `45.3` to `72.7/72.3`, because
larger test-oracle designs expose more useful alternatives. Budget-pressure
diagnostics fall from 51 total cases at 20% to 45 at 60% and 22 at 100%, while
no-training-signal cases rise from 85 to 173/195. Capacity relieves budget
pressure but cannot create missing workload supervision.

## MCV/FD allocation

MCV mean bytes rise from `10039.6` at 10% to `102188.8` at 100%; FD bytes rise
from `459.0` to `2863.8`. FD count grows from 14.2 to 95.8, but its count share
falls from `37.0%` to `32.1%`, and its byte share remains small. Larger budgets
do not disproportionately shift capacity into FD. This does not imply FD is
harmless: a few FD paths dominate particular regressions while MCV+FD
composition remains important for positive transfer.

## Major regression queries across budgets

- `query.62`: at 10–20%, FD 398 causes q-error `2699.38`; at 40%, one split
  selects FD 552 (`2164.81`); 60–80% consume neither; at 100%, FD 552 reappears
  in one split. MCV 990 is never selected by the train designs. This is a
  non-monotonic candidate-entry phenomenon, not a single high-budget threshold.
- `query.274`: 10% is strongly beneficial (`1.23`), 20% becomes harmful
  (`136.20`), and later budgets remain split-dependent through MCV 691 versus
  MCV 2/190 paths.
- `query.361`: regression begins at 40% when MCV 1099 enters; it persists in
  some designs while other splits remain neutral or become positive.
- `query.161`: MCV 835 first creates regression at 40%; higher budgets either
  worsen it through MCV 529/835 or repair it through MCV 833. Again, the
  threshold is query/design-specific.

## Limitations

Only ten deterministic IID splits and seven budgets are studied. Statistics
are descriptive. The reduced oracle protocol uses only splits 0–2 at 20/60%,
and comparisons to 100% are made on the same subset. Independent local search
can make one training curve slightly non-monotonic. This experiment does not
cover template-disjoint workloads, distribution shift, fresh `ANALYZE`, new
candidate generation, or globally optimal designs.

## Final verdict

1. **Does increasing statistics budget monotonically improve training performance?**  
   **Nearly.** Aggregate train loss decreases at every level and 59/60 split transitions improve; one small 80→100% local-search exception remains.

2. **Does increasing statistics budget monotonically improve held-out performance?**  
   **No.** Both mean and per-split curves are non-monotonic and highly split-dependent.

3. **Is there evidence of train-improving but test-worsening budget increments?**  
   **Yes:** 21/60 transitions, or 20/50 after excluding 0→10%, with nonzero-budget cases in 9/10 splits.

4. **Does the train-test gap increase with budget?**  
   Not monotonically. It rises through 40% (`15.070`) and then falls to `11.844` at 100%.

5. **At what budget levels does held-out performance saturate or degrade?**  
   There is no common threshold. Aggregate degradation occurs at 10→20%, 20→40%, and slightly 60→80%; improvements resume at 40→60% and 80→100%.

6. **Is the full 100-percent budget usually the best held-out budget?**  
   **No.** It is best for only 2/10 splits.

7. **Do larger budgets select more train-specific or test-harmful candidates?**  
   **More in absolute number, yes; proportionally, no.** Test consumption per selected occurrence falls, while harmful-effect rate falls from 23.7% to 19.0%.

8. **Does harmful-presence magnitude increase with budget?**  
   **No.** Harmful count rises, but magnitude peaks at 10–20%, drops sharply, and only modestly rebounds at 100%.

9. **How does coverage failure change with budget?**  
   Budget pressure decreases, but no-training-signal coverage failures persist and dominate. Oracle recovery on matched splits saturates around 69% by 60%.

10. **How does MCV/FD capacity allocation change with budget?**  
    Both grow, but MCV dominates bytes. FD count share decreases modestly; no disproportionate high-budget FD shift is observed.

11. **Are `query.62` and the other major regressions budget-threshold phenomena?**  
    They are candidate-entry phenomena with different, non-monotonic thresholds. `query.361`/`query.161` begin near 40%, whereas `query.62` is harmful at low, middle and full budgets but neutral at 60–80%.

12. **Does the evidence support interpreting statistics budget as a model-capacity parameter?**  
    **Yes.** It controls design size and training fit, changes specialization and creates train-positive/test-negative transitions. Its generalization effect is not monotonic.

13. **Is there empirical evidence of statistics-design overfitting?**  
    **Yes under the operational definition:** many budget increments improve train while worsening test. There is no evidence that all high budgets are globally worse.

14. **Does this motivate a future stopping rule or regularizer?**  
    **Yes.** The heterogeneous non-monotonic curves motivate uncertainty/generalization-aware stopping or regularization, but this experiment does not implement either.
