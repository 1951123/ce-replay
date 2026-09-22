# CE-Replay: Workload-Specialized Cardinality Estimation for Statistics Physical Design

## 1. Problem

We study workload-aware physical design of extended statistics.

Let the workload be:

$$
Q
$$

Let the set of candidate statistics objects be:

$$
S
$$

Let the selected statistics be:

$$
Y \subseteq S
$$

Let the physical precedence relevant to the supported DBMS semantics be:

$$
\pi
$$

The statistics design is:

$$
D=(Y,\pi)
$$

Let the frozen repository of candidate statistics payloads be:

$$
\mathcal P_0
$$

Let the ground-truth cardinality for the supported estimation target of query
$$
q
$$
be:

$$
N_q
$$

The optimization objective is:

$$
D^*
=
\arg\min_D
\sum_{q\in Q}
w_q
L\left(
\hat N_q(D;\mathcal P_0),
N_q
\right)
$$

subject to resource constraints such as:

$$
C_{\mathrm{storage}}(D)\le B.
$$

The current work uses cardinality-estimation q-error as the loss function:

$$
L
$$

The objective is therefore estimation quality, not query latency or end-to-end
execution time.


## 2. Why Statistics Design Requires Native CE Semantics

A candidate statistic does not have a design-independent value.

Its effect depends on which other statistics are present and on how the native
cardinality estimator consumes them.

For candidate statistic

$$
s,
$$

its marginal effect under design

$$
D
$$

can be written as:

$$
\Delta_s(D)
=
L(D)-L(D\oplus s).
$$

Empirically:

$$
\Delta_s(\varnothing)
\neq
\Delta_s(D).
$$

On the full Census pair-candidate workload, singleton-based selection produced loss:

$$
6966.36,
$$

while design-dependent marginal selection produced:

$$
812.67.
$$

Statistics design is therefore an interaction problem rather than an independent
candidate-ranking problem.


### 2.1 Physical precedence can affect estimation

For the supported PostgreSQL 16 MCV fragment, native statistic selection can depend
on catalog/OID order when otherwise tied.

Thus the physical design includes relevant precedence:

$$
D=(Y,\pi).
$$

Experiments show that changing

$$
\pi
$$

can change both cardinality estimates and subsequent selection marginals:

$$
\Delta_s(Y,\pi_1)
\neq
\Delta_s(Y,\pi_2).
$$

Hence precedence cannot always be treated as deployment-only post-processing.


### 2.2 CE mechanisms can interact through estimator state

PostgreSQL MCV and functional-dependency statistics are not independent correction
factors.

For the supported restriction-estimation pipeline:

$$
MCV
\rightarrow
estimatedclauses
\rightarrow
FD.
$$

An MCV statistic can consume clauses that would otherwise make an FD applicable.

Therefore:

$$
G_q^{MCV+FD}
\neq
G_q^{MCV}\times G_q^{FD}.
$$

A statistics optimizer must reproduce the native consumption semantics that generate
these interactions.


## 3. CE-Replay

Instead of learning a separate function that predicts the DBMS response to a
statistics design, CE-Replay constructs an executable representation of the relevant
native CE semantics.

For supported semantic fragment

$$
\mathcal F,
$$

we write specialization as:

$$
Specialize_{\mathcal F}
(
CE_{DBMS},
q,
\Theta_q
)
=
G_q^{\mathcal F}(D,\mathcal P_0),
$$

where

$$
\Theta_q
$$

contains workload-fixed and planner-fixed context.

The current prototype performs mechanism-specific specialization based on native
source semantics and instrumentation. It is not an automatic partial evaluator for
arbitrary DBMS source code.


### 3.1 Stateful IR

A replay node is modeled as:

$$
v_i:
(X_i,D,P_i,\Theta_i)
\rightarrow
(X_{i+1},o_i).
$$

The components have the following meanings.

Incoming CE state:

$$
X_i
$$

Physical statistics design:

$$
D
$$

Relevant statistics payload:

$$
P_i
$$

Specialized context:

$$
\Theta_i
$$

Updated CE state:

$$
X_{i+1}
$$

Numerical or semantic output:

$$
o_i
$$

A query replay program is:

$$
G_q
=
v_k\circ\cdots\circ v_1.
$$

This representation preserves design-dependent control flow instead of freezing the
winner observed in one native execution.


## 4. Validated PostgreSQL 16 Mechanisms

### 4.1 MCV

For the supported base-relation AND-predicate fragment, PostgreSQL repeatedly selects
applicable MCV statistics according to native greedy semantics.

The relevant priority is:

1. maximize currently unestimated attributes/expressions covered;
2. minimize total statistic keys;
3. use statistics-list/catalog order for remaining ties.

Selected statistics consume estimated clauses, so overlapping statistics can suppress
one another while compatible statistics can compose.

External replay reads native MCV payloads and reproduces the corresponding
selectivity computation.

Across 128 tested designs and four statistics targets:

$$
Replay_{MCV}
=
Native_{MCV}
$$

to floating-point precision, with maximum observed relative error approximately:

