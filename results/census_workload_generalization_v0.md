# Workload-Generalization-v0

## Protocol

Ten deterministic IID 80/20 splits were evaluated, each with 374 train and 94
test queries. Every split uses the same frozen MCV/FD payload repository,
3,011-candidate global universe, `105061`-byte budget, precedence policy and CE
semantics. No `ANALYZE` was executed.

Train optimization uses test SQL structure only through the pre-existing global
candidate universe. Test truth, q-error, marginal benefit, move rank, stopping
decision and precedence decision are never used. Thus this is an IID
selection-generalization experiment with acknowledged structural leakage, not
a leakage-free deployment simulation.

The existing joint marginal-greedy initializer and exact ADD/DROP/SWAP
best-improvement search are used. Move evaluation uses an exact algebraic form
of the existing compositional replay. On seed 0 it reproduced the canonical
incremental evaluator's train loss (`652.4789209010863`), held-out loss
(`369.4885688553416`) and recovery (`0.9417240231980216`) exactly, while
reducing runtime from about 334 to 65 seconds.

## Headline results

| Metric | Result |
|---|---:|
| Positive held-out gain splits | **9/10 (90%)** |
| Mean / median held-out gain per query | `10.7060` / `2.7437` |
| Mean relative reduction from no extstats | `37.03%` |
| Relative reduction range | `-0.13%–91.69%` |
| No-extstats mean test q-error | `24.3134` |
| Train-design mean test q-error | `13.6074` |
| Full-supervision reference mean test q-error | `1.7472` |
| Test-oracle mean test q-error | `1.6125` |
| Mean / median held-out oracle-gap recovery | `44.47%` / `39.62%` |
| Recovery range | `-0.26%–94.17%` |
| Mean train/test per-query gap | `+11.8435` |
| Improved / unchanged / worsened query-instances | `412 / 216 / 312` |

The result is **moderate and highly heterogeneous generalization**. Aggregate
held-out loss improves in nine splits, but one has slight negative transfer and
two positive splits recover less than 1% of the test-supervised gain. Across
splits, no-extstats test mean q-error ranges from `3.27` to `60.65`, so the
complete split distribution matters more than one pooled total.

The train/test gap is measurable: train mean q-error averages `1.7639`, versus
held-out `13.6074`, and is positive in all ten splits. It is not by itself a
pure overfitting estimate because random splits differ greatly in difficulty.

## Design and selection stability

Train designs contain on average 202.7 MCV and 95.8 FD objects and use 105052.6
bytes. Mean Jaccard similarity to the full-workload design is `42.10%`;
pairwise cross-split Jaccard is only `37.04%` (range `29.07%–45.11%`).
Similarity to the corresponding test-oracle designs averages `6.19%`.

Of 3,011 candidates, 775 are selected in at least one split. A stable core
exists but is small: 26 candidates (19 MCV, 7 FD) appear in all ten splits and
116 (89 MCV, 27 FD) in at least eight. Among ever-selected candidates, median
selection frequency is 30%.

Across the ten designs, 1,492 selections have structural incidence in both
train and test and 1,493 are train-only. No test-only-scope candidate is
selected. The global universe exposes those candidates, but supplies no test
cardinality supervision or positive train marginal for them.

## Consumption and transfer paths

- A mean 73.2/94 test queries (`77.9%`) consume a selected object.
- A mean 75.9 selected MCVs are consumed on test (`37.45%` of selected MCVs).
- A mean 16.5 selected FDs are consumed on test (`17.29%` of selected FDs).
- A mean 92.4 objects are consumed by both train and test; 206.1 only by train;
  none is unconsumed by both sets.

Candidate-removal analysis finds 503 train-useful/test-useful paths, 407
train-useful/test-harmful paths, 14 train-useful/test-neutral paths, and 2,061
selected objects not consumed on that split's test set. These counterfactual
test contributions are computed only after design finalization.

## Query-level transfer and regressions

Across 940 held-out query-instances, 412 improve (`43.83%`), 216 are unchanged
within `1e-12` (`22.98%`), and 312 worsen (`33.19%`). Aggregate improvement can
therefore coexist with many small regressions.

Regression magnitude is strongly concentrated: `query.62` contributes
`44.70%`; the top four (`query.62`, `query.274`, `query.361`, `query.161`)
contribute `70.85%`; the top ten contribute `80.02%`. Trace diagnosis classifies
243/312 regressions as MCV winner/payload effects, 57 as FD interactions, and
12 as cross-mechanism suppression. The largest candidate-removal harmful
signals include MCV 188, 691, 2 and 79 and FD 552; interacting removal effects
must not be summed as additive attribution.

## Final verdict

1. **Does train-optimized statistics design improve randomly held-out queries?**  
   **Usually yes.** Aggregate held-out loss improves in 9/10 splits, but not universally.

2. **What fraction of random splits show positive held-out improvement?**  
   **90% (9/10).**

3. **How large is the held-out improvement relative to no extended statistics?**  
   Mean reduction is **10.706 q-error units per query**, or **37.03%** per split; median reduction is 2.744 units. The range is `-0.13%–91.69%`.

4. **How much of the test-supervised reference improvement is recovered?**  
   Mean held-out oracle-gap recovery is **44.47%**, median **39.62%**, with range `-0.26%–94.17%`. This is descriptive, not an approximation guarantee.

5. **Is there a measurable train-test generalization gap?**  
   **Yes.** Mean train q-error is `1.7639`, mean test q-error `13.6074`, and average gap `+11.8435`. Difficulty imbalance prevents attributing all of it to overfitting.

6. **How stable are selected statistics across random training samples?**  
   **A small stable core, but low overall stability.** Only 26/3,011 candidates appear in every split; 116 appear in at least 80%. Mean pairwise Jaccard is `37.04%`.

7. **Are train-selected statistics actually consumed by held-out queries?**  
   **Yes.** On average 73.2/94 held-out queries consume one or more; 37.45% of selected MCVs and 17.29% of selected FDs are consumed on test.

8. **How many held-out queries improve, remain unchanged, or regress?**  
   **412 / 216 / 312** (`43.83% / 22.98% / 33.19%`).

9. **Is negative transfer concentrated in a small number of queries or statistics?**  
   **Yes in magnitude.** One query accounts for 44.70% and the top four for 70.85%. MCV effects dominate, with smaller FD and cross-mechanism components.

10. **Does the evidence support transferable data-distribution structure rather than mere fitting?**  
    **Yes, but only moderately.** Nine positive splits, direct held-out consumption, 503 train-useful/test-useful paths and up to 94% recovery demonstrate transfer. High variance, many regressions and low overlap reject a stronger claim of consistent near-oracle transfer.

11. **What claims remain unsupported?**  
    This does not establish generalization to unseen templates, unseen predicate-column structures, distribution shift, other databases/data distributions, candidate-generation generalization, or fresh-`ANALYZE` performance. Random splitting may put latent-template siblings in both partitions, and the global universe leaks held-out predicate structure.

Exact split membership, trajectories, designs, overlap, consumption paths,
removal contributions and per-query outcomes are retained in the JSON and
compressed query CSV.
