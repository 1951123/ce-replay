# 6. Semantics-Guided Physical Design

CE-Replay separates faithful statistics-sensitive evaluation from combinatorial search. This section presents the concrete search used in the final workload-scale experiments. The search is deliberately conventional: contextual marginal-greedy construction followed by deterministic ADD/DROP/SWAP local improvement. The technical role of CE-Replay is to provide exact-within-scope objectives and semantic dependencies for evaluating those moves.

## 6.1 Maintenance-feasible states

A candidate state is feasible when its recurring maintenance cost does not exceed the supplied budget, as defined in Section 3. The optimization algorithm treats maintenance cost through the generic feasibility interface. In the empirical instantiation, candidate prices are mechanism-weighted object counts calibrated independently from aggregate `ANALYZE` latency in each measured environment.

The search does not hard-code payload bytes or one universal MCV/FD ratio. A different calibrated maintenance function can be substituted without changing CE-Replay semantics. Fixed table-level collection overhead is common to the compared states and is not represented as a candidate-specific price.

The final cross-workload solver searches candidate selection under a fixed recorded physical precedence. Earlier semantic validation establishes that PostgreSQL creation/OID order can affect tied MCV selection, so precedence remains part of PostgreSQL-specific physical realization where relevant. The final solver does not claim to optimize arbitrary precedence jointly with selection.

## 6.2 Contextual marginal-greedy initialization

Search begins from the empty selected set. At each construction step, the solver considers every maintenance-feasible addition and invokes the objective oracle against the current design. It chooses a strictly improving candidate by contextual objective improvement per maintenance unit, with deterministic secondary ordering, commits the addition, and recomputes remaining marginal values in the new state. Construction stops when no feasible addition improves the objective.

This is not static singleton ranking. Because selection changes native control state, a candidate's marginal effect must be evaluated in its current context. A candidate harmful as a singleton may become useful after other selections, while an initially beneficial candidate may become redundant or harmful.

## 6.3 ADD/DROP/SWAP local search

The greedy state seeds exhaustive best-improvement search over three move classes:

- **ADD:** insert one unselected candidate if the resulting design remains maintenance-feasible;
- **DROP:** remove one selected candidate; and
- **SWAP:** remove one selected candidate and insert one unselected candidate if the resulting design is feasible.

Every move value is computed relative to the current state using the CE-Replay objective. The solver does not estimate a swap by adding independent singleton effects, because an atomic remove/add change can alter shared MCV control and downstream FD applicability. Feasibility is checked on the resulting state before the move is eligible.

The implementation selects the move with the greatest objective reduction. Stable move-class and candidate-identity keys resolve exact ties deterministically. The accepted move is committed, semantic dependency/cache state is updated, and the complete feasible neighborhood is reconsidered.

The solver terminates when no feasible ADD, DROP, or SWAP move improves the objective beyond the established numerical tolerance. When the complete terminal neighborhood is audited, this establishes local optimality under that neighborhood for the fixed payload repository and recorded precedence. It does not establish a full-instance global optimum.

## 6.4 Paper-style pseudocode

```text
procedure DESIGN(CE-Replay, candidates, maintenance-cost, budget):
    design <- empty maintenance-feasible design
    state  <- CE-Replay.initialize(design)

    repeat:                                  // contextual greedy construction
        best <- NONE
        for candidate in deterministic candidate order:
            if ADD(candidate) is maintenance-feasible:
                result <- CE-Replay.evaluate_incrementally(state, ADD(candidate))
                if result strictly improves objective per maintenance unit:
                    best <- deterministic better of best and result
        if best is NONE:
            break
        design, state <- commit(best)

    repeat:                                  // exhaustive current neighborhood
        best <- NONE
        for move in every feasible ADD, DROP, and SWAP:
            affected <- CE-Replay.dependencies(state, move)
            result   <- CE-Replay.evaluate_incrementally(state, move, affected)
            best     <- deterministic best-improvement choice(best, result)
        if best is NONE or best does not strictly improve objective:
            return design, state
        design, state <- commit(best)
```

The pseudocode abstracts implementation caches but preserves the evaluated policy: contextual construction, complete feasible ADD/DROP/SWAP enumeration, exact replay-derived move values, deterministic choice, and termination at a neighborhood local optimum.

## 6.5 Exactness audits and guarantee boundary

