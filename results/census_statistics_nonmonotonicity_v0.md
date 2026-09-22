# Statistics-Nonmonotonicity-v0

## Scope

PostgreSQL 16.14, current Census workload, frozen MCV+FD payloads, and the fixed precedence used by the mixed optimizer. No PostgreSQL execution, new optimization, repeated `ANALYZE`, or train/test split is involved.

## Three fixed designs

| Design | MCV | FD | Total | Aggregate q-error | Mean q-error | Median q-error |
|---|---:|---:|---:|---:|---:|---:|
| Empty | 0 | 0 | 0 | 11808.960378745707 | 25.232821322106 | 1.278444727158 |
| Existing optimized mixed | 205 | 56 | 261 | 805.316471766631 | 1.720761691809 | 1.127332840212 |
| All candidates | 2253 | 758 | 3011 | 10932.295550009163 | 23.359605876088 | 1.242195467893 |

All candidates are **worse** than the optimized strict subset by 10126.979078242532 aggregate q-error (1257.515453%). The all-candidate design is evaluated as a semantic comparison and is not required to satisfy the experiment's resource budget.

## Single-statistic additions

| Source design | Feasible tested | Improve | Unchanged | Worsen |
|---|---:|---:|---:|---:|
| Empty | 3011 | 1444 | 7 | 1560 |
| Existing optimized mixed | 0 | 0 | 0 | 0 |
| Combined | 3011 | 1444 | 7 | 1560 |

The strongest harmful addition is `MCV:671` (`v3_scale_0671`) from the empty design. Loss changes from 11808.960378745707 to 13726.220648166491: +1917.260269420784 (16.235640%). Its structurally affected queries are [22, 65, 184, 308, 338].

## Semantic explanation

Classification: **MCV winner/GreedyCover change**.

The causal chain is: add `MCV:671` → native-supported replay control/response changes → estimated rows change → aggregate q-error increases.

The clearest affected query is query 184: rows 54178.4347136 → 79138.815601, truth 13, and q-error 4167.571901046825 → 6087.601200076931. Its MCV trace changes from `[]` to `[671]` and its FD trace from `[]` to `[]`. Only the top five changed query traces are retained in the JSON artifact.

## Removal from all statistics

All 3011 single removals were tested. 317 improve the objective. The best removes `MCV:1267` (`v3_scale_1267`), changing loss from 10932.295550009163 to 10316.982441211823 (-615.313108797340, -5.628398%).

## Interpretation

Within the tested setting, set inclusion is empirically non-monotone: at least one tested `Y, s` has `L(Y union {s}) > L(Y)`, and the all-statistics design is worse than an optimized strict subset. Statistics selection therefore remains semantically meaningful even without a storage budget. The budget adds a separate resource tradeoff; serialized payload size is only a controlled additive proxy, not a complete PostgreSQL collection or maintenance-cost model.

This does not claim that extended statistics are universally harmful or that PostgreSQL always becomes worse when more statistics are installed.

## Required verdict

1. **What is the workload loss with no extended statistics?** 11808.960378745707.
2. **What is the workload loss of the existing optimized mixed design?** 805.316471766631.
3. **What is the workload loss with all MCV+FD candidates?** 10932.295550009163.
4. **Is the all-statistics design worse than the optimized strict subset?** Yes; the absolute/relative difference is 10126.979078242532 / 1257.515453%.
5. **How many tested single-statistic additions worsen the workload objective?** 1560 of 3011 budget-feasible additions.
6. **What is the strongest harmful-addition example?** Add `MCV:671` to the empty design: 11808.960378745707 → 13726.220648166491, +1917.260269420784 (16.235640%).
7. **What native CE semantic mechanism causes that example?** MCV winner/GreedyCover change.
8. **Does removing any statistic from the all-statistics design improve the objective?** Yes; best removal `MCV:1267` changes loss by -615.313108797340.
9. **Does the evidence establish empirical non-monotonicity of the fixed-workload objective?** Yes, within the stated frozen Census/PostgreSQL semantic boundary.
10. **Does statistics selection remain meaningful even without a storage/resource budget?** Yes: the all-statistics design is worse than a strict subset, independently of budget feasibility.
