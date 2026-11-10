"""
PCC-Tensor 3.1: Mathematical & Structural Invariant Verification Test Suite.
Verifies all type systems, interval temporal operators, DAG cycle detectors,
and Evidence Closure Certificate forward-replay proofs.
"""

import datetime
from decimal import Decimal
import pytest

from my_research.src.model import (
    DECIMAL_CONTEXT,
    parse_exact_decimal,
    ExactNumeric,
    BoundedNumeric,
    NumericRange,
    MissingValue,
    BoundOperator,
    MissingReason,
    DocumentConventionProfile,
    DurationPeriod,
    InstantPeriod,
    TemporalRelation,
    evaluate_temporal_relation,
    ProvenanceAnchor,
    MultiSourceProvenanceBundle,
    UnitAssertion,
    EntityCoordinate,
    MetricCoordinate,
    BalanceType,
    STESFact,
    HeaderNode,
    LogicalColumn,
    LogicalRow,
    CellNode,
    FootnoteNode,
    StructuralGraph,
)

from my_research.src.model.ecc import (
    EvidenceClosureCertificate,
    TransformationStep,
    CryptoSignaturePayload,
    FormalProofVerifier,
    VerificationVerdict,
)


def test_exact_decimal_arithmetic():
    """Verifies that Decimal arithmetic maintains exact 28-precision without floating-point drift."""
    d1 = parse_exact_decimal("158.20")
    d2 = parse_exact_decimal("-158.20")
    assert d1 + d2 == Decimal("0.00")
    assert isinstance(d1, Decimal)
    # Check Banker's rounding context
    with pytest.raises(Exception):
        ExactNumeric(raw_text="100", value=100.0)  # Must reject float


def test_value_lattice_tagged_union():
    """Verifies that bounded numbers and missing values maintain distinct semantic types."""
    exact = ExactNumeric(raw_text="274.80", value=Decimal("274.80"))
    assert exact.value == Decimal("274.80")

    bounded = BoundedNumeric(raw_text="<0.01", bound=Decimal("0.01"), operator=BoundOperator.LT)
    assert bounded.bound == Decimal("0.01")
    assert bounded.operator == BoundOperator.LT

    missing = MissingValue(raw_text="—", reason=MissingReason.NIL_DASH)
    assert missing.reason == MissingReason.NIL_DASH


def test_temporal_interval_algebra():
    """Verifies that Duration(3M) and Duration(9M) correctly yield CONTAINED_BY, fixing the false-disjointness bug."""
    p_3m = DurationPeriod(
        start_date=datetime.date(2026, 7, 1),
        end_date=datetime.date(2026, 9, 30),
        fiscal_quarter=3,
        fiscal_year=2026,
    )
    p_9m = DurationPeriod(
        start_date=datetime.date(2026, 1, 1),
        end_date=datetime.date(2026, 9, 30),
        fiscal_year=2026,
    )

    # 3-Month period is contained within the 9-Month period
    rel_3m_in_9m = evaluate_temporal_relation(p_3m, p_9m)
    assert rel_3m_in_9m == TemporalRelation.CONTAINED_BY

    # 9-Month period contains the 3-Month period
    rel_9m_contains_3m = evaluate_temporal_relation(p_9m, p_3m)
    assert rel_9m_contains_3m == TemporalRelation.CONTAINS


def test_unit_assertion_arbitrary_exponents():
    """Verifies arbitrary integer scale exponents including negative powers (cents/percentages)."""
    # Standard $ Millions (s = 6)
    unit_millions = UnitAssertion(currency="USD", scale_exponent=6)
    assert unit_millions.scale_multiplier == Decimal("1000000")

    # iXBRL Cents (s = -2 -> 0.01)
    unit_cents = UnitAssertion(currency="USD", scale_exponent=-2)
    assert unit_cents.scale_multiplier == Decimal("0.01")


def test_canonical_ir_dag_validation():
    """Verifies that structural hierarchy enforces an acyclic DAG and catches cyclic headers."""
    graph = StructuralGraph()

    # Add valid headers: Level 1 -> Level 2
    h1 = HeaderNode(header_id="H_ROOT", label="Three Months", level=1, col_start=0, col_end=2)
    h2 = HeaderNode(header_id="H_SUB", label="2026", level=2, col_start=0, col_end=1, parent_header_id="H_ROOT")
    graph.add_header(h1)
    graph.add_header(h2)

    is_dag, err = graph.validate_acyclic_dag()
    assert is_dag is True

    # Inject circular reference: H_ROOT -> H_SUB and H_SUB -> H_ROOT
    h1_bad = HeaderNode(header_id="H_ROOT", label="Three Months", level=1, col_start=0, col_end=2, parent_header_id="H_SUB")
    graph.headers["H_ROOT"] = h1_bad

    is_dag_bad, err_bad = graph.validate_acyclic_dag()
    assert is_dag_bad is False
    assert "cycle detected" in err_bad.lower()


def test_evidence_closure_certificate_forward_replay():
    """Verifies Evidence Closure Certificate forward-replay verification."""
    prov_val = ProvenanceAnchor(
        doc_sha256="4a7d1ed414474e4033ac29ccb8653d9b",
        page_id=1,
        bbox_pts=(145.2, 580.4, 210.8, 592.1),
        raw_text="(158.20)",
        evidence_role="VALUE",
    )
    bundle = MultiSourceProvenanceBundle(value_anchor=prov_val)

    entity = EntityCoordinate(canonical_id="CHRONOS", display_name="Chronos Technologies")
    metric = MetricCoordinate(canonical_id="OP_LOSS", raw_label="Operating Loss")
    temporal = DurationPeriod(start_date=datetime.date(2026, 7, 1), end_date=datetime.date(2026, 9, 30))
    typed_val = ExactNumeric(raw_text="(158.20)", value=Decimal("-158.20"))
    unit = UnitAssertion(currency="USD", scale_exponent=6)

    fact = STESFact(
        fact_id="F_001",
        entity=entity,
        metric=metric,
        temporal=temporal,
        typed_value=typed_val,
        unit=unit,
        provenance=bundle,
    )

    cert = EvidenceClosureCertificate(
        certificate_id="CERT_001",
        fact_id="F_001",
        provenance_bundle=bundle,
        fact=fact,
    )

    verdict, failures = FormalProofVerifier.verify_fact_certificate(cert)
    assert verdict == VerificationVerdict.PASS
    assert len(failures) == 0
    assert fact.canonical_display_value == "USD -158,200,000.00"

