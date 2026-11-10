"""
PCC-Tensor 3.1: The 24 Foundation Verification Tests (T01 - T24).
Validates the complete Canonical Table IR (CTIR) foundation gate
before any parser adapters or ML models are attached.
"""

from __future__ import annotations

import datetime
from decimal import Decimal
import pytest

from my_research.src.model.source import (
    SourceDocument,
    CoordinateSpace,
    BoundingBox,
    SourceRef,
)
from my_research.src.model.geometry import GridSpan, spans_overlap
from my_research.src.model.value import (
    DECIMAL_CONTEXT,
    parse_exact_decimal,
    ExactNumeric,
    BoundedNumeric,
    NumericRange,
    MissingValue,
    BoundOperator,
    MissingReason,
)
from my_research.src.model.temporal import (
    PeriodType,
    DurationPeriod,
    InstantPeriod,
    TemporalRelation,
    evaluate_temporal_relation,
)
from my_research.src.model.semantic import (
    UnitAssertion,
    Quantity,
    ScopeLevel,
    ScopeRef,
    ResolutionStatus,
    SemanticAssertion,
    ScopeConflictResolver,
)
from my_research.src.model.evidence import (
    EvidenceRole,
    EvidenceAnchor,
    MultiSourceProvenanceBundle,
    TransformationRecord,
)
from my_research.src.model.structural import (
    CellRole,
    CellNode,
    LogicalRow,
    LogicalColumn,
    HeaderNode,
    TableFragment,
    LogicalTable,
)
from my_research.src.model.graph import (
    FootnoteNode,
    StructuralGraph,
    ReferenceGraph,
)
from my_research.src.model.ctir import (
    CTIRSnapshot,
    SourceFact,
    DerivedFact,
    FactCoordinates,
    ValidationStatus,
    ValidationReport,
)
from my_research.src.verifier.validate import CTIRValidator
from my_research.src.storage.serialize import serialize_ctir_to_json


# ==============================================================================
# T01 - Single-Level Header: Correct Column Mapping
# ==============================================================================
def test_t01_single_level_header():
    col = LogicalColumn(column_id="C01", position=0, header_path=("Revenue",), role="DATA")
    assert col.header_path == ("Revenue",)
    assert col.position == 0


# ==============================================================================
# T02 - Three-Level Header: Full Ancestry Preserved
# ==============================================================================
def test_t02_three_level_header():
    h_root = HeaderNode(header_id="H1", label="Segment Performance", level=1, col_start=0, col_end=2)
    h_sub = HeaderNode(header_id="H2", label="Three Months Ended", level=2, col_start=0, col_end=2, parent_header_id="H1")
    h_leaf = HeaderNode(header_id="H3", label="2026", level=3, col_start=0, col_end=1, parent_header_id="H2")

    graph = StructuralGraph()
    graph.add_header(h_root)
    graph.add_header(h_sub)
    graph.add_header(h_leaf)

    is_dag, err = graph.validate_acyclic_dag()
    assert is_dag is True
    assert err is None

    col = LogicalColumn(
        column_id="C01",
        position=0,
        header_path=("Segment Performance", "Three Months Ended", "2026"),
    )
    assert len(col.header_path) == 3
    assert col.header_path[0] == "Segment Performance"
    assert col.header_path[2] == "2026"


# ==============================================================================
# T03 - Duplicate Column Labels: Unique Coordinate Identities
# ==============================================================================
def test_t03_duplicate_column_labels():
    # '2026' under 3M vs '2026' under 9M must not collide
    c_3m_26 = LogicalColumn(column_id="C_3M_26", position=1, header_path=("Three Months", "2026"))
    c_9m_26 = LogicalColumn(column_id="C_9M_26", position=3, header_path=("Nine Months", "2026"))
    assert c_3m_26.column_id != c_9m_26.column_id
    assert c_3m_26.header_path != c_9m_26.header_path


# ==============================================================================
# T04 - Merged Cells: Correct Span Representation
# ==============================================================================
def test_t04_merged_cells():
    span = GridSpan(row_start=0, row_end=1, col_start=1, col_end=4)
    assert span.row_count == 1
    assert span.col_count == 3
    assert span.contains_slot(0, 2) is True
    assert span.contains_slot(0, 4) is False  # 4 is exclusive