$$
5.55\times10^{-16}.
$$


### 4.2 Functional Dependencies

FD processing follows different internal semantics.

Matching dependency payloads are aggregated across statistics objects. Applicable
dependencies are selected according to:

1. full coverage;
2. maximum arity;
3. maximum dependency degree.

A selected dependency consumes its implied attribute, and selected dependencies are
numerically applied in reverse selection order.

For dependency degree

$$
f,
$$

the tested numerical update is:

$$
P(b\mid a)
=
\begin{cases}
f+(1-f)P(b),
&
P(a)\le P(b),
\\[2mm]
f\frac{P(b)}{P(a)}
+
(1-f)P(b),
&
P(a)>P(b).
\end{cases}
$$

Workload validation achieved:

$$
468/468
$$

queries within:

$$
10^{-12}
$$

of the native oracle, with maximum relative error:

$$
6.66\times10^{-16}.
$$


### 4.3 MCV--FD composition

The two mechanisms communicate through CE state:

$$
X_0
\xrightarrow{MCV}
X_1
\xrightarrow{FD}
X_2.
$$

For example:

$$
MCV(a,b)
\rightarrow
estimatedclauses(a,b)
\rightarrow
FD(a,b,c)\text{ unavailable}.
$$

A disjoint dependency can remain applicable.

This establishes that heterogeneous statistics mechanisms can require stateful
composition rather than independent response models.


## 5. Semantics-Guided Physical-Design Search

CE-Replay serves three roles:

$$
\boxed{
\text{evaluation}
+
\text{dependency exposure}
+
\text{search guidance}
}
$$


### 5.1 Design-dependent evaluation

For each move:

$$
D\rightarrow D',
$$

the optimizer evaluates:

