# Paper Title Candidates v0

| Candidate title | Emphasis | Strength | Overclaim risk |
|---|---|---|---|
| **CE-Replay: Executable Cardinality-Estimation Semantics for Statistics Physical Design** | Representation and application | Names the central artifact and bounded task directly | Low; “semantics” must remain scoped in the paper. |
| CE-Replay: Workload-Specialized Semantics for Extended-Statistics Design | Workload specialization | Makes the specialization boundary visible | Low; may underemphasize maintenance and dependency use. |
| Statistics Physical Design with Executable Cardinality-Estimation Semantics | Physical-design problem | Broadly legible without a coined term first | Medium; could sound DBMS-general without subtitle context. |
| Maintenance-Constrained Statistics Design with CE-Replay | Resource-aware optimization | Highlights the final resource formulation | Low; underplays semantic non-monotonicity and dependencies. |
| Executable Native Semantics for Extended-Statistics Physical Design | Native-semantic fidelity | Strong technical characterization | Medium; “native” needs a PostgreSQL 16.14 supported-fragment qualifier in prose. |
| CE-Replay: Objective and Dependency Oracles for Statistics Design | Dual interface | Distinguishes replay from estimator reimplementation | Low; “oracle” is exact only within the validated frozen-realization boundary. |
| Workload-Specialized CE Replay for Maintenance-Aware Statistics Design | Full method chain | Captures workload, method, and resource | Low, but less concise. |

## Recommended working title

**CE-Replay: Executable Cardinality-Estimation Semantics for Statistics Physical Design**

This title survives the limitations audit: it does not promise full PostgreSQL CE, automatic compilation, global optimality, learned CE, runtime improvement, or cross-DBMS validation. The body must define CE-Replay immediately as the supported workload-specialized fragment.