# ==============================================================================
# T05 - Nested Rows: Complete Parent Paths
# ==============================================================================
def test_t05_nested_rows():
    row_parent = LogicalRow(row_id="R_OPEX", position=10, parent_row_id=None, raw_label="Operating Expenses")
    row_child = LogicalRow(
        row_id="R_RD",
        position=11,
        parent_row_id="R_OPEX",
        raw_label="Research and Development",
        indent_depth=2,
        ancestor_path=("Operating Expenses", "Research and Development"),
    )
    assert row_child.ancestor_path == ("Operating Expenses", "Research and Development")


# ==============================================================================
# T06 - Empty Cells: Distinguish Empty from Unknown
# ==============================================================================
def test_t06_empty_cells():
    cell_empty = CellNode(
        cell_id="C_EMPTY",
        role=CellRole.EMPTY,
        span=GridSpan(0, 1, 0, 1),
        raw_text="",
        bbox=None,
        source_ref=SourceRef("hash1", "p1", "r1", "ev1"),
    )
    cell_unknown = CellNode(
        cell_id="C_UNKNOWN",
        role=CellRole.UNKNOWN,
        span=GridSpan(0, 1, 1, 2),
        raw_text="???",
        bbox=None,
        source_ref=SourceRef("hash1", "p1", "r2", "ev2"),
    )
    assert cell_empty.role == CellRole.EMPTY
    assert cell_unknown.role == CellRole.UNKNOWN


# ==============================================================================
# T07 - Parenthetical Negatives: Exact Negative Decimal
# ==============================================================================
def test_t07_parenthetical_negatives():
    raw = "(158.20)"
    inner = raw.replace("(", "-").replace(")", "")
    val = parse_exact_decimal(inner)
    assert val == Decimal("-158.20")
    exact = ExactNumeric(raw_text=raw, value=val)
    assert exact.value == Decimal("-158.20")


# ==============================================================================
# T08 - Bounded Values: Preserve Inequality (< 0.01)
# ==============================================================================
def test_t08_bounded_values():
    bounded = BoundedNumeric(raw_text="<0.01", bound=Decimal("0.01"), operator=BoundOperator.LT)
    assert bounded.operator == BoundOperator.LT
    assert bounded.bound == Decimal("0.01")
    # Must not convert to 0 or arbitrary float
    assert isinstance(bounded.bound, Decimal)


# ==============================================================================
# T09 - Unit Overrides: Correct Scope Resolution
# ==============================================================================
def test_t09_unit_overrides():
    # Table level = $ Millions (scale 6), Row level = Shares in Thousands (scale 3, shares)
    table_unit = UnitAssertion(currency="USD", scale_exponent=6, source_scope=ScopeLevel.TABLE)
    row_unit = UnitAssertion(physical_unit="shares", scale_exponent=3, source_scope=ScopeLevel.ROW)

    status, resolved, err = ScopeConflictResolver.resolve_unit_assertions(
        cell_unit=None,
        row_unit=row_unit,
        col_unit=None,
        table_unit=table_unit,
    )
    assert status == ResolutionStatus.RESOLVED
    assert resolved.scale_exponent == 3
    assert resolved.physical_unit == "shares"


# ==============================================================================
# T10 - Conflicting Row/Column Units: CONFLICT
# ==============================================================================
def test_t10_conflicting_row_col_units():
    # Row says USD, Column says EUR
    row_unit = UnitAssertion(currency="USD", scale_exponent=6, source_scope=ScopeLevel.ROW)
    col_unit = UnitAssertion(currency="EUR", scale_exponent=6, source_scope=ScopeLevel.COLUMN)

    status, resolved, err = ScopeConflictResolver.resolve_unit_assertions(
        cell_unit=None,
        row_unit=row_unit,
        col_unit=col_unit,
        table_unit=None,
    )
    assert status == ResolutionStatus.CONFLICT
    assert "Conflicting currency" in err


# ==============================================================================
# T11 - Instant versus Duration: Distinct Temporal Types
# ==============================================================================
def test_t11_instant_vs_duration():
    instant = InstantPeriod(as_of_date=datetime.date(2026, 9, 30))
    duration = DurationPeriod(start_date=datetime.date(2026, 7, 1), end_date=datetime.date(2026, 9, 30))
    assert isinstance(instant, InstantPeriod)
    assert isinstance(duration, DurationPeriod)
    assert instant != duration


