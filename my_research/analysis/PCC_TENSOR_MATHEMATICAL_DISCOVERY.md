# PCC-Tensor: Mathematical Discovery and Formal Results

**Working paradigm:** Evidence-Closed Table Compilation (ECTC)  
**System / architecture:** PCC-Tensor  
**Canonical representation:** Canonical Table Intermediate Representation (CTIR)  
**Status:** Research formalization and mathematical audit — not a claim of completed empirical validation

---

## 1. Research question

Can heterogeneous document tables be compiled into a canonical, typed, evidence-preserving representation, and can explicit verification of structure, context, units, time, and provenance improve reliable retrieval compared with flat-text chunking?

The aim is not merely to build another table parser, chunker, or chatbot. The proposed contribution is a compiler-like representation and verification layer between source documents and downstream retrieval or language-model systems.

The central research idea is:

> A table fact can depend on several jointly necessary semantic coordinates. If a serialization or chunking operation removes distinctions needed to interpret a query, two different source states can become indistinguishable to the downstream decoder. A verified canonical representation should preserve the relevant coordinates and the evidence supporting them.

This claim is deliberately narrower than saying that all flat-text retrieval fails, or that every table can be reconstructed perfectly. The formal results below identify specific information-loss conditions and the guarantees that a compiler can provide under explicit assumptions.

## 2. Canonical fact representation

Represent a source fact as the typed tuple

\[
F=\langle E,M,R,C,T,U,Q,V,P\rangle,
\]

where:

| Coordinate | Meaning |
|---|---|
| \(E\) | Entity or subject to which the fact applies |
| \(M\) | Metric, attribute, or measured quantity |
| \(R\) | Row ancestry and row-scope context |
| \(C\) | Column ancestry and column-scope context |
| \(T\) | Temporal scope or reporting period |
| \(U\) | Unit, currency, scale, and precision context |
| \(Q\) | Qualifiers, footnotes, conditions, and modifiers |
| \(V\) | Typed value, including its value kind |
| \(P\) | Provenance bundle connecting the fact to source evidence |

The tuple is a proposed semantic schema. It is not automatically a mathematical tensor merely because it has multiple coordinates. Unless tensor operations, vector spaces, or suitable geometric structure are defined, the more precise description is a **typed relational fact space** or **canonical semantic fact space**.

A useful initial domain is

\[
\mathcal{F}\subseteq E\times M\times R\times C\times T\times U\times Q\times V\times P.
\]

The project’s earlier STES shorthand used a smaller product, \(E\times M\times V\times Q\times P\). That shorthand must either be expanded to include \(R,C,T,U\), or explicitly define which of those coordinates are encapsulated inside \(Q\) or \(P\). The formal specification should use one consistent schema throughout.

## 3. Main result: Semantic Indistinguishability Theorem

### 3.1 Definitions

Let:

- \(X\) be a set of possible structured source-table states;
- \(Y\) be a set of serialized or retrieved observations;
- \(g_B:X\to Y\) be the observation function induced by a particular serialization and retrieval operation (for example, producing a chunk under configuration \(B\));
- \(A\) be the answer space for a query; and
- \(q:X\to A\) be the correct answer to that query when evaluated against the complete source state.

The subscript \(B\) denotes the observation or chunking configuration. The theorem does not assume that every chunking method behaves identically; it applies to the particular observation map being studied.

### 3.2 Theorem

**Theorem 1 — Semantic Indistinguishability.**

If there exist two source states \(x_1,x_2\in X\) such that

\[
g_B(x_1)=g_B(x_2)
\quad\text{and}\quad
q(x_1)\ne q(x_2),
\]

then no deterministic decoder \(d:Y\to A\), receiving only the observation \(g_B(x)\), can return the correct answer for both \(x_1\) and \(x_2\).

**Proof.** Since \(g_B(x_1)=g_B(x_2)\), a deterministic decoder receives exactly the same input in both cases. Therefore,

\[
d(g_B(x_1))=d(g_B(x_2)).
\]

But the correct answers differ:

\[
q(x_1)\ne q(x_2).
\]

The single decoder output therefore cannot equal both correct answers. Hence it must be wrong for at least one of the two source states. \(\square\)

### 3.3 Interpretation

