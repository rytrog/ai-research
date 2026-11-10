# 📓 D-COMP RESEARCH LOG & EXPERIMENTAL LEDGER

## Standard Operating Procedure for Every Experiment:
1. **Hypothesis Formulation:** State the exact physical/structural assumption being tested.
2. **Baseline Configuration:** Define the control group (e.g., Naive Recursive 512, LlamaIndex TableParser).
3. **Challenger Configuration:** Define the exact D-COMP deterministic mechanism under test.
4. **Adversarial Input:** Run on real SEC 10-K filings with known pathological structures.
5. **Quantitative Metrics:**
   - Evidence Retrieval Recall@1, Recall@3, Recall@5
   - Exact Value Precision (Correct number + correct date + correct unit)
   - Ingestion Latency (ms) & Query Latency (ms)
   - Max Token Count vs. 512-budget ceiling

---

## 📅 Log Entry: Initialization (Day 1)
- **Status:** Research laboratory initialized.
- **Environment:** `st_test` environment verified (`torch 2.6.0+cu124` CUDA FP16 + `Qwen3-Embedding-0.6B`).
- **Focus:** Building the adversarial table stress-test harness and cataloging exact failure points in real SEC 10-K tables.
- **Immediate Task:** Construct `analysis/worst_case_failures.md` outlining the exact mathematical and structural failure cases of existing table solutions.

---

## 📅 Log Entry: SOTA Literature Audit & The PCC-Tensor Breakthrough (Day 2)
> ⚠️ **HISTORICAL AUDIT NOTE (SUPERSEDED):** Preliminary claims recorded on Day 2 regarding "universal 19-30% RAG ceiling", "EnSI-RAG 468.5s per query runtime", "512 hard token budget for Qwen3", and "0.42ms end-to-end PDF processing" have been formally superseded by the rigorous literature decomposition and empirical protocols established in Day 3.
- **Status:** Initial theoretical exploration completed.
- **Hypothesis:** Multi-dimensional table coordinate loss causes the steep accuracy drop in standard RAG on complex financial tables.
- **Artifact:** Initial working blueprint recorded in `my_research/analysis/PCC_N_DIMENSIONAL_TENSOR_ARCHITECTURE.md`.

---

## 📅 Log Entry: Rigorous Peer-Review Audit & PCC-Tensor 3.0 Formal Specification (Day 3)
- **Status:** Completed comprehensive mathematical and scientific overhaul. Frozen PCC-Tensor 2.0 and authored the canonical **PCC-Tensor 3.0 Research Specification**.
- **Key Corrections:**
  1. *Scientific Baseline Clarifications:* FinanceBench sample size (150 questions), EnSI-RAG latency breakdown (468s offline vs 19s online), and Qwen3 32K context budget decoupling.
  2. *Sparse Typed Evidence Space (STES):* Replaced rigid 5D Cartesian tensor with extensible relation $\mathcal{F} \subseteq \mathcal{E} \times \mathcal{M} \times \mathcal{V} \times \mathcal{Q} \times \mathcal{P}_{\text{bundle}}$.
  3. *Partial-Order Scope Resolution (SCRA):* Replaced broken linear scope hierarchy with orthogonal column/row poset resolution and conflict detection.
  4. *Interval Temporal Algebra:* Replaced false disjointness assumption with formal interval relation operators (DurationPeriod, InstantPeriod, EQUALS, CONTAINS, OVERLAPS).
  5. *Tagged Semantic Value Lattice:* Replaced overloaded status enum with typed tagged union (`ExactNumeric`, `BoundedNumeric`, `NumericRange`, `MissingValue`), exact `Decimal` context, and Document Convention Profiles.
  6. *Decoupled Structural Graph ($G_T$):* Separated acyclic structural tree $G_{\text{structure}}$ from cyclic reference graph $G_{\text{references}}$ and continuation path $G_{\text{continuation}}$.
  7. *Evidence Closure Certificates (ECC):* Forward-replay verification replacing invalid reversible transformation assumption; separated $ECC_{\text{fact}}$ from $ECC_{\text{chunk}}$ with Ed25519 signature payload.
  8. *Multi-Signal Continuation Stitching:* Added tri-state period matching (MATCH, CONFLICT, UNKNOWN) and ordered header-path similarity.