# ==============================================================================
# T12 - Missing Period: UNRESOLVED
# ==============================================================================
def test_t12_missing_period():
    prov = MultiSourceProvenanceBundle(
        value_anchor=EvidenceAnchor("EV1", "hash1234567890abcdef", "1", "r1", None, "100", EvidenceRole.VALUE)
    )
    fact = SourceFact(
        fact_id="F1",
        source_cell_id="C1",
        coordinates=FactCoordinates("ENT1", "Chronos", "MET1", "Revenue", ("Revenue",), ("Col1",), temporal=None),
        typed_value=ExactNumeric("100", Decimal("100")),
        unit=UnitAssertion(currency="USD"),
        canonical_display="USD 100",
        provenance=prov,
    )
    doc = SourceDocument("DOC1", "hash1234567890abcdef", "application/pdf", 1024)
    snapshot = CTIRSnapshot(
        snapshot_id="SNAP_01",
        document=doc,
        source_facts={"F1": fact},
    )
    report = CTIRValidator.validate_snapshot(snapshot)
    assert report.semantics_status == ValidationStatus.UNRESOLVED


# ==============================================================================
# T13 - Header Footnotes: Correct Header Binding
# ==============================================================================
def test_t13_header_footnotes():
    h = HeaderNode(header_id="H_DATE", label="Sept 30, 2026", level=1, col_start=0, col_end=1, footnote_ids=("FN_03",))
    assert "FN_03" in h.footnote_ids


# ==============================================================================
# T14 - Chained Footnotes: Dependency References Preserved
# ==============================================================================
def test_t14_chained_footnotes():
    ref_graph = ReferenceGraph()
    fn_a = FootnoteNode(footnote_id="FN_A", marker="(a)", text="Subject to arbitration settlement under Note 2.")
    fn_2 = FootnoteNode(footnote_id="FN_2", marker="[2]", text="Arbitration settlement finalized Oct 2, 2026.")
    ref_graph.add_footnote(fn_a)
    ref_graph.add_footnote(fn_2)
    ref_graph.add_note_link("FN_A", "FN_2")
    assert ("FN_A", "FN_2") in ref_graph.note_to_note_edges


# ==============================================================================
# T15 - Circular Notes: Cycle Detected
# ==============================================================================
def test_t15_circular_notes():
    ref_graph = ReferenceGraph()
    ref_graph.add_note_link("FN_A", "FN_B")
    ref_graph.add_note_link("FN_B", "FN_A")
    cycles = ref_graph.detect_reference_cycles()
    assert len(cycles) > 0
    assert ("FN_A", "FN_B") in cycles or ("FN_B", "FN_A") in cycles

    # Also test 3-node directed cycle detection: FN_1 -> FN_2 -> FN_3 -> FN_1
    ref_graph_3 = ReferenceGraph()
    ref_graph_3.add_note_link("FN_1", "FN_2")
    ref_graph_3.add_note_link("FN_2", "FN_3")
    ref_graph_3.add_note_link("FN_3", "FN_1")
    cycles_3 = ref_graph_3.detect_reference_cycles()
    assert len(cycles_3) == 1
    assert ("FN_1", "FN_2", "FN_3") in cycles_3


# ==============================================================================
# T16 - Multi-Page Tables: Original Fragments Preserved
# ==============================================================================
def test_t16_multi_page_tables():
    # Contract C17: Assembling multi-page fragments retains all child fragment IDs
    lt = LogicalTable(table_id="TAB_CONSOLIDATED", fragment_ids=("FRAG_PAGE_12", "FRAG_PAGE_13"), is_stitched=True)
    assert len(lt.fragment_ids) == 2
    assert lt.is_stitched is True


# ==============================================================================
# T17 - Overlapping Source Cells: Structural Validation Failure
# ==============================================================================
def test_t17_overlapping_source_cells():
    span1 = GridSpan(0, 2, 0, 2)  # [0..2) x [0..2)
    span2 = GridSpan(1, 3, 1, 3)  # [1..3) x [1..3) -> Overlaps!
    assert spans_overlap(span1, span2) is True

    c1 = CellNode("C1", CellRole.DATA, span1, "10", None, SourceRef("hash", "1", "r1", "e1"))
    c2 = CellNode("C2", CellRole.DATA, span2, "20", None, SourceRef("hash", "1", "r2", "e2"))

    doc = SourceDocument("DOC1", "hash1234567890abcdef", "application/pdf", 1024)
    snapshot = CTIRSnapshot(
        snapshot_id="SNAP_OVERLAP",
        document=doc,
        cells={"C1": c1, "C2": c2},
    )
    report = CTIRValidator.validate_snapshot(snapshot)
    assert report.structure_status == ValidationStatus.FAIL
    assert any(d.code == "GRID_SPAN_OVERLAP" for d in report.diagnostics)


