# Evidence-Closed Table Compilation (ECTC): The Mathematical Theory

**A Unified Foundation of Canonical Coordinate Spaces, Semantic Indistinguishability, Orthogonal Poset Algebras, Value Lattices, and Forward-Replay Proof Certification**

*Antigravity Advanced Agentic AI Research Laboratory*  
*Target Publication: ACM Transactions on Database Systems (TODS) / IEEE TKDE / NeurIPS / ACL Formal Methods Track*  
*Date: 2026-11-10*  
*Status: Formal Mathematical Foundation & Research Monograph*

---

## Executive Abstract

We formalize the mathematical theory of **Evidence-Closed Table Compilation (ECTC)**, the foundational architecture of **PCC-Tensor 3.2**. 

The central discovery of this research is not simply that document tables possess multiple dimensions. Rather, it is an information-theoretic limit:

> **The Core Thesis:** Tabular factual assertions depend on a set of jointly necessary, query-relevant semantic coordinates. Standard serialization and chunking operations collapse these coordinates, mapping distinct source states requiring different answers to identical text observations. In this fiber collapse, downstream models face an insurmountable information-loss barrier that no decoder—regardless of parameter scale or training—can universally resolve without additional evidence.

ECTC addresses this barrier by replacing unverified text chunking with a compiler-based, verified representation layer between raw document tables and retrieval engines.

