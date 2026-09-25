# CE-Replay-Native-WallClock-v0 Protocol

- Four contracts: client-observed `T_PG-plan`, server-side
  `T_PG-CE`, warm in-memory `T_Replay-full`, and supplied-move
  `T_Replay-inc`.
- Correctness is a hard pre-timing gate. Census uses all 468 queries. DMV
  checks all 1,965 estimates and aggregates q-error over the 1,963 positive-
  truth queries; `dmv.173` and `dmv.943` remain semantic checks only.
- Native timing uses PostgreSQL 16.14, one long-lived connection/backend,
  `EXPLAIN (FORMAT JSON)`, an already-running warm server, and no query
  execution. `CREATE STATISTICS` and `ANALYZE` are outside every timer.
- The dedicated GUC is disabled by default. Trace-on mode validates semantics;
  trace-off timing mode suppresses all pre-existing per-node CE notices and
  emits only one post-region timing record per base-relation estimate.
- Replay setup, imports, parsing, payload loading, state construction, snapshot
  restoration, and result serialization are excluded. Normal Python garbage
  collection remains enabled.
- Independent move populations are frozen before timing. Census uses the
  initial state of the recorded mixed trajectory. DMV uses the stable
  mechanism/candidate ordering with alternating candidates selected (50.7%).
  ADD, DROP, and SWAP populations are stratified using affected-query-count
  tertiles; eight moves per stratum and pooled cell are selected by SHA-256 of
  seed `ce-replay-wallclock-v0` plus the move representation.
- Exactly five complete untimed warmup batches precede each cell. Calibration
  selects the smallest power-of-two multiplier exceeding 100 ms. Exactly 30
  measured batches follow. Raw batch nanoseconds are retained.
- Reported statistics are median, p25, p75, p95, mean, standard deviation,
  batch size, batch count, total duration, and median-derived ratios.
- Fixed query/design/move order; no parallel replay; no post-result removal,
  tuning, or protocol changes.
