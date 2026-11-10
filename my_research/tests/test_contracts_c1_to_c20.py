"""
PCC-Tensor 3.2: Formal Contract Verification Suite (Contracts C1 through C20).
Enforces the 20 mathematical invariants of Evidence-Closed Table Compilation.
Tests positive conforming cases, negative violation cases, and unresolved non-fatal cases.
"""

from __future__ import annotations

import datetime
import pathlib
from decimal import Decimal
import pytest

from my_research.src.adapter.ascii_table import AsciiTableScheduleAdapter
from my_research.src.adapter.base import BaseTableAdapter
from my_research.src.compiler.table_compiler import TableCompiler
from my_research.src.model.ctir import (
    CTIRSnapshot,
    DerivedFact,
    FactCoordinates,
    SourceFact,
    ValidationReport,
    ValidationStatus,
)
from my_research.src.model.evidence import (
    EvidenceAnchor,
    EvidenceRole,
    MultiSourceProvenanceBundle,
    TransformationRecord,
)
from my_research.src.model.geometry import GridSpan
from my_research.src.model.structural import (
    CellNode,
    CellRole,
    HeaderNode,
    LogicalColumn,
    LogicalRow,
    LogicalTable,
    TableFragment,
)
from my_research.src.model.semantic import ScopeLevel, UnitAssertion
from my_research.src.model.source import BoundingBox, CoordinateSpace, SourceDocument, SourceRef
from my_research.src.model.temporal import DurationPeriod, InstantPeriod
from my_research.src.model.value import (
    BoundOperator,
    BoundedNumeric,
    ExactNumeric,
    MissingReason,
    MissingValue,
)
from my_research.src.storage.serialize import serialize_ctir_to_json
from my_research.src.verifier.validate import CTIRValidator

DATA_DIR = pathlib.Path(__file__).resolve().parent.parent / "data"


# ==============================================================================
# Helper fixtures
# ==============================================================================
@pytest.fixture
def base_doc() -> SourceDocument:
    return SourceDocument(
        document_id="DOC_VALID_01",
        sha256="a" * 64,
        mime_type="text/plain",
        byte_length=1024,
    )


@pytest.fixture
def base_space() -> CoordinateSpace:
    return CoordinateSpace(
        space_id="SPACE_01",
        kind="MARKDOWN_OFFSET",
        width=Decimal("100"),
        height=Decimal("100"),
    )


@pytest.fixture
def valid_fact_bundle(base_doc) -> MultiSourceProvenanceBundle:
    return MultiSourceProvenanceBundle(
        value_anchor=EvidenceAnchor("ev_v", base_doc.sha256, "p0", "r0", None, "100.00", EvidenceRole.VALUE),
        metric_anchor=EvidenceAnchor("ev_m", base_doc.sha256, "p0", "r0", None, "Revenue", EvidenceRole.METRIC_LABEL),
        period_anchor=EvidenceAnchor("ev_p", base_doc.sha256, "p0", "r0", None, "2026", EvidenceRole.PERIOD_DECLARATION),
        unit_anchor=EvidenceAnchor("ev_u", base_doc.sha256, "p0", "r0", None, "USD 10^6", EvidenceRole.UNIT_DECLARATION),
        entity_anchor=EvidenceAnchor("ev_e", base_doc.sha256, "p0", "r0", None, "Entity Corp", EvidenceRole.ENTITY_IDENTITY),
    )


# ==============================================================================
# Contract C1: Source Document Integrity
# ==============================================================================
def test_contract_c1_source_integrity(base_doc):
    # Positive: Valid SHA-256 and byte length
    snap_ok = CTIRSnapshot("snap_c1", document=base_doc)
    diags_ok = CTIRValidator.verify_c1_source_integrity(snap_ok)
    assert len(diags_ok) == 0

    # Negative 1: Missing SourceDocument
    snap_null = CTIRSnapshot("snap_c1_null", document=None)
    diags_null = CTIRValidator.verify_c1_source_integrity(snap_null)
    assert any(d.code == "SOURCE_MISSING_DOCUMENT" for d in diags_null)

    # Negative 2: Tampered / Short Hash
    doc_bad = SourceDocument("doc_bad", "invalid_short_hash", "text/plain", 100)
    snap_bad = CTIRSnapshot("snap_c1_bad", document=doc_bad)
    diags_bad = CTIRValidator.verify_c1_source_integrity(snap_bad)
    assert any(d.code == "SOURCE_INVALID_HASH" for d in diags_bad)