- **Artifact Persisted:** `my_research/analysis/PCC_TENSOR_3.0_FORMAL_SPECIFICATION.md` (Version 3.1.0-REVISED, Frozen Contract).
- **Next Step:** Implement Phase 1: Canonical Table IR data structures and formal contracts in `my_research/src/model/` with 100% test coverage.

---

## 📅 Log Entry: CTIR 3.1 Core Foundation Implemented & Verified (Day 4)
- **Status:** Phase 1 complete. Core Canonical Table IR (CTIR 3.1) data structures, serialization engine, and formal verifier fully implemented and validated.
- **Key Modules Implemented:**
  1. *L0 Source & Coordinate Space:* `SourceDocument` (SHA-256 integrity), `CoordinateSpace` (`PDF_POINT`, `HTML_DOM`, etc.), `BoundingBox` (coordinate ordering & area sanity), `SourceRef`.
  2. *L1 Geometry:* `GridSpan` with formal slot non-overlap predicate `spans_overlap()`.
  3. *L2 Semantic Values & Context:* Tagged union `TypedSemanticValue` (`ExactNumeric`, `BoundedNumeric`, `NumericRange`, `MissingValue`), `DECIMAL_CONTEXT` (28 precision, Banker's rounding), `DocumentConventionProfile`, `DurationPeriod`, `InstantPeriod`, interval relation operator `evaluate_temporal_relation()`, `UnitAssertion` (scale $10^s, s \in \mathbb{Z}$), `Quantity`, and `ScopeConflictResolver` (partial-order poset conflict detection).
  4. *L3 Evidence & Graphs:* `EvidenceAnchor`, `MultiSourceProvenanceBundle`, `TransformationRecord`, `CellNode`, `LogicalRow`, `LogicalColumn`, `HeaderNode`, `TableFragment`, `LogicalTable`, `StructuralGraph` (strict acyclic DAG check), and `ReferenceGraph` (cycle-detecting footnote graph).
  5. *L4 CTIR Snapshot & Verifier:* `SourceFact`, `DerivedFact` (execution lineage), `ValidationReport`, `CTIRSnapshot`, canonical JSON serialization (`storage/serialize.py`), and `CTIRValidator` (`verifier/validate.py`) enforcing contracts C1 to C20.
- **Verification:** All 30 tests passed (`pytest test_canonical_ir.py test_ctir_foundation.py` -> 30/30 in 0.21s).
- **Next Step:** Phase 2 Implementation — Input Adapters & Pre-Processors (Markdown Lexer, HTML DOM Extractor, PDF Geometry Adapter).

---

## 📅 Log Entry: Adapters, Semantic Compiler & Adversarial Benchmark Verification (Day 5)
- **Status:** Phase 2 (Input Adapters), Phase 3 (Semantic Compiler & Scope Poset), and Phase 4 (End-to-End Adversarial Benchmark) completed and empirically verified.
- **Key Modules Implemented:**
  1. *Format Adapters (`src/adapter/`):*
     - `MarkdownTableLexer`: Grammar-aware parser handling escaped pipes (`\|`), LaTeX math (`$|x| + |y|$`), inline code backticks, column alignment, and footnotes into `TableFragment`.
     - `HtmlDomAdapter`: 2D occupancy matrix tracker resolving arbitrary `rowspan` and `colspan` combinations, CSS hierarchical indentation, and footnote tags.
     - `PdfGeometryAdapter`: PyMuPDF (`fitz`) geometry extractor capturing point-space bounding boxes $[x_0, y_0, x_1, y_1]$ in typographic points (`PDF_POINT`).
     - `AsciiTableScheduleAdapter`: Fixed-width monospaced parser specialized for SEC Form 10-K/10-Q text schedules, discovering column bounds, multi-level super-headers, and explanatory footnote blocks.
  2. *Semantic Compiler (`src/compiler/`):*
     - `RowHierarchyBuilder`: Indentation stack ($\Sigma_{\text{stub}}$) constructing strict acyclic DAGs with complete ancestor paths (Section -> Detail -> Subtotal -> Total).
     - `ValueNormalizer`: Deterministic morphosyntactic parser converting parenthetical negatives (`(158.20)`), currency symbols, percentages, and bounded ranges into `TypedSemanticValue` with verified forward-replay transformation records.
     - `ScopeResolver`: Partial-order poset engine (SCRA) resolving temporal intervals (`DurationPeriod` vs `InstantPeriod`), fiscal labels, and unit assertion overrides (preserving non-monetary physical units without false currency pollution).
     - `TableCompiler`: Assembles complete Layer L4 `CTIRSnapshot` with bound facts, multi-source provenance bundles (MSEP), and runs the 9-stage `CTIRValidator`.
  3. *Symbolic Query Engine (`src/query/`):*
     - `CTIRQueryEngine`: Coordinate-aware retrieval over CTIR facts with interval temporal matching, metric disambiguation, and linked footnote provenance.
- **Verification & Empirical Benchmark:**
  - **Full Test Suite:** 42/42 tests passing (`test_adapters.py`, `test_canonical_ir.py`, `test_compiler.py`, `test_ctir_foundation.py`) in 0.49s.
  - **Adversarial Benchmark (`02_adversarial_qa_benchmark.py`):**
    - **Exact Value Accuracy:** **100.0% (8/8)** on the pathological SEC 10-Q red-team schedule.
    - **Footnote Provenance Linkage:** **100.0% (8/8)**.
    - **Ingestion & Compilation Latency:** **38.41 ms** (212 facts compiled).
    - **Average Query Latency:** **1.012 ms** per query.
    - **Validation Gate:** **PASS** (Contracts C1 through C20 strictly enforced).

---

## 📅 Log Entry: Relation-Preserving Table Chunker & SOTA Baselines Implemented (Day 6)
- **Status:** Relation-Preserving Semantic Table Chunker and SOTA baseline chunkers implemented and unit-tested. Full test suite at 45/45 passing.
- **Key Modules Implemented:**
  1. *Relation-Preserving Chunker (`src/chunker/relation_preserving_chunker.py`):*
     - Invariant 1 (Complete Coordinate Closure): Every chunk carries Table Title, Entity Scope, Global Unit Banner, Full Row Ancestor Hierarchy, and Multi-Tier Column Header Paths.
     - Invariant 2 (Bifurcated Dual View): Emits synchronized Dense Linearized Propositions (`dense_text`) for vector models and a self-contained Micro-Grid (`markdown_microgrid`) with restored headers.
     - Invariant 3 (Footnote Colocation): Footnotes cited by cells within a chunk are automatically colocated inside that chunk, eliminating cross-chunk footnote severance.
     - Invariant 4 (SAKI-RAG Dynamic Token Budgeting): Dynamic row knapsack packing ensuring chunk token count stays strictly within the $\le 512$ token ceiling.
     - Invariant 5 (Chunk Certificate ECC): Every chunk carries an Evidence Closure Certificate with SHA-256 content digest and verification booleans.
  2. *Baselines (`src/baselines/`):*
     - `NaiveFixedWindowChunker` (`src/baselines/naive_chunker.py`): 512-character sliding window simulating LangChain/LlamaIndex chunking.
     - `MarkdownRowGroupChunker` (`src/baselines/markdown_chunker.py`): Row-group chunker simulating flat Markdown table slicing.
- **Verification:** 45/45 tests passing in 0.90s (`pytest my_research/tests` -> 100% pass rate).


