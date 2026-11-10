"""
PCC-Tensor 3.2: Verification Trust Boundary Hardening Tests (T01 - T06).
Tests the formal verification trust boundary:
- T01: Forged transformation output must be rejected.
- T02: Broken transformation chain must be rejected.
- T03: DerivedFact cannot be prematurely promoted to PASS before verification.
- T04: Three-state preservation: UNRESOLVED must never automatically become FAIL or PASS.
- T05: Failed snapshot must reject query retrieval.
- T06: Individual UNRESOLVED fact cannot be returned as a verified answer.
"""

from __future__ import annotations

import datetime
from decimal import Decimal
import pytest

from my_research.src.compiler.table_compiler import TableCompiler
from my_research.src.model.ctir import (
    CTIRSnapshot,
    DerivedFact,
    FactCoordinates,
    SourceFact,
    ValidationDiagnostic,
    ValidationReport,
    ValidationStatus,
)
from my_research.src.model.evidence import (
    EvidenceAnchor,
    EvidenceRole,
    MultiSourceProvenanceBundle,
    TransformationRecord,
)
from my_research.src.model.semantic import UnitAssertion
from my_research.src.model.source import SourceDocument, SourceRef
from my_research.src.model.structural import CellNode, CellRole, GridSpan, TableFragment
from my_research.src.model.temporal import InstantPeriod
from my_research.src.model.value import ExactNumeric
from my_research.src.query.engine import CTIRQueryEngine
from my_research.src.verifier.validate import CTIRValidator