The relevant failure is not merely that the serialization map \(g_B\) is non-injective. Non-injectivity matters for a particular query only when two source states in the same observation fibre have different correct answers.

For an observation \(y\), define its fibre as

\[
 g_B^{-1}(y)=\{x\in X:g_B(x)=y\}.
\]

A query is answer-identifiable from \(y\) only if \(q\) is constant on that fibre. Equivalently,

\[
q(x_1)=q(x_2)
\quad\text{for every }x_1,x_2\in g_B^{-1}(y).
\]

This is the exact query-relative condition. A serializer may discard information irrelevant to one query while still preserving enough information to answer that query correctly.

### 3.4 Probabilistic corollary

Suppose an observation fibre contains \(k\) source states with distinct answer classes and those classes are equally likely. A decoder receiving only that observation has maximum success probability

\[
P(\text{correct}\mid y)\leq \frac{1}{k}.
\]

More generally, if the answer classes have posterior probabilities \(p_1,\ldots,p_k\), the best possible zero-one-loss decoder has conditional error

\[
P(\text{error}\mid y)=1-\max_i p_i.
\]

These bounds require a probability distribution over the possible states or answer classes. They are not unconditional consequences of non-injectivity. Additional side information, metadata, other chunks, indexes, or a verified join can refine the observation and remove the ambiguity.

### 3.5 Research implication

ECTC should seek to preserve the distinctions required by the target query, rather than claim that every possible detail of the source must be embedded in every chunk. A sound retrieval system can also combine independently retrieved evidence, provided that the join is explicit, traceable, and checked.

## 4. Coordinate Severance Result

### 4.1 Token-anchor model

Suppose a fact requires a set of source evidence anchors. For a point-token model, let their token positions be

\[
p_1,p_2,\ldots,p_m.
\]

Define the anchor diameter

\[
\Delta=\max_i p_i-\min_i p_i.
\]

A contiguous chunk containing at most \(B\) tokens can contain point anchors only if

\[
\Delta\leq B-1,
\]

assuming integer token positions and a chunk of \(B\) consecutive token positions. Consequently, if

\[
\Delta\geq B,
\]

no single such chunk can contain all anchors.

For interval-valued anchors \([\ell_i,r_i]\), use the full hull length:

\[
H=\max_i r_i-\min_i\ell_i+1.
\]

All anchors can fit in a single contiguous chunk of capacity \(B\) only if

\[
H\leq B.
\]

Thus \(H>B\) is a sufficient geometric condition for single-chunk severance.

### 4.2 Scope of the result

This is a conditional statement about one contiguous chunk and the specified anchor locations. It does **not** prove that a complete retrieval system cannot recover the relationship by:

- retrieving multiple chunks;
- injecting repeated headers or metadata;
- using a side index;
- joining row, column, footnote, and value evidence; or
- consulting the original source after retrieval.

The experiment should therefore distinguish **single-chunk closure** from **system-level recoverability**. A multi-chunk join can overcome severance, but the join itself must preserve the relevant coordinates and provenance.

### 4.3 Empirical quantities

Distances between headers, values, scale declarations, footnotes, and period labels should be measured on the actual evaluation corpus. A universal anchor diameter (for example, a fixed number of tokens) cannot be asserted without corpus evidence.

## 5. Orthogonal row and column context

### 5.1 Why row and column scopes differ

A cell’s meaning can depend on both its row ancestry and its column ancestry. These are different structural axes. A row-level declaration and a column-level declaration should not be treated as though one were automatically a descendant of the other.

A cell can be represented by the pair

\[
\operatorname{Cell}(r,c)=(r,c),
\]

where \(r\) is a row-scope path and \(c\) is a column-scope path.

A product scope model is useful:

\[
\mathcal{S}=\mathcal{R}\times\mathcal{C},
\]

where \(\mathcal{R}\) and \(\mathcal{C}\) each carry their own specificity or ancestry relation. If meets or joins are needed, they must be defined in the row and column component orders and then combined componentwise where they exist. The notation

\[
\operatorname{Cell}_{i,j}=\operatorname{Row}_i\sqcap\operatorname{Column}_j
\]

is only justified after the relevant order and meet operation have been formally defined.

### 5.2 Property-wise context resolution

Let the context vector be

\[
U=(\text{currency},\text{dimension},\text{scale},\text{precision}).
\]

The resolver should operate independently for each property. For property \(k\), let the candidate assertions be drawn from the applicable table, column, row, cell, and local evidence scopes. A field resolver can be written as

\[
U_k^*=\phi_k(A_k),
\]

where \(A_k\) is the ordered or otherwise adjudicated set of assertions relevant to property \(k\).

This prevents an override of one property from erasing unrelated context. For example, a row-specific scale of \(10^0\) should not silently erase a table-wide currency declaration of USD or a table-wide scale default that applies to other rows.

The design requires more than a `FirstDefined` rule. The specification must define:

1. which scopes are applicable to a cell;
2. the precedence or authority rules for each property;
3. how two applicable but conflicting assertions are handled;
4. how missing assertions differ from explicit values; and
5. when a conflict yields an unresolved result rather than an arbitrary winner.

An explicit scale exponent of zero is a valid assertion. It must be distinguishable from a missing scale assertion (`None`).

### 5.3 What is and is not proved

Coordinate-wise resolution is a sufficient design for property-level non-interference when its applicability and conflict rules are well-defined. It is not proved to be the only correct implementation. The research claim should be about the guarantees of the specified resolver, not universal uniqueness.

## 6. Typed values and the value-domain issue

The value model may include exact scalars, bounded values, ranges, missing values, and conflicts. However, listing tagged value variants does not by itself define a lattice.

To call a value domain a lattice, the formal specification must define a partial order and establish the existence of joins and meets for every pair (or for every pair in the stated domain).

One possible construction uses sets of possible meanings. Let \(\gamma(v)\) map a represented value to the set of concrete values it permits. An information order can be defined by

\[
v_1\sqsubseteq v_2
\quad\Longleftrightarrow\quad
\gamma(v_2)\subseteq\gamma(v_1),
\]

so that \(v_2\) is at least as informative as \(v_1\). A powerset construction can supply lattice operations, but the semantics of missing reasons, incompatible units, and conflicts still need explicit treatment.

A simpler initial design is a flat domain with:

- \(\bot\): unresolved or no information;
- concrete typed values, mutually incomparable when distinct; and
- \(\top_{\mathrm{conflict}}\): incompatible assertions.

Whichever construction is chosen, the project should not claim a bounded complete lattice until the order, bottom, top, joins, and meets are defined and proved.

## 7. Unit-scale error result

Suppose the source value is \(v\), expressed with a true scale exponent \(s\), so the corresponding quantity is

\[
Q=v\,10^s.
\]

If a downstream process instead assumes exponent \(s_0\), it computes

\[
\widehat Q=v\,10^{s_0}.
\]

For \(v\ne0\), the relative absolute error is

\[
\frac{|Q-\widehat Q|}{|Q|}
=\left|10^{s_0-s}-1\right|.
\]

For a true scale of \(s=6\) and an assumed scale of \(s_0=0\),

\[
\frac{|Q-\widehat Q|}{|Q|}
=|10^{-6}-1|
=0.999999,
\]

which is a relative error of **99.9999%**. The true quantity is one million times the incorrectly scaled estimate, assuming the same nonzero displayed value and no other transformation.

This result is conditional on the stated scale mismatch. It does not imply that every language model or retrieval system defaults to scale zero. A system may recover the scale from other context; the experiment must test whether it actually does so.

## 8. Evidence provenance and anchor requirements

### 8.1 Role-specific evidence

A provenance bundle can contain anchors for distinct semantic roles, such as:

\[
P=\langle
\alpha_V,
\alpha_M,
\alpha_T,
\alpha_U,
\alpha_E,
\{\alpha_{F_i}\}
\rangle,
\]

where the anchors may support the value, metric, temporal scope, unit, entity, and footnotes or qualifiers.

The role structure matters: evidence that locates a number is not automatically evidence that establishes its metric, unit, period, or entity.

### 8.2 Conditional anchor policy

A fixed requirement that every fact must possess every anchor is too rigid for heterogeneous source documents. Some facts may not have an explicit period, unit, or footnote. The compiler should define a fact-type-specific required-anchor policy.

For every required semantic role, the result should be one of:

- supported by a source anchor;
- supported by an explicitly permitted inference with recorded rule and inputs; or
- unresolved.

Missing evidence must not be silently fabricated. Optional evidence roles can remain absent when the fact type does not require them.

### 8.3 Hashes and authenticity

A cryptographic digest such as SHA-256 can establish that a byte sequence matches a previously recorded digest, assuming the digest is trusted. It does not, by itself, prove who authored or issued the document, whether the source is authoritative, or whether the content is true.

Authenticity requires an appropriate trust mechanism, such as a verified digital signature and a defined public-key trust policy. A signature field that is merely present, or a signature payload that is never cryptographically verified, does not provide that guarantee.

## 9. Forward replay and transformation verification

Let the raw source string be \(s_0\), and let the recorded deterministic transformation sequence be

\[
s_{i+1}=T_i(s_i),\qquad i=0,\ldots,n-1.
\]

A verifier should independently execute each allowlisted transformation and compare the resulting outputs with the recorded chain. It should not accept a Boolean assertion such as `replayed_successfully = True` as proof that replay occurred.

The verifier should check, at minimum:

1. the source bytes or source-text anchor used as input;
2. the transformation identity, version, configuration, and order;
3. the actual output of each transformation;
4. continuity between each output and the next input;
5. the final normalized typed value; and
6. the semantic evaluation, including unit and scope resolution, where applicable.

A useful decomposition separates:

- textual normalization;
- value parsing;
- unit and scope resolution; and
- arithmetic or derived-quantity evaluation.

A replayed display string need not be the same thing as the typed semantic value. The verifier should compare the appropriate normalized representation at each stage.

Deterministic reproducibility also requires frozen parser/model versions, configuration, dependency versions where relevant, deterministic ordering and identifiers, and a defined execution environment. The statement `Compile(doc, adapter) = Compile(doc, adapter)` is tautological unless the execution conditions and expected output are specified.

## 10. Conditional soundness of ECTC

The strongest defensible correctness claim is conditional soundness relative to declared assumptions and verified evidence.

A suitable form is:

> If the source evidence is correctly identified, the structural parser and semantic resolver satisfy their stated contracts, the required anchors are valid, the transformation chain is independently replayed, and all relevant verification rules pass, then the emitted fact is internally consistent with the checked source evidence and declared interpretation rules.

This is not the same as proving that the source document itself is true. A compiler cannot guarantee universal factual correctness merely because:

- row and column paths are nonempty and acyclic;
- decimal arithmetic is used;
- a unit field is non-null;
- a provenance anchor exists; or
- a hash digest is present.

Each of those checks supports only a narrower property. For example, decimal arithmetic can avoid binary floating-point input artifacts when values are parsed from decimal strings, but it does not prove that the parser chose the correct sign or scale. Fixed precision arithmetic can also round repeating divisions such as \(1/3\).

The specification should distinguish:

- **fact-level status:** whether a particular fact is verified, unresolved, or invalid;
- **snapshot-level status:** whether the compiled document/table snapshot satisfies its global integrity and policy gates; and
- **retrieval policy:** which fact-level statuses may be returned under the current application policy.

A whole-snapshot failure need not logically imply that every individual fact is false, but a security-first implementation may choose to block all retrieval from a failed snapshot. That policy should be explicit and tested.

## 11. Audit of the six proposed mathematical claims

The earlier theory notes contain six main theorem-style claims. Their present status is summarized below.

| Claim | Current mathematical status | Required correction |
|---|---|---|
| 1. Coordinate severance | Valid as a conditional geometric result for one contiguous chunk | State the token-count convention and anchor-span model; do not generalize to multi-chunk systems |
| 2. Non-invertible information loss | Core idea is valid; the earlier proof has type and information-theoretic gaps | Use Theorem 1 above; only use entropy or Fano bounds with a defined probability model |
| 3. Scale divergence | Valid for the stated scale mismatch | Use the general exponent formula; do not assume all downstream systems default to scale zero |
| 4. Orthogonal row/column scopes | Strong design motivation; formal algebra is incomplete | Define scope orders, property precedence, conflict handling, and missing-value semantics |
| 5. Random/sliding chunk probability | Not valid as previously stated | Remove the universal probability claim until the sampling model and chunk geometry are derived correctly |
| 6. ECTC soundness/completeness | Current proof is circular or overclaims source truth | Prove conditional internal-consistency guarantees relative to explicit parser, evidence, and verifier assumptions |

### 11.1 Corrected uniform-position formula (only under an explicit model)

If \(m\) anchor positions are independent and uniformly distributed on \([0,L]\), and \(0\leq B\leq L\), the probability that their range is at most \(B\) is

\[
P\left(\max_i p_i-\min_i p_i\leq B\right)
=m\left(\frac{B}{L}\right)^{m-1}
-(m-1)\left(\frac{B}{L}\right)^m.
\]

This is a result for the stated IID continuous-uniform model. Real table anchors are not generally independent or uniformly distributed. Aligned or sliding chunkers also require their own window-start and stride analysis. Therefore this formula must not be presented as a general probability of retrieval failure for real documents.

## 12. Graph and cycle handling

A canonical representation of a directed simple cycle can choose a distinguished rotation, such as the rotation beginning at the minimum node identifier. This removes rotational duplicates from a cycle representation. It does not, by itself, create a new cycle-enumeration algorithm.

The number of simple cycles in a directed graph can be exponential in the number of vertices. Therefore, enumerating all simple cycles cannot generally be claimed to run in \(O(V+E)\). An output-sensitive algorithm such as Johnson-style enumeration has a bound of the form

\[
O((V+E)(K+1)),
\]

where \(K\) is the number of elementary cycles output, under the corresponding algorithmic assumptions. The implementation and complexity claim must name the actual algorithm used.

## 13. Implementation implications from the audit

The mathematical guarantees above imply several concrete engineering requirements. These are not all proved by the mathematics alone; they are implementation obligations needed to make the claims operational.

1. **Independent transformation replay:** do not trust a stored success Boolean or declared output without executing the transformation chain.
2. **Derived-fact lineage:** derived facts must be verified from their inputs and transformation rules; they should not become verified merely because they were created.
3. **Three-state status preservation:** keep `PASS`, `FAIL`, and `UNRESOLVED` distinct through compilation, validation, serialization, and reporting.
4. **Retrieval gate:** define whether facts from failed or unresolved snapshots may be returned, and enforce that policy in the query path.
5. **Serialization round trip:** serialize the complete semantic object graph and test reconstruction, rather than serializing summaries and marking the result successful unconditionally.
6. **Chunk-size enforcement:** use a real tokenizer or a declared conservative token-count method; reject or split chunks that exceed the configured capacity. Certificate closure fields must be computed, not hardcoded.
7. **No silent generic unit defaults:** a generic table with no unit evidence must not silently inherit a domain-specific default such as USD millions.
8. **Parser uncertainty:** PDF/HTML/Markdown adapters must preserve uncertainty and source geometry where possible; extraction heuristics should not be presented as verified structure without evidence.
9. **Temporal semantics:** state which interval relations are implemented. Six relations are not the complete set of thirteen Allen interval relations.
10. **Cryptographic trust:** distinguish content-integrity hashes from issuer authentication and verify signatures against a declared trust policy.

## 14. A focused experimental programme

The mathematical results suggest a compact, falsifiable evaluation plan.

### 14.1 Core baselines

Compare at least:

- flat-text table serialization with ordinary chunking;
- table-aware serialization with repeated headers or metadata;
- multi-chunk retrieval with explicit joins; and
- ECTC/PCC-Tensor with CTIR, scope resolution, provenance, and verification.

The evaluation should avoid treating every baseline as equally weak. A strong table-aware or multi-hop baseline is necessary to show where the compiler layer adds value.

### 14.2 Controlled ambiguity tests

Construct pairs of source tables \(x_1,x_2\) with identical observations under a specified serializer but different answers to a target query:

\[
g_B(x_1)=g_B(x_2),\qquad q(x_1)\ne q(x_2).
\]

Then test whether the baseline fails as predicted, and whether metadata, joins, or CTIR remove the ambiguity. This directly operationalizes Theorem 1.

### 14.3 Coordinate ablations

Independently remove or corrupt:

- row ancestry;
- column ancestry;
- time scope;
- unit or scale;
- qualifiers and footnotes; and
- provenance roles.

Measure answer accuracy, unsupported-answer rate, unresolved rate, and evidence traceability. The study should report both successful recovery and deliberate abstention.

### 14.4 Verification fault injection

Inject forged transformation outputs, broken replay chains, incorrect scales, conflicting row/column assertions, missing required anchors, bad signatures, and invalid snapshot states. Measure whether the verifier detects each issue and whether the retrieval path obeys the status policy.

### 14.5 Metrics

Useful metrics include:

- answer accuracy on answerable queries;
- false-answer rate on ambiguous or unsupported queries;
- abstention precision and recall;
- fact-level verification precision and recall;
- provenance-role coverage;
- source-to-answer traceability;
- parser structural accuracy;
- chunk closure rate;
- multi-chunk join correctness; and
- latency and resource cost.

Do not report a single aggregate accuracy alone. A system that abstains on every difficult case can have a low false-answer rate while being useless; report coverage and accuracy together.

## 15. Recommended novelty statement

A cautious and defensible candidate contribution is:

> **Evidence-Closed Table Compilation (ECTC)** is a compiler-oriented framework for representing table facts as typed semantic coordinates and admitting them to verified retrieval only when their required structural context, property-specific interpretation, and role-specific source evidence satisfy explicit contracts. Its central motivation is query-relative semantic indistinguishability: a serialization that maps answer-distinct source states to the same observation cannot support a universally correct decoder from that observation alone.

The potential novelty is in the particular integration of:

- a canonical typed table-fact representation;
- explicit row/column scope and property-wise context resolution;
- role-specific provenance closure;
- replayable transformation lineage; and
- fact- and snapshot-level verification gates for retrieval.

This is a **candidate** novelty statement, not a completed proof of novelty. A literature review is still needed to establish how the integration differs from existing table-aware RAG, table graph, provenance, document compiler, and proof-carrying data systems.

Avoid claiming to have invented table graphs, hierarchical table interpretation, provenance, exact decimal arithmetic, interval logic, canonical intermediate representations, or proof-carrying values in the abstract.

## 16. Immediate formalization priorities

The next mathematical work should be performed in this order:

1. **Freeze the semantic schema.** Reconcile the nine-coordinate tuple with the smaller STES definition.
2. **Define scope algebra.** Specify row and column partial orders, applicable scopes, per-property precedence, and conflicts.
3. **Choose a value-domain order.** Either define a genuine lattice with proofs or use a simpler typed domain without calling it a lattice.
4. **State soundness assumptions.** Separate parser correctness assumptions, evidence validity, replay correctness, and source truth.
5. **Formalize status propagation.** Define fact-level and snapshot-level states, including how `UNRESOLVED` behaves.
6. **Specify reproducibility.** Freeze versions, configurations, deterministic identifiers, and ordering.
7. **Derive chunking probabilities only after choosing a realistic corpus model.** Otherwise keep the deterministic geometric severance result.
8. **Design controlled counterexample experiments.** Test answer-distinct states that become observationally identical under particular baselines.

## 17. Final mathematical position

The strongest discovery at this stage is not a universal theorem that flat-text RAG must fail. It is the precise information-theoretic observation that **when an observation collapses two source states that require different answers, no decoder using only that observation can be correct for both**.

The engineering opportunity is to prevent or repair that query-relevant collapse by preserving typed coordinates, resolving context without cross-property interference, linking each semantic role to evidence, and verifying transformations before facts are admitted to retrieval.

That is a meaningful foundation for ECTC. The remaining work is to formalize the scope and value domains, state conditional guarantees honestly, and validate the benefits against strong baselines and adversarial counterexamples.

---

## Source documents reviewed

This note synthesizes and audits the mathematical ideas in the project materials:

- `EVIDENCE_CLOSED_COMPILATION_MATHEMATICAL_THEORY.md`
- `EVIDENCE_CLOSED_TABLE_COMPILATION_THESIS.md`
- `MATHEMATICAL_PROOFS_TABLE_COORDINATE_DESTRUCTION.md`
- `PCC_N_DIMENSIONAL_TENSOR_ARCHITECTURE(2).md`
- `PCC_TENSOR_3.0_FORMAL_SPECIFICATION(1).md`
- `worst_case_failures(1).md`

The corrections and caveats in this note are part of the mathematical audit; they should be retained when these results are incorporated into a thesis or paper.