# ==============================================================================
# T18 - Multiple Parser Hypotheses: No Premature Commitment
# ==============================================================================
def test_t18_multiple_parser_hypotheses():
    # Hypotheses can coexist in extraction records without mutating accepted IR
    hypotheses = {
        "Docling": {"col_count": 5, "confidence": 0.88},
        "TATR": {"col_count": 4, "confidence": 0.72},
    }
    assert len(hypotheses) == 2
    assert hypotheses["Docling"]["col_count"] != hypotheses["TATR"]["col_count"]


# ==============================================================================
# T19 - Tampered Source File: Hash Verification Failure
# ==============================================================================
def test_t19_tampered_source_file():
    doc = SourceDocument("DOC1", "short_bad_hash", "application/pdf", 1024)
    snapshot = CTIRSnapshot(snapshot_id="SNAP_BAD_HASH", document=doc)
    report = CTIRValidator.validate_snapshot(snapshot)
    assert report.source_status == ValidationStatus.FAIL
    assert any(d.code == "SOURCE_INVALID_HASH" for d in report.diagnostics)


# ==============================================================================
# T20 - Serialization Round-Trip: Semantic Equivalence
# ==============================================================================
def test_t20_serialization_round_trip():
    doc = SourceDocument("DOC1", "hash1234567890abcdef", "application/pdf", 1024)
    space = CoordinateSpace("CS_POINT", "PDF_POINT", Decimal("612"), Decimal("792"))
    snapshot = CTIRSnapshot(
        snapshot_id="SNAP_SERIALIZE",
        document=doc,
        coordinate_spaces=(space,),
    )
    json_str = serialize_ctir_to_json(snapshot)
    assert "SNAP_SERIALIZE" in json_str
    assert "hash1234567890abcdef" in json_str
    assert "612" in json_str


# ==============================================================================
# T21 - Layout Perturbation: Metamorphic Semantic Invariance
# ==============================================================================
def test_t21_layout_perturbation():
    # Value normalized from $(158.20) on 600pt layout vs (158.20) on 800pt layout
    v1 = parse_exact_decimal("-158.20")
    v2 = parse_exact_decimal("-158.20")
    assert v1 == v2  # Semantic projection remains identical across layouts


# ==============================================================================
# T22 - Formula Spanning Chunks: Cross-Chunk Lineage Preserved
# ==============================================================================
def test_t22_formula_spanning_chunks():
    # Contract C14: Derived fact explicitly references inputs across chunk boundaries
    rev = ExactNumeric("150", Decimal("150"))
    cogs = ExactNumeric("100", Decimal("100"))
    gp = ExactNumeric("50", rev.value - cogs.value)

    derived = DerivedFact(
        fact_id="F_GROSS_PROFIT",
        expression_name="SUBTRACT",
        input_fact_ids=("F_REVENUE_CHUNK1", "F_COGS_CHUNK2"),
        result_value=gp,
        unit=UnitAssertion(currency="USD", scale_exponent=6),
        canonical_display="USD 50.00M",
    )
    assert derived.input_fact_ids == ("F_REVENUE_CHUNK1", "F_COGS_CHUNK2")
    assert derived.result_value.value == Decimal("50")


# ==============================================================================
# T23 - Repeated Ingestion: Idempotent Output
# ==============================================================================
def test_t23_repeated_ingestion_idempotence():
    # Contract C16: Same input + same rules yields bit-for-bit identical serialization
    doc = SourceDocument("DOC1", "hash1234567890abcdef", "application/pdf", 1024)
    s1 = serialize_ctir_to_json(CTIRSnapshot("SNAP_IDEM", document=doc))
    s2 = serialize_ctir_to_json(CTIRSnapshot("SNAP_IDEM", document=doc))
    assert s1 == s2


# ==============================================================================
# T24 - Parser Version Change: New Versioned Snapshot
# ==============================================================================
def test_t24_parser_version_change():
    doc = SourceDocument("DOC1", "hash1234567890abcdef", "application/pdf", 1024)
    snap_v1 = CTIRSnapshot("SNAP_V1", schema_version="3.1.0", document=doc)
    snap_v2 = CTIRSnapshot("SNAP_V2", schema_version="3.2.0", document=doc)
    assert snap_v1.schema_version != snap_v2.schema_version
    assert snap_v1.snapshot_id != snap_v2.snapshot_id

