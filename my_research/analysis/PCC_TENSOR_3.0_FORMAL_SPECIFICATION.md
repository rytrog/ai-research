# 🏛️ PCC-TENSOR 3.1: FORMAL CANONICAL SPECIFICATION & ENGINEERING CONTRACT
## Proof-Carrying Structural Compilation for Reliable Retrieval-Augmented Generation over Complex Enterprise Tables
**Document Version:** 3.1.0-REVISED (Mathematical & Engineering Contract Frozen)  
**Location:** `my_research/analysis/PCC_TENSOR_3.0_FORMAL_SPECIFICATION.md`  
**Authors / Lab:** D-COMP Research Lab (AI Research Group)  
**Target Venues:** ACL 2027 / NeurIPS 2026 (Datasets & Benchmarks) / EMNLP 2026  
**Status:** IMPLEMENTATION-FROZEN CANONICAL CONTRACT  

---

## 1. SCIENTIFIC AUDIT & EMPIRICAL CORRECTIONS (SUPERSEDED CLAIMS LOG)

To ensure unassailable peer-review integrity, this section establishes the strict empirical boundary between verified literature baselines, theoretical hypotheses, and empirical measurements:

### 1.1 Corrected Baseline Record
| System / Metric | Previous Informal Phrasing | Rigorous Research-Grade Formulation |
| :--- | :--- | :--- |
| **FinanceBench Baseline** | *"19%–30% universal RAG ceiling"* | **Empirical Sample Vulnerability:** FinanceBench (Patronus AI, 2023) evaluated a 150-question manually verified gold sample using GPT-4-Turbo with vector retrieval; the model failed or refused on 81% of questions (~19% accuracy on that subset). This is not a universal theoretical ceiling. |
| **EnSI-RAG Latency** | *"Takes 468.5s per query"* | **Preprocessing vs. Inference Separation:** EnSI-RAG (Meng et al., UIUC, Aug 2026) Table 3 reports an offline LLM extraction cost of **468.51s per query** after amortizing across large corpora. At online runtime, retrieval takes **19.01s** and generation takes **6.73s**. |
| **EnSI-RAG Accuracy** | *"Obtains 100% accuracy"* | **Domain-Specific Ablation:** The 100.00% figure is specifically a row-level vs. table-level passage ablation on the English Financial subset of Loong (Table 4), not a general benchmark score across all Loong/Oolong multi-hop tasks. |
| **Embedding Budget** | *"Qwen3 has a 512 hard token limit"* | **Experimental Invariant:** Qwen3-Embedding model card specifies a 32K context window. The $\le 512$ token ceiling is an **experimental design parameter** to optimize signal-to-noise ratio, prevent centroid dilution (SAKI-RAG), and ensure lightweight inference. |
| **PDF Extraction Reality** | *"Pass 1 character offset slicing"* | **Geometric Bounding Box Mandate:** Digital PDFs consist of positioned glyph streams, font dictionaries, and drawing commands without intrinsic monospace alignment. Native bounding boxes $[x_0, y_0, x_1, y_1]$ in typographic points are mandatory. |

---

## 2. SPARSE TYPED EVIDENCE SPACE (STES) & MULTI-SOURCE PROVENANCE

### 2.1 Rejection of Dense Cartesian Tensors
Real enterprise tables violate dense $N$-dimensional Cartesian models ($\mathcal{E} \times \mathcal{M} \times \mathcal{H} \dots$) because reporting attributes are sparse, heterogeneous, and interdependent.

### 2.2 Formal Definition of STES
We model the knowledge substrate as a **Sparse Typed Evidence Relation**:

$$\mathcal{F} \subseteq \mathcal{E} \times \mathcal{M} \times \mathcal{V} \times \mathcal{Q} \times \mathcal{P}_{\text{bundle}}$$

Where:
* **$\mathcal{E}$ (Entity Space):** Canonical or unresolved entity anchor:
  $$e = \langle \text{entity\_id}, \text{legal\_name}, \text{cik\_or_lei}, \text{segment\_path}, \text{resolution\_confidence} \rangle$$
* **$\mathcal{M}$ (Metric Space):** Reporting metric concept:
  $$m = \langle \text{metric\_id}, \text{canonical\_concept}, \text{balance\_type} \in \{\text{DEBIT}, \text{CREDIT}, \text{NEUTRAL}, \text{UNKNOWN}\} \rangle$$
