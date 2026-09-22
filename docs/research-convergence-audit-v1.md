# Research-Convergence-Audit-v1

## 1. Frozen core research problem

本文的核心问题冻结为：**给定目标 DBMS、数据库实例、固定目标查询 workload、候选扩展统计对象及预算，选择一组统计对象，使 DBMS 原生基数估计在该目标 workload 上的加权误差最小。**

目标 workload 是优化输入，不是训练集；本文不声称对未见查询、模板或分布泛化。核心证据只覆盖 PostgreSQL 16.14 的受支持 base-relation restriction CE 片段，以及 Census 上的 MCV+FD 设计。已有 generalization 实验保留为未来工作档案，不进入核心论证。

冻结的研究对象包括：查询及其真实基数、候选定义和成本、预算、冻结的 hypothetical statistics payload、DBMS 原生 CE 语义、以及 PostgreSQL 特定的物理实现顺序。新查询泛化、join CE、完整 planner replay 和执行时间优化均不属于当前核心问题。

## 2. Formal optimization formulation

令：

- \(Q\) 为固定目标查询集合，\(N_q\) 为真实基数，\(w_q\) 为权重；
- \(S\) 为候选 statistics definitions，\(c_s\) 为成本，\(B\) 为预算；
- \(P\) 为候选的冻结 hypothetical payload repository；
- \(Y\subseteq S\) 为选择变量；
- \(\rho\in\mathcal R(Y)\) 为 DBMS-specific physical realization，例如 PostgreSQL 中相关对象的 creation/OID precedence；
- \(F_{DBMS}\) 为受支持的原生 CE 语义。

估计值与目标函数为：

\[
\widehat N_q(Y,\rho;P)=F_{DBMS}(q,Y,\rho,P),
\]

\[
L(Y,\rho;P)=\sum_{q\in Q}w_q\,\ell(\widehat N_q(Y,\rho;P),N_q),
\qquad
\ell(\widehat N,N)=\max\left(\frac{\widehat N}{N},\frac{N}{\widehat N}\right).
\]

设计问题是：

\[
\min_{Y,\rho} L(Y,\rho;P)
\quad\text{s.t.}\quad
\sum_{s\in Y}c_s\le B,
\quad \rho\in\mathcal R(Y).
\]

选择 \(Y\) 是 DBMS-generic 的组合优化变量；\(\rho\) 是可选的 DBMS-specific realization variable，不能被普遍等同于 statistics selection。当前最终 mixed experiment **固定** \(P=P_0\) 和 \(\rho=\rho_0\)，只优化 \(Y\)。早期 MCV-only 实验曾交替优化选择与可达 precedence，但这不是最终 mixed optimizer 的保证。