@pytest.fixture
def base_doc() -> SourceDocument:
    return SourceDocument(
        document_id="DOC_TRUST_01",
        sha256="b" * 64,
        mime_type="text/plain",
        byte_length=512,
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
# T01: Forged transformation output must be rejected
# ==============================================================================
def test_t01_forged_transformation_rejected(base_doc, valid_fact_bundle):
    """
    T01: Altering a transformation output must be rejected by independent execution.
    An attacker creates a fake record claiming 'WHATEVER' transforms to '1000000',
    setting replayed_successfully=True. The verifier must independently execute
    the rule, detect the forgery, and reject it.
    """
    coord = FactCoordinates("e0", "Corp", "m0", "Rev", (), ("2026",), InstantPeriod(datetime.date(2026, 9, 30)))
    unit = UnitAssertion(currency="USD", scale_exponent=0)

    # Forged transformation: claim strip_whitespace("WHATEVER") produces "1000000" with replayed_successfully=True
    tx_forged = TransformationRecord(
        transformation_id="tx_fake",
        rule_name="strip_whitespace",
        input_raw="WHATEVER",
        output_result="1000000",
        replayed_successfully=True,
    )
    fact_forged = SourceFact(
        "f_forged", "c1", coord, ExactNumeric("WHATEVER", Decimal("1000000")), unit, "1000000",
        valid_fact_bundle, ValidationStatus.UNRESOLVED, (tx_forged,)
    )
    snapshot = CTIRSnapshot("snap_forged", document=base_doc, source_facts={"f_forged": fact_forged})

    diags = CTIRValidator.verify_c8_raw_value_preservation(snapshot)
    assert any(
        d.code in ("TRANSFORMATION_REPLAY_MISMATCH", "FORGED_TRANSFORMATION", "TRANSFORMATION_EXECUTION_FAILURE")
        for d in diags
    ), "Validator trusted replayed_successfully=True without executing the transformation rule!"


# ==============================================================================
# T02: Broken transformation chain must be rejected
# ==============================================================================
def test_t02_broken_transformation_chain_rejected(base_doc, valid_fact_bundle):
    """
    T02: An operation whose input doesn't match the previous output must be rejected.
    Chain:
      tx1 output = '(158.20)'
      tx2 input = 'DIFFERENT_INPUT' -> Discontinuous chain!
    """
    coord = FactCoordinates("e0", "Corp", "m0", "Rev", (), ("2026",), InstantPeriod(datetime.date(2026, 9, 30)))
    unit = UnitAssertion(currency="USD", scale_exponent=0)

    tx1 = TransformationRecord("tx_1", "strip_whitespace", " (158.20) ", "(158.20)", True)
    # tx2's input does NOT match tx1's output!
    tx2 = TransformationRecord("tx_2", "parentheses_to_negative_decimal", "DIFFERENT_INPUT", "-158.20", True)

    fact_broken = SourceFact(
        "f_broken", "c1", coord, ExactNumeric(" (158.20) ", Decimal("-158.20")), unit, "-158.20",
        valid_fact_bundle, ValidationStatus.UNRESOLVED, (tx1, tx2)
    )
    snapshot = CTIRSnapshot("snap_broken", document=base_doc, source_facts={"f_broken": fact_broken})

    diags = CTIRValidator.verify_c8_raw_value_preservation(snapshot)
    assert any(
        d.code in ("TRANSFORMATION_CHAIN_BROKEN", "TRANSFORMATION_REPLAY_MISMATCH")
        for d in diags
    ), "Validator accepted discontinuous transformation chain where tx[i].input_raw != tx[i-1].output_result!"


# ==============================================================================
# T03: Premature derived PASS must be rejected
# ==============================================================================
def test_t03_premature_derived_pass_rejected(base_doc, valid_fact_bundle):
    """
    T03: A derived fact cannot start as PASS in an unverified snapshot.
    Contract C20 must inspect DerivedFact as well as SourceFact.
    """
    coord = FactCoordinates("e0", "Corp", "m0", "Rev", (), ("2026",), InstantPeriod(datetime.date(2026, 9, 30)))
    unit = UnitAssertion(currency="USD", scale_exponent=0)

    # Derived fact prematurely marked PASS without a validation report
    premature_derived = DerivedFact(
        fact_id="df_premature",
        expression_name="ADD_OUTFLOW",
        input_fact_ids=("f1", "f2"),
        result_value=ExactNumeric("40.00", Decimal("40.00")),
        unit=unit,
        canonical_display="40.00",
        execution_engine="DECIMAL_KERNEL",
        verification_state=ValidationStatus.PASS,  # Premature!
    )
    snapshot = CTIRSnapshot(
        "snap_premature_df",
        document=base_doc,
        derived_facts={"df_premature": premature_derived},
        validation_report=None,
    )

    diags = CTIRValidator.verify_c20_gate_authority(snapshot)
    assert any(
        d.code == "VALIDATION_PREMATURE_PROMOTION" and d.target_id == "df_premature"
        for d in diags
    ), "Contract C20 ignored premature promotion on DerivedFact!"


# ==============================================================================
# T04: Three-state preservation: UNRESOLVED must never become FAIL or PASS
# ==============================================================================
def test_t04_three_state_preservation(base_doc, valid_fact_bundle):
    """
    T04: An UNRESOLVED snapshot must leave facts as UNRESOLVED, not convert them to FAIL.
    """
    coord = FactCoordinates("e0", "Corp", "m0", "Rev", (), ("2026",), None)  # Missing temporal -> UNRESOLVED
    unit = UnitAssertion(currency="USD", scale_exponent=0)

    # Fact with missing temporal coordinate triggers a WARNING diagnostic -> UNRESOLVED report
    fact_unres = SourceFact(
        "f_unres", "c1", coord, ExactNumeric("100.00", Decimal("100.00")), unit, "100.00",
        valid_fact_bundle, ValidationStatus.UNRESOLVED
    )
    c1 = CellNode("c1", CellRole.DATA, GridSpan(0, 1, 0, 1), "100.00", None, SourceRef(base_doc.sha256, "0", "0", "c1"))
    frag = TableFragment("frag_1", "p0", 1, 1, cells=(c1,))

    compiler = TableCompiler()
    snapshot = compiler.compile(
        source_doc=base_doc,
        fragment=frag,
        footnotes=[],
        entity_name="Test Corp",
        snapshot_id="snap_t04_three_state",
    )

    # If the snapshot report is UNRESOLVED, the fact state MUST be UNRESOLVED, not FAIL or PASS
    assert snapshot.validation_report is not None
    assert snapshot.validation_report.overall_status == ValidationStatus.UNRESOLVED, (
        f"Expected UNRESOLVED report for missing temporal, got {snapshot.validation_report.overall_status}"
    )
    fact = snapshot.source_facts.get("f_unres") or next(iter(snapshot.source_facts.values()))
    assert fact.verification_state == ValidationStatus.UNRESOLVED, (
        f"Three-state violation: UNRESOLVED status was coerced to {fact.verification_state}!"
    )


# ==============================================================================
# T05: Failed snapshot must reject query retrieval
# ==============================================================================
def test_t05_failed_snapshot_retrieval_rejected(base_doc, valid_fact_bundle):
    """
    T05: A snapshot with FAIL status cannot return factual answers from CTIRQueryEngine.
    """
    coord = FactCoordinates("e0", "Corp", "m0", "Revenue", (), ("2026",), InstantPeriod(datetime.date(2026, 9, 30)))
    unit = UnitAssertion(currency="USD", scale_exponent=6)
    fact = SourceFact(
        "f_rev", "c1", coord, ExactNumeric("100.00", Decimal("100.00")), unit, "USD 100,000,000.00",
        valid_fact_bundle, ValidationStatus.PASS
    )

    # Snapshot with FAIL validation report
    failed_report = ValidationReport(
        schema_status=ValidationStatus.FAIL,
        diagnostics=(ValidationDiagnostic(code="TEST_FAIL", target_id="f_rev", severity="ERROR", message="Fatal"),),
    )
    failed_snapshot = CTIRSnapshot(
        "snap_failed",
        document=base_doc,
        source_facts={"f_rev": fact},
        validation_report=failed_report,
    )

    engine = CTIRQueryEngine(failed_snapshot)
    results = engine.query("What was the Revenue?")

    assert len(results) == 0, (
        f"Retrieval trust boundary breached! Query engine returned {len(results)} answers from a FAIL snapshot: {results}"
    )


# ==============================================================================
# T06: Individual UNRESOLVED fact cannot be returned as a verified answer
# ==============================================================================
def test_t06_unverified_fact_retrieval_rejected(base_doc, valid_fact_bundle):
    """
    T06: An individual UNRESOLVED fact cannot be returned as a verified answer.
    """
    coord = FactCoordinates("e0", "Corp", "m0", "Revenue", (), ("2026",), InstantPeriod(datetime.date(2026, 9, 30)))
    unit = UnitAssertion(currency="USD", scale_exponent=6)

    # Fact explicitly in UNRESOLVED state
    unresolved_fact = SourceFact(
        "f_unverified", "c1", coord, ExactNumeric("100.00", Decimal("100.00")), unit, "USD 100,000,000.00",
        valid_fact_bundle, verification_state=ValidationStatus.UNRESOLVED  # Unverified!
    )
    passing_report = ValidationReport()
    snapshot = CTIRSnapshot(
        "snap_unverified",
        document=base_doc,
        source_facts={"f_unverified": unresolved_fact},
        validation_report=passing_report,
    )

    engine = CTIRQueryEngine(snapshot)
    results = engine.query("What was the Revenue?")

    assert len(results) == 0, (
        f"Retrieval trust boundary breached! Query engine returned UNRESOLVED fact as verified answer: {results}"
    )