# ==============================================================================
# Contract C2: Table Fragment Preservation
# ==============================================================================
def test_contract_c2_fragment_preservation(base_doc):
    c1 = CellNode("cell_1", CellRole.DATA, GridSpan(0, 1, 0, 1), "10", None, SourceRef(base_doc.sha256, "0", "0", "c1"))
    c2 = CellNode("cell_2", CellRole.DATA, GridSpan(0, 1, 1, 2), "20", None, SourceRef(base_doc.sha256, "0", "0", "c2"))
    frag = TableFragment("frag_1", "p0", 1, 2, cells=(c1, c2))
    snap_ok = CTIRSnapshot("snap_c2", document=base_doc, fragments=(frag,))
    assert len(CTIRValidator.verify_c2_fragment_preservation(snap_ok)) == 0

    # Negative: Duplicate cell ID
    c2_dup = CellNode("cell_1", CellRole.DATA, GridSpan(0, 1, 1, 2), "20", None, SourceRef(base_doc.sha256, "0", "0", "c1"))
    frag_dup = TableFragment("frag_dup", "p0", 1, 2, cells=(c1, c2_dup))
    snap_dup = CTIRSnapshot("snap_c2_dup", document=base_doc, fragments=(frag_dup,))
    diags = CTIRValidator.verify_c2_fragment_preservation(snap_dup)
    assert any(d.code == "FRAGMENT_DUPLICATE_CELL_ID" for d in diags)


# ==============================================================================
# Contract C3: Bounding-Box Validity & Coordinate Space
# ==============================================================================
def test_contract_c3_geometry_space(base_doc, base_space):
    # Positive: Valid bounding box within space
    bbox_ok = BoundingBox(Decimal("10"), Decimal("10"), Decimal("50"), Decimal("50"), base_space.space_id)
    c1 = CellNode("cell_1", CellRole.DATA, GridSpan(0, 1, 0, 1), "10", bbox_ok, SourceRef(base_doc.sha256, "0", "0", "c1"))
    snap_ok = CTIRSnapshot("snap_c3", document=base_doc, coordinate_spaces=(base_space,), cells={"cell_1": c1})
    assert len(CTIRValidator.verify_c3_geometry_space(snap_ok)) == 0

    # Negative 1: Undeclared coordinate space
    bbox_undeclared = BoundingBox(Decimal("10"), Decimal("10"), Decimal("50"), Decimal("50"), "UNKNOWN_SPACE")
    c_und = CellNode("c_und", CellRole.DATA, GridSpan(0, 1, 0, 1), "10", bbox_undeclared, SourceRef(base_doc.sha256, "0", "0", "c"))
    snap_und = CTIRSnapshot("snap_und", document=base_doc, coordinate_spaces=(base_space,), cells={"c_und": c_und})
    assert any(d.code == "GEOMETRY_UNDECLARED_SPACE" for d in CTIRValidator.verify_c3_geometry_space(snap_und))

    # Negative 2: Degenerate BBox (x0 >= x1) is blocked at instantiation
    with pytest.raises(ValueError, match="x0 .* >= x1"):
        BoundingBox(Decimal("50"), Decimal("10"), Decimal("10"), Decimal("50"), base_space.space_id)

    # Negative 2 (defense-in-depth): Validator catches bypass degenerate bbox
    bbox_deg = object.__new__(BoundingBox)
    object.__setattr__(bbox_deg, "x0", Decimal("50"))
    object.__setattr__(bbox_deg, "y0", Decimal("10"))
    object.__setattr__(bbox_deg, "x1", Decimal("10"))
    object.__setattr__(bbox_deg, "y1", Decimal("50"))
    object.__setattr__(bbox_deg, "coordinate_space_id", base_space.space_id)
    c_deg = CellNode("c_deg", CellRole.DATA, GridSpan(0, 1, 0, 1), "10", bbox_deg, SourceRef(base_doc.sha256, "0", "0", "c"))
    snap_deg = CTIRSnapshot("snap_deg", document=base_doc, coordinate_spaces=(base_space,), cells={"c_deg": c_deg})
    assert any(d.code == "GEOMETRY_DEGENERATE_BBOX" for d in CTIRValidator.verify_c3_geometry_space(snap_deg))

    # Negative 3: Out of bounds bbox (exceeds width)
    bbox_oob = BoundingBox(Decimal("10"), Decimal("10"), Decimal("150"), Decimal("50"), base_space.space_id)
    c_oob = CellNode("c_oob", CellRole.DATA, GridSpan(0, 1, 0, 1), "10", bbox_oob, SourceRef(base_doc.sha256, "0", "0", "c"))
    snap_oob = CTIRSnapshot("snap_oob", document=base_doc, coordinate_spaces=(base_space,), cells={"c_oob": c_oob})
    assert any(d.code == "GEOMETRY_OUT_OF_BOUNDS" for d in CTIRValidator.verify_c3_geometry_space(snap_oob))


