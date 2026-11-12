"""
PCC-Tensor 3.2: Adversarial Contract Boundary Attack Suite.
Ten rigorous adversarial attacks designed to discover whether the compiler,
validator, and retrieval engine can be fooled by forged proofs, broken chains,
silent status coercions, serialization gaps, or unverified claims.

Cases:
 1. Forged replay-success flag
 2. Broken transformation chain
 3. Derived fact without verified lineage
 4. UNRESOLVED status never silently promoted
 5. Failed snapshot retrieval admission enforcement
 6. Incomplete serialization round-trip gap
 7. Chunk exceeding token budget & hardcoded ECC flags
 8. Missing unit declaration (silent USD default trap)
 9. Ambiguous currency / math parsing preservation
10. Forged document signature (hash vs. signature authenticity)
"""

from __future__ import annotations

import datetime
from decimal import Decimal
import pytest

from my_research.src.compiler.table_compiler import TableCompiler
from my_research.src.compiler.scope_resolver import ScopeResolver
from my_research.src.compiler.value_normalizer import ValueNormalizer
from my_research.src.chunker.relation_preserving_chunker import (
    ChunkBudgetExceededError,
    RelationPreservingTableChunker,
)
from my_research.src.model.ctir import (
    CTIRSnapshot,
    DerivedFact,
    FactCoordinates,
    SourceFact,
    ValidationDiagnostic,
    ValidationReport,
    ValidationStatus,
)
from my_research.src.model.ecc import (
    CryptoSignaturePayload,
    EvidenceClosureCertificate,
    FormalProofVerifier,
    VerificationVerdict,
)
from my_research.src.model.evidence import (
    EvidenceAnchor,
    EvidenceRole,
    MultiSourceProvenanceBundle,
    TransformationRecord,
    verify_transformation_chain,
)
from my_research.src.model.semantic import ResolutionStatus, ScopeConflictResolver, ScopeLevel, UnitAssertion
from my_research.src.model.source import SourceDocument, SourceRef
from my_research.src.model.structural import (
    CellNode,
    CellRole,
    GridSpan,
    LogicalColumn,
    LogicalRow,
    TableFragment,
)
from my_research.src.model.temporal import DurationPeriod, InstantPeriod
from my_research.src.model.value import (
    BoundOperator,
    BoundedNumeric,
    ExactNumeric,
    MissingReason,
    MissingValue,
    parse_exact_decimal,
)
from my_research.src.query.engine import CTIRQueryEngine
from my_research.src.storage.serialize import serialize_ctir_to_json
from my_research.src.verifier.validate import CTIRValidator