* **$\mathcal{V}$ (Tagged Semantic Value Lattice):** An instance of the disjoint tagged union (see Section 4).
* **$\mathcal{Q}$ (Extensible Qualifier Set):** Typed qualifiers $\{ k \mapsto v_k \}$ where $k \in \{\text{scenario}, \text{consolidation}, \text{standard}, \text{restatement}, \text{geography}, \text{basis}\}$.
* **$\mathcal{P}_{\text{bundle}}$ (Multi-Source Evidence Provenance — MSEP):**
  A fact cannot be anchored to a single byte span. Its truth value depends on a **Provenance Bundle**:
  $$\mathcal{P}_{\text{bundle}} = \{ p_{\text{value}}, p_{\text{metric\_stub}}, p_{\text{period\_header}}, p_{\text{unit\_banner}}, p_{\text{entity\_preamble}}, p_{\text{footnotes}} \}$$
  Each individual anchor $p_x$ carries:
  $$p_x = \langle \text{doc\_sha256}, \text{page\_id}, \text{bbox} \in \mathbb{R}^4, \text{raw\_text}, \text{adapter\_id}, \text{evidence\_role} \rangle$$

---

## 3. CANONICAL STRUCTURAL GRAPH $G_T$ (DECOUPLED LAYERS)

To guarantee that hierarchical tree containment remains strictly acyclic while accommodating cyclic cross-references, $G_T$ is decomposed into three distinct subgraphs:

$$G_T = G_{\text{structure}} \cup G_{\text{references}} \cup G_{\text{continuation}}$$

```
┌────────────────────────────────────────────────────────────────────────┐
│                        CANONICAL TABLE IR (G_T)                        │
├────────────────────────────────────────────────────────────────────────┤
│ 1. G_structure (Strict Directed Acyclic Graph - DAG):                  │
│    - Root TableNode -> HeaderTree (PARENT_HEADER edges)                │
│    - Root TableNode -> RowHierarchyTree (PARENT_ROW edges)             │
│    - Explicit CellNode(row_id, col_id, row_span, col_span, bbox)      │
├────────────────────────────────────────────────────────────────────────┤
│ 2. G_references (Directed Multi-Graph; Cycles Permitted):              │
│    - FOOTNOTE_REF edges: Cell -> Note, Note -> Note, Header -> Note    │
│    - FORMULA_REF edges: Cell_gross = Cell_rev - Cell_cogs              │
├────────────────────────────────────────────────────────────────────────┤
│ 3. G_continuation (Ordered Fragment Path):                             │
│    - TableFragment_1 -> TableFragment_2 (CONTINUATION_OF edges)        │
└────────────────────────────────────────────────────────────────────────┘
```

### 3.1 Explicit Merged-Cell Contract
A merged cell covering $r \in [r_0, r_0 + \Delta_r)$ and $c \in [c_0, c_0 + \Delta_c)$ is represented as a single `CellNode` with explicit `row_span = \Delta_r` and `col_span = \Delta_c`. It does **not** automatically clone into $\Delta_r \times \Delta_c$ semantic facts; logical propagation is governed by structural semantics.

---

## 4. TYPED SEMANTIC VALUE LATTICE & EXACT ARITHMETIC

### 4.1 Tagged Union Specification
To eliminate conflation between censored numbers, footnote asterisks, and nil dashes, cell values belong to a formal disjoint tagged union:

```python
from dataclasses import dataclass
from decimal import Decimal, Context, ROUND_HALF_EVEN
from enum import Enum
from typing import Optional, Tuple, Union

# Global Accounting Decimal Context (28 decimal places, Banker's Rounding)
DECIMAL_CONTEXT = Context(prec=28, rounding=ROUND_HALF_EVEN)

class BoundOperator(str, Enum):
    LT = "LT"   # <
    LE = "LE"   # <=
    GT = "GT"   # >
    GE = "GE"   # >=

class MissingReason(str, Enum):
    NIL_DASH = "NIL_DASH"              # "—" or "-" symbol (document-convention dependent)
    REPORTED_ZERO = "REPORTED_ZERO"    # Explicit "0", "0.00"
    NOT_APPLICABLE = "NOT_APPLICABLE"  # "N/A"
    NOT_MEANINGFUL = "NOT_MEANINGFUL"  # "NM" (ratio base zero/negative)
    IMMATERIAL = "IMMATERIAL"          # Confirmed immaterial disclosure
    SUPPRESSED = "SUPPRESSED"          # Confidential or redacted
    UNKNOWN = "UNKNOWN"                # Unresolved non-numeric text

@dataclass(frozen=True)
class ExactNumeric:
    raw_text: str
    value: Decimal

@dataclass(frozen=True)
class BoundedNumeric:
    raw_text: str
    bound: Decimal
    operator: BoundOperator

@dataclass(frozen=True)
class NumericRange:
    raw_text: str
    lower_bound: Decimal
    upper_bound: Decimal
    lower_inclusive: bool = True
    upper_inclusive: bool = True

@dataclass(frozen=True)
class MissingValue:
    raw_text: str
    reason: MissingReason
    convention_note: Optional[str] = None

# Canonical Tagged Value
TypedSemanticValue = Union[ExactNumeric, BoundedNumeric, NumericRange, MissingValue]
```

### 4.2 Document-Convention Profile for Nil Symbols
A dash `—` is **never blindly assumed to be zero**. It is evaluated through a strict two-stage predicate:
$$\operatorname{ResolveNil}(\text{cell}, \text{Profile}) = \begin{cases}
\text{ExactNumeric}(\text{raw}="—", \text{value}=0.0) & \text{if } \text{Profile}.\text{dash\_equals\_zero} \equiv \text{True} \\
\text{MissingValue}(\text{raw}="—", \text{reason}=\text{NIL\_DASH}) & \text{otherwise (Status: UNRESOLVED)}
\end{cases}$$

---

## 5. SCOPE-AWARE UNIT AND CONTEXT ALGEBRA (SUCA / SCRA)

### 5.1 Rejection of Linear Order: Partial-Order Scope Lattice
Columns and Rows are **orthogonal scopes** that intersect at a cell. We model scope containment as a **Partially Ordered Set (Poset)**:

$$\begin{array}{ccc}
 & \text{Document} & \\
 & \downarrow & \\
 & \text{Table} & \\
 & \downarrow & \\
 & \text{Section} & \\
 \swarrow & & \searrow \\
\text{Column Scope} & & \text{Row Scope} \\
 \searrow & & \swarrow \\
 & \text{Cell Intersection} & 
\end{array}$$

### 5.2 Property-Specific Resolution Rules (Scope Conflict Resolution Algebra - SCRA)
Different properties resolve through distinct precedence paths:
1. **Physical Dimension & Currency ($\mathcal{U}_{\text{phys}}, \mathcal{U}_{\text{curr}}$):**
   * If Row specifies unit (e.g. `Common Shares`) and Column specifies period, both apply orthogonally.
   * If both Row and Column specify contradictory units (e.g. Row says `USD`, Column says `EUR`), the conflict detector emits `AMBIGUOUS_UNIT_CONFLICT` and halts normalization.
2. **Scale Multiplier ($\mathcal{U}_{\text{scale}} = 10^s, s \in \mathbb{Z}$):**
   * Scale factor is an arbitrary integer exponent $s \in \mathbb{Z}$ (supporting $s = -2$ for cents in iXBRL, $s = 0$ for per-share, $s = 6$ for millions).
   * **Precedence Lattice:** $\text{Cell} \succ \text{Row Override} \succ \text{Column Override} \succ \text{Table Banner}$.

```python
@dataclass(frozen=True)
class UnitAssertion:
    currency: Optional[str] = None          # ISO 4217 (USD, EUR)
    physical_unit: Optional[str] = None     # UCUM code (shares, 1/cm2)
    scale_exponent: int = 0                 # s in 10^s
    xbrl_decimals: Optional[int] = None     # Reported accuracy
    source_scope: str = "TABLE"             # CELL | ROW | COLUMN | TABLE
    source_anchor: Optional[str] = None
```

---

## 6. FORMAL TEMPORAL ALGEBRA: INTERVAL SEMANTICS

### 6.1 Rejection of False Disjointness
Periods sharing an end date are **not** disjoint ($I_1 \cap I_2 \neq \emptyset$). They are distinct intervals with subset relationships.

### 6.2 Typed Interval Representations & Operators
```python
import datetime

@dataclass(frozen=True)
class DurationPeriod:
    start_date: datetime.date
    end_date: datetime.date
    calendar_id: str = "GREGORIAN"
    fiscal_year: Optional[int] = None
    fiscal_quarter: Optional[int] = None
    fiscal_label: Optional[str] = None

@dataclass(frozen=True)
class InstantPeriod:
    as_of_date: datetime.date
    calendar_id: str = "GREGORIAN"

class TemporalRelation(str, Enum):
    EQUALS = "EQUALS"
    CONTAINS = "CONTAINS"
    CONTAINED_BY = "CONTAINED_BY"
    OVERLAPS = "OVERLAPS"
    BEFORE = "BEFORE"
    AFTER = "AFTER"

def evaluate_temporal_relation(p1: DurationPeriod, p2: DurationPeriod) -> TemporalRelation:
    if p1.start_date == p2.start_date and p1.end_date == p2.end_date:
        return TemporalRelation.EQUALS
    if p1.start_date <= p2.start_date and p1.end_date >= p2.end_date:
        return TemporalRelation.CONTAINS
    if p1.start_date >= p2.start_date and p1.end_date <= p2.end_date:
        return TemporalRelation.CONTAINED_BY
    if p1.end_date < p2.start_date:
        return TemporalRelation.BEFORE
    if p1.start_date > p2.end_date:
        return TemporalRelation.AFTER
    return TemporalRelation.OVERLAPS
```

---

## 7. EVIDENCE CLOSURE CERTIFICATES (ECC) & FORWARD-REPLAY VERIFIER

### 7.1 Reversible Transformation Replaced by Forward-Replay
Because string-to-number normalizations are non-injective (e.g. `$(1,000.00)` and `(1000)` both map to `Decimal("-1000.00")`), the verifier does **not** attempt backward string generation.

Instead, the verifier executes **Forward Replay**:
$$v_{\text{replayed}} = T_k(\dots T_2(T_1(v_{\text{raw}})))$$
Verification holds if and only if:
1. $v_{\text{replayed}} \equiv v_{\text{stored}}$.
2. $\text{SHA256}(v_{\text{raw}}) \equiv p_{\text{val}}.\text{raw\_text\_hash}$.

### 7.2 Separation of Fact Certificate ($ECC_{\text{fact}}$) vs. Chunk Certificate ($ECC_{\text{chunk}}$)
* **$ECC_{\text{fact}}$ (Semantic Evidence Certificate):** Verifies source coordinate binding, header closure, unit proof, footnote binding, and forward-replay normalization.
* **$ECC_{\text{chunk}}$ (Retrievable Context Certificate):** Verifies serializations, context duplication limits, and hard token budget $\le 512$ via native Rust BPE.

### 7.3 Cryptographic Signature Schema
```json
{
  "ecc_fact_id": "ECC_FACT_CHRONOS_2026_Q3_OPERATING_LOSS",
  "certificate_version": "3.1.0",
  "provenance_bundle": {
    "doc_sha256": "4a7d1ed414474e4033ac29ccb8653d9b",
    "value_anchor": { "page": 1, "bbox": [145.2, 580.4, 210.8, 592.1], "raw": "(158.20)" },
    "metric_anchor": { "page": 1, "bbox": [32.0, 580.4, 140.0, 592.1], "raw": "OPERATING INCOME / (LOSS) (EBIT)" },
    "period_anchor": { "page": 1, "bbox": [145.2, 85.0, 210.8, 98.0], "raw": "Three Months Ended September 30, 2026" },
    "unit_anchor": { "page": 1, "bbox": [32.0, 45.0, 400.0, 56.0], "raw": "All monetary amounts in millions of U.S. Dollars ($ USD Millions)" }
  },
  "canonical_fact": {
    "entity": "Chronos Technologies Group Inc.",
    "metric": "OperatingIncomeLoss",
    "temporal": { "type": "duration", "start": "2026-07-01", "end": "2026-09-30" },
    "typed_value": { "status": "numeric", "decimal": "-158.20", "unit": "USD", "scale": 6 }
  },
  "signature": {
    "algorithm": "Ed25519",
    "key_id": "lab-root-key-01",
    "payload_digest": "sha256:7b1e84f67c...",
    "signature_bytes": "3a8c1f..."
  }
}
```

---

## 8. CALIBRATED CONTINUATION STITCHER WITH TRI-STATE MATCHING

### 8.1 Tri-State Period Compatibility
When comparing Table $T_A$ with potential continuation fragment $T_B$:
$$\operatorname{PeriodMatch}(T_A, T_B) = \begin{cases}
\text{MATCH} & \text{Explicit period headers align} \\
\text{UNKNOWN} & \text{Fragment } T_B \text{ omits period headers (inheritable)} \\
\text{CONFLICT} & \text{Contradictory period headers detected (e.g. 2025 vs 2026)}
\end{cases}$$

**Stitching Rule:**
$$\text{If } \operatorname{PeriodMatch}(T_A, T_B) \equiv \text{CONFLICT} \implies \text{ABORT MERGE (Score } S_{\text{stitch}} = 0.0\text{)}$$

### 8.2 Ordered Header-Path Comparison
Instead of unordered Jaccard on string sets, column alignment compares **Ordered Header Paths**:
$$s_{\text{schema}} = \frac{1}{\max(C_A, C_B)} \sum_{j=1}^{\min(C_A, C_B)} \operatorname{PathSimilarity}(\text{Path}_A(j), \text{Path}_B(j))$$

---

## 9. SYNCHRONIZED TRI-INDEX RETRIEVAL ENGINE

### 9.1 Multi-Dimensional Symbolic Key
To prevent collisions between GAAP and Non-GAAP or Consolidated vs. Parent disclosures, the symbolic index key is:

$$K_f = \langle \text{entity\_id}, \text{metric\_id}, \text{period\_code}, \text{scenario}, \text{basis}, \text{consolidation}, \text{version} \rangle \longrightarrow \{\text{FactIDs}\}$$

### 9.2 Atomic Ingestion Snapshot
All three indexes are published atomically under a unified **Snapshot Manifest**:
$$\text{Snapshot} = \langle \text{doc\_version}, \text{ir\_version}, \text{fact\_store\_ver}, \text{dense\_index\_ver}, \text{symbolic\_index\_ver}, \text{struct\_index\_ver} \rangle$$
Readers query only validated, complete snapshots; partial ingestion states are never exposed.

---

## 10. REVISED BENCHMARK METRICS: ECR & ECP

We replace informal precision/recall definitions with **Slot-Weighted Metrics**:

### 10.1 Weighted Slot Definitions
Let $\mathcal{S}$ be the set of evidential slots $\{ \text{value}, \text{metric}, \text{period}, \text{unit}, \text{footnotes} \}$.
* $w_s$: Importance weight of slot $s$ ($\sum_{s \in \mathcal{S}} w_s = 1.0$).
* $\text{TP}_w$: Sum of weights for slots where retrieved evidence matches gold truth on value, coordinates, and role.
* $\text{FN}_w$: Sum of weights for missing required gold slots.
* $\text{FP}_u$: Penalty for incorrect or contradictory evidence retrieved.

$$\operatorname{ECR} = \frac{\text{TP}_w}{\text{TP}_w + \text{FN}_w}$$

$$\operatorname{ECP} = \frac{\text{TP}_w}{\text{TP}_w + \text{FP}_u}$$

*Note on GriTS:* **GriTS** (Grid Table Similarity: GriTS-Top, GriTS-Loc, GriTS-Con) is cited and adopted as the established baseline structural metric per Smock, Pesala, and Abraham (Microsoft Research, 2022).

---

## 11. METAMORPHIC STRUCTURAL INVARIANCE CONTRACT

Let $D$ be a valid document and $\tau \in \mathcal{T}_{\text{metamorphic}}$ be a semantics-preserving layout transformation (e.g. altering column margins, font size, whitespace padding, or border styles).

The compiler satisfies **Metamorphic Semantic Invariance**:

$$\pi_{\text{sem}}(\mathcal{C}(\tau(D))) \equiv \pi_{\text{sem}}(\mathcal{C}(D))$$

Where $\pi_{\text{sem}}$ projects extracted evidence to its canonical semantic facts, while source bounding boxes $\mathcal{P}_{\text{bbox}}$ naturally update to the new geometry.

---

## 12. IMMUTABLE ARCHITECTURAL CONTRACT FREEZE

By authorization of this document, **PCC-Tensor 3.1 is formally frozen as the implementation contract**:
1. All data structures in `my_research/src/model/` must strictly comply with Section 2, 4, 5, 6, and 7.
2. Binary floating point arithmetic is forbidden in core modules.
3. Linear scope resolution is forbidden; partial-order posets must be implemented.
4. Python reference implementation must be established and benchmarked against the 30-pathology suite before any Rust optimization.
