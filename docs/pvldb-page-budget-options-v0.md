# PVLDB Page-Budget Options

The baseline occupies approximately 12.25 non-reference pages. These are options for a later optimization pass; none has been executed.

## Tier A — low scientific risk

| Intervention | Estimated saving | Claim risk | Readability effect | Reviewer risk |
|---|---:|---|---|---|
| Remove prose that repeats complete T2--T5 cells while retaining each RQ answer and qualification | 0.25--0.5 page | Low | Improves | Low |
| Shorten F1--F4 captions after final figures encode their explanatory content | 0.2--0.4 page | Low if scope language remains | Improves | Low |
| Move fixture lists, terminal traces, repeated-ANALYZE distributions, and detailed fit diagnostics to supplemental | 0.3--0.6 page | Low | Improves main flow | Low |
| Tighten repeated transitions in Introduction, Methodology, and Discussion | 0.15--0.3 page | Low | Improves | Low |

Estimated safe Tier A relief: **0.9--1.5 pages**. The lower end already covers the measured overflow and supplies needed float-placement margin.

## Tier B — moderate editorial risk

| Intervention | Estimated saving | Claim risk | Readability effect | Reviewer risk |
|---|---:|---|---|---|
| Redesign T3 and T4 to separate headline outcomes from supplemental audit detail | 0.3--0.6 page | Medium | Likely improves | Medium |
| Co-design F4 and T5 to remove duplicated composition/deployment evidence | 0.25--0.5 page | Medium | Could improve | Medium |
| Redesign T1 as a narrower workload-comparison table | 0.15--0.3 page | Medium | Likely improves | Low--medium |
| Condense Section 3 notation presentation without deleting equations | 0.15--0.3 page | Medium | Mixed | Medium |
| Condense Related Work while preserving all positioning boundaries and citations | 0.2--0.4 page | Medium | Mixed | Medium--high |

Estimated additional Tier B relief: **1.0--2.0 pages**, not additive at all upper bounds because redesigned artifacts affect float placement.

## Tier C — high scientific/reviewer risk

Reject as ordinary page-saving actions:

- removing either workload;
- removing fresh native validation or deployment evidence;
- hiding the mixed-evaluator slowdown;
- removing non-monotonicity, harmful additions, precedence sensitivity, or giant-component failure;
- dropping the DMV zero-truth or frozen-provenance caveat;
- weakening neighborhood-local, acquisition, realization, or maintenance-model boundaries;
- deleting RQ evidence or literature positioning.

These actions would save space by weakening the paper and should not be used.

## Safest next three actions

1. Render F1--F4, then shorten captions only where the visualization carries the same scope information.
2. Remove prose duplicated by T2--T5 while retaining explicit RQ answers and negative-result interpretation.
3. Move secondary fixtures, traces, distributions, and fit diagnostics to supplemental material, leaving headline evidence in the main paper.