# ==============================================================================
# Contract C4: Grid Consistency & Non-Overlap
# ==============================================================================
def test_contract_c4_grid_consistency(base_doc):
    c1 = CellNode("c1", CellRole.DATA, GridSpan(0, 1, 0, 1), "10", None, SourceRef(base_doc.sha256, "0", "0", "c1"))
    c2 = CellNode("c2", CellRole.DATA, GridSpan(0, 1, 1, 2), "20", None, SourceRef(base_doc.sha256, "0", "0", "c2"))
    snap_ok = CTIRSnapshot("snap_c4", document=base_doc, cells={"c1": c1, "c2": c2})
    assert len(CTIRValidator.verify_c4_grid_consistency(snap_ok)) == 0

    # Negative: Overlapping spans
    c2_overlap = CellNode("c2_ol", CellRole.DATA, GridSpan(0, 2, 0, 1), "20", None, SourceRef(base_doc.sha256, "0", "0", "c2"))
    snap_ol = CTIRSnapshot("snap_ol", document=base_doc, cells={"c1": c1, "c2_ol": c2_overlap})
    assert any(d.code == "GRID_SPAN_OVERLAP" for d in CTIRValidator.verify_c4_grid_consistency(snap_ol))


# ==============================================================================
# Contract C5: Structural Hierarchy Acyclicity
# ==============================================================================
def test_contract_c5_structural_acyclicity(base_doc):
    h1 = HeaderNode("H1", "Revenue", 1, 0, 1, None)
    h2 = HeaderNode("H2", "Product", 2, 0, 1, "H1")
    snap_ok = CTIRSnapshot("snap_c5", document=base_doc, headers={"H1": h1, "H2": h2})
    assert len(CTIRValidator.verify_c5_structural_acyclicity(snap_ok)) == 0

    # Negative: Cyclic header relationship
    h1_cycle = HeaderNode("H1", "Revenue", 1, 0, 1, "H2")
    snap_cycle = CTIRSnapshot("snap_cycle", document=base_doc, headers={"H1": h1_cycle, "H2": h2})
    assert any(d.code == "STRUCTURAL_CYCLE_DETECTED" for d in CTIRValidator.verify_c5_structural_acyclicity(snap_cycle))


# ==============================================================================
# Contract C6: Column Header Closure
# ==============================================================================
def test_contract_c6_column_header_closure(base_doc):
    col_ok = LogicalColumn("COL_0", 0, ("Three Months Ended", "2026"))
    snap_ok = CTIRSnapshot("snap_c6", document=base_doc, columns={"COL_0": col_ok})
    assert len(CTIRValidator.verify_c6_column_header_closure(snap_ok)) == 0

    # Negative: Empty header path
    col_empty = LogicalColumn("COL_BAD", 0, ())
    snap_bad = CTIRSnapshot("snap_c6_bad", document=base_doc, columns={"COL_BAD": col_empty})
    assert any(d.code == "COLUMN_EMPTY_HEADER_PATH" for d in CTIRValidator.verify_c6_column_header_closure(snap_bad))


# ==============================================================================
# Contract C7: Row Hierarchy Closure
# ==============================================================================
def test_contract_c7_row_hierarchy_closure(base_doc):
    r1 = LogicalRow("R1", 0, None, "SECTION", "Operating Expenses", 0, ())
    r2 = LogicalRow("R2", 1, "R1", "DETAIL", "R&D", 1, ("Operating Expenses",))
    snap_ok = CTIRSnapshot("snap_c7", document=base_doc, rows={"R1": r1, "R2": r2})
    assert len(CTIRValidator.verify_c7_row_hierarchy_closure(snap_ok)) == 0

    # Negative: Dangling parent row reference
    r2_dangling = LogicalRow("R2", 1, "NON_EXISTENT_ROW", "DETAIL", "R&D", 1, ())
    snap_dang = CTIRSnapshot("snap_dang", document=base_doc, rows={"R1": r1, "R2": r2_dangling})
    assert any(d.code == "ROW_DANGLING_PARENT" for d in CTIRValidator.verify_c7_row_hierarchy_closure(snap_dang))