物理部署后重新 `ANALYZE` 得到的是新 realization \(P'\)，因此部署验证检查 \(F_{DBMS}(Y,\rho;P')\) 与 PostgreSQL native CE 的一致性；它不假设 \(P'=P\)，也不假设选择定义唯一决定 payload。

实现中 q-error 对数值使用极小正数 floor。当前证据没有专门验证 true/estimated cardinality 为零的语义，因此零基数应列为边界而非默认已解决。

## 3. Research questions

### RQ1 — Objective semantics

能否把 DBMS 在受支持 CE 片段中的 statistics-dependent 行为抽取为 design-parametric、可执行的 objective evaluator，并在原生 observation boundary 上精确复现？

### RQ2 — Physical-design optimization

该 evaluator 能否驱动预算约束下的 statistics physical-design search，并在小规模穷举和 workload-scale Census 上产生正确、有效的设计？

### RQ3 — Semantic incremental evaluation

能否利用语义依赖和结构失效规则，在不改变完整当前邻域搜索轨迹的前提下减少 move evaluation 工作量？

### RQ4 — Composition and deployment

多个 CE mechanism 能否按原生顺序组合；所得 mixed design 能否物理部署，并在 fresh payload 上保持 replay/native 一致？

“对未见 workload 泛化”不是第五个核心 RQ。

## 4. System abstraction

系统主链为：

\[
\text{native CE source + payload schema + target workload}
\rightarrow
\text{source-guided executable specialization}
\rightarrow
\text{objective/dependency oracle}
\rightarrow
\text{replaceable combinatorial search}
\rightarrow
\text{physical realization}
\rightarrow
\text{native validation}.
\]

`CE-Replay` 的角色是 objective evaluator 和 dependency oracle，不是搜索算法。它把固定 workload context、payload、design-dependent eligibility/consumption 和数值组合语义显式化；greedy、local search 或穷举均可替换。当前构造属于**人工辅助、源码引导的机制特化**，不是已经实现的任意 DBMS 自动 partial evaluator。

## 5. Complete experiment inventory

完整机器可读清单见 [`results/research-evidence-matrix-v1.json`](../results/research-evidence-matrix-v1.json)。下表给出 28 项实验的论文角色；历史试探被保留，但不与最终证据重复计数。

| # | Experiment | Category | Need | Paper placement |
|---:|---|---|---|---|
| 1 | Census locality analysis | NEGATIVE-RESULT | N3 | Appendix |
| 2 | Creation/OID-order probe | SUPPORTING | N2 | Semantic model |
| 3 | First-applicable pilot | NEGATIVE-RESULT | N3 | Appendix |
| 4 | MCV consumption/composition | CORE-SEMANTICS | N2 | Appendix |
| 5 | CE-Replay-IR-v0 | SUPPORTING | N3 | Historical |
| 6 | CE-Replay-IR-v1-A | CORE-SEMANTICS | N2 | Appendix |
| 7 | CE-Replay-IR-v1-B | CORE-SEMANTICS | N1 | Main E1 |
| 8 | CE-Replay-Optimize-v0 | CORE-OPTIMIZATION | N1 | Main E2 |
| 9 | CE-Replay-Optimize-v1 | CORE-OPTIMIZATION | N1 | Main E3 |
| 10 | CE-Replay-Optimize-v2 | NEGATIVE-RESULT | N3 | Appendix |
| 11 | CE-Replay-Optimize-v3 | SUPPORTING | N3 | Appendix |
| 12 | MCV-Deploy-v0 | CORE-COMPOSITION-DEPLOYMENT | N2 | Appendix |
| 13 | FD-Semantics-v0 | CORE-SEMANTICS | N1 | Main E1/E5 |
| 14 | CE-Replay-Optimize-v4 | CORE-COMPOSITION-DEPLOYMENT | N1 | Main E5 |
| 15 | CE-Semantic-State-v0 | NEGATIVE-RESULT | N3 | Appendix |
| 16 | MCV-Commutativity-v0 | NEGATIVE-RESULT | N3 | Appendix |
| 17 | MCV-Semantic-Factorization-v0 | NEGATIVE-RESULT | N3 | Appendix |
| 18 | Semantic-Move-Pruning-v0 | CORE-INCREMENTAL | N2 | Appendix/E4 detail |
| 19 | Semantic-Optimizer-v0 | CORE-INCREMENTAL | N1 | Main E4 |
| 20 | Compositional-Semantic-Optimizer-v0 | CORE-INCREMENTAL | N1 | Main E4/E5 |
| 21 | Mixed-Deploy-v0 | CORE-COMPOSITION-DEPLOYMENT | N1 | Main E6 |
| 22 | Research-Synthesis-v0 | SUPPORTING | N3 | Internal record |
| 23 | Repeated-Analyze-Robustness-v0 | ROBUSTNESS-SENSITIVITY | N2 | Main E7 short / Appendix |
| 24 | Workload-Generalization-v0 | GENERALIZATION-FUTURE | N4 | Future archive |
| 25 | Generalization-Mechanism-Analysis-v0 | GENERALIZATION-FUTURE | N4 | Future archive |
| 26 | Budget-Generalization-Curve-v0 | GENERALIZATION-FUTURE | N4 | Future archive |
| 27 | Census structural-group audit | GENERALIZATION-FUTURE | N4 | Future archive |
| 28 | Structural-Distance-Generalization-v0 | GENERALIZATION-FUTURE | N4 | Future archive |

## 6. Evidence classification

分类互斥计数为：CORE-SEMANTICS 4、CORE-OPTIMIZATION 2、CORE-INCREMENTAL 3、CORE-COMPOSITION-DEPLOYMENT 3、SUPPORTING 4、NEGATIVE-RESULT 6、ROBUSTNESS-SENSITIVITY 1、GENERALIZATION-FUTURE 5，共 28 项。

必要性计数为：N1 8、N2 6、N3 9、N4 5。N1 构成核心 claim 的最小实证骨架；N2 解释边界和稳定性；N3 记录被排除的假设与研究路径；N4 不进入当前论文核心。

一项实验只有一个 primary category，避免用同一证据重复放大贡献。一个实验可以回答多个 RQ，但其“不支持什么”必须与支持的 claim 同时陈述。

## 7. Minimum evidence chain

最小证据链是：

1. **CE-Replay-IR-v1-B + FD-Semantics-v0**：MCV 与 FD 受支持片段的原生语义可执行且在 raw/native boundary 上精确。
2. **CE-Replay-Optimize-v0**：五候选全集上，replay optimum 与 native exhaustive optimum 在所有预算阈值一致。
3. **CE-Replay-Optimize-v1**：完整 Census pair universe 上，replay 可驱动 workload-scale 设计，并支持 dependency-local evaluation。
4. **Semantic-Optimizer-v0**：结构失效规则保持 MCV 完整当前邻域轨迹，同时减少 control replay。
5. **CE-Replay-Optimize-v4**：MCV 与 FD 必须按联合原生语义优化；独立优化会选择被抑制、从不消费的 FD。
6. **Compositional-Semantic-Optimizer-v0**：mixed 增量 evaluator 保持完整当前邻域 trajectory，并刻画跨 mechanism 的定向失效边界。
7. **Mixed-Deploy-v0**：最终 mixed design 可部署；在 fresh payload 上 replay 与 native 完全一致，且 frozen-to-fresh drift 被独立量化。

删除任一环节都会分别失去 semantic fidelity、controlled optimization correctness、workload scale、incremental exactness、composition necessity 或 physical closure 中的一项。

## 8. Main-paper experiment set

建议正文保留七个实验块，而不是按历史顺序叙述所有实验：

- **E1 Native semantic fidelity**：v1-B 的 4×32 MCV designs（最大相对误差 \(5.55\times10^{-16}\)）与 FD 13 scenarios（最大误差 0）。
- **E2 Controlled optimization correctness**：5 candidates、32 designs、所有可行预算阈值上 replay/native global optimum 一致。
- **E3 Workload-scale physical design**：468 queries、2,253 MCV candidates；给出 random/singleton/marginal/local 的 4922.86/6966.36/812.67/806.26，并明确它们不是全局最优证明。
- **E4 Semantic incremental evaluation**：MCV 轨迹 17 accepted moves 加终止轮完全一致；171.31× fewer control replays、3.51× phase speedup。mixed 轨迹 19 moves 完全一致，但 wall time 没有加速。
- **E5 Multi-mechanism composition**：joint loss 806.444 对 independent 813.942；independent 的 97 个 FD 中 72 个从未消费，joint 的 54 个均被消费。
- **E6 Physical deployment**：205 MCV + 56 FD；fresh replay/native loss 均为 819.191，468/468 匹配，最大误差 \(8.05\times10^{-16}\)。
- **E7 Sensitivity**：30 次 ANALYZE 的 14,040/14,040 semantic matches；loss CV 1.835%。正文只保留短版，细节进 appendix。

order sensitivity 可作为系统模型中的一张小图或例子，而不是独立大实验。

## 9. Appendix experiment set

Appendix 应保留：locality/giant component；first-applicable 反例；MCV consumption mask；IR-v0/v1-A 演进；Optimize-v2 的 disconnected budget exchange；Optimize-v3 的 MCV precedence refinement；MCV-only deployment；semantic state counterexample；commutativity；factorization；单轮 move pruning；repeated ANALYZE 完整分布。

这些材料有三种作用：解释为何最终 abstraction 必须 design-parametric；证明增量 evaluator 的失效规则不是经验猜测；记录 component decomposition、restart-state compression、partial-order reduction 和 query-local factorization 等路线为何在 Census 上没有成为主算法。它们不应挤占正文主链，也不应被当作额外贡献计数。

## 10. Negative results and what they rule out

- **Connected components**：467/468 queries 与全部 2,253 pair candidates 位于 giant component，排除 Census 上严格 component-wise objective decomposition 作为主加速来源；不否认 affected-query locality。
- **First applicable**：最高 98.91× 失配，排除静态“第一个统计对象决定 estimate”的代理模型。
- **Locality-only move search**：58.23% 的 improving swaps 是 disconnected budget exchanges，排除只搜索语义相邻 candidate pair 的完整性假设。
- **Restart-state compression**：新增低 OID 对象会重新暴露此前被投影掉的 selected state，排除 execution-sufficient state 自动等于 extension-sufficient state。
- **Commutativity/POR**：31.37% enabled pairs 可交换，但 canonical OID execution 未缩小 tested outer design space，排除把局部 commutativity 直接转成全局搜索削减。
- **Numerical factorization**：虽能精确重构 3,374,717 个 designs，但所有非空 Census query-local graph 都是单 factor，排除该 workload 上非平凡 factor decomposition。
- **Mixed semantic wall time**：145.68s 对 exhaustive oracle 45.05s，排除“语义缓存必然带来 wall-clock 加速”的普遍主张。

这些是对具体假设和当前 workload 的反证，不是对其他 workloads 的不可能性定理。

## 11. Generalization/future-work archive

五项 generalization 结果移出核心：

- IID 80/20 split 在 9/10 splits 上正向，平均 held-out oracle-gap recovery 44.47%，但 candidate universe 有全局信息且不代表 unseen template。
- mechanism analysis 能用 removal/addition 诊断解释大部分 harmful/missing benefit，但没有产生 robust optimizer。
- budget curve 出现 21/60 train-improving/test-worsening transitions，只说明 train/test 解释下预算类似适应容量。
- Census 在三种 exact statistics-relevant signature 下均为 468 singleton groups，因而不存在有意义的 group-disjoint template split。
- column/candidate coverage 很高，简单 structural distance 与 transfer 几乎不相关；selected coverage-consumption 的 Spearman 为 0.644。

这些结果可以形成后续论文的问题陈述，但不能反向把当前固定 target workload 称为训练集，也不能支持 unseen-template generalization claim。

## 12. Exactness and optimization guarantees

必须严格区分三层 exactness：

1. **Semantic exactness**：给定同一 query、design、precedence 和 payload snapshot，external replay 与 native supported CE 数值一致。v1-B、FD 与 deployment 提供此证据。
2. **Move-evaluation exactness**：增量 evaluator 与完整 evaluator 对 audited ADD/DROP/SWAP 当前邻域给出同一 move values/best move/trajectory。Semantic-Optimizer 与 Compositional-Semantic-Optimizer 提供此证据。
3. **Search optimality**：只有 Optimize-v0 的五候选穷举得到 global optimum。workload-scale 算法没有 global-optimum guarantee。

当前 optimizer 的精确角色如下：

- v0：枚举所有 \(2^5=32\) designs，在每个预算阈值给出 global exhaustive optimum。
- v1/v4：用 deterministic construction、marginal greedy、seeds 与 refinement 生成初始/候选设计；属于启发式搜索。
- Semantic-Optimizer-v0：对固定 MCV precedence，在完整 ADD/DROP/SWAP 邻域上做 deterministic best improvement；停止时为该邻域 local optimum。
- Compositional-Semantic-Optimizer-v0：对固定 mixed precedence 与 frozen payload 做同样的完整当前邻域 best improvement；最终 frozen loss 805.316，停止时为该邻域 local optimum。
- CE-Replay：计算 objective 和 dependency，不选择搜索路径。

因此可写“exact native-semantics evaluator”“exact current-neighborhood trajectory”和“local optimum under the tested neighborhood”，不可写“exact optimizer”或“global optimum”描述 workload-scale 结果。

预算约束下的 statistics selection 具有 knapsack-like 组合结构，但当前 artifact 没有给出正式 NP-hardness reduction；复杂性定理仍是 proof obligation。

## 13. Supported semantic boundary

| Status | Boundary |
|---|---|
| End-to-end validated | PostgreSQL 16.14；base-relation restriction CE；固定 Census AND predicates；pair-column MCV；workload-integrated equality-eligible FD；MCV→FD directed composition；同 payload snapshot 的 raw/native replay |
| Mechanism/node-level validated | FD equality-to-pseudoconstant、IN/ANY、same-attribute OR、boolean、exact expression match；拒绝 range 和 single-attribute dependency；部分 expression fixture |
| Architectural only | 将相同 IR/evaluator/search separation 扩展到其他 base-restriction mechanisms 或其他 DBMS |
| Unsupported | joins、parameterized paths、完整 planner/path search、arbitrary expressions、ndistinct 等其他 extstats、跨 major-version 等价、query execution latency improvement |

`EXPLAIN Plan Rows` 是 `clamp_row_est()` 和整数 observation 后的值；v1-B 的 native primitive 比较的是 raw pre-clamp double。早期 1–2% residual 因而不能与 semantic error 混为一谈。

## 14. Payload and deployment model

需要分开四个对象：

1. **Candidate definition**：列集合、statistics kind、表达式及成本；决定“可以创建什么”。
2. **Frozen hypothetical payload \(P_0\)**：离线优化使用的 MCV items/frequencies、FD degrees、schema 和 `stxkeys` order；决定一次 replay 的数值。
3. **Physical realization \(\rho\)**：实际创建集合和顺序；在 PostgreSQL overlapping MCV 中可影响 OID precedence。
4. **Fresh deployed payload \(P_1\)**：部署并重新 ANALYZE 后得到的 payload；可能与 \(P_0\) 漂移，也可能导致某些 FD payload 不再出现。

order probe 证明同一选择集合的 PostgreSQL estimate 可受 creation/OID order 影响。MCV-only v3 曾对可达 precedence 做交替局部改进，MCV deploy 实现了该顺序；最终 mixed v4 与 compositional optimizer 则固定 precedence，Mixed-Deploy 只验证该 realization。因此 precedence 是 PostgreSQL-specific optional variable，不是所有 DBMS 都必须暴露、也不是最终 mixed result 已全面优化的维度。

Mixed deployment 中 frozen/fresh/native loss 为 805.316/819.191/819.191；两个 FD payload 在 fresh realization 中消失。该结果支持“同 snapshot 的 replay exact”，同时否定“candidate definition 唯一决定 payload”或“frozen objective 等于 fresh objective”。

## 15. Performance-claim audit

所有加速数字必须附 denominator：

- Optimize-v1 的 **47.7× wall-time** 和 **107.3× replay-count**，比较的是 full all-query toggle recomputation 与 affected-query incremental toggle，不是完整 optimizer 或 PostgreSQL planning time。
- Semantic-Optimizer-v0 的 **171.31× fewer control replays** 和 **3.51× phase speedup**，比较的是同一 MCV-only exhaustive-current-neighborhood trajectory 的 control evaluator。
- Semantic-Move-Pruning 单轮 **25.19× fewer control replays** 只是 audited round，不是 end-to-end 数字。
- Compositional experiment 的 **58.89×** 与 **154.61×** 是两层 control-work reductions；实现 wall time 实际为 145.68s，对比 oracle 45.05s，故不能声称 mixed end-to-end speedup。

论文可以主张“减少 replay/control work 且保持 trajectory”，但 mixed implementation 尚不能主张普遍运行时间加速。也不能把 evaluator 加速等同于 PostgreSQL query execution 加速。

## 16. Strongest supported contributions

最强贡献陈述是：

> 对 PostgreSQL 16.14 的受支持 base-restriction MCV+FD 片段，我们展示了一种源码引导、workload-specialized 的可执行 CE 表示；它在固定 payload snapshot 上以浮点精度复现 native estimates，作为预算约束 statistics design 的 objective/dependency oracle，支持保持完整当前邻域轨迹的语义增量评估，并通过 fresh mixed physical deployment 完成 replay-to-DBMS 闭环。

可拆成三点：

1. **语义贡献**：不是学习 CE response，而是从 native payload 与选择/消费/组合规则构造 design-parametric evaluator。
2. **优化贡献**：将 evaluator 与可替换 search 分离；在小规模证明 global optimum 一致，在 workload scale 给出固定邻域 local optimization 与 exact incremental trajectory。
3. **系统贡献**：支持 MCV→FD 的定向组合，避免选择被抑制的 FD，并在 fresh PostgreSQL deployment 上验证同 snapshot 的 native fidelity。

## 17. Unsupported claims

下列说法不得出现在标题、摘要或结论中，除非明确加边界：

- “完整重放 PostgreSQL cardinality estimation”或“支持任意 fixed plan”。
- “自动从任意 DBMS 源码生成 optimizer/objective”。
- “workload-scale global optimum”“exact optimizer”或已证明近似比。
- “所有 extstats mechanism、joins、expressions 或 PostgreSQL 版本均支持”。
- “选择集合唯一决定 estimate”或“fresh ANALYZE 不影响 objective”。
- “semantic caching 在 mixed case 带来 wall-clock speedup”。
- “Census 有统一查询模板”或实验验证了 unseen-template generalization。
- “更大 budget 总是伤害/改善泛化”。
- “优化统计对象改善 query runtime/plan quality”；当前核心目标和证据是 CE q-error。
- “问题已正式证明 NP-hard”。
- “OID precedence 是 DBMS-generic design variable”或最终 mixed design 已联合优化任意 precedence。

## 18. Remaining fixed-workload gaps

### Critical

1. **外部有效性**：当前完整闭环只有 Census/PostgreSQL 16.14。需要第二个真实数据库/workload，在不扩展机制边界的前提下复现 semantic fidelity、optimization 和 fresh deployment。
2. **竞争基线与界限**：除 random/singleton/marginal/local 和 controlled exhaustive oracle 外，缺少一个可信的固定-workload physical-design baseline，以及 workload-scale optimum gap/lower bound。

### Important

3. **mixed fixed-workload budget curve**：已有 generalization budget curve 不能替代全 workload mixed objective 随预算的质量/成本曲线。
4. **实现性能**：mixed semantic optimizer 的 control work 降低尚未转化为 wall-time 加速；需要 profile/engineering 后才能提出 runtime claim。
5. **正式复杂性**：若论文需要 NP-hardness，需要独立、可审查的 reduction；否则只称 knapsack-like combinatorial problem。
6. **零基数与更多边界条件**：q-error floor、缺失 payload、ties 和 expression coverage 需要在 claim boundary 中持续显式化。

### Nice to have

7. 更多 PostgreSQL minor/major versions、另一 DBMS 或第三种 CE mechanism。
8. 自动化 source-to-IR extraction；当前为 source-guided specialization。
9. plan/runtime downstream 效果；只有当论文希望从 CE quality 扩展到执行性能时才需要。

这些 gap 不阻止当前固定-workload核心成立；它们决定 claim 的宽度和投稿强度。

## 19. Recommended next action

立即冻结核心论文 spine，按 E1–E7 重组正文，使用本审计中的边界语言，并停止把 generalization 结果并入核心。若只允许再做一个实验，选择：

> **在第二个真实数据库/workload 上，保持同一 PostgreSQL 16.14、同一受支持 base-restriction MCV+FD fragment 和固定-target-workload objective，复现 semantic fidelity → simple baselines/local optimization → fresh physical deployment 的端到端闭环。**

这项实验直接补当前最大的外部有效性缺口，又不需要引入 join、planner search、新机制或 generalization-aware optimizer。

### Final verdict — 17 required answers

1. **What is the frozen core research problem?** 在固定目标 workload、真实基数、候选 extstats、成本与预算下，选择 statistics design，使 PostgreSQL 受支持原生 CE 的加权 q-error 最小；目标 workload 是优化输入，不是训练集。
2. **What are the primary decision variables?** 主变量是 DBMS-generic selection \(Y\subseteq S\)。DBMS-specific physical realization \(\rho\)（如 PostgreSQL creation/OID precedence）是应单列的可选变量；最终 mixed optimizer 固定 \(\rho\)。payload \(P\) 是给定 realization，不是当前优化变量。
3. **What exactly is the objective function?** \(L(Y,\rho;P)=\sum_q w_q\max(\widehat N_q/N_q,N_q/\widehat N_q)\)，其中 \(\widehat N_q=F_{DBMS}(q,Y,\rho,P)\)，约束为 \(\sum_{s\in Y}c_s\le B\)。当前最终实验优化冻结 \(P_0,\rho_0\) 下的 \(Y\)。
4. **What role does CE-Replay play?** 它是受支持 native CE 片段的 design-parametric objective evaluator 与 dependency oracle；不是搜索算法，也不是完整 planner emulator。
5. **What role does the combinatorial optimizer play?** 它在预算约束下调用 evaluator 搜索 \(Y\)。搜索策略可替换；小实例用穷举作 correctness oracle，workload scale 用 construction/local search，增量版本保持完整当前邻域 trajectory。
6. **What are the four primary research questions?** RQ1 objective semantics；RQ2 budgeted physical-design optimization；RQ3 exact semantic incremental evaluation；RQ4 multi-mechanism composition and physical deployment。
7. **Which experiments are strictly essential to the central thesis?** N1 八项：CE-Replay-IR-v1-B、CE-Replay-Optimize-v0、CE-Replay-Optimize-v1、FD-Semantics-v0、CE-Replay-Optimize-v4、Semantic-Optimizer-v0、Compositional-Semantic-Optimizer-v0、Mixed-Deploy-v0。
8. **Which experiments are useful but belong in the appendix?** locality、first-applicable、MCV consumption、IR-v0/v1-A、Optimize-v2/v3、MCV-only deployment、semantic-state、commutativity、factorization、single-round move pruning，以及 repeated-ANALYZE 的完整细节；正文只需要其中少量边界性结论。
9. **Which experiments are negative results that justify the final architecture?** Census locality/giant component、first-applicable pilot、Optimize-v2 locality-only move search、CE-Semantic-State-v0、MCV-Commutativity-v0、MCV-Semantic-Factorization-v0；另有 mixed semantic wall-time 反例限制性能 claim。
10. **Which experiments should be archived as generalization/future-work material?** Workload-Generalization-v0、Generalization-Mechanism-Analysis-v0、Budget-Generalization-Curve-v0、Census structural-group audit、Structural-Distance-Generalization-v0。
11. **What semantic exactness has actually been established?** 对 PostgreSQL 16.14、同一 payload snapshot、受支持 base-relation MCV+FD 片段，external replay 与 native raw CE 达到浮点精度；这不覆盖完整 CE/planner。
12. **What optimization exactness has actually been established?** 五候选 v0 在所有预算阈值有 global exhaustive agreement；workload-scale incremental evaluators精确复现完整 ADD/DROP/SWAP 当前邻域的 move values、best moves 和 trajectory；终点只保证固定 payload/precedence 下的 tested-neighborhood local optimum。
13. **What global-optimality claims are unsupported?** Census workload-scale MCV 或 mixed design 的 global optimum、近似比、任意 selection+precedence 联合 optimum，以及“exact optimizer”均不受支持。
14. **What is the exact PostgreSQL semantic boundary currently validated?** PostgreSQL 16.14 的 base-relation restriction CE；pair-column MCV、workload-integrated equality-eligible FD、MCV→FD directed composition，以及节点级 FD equality/IN/OR/boolean/exact-expression applicability probes。joins、parameterized paths、完整 planner、任意 expressions 与其他 extstats kinds 不在边界内。
15. **What is the strongest supported contribution statement?** 源码引导、workload-specialized 的 executable native-CE representation 能作为固定-workload statistics design 的浮点精确 objective/dependency oracle，支持保持完整当前邻域轨迹的语义增量评估，并完成 mixed MCV+FD 的 fresh PostgreSQL deployment 闭环。
16. **What are the top remaining gaps for the fixed-workload paper?** 最关键是第二真实 workload/database 的外部有效性，以及可信固定-workload baseline/optimality bound；其次是 mixed budget curve、mixed evaluator wall-time engineering、正式复杂性证明和零基数等边界覆盖。
17. **If only one new experiment were allowed, what should it be and why?** 在第二个真实数据库/workload 上，保持 PostgreSQL 16.14 与现有 MCV+FD semantic fragment，复现 semantic fidelity、简单基线/local optimization 和 fresh deployment；它直接补最大外部有效性缺口且不扩展机制 scope。此审计不运行该实验。