In this monograph, we establish:
1. **The Semantic Indistinguishability Theorem**: The foundational result proving that fiber collapse under lossy serialization renders deterministic decoding mathematically impossible for answer-distinct states.
2. **The 9-Tuple Canonical Semantic Fact Space ($\mathcal{F}$)**: Formulating tabular facts as typed coordinate tuples $\mathcal{F} = \langle E, M, R, C, T, U, Q, V, P \rangle$ over a discrete relational product domain.
3. **The Coordinate Severance & Token Hull Bounds**: Tight geometric limits proving that contiguous token budgets must sever semantic coordinates whenever the spatial anchor diameter or convex hull exceeds chunk capacity.
4. **The Scope-Aware Unit & Context Algebra (SUCA)**: Formulating row and column hierarchies as orthogonal, incomparable sub-posets ($\text{Row}_i \parallel \text{Col}_j$) and proving that property-independent projection operators ($\phi_k$) eliminate cross-property context contamination.
5. **The Order-of-Magnitude Scale Divergence Law**: The general scale error formula $\mathcal{E} = |10^{s_0 - s} - 1|$, explaining deterministic million-fold hallucinations in financial schedules.
6. **The Typed Value Domain & Exact Decimal Arithmetic**: Constructing an information-refinement partial order $(\mathcal{V}, \sqsubseteq)$ over 28-digit fixed-point decimals ($\mathbb{D}_{28}$, Banker's Rounding), intervals, bounded inequalities, and GAAP missing-value taxonomies.
7. **The Footnote Reference Graph ($G_{\text{ref}}$) & Lineage DAGs**: Canonical Elementary Cycle Decomposition for circular notes and acyclic directed computation graphs for derived aggregates.
8. **Role-Specific Evidence Provenance & Cryptographic Boundaries**: The 5-anchor atomic evidence bundle $P = \langle \alpha_V, \alpha_M, \alpha_T, \alpha_U, \alpha_E, \{\alpha_{F_k}\} \rangle$ and the formal distinction between content digests and cryptographic authentication.
9. **Forward-Replay Verification & Tri-State Truth Domain**: Independent, executable transformation replay and the formal tri-state verification predicate $\operatorname{Verify}(\mathcal{S}) \in \{\text{PASS}, \text{FAIL}, \text{UNRESOLVED}\}$ governing retrieval admission.
10. **The 20 Formal Contracts ($C_1$–$C_{20}$) & Conditional Soundness**: Rigorous conditional guarantees establishing internal consistency relative to declared parser and verifier contracts.

---

# 1. The Mathematical Foundation: Semantic Indistinguishability

### 1.1 Formal System Model

Let:
- $\mathcal{X}$ denote the universe of all possible structured source-table states. A state $x \in \mathcal{X}$ contains full 2D geometric cell layouts, parent-child row hierarchies, superheaders, unit declarations, and footnote citations.
- $\mathcal{Y} \subseteq \Sigma^*$ denote the observation space of serialized, chunked character or token sequences.
- $g_B: \mathcal{X} \longrightarrow \mathcal{Y}$ denote the composite serialization and chunking observation operator under configuration $B$ (e.g. token budget, markdown projection, row-grouping heuristic).
- $\mathcal{A}$ denote the discrete or continuous semantic answer space for a natural language or structured query.
- $q: \mathcal{X} \longrightarrow \mathcal{A}$ denote the ground-truth semantic query evaluation map that computes the correct answer from the complete structured table state $x$.
- $d: \mathcal{Y} \longrightarrow \mathcal{A}$ denote any downstream decoding operator (e.g. an LLM, classifier, or heuristic extractor) that attempts to answer query $q$ observing solely $y = g_B(x)$.

---

### 1.2 Observation Fibers and Answer Identifiability

#### Definition 1.1 (Observation Fiber)
For any observation $y \in \mathcal{Y}$, the **observation fiber** $g_B^{-1}(y) \subseteq \mathcal{X}$ is the pre-image of $y$ under the observation map:
$$g_B^{-1}(y) \triangleq \{ x \in \mathcal{X} \mid g_B(x) = y \}$$

#### Definition 1.2 (Query Answer-Identifiability)
A query $q$ is **answer-identifiable** under observation $y = g_B(x)$ if and only if the ground-truth answer map $q$ is constant across the entire fiber $g_B^{-1}(y)$:
$$\forall x_1, x_2 \in g_B^{-1}(y), \quad q(x_1) = q(x_2)$$

If $q$ is not constant on $g_B^{-1}(y)$, the observation $y$ suffers from **query-relevant information loss**.

---

### 1.3 The Semantic Indistinguishability Theorem

#### Theorem 1.1 (Semantic Indistinguishability)
Let $g_B: \mathcal{X} \to \mathcal{Y}$ be an observation operator and $q: \mathcal{X} \to \mathcal{A}$ be a query.  
If there exist two source states $x_1, x_2 \in \mathcal{X}$ such that:
$$g_B(x_1) = g_B(x_2) \quad \text{and} \quad q(x_1) \ne q(x_2)$$
then **no deterministic decoder $d: \mathcal{Y} \to \mathcal{A}$ receiving only the observation $g_B(x)$ can correctly answer $q$ for both $x_1$ and $x_2$**.

#### Proof
1. Since $x_1$ and $x_2$ map to the identical observation:
   $$g_B(x_1) = g_B(x_2) = y \in \mathcal{Y}$$
2. A deterministic decoder $d$ is a single-valued function $d: \mathcal{Y} \to \mathcal{A}$. Applied to the input observation $y$, it must yield a single, unique value:
   $$d(y) = a^* \in \mathcal{A}$$
3. Consequently:
   $$d(g_B(x_1)) = d(y) = a^* \quad \text{and} \quad d(g_B(x_2)) = d(y) = a^*$$
4. For the decoder to be correct on state $x_1$, correctness requires:
   $$d(g_B(x_1)) = q(x_1) \implies a^* = q(x_1)$$
5. For the decoder to be correct on state $x_2$, correctness requires:
   $$d(g_B(x_2)) = q(x_2) \implies a^* = q(x_2)$$
6. Combining steps 4 and 5 yields:
   $$q(x_1) = a^* = q(x_2) \implies q(x_1) = q(x_2)$$
7. But the hypothesis explicitly states:
   $$q(x_1) \ne q(x_2)$$
8. This is a direct contradiction.
9. Therefore, no deterministic decoder $d$ can return the correct answer for both source states using only the observation $y = g_B(x)$.  
$\blacksquare$

---

### 1.4 Concrete Financial Counterexample

Consider two distinct SEC Form 10-Q filing states:

$$\begin{aligned}
x_1: \quad &\begin{array}{l|cc}
\textbf{Metric} & \textbf{Three Months Ended Sept 30, 2026} & \textbf{Nine Months Ended Sept 30, 2026} \\
\hline
\text{Operating Loss} & (158.20) & (86.87)
\end{array} \\
\\
x_2: \quad &\begin{array}{l|cc}
\textbf{Metric} & \textbf{Nine Months Ended Sept 30, 2026} & \textbf{Three Months Ended Sept 30, 2026} \\
\hline
\text{Operating Loss} & (158.20) & (86.87)
\end{array}
\end{aligned}$$

Let query $q$ be: *"What was the Operating Loss for the Three Months Ended September 30, 2026?"*
$$q(x_1) = -158.20 \times 10^6, \quad q(x_2) = -86.87 \times 10^6 \implies q(x_1) \ne q(x_2)$$

Suppose a naive sliding-window chunker extracts only the row text without column superheaders:
$$g_B(x_1) = g_B(x_2) = \text{"Operating Loss \dots (158.20) \dots (86.87)"}$$

By Theorem 1.1, because $g_B(x_1) = g_B(x_2)$ while $q(x_1) \ne q(x_2)$, no downstream language model—regardless of parameter count—can determine whether the first number represents the 3-month or 9-month figure. The information is physically absent from the observation.

---

### 1.5 Probabilistic & Information-Theoretic Corollaries

#### Corollary 1.2 (Zero-One Loss Bounds)
Let $\mathbb{P}(X)$ be a probability distribution over source table states $\mathcal{X}$.  
Let observation $y \in \mathcal{Y}$ have fiber $g_B^{-1}(y)$ partitioned into $K$ answer equivalence classes $\{C_1, C_2, \dots, C_K\}$ where:
$$C_k = \{ x \in g_B^{-1}(y) \mid q(x) = a_k \}, \quad a_i \ne a_j \text{ for } i \ne j$$
Let $p_k = \mathbb{P}(x \in C_k \mid g_B(x) = y)$ be the posterior probability of answer class $a_k$.

Then the minimum conditional error probability $P_e(y)$ for any decoder $d$ is:
$$P_e(y) = 1 - \max_{1 \le k \le K} p_k$$
If all $K$ answer classes are conditionally equiprobable ($p_k = 1/K$):
$$\mathbb{P}(\text{correct} \mid y) \le \frac{1}{K} \implies P_e(y) \ge 1 - \frac{1}{K}$$

#### Corollary 1.3 (Fano's Inequality Lower Bound)
Under random variable $Q = q(X)$ with discrete entropy $H(Q \mid Y = y)$:
$$P_e(y) \ge \frac{H(Q \mid Y = y) - 1}{\log_2 |\mathcal{A}|}$$
When coordinate severance creates $d$ independent binary coordinate ambiguities, $H(Q \mid Y = y) = d$, establishing that positive conditional entropy strictly bounds the error probability away from zero.

---

# 2. Canonical Semantic Fact Space ($\mathcal{F}$)

Rather than relying on continuous differential manifolds, we formalize the Canonical Table Intermediate Representation (CTIR) as a **typed relational fact space**.

### Definition 2.1 (Relational Product Fact Space)
Let the semantic fact domain $\mathcal{F}$ be defined over a Cartesian product of 9 discrete semantic domains:
$$\mathcal{F} \subseteq \mathcal{D}_E \times \mathcal{D}_M \times \mathcal{D}_R \times \mathcal{D}_C \times \mathcal{D}_T \times \mathcal{D}_U \times \mathcal{D}_Q \times \mathcal{V} \times \mathcal{P}_{\text{evid}}$$

Every canonical source fact $f \in \mathcal{F}$ is an immutable 9-tuple:
$$\boxed{F = \langle E, M, R, C, T, U, Q, V, P \rangle}$$

---

### Definition 2.2 (Coordinate Domain Specifications)

1. **Entity Coordinate ($E \in \mathcal{D}_E$)**:
   $$E = \langle \text{entity\_id} \in \Sigma^*, \; \text{legal\_name} \in \Sigma^*, \; \text{lei} \in \Sigma^* \cup \{\bot\}, \; \text{level} \in \{\text{CONSOLIDATED}, \text{PARENT}, \text{SEGMENT}\} \rangle$$
   Ensures corporate subject identity is permanently bound, eliminating multi-subsidiary entity drift.

2. **Metric Coordinate ($M \in \mathcal{D}_M$)**:
   $$M = \langle \text{metric\_id} \in \Sigma^*, \; \text{raw\_label} \in \Sigma^*, \; \text{concept} \in \Sigma^* \cup \{\bot\}, \; \text{statement} \in \{\text{IS}, \text{BS}, \text{CF}, \text{EQ}, \text{NOTES}\} \rangle$$
   Represents the financial or operational accounting line item.

3. **Row Ancestry Path ($R \in \mathcal{D}_R$)**:
   $$R = (r_1, r_2, \dots, r_k) \in (\Sigma^*)^k, \quad k \ge 0$$
   An ordered tuple representing the root-to-leaf path in the row stub tree:
   $$r_1 = \text{Primary Section} \succ r_2 = \text{Subsection} \succ \dots \succ r_k = \text{Immediate Line Item}$$

4. **Column Ancestry Path ($C \in \mathcal{D}_C$)**:
   $$C = (c_1, c_2, \dots, c_j) \in (\Sigma^*)^j, \quad j \ge 1$$
   An ordered tuple representing the superheader hierarchy:
   $$c_1 = \text{Header Level 1} \succ c_2 = \text{Header Level 2} \succ \dots \succ c_j = \text{Leaf Column Label}$$

5. **Temporal Coordinate ($T \in \mathcal{D}_T$)**:
   Defined over an Allen Interval Algebra $\mathcal{A}_{\text{allen}}$:
   $$T \in \mathcal{T}_{\text{duration}} \cup \mathcal{T}_{\text{instant}}$$
   $$\mathcal{T}_{\text{duration}} = \{ \langle t_{\text{start}}, t_{\text{end}}, \Delta d, \text{label} \rangle \mid t_{\text{start}} \le t_{\text{end}} \in \text{Date}, \; \Delta d = (t_{\text{end}} - t_{\text{start}} + 1) \in \mathbb{N} \}$$
   $$\mathcal{T}_{\text{instant}} = \{ \langle t_{\text{as\_of}}, \text{label} \rangle \mid t_{\text{as\_of}} \in \text{Date} \}$$

6. **Unit Coordinate ($U \in \mathcal{D}_U$)**:
   A 4-dimensional unit vector:
   $$U = \langle \text{currency} \in \text{ISO\_4217} \cup \{\bot\}, \; \text{dimension} \in \text{UCUM} \cup \{\bot\}, \; s \in \mathbb{Z} \cup \{\bot\}, \; \text{prec} \in \mathbb{N} \cup \{\bot\} \rangle$$
   where $s$ is the integer scale exponent defining the magnitude multiplier $10^s$.

7. **Qualifiers ($Q \in \mathcal{D}_Q$)**:
   A key-value dictionary $Q: \mathcal{K} \to \Sigma^*$ capturing accounting basis (e.g. `GAAP`, `Non-GAAP`), restatement status, and scenario.

8. **Typed Semantic Value ($V \in \mathcal{V}$)**:
   An element of the closed typed value lattice (defined in Section 5).

9. **Multi-Source Evidence Bundle ($P \in \mathcal{P}_{\text{evid}}$)**:
   The atomic provenance anchor bundle (defined in Section 7).

---

# 3. Coordinate Severance & Token Hull Geometry

### 3.1 Point-Token Anchor Diameter

Let a fact require $m$ semantic anchors whose positions in a 1D tokenized document sequence are:
$$\mathcal{P}_{\text{anchors}} = \{ p_1, p_2, \dots, p_m \} \subset \mathbb{N}$$

#### Definition 3.1 (Anchor Diameter)
The spatial anchor diameter $\Delta$ is the distance between the outermost anchors:
$$\Delta \triangleq \max_{1 \le i \le m} p_i - \min_{1 \le i \le m} p_i$$

#### Theorem 3.1 (Single-Chunk Coordinate Severance)
Let a chunking operator partition a document into contiguous chunks $S_k = [a_k, b_k]$ with maximum capacity $B \in \mathbb{N}$ tokens ($b_k - a_k \le B - 1$).  
If $\Delta \ge B$, **no single chunk can contain all $m$ anchors**:
$$\forall S_k, \quad \exists p_i \in \mathcal{P}_{\text{anchors}} \quad \text{such that} \quad p_i \notin S_k$$

#### Proof
1. A contiguous chunk of $B$ integer tokens spans an interval $[a_k, b_k]$ with length:
   $$\operatorname{span}(S_k) = b_k - a_k \le B - 1$$
2. For all anchors to reside in $S_k$, we must have:
   $$a_k \le \min_i p_i \le \max_i p_i \le b_k$$
3. Thus:
   $$\Delta = \max_i p_i - \min_i p_i \le b_k - a_k \le B - 1 < B$$
4. Hence, if $\Delta \ge B$, no single chunk can contain the entire anchor set.  
$\blacksquare$

---

### 3.2 Interval-Anchor Convex Hull

When evidence anchors are intervals $[\ell_i, r_i]$ rather than single points:

#### Definition 3.2 (Anchor Convex Hull Length)
The convex hull length $H$ covering all interval anchors is:
$$H \triangleq \max_{1 \le i \le m} r_i - \min_{1 \le i \le m} \ell_i + 1$$

#### Theorem 3.2 (Interval Severance Invariant)
All $m$ interval anchors fit within a contiguous token window of budget $B$ only if:
$$H \le B$$
If $H > B$, severance across at least two chunks is geometrically guaranteed.

---

### 3.3 Explicit Separation: Single-Chunk Closure vs. System Recoverability

> **Crucial Methodological Distinction:**  
> Theorems 3.1 and 3.2 prove that **single contiguous chunks** cannot contain all necessary coordinate anchors when $H > B$.  
> They do **not** imply that an entire multi-chunk system cannot answer the query if it employs multi-hop retrieval, table-aware header injection, or relational indexing.  
> However, any multi-chunk system that successfully resolves severed facts must perform a **semantic join** across chunks, which itself requires verified coordinates and provenance to avoid incorrect cross-row/column binding.

---

# 4. Scope-Aware Unit & Context Algebra (SUCA)

### 4.1 Orthogonal Row and Column Scopes

Traditional documents adhere to a total tree nesting:
$$\text{Document} \prec \text{Chapter} \prec \text{Section} \prec \text{Paragraph} \prec \text{Sentence}$$

In semi-structured tables, the structural hierarchy diverges into two independent semantic axes:

#### Definition 4.1 (Scope Poset)
The scope domain $\mathcal{S}$ is a partially ordered set $(\mathcal{S}, \preceq)$ defined as:
$$\mathcal{S} = \{ \text{Doc}, \text{Table}, \text{Section} \} \cup \{ \text{Row}_i \}_{i=1}^N \cup \{ \text{Col}_j \}_{j=1}^M \cup \{ \text{Cell}_{i,j} \}_{i,j}$$

The partial order satisfies:
$$\text{Doc} \prec \text{Table} \prec \text{Section} \prec \text{Row}_i \prec \text{Cell}_{i,j}$$
$$\text{Doc} \prec \text{Table} \prec \text{Section} \prec \text{Col}_j \prec \text{Cell}_{i,j}$$

#### Axiom 4.1 (Row-Column Incomparability)
For any row $i$ and column $j$:
$$\text{Row}_i \not\preceq \text{Col}_j \quad \text{and} \quad \text{Col}_j \not\preceq \text{Row}_i \quad \iff \quad \text{Row}_i \parallel \text{Col}_j$$

#### Definition 4.2 (Cell as Coordinate Meet)
A data cell $\text{Cell}_{i,j}$ represents the intersection (infimum) of its row-scope and column-scope paths:
$$\text{Cell}_{i,j} = \text{Row}_i \sqcap \text{Col}_j$$

```
                         Document Scope
                               │
                          Table Scope
                               │
                         Section Scope
                               │
                   ┌───────────┴───────────┐
                   ▼                       ▼
              Row Scope ────────────── Col Scope   (Incomparable: Row || Col)
                   │                       │
                   └───────────┬───────────┘
                               ▼
                           Cell Scope  (Infimum: Cell = Row ⊓ Col)
```

---

### 4.2 Property-Independent Poset Projection

Let $U = \langle u_{\text{curr}}, u_{\text{phys}}, u_{\text{scale}}, u_{\text{prec}} \rangle$ be the unit context vector.

#### Theorem 4.1 (Property-Independent Projection Theorem)
Let candidate assertions for property $k$ across applicable scopes be evaluated via independent projection functions $\phi_k$:
$$\phi_k(\text{Cell}_{i,j}) = \operatorname{FirstDefined}\Big( \operatorname{Cell}(u_k), \; \mathcal{A}\big(\operatorname{Row}_i(u_k), \operatorname{Col}_j(u_k)\big), \; \operatorname{Section}(u_k), \; \operatorname{Table}(u_k), \; \operatorname{Doc}(u_k) \Big)$$
where $\mathcal{A}$ is a defined precedence arbitrator (e.g. Row precedes Column for scale overrides, Column precedes Row for temporal qualifiers).

Then:
1. **Property Isolation**: An assertion on facet $u_k$ at scope $\sigma_a$ cannot overwrite or nullify an orthogonal facet $u_m$ ($m \ne k$) declared at scope $\sigma_b$.
2. **Local Override Soundness**: A local override on scale ($s=0$) at row scope strictly masks global table scale ($s=6$) without destroying global currency ($USD$).

#### Proof
1. Let $\sigma_{\text{tbl}}$ declare currency $u_{\text{curr}} = \text{"USD"}$ and scale $u_{\text{scale}} = 6$ ($10^6$), with $u_{\text{phys}} = \bot$.
2. Let $\sigma_{\text{row}}$ declare metric *Diluted EPS* with physical dimension $u_{\text{phys}} = \text{"USD/share"}$ and scale override $u_{\text{scale}} = 0$ ($10^0$), with currency $u_{\text{curr}} = \bot$.
3. Under a monolithic resolver $\Omega(\sigma) = \langle u_{\text{curr}}, u_{\text{phys}}, u_{\text{scale}}, u_{\text{prec}} \rangle$:
   - Selecting $\sigma_{\text{row}}$ yields: $\langle \bot, \text{"USD/share"}, 0, \bot \rangle$ $\implies$ currency is lost ($\bot$).
   - Selecting $\sigma_{\text{tbl}}$ yields: $\langle \text{"USD"}, \bot, 6, \bot \rangle$ $\implies$ scale $10^6$ is applied (\$1,450,000 per share).
4. Under independent projections $\phi_k$:
   $$\phi_{\text{curr}}(\text{Cell}) = \operatorname{FirstDefined}(\bot, \operatorname{Row}(\bot), \operatorname{Table}(\text{"USD"})) = \mathbf{\text{"USD"}}$$
   $$\phi_{\text{phys}}(\text{Cell}) = \operatorname{FirstDefined}(\bot, \operatorname{Row}(\text{"USD/share"}), \operatorname{Table}(\bot)) = \mathbf{\text{"USD/share"}}$$
   $$\phi_{\text{scale}}(\text{Cell}) = \operatorname{FirstDefined}(\bot, \operatorname{Row}(0), \operatorname{Table}(6)) = \mathbf{0}$$
5. The combined unit is:
   $$U_{\text{resolved}} = \langle \text{"USD"}, \text{"USD/share"}, 0, 2 \rangle$$
6. Valuation yields: $1.45 \times 10^0 = \mathbf{\$1.45\text{ per share}}$, with zero cross-property interference.  
$\blacksquare$

---

### 4.3 General Order-of-Magnitude Scale Divergence Law

#### Theorem 4.2 (Scale Divergence Law)
Let a cell have true value significand $v \ne 0$ and true scale exponent $s \in \mathbb{Z}$, representing physical quantity:
$$Q = v \cdot 10^s$$
If an unverified downstream process defaults to or assumes scale exponent $s_0 \in \mathbb{Z}$, producing estimate:
$$\widehat{Q} = v \cdot 10^{s_0}$$
the relative absolute error $\mathcal{E}$ is:
$$\boxed{\mathcal{E}(s, s_0) \triangleq \frac{|Q - \widehat{Q}|}{|Q|} = \left| 10^{s_0 - s} - 1 \right|}$$

#### Proof
$$\frac{|Q - \widehat{Q}|}{|Q|} = \frac{|v \cdot 10^s - v \cdot 10^{s_0}|}{|v \cdot 10^s|} = \frac{|v| \cdot |10^s - 10^{s_0}|}{|v| \cdot 10^s} = \frac{|10^s(1 - 10^{s_0 - s})|}{10^s} = |1 - 10^{s_0 - s}| = |10^{s_0 - s} - 1| \quad \blacksquare$$

#### Special Cases:
- **Defaulting to Scale Zero ($s_0 = 0$) on Millions ($s = 6$):**
  $$\mathcal{E}(6, 0) = |10^{-6} - 1| = |0.000001 - 1| = 0.999999 \quad (\mathbf{99.9999\% \text{ relative error}})$$
  The true quantity is exactly $1,000,000\times$ the unscaled estimate.
- **Defaulting to Scale Zero ($s_0 = 0$) on Thousands ($s = 3$):**
  $$\mathcal{E}(3, 0) = |10^{-3} - 1| = 0.999 \quad (\mathbf{99.9\% \text{ relative error}})$$

---

# 5. The Typed Value Domain & Exact Decimal Arithmetic

### 5.1 Value Domain Construction

The value space $\mathcal{V}$ is partitioned into four mutually disjoint semantic sub-domains:
$$\mathcal{V} = \mathcal{V}_{\text{exact}} \;\dot\cup\; \mathcal{V}_{\text{bounded}} \;\dot\cup\; \mathcal{V}_{\text{range}} \;\dot\cup\; \mathcal{V}_{\text{missing}}$$

```
                             Top: ⊤ (Conflict / Incompatible Assertions)
                              ╱        │         │        ╲
                             ╱         │         │         ╲
                            ▼          ▼         ▼          ▼
                        V_exact    V_bounded  V_range   V_missing
                            ╲          │         │         ╱
                             ╲         │         │        ╱
                              ▼        ▼         ▼       ▼
                             Bottom: ⊥ (Unresolved / No Information)
```

1. **Exact Numeric Domain ($\mathcal{V}_{\text{exact}}$)**:
   $$\mathcal{V}_{\text{exact}} = \{ \langle \text{raw} \in \Sigma^*, \; d \in \mathbb{D}_{28} \rangle \}$$
   where $\mathbb{D}_{28}$ is the set of fixed-point decimals with 28 digits of precision operating under Banker's Rounding (`ROUND_HALF_EVEN`).
   All arithmetic is strictly closed:
   $$\forall a, b \in \mathbb{D}_{28}, \quad a \odot b \in \mathbb{D}_{28} \quad (\odot \in \{+, -, \times, /\})$$
   Eliminates all IEEE-754 binary floating-point representation drift ($0.1 + 0.2 \ne 0.3$).

2. **Bounded Inequality Domain ($\mathcal{V}_{\text{bounded}}$)**:
   $$\mathcal{V}_{\text{bounded}} = \{ \langle \text{raw} \in \Sigma^*, \; b \in \mathbb{D}_{28}, \; op \in \{\text{LT}, \text{LE}, \text{GT}, \text{GE}\} \rangle \}$$
   Maps thresholds (e.g. `< 0.01`, `≥ 95%`) to semi-infinite intervals:
   $$\text{Interval}(\langle b, \text{LT} \rangle) = (-\infty, b), \quad \text{Interval}(\langle b, \text{GE} \rangle) = [b, +\infty)$$

3. **Closed Range Interval Domain ($\mathcal{V}_{\text{range}}$)**:
   $$\mathcal{V}_{\text{range}} = \{ \langle \text{raw} \in \Sigma^*, \; l \in \mathbb{D}_{28}, \; u \in \mathbb{D}_{28} \rangle \mid l \le u \}$$

4. **GAAP Missing-Value Domain ($\mathcal{V}_{\text{missing}}$)**:
   $$\mathcal{V}_{\text{missing}} = \{ \langle \text{raw} \in \Sigma^*, \; \text{reason} \in \mathcal{M}_{\text{reasons}} \rangle \}$$
   $$\mathcal{M}_{\text{reasons}} = \{ \text{NIL\_DASH}, \text{REPORTED\_ZERO}, \text{NOT\_APPLICABLE}, \text{NOT\_MEANINGFUL}, \text{IMMATERIAL}, \text{SUPPRESSED}, \text{UNKNOWN} \}$$
   Prevents conflating an explicit reported zero (`0.00`) with an unstated dash (`—`).

---

### 5.2 Information-Refinement Partial Order

#### Definition 5.1 (Information Order $\sqsubseteq$)
Let $\gamma: \mathcal{V} \to \mathcal{P}(\mathbb{R} \cup \mathcal{M}_{\text{reasons}})$ map each represented value to the set of concrete states it permits:
- $\gamma(\bot) = \mathbb{R} \cup \mathcal{M}_{\text{reasons}}$ (no information; permits everything)
- $\gamma(\langle \text{raw}, d \rangle) = \{ d \}$
- $\gamma(\langle \text{raw}, b, \text{LT} \rangle) = (-\infty, b)$
- $\gamma(\langle \text{raw}, l, u \rangle) = [l, u]$
- $\gamma(\langle \text{raw}, r \rangle) = \{ r \}$
- $\gamma(\top) = \emptyset$ (inconsistent/conflict; permits nothing)

The partial order $\sqsubseteq$ (information refinement) is defined by set inclusion:
$$v_1 \sqsubseteq v_2 \iff \gamma(v_2) \subseteq \gamma(v_1)$$

Under this ordering:
- $\bot \sqsubseteq v \sqsubseteq \top$ for all $v \in \mathcal{V}$.
- For distinct exact values $d_1 \ne d_2$, $\gamma(d_1) \cap \gamma(d_2) = \emptyset \implies d_1 \sqcup d_2 = \top$.

---

# 6. Topological DAGs, Reference Cycles, & Lineage

### 6.1 Row and Column Acyclicity
Tables are structurally constrained by two Directed Acyclic Graphs (DAGs):
1. **Row Hierarchy DAG**: $G_{\text{row}} = (V_R, E_R)$, where $(r_a, r_b) \in E_R \iff r_a = \operatorname{parent}(r_b)$.
2. **Column Header DAG**: $G_{\text{col}} = (V_C, E_C)$, where $(c_a, c_b) \in E_C \iff c_a = \operatorname{parent}(c_b)$.

Both graphs are verified strictly acyclic (**Contract C5**):
$$\operatorname{Cycles}(G_{\text{row}}) = \emptyset \quad \land \quad \operatorname{Cycles}(G_{\text{col}}) = \emptyset$$

---

### 6.2 Footnote Reference Cycles and Canonical Decomposition

Unlike header trees, footnote citations often form circular cross-references (Note A references Note B, Note B references Note A).

Let $G_{\text{ref}} = (V_{\text{fn}}, E_{\text{ref}})$ be the directed footnote citation graph.  
To prevent infinite recursion during retrieval expansion, ECTC canonicalizes elementary cycles:

#### Theorem 6.1 (Canonical Cycle Decomposition)
Let $V_{\text{fn}}$ be totally ordered by an index mapping $\operatorname{idx}: V_{\text{fn}} \to \mathbb{N}$.  
An elementary directed cycle $\mathcal{C} = (v_1, v_2, \dots, v_k, v_1)$ is in canonical form if and only if:
$$v_1 = \min_{1 \le i \le k} \operatorname{idx}(v_i)$$

Using Johnson's elementary cycle enumeration, all cycles in $G_{\text{ref}}$ can be enumerated without recursion hazards in time:
$$\mathcal{O}\big((|V_{\text{fn}}| + |E_{\text{ref}}|)(K + 1)\big)$$
where $K$ is the number of elementary cycles.

---

### 6.3 Derived Fact Calculation Lineage

When a table reports calculated aggregate quantities (e.g. $\text{Free Cash Flow} = \text{Operating Cash Flow} + \text{CapEx Outflow}$):

#### Definition 6.1 (Derived Fact Tuple)
A derived fact $f_d$ has explicit calculation lineage:
$$f_d = \langle \text{id}, \; \text{expr}, \; \vec{\mathcal{F}}_{\text{inputs}}, \; V_{\text{calc}}, \; U, \; \text{display}, \; \text{engine}=\text{"DECIMAL\_KERNEL"}, \; \text{status} \rangle$$

The verifier enforces three invariants (**Contract C14**):
1. **Lineage DAG Acyclicity**: The derivation dependency graph over derived facts is strictly acyclic ($\operatorname{Cycles}(G_{\text{calc}}) = \emptyset$).
2. **Failure Propagation**: If any input $f_{\text{in}} \in \vec{\mathcal{F}}_{\text{inputs}}$ has status $\text{FAIL}$, $f_d$ cannot pass.
3. **Exact Arithmetic Replay**: Under `DECIMAL_CONTEXT`:
   $$\operatorname{Execute}(\text{expr}, \{ \operatorname{Val}(u) \mid u \in \vec{\mathcal{F}}_{\text{inputs}} \}) \equiv V_{\text{calc}}$$

---

# 7. Role-Specific Provenance & Cryptographic Trust

### 7.1 Multi-Source Evidence Provenance (MSEP)

A numerical fact cannot be grounded by a single character offset. Its meaning requires **joint role-specific evidence closure** (**Contract C13**):

$$P = \langle \alpha_V, \; \alpha_M, \; \alpha_T, \; \alpha_U, \; \alpha_E, \; \{\alpha_{F_k}\}_{k=1}^K \rangle$$

where each atomic anchor $\alpha$ is defined as:
$$\alpha = \langle \text{id} \in \Sigma^*, \; \mathcal{H}_{\text{doc}} \in \{0, 1\}^{256}, \; \text{page} \in \mathbb{N} \cup \{\bot\}, \; \text{bbox} \in \text{BBox} \cup \{\bot\}, \; \text{raw} \in \Sigma^*, \; \text{role} \in \text{Role} \rangle$$

The semantic anchor roles are:
- $\alpha_V$: **Value Anchor** (grounds raw text `(158.20)`).
- $\alpha_M$: **Metric Anchor** (grounds row label `Photomask amortization`).
- $\alpha_T$: **Period Anchor** (grounds header `Three Months Ended September 30, 2026`).
- $\alpha_U$: **Unit Anchor** (grounds table scale `in Millions`).
- $\alpha_E$: **Entity Anchor** (grounds entity `Chronos Technologies Group Inc.`).
- $\{\alpha_{F_k}\}$: **Footnote Anchors** (grounds explanatory footnotes).

#### Definition 7.1 (Conditional Anchor Closure Predicate)
A fact satisfies Evidence Closure if all mandatory anchors for its fact type are non-null:
$$\operatorname{Closed}(P) \iff \alpha_V \ne \bot \;\land\; \alpha_M \ne \bot \;\land\; \alpha_T \ne \bot \;\land\; \alpha_U \ne \bot \;\land\; \alpha_E \ne \bot$$

If an anchor is absent from the source document, it must be marked `UNRESOLVED` or resolved via an explicit recorded inference rule; it must never be silently fabricated.

---

### 7.2 Cryptographic Content Digests vs. Issuer Authentication

ECTC explicitly distinguishes three trust mechanisms:
1. **Fact Evidence Verification**: Replaying transformation rules and checking provenance anchors against source bytes.
2. **Chunk Integrity Verification**: SHA-256 content hashing establishing that serialized chunk bytes match compiled CTIR snapshots.
3. **Cryptographic Authentication**: Ed25519 digital signatures verified against a public-key trust chain, authenticating compiler and signer identity. A content hash proves immutability relative to a prior state; only a cryptographic signature establishes authorship and provenance authority.

---

# 8. Forward-Replay Ledger & Tri-State Truth Domain

### 8.1 Executable Transformation Registry & Forward Replay

A compiler must not accept a stored boolean flag (`replayed_successfully = True`) as proof of transformation validity.

#### Definition 8.1 (Transformation Record)
Every normalizer step records an immutable ledger entry:
$$\tau = \langle \text{id} \in \Sigma^*, \; \text{rule} \in \mathcal{R}_{\text{allowlist}}, \; s_{\text{in}} \in \Sigma^*, \; s_{\text{out}} \in \Sigma^* \rangle$$

#### Theorem 8.1 (Independent Forward-Replay Invariance - Contract C8)
Let $\mathcal{R}_{\text{allowlist}}$ be an executable registry of deterministic pure functions.  
The verifier re-executes each transformation step independently:
$$\hat{s}_1 = \mathcal{R}[\tau_1.\text{rule}](s_0), \quad \hat{s}_2 = \mathcal{R}[\tau_2.\text{rule}](\hat{s}_1), \quad \dots, \quad \hat{s}_n = \mathcal{R}[\tau_n.\text{rule}](\hat{s}_{n-1})$$

A fact satisfies Contract C8 if and only if:
1. Continuous Replay: $\forall i \in \{1, \dots, n-1\}, \; \tau_{i+1}.s_{\text{in}} = \tau_i.s_{\text{out}}$.
2. Execution Equality: $\forall i \in \{1, \dots, n\}, \; \hat{s}_i = \tau_i.s_{\text{out}}$.
3. Target Soundness: $\hat{s}_n = V_{\text{exact}}.\text{canonical\_display}$.

Any forged transformation, discontinuous input, or un-allowlisted rule produces `TRANSFORMATION_REPLAY_MISMATCH`, immediately failing verification.

---

### 8.2 The Tri-State Verification Predicate

Verification maps a compiled snapshot $\mathcal{S}$ into a tri-state truth domain:
$$\operatorname{Verify}(\mathcal{S}): \mathcal{S}_{\text{CTIR}} \longrightarrow \{\text{PASS}, \; \text{FAIL}, \; \text{UNRESOLVED}\}$$

- $\text{FAIL}$: Any fatal mathematical invariant is violated (e.g. cycle in header DAG, overlapping cells, broken transformation chain, division by zero).
- $\text{UNRESOLVED}$: Non-fatal context is missing (e.g. unstated temporal period, missing optional footnote anchor).
- $\text{PASS}$: All formal contracts evaluate to TRUE with zero error or warning diagnostics.

#### Definition 8.2 (Retrieval Trust Boundary Admission Gate)
The query engine admits fact $f$ into candidate evaluation if and only if both snapshot-level and fact-level statuses pass:
$$\boxed{\operatorname{Admit}(f) \iff \operatorname{Status}(\mathcal{S}) = \text{PASS} \;\land\; \operatorname{Status}(f) = \text{PASS}}$$

---

# 9. The 20 Formal Contracts ($C_1$ through $C_{20}$)

$$\operatorname{Verify}(\mathcal{S}) = \bigwedge_{i=1}^{20} C_i(\mathcal{S})$$

| Contract | Name | Formal Mathematical Invariant | Severity |
| :---: | :--- | :--- | :---: |
| **$C_1$** | **Source Document Integrity** | $\mathcal{H}_{\text{SHA256}}(\mathcal{S}.\text{bytes}) \equiv \mathcal{S}.\text{doc.sha256} \land |\text{bytes}| \equiv \mathcal{S}.\text{doc.length}$ | $\text{FATAL}$ |
| **$C_2$** | **Fragment Preservation** | $\forall c_a \ne c_b \in \mathcal{S}.\text{cells}, \; \text{id}(c_a) \ne \text{id}(c_b)$ | $\text{FATAL}$ |
| **$C_3$** | **Geometric Space Containment** | $\forall \text{bbox}: 0 \le x_0 < x_1 \le \text{width} \land 0 \le y_0 < y_1 \le \text{height}$ | $\text{FATAL}$ |
| **$C_4$** | **Grid Non-Overlap** | $\forall c_a \ne c_b: \operatorname{Area}\left(\operatorname{GridSpan}(c_a) \cap \operatorname{GridSpan}(c_b)\right) = 0$ | $\text{FATAL}$ |
| **$C_5$** | **Structural DAG Acyclicity** | $\operatorname{Cycles}(G_{\text{col}}) = \emptyset \land \operatorname{Cycles}(G_{\text{row}}) = \emptyset$ | $\text{FATAL}$ |
| **$C_6$** | **Column Header Closure** | $\forall \text{col} \in \mathcal{S}.\text{columns}: |\text{col.header\_path}| \ge 1 \land \text{col.header\_path} \ne ()$ | $\text{FATAL}$ |
| **$C_7$** | **Row Hierarchy Closure** | $\forall r \in \mathcal{S}.\text{rows}: \operatorname{parent}(r) \in \mathcal{S}.\text{rows} \cup \{\bot\} \land \operatorname{NoDanglingRefs}$ | $\text{FATAL}$ |
| **$C_8$** | **Raw Value Replay Proof** | $\forall f: \operatorname{Replay}(f.\text{raw}, \vec{\tau}) \equiv f.V \land \forall \tau_i, \tau_i.\text{rule} \in \mathcal{R}_{\text{allowlist}}$ | $\text{FATAL}$ |
| **$C_9$** | **Value Lattice Soundness** | $\forall f: f.V \in \mathcal{V} \land f.V.d \in \mathbb{D}_{28} \land (l \le u \text{ for ranges})$ | $\text{FATAL}$ |
| **$C_{10}$** | **Unit Scale Consistency** | $\forall f: v_{\text{canonical}} = v_{\text{exact}} \times 10^s, \quad s \in \mathbb{Z} \cup \{\bot\}$ | $\text{FATAL}$ |
| **$C_{11}$** | **Temporal Interval Soundness** | $\forall T \in \mathcal{T}_{\text{duration}}: t_{\text{start}} \le t_{\text{end}} \land \Delta d = (t_{\text{end}} - t_{\text{start}} + 1) > 0$ | $\text{FATAL}$ |
| **$C_{12}$** | **Scope Poset Orthogonality** | $\forall f: f.U = \langle \phi_{\text{curr}}, \phi_{\text{phys}}, \phi_{\text{scale}}, \phi_{\text{prec}} \rangle \ne \bot$ | $\text{FATAL}$ |
| **$C_{13}$** | **Provenance Closure** | $\forall f: \operatorname{Closed}(f.P) \equiv \text{TRUE} \implies \alpha_V, \alpha_M, \alpha_T, \alpha_U, \alpha_E \ne \bot$ | $\text{WARN}$ |
| **$C_{14}$** | **Derived Fact Lineage DAG** | $\operatorname{Cycles}(G_{\text{calc}}) = \emptyset \land \operatorname{Execute}(\text{expr}, \vec{\mathcal{F}}_{\text{in}}) \equiv V_{\text{calc}}$ | $\text{FATAL}$ |
| **$C_{15}$** | **Canonical Serialization** | $\operatorname{Deserialize}(\operatorname{Serialize}(\mathcal{S})) \cong \mathcal{S}$ | $\text{FATAL}$ |
| **$C_{16}$** | **Deterministic Invariance** | $\operatorname{Compile}(\text{doc}, \text{adapter}) \equiv \operatorname{Compile}(\text{doc}, \text{adapter})$ | $\text{FATAL}$ |
| **$C_{17}$** | **Fragment Stitching Integrity** | $\forall \text{lt} \in \mathcal{S}.\text{logical\_tables}: \text{lt.is\_stitched} \implies |\text{lt.fragment\_ids}| \ge 2$ | $\text{FATAL}$ |
| **$C_{18}$** | **Footnote Graph Soundness** | $\forall \text{ref} \in \text{cited\_notes}: \text{ref} \in \mathcal{S}.\text{footnote\_definitions}$ | $\text{WARN}$ |
| **$C_{19}$** | **Missing Value Taxonomy** | $\forall f \in \mathcal{V}_{\text{missing}}: f.V.\text{reason} \in \mathcal{M}_{\text{reasons}} \land \text{reason} \ne \bot$ | $\text{FATAL}$ |
| **$C_{20}$** | **Gate Authority Invariant** | $\forall f \in \mathcal{S}.\text{facts}: f.\text{status} = \text{PASS} \iff \operatorname{Verify}(\mathcal{S}) = \text{PASS}$ | $\text{FATAL}$ |

---

# 10. Conditional Correctness Guarantees

We state the correctness guarantees of Evidence-Closed Table Compilation as **conditional mathematical theorems** relative to explicit assumptions:

#### Theorem 10.1 (Conditional Soundness of ECTC)
Assume:
1. **Source Parser Soundness**: The ingestion adapter accurately identifies physical cell spans and textual characters without hallucinating or dropping tokens.
2. **Contract Satisfaction**: The compiled snapshot $\mathcal{S}$ satisfies all 20 formal contracts with zero diagnostics ($\operatorname{Verify}(\mathcal{S}) = \text{PASS}$).
3. **Replay Determinism**: All transformation rules $\tau_i \in \mathcal{R}_{\text{allowlist}}$ are deterministic pure functions.

Then:
1. **Semantic Internal Consistency**: Every emitted fact $f \in \mathcal{S}.\text{source\_facts}$ is mathematically and structurally consistent with the verified source evidence anchors and declared interpretation rules.
2. **Zero Coordinate Severance**: Every fact preserves its complete 9-tuple coordinate set $\langle E, M, R, C, T, U, Q, V, P \rangle$, eliminating single-chunk severance ($\operatorname{CPR} \equiv 100\%$).
3. **Zero Representation Drift**: Every numeric value is exact under 28-digit Decimal context, eliminating binary floating-point representation drift ($\operatorname{NVA} \equiv 100\%$).
4. **Zero Cross-Property Contamination**: Mid-table row overrides strictly preserve orthogonal table-level currency declarations ($\operatorname{UDA} \equiv 100\%$).
5. **Traceable Lineage**: Every fact's source provenance is grounded in verified source file byte digests ($\operatorname{PCR} \equiv 100\%$).

> **Honest Boundary Condition:** ECTC guarantees *internal consistency* relative to verified source evidence and explicit interpretation rules. It cannot prove that the original human author or source document reported objectively true accounting facts.

---

# 11. Controlled Experimental Methodology & Counterexamples

To validate this theory against external benchmarks, the research programme specifies three controlled evaluation protocols:

### 11.1 Controlled Ambiguity Counterexample Protocol
Construct test pairs $x_1, x_2 \in \mathcal{X}$ satisfying:
$$g_B(x_1) = g_B(x_2) \quad \text{and} \quad q(x_1) \ne q(x_2)$$
Test whether flat-text chunking systems fail as predicted by Theorem 1.1, and verify that CTIR's coordinate representation eliminates the fiber collapse.

### 11.2 Coordinate Ablation Protocol
Independently ablate individual coordinate components from CTIR:
- $\mathcal{F} \setminus R$: Ablate row ancestry (causes line-item ambiguity).
- $\mathcal{F} \setminus C$: Ablate column superheaders (causes duration/instant confusion).
- $\mathcal{F} \setminus U_{\text{scale}}$: Ablate scale exponent (induces $10^6\times$ divergence via Theorem 4.2).
- $\mathcal{F} \setminus P$: Ablate footnote anchors (causes cross-chunk footnote decoupling).

### 11.3 Verification Fault Injection Protocol
Synthetically inject forgeries and contract violations:
- Forged transformation records (`rule="invent"`).
- Discontinuous transformation chains ($s_{\text{in}} \ne s_{\text{out}}$).
- Incompatible input currencies in derived fact additions (USD + EUR).
- Dependency cycles in derived facts ($f_{d,1} \to f_{d,2} \to f_{d,1}$).
- Premature fact promotion in unvalidated snapshots.

Measure detection rates across the validator and verify that the retrieval trust boundary strictly excludes all unverified assertions.

---

# 12. Conclusion: The Foundational Mathematical Paradigm

Evidence-Closed Table Compilation provides a rigorous foundation for semi-structured document retrieval. By demonstrating that flat-text RAG failure is rooted in **query-relative fiber collapse (Semantic Indistinguishability)** and resolving it through **orthogonal scope posets, exact value domains, and forward-replay proof certification**, ECTC replaces heuristic text guessing with verified mathematical compilation.

$$\boxed{
\text{Raw Semi-Structured Table}
\xrightarrow[\text{Adapters}]{\text{Parse}}
\text{Coordinate Space } \mathcal{F}
\xrightarrow[\text{Validator}]{\text{Verify}(C_1 \dots C_{20})}
\text{Evidence-Closed Facts (PASS)}
\xrightarrow[\text{Engine}]{\text{Admit}}
\text{Verified Retrieval}
}$$