$$
\Delta(D,D')
=
L(G_Q(D;\mathcal P_0))
-
L(G_Q(D';\mathcal P_0)).
$$

No singleton-benefit assumption is required.


### 5.2 Incremental invalidation

Only queries whose replay programs depend on a changed candidate need to be
re-evaluated.

At 2,253 Census pair candidates, a candidate affects only:

$$
4.36/468
$$

queries per toggle on average in the full-scale experiment.

This reduced replay work by approximately:

$$
107.3\times
$$

in query-evaluation count relative to full workload recomputation.


### 5.3 Semantic neighborhoods

CE dependencies expose candidate neighborhoods that can restrict local-search moves.

However, semantic locality is not the only interaction channel.

Under a global storage budget:

$$
\mathcal M_Y
=
\mathcal M_{\mathrm{semantic}}
\cup
\mathcal M_{\mathrm{budget}}.
$$

In the measured improving swaps:

- 1-hop semantic:

$$
2.18\%
$$

- 2-hop semantic:

$$
39.60\%
$$

- disconnected budget exchanges:

$$
58.23\%
$$

Thus semantic locality is useful for search pruning, but a global resource-exchange
channel remains necessary.


## 6. Joint Selection and Precedence

For PostgreSQL MCV, only precedence relations reachable through native tie states can
affect estimation.

For the full Census marginal design:

- selected candidates: 208;
- candidates participating in reachable ties: 194;
- reachable tie edges: 540;
- mean tie degree: 5.57;
- maximum tie degree: 16.

This replaces an irrelevant conceptual search over:

$$
|Y|!
$$

permutations with a much smaller semantics-derived precedence neighborhood.


### 6.1 Alternating refinement

Because:

$$
Y^*(\pi_1)
\neq
Y^*(\pi_2),
$$

selection and precedence are optimized jointly through alternating refinement:

$$
Y
\leftarrow
OptimizeSelection(\pi),
$$

followed by:

$$
\pi
\leftarrow
OptimizePrecedence(Y).
$$

The full Census experiment improved:

$$
812.671
\rightarrow
795.512.
$$

The improvement was:

$$
2.1115\%.
$$

Most of the gain appeared in the first two rounds, providing no current evidence that
a substantially more complex joint solver is required.


## 7. Cross-Mechanism Physical Design

Let the candidate universe contain both MCV and FD statistics:

$$
S
=
S_{MCV}\cup S_{FD}.
$$

Independent mechanism selection ignores state-mediated suppression.

Joint semantic optimization instead evaluates the composed replay:

$$
G_q^{MCV+FD}(D).
$$

In the v4 Census setting:

| Strategy | Loss | MCV | FD | Never-consumed FD |
|---|---:|---:|---:|---:|
| MCV-only | 813.522 | 209 | 0 | 0 |
| FD-only | 11,791.248 | 0 | 203 | 0 |
| Independent | 813.942 | 203 | 97 | 72 |
| Joint semantic | **806.444** | 206 | 54 | **0** |

Joint semantic optimization improved over independent selection by:

$$
0.9213\%.
$$

Of the 97 FD objects selected independently:

$$
\frac{72}{97}
=
74.23\%
$$

were never consumed by any workload query after composition with MCV.

These objects consumed:

$$
2210\text{ bytes},
$$

corresponding to approximately:

$$
2.10\%
$$

of the modeled total budget.

Under the modeled workload, CE objective, and storage budget, those objects paid
resource cost while contributing zero replay benefit.

This demonstrates that compositional CE semantics can materially affect statistics
physical-design decisions.


## 8. Deployment and Payload Drift

Optimization uses a frozen candidate payload repository:

$$
\mathcal P_0.
$$

For a hypothetical design

$$
D,
$$

replay activates the relevant payload subset:

$$
P(D;\mathcal P_0).
$$

Physical deployment creates statistics again and may produce a different repository:

$$
\mathcal P'
=
B(Data,D^*,\lambda,\xi').
$$

Therefore two effects must be separated.


### 8.1 Semantic replay error

For the same fresh payload:

$$
\epsilon_{\mathrm{semantic}}
=
L_{\mathrm{Native}}(D^*;\mathcal P')
-
L_{\mathrm{Replay}}(D^*;\mathcal P').
$$


### 8.2 Payload drift

Between optimization-time and deployment-time payloads:

$$
\Delta_{\mathrm{payload}}
=
L_{\mathrm{Replay}}(D^*;\mathcal P')
-
L_{\mathrm{Replay}}(D^*;\mathcal P_0).
$$

In the MCV deployment experiment:

$$
795.511630
\rightarrow
813.802407,
$$

corresponding to:

$$
+2.2992\%
$$

observed payload drift.

For the fresh payload, replay and native PostgreSQL still agreed for:

$$
468/468
$$

queries within:

$$
10^{-12},
$$

with maximum relative error:

$$
5.64\times10^{-15}.
$$

Thus the observed deployment discrepancy in this experiment was payload-induced
rather than replay-induced.

A single deployment run does not establish the distribution or expected magnitude of
sampling drift.


## 9. Scope

The current semantic-equivalence claim is restricted to validated PostgreSQL 16
statistics-sensitive base-relation restriction fragments.

The supported mechanisms currently include:

- MCV statistics;
- functional dependencies;
- tested predicate forms;
- tested MCV-to-FD composition.

The system does not currently claim exact replay of:

- arbitrary PostgreSQL CE;
- join estimation;
- arbitrary parameterized paths;
- all expression semantics;
- all extended-statistics mechanisms;
- complete optimizer behavior;
- future PostgreSQL versions.

We denote the validated semantic boundary by:

$$
\mathcal F_{\mathrm{supported}}.
$$

All exactness claims are relative to this boundary.


## 10. Core Contributions

### C1. Statistics-parametric CE specialization

The system specializes native statistics-sensitive CE semantics into a workload-level
executable representation:

$$
G_Q(D,\mathcal P).
$$


### C2. Native-semantic replay

Within the validated PostgreSQL 16 MCV and FD fragments, external replay matches
instrumented native computation to floating-point precision.


### C3. Stateful mechanism composition

Different CE mechanisms are represented as state transitions, allowing interactions
such as:

$$
MCV
\rightarrow
estimatedclauses
\rightarrow
FD.
$$


### C4. Semantics-guided physical-design optimization

The replay representation provides both objective evaluation and dependency
information useful for search.


### C5. Physical realization as part of design

For the supported PostgreSQL MCV semantics:

$$
D=(Y,\pi),
$$

and selection and precedence are empirically coupled.


### C6. Cross-mechanism design

Joint MCV--FD optimization avoids resource allocation to statistics that are selected
independently but suppressed by composed native CE semantics.


## 11. Remaining Core Validation

Before freezing the experimental evaluation, two deployment questions remain.


### 11.1 Mixed-design deployment

Physically deploy the final joint MCV--FD design and measure:

$$
L_{\mathrm{frozen}},
$$

$$
L_{\mathrm{fresh\ replay}},
$$

and:

$$
L_{\mathrm{fresh\ native}}.
$$

This separates payload drift:

$$
\Delta_{\mathrm{payload}}
$$

from semantic replay error:

$$
\epsilon_{\mathrm{semantic}}.
$$


### 11.2 Repeated statistics construction

Repeat `ANALYZE` across multiple independent statistics constructions and measure:

$$
L(D,P_1),
\ldots,
L(D,P_k).
$$

This experiment should determine whether payload variation is small deployment noise
or a material robustness problem.

A robust objective such as:

$$
\min_D
\mathbb E_P[L(D,P)]
$$

should only become part of the core system if repeated experiments show that the
effect is practically important.


## 12. Research Position

Traditional physical-design systems must efficiently estimate optimizer response over
large design spaces.

CE-Replay targets a narrower but structurally different problem: statistics designs
whose effects are mediated by identifiable cardinality-estimation semantics.

The central transformation is:

$$
\boxed{
\text{DBMS statistics-sensitive CE semantics}
\rightarrow
\text{workload-specialized executable CE program}
}
$$

followed by:

$$
\boxed{
\text{executable CE program}
\rightarrow
\text{semantics-guided statistics physical design}
}
$$

The project therefore does not attempt to reproduce the entire optimizer.

It exploits native CE semantics precisely where statistics physical design interacts
with the optimizer's model of the data.