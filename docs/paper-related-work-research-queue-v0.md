# Related Work Research Queue v0

This queue covers every literature-dependent placeholder in `paper-full-draft-v0.md`. No source has been selected or verified in this drafting task.

| ID | Section | Claim needing support | Category | Desired source | Search keywords | Role | Priority |
|---|---|---|---|---|---|---|---|
| RW1 | 1 | Physical-design systems use optimizer what-if interfaces. | Automated physical design | Foundational advisor paper or DBMS documentation | database physical design what-if optimizer interface | Competitive positioning | High |
| RW2 | 1 | INUM-style work specializes or reuses optimizer response. | Fast hypothetical evaluation | Original peer-reviewed INUM paper and follow-ups | INUM optimizer response reuse physical design | Competitive positioning | High |
| RW3 | 2.1 | Classical selectivity estimation often relies on independence assumptions. | Cardinality estimation | Textbook/survey plus foundational paper | selectivity estimation attribute independence database | Background | High |
| RW4 | 2.1 | PostgreSQL extended statistics provide multivariate MCV/FD mechanisms. | DBMS semantics | Official PostgreSQL 16 documentation | PostgreSQL 16 extended statistics MCV dependencies | Background | High |
| RW5 | 2.2 | Automated index/materialized-view design is a related physical-design class. | Automated physical design | Foundational systems and survey | automated index selection materialized view advisor survey | Background/positioning | Medium |
| RW6 | 10.1 | Persistent physical structures are selected under workload/resource constraints. | Automated physical design | Survey and representative advisors | workload physical database design resource constraint | Competitive positioning | High |
| RW7 | 10.1 | Native what-if facilities support hypothetical configuration evaluation. | Automated physical design | Peer-reviewed system paper or official interface documentation | hypothetical index what-if optimizer physical design | Competitive positioning | High |
| RW8 | 10.2 | INUM and related methods cache or specialize plan-cost response. | Fast hypothetical evaluation | Original and follow-up peer-reviewed papers | INUM plan templates cost caching what-if | Competitive positioning | High |
| RW9 | 10.2 | Modern systems evaluate hypothetical physical configurations efficiently. | Fast hypothetical evaluation | Recent peer-reviewed systems papers | fast hypothetical configuration evaluation database advisor | Competitive positioning | Medium |
| RW10 | 10.3 | Classical CE combines catalog statistics and modeling assumptions. | Cardinality estimation | Survey/tutorial/foundational work | database cardinality estimation survey catalog statistics | Background | High |
| RW11 | 10.3 | Multivariate statistics address dependence missed by univariate summaries. | Multivariate statistics | Foundational database-statistics work and DBMS docs | multivariate statistics correlated predicates selectivity | Background/positioning | High |
| RW12 | 10.3 | Learned CE estimates cardinalities or data/query distributions. | Learned CE | Survey and representative peer-reviewed systems | learned cardinality estimation survey query workload | Competitive positioning | Medium |
| RW13 | 10.4 | Prior work selects multivariate statistics from workloads. | Extended-statistics selection | Closest peer-reviewed methods | automatic multivariate statistics selection workload | Competitive positioning | Critical |
| RW14 | 10.4 | DBMSs or advisors automatically create/recommend extended statistics. | Extended-statistics configuration | Vendor/open-source documentation and papers | automatic extended statistics recommendation create statistics advisor | Competitive positioning | Critical |

## Search order

1. RW13–RW14: establish the closest-problem boundary before making novelty claims.
2. RW1–RW2 and RW6–RW9: position CE-Replay against native what-if and response-specialization methods.
3. RW3–RW4 and RW10–RW12: supply concise background and distinguish replay from learned CE.
4. RW5: complete the broader physical-design framing.

Priority or novelty language remains prohibited until this queue is resolved with verified sources.