# ==============================================================================
# Contract C8: Raw Value Preservation & Transformation Replay
# ==============================================================================
def test_contract_c8_raw_value_preservation(base_doc, valid_fact_bundle):
    coord = FactCoordinates("e0", "Corp", "m0", "Rev", (), ("2026",), InstantPeriod(datetime.date(2026, 9, 30)))
    unit = UnitAssertion(currency="USD", scale_exponent=6)
    tx = TransformationRecord("tx_1", "PAREN_NEG", "(158.20)", "-158.20", True)

    fact_ok = SourceFact(
        "f_ok", "c1", coord, ExactNumeric("-158.20", Decimal("-158.20")), unit, "USD -158,200,000.00",
        valid_fact_bundle, ValidationStatus.UNRESOLVED, (tx,)
    )
    snap_ok = CTIRSnapshot("snap_c8", document=base_doc, source_facts={"f_ok": fact_ok})
    assert len(CTIRValidator.verify_c8_raw_value_preservation(snap_ok)) == 0

    # Negative: Missing raw text
    fact_no_raw = SourceFact(
        "f_no_raw", "c1", coord, ExactNumeric("", Decimal("-158.20")), unit, "-158.20",
        valid_fact_bundle, ValidationStatus.UNRESOLVED
    )
    snap_no_raw = CTIRSnapshot("snap_no_raw", document=base_doc, source_facts={"f_no_raw": fact_no_raw})
    assert any(d.code == "RAW_TEXT_MISSING" for d in CTIRValidator.verify_c8_raw_value_preservation(snap_no_raw))

    # Negative: Replay failure
    tx_fail = TransformationRecord("tx_2", "PAREN_NEG", "(158.20)", "-158.20", False)
    fact_fail_replay = SourceFact(
        "f_fail_tx", "c1", coord, ExactNumeric("(158.20)", Decimal("-158.20")), unit, "-158.20",
        valid_fact_bundle, ValidationStatus.UNRESOLVED, (tx_fail,)
    )
    snap_fail_tx = CTIRSnapshot("snap_fail_tx", document=base_doc, source_facts={"f_fail_tx": fact_fail_replay})
    assert any(d.code == "TRANSFORMATION_REPLAY_MISMATCH" for d in CTIRValidator.verify_c8_raw_value_preservation(snap_fail_tx))


# ==============================================================================
# Contract C9: Typed Value Lattice Soundness
# ==============================================================================
def test_contract_c9_value_lattice_soundness(base_doc, valid_fact_bundle):
    coord = FactCoordinates("e0", "Corp", "m0", "Rev", (), ("2026",), InstantPeriod(datetime.date(2026, 9, 30)))
    unit = UnitAssertion(currency="USD", scale_exponent=0)

    # Positive: ExactNumeric with Decimal
    fact_exact = SourceFact("f1", "c1", coord, ExactNumeric("100", Decimal("100")), unit, "100", valid_fact_bundle)
    # Positive: BoundedNumeric
    fact_bounded = SourceFact("f2", "c2", coord, BoundedNumeric("< 0.01", Decimal("0.01"), BoundOperator.LT), unit, "<0.01", valid_fact_bundle)
    # Positive: MissingValue
    fact_missing = SourceFact("f3", "c3", coord, MissingValue("—", MissingReason.NIL_DASH), unit, "[NIL_DASH]", valid_fact_bundle)

    snap = CTIRSnapshot("snap_c9", document=base_doc, source_facts={"f1": fact_exact, "f2": fact_bounded, "f3": fact_missing})
    assert len(CTIRValidator.verify_c9_value_lattice_soundness(snap)) == 0

    # Negative 1: Non-lattice type (e.g. raw string passed as typed_value)
    fact_invalid_type = SourceFact("f_bad_type", "c1", coord, "not_a_value_lattice_instance", unit, "err", valid_fact_bundle) # type: ignore
    snap_bad_type = CTIRSnapshot("snap_bad_type", document=base_doc, source_facts={"f_bad_type": fact_invalid_type})
    assert any(d.code == "VALUE_INVALID_LATTICE_TYPE" for d in CTIRValidator.verify_c9_value_lattice_soundness(snap_bad_type))

    # Negative 2: Float precision drift blocked at instantiation
    with pytest.raises(TypeError, match="Value must be a decimal.Decimal instance"):
        ExactNumeric("100.5", 100.5)  # type: ignore

    # Negative 3 (defense-in-depth): Validator catches float drift if bypassed
    bad_val = object.__new__(ExactNumeric)
    object.__setattr__(bad_val, "raw_text", "100.5")
    object.__setattr__(bad_val, "value", 100.5)
    fact_float = SourceFact("f_float", "c1", coord, bad_val, unit, "100.5", valid_fact_bundle)
    snap_float = CTIRSnapshot("snap_float", document=base_doc, source_facts={"f_float": fact_float})
    assert any(d.code == "VALUE_FLOAT_PRECISION_DRIFT" for d in CTIRValidator.verify_c9_value_lattice_soundness(snap_float))