@pytest.fixture
def base_doc() -> SourceDocument:
    return SourceDocument(
        document_id="DOC_ADV_01",
        sha256="a" * 64,
        mime_type="text/plain",
        byte_length=1024,
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
# Case 1: Forged replay-success flag
# Attack: Forged transformation record claiming success without executing valid rule.
# Expected: Reject with TRANSFORMATION_RULE_UNREGISTERED or TRANSFORMATION_REPLAY_MISMATCH.
# ==============================================================================
def test_adv01_forged_replay_success_flag(base_doc, valid_fact_bundle):
    coord = FactCoordinates("e0", "Corp", "m0", "Rev", (), ("2026",), InstantPeriod(datetime.date(2026, 9, 30)))
    unit = UnitAssertion(currency="USD", scale_exponent=0)

    # Attack 1A: Non-existent rule name
    tx_fake_rule = TransformationRecord(
        transformation_id="tx_fake_rule",
        rule_name="invent_millions",
        input_raw="(158.20)",
        output_result="-158.20",
        replayed_successfully=True,  # Forged flag!
    )
    fact_fake_rule = SourceFact(
        "f_fake_rule", "c1", coord, ExactNumeric("(158.20)", Decimal("-158.20")), unit, "-158.20",
        valid_fact_bundle, ValidationStatus.UNRESOLVED, (tx_fake_rule,)
    )
    snap_fake_rule = CTIRSnapshot("snap_fake_rule", document=base_doc, source_facts={"f1": fact_fake_rule})
    diags_rule = CTIRValidator.verify_c8_raw_value_preservation(snap_fake_rule)
    assert any(d.code in ("TRANSFORMATION_RULE_UNREGISTERED", "TRANSFORMATION_REPLAY_MISMATCH") for d in diags_rule), (
        "Security gap: Validator accepted unregistered transformation rule because replayed_successfully=True!"
    )

    # Attack 1B: Valid rule name, but fabricated output (strip_whitespace claims to turn 100 into 999)
    tx_forged_out = TransformationRecord(
        transformation_id="tx_forged_out",
        rule_name="strip_whitespace",
        input_raw=" 100.00 ",
        output_result="999.00",  # Fabricated output!
        replayed_successfully=True,  # Forged flag!
    )
    fact_forged_out = SourceFact(
        "f_forged_out", "c2", coord, ExactNumeric(" 100.00 ", Decimal("999.00")), unit, "999.00",
        valid_fact_bundle, ValidationStatus.UNRESOLVED, (tx_forged_out,)
    )
    snap_forged_out = CTIRSnapshot("snap_forged_out", document=base_doc, source_facts={"f2": fact_forged_out})
    diags_out = CTIRValidator.verify_c8_raw_value_preservation(snap_forged_out)
    assert any(d.code == "TRANSFORMATION_REPLAY_MISMATCH" for d in diags_out), (
        "Security gap: Validator trusted replayed_successfully=True instead of executing strip_whitespace!"
    )


# ==============================================================================
# Case 2: Broken transformation chain
# Attack: Multi-step chain with discontinuous intermediate inputs.
# Expected: Reject with TRANSFORMATION_CHAIN_BROKEN.
# ==============================================================================
def test_adv02_broken_transformation_chain(base_doc, valid_fact_bundle):
    coord = FactCoordinates("e0", "Corp", "m0", "Rev", (), ("2026",), InstantPeriod(datetime.date(2026, 9, 30)))
    unit = UnitAssertion(currency="USD", scale_exponent=0)

    # tx1 outputs '(158.20)', but tx2 inputs 'DIFFERENT_INPUT'
    tx1 = TransformationRecord("tx_1", "strip_whitespace", " (158.20) ", "(158.20)", True)
    tx2 = TransformationRecord("tx_2", "parentheses_to_negative_decimal", "DIFFERENT_INPUT", "-158.20", True)

    fact_broken = SourceFact(
        "f_broken", "c1", coord, ExactNumeric(" (158.20) ", Decimal("-158.20")), unit, "-158.20",
        valid_fact_bundle, ValidationStatus.UNRESOLVED, (tx1, tx2)
    )
    snap_broken = CTIRSnapshot("snap_broken", document=base_doc, source_facts={"f_broken": fact_broken})

    diags = CTIRValidator.verify_c8_raw_value_preservation(snap_broken)
    assert any(d.code in ("TRANSFORMATION_CHAIN_BROKEN", "TRANSFORMATION_REPLAY_MISMATCH") for d in diags), (
        "Security gap: Validator accepted discontinuous transformation chain!"
    )


# ==============================================================================
# Case 3: Derived fact without verified lineage
# Attack: Derived facts with missing inputs, false arithmetic, failed inputs, or cycles.
# Expected: Never PASS; emit formal lineage error diagnostics.
# ==============================================================================
def test_adv03_derived_fact_without_verified_lineage(base_doc, valid_fact_bundle):
    coord = FactCoordinates("e0", "Corp", "m0", "Rev", (), ("2026",), InstantPeriod(datetime.date(2026, 9, 30)))
    unit = UnitAssertion(currency="USD", scale_exponent=6)

    f_rev = SourceFact("f_rev", "c1", coord, ExactNumeric("100.00", Decimal("100.00")), unit, "100.00", valid_fact_bundle)
    f_cogs = SourceFact("f_cogs", "c2", coord, ExactNumeric("-60.00", Decimal("-60.00")), unit, "-60.00", valid_fact_bundle)

    # Attack 3A: Premature PASS before validation
    df_premature = DerivedFact("df_prem", "ADD_OUTFLOW", ("f_rev", "f_cogs"), ExactNumeric("40.00", Decimal("40.00")), unit, "40.00", verification_state=ValidationStatus.PASS)
    snap_prem = CTIRSnapshot("snap_prem", document=base_doc, source_facts={"f_rev": f_rev, "f_cogs": f_cogs}, derived_facts={"df_prem": df_premature}, validation_report=None)
    diags_prem = CTIRValidator.verify_c20_gate_authority(snap_prem)
    assert any(d.code == "VALIDATION_PREMATURE_PROMOTION" for d in diags_prem), "Derived fact prematurely marked PASS bypassed C20!"

    # Attack 3B: Missing inputs
    df_ghost = DerivedFact("df_ghost", "ADD_OUTFLOW", ("f_rev", "f_nonexistent"), ExactNumeric("40.00", Decimal("40.00")), unit, "40.00")
    snap_ghost = CTIRSnapshot("snap_ghost", document=base_doc, source_facts={"f_rev": f_rev}, derived_facts={"df_ghost": df_ghost})
    diags_ghost = CTIRValidator.verify_c14_fact_lineage(snap_ghost)
    assert any(d.code == "DERIVED_MISSING_INPUT_FACT" for d in diags_ghost), "Derived fact with ghost inputs accepted by C14!"

    # Attack 3C: Arithmetic falsification (100 + (-60) claimed to be 999.00)
    df_false_math = DerivedFact("df_false", "ADD_OUTFLOW", ("f_rev", "f_cogs"), ExactNumeric("999.00", Decimal("999.00")), unit, "999.00")
    snap_math = CTIRSnapshot("snap_math", document=base_doc, source_facts={"f_rev": f_rev, "f_cogs": f_cogs}, derived_facts={"df_false": df_false_math})
    diags_math = CTIRValidator.verify_c14_fact_lineage(snap_math)
    assert any(d.code == "DERIVED_CALCULATION_MISMATCH" for d in diags_math), "Derived fact with falsified arithmetic accepted by C14!"

    # Attack 3D: Input has FAIL state
    f_failed = SourceFact("f_fail", "c3", coord, ExactNumeric("-60.00", Decimal("-60.00")), unit, "-60.00", valid_fact_bundle, verification_state=ValidationStatus.FAIL)
    df_on_fail = DerivedFact("df_bad_in", "ADD_OUTFLOW", ("f_rev", "f_fail"), ExactNumeric("40.00", Decimal("40.00")), unit, "40.00")
    snap_fail = CTIRSnapshot("snap_fail", document=base_doc, source_facts={"f_rev": f_rev, "f_fail": f_failed}, derived_facts={"df_bad_in": df_on_fail})
    diags_fail = CTIRValidator.verify_c14_fact_lineage(snap_fail)
    assert any(d.code == "DERIVED_INPUT_FAILED" for d in diags_fail), "Derived fact accepted even though input fact had FAIL state!"

    # Attack 3E: Lineage circular dependency
    df_cyc1 = DerivedFact("df_c1", "SUM", ("f_rev", "df_c2"), ExactNumeric("100.00", Decimal("100.00")), unit, "100.00")
    df_cyc2 = DerivedFact("df_c2", "SUM", ("df_c1",), ExactNumeric("100.00", Decimal("100.00")), unit, "100.00")
    snap_cyc = CTIRSnapshot("snap_cyc", document=base_doc, source_facts={"f_rev": f_rev}, derived_facts={"df_c1": df_cyc1, "df_c2": df_cyc2})
    diags_cyc = CTIRValidator.verify_c14_fact_lineage(snap_cyc)
    assert any(d.code == "DERIVED_LINEAGE_CYCLE" for d in diags_cyc), "Cyclic derived fact dependency accepted by C14!"


# ==============================================================================
# Case 4: UNRESOLVED status never silently promotes
# Attack: Feed an ungrounded temporal header that emits WARNING.
# Expected: Snapshot overall_status is UNRESOLVED, and facts remain UNRESOLVED (neither PASS nor FAIL).
# ==============================================================================
def test_adv04_unresolved_status_never_silently_promotes(base_doc):
    r0 = LogicalRow("ROW_000", 0, None, "DETAIL", "Operating Loss", 0, ())
    col0 = LogicalColumn("COL_00", 0, ("Line Item",), role="ROW_HEADER")
    col1 = LogicalColumn("COL_01", 1, ("Undated Column Header",))  # No date -> temporal unresolved!

    c_stub = CellNode("c_stub", CellRole.ROW_HEADER, GridSpan(0, 1, 0, 1), "Operating Loss", None, SourceRef(base_doc.sha256, "0", "0", "c_stub"))
    c_val = CellNode("c_val", CellRole.DATA, GridSpan(0, 1, 1, 2), "(158.20)", None, SourceRef(base_doc.sha256, "0", "0", "c_val"))
    frag = TableFragment("frag_unres", "p0", 1, 2, cells=(c_stub, c_val), rows=(r0,), columns=(col0, col1))

    compiler = TableCompiler()
    snapshot = compiler.compile(
        source_doc=base_doc,
        fragment=frag,
        footnotes=[],
        entity_name="Adversarial Corp",
        snapshot_id="snap_adv04",
    )

    assert snapshot.validation_report is not None
    assert snapshot.validation_report.overall_status == ValidationStatus.UNRESOLVED, (
        f"Expected overall UNRESOLVED status, got {snapshot.validation_report.overall_status}"
    )
    for fact in snapshot.source_facts.values():
        assert fact.verification_state == ValidationStatus.UNRESOLVED, (
            f"Tri-state violation! UNRESOLVED status was coerced to {fact.verification_state}"
        )


# ==============================================================================
# Case 5: Failed snapshot retrieval admission enforcement
# Attack: Query a snapshot with FAIL or UNRESOLVED state, or query unverified facts.
# Expected: Query engine must return [] (zero answers).
# ==============================================================================
def test_adv05_failed_snapshot_retrieval_admission_enforcement(base_doc, valid_fact_bundle):
    coord = FactCoordinates("e0", "Corp", "m0", "Revenue", (), ("2026",), InstantPeriod(datetime.date(2026, 9, 30)))
    unit = UnitAssertion(currency="USD", scale_exponent=6)
    fact_pass = SourceFact("f_rev", "c1", coord, ExactNumeric("100.00", Decimal("100.00")), unit, "USD 100M", valid_fact_bundle, ValidationStatus.PASS)

    # Attack 5A: Snapshot is FAIL
    fail_report = ValidationReport(schema_status=ValidationStatus.FAIL, diagnostics=(ValidationDiagnostic("ERR", "c1", "ERROR", "Fatal"),))
    snap_fail = CTIRSnapshot("snap_f", document=base_doc, source_facts={"f_rev": fact_pass}, validation_report=fail_report)
    engine_fail = CTIRQueryEngine(snap_fail)
    assert len(engine_fail.query("What was Revenue?")) == 0, "Query engine returned answers from a FAIL snapshot!"

    # Attack 5B: Snapshot has no validation report (unvalidated)
    snap_none = CTIRSnapshot("snap_n", document=base_doc, source_facts={"f_rev": fact_pass}, validation_report=None)
    engine_none = CTIRQueryEngine(snap_none)
    assert len(engine_none.query("What was Revenue?")) == 0, "Query engine returned answers from unvalidated snapshot!"

    # Attack 5C: Passing snapshot, but fact is UNRESOLVED
    fact_unres = SourceFact("f_unres", "c1", coord, ExactNumeric("100.00", Decimal("100.00")), unit, "USD 100M", valid_fact_bundle, ValidationStatus.UNRESOLVED)
    pass_report = ValidationReport(
        schema_status=ValidationStatus.PASS, source_status=ValidationStatus.PASS,
        geometry_status=ValidationStatus.PASS, structure_status=ValidationStatus.PASS,
        semantics_status=ValidationStatus.PASS, relationships_status=ValidationStatus.PASS,
        provenance_status=ValidationStatus.PASS, lineage_status=ValidationStatus.PASS,
        serialization_status=ValidationStatus.PASS,
    )
    snap_fact_unres = CTIRSnapshot("snap_u", document=base_doc, source_facts={"f_unres": fact_unres}, validation_report=pass_report)
    engine_unres = CTIRQueryEngine(snap_fact_unres)
    assert len(engine_unres.query("What was Revenue?")) == 0, "Query engine returned unverified fact from passing snapshot!"


# ==============================================================================
# Case 6: Incomplete serialization: Round-trip verification audit
# Attack: Test whether serialization establishes Deserialize(Serialize(CTIR)) == CTIR.
# Expected: Verify that serialization preserves all factual contents and round-trips losslessly.
# ==============================================================================
def test_adv06_incomplete_serialization_round_trip(base_doc, valid_fact_bundle):
    coord = FactCoordinates("e0", "Corp", "m0", "Revenue", (), ("2026",), InstantPeriod(datetime.date(2026, 9, 30)))
    unit = UnitAssertion(currency="USD", scale_exponent=6)
    fact = SourceFact("f1", "c1", coord, ExactNumeric("100.00", Decimal("100.00")), unit, "100.00", valid_fact_bundle)
    df = DerivedFact("df1", "ADD_OUTFLOW", ("f1",), ExactNumeric("100.00", Decimal("100.00")), unit, "100.00")

    snapshot = CTIRSnapshot(
        snapshot_id="snap_c15_audit",
        document=base_doc,
        source_facts={"f1": fact},
        derived_facts={"df1": df},
    )

    from my_research.src.storage.serialize import deserialize_ctir_from_json, serialize_ctir_to_json
    json_str = serialize_ctir_to_json(snapshot)
    import json
    data = json.loads(json_str)

    # Contract C15 check: Serialized payload MUST contain full source_facts and derived_facts
    assert "source_facts" in data, (
        "Security gap T06: serialize_ctir_to_json emits metadata summary (facts_count) but omits full source_facts dictionary!"
    )
    assert "derived_facts" in data, "Contract C15 failure: Serialized JSON omits derived_facts dictionary!"
    assert len(data["source_facts"]) == 1

    # Round-trip verification: Deserialize(Serialize(S)) == S
    reconstructed = deserialize_ctir_from_json(json_str)
    assert reconstructed.snapshot_id == snapshot.snapshot_id
    assert "f1" in reconstructed.source_facts
    rf = reconstructed.source_facts["f1"]
    assert rf.canonical_display == fact.canonical_display
    assert isinstance(rf.typed_value, ExactNumeric)
    assert rf.typed_value.value == Decimal("100.00")
    assert rf.coordinates.raw_metric_label == "Revenue"
    assert "df1" in reconstructed.derived_facts


# ==============================================================================
# Case 7: Chunk exceeding token budget & ECC hardcoded flags
# Attack: Create a row exceeding the 512 token budget, and disable coordinate closure.
# Expected: Chunker should not exceed configured budget, and ECC certificate flags
#           must NOT claim header closure when headers were disabled.
# ==============================================================================
def test_adv07_chunk_exceeding_token_budget_and_ecc_flags(base_doc, valid_fact_bundle):
    # Construct a snapshot with a massive row label that exceeds 512 tokens
    huge_label = "Very long financial descriptive metric line item " * 60  # ~3000 chars -> ~750 tokens
    coord = FactCoordinates("e0", "Corp", "m0", huge_label, (), ("2026",), InstantPeriod(datetime.date(2026, 9, 30)))
    unit = UnitAssertion(currency="USD", scale_exponent=6)

    fact = SourceFact("f_huge", "cell_r001_c01", coord, ExactNumeric("100.00", Decimal("100.00")), unit, "USD 100M", valid_fact_bundle)
    col0 = LogicalColumn("COL_00", 0, ("Line Item",), role="ROW_HEADER")
    col1 = LogicalColumn("COL_01", 1, ("2026",))

    snapshot = CTIRSnapshot(
        snapshot_id="snap_huge",
        document=base_doc,
        source_facts={"f_huge": fact},
        columns={"COL_00": col0, "COL_01": col1},
    )

    # Attack 7A: Run chunker with 512 budget on oversized row -> Must enforce budget!
    chunker = RelationPreservingTableChunker(token_budget=512, enable_coordinate_closure=False, enable_superheader_closure=False)
    with pytest.raises(ChunkBudgetExceededError):
        chunker.chunk_snapshot(snapshot)

    # Attack 7B: Check if ECC certificate claims header closure when header closure was disabled!
    coord_normal = FactCoordinates("e0", "Corp", "m0", "Revenue", (), ("2026",), InstantPeriod(datetime.date(2026, 9, 30)))
    fact_normal = SourceFact("f_norm", "cell_r001_c01", coord_normal, ExactNumeric("100.00", Decimal("100.00")), unit, "USD 100M", valid_fact_bundle)
    snapshot_normal = CTIRSnapshot(
        snapshot_id="snap_normal",
        document=base_doc,
        source_facts={"f_norm": fact_normal},
        columns={"COL_00": col0, "COL_01": col1},
    )
    chunker_no_headers = RelationPreservingTableChunker(token_budget=2048, enable_coordinate_closure=False, enable_superheader_closure=False)
    chunks = chunker_no_headers.chunk_snapshot(snapshot_normal)
    assert len(chunks) > 0
    ecc = chunks[0].certificate
    assert ecc.has_header_closure is False, (
        "Security gap T07: ECC certificate has hardcoded has_header_closure=True despite headers being disabled!"
    )
    assert ecc.has_unit_closure is False, (
        "Security gap T07: ECC certificate has hardcoded has_unit_closure=True despite coordinate closure disabled!"
    )


# ==============================================================================
# Case 8: Missing unit declaration: Silent USD default trap
# Attack: Input a generic table (e.g. Headcount: 8,420 or Temperature: 45) with NO currency declared.
# Expected: Does ScopeResolver silently assume USD millions? It must remain UNRESOLVED.
# ==============================================================================
def test_adv08_missing_unit_declaration_silent_default(base_doc):
    # A generic table reporting headcount or scientific quantities
    resolver_default = ScopeResolver()
    
    # Target assertion: ScopeResolver must not silently default to USD millions!
    assert resolver_default.table_default_unit is None, (
        "Vulnerability T08: ScopeResolver must not default to USD millions when no unit is declared!"
    )
    status, resolved, reason = ScopeConflictResolver.resolve_unit_assertions(
        cell_unit=None, row_unit=None, col_unit=None, table_unit=None
    )
    assert status == ResolutionStatus.UNRESOLVED, f"Expected UNRESOLVED, got {status}"
    assert resolved is None, f"Expected resolved unit to be None, got {resolved}"

    # Verify that an explicit unit with no currency passes without being forced to USD
    unit_headcount = UnitAssertion(currency=None, physical_unit="Headcount Units", scale_exponent=0, source_scope=ScopeLevel.ROW)
    assert unit_headcount.currency is None
    assert unit_headcount.scale_exponent == 0

    # End-to-end check: generic table without unit declarations remains UNRESOLVED and does not assume USD
    r0 = LogicalRow("ROW_000", 0, None, "DETAIL", "Generic Operational Count", 0, ())
    col0 = LogicalColumn("COL_00", 0, ("Metric",), role="ROW_HEADER")
    col1 = LogicalColumn("COL_01", 1, ("2026",))
    c_stub = CellNode("c_stub", CellRole.ROW_HEADER, GridSpan(0, 1, 0, 1), "Generic Operational Count", None, SourceRef(base_doc.sha256, "0", "0", "c_stub"))
    c_val = CellNode("c_val", CellRole.DATA, GridSpan(0, 1, 1, 2), "8,420", None, SourceRef(base_doc.sha256, "0", "0", "c_val"))
    frag = TableFragment("frag_generic", "p0", 1, 2, cells=(c_stub, c_val), rows=(r0,), columns=(col0, col1))

    compiler = TableCompiler()
    snap = compiler.compile(source_doc=base_doc, fragment=frag, footnotes=[], entity_name="Generic Inc", snapshot_id="snap_gen")
    assert snap.validation_report.overall_status == ValidationStatus.UNRESOLVED
    for f in snap.source_facts.values():
        assert f.unit is None or f.unit.currency is None
        assert f.verification_state == ValidationStatus.UNRESOLVED


# ==============================================================================
# Case 9: Ambiguous currency / math parsing: Preserve original meaning
# Attack: Feed diverse and ambiguous numeric expressions.
# Expected: Verbatim raw text is strictly preserved; bounds, missing values, and percentages are not conflated.
# ==============================================================================
def test_adv09_ambiguous_currency_math_parsing_preserves_meaning():
    normalizer = ValueNormalizer()

    # 1. Parenthetical negative
    val_paren = normalizer.normalize("(158.20)")[0]
    assert isinstance(val_paren, ExactNumeric)
    assert val_paren.value == Decimal("-158.20")
    assert val_paren.raw_text == "(158.20)", "Verbatim raw_text lost in parenthetical negative normalization!"

    # 2. Bounded inequality '< 0.01'
    val_bound = normalizer.normalize("< 0.01")[0]
    assert isinstance(val_bound, BoundedNumeric)
    assert val_bound.operator == BoundOperator.LT
    assert val_bound.bound == Decimal("0.01")
    assert val_bound.raw_text == "< 0.01"

    # 3. Nil-dash '—' vs reported zero '0.00'
    val_dash = normalizer.normalize("—")[0]
    assert isinstance(val_dash, MissingValue)
    assert val_dash.reason == MissingReason.NIL_DASH
    assert val_dash.raw_text == "—"

    val_zero = normalizer.normalize("0.00")[0]
    assert isinstance(val_zero, ExactNumeric)
    assert val_zero.value == Decimal("0.00")

    # They must never be equal
    assert val_dash != val_zero, "Nil-dash conflated with explicit zero!"


# ==============================================================================
# Case 10: Forged document signature: Hash vs. signature authenticity
# Attack: Supply a certificate with a matching SHA-256 digest but a forged/dummy signature.
# Expected: A SHA-256 hash match must NOT be treated as verified public-key cryptographic authenticity.
# ==============================================================================
def test_adv10_forged_document_signature_authenticity(base_doc, valid_fact_bundle):
    coord = FactCoordinates("e0", "Corp", "m0", "Rev", (), ("2026",), InstantPeriod(datetime.date(2026, 9, 30)))
    unit = UnitAssertion(currency="USD", scale_exponent=0)
    fact = SourceFact("f_sig", "c1", coord, ExactNumeric("100.00", Decimal("100.00")), unit, "100.00", valid_fact_bundle)

    # Construct certificate with forged signature payload
    cert_id = "cert_forged_01"
    import hashlib
    hasher = hashlib.sha256()
    hasher.update(cert_id.encode("utf-8"))
    hasher.update("f_sig".encode("utf-8"))
    hasher.update("100.00".encode("utf-8"))
    matching_digest = hasher.hexdigest()

    forged_sig = CryptoSignaturePayload(
        algorithm="Ed25519",
        key_id="forged_attacker_key",
        payload_digest=matching_digest,  # Matches the SHA-256!
        signature_bytes="FAKE_UNVERIFIED_SIGNATURE_BYTES",  # Not a real Ed25519 signature!
    )

    cert = EvidenceClosureCertificate(
        certificate_id=cert_id,
        fact_id="f_sig",
        provenance_bundle=valid_fact_bundle,
        fact=fact,
        signature=forged_sig,
    )

    verdict, failures = FormalProofVerifier.verify_fact_certificate(cert)

    # Cryptographic Authenticity check: Forged signature must be REJECTED with FAIL
    assert verdict == VerificationVerdict.FAIL, (
        "Security gap T10: FormalProofVerifier accepted forged signature because SHA-256 matched!"
    )
    assert any("Ed25519" in f or "key" in f for f in failures)

    # Genuine signature check: A legitimately signed certificate evaluates to PASS
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    priv_key = Ed25519PrivateKey.generate()
    pub_key = priv_key.public_key()
    trusted_key_id = "trusted_authority_01"
    FormalProofVerifier.register_trusted_key(trusted_key_id, pub_key)

    genuine_sig = FormalProofVerifier.sign_fact(
        certificate_id=cert_id,
        fact_id="f_sig",
        canonical_display="100.00",
        private_key=priv_key,
        key_id=trusted_key_id,
    )
    genuine_cert = EvidenceClosureCertificate(
        certificate_id=cert_id,
        fact_id="f_sig",
        provenance_bundle=valid_fact_bundle,
        fact=fact,
        signature=genuine_sig,
    )
    g_verdict, g_failures = FormalProofVerifier.verify_fact_certificate(genuine_cert)
    assert g_verdict == VerificationVerdict.PASS, f"Genuine certificate rejected: {g_failures}"
    assert len(g_failures) == 0