Exhaustive enumeration on a small Census instance compares replay-selected and native-evaluated global optima across the complete design space. Restricted DMV instances similarly compare the production search with their exhaustive optima. These audits validate objective and search behavior on the audited instances; they do not transfer global-optimum guarantees to the full Census or DMV candidate universes.

The workload-scale guarantee has three layers:

1. CE-Replay evaluates the supported native semantic response for the supplied frozen realization within the validated numerical tolerance.
2. Incremental evaluation returns the same audited move values and accepted trajectory as broader control replay under the tested dependency rules.
3. A complete terminal audit establishes local optimality under the feasible ADD/DROP/SWAP neighborhood.

The method makes no approximation-ratio claim and does not change the combinatorial worst case of statistics selection.

## 6.6 Semantic dependency and invalidation

A naive move evaluator can rerun the entire supported semantic program for every workload query. CE-Replay instead identifies the queries, semantic dimensions, and downstream mechanisms that a move can affect. Candidate-query incidence provides the outer affected set; executable control state refines the work required within each affected query.

The evaluator distinguishes realized dependencies from structural/counterfactual dependencies. A currently unused statistic may still change a future GreedyCover winner when added. Similarly, an MCV toggle can leave the MCV numerical result unchanged yet alter the residual clause state relevant to FD. Safe invalidation therefore follows potential semantic influence, not only the current selected trace or current numerical equality.

The dependency model does not require the global query-candidate graph to decompose into disconnected components. Sparse degrees can provide small affected sets even when a giant connected component spans the workload, and the same evaluator remains correct in a dense high-reuse regime. Topology changes how much work can be avoided, not the definition of correctness.

## 6.7 Incremental evaluation hierarchy

For one candidate move, the evaluator chooses the narrowest justified computation:

1. **No query work** when the move has no structural influence on that query.
2. **Numerical update** when cached semantic control remains valid and only stored objective contributions must be recomputed or combined.
3. **Local MCV control replay** when the move can alter MCV applicability, winner selection, or consumption.
4. **FD replay** when an FD changes directly or an upstream MCV change can alter the FD input boundary.
5. **Broader replay fallback** when a narrower update cannot be proven safe.

Safe pruning is semantic, not a heuristic ranking rule: a computation is omitted only when the dependency model establishes that the move cannot affect the relevant replay result. The final objective comparison remains exact with respect to the frozen replay semantics.

Avoiding semantic control replay can expose numerical aggregation as the dominant implementation cost. Consequently, reduced control work does not imply lower wall-clock runtime. The empirical evaluation reports trajectory equality, replay/control-work reduction, and elapsed time separately.

## 6.8 Qualitative cost structure

Move-evaluation work depends on the number of feasible candidate moves, the number of queries structurally affected by each move, the semantic stages requiring control replay, and the numerical aggregation required to compare objectives. CE-Replay reduces exact evaluation work by exploiting affected-query and mechanism state; it does not remove the outer combinatorial search problem.

The implementation is not tied to sparse incidence. Sparse candidate-query degree increases the opportunity for local updates, while dense high-reuse incidence reduces that opportunity. The same correctness rules apply in both cases because each omitted computation is justified by semantic dependency rather than by an assumed workload topology.

## 6.9 Replaceable search boundary

The objective and dependency interfaces do not prescribe local search. Another search strategy could invoke the same CE-Replay evaluator and dependency information. The evaluated system instantiates one deterministic solver so that move correctness, termination, and deployment can be audited. This architectural separation should not be read as evidence that every possible search strategy has been implemented or evaluated.

## 6.10 Payload realization and deployment boundary

Optimization is conditional on the frozen candidate-payload repository. After search terminates, deployment creates the selected statistics in the recorded physical realization and invokes `ANALYZE`. The resulting fresh payload may differ numerically from the frozen repository, and a requested FD payload may fail to materialize.

Fresh validation therefore re-runs CE-Replay with the fresh payload and compares its estimate with native PostgreSQL for that same realization. Agreement establishes fresh semantic fidelity; it does not imply that the fresh objective equals the frozen optimization prediction. Payload realization drift and semantic replay error remain separate quantities.

The current prototype assumes offline acquisition of hypothetical candidate payloads. It does not provide a general zero-cost payload generator. Acquisition cost is a one-time design input and is not conflated with the recurring maintenance resource imposed by the deployed selected statistics.