# ==============================================================================
# Contract C10: Unit Consistency
# ==============================================================================
def test_contract_c10_unit_consistency(base_doc, valid_fact_bundle):
    coord = FactCoordinates("e0", "Corp", "m0", "Rev", (), ("2026",), InstantPeriod(datetime.date(2026, 9, 30)))
    # Positive: scale 6 with multiplier 10^6 = 1,000,000
    unit_ok = UnitAssertion(currency="USD", scale_exponent=6)
    fact_ok = SourceFact("f1", "c1", coord, ExactNumeric("10", Decimal("10")), unit_ok, "USD 10,000,000", valid_fact_bundle)
    snap_ok = CTIRSnapshot("snap_c10", document=base_doc, source_facts={"f1": fact_ok})
    assert len(CTIRValidator.verify_c10_unit_consistency(snap_ok)) == 0


# ==============================================================================
# Contract C11: Temporal Interval Consistency
# ==============================================================================
def test_contract_c11_temporal_consistency(base_doc, valid_fact_bundle):
    # Positive: Duration with start <= end
    p_ok = DurationPeriod(datetime.date(2026, 7, 1), datetime.date(2026, 9, 30), 91, "Q3 2026")
    coord_ok = FactCoordinates("e0", "Corp", "m0", "Rev", (), ("2026",), p_ok)
    fact_ok = SourceFact("f1", "c1", coord_ok, ExactNumeric("10", Decimal("10")), UnitAssertion(), "10", valid_fact_bundle)
    snap_ok = CTIRSnapshot("snap_c11", document=base_doc, source_facts={"f1": fact_ok})
    assert len(CTIRValidator.verify_c11_temporal_consistency(snap_ok)) == 0

    # Negative 1: Inverted temporal interval blocked at instantiation
    with pytest.raises(ValueError, match="Contract C11 violation: start_date .* > end_date"):
        DurationPeriod(datetime.date(2026, 10, 1), datetime.date(2026, 9, 30), -1, "Bad Duration")

    # Negative 2 (defense-in-depth): Validator catches inverted interval if bypassed
    p_bad = object.__new__(DurationPeriod)
    object.__setattr__(p_bad, "start_date", datetime.date(2026, 10, 1))
    object.__setattr__(p_bad, "end_date", datetime.date(2026, 9, 30))
    object.__setattr__(p_bad, "calendar_id", -1)
    object.__setattr__(p_bad, "fiscal_year", "Bad Duration")
    object.__setattr__(p_bad, "fiscal_quarter", None)
    object.__setattr__(p_bad, "fiscal_label", None)
    coord_bad = FactCoordinates("e0", "Corp", "m0", "Rev", (), ("2026",), p_bad)
    fact_bad = SourceFact("f2", "c2", coord_bad, ExactNumeric("10", Decimal("10")), UnitAssertion(), "10", valid_fact_bundle)
    snap_bad = CTIRSnapshot("snap_c11_bad", document=base_doc, source_facts={"f2": fact_bad})
    assert any(d.code == "TEMPORAL_INVERTED_INTERVAL" for d in CTIRValidator.verify_c11_temporal_consistency(snap_bad))

    # Unresolved: Missing temporal coordinate
    coord_none = FactCoordinates("e0", "Corp", "m0", "Rev", (), ("2026",), None)
    fact_none = SourceFact("f3", "c3", coord_none, ExactNumeric("10", Decimal("10")), UnitAssertion(), "10", valid_fact_bundle)
    snap_none = CTIRSnapshot("snap_c11_none", document=base_doc, source_facts={"f3": fact_none})
    diags_none = CTIRValidator.verify_c11_temporal_consistency(snap_none)
    assert any(d.code == "SEMANTICS_MISSING_TEMPORAL" and d.severity == "WARNING" for d in diags_none)


