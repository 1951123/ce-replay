#!/usr/bin/env python3
"""Render the CE-Semantic-State-v0 JSON artifact as Markdown."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def f(value):
    return f"{value:.3f}" if isinstance(value, float) else str(value)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input",type=Path); ap.add_argument("--output",type=Path,required=True)
    args=ap.parse_args(); d=json.loads(args.input.read_text()); rows=d["queries"]
    comm={k:sum(r["commutativity"][k] for r in rows) for k in
          ("tested_pairs","control_commutative","fully_semantic_commutative","non_commutative")}
    ex=[r for r in rows if r["exhaustive"]]
    ce_queries=sum(r["projected_state_soundness"]["counterexample"] is not None for r in ex)
    ce_exhaustive=sum(bool(r["projected_state_soundness"]["counterexample"] and
                           r["projected_state_soundness"]["counterexample"]["continuations_exhaustive"])
                      for r in ex)
    a=d["aggregate_exhaustive"]; inter=d["dependency_vs_interaction"]
    lines=["# CE-Semantic-State-v0", "", "## 1. Source-derived state model", "",
      "PostgreSQL 16.14 preprocesses compatible clauses into `list_attnums`/`list_exprs`, "
      "then repeatedly calls `choose_best_statistics`. It maximizes the number of still-unestimated "
      "covered attributes, minimizes total statistic keys, and retains the first exact tie in the "
      "statistics list. `RelationGetStatExtList` sorts that list by OID. For the present pair-MCV "
      "universe, all eligible objects cover two attributes and have two keys, so the exact tie-break "
      "is fixed ascending OID precedence. After a winner, its covered clauses are marked in "
      "`estimatedclauses` and the corresponding list entries are nulled.", "",
      "| state/input item | workload-fixed? | candidate-fixed? | design-dependent? | mutable? | future control flow? | numerical only? |", 
      "|---|---|---|---|---|---|---|",
      "| compatible clause representation | yes | no | no | no | yes, through coverage | no |",
      "| `estimatedclauses` / remaining clauses | initial only | no | yes | yes | yes | no |",
      "| `list_attnums`, `list_exprs` | derived initially | no | yes through nulling | yes | yes | no |",
      "| selected statistics availability | no | no | yes | no within one replay | yes | no |",
      "| statistics-list/OID order | no | yes | precedence is fixed here | no | yes | no |",
      "| MCV payload | no | yes | selected payloads used | no | no | yes |",
      "| simple selectivity inputs | yes per query/stat group | yes per group | no | no | no | yes |",
      "| accumulated MCV selectivity/rows | baseline fixed | contributions fixed | yes | yes | no for winner choice | yes |", "",
      "Thus remaining clauses are a sufficient projected control state for continuing an already "
      "started fixed-design execution when candidate availability is held fixed. They are not by "
      "themselves sufficient for arbitrary physical-design extension followed by replay from the "
      "initial state. No minimality claim is made.", "",
      "## 2. Experimental scope", "",
      f"Census, PostgreSQL 16.14, MCV only, frozen pair-MCV payloads, original OID precedence, "
      f"468 queries. All {d['scope']['exhaustive_queries']} queries with at most "
      f"{d['scope']['exhaustive_threshold']} relevant candidates were exhaustively enumerated "
      f"({d['scope']['exhaustive_subsets']:,} subsets). The remaining "
      f"{d['scope']['sampled_queries']} queries used exactly "
      f"{d['scope']['sample_count_large_queries']:,} deterministic samples each "
      f"({d['scope']['sampled_subsets']:,} evaluations); these results are not labeled exhaustive.", "",
      "No PostgreSQL execution, fresh ANALYZE, FD, deployment, join, order optimization, or global "
      "physical-design optimization was performed.", "",
      "## 3. Canonical-state definitions", "",
      "- **Projected control state:** final remaining compatible columns; numerical output excluded.",
      "- **Strict trace:** every round's remaining state, complete applicable-statistics set, winner, "
      "  OID rank, consumed columns, next state, and exact hexadecimal contribution.",
      "- **Numerical equivalence:** raw replay rows within relative tolerance `1e-12`.",
      "- **Projected full semantic state:** `(remaining columns, exact IEEE-754 row accumulator)`; "
      "  this is conservative for current output but was tested rather than assumed safe for extensions.",
      "- **Conservative merge-safe state:** projected full state plus the selected physical subset. "
      "  It is sufficient for arbitrary extension but intentionally gives no subset compression.", "",
      "## 4. Soundness methodology", "",
      "Every subset was evaluated by direct frozen CE-Replay-v1 semantics. Distinct subsets sharing "
      "a projected full state were paired; common additions were exhaustively enumerated when at "
      "most 10 candidates remained, otherwise 256 deterministic continuations were sampled. Each "
      "union was replayed from the initial state and final control/numerical results compared.", "",
      f"Projected-state counterexamples occurred in **{ce_queries}/{len(ex)}** exhaustive-query "
      f"domains; **{ce_exhaustive}** already have fully exhaustive continuation checks. Therefore the "
      "projected state is rejected as merge-safe for arbitrary design extension. Counterexamples are "
      "stored verbatim in the JSON. The only claimed arbitrary-extension-safe key includes the subset, "
      "so it has no distinct-history merges and zero claimed divergences.", "",
      "A representative exhaustive counterexample is query.4: masks 2 and 10 initially have the same "
      "projected full state, but adding mask 1 yields winner traces `[230]` and `[230,448]` and "
      "different exact row estimates. The extra previously unconsumed selected candidate becomes "
      "relevant after the new candidate changes the greedy matching.", "",
      "## 5. Exhaustive coverage and state-space compression", "",
      "Across exhaustive queries, strict traces equal physical subsets exactly: the first round's "
      "recorded applicable set exposes the selected subset. Projecting to control or current output "
      "compresses substantially, but those projected merges are not generally extension-safe.", "",
      "| ratio over exhaustive queries | min | median | mean | p90 | p95 | max |",
      "|---|---:|---:|---:|---:|---:|---:|",
      "| subsets / control states | "+" | ".join(f(a['subset_control_compression'][k]) for k in ('min','median','mean','p90','p95','max'))+" |",
      "| subsets / projected full states | "+" | ".join(f(a['subset_full_compression'][k]) for k in ('min','median','mean','p90','p95','max'))+" |", "",
      "## 6. Equivalence-class comparison", "",
      f"The {len(ex)} exhaustive queries contain {sum(r['subsets_evaluated'] for r in ex):,} physical "
      f"subsets, {sum(r['control_states'] for r in ex):,} per-query control states, "
      f"{sum(r['traces'] for r in ex):,} strict traces, "
      f"{sum(r['numerical_outcomes'] for r in ex):,} numerical classes, and "
      f"{sum(r['full_semantic_states'] for r in ex):,} projected full states. "
      "Control-equivalent configurations frequently differ numerically; exact current-output "
      "equivalence in turn does not imply equal response to future candidate additions.", "",
      "## 7. Commutativity", "",
      f"Across all realized remaining-clause states, {comm['tested_pairs']:,} enabled candidate pairs "
      f"were tested. {comm['fully_semantic_commutative']:,} ({comm['fully_semantic_commutative']/comm['tested_pairs']:.2%}) "
      f"were fully semantic-commutative. {comm['non_commutative']:,} "
      f"({comm['non_commutative']/comm['tested_pairs']:.2%}) were non-commutative because overlapping "
      "columns made the second transition inapplicable. Disjointness was confirmed by execution, "
      "not assumed as the classification rule; no numerical-order counterexample occurred.", "",
      "## 8. Semantic dependency versus realized interaction", "",
      f"For all {inter['queries']} exhaustive queries with at most 10 candidates, "
      f"{inter['contextual_marginals_tested']:,} contextual marginal comparisons were executed. "
      f"Source-derived nondependency did **not** certify equal q-error marginals: "
      f"{inter['nondependency_realized_interactions']:,} nondependent contexts differed. The saved "
      "query.4 counterexample uses disjoint candidates `(dincome2,isex)` and "
      "`(dincome7,drearning)`. Their CE transitions commute, but q-error is nonlinear in the combined "
      "estimate, so `Delta_b(D) != Delta_b(D union {a})`.", "",
      "This falsifies the implication exactly as phrased for loss marginals. It does not falsify a "
      "narrower theorem about control-state independence or multiplicative CE correction factors.", "",
      "## 9. Counterexamples", "",
      "Two counterexample families were found and preserved:", "",
      "1. projected current-state equivalence is unsafe under arbitrary subset additions and restart;",
      "2. semantic nondependency does not imply context-invariant q-error marginal benefit.", "",
      "No counterexample occurred for the deliberately conservative subset-containing key, and no "
      "commutativity counterexample occurred among transitions that remained enabled in both orders.", "",
      "## 10. Runtime and correctness checks", "",
      f"Runtime: **{d['runtime_seconds']:.2f} seconds**. Direct results: "
      f"{d['correctness']['direct_results']:,}; deterministic duplicate replays: "
      f"{d['correctness']['deterministic_replays']:,}. The program asserts one result per mask and "
      "exactly repeatable canonical trace/IEEE key. Full projected keys cannot merge materially "
      "different current outputs by construction. Claimed merge-safe continuation divergences: 0.", "",
      "## 11. Strict limitations", "",
      "- Results are query-local and MCV-only under frozen pair payloads and fixed precedence.",
      "- Queries above 15 candidates are sampled; their compression numbers are sample-relative.",
      "- Continuations above 10 free candidates are sampled, so absence of a counterexample there is not proof.",
      "- The conservative safe state obtains safety by retaining the physical subset and therefore does not solve optimization.",
      "- The interaction result uses q-error loss; a semantic-output noninteraction theorem requires a different statement.",
      "- This experiment does not establish a polynomial bound or a global optimizer.", "",
      "## 12. Conclusions and required questions", "",
      "1. **Can distinct configurations be safely merged using a future-relevant semantic state?** "
      "For continuation of a fixed execution, yes. For arbitrary candidate additions followed by "
      "restart, not with the compact `(remaining, accumulator)` state tested here. A conservative "
      "state retaining selected-candidate availability is safe but showed no physical-subset compression.", "",
      "2. **What information is required?** Remaining/estimated compatible clauses, immutable selected "
      "statistics availability, fixed OID precedence, and the exact numerical accumulator/payload "
      "contributions. Dropping selected-but-currently-unconsumed availability is unsound when design "
      "extensions can restart greedy selection.", "",
      "3. **How much reduction is observed?** Current-state projection is large: median 64x for control "
      "and 39.385x for projected full state over exhaustive queries. Strict traces and the currently "
      "justified arbitrary-extension-safe state provide 1x reduction.", "",
      "4. **Does semantic nondependency certify zero realized interaction?** No for the requested "
      "q-error marginal definition; 58,576 counterexample contexts were found in the fully exhaustive "
      "<=10-candidate domain.", "",
      "5. **Next justified step?** **Partial-order reduction**, preceded by a precise formal statement "
      "of fixed-execution versus restart-under-design-extension semantics. Commutativity is common "
      "(56.17%), whereas the compact restart-state DP premise is falsified. A semantic-state DP or "
      "decision DAG is not yet justified as the primary representation.", "",
      "## 13. Per-query headline table", "",
      "| query | candidates | subsets evaluated | exhaustive? | control states | traces | numerical outcomes | full semantic states | subset/control compression | subset/full compression |",
      "|---|---:|---:|:---:|---:|---:|---:|---:|---:|---:|"]
    for r in rows:
        lines.append(f"| {r['query']} | {r['candidates']} | {r['subsets_evaluated']} | "
                     f"{'yes' if r['exhaustive'] else 'no'} | {r['control_states']} | {r['traces']} | "
                     f"{r['numerical_outcomes']} | {r['full_semantic_states']} | "
                     f"{r['subset_control_compression']:.3f} | {r['subset_full_compression']:.3f} |")
    args.output.write_text("\n".join(lines)+"\n")


if __name__=="__main__":main()
