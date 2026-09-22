# Positioning-Hardening Reviewer Mini-Audit

## Objection A: Is CE-Replay just INUM/C-PQO for statistics?

INUM and C-PQO are the closest representation-level precedents: they reuse optimizer-derived information to represent plan/cost behavior over physical configurations. CE-Replay targets a different computation layer. It keeps a bounded statistics-sensitive estimator computation executable across hypothetical statistics states, including applicability, winner selection, clause consumption, payload-dependent numerical updates, and cross-mechanism state. The claim rests on these positively documented representation targets, not on an assertion that INUM or C-PQO lacks an undocumented capability.

## Objection B: Is CE-Replay merely a reimplementation of PostgreSQL estimator source code?

PostgreSQL supplies the native semantics and normally resolves them for one concrete catalog and statistics state. CE-Replay manually extracts a bounded fragment into a design-parametric representation in which statistics-dependent decisions remain executable across hypothetical states. That form exposes a workload objective interface and the state transitions used as a dependency interface. The contribution is not invention of PostgreSQL's MCV/FD rules, automatic source translation, or a second implementation of one fixed estimate.

## Objection C: Is the dependency oracle just incremental query re-optimization?

Incremental query re-optimization maintains optimizer search and pruning state after cardinality or cost changes. CE-Replay's oracle is upstream and narrower: a statistics-design move propagates through statistics-sensitive estimator applicability, consumption, numerical contribution, and downstream mechanism state before optimizer search. The paper therefore claims a statistics-semantic dependency interface, not generic incremental optimization.

## Objection D: Is statistics selection already solved by automatic statistics management?

Automatic statistics management, workload-aware selection, correlation discovery, and selective acquisition are established. CE-Replay assumes candidate definitions and a frozen payload repository rather than claiming discovery or acquisition. It addresses complete-design evaluation when native statistics objects interact through estimator control and when the selected state must satisfy an empirically motivated recurring-maintenance constraint. This is a bounded focus within an established problem area, not a claim that prior statistics management is absent or ineffective.

## Residual threat

The strongest remaining threat is that CE-Replay may be viewed as a mechanism-specific instance of the established idea of configuration-parametric optimizer representation. That threat does not collapse the contribution if the paper consistently anchors it in the represented computation and demonstrated interfaces: bounded native estimator state remains executable over statistics designs and supplies both objective values and safe move dependencies. It would collapse the positioning if the paper instead relied on generic what-if evaluation, reuse, or fewer optimizer calls as novelty.