# ==============================================================================
# Contract C12: Scope Poset Orthogonality
# ==============================================================================
def test_contract_c12_scope_poset(base_doc, valid_fact_bundle):
    coord = FactCoordinates("e0", "Corp", "m0", "Rev", (), ("2026",), InstantPeriod(datetime.date(2026, 9, 30)))
    unit_ok = UnitAssertion(currency="USD", scale_exponent=6)
    fact_ok = SourceFact("f1", "c1", coord, ExactNumeric("10", Decimal("10")), unit_ok, "10", valid_fact_bundle)
    snap_ok = CTIRSnapshot("snap_c12", document=base_doc, source_facts={"f1": fact_ok})
    assert len(CTIRValidator.verify_c12_scope_poset(snap_ok)) == 0

    # Negative: Missing unit assertion
    fact_null_unit = SourceFact("f_null_u", "c1", coord, ExactNumeric("10", Decimal("10")), None, "10", valid_fact_bundle) # type: ignore
    snap_null_u = CTIRSnapshot("snap_c12_bad", document=base_doc, source_facts={"f_null_u": fact_null_unit})
    assert any(d.code == "SCOPE_UNRESOLVED_UNIT" for d in CTIRValidator.verify_c12_scope_poset(snap_null_u))


# ==============================================================================
# Contract C13: Multi-Source Provenance Closure
# ==============================================================================
def test_contract_c13_provenance_closure(base_doc, valid_fact_bundle):
    coord = FactCoordinates("e0", "Corp", "m0", "Rev", (), ("2026",), InstantPeriod(datetime.date(2026, 9, 30)))
    fact_ok = SourceFact("f1", "c1", coord, ExactNumeric("10", Decimal("10")), UnitAssertion(), "10", valid_fact_bundle)
    snap_ok = CTIRSnapshot("snap_c13", document=base_doc, source_facts={"f1": fact_ok})
    assert len(CTIRValidator.verify_c13_provenance_closure(snap_ok)) == 0

    # Negative: Missing Value Anchor
    bundle_no_val = MultiSourceProvenanceBundle(value_anchor=None) # type: ignore
    fact_no_val = SourceFact("f_no_val", "c1", coord, ExactNumeric("10", Decimal("10")), UnitAssertion(), "10", bundle_no_val)
    snap_no_val = CTIRSnapshot("snap_no_val", document=base_doc, source_facts={"f_no_val": fact_no_val})
    assert any(d.code == "PROVENANCE_MISSING_VALUE_ANCHOR" for d in CTIRValidator.verify_c13_provenance_closure(snap_no_val))

    # Unresolved: Incomplete Evidence Closure (e.g. missing unit anchor)
    bundle_partial = MultiSourceProvenanceBundle(
        value_anchor=EvidenceAnchor("v", base_doc.sha256, "p0", "r0", None, "10", EvidenceRole.VALUE),
        unit_anchor=None,
    )
    fact_partial = SourceFact("f_part", "c1", coord, ExactNumeric("10", Decimal("10")), UnitAssertion(), "10", bundle_partial)
    snap_part = CTIRSnapshot("snap_part", document=base_doc, source_facts={"f_part": fact_partial})
    diags_part = CTIRValidator.verify_c13_provenance_closure(snap_part)
    assert any(d.code == "PROVENANCE_INCOMPLETE_CLOSURE" and d.severity == "WARNING" for d in diags_part)


# ==============================================================================
# Contract C14: Fact Lineage & Source vs. Derived Facts
# ==============================================================================
def test_contract_c14_fact_lineage(base_doc, valid_fact_bundle):
    coord = FactCoordinates("e0", "Corp", "m0", "Rev", (), ("2026",), InstantPeriod(datetime.date(2026, 9, 30)))
    unit = UnitAssertion(currency="USD", scale_exponent=6)

    f_rev = SourceFact("f_rev", "c1", coord, ExactNumeric("100.00", Decimal("100.00")), unit, "100.00", valid_fact_bundle)
    f_cogs = SourceFact("f_cogs", "c2", coord, ExactNumeric("-60.00", Decimal("-60.00")), unit, "-60.00", valid_fact_bundle)

    # Positive: Verified derived fact (100.00 + (-60.00) = 40.00)
    df_ok = DerivedFact("df_gross", "ADD_OUTFLOW", ("f_rev", "f_cogs"), ExactNumeric("40.00", Decimal("40.00")), unit, "40.00")
    snap_ok = CTIRSnapshot("snap_c14", document=base_doc, source_facts={"f_rev": f_rev, "f_cogs": f_cogs}, derived_facts={"df_gross": df_ok})
    assert len(CTIRValidator.verify_c14_fact_lineage(snap_ok)) == 0

    # Negative 1: Missing input fact
    df_missing_inp = DerivedFact("df_bad", "ADD_OUTFLOW", ("f_rev", "f_missing"), ExactNumeric("40.00", Decimal("40.00")), unit, "40.00")
    snap_missing = CTIRSnapshot("snap_miss", document=base_doc, source_facts={"f_rev": f_rev}, derived_facts={"df_bad": df_missing_inp})
    assert any(d.code == "DERIVED_MISSING_INPUT_FACT" for d in CTIRValidator.verify_c14_fact_lineage(snap_missing))

    # Negative 2: Arithmetic calculation mismatch (expected 40.00, claims 99.00)
    df_mismatch = DerivedFact("df_err", "ADD_OUTFLOW", ("f_rev", "f_cogs"), ExactNumeric("99.00", Decimal("99.00")), unit, "99.00")
    snap_mismatch = CTIRSnapshot("snap_mis", document=base_doc, source_facts={"f_rev": f_rev, "f_cogs": f_cogs}, derived_facts={"df_err": df_mismatch})
    assert any(d.code == "DERIVED_CALCULATION_MISMATCH" for d in CTIRValidator.verify_c14_fact_lineage(snap_mismatch))


# ==============================================================================
# Contract C17: Stitched Fragments Preservation
# ==============================================================================
def test_contract_c17_stitched_fragments(base_doc):
    f1 = TableFragment("frag_p1", "p1", 1, 1)
    f2 = TableFragment("frag_p2", "p2", 1, 1)
    lt_ok = LogicalTable("tbl_stitched", ("frag_p1", "frag_p2"), is_stitched=True)
    snap_ok = CTIRSnapshot("snap_c17", document=base_doc, fragments=(f1, f2), logical_tables=(lt_ok,))
    assert len(CTIRValidator.verify_c17_stitched_fragments(snap_ok)) == 0

    # Negative: Stitched table references missing fragment
    lt_bad = LogicalTable("tbl_bad", ("frag_p1", "frag_nonexistent"), is_stitched=True)
    snap_bad = CTIRSnapshot("snap_c17_bad", document=base_doc, fragments=(f1,), logical_tables=(lt_bad,))
    assert any(d.code == "STITCHED_MISSING_FRAGMENTS" for d in CTIRValidator.verify_c17_stitched_fragments(snap_bad))


# ==============================================================================
# Contract C19: Bounded & Missing Value Grounding
# ==============================================================================
def test_contract_c19_bounded_and_missing(base_doc, valid_fact_bundle):
    coord = FactCoordinates("e0", "Corp", "m0", "Rev", (), ("2026",), InstantPeriod(datetime.date(2026, 9, 30)))
    unit = UnitAssertion()

    # Positive: Valid MissingValue and BoundedNumeric
    f_missing = SourceFact("f_m", "c1", coord, MissingValue("—", MissingReason.NIL_DASH), unit, "[NIL_DASH]", valid_fact_bundle)
    f_bound = SourceFact("f_b", "c2", coord, BoundedNumeric("< 0.05", Decimal("0.05"), BoundOperator.LT), unit, "<0.05", valid_fact_bundle)
    snap_ok = CTIRSnapshot("snap_c19", document=base_doc, source_facts={"f_m": f_missing, "f_b": f_bound})
    assert len(CTIRValidator.verify_c19_bounded_and_missing(snap_ok)) == 0

    # Negative: MissingValue without reason
    f_null_reason = SourceFact("f_nr", "c1", coord, MissingValue("—", None), unit, "[NULL]", valid_fact_bundle) # type: ignore
    snap_bad = CTIRSnapshot("snap_c19_bad", document=base_doc, source_facts={"f_nr": f_null_reason})
    assert any(d.code == "MISSING_VALUE_NULL_REASON" for d in CTIRValidator.verify_c19_bounded_and_missing(snap_bad))


# ==============================================================================
# Contract C20: Gate Authority & Promotion
# ==============================================================================
def test_contract_c20_gate_authority(base_doc, valid_fact_bundle):
    coord = FactCoordinates("e0", "Corp", "m0", "Rev", (), ("2026",), InstantPeriod(datetime.date(2026, 9, 30)))
    unit = UnitAssertion()

    # Negative: Prematurely promoted fact in unverified snapshot
    premature_fact = SourceFact(
        "f_premature", "c1", coord, ExactNumeric("10", Decimal("10")), unit, "10",
        valid_fact_bundle, verification_state=ValidationStatus.PASS # Premature!
    )
    snap_unverified = CTIRSnapshot("snap_premature", document=base_doc, source_facts={"f_premature": premature_fact}, validation_report=None)
    diags = CTIRValidator.verify_c20_gate_authority(snap_unverified)
    assert any(d.code == "VALIDATION_PREMATURE_PROMOTION" for d in diags)


# ==============================================================================
# Contract C15: Canonical Serialization Invariance
# ==============================================================================
def test_contract_c15_canonical_serialization(base_doc, base_space):
    snap = CTIRSnapshot("snap_c15", document=base_doc, coordinate_spaces=(base_space,))
    json_str = serialize_ctir_to_json(snap)
    assert "CTIR" in json_str
    assert base_doc.document_id in json_str
    assert "SPACE_01" in json_str


# ==============================================================================
# Contract C16: Deterministic Compilation Invariance
# ==============================================================================
def test_contract_c16_deterministic_compilation():
    schedule_path = DATA_DIR / "sec_10k_adversarial_schedule.txt"
    with open(schedule_path, "r", encoding="utf-8") as f:
        content = f.read()

    doc1, _ = BaseTableAdapter.create_source_document("doc1", content, "text/plain")
    doc2, _ = BaseTableAdapter.create_source_document("doc1", content, "text/plain")
    adapter = AsciiTableScheduleAdapter()

    f1, fn1, cs1 = adapter.parse(doc1, content)
    f2, fn2, cs2 = adapter.parse(doc2, content)

    comp = TableCompiler()
    s1 = comp.compile(doc1, f1, fn1, "Entity", "snap_det_1", cs1)
    s2 = comp.compile(doc2, f2, fn2, "Entity", "snap_det_1", cs2)

    assert len(s1.source_facts) == len(s2.source_facts)
    for fid in s1.source_facts:
        assert s1.source_facts[fid].canonical_display == s2.source_facts[fid].canonical_display


# ==============================================================================
# Contract C18: Reference Graph & Footnote Soundness
# ==============================================================================
def test_contract_c18_reference_graph(base_doc):
    c1 = CellNode("c1", CellRole.DATA, GridSpan(0, 1, 0, 1), "10", None, SourceRef(base_doc.sha256, "0", "0", "c1"), footnote_ids=("1",))
    # Unresolved citation: cites "1", but evidence anchors has no footnote 1
    snap_unresolved = CTIRSnapshot("snap_c18", document=base_doc, cells={"c1": c1})
    diags = CTIRValidator.verify_c18_reference_graph(snap_unresolved)
    assert any(d.code == "REFERENCE_UNRESOLVED_NOTE" for d in diags)


# ==============================================================================
# End-to-End Validator Tri-State Evaluation: Verify(CTIR) in {PASS, FAIL, UNRESOLVED}
# ==============================================================================
def test_end_to_end_tristate_validator_evaluation():
    schedule_path = DATA_DIR / "sec_10k_adversarial_schedule.txt"
    with open(schedule_path, "r", encoding="utf-8") as f:
        content = f.read()

    doc, _ = BaseTableAdapter.create_source_document("doc_sec_tristate", content, "text/plain")
    adapter = AsciiTableScheduleAdapter()
    frag, footnotes, coord_space = adapter.parse(doc, content, table_id="t_tristate")

    compiler = TableCompiler()
    snapshot = compiler.compile(
        source_doc=doc,
        fragment=frag,
        footnotes=footnotes,
        entity_name="Chronos Technologies Group Inc.",
        snapshot_id="snap_tristate_eval",
        coordinate_space=coord_space,
    )

    # 1. Full Conforming Snapshot must strictly evaluate to PASS
    assert snapshot.validation_report is not None
    assert snapshot.validation_report.overall_status == ValidationStatus.PASS
    # Facts promoted to PASS
    assert all(f.verification_state == ValidationStatus.PASS for f in snapshot.source_facts.values())

    # 2. Corrupted snapshot must strictly evaluate to FAIL
    bad_doc = SourceDocument("bad_doc", "corrupted_hash", "text/plain", 100)
    corrupted_snapshot = CTIRSnapshot(
        snapshot_id="snap_corrupted",
        document=bad_doc,
        coordinate_spaces=snapshot.coordinate_spaces,
        source_facts=snapshot.source_facts,
    )
    fail_report = CTIRValidator.validate_snapshot(corrupted_snapshot)
    assert fail_report.overall_status == ValidationStatus.FAIL
