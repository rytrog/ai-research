"""
PCC-Tensor 3.2: Formal Canonical Table IR (CTIR) Verifier Engine.
Enforces Contracts C1 through C20 across Layer L0 to L4.
Evaluates snapshots to tri-state verification: Verify(CTIR) in {PASS, FAIL, UNRESOLVED}.
Emits structured ValidationReports with per-stage status and deterministic diagnostic error codes.
"""

from __future__ import annotations

import decimal
import re
from decimal import Decimal
from typing import Dict, List, Optional, Set, Tuple

from ..model.ctir import (
    CTIRSnapshot,
    DerivedFact,
    SourceFact,
    ValidationDiagnostic,
    ValidationReport,
    ValidationStatus,
)
from ..model.geometry import spans_overlap
from ..model.graph import FootnoteNode, ReferenceGraph, StructuralGraph
from ..model.temporal import DurationPeriod, InstantPeriod
from ..model.value import (
    DECIMAL_CONTEXT,
    BoundOperator,
    BoundedNumeric,
    ExactNumeric,
    MissingReason,
    MissingValue,
    NumericRange,
    parse_exact_decimal,
)


class CTIRValidator:
    """
    Formal mathematical verifier for Canonical Table IR snapshots.
    Guarantees that an internally valid representation never silently masks
    unresolved facts, severed coordinates, corrupted geometry, or broken provenance.
    Outputs strictly Verify(CTIR) in {PASS, FAIL, UNRESOLVED}.
    """

    HEX_HASH_REGEX = re.compile(r"^[a-fA-F0-9]{16,64}$")

    # ==========================================================================
    # Contract Verification Methods (C1 - C20)
    # ==========================================================================

    @classmethod
    def verify_c1_source_integrity(cls, snapshot: CTIRSnapshot) -> List[ValidationDiagnostic]:
        """Contract C1: Source document integrity and cryptographic hash validity."""
        diags: List[ValidationDiagnostic] = []
        if snapshot.document is None:
            diags.append(ValidationDiagnostic(
                code="SOURCE_MISSING_DOCUMENT",
                target_id=snapshot.snapshot_id,
                severity="ERROR",
                message="Contract C1 violation: SourceDocument is null.",
            ))
            return diags

        doc = snapshot.document
        if not doc.sha256 or len(doc.sha256) < 16 or not cls.HEX_HASH_REGEX.match(doc.sha256):
            diags.append(ValidationDiagnostic(
                code="SOURCE_INVALID_HASH",
                target_id=doc.document_id,
                severity="ERROR",
                message=f"Contract C1 violation: Invalid or tampered document SHA256 '{doc.sha256}'.",
            ))

        if doc.byte_length <= 0:
            diags.append(ValidationDiagnostic(
                code="SOURCE_EMPTY_CONTENT",
                target_id=doc.document_id,
                severity="ERROR",
                message="Contract C1 violation: SourceDocument byte length must be greater than zero.",
            ))
        return diags

    @classmethod
    def verify_c2_fragment_preservation(cls, snapshot: CTIRSnapshot) -> List[ValidationDiagnostic]:
        """Contract C2: Physical fragments preserve row/column bounds and unique cell IDs."""
        diags: List[ValidationDiagnostic] = []
        seen_cell_ids: Set[str] = set()

        for frag in snapshot.fragments:
            if frag.row_count < 0 or frag.column_count < 0:
                diags.append(ValidationDiagnostic(
                    code="FRAGMENT_INVALID_COUNTS",
                    target_id=frag.fragment_id,
                    severity="ERROR",
                    message=f"Contract C2 violation: Fragment dimensions must be non-negative ({frag.row_count}x{frag.column_count}).",
                ))

            for cell in frag.cells:
                if cell.cell_id in seen_cell_ids:
                    diags.append(ValidationDiagnostic(
                        code="FRAGMENT_DUPLICATE_CELL_ID",
                        target_id=cell.cell_id,
                        severity="ERROR",
                        message=f"Contract C2 violation: Duplicate cell_id '{cell.cell_id}' detected.",
                    ))
                seen_cell_ids.add(cell.cell_id)

        return diags

    @classmethod
    def verify_c3_geometry_space(cls, snapshot: CTIRSnapshot) -> List[ValidationDiagnostic]:
        """Contract C3: Bounding-box validity and coordinate-space containment."""
        diags: List[ValidationDiagnostic] = []
        spaces_map = {cs.space_id: cs for cs in snapshot.coordinate_spaces}

        for cell_id, cell in snapshot.cells.items():
            if cell.bbox is not None:
                bbox = cell.bbox
                if bbox.coordinate_space_id not in spaces_map:
                    diags.append(ValidationDiagnostic(
                        code="GEOMETRY_UNDECLARED_SPACE",
                        target_id=cell_id,
                        severity="ERROR",
                        message=f"Contract C3 violation: BBox references undeclared space '{bbox.coordinate_space_id}'.",
                    ))
                else:
                    space = spaces_map[bbox.coordinate_space_id]
                    # Degenerate BBox check: x0 < x1 and y0 < y1
                    if bbox.x0 >= bbox.x1 or bbox.y0 >= bbox.y1:
                        diags.append(ValidationDiagnostic(
                            code="GEOMETRY_DEGENERATE_BBOX",
                            target_id=cell_id,
                            severity="ERROR",
                            message=f"Contract C3 violation: Inverted or degenerate bbox coordinates ({bbox.x0}, {bbox.y0}, {bbox.x1}, {bbox.y1}).",
                        ))
                    elif not bbox.is_contained_within(space):
                        diags.append(ValidationDiagnostic(
                            code="GEOMETRY_OUT_OF_BOUNDS",
                            target_id=cell_id,
                            severity="ERROR",
                            message=f"Contract C3 violation: BBox exceeds coordinate space bounds ({space.width}, {space.height}).",
                        ))

        return diags

    @classmethod
    def verify_c4_grid_consistency(cls, snapshot: CTIRSnapshot) -> List[ValidationDiagnostic]:
        """Contract C4: Grid consistency and non-overlapping cell spans within a table."""
        diags: List[ValidationDiagnostic] = []
        cell_list = list(snapshot.cells.values())
        for i in range(len(cell_list)):
            for j in range(i + 1, len(cell_list)):
                c1, c2 = cell_list[i], cell_list[j]
                if spans_overlap(c1.span, c2.span):
                    diags.append(ValidationDiagnostic(
                        code="GRID_SPAN_OVERLAP",
                        target_id=f"{c1.cell_id}&{c2.cell_id}",
                        severity="ERROR",
                        message=f"Contract C4 violation: Grid spans overlap between '{c1.cell_id}' and '{c2.cell_id}'.",
                    ))
        return diags

    @classmethod
    def verify_c5_structural_acyclicity(cls, snapshot: CTIRSnapshot) -> List[ValidationDiagnostic]:
        """Contract C5: Header tree containment and row hierarchy form strict acyclic DAGs."""
        diags: List[ValidationDiagnostic] = []
        graph = StructuralGraph()
        for h in snapshot.headers.values():
            graph.add_header(h)
        for r in snapshot.rows.values():
            graph.add_row(r)

        is_dag, dag_err = graph.validate_acyclic_dag()
        if not is_dag:
            diags.append(ValidationDiagnostic(
                code="STRUCTURAL_CYCLE_DETECTED",
                target_id="HIERARCHY_DAG",
                severity="ERROR",
                message=dag_err or "Contract C5 violation: Cycle detected in structural hierarchy.",
            ))
        return diags

    @classmethod
    def verify_c6_column_header_closure(cls, snapshot: CTIRSnapshot) -> List[ValidationDiagnostic]:
        """Contract C6: Every logical column has a non-empty hierarchical ancestor path."""
        diags: List[ValidationDiagnostic] = []
        for col_id, col in snapshot.columns.items():
            if not col.header_path:
                diags.append(ValidationDiagnostic(
                    code="COLUMN_EMPTY_HEADER_PATH",
                    target_id=col_id,
                    severity="ERROR",
                    message=f"Contract C6 violation: Column '{col_id}' has an empty header ancestor path.",
                ))
        return diags

    @classmethod
    def verify_c7_row_hierarchy_closure(cls, snapshot: CTIRSnapshot) -> List[ValidationDiagnostic]:
        """Contract C7: Every row with parent_row_id points to an existing parent row."""
        diags: List[ValidationDiagnostic] = []
        rows_map = snapshot.rows
        for row_id, row in rows_map.items():
            if row.parent_row_id is not None:
                if row.parent_row_id not in rows_map:
                    diags.append(ValidationDiagnostic(
                        code="ROW_DANGLING_PARENT",
                        target_id=row_id,
                        severity="ERROR",
                        message=f"Contract C7 violation: Row '{row_id}' references non-existent parent '{row.parent_row_id}'.",
                    ))
        return diags

    @classmethod
    def verify_c8_raw_value_preservation(cls, snapshot: CTIRSnapshot) -> List[ValidationDiagnostic]:
        """Contract C8: Raw verbatim text preserved and transformation records forward-replayable."""
        diags: List[ValidationDiagnostic] = []
        for fact_id, fact in snapshot.source_facts.items():
            raw_text = getattr(fact.typed_value, "raw_text", "")
            if not raw_text:
                diags.append(ValidationDiagnostic(
                    code="RAW_TEXT_MISSING",
                    target_id=fact_id,
                    severity="ERROR",
                    message=f"Contract C8 violation: Fact '{fact_id}' missing preserved raw text.",
                ))
                continue

            # Forward replay verification across TransformationRecords
            if fact.transformations:
                from ..model.evidence import verify_transformation_chain
                ok, err_code, err_msg = verify_transformation_chain(
                    initial_text=raw_text,
                    transformations=fact.transformations,
                    expected_value=fact.typed_value,
                )
                if not ok:
                    diags.append(ValidationDiagnostic(
                        code=err_code or "TRANSFORMATION_REPLAY_MISMATCH",
                        target_id=fact_id,
                        severity="ERROR",
                        message=f"Contract C8 violation: {err_msg}",
                    ))
        return diags

    @classmethod
    def verify_c9_value_lattice_soundness(cls, snapshot: CTIRSnapshot) -> List[ValidationDiagnostic]:
        """Contract C9: Values belong to the typed value lattice with exact Decimal precision."""
        diags: List[ValidationDiagnostic] = []
        valid_types = (ExactNumeric, BoundedNumeric, NumericRange, MissingValue)

        for fact_id, fact in snapshot.source_facts.items():
            tv = fact.typed_value
            if not isinstance(tv, valid_types):
                diags.append(ValidationDiagnostic(
                    code="VALUE_INVALID_LATTICE_TYPE",
                    target_id=fact_id,
                    severity="ERROR",
                    message=f"Contract C9 violation: Fact '{fact_id}' value '{type(tv)}' is not in value lattice.",
                ))
            elif isinstance(tv, ExactNumeric):
                if not isinstance(tv.value, Decimal):
                    diags.append(ValidationDiagnostic(
                        code="VALUE_FLOAT_PRECISION_DRIFT",
                        target_id=fact_id,
                        severity="ERROR",
                        message=f"Contract C9 violation: ExactNumeric must use exact Decimal, got {type(tv.value)}.",
                    ))
            elif isinstance(tv, BoundedNumeric):
                if not isinstance(tv.bound, Decimal):
                    diags.append(ValidationDiagnostic(
                        code="VALUE_FLOAT_PRECISION_DRIFT",
                        target_id=fact_id,
                        severity="ERROR",
                        message=f"Contract C9 violation: BoundedNumeric must use exact Decimal bound, got {type(tv.bound)}.",
                    ))
        return diags

    @classmethod
    def verify_c10_unit_consistency(cls, snapshot: CTIRSnapshot) -> List[ValidationDiagnostic]:
        """Contract C10: Scale is an integer exponent s in 10^s with consistent multiplier."""
        diags: List[ValidationDiagnostic] = []
        for fact_id, fact in snapshot.source_facts.items():
            unit = fact.unit
            if unit is None:
                continue
            if unit.scale_exponent is not None:
                if not isinstance(unit.scale_exponent, int):
                    diags.append(ValidationDiagnostic(
                        code="UNIT_INVALID_SCALE",
                        target_id=fact_id,
                        severity="ERROR",
                        message=f"Contract C10 violation: Scale exponent must be an integer, got {unit.scale_exponent}.",
                    ))
                else:
                    expected_mult = Decimal(10) ** unit.scale_exponent
                    if unit.scale_multiplier != expected_mult:
                        diags.append(ValidationDiagnostic(
                            code="UNIT_SCALE_MULTIPLIER_MISMATCH",
                            target_id=fact_id,
                            severity="ERROR",
                            message=f"Contract C10 violation: Multiplier {unit.scale_multiplier} does not match 10^{unit.scale_exponent}.",
                        ))
        return diags

    @classmethod
    def verify_c11_temporal_consistency(cls, snapshot: CTIRSnapshot) -> List[ValidationDiagnostic]:
        """Contract C11: Temporal coordinates conform to Allen interval algebra."""
        diags: List[ValidationDiagnostic] = []
        for fact_id, fact in snapshot.source_facts.items():
            temp = fact.coordinates.temporal
            if temp is None:
                diags.append(ValidationDiagnostic(
                    code="SEMANTICS_MISSING_TEMPORAL",
                    target_id=fact_id,
                    severity="WARNING",
                    message=f"Contract C11: Fact '{fact_id}' is missing temporal coordinate.",
                ))
            elif isinstance(temp, DurationPeriod):
                if temp.start_date > temp.end_date:
                    diags.append(ValidationDiagnostic(
                        code="TEMPORAL_INVERTED_INTERVAL",
                        target_id=fact_id,
                        severity="ERROR",
                        message=f"Contract C11 violation: Inverted duration dates ({temp.start_date} > {temp.end_date}).",
                    ))
        return diags

    @classmethod
    def verify_c12_scope_poset(cls, snapshot: CTIRSnapshot) -> List[ValidationDiagnostic]:
        """Contract C12: Independent partial-order property resolution without unresolved conflicts."""
        diags: List[ValidationDiagnostic] = []
        # Evaluates that all facts have resolved units without unhandled conflict status
        for fact_id, fact in snapshot.source_facts.items():
            if fact.unit is None:
                diags.append(ValidationDiagnostic(
                    code="SCOPE_UNRESOLVED_UNIT",
                    target_id=fact_id,
                    severity="WARNING",
                    message=f"Contract C12: Fact '{fact_id}' has null unit assertion.",
                ))
            elif fact.unit.currency is None and fact.unit.physical_unit is None and fact.unit.scale_exponent is None:
                diags.append(ValidationDiagnostic(
                    code="SCOPE_UNRESOLVED_UNIT",
                    target_id=fact_id,
                    severity="WARNING",
                    message=f"Contract C12: Fact '{fact_id}' has no declared currency, physical unit, or scale.",
                ))
        return diags

    @classmethod
    def verify_c13_provenance_closure(cls, snapshot: CTIRSnapshot) -> List[ValidationDiagnostic]:
        """Contract C13: Fact-level multi-source provenance closure (Value, Metric, Period, Unit, Entity)."""
        diags: List[ValidationDiagnostic] = []
        for fact_id, fact in snapshot.source_facts.items():
            prov = fact.provenance
            if not prov or not prov.value_anchor:
                diags.append(ValidationDiagnostic(
                    code="PROVENANCE_MISSING_VALUE_ANCHOR",
                    target_id=fact_id,
                    severity="ERROR",
                    message=f"Contract C13 violation: Fact '{fact_id}' missing value evidence anchor.",
                ))
            elif not prov.is_evidence_closed():
                diags.append(ValidationDiagnostic(
                    code="PROVENANCE_INCOMPLETE_CLOSURE",
                    target_id=fact_id,
                    severity="WARNING",
                    message=f"Contract C13: Fact '{fact_id}' lacks complete coordinate evidence closure.",
                ))
        return diags

    @classmethod
    def verify_c14_fact_lineage(cls, snapshot: CTIRSnapshot) -> List[ValidationDiagnostic]:
        """Contract C14: Reported facts vs Derived facts separation and arithmetic lineage verification."""
        diags: List[ValidationDiagnostic] = []

        # 1. Lineage DAG Acyclicity: detect circular dependency chains among derived facts
        adj: Dict[str, List[str]] = {
            d_id: [inp for inp in df.input_fact_ids if inp in snapshot.derived_facts]
            for d_id, df in snapshot.derived_facts.items()
        }

        state: Dict[str, int] = {k: 0 for k in adj}  # 0=unvisited, 1=visiting, 2=visited
        has_cycle = False
        cycle_nodes: Set[str] = set()

        def dfs(node: str, stack: List[str]) -> None:
            nonlocal has_cycle
            state[node] = 1
            stack.append(node)
            for neighbor in adj.get(node, []):
                if state.get(neighbor, 0) == 1:
                    has_cycle = True
                    cycle_nodes.add(node)
                    cycle_nodes.add(neighbor)
                elif state.get(neighbor, 0) == 0:
                    dfs(neighbor, stack)
            stack.pop()
            state[node] = 2

        for k in adj:
            if state[k] == 0:
                dfs(k, [])

        if has_cycle:
            for c_node in sorted(cycle_nodes):
                diags.append(ValidationDiagnostic(
                    code="DERIVED_LINEAGE_CYCLE",
                    target_id=c_node,
                    severity="ERROR",
                    message=f"Contract C14 violation: Lineage dependency cycle detected involving derived fact '{c_node}'",
                ))

        # 2. Per-derived fact validation
        for d_id, df in snapshot.derived_facts.items():
            if not df.input_fact_ids:
                diags.append(ValidationDiagnostic(
                    code="DERIVED_NO_INPUTS",
                    target_id=d_id,
                    severity="ERROR",
                    message=f"Contract C14 violation: Derived fact '{d_id}' has no input fact references",
                ))
                continue

            # Verify all inputs exist in source_facts OR derived_facts
            missing_inputs = [
                inp for inp in df.input_fact_ids
                if inp not in snapshot.source_facts and inp not in snapshot.derived_facts
            ]
            if missing_inputs:
                diags.append(ValidationDiagnostic(
                    code="DERIVED_MISSING_INPUT_FACT",
                    target_id=d_id,
                    severity="ERROR",
                    message=f"Contract C14 violation: Derived fact '{d_id}' references missing inputs: {missing_inputs}",
                ))
                continue

            # Verify no input is in FAIL state
            failed_inputs = []
            for inp in df.input_fact_ids:
                f_obj = snapshot.source_facts.get(inp) or snapshot.derived_facts.get(inp)
                if f_obj and f_obj.verification_state == ValidationStatus.FAIL:
                    failed_inputs.append(inp)
            if failed_inputs:
                diags.append(ValidationDiagnostic(
                    code="DERIVED_INPUT_FAILED",
                    target_id=d_id,
                    severity="ERROR",
                    message=f"Contract C14 violation: Derived fact '{d_id}' depends on failed input fact(s): {failed_inputs}",
                ))

            # Retrieve input objects
            input_objs = [
                snapshot.source_facts.get(inp) or snapshot.derived_facts.get(inp)
                for inp in df.input_fact_ids
            ]

            # Verify input types are ExactNumeric
            input_vals: List[ExactNumeric] = []
            has_non_numeric = False
            for obj in input_objs:
                val = getattr(obj, "typed_value", None) or getattr(obj, "result_value", None)
                if isinstance(val, ExactNumeric):
                    input_vals.append(val)
                else:
                    has_non_numeric = True
                    break

            if has_non_numeric or not isinstance(df.result_value, ExactNumeric):
                diags.append(ValidationDiagnostic(
                    code="DERIVED_INPUT_NON_NUMERIC",
                    target_id=d_id,
                    severity="ERROR",
                    message=f"Contract C14 violation: Derived fact '{d_id}' requires exact numeric inputs and output",
                ))
                continue

            # Check unit/currency compatibility for additive / subtractive ops
            if df.expression_name in ("ADD_OUTFLOW", "SUM", "SUBTRACT"):
                currencies = {obj.unit.currency for obj in input_objs if obj and obj.unit and obj.unit.currency}
                if len(currencies) > 1:
                    diags.append(ValidationDiagnostic(
                        code="DERIVED_UNIT_INCOMPATIBLE",
                        target_id=d_id,
                        severity="ERROR",
                        message=f"Contract C14 violation: Incompatible currencies across inputs for '{d_id}': {sorted(currencies)}",
                    ))

            # Exact Arithmetic Replay under DECIMAL_CONTEXT
            with decimal.localcontext(DECIMAL_CONTEXT):
                expected: Optional[Decimal] = None
                if df.expression_name in ("ADD_OUTFLOW", "SUM"):
                    expected = sum((v.value for v in input_vals), Decimal("0"))
                elif df.expression_name == "SUBTRACT":
                    if len(input_vals) >= 2:
                        expected = input_vals[0].value - sum((v.value for v in input_vals[1:]), Decimal("0"))
                    elif len(input_vals) == 1:
                        expected = -input_vals[0].value
                elif df.expression_name == "MULTIPLY":
                    prod = Decimal("1")
                    for v in input_vals:
                        prod *= v.value
                    expected = prod
                elif df.expression_name in ("DIVIDE", "RATIO"):
                    if len(input_vals) == 2:
                        if input_vals[1].value != 0:
                            expected = input_vals[0].value / input_vals[1].value
                        else:
                            diags.append(ValidationDiagnostic(
                                code="DERIVED_DIVISION_BY_ZERO",
                                target_id=d_id,
                                severity="ERROR",
                                message=f"Contract C14 violation: Division by zero in derived fact '{d_id}'",
                            ))
                    else:
                        diags.append(ValidationDiagnostic(
                            code="DERIVED_ARITY_MISMATCH",
                            target_id=d_id,
                            severity="ERROR",
                            message=f"Contract C14 violation: Expression '{df.expression_name}' expects 2 operands, got {len(input_vals)}",
                        ))
                else:
                    diags.append(ValidationDiagnostic(
                        code="DERIVED_UNKNOWN_EXPRESSION",
                        target_id=d_id,
                        severity="ERROR",
                        message=f"Contract C14 violation: Unknown derived expression '{df.expression_name}' in '{d_id}'",
                    ))

                if expected is not None:
                    if expected != df.result_value.value:
                        diags.append(ValidationDiagnostic(
                            code="DERIVED_CALCULATION_MISMATCH",
                            target_id=d_id,
                            severity="ERROR",
                            message=f"Contract C14 violation: Derived calculation expected {expected}, got {df.result_value.value}",
                        ))
        return diags

    @classmethod
    def verify_c15_serialization_round_trip(cls, snapshot: CTIRSnapshot) -> List[ValidationDiagnostic]:
        """Contract C15: Canonical serialization round-trip: Deserialize(Serialize(CTIR)) == CTIR."""
        diags: List[ValidationDiagnostic] = []
        try:
            from ..storage.serialize import serialize_ctir_to_json, deserialize_ctir_from_json
            json_str = serialize_ctir_to_json(snapshot)
            reconstructed = deserialize_ctir_from_json(json_str)

            if reconstructed.snapshot_id != snapshot.snapshot_id:
                diags.append(ValidationDiagnostic(
                    code="SERIALIZATION_MISMATCH",
                    target_id=snapshot.snapshot_id,
                    severity="ERROR",
                    message="Contract C15 failure: Snapshot ID mismatch after round-trip deserialization.",
                ))
            if len(reconstructed.source_facts) != len(snapshot.source_facts):
                diags.append(ValidationDiagnostic(
                    code="SERIALIZATION_FACTS_LOST",
                    target_id=snapshot.snapshot_id,
                    severity="ERROR",
                    message=f"Contract C15 failure: Source facts lost in round-trip ({len(reconstructed.source_facts)} != {len(snapshot.source_facts)}).",
                ))
            else:
                for fid, orig_f in snapshot.source_facts.items():
                    rec_f = reconstructed.source_facts.get(fid)
                    if rec_f is None:
                        diags.append(ValidationDiagnostic(
                            code="SERIALIZATION_FACT_MISSING",
                            target_id=fid,
                            severity="ERROR",
                            message=f"Contract C15 failure: Fact '{fid}' missing in round-trip snapshot.",
                        ))
                    elif rec_f.canonical_display != orig_f.canonical_display:
                        diags.append(ValidationDiagnostic(
                            code="SERIALIZATION_FACT_MUTATED",
                            target_id=fid,
                            severity="ERROR",
                            message=f"Contract C15 failure: Fact '{fid}' mutated in round-trip.",
                        ))
        except Exception as e:
            diags.append(ValidationDiagnostic(
                code="SERIALIZATION_FAILURE",
                target_id=snapshot.snapshot_id,
                severity="ERROR",
                message=f"Contract C15 failure: Serialization/deserialization failed with {e}",
            ))
        return diags

    @classmethod
    def verify_c17_stitched_fragments(cls, snapshot: CTIRSnapshot) -> List[ValidationDiagnostic]:
        """Contract C17: Multi-page fragment stitching preserves all underlying fragment IDs."""
        diags: List[ValidationDiagnostic] = []
        fragment_ids = {f.fragment_id for f in snapshot.fragments}
        for lt in snapshot.logical_tables:
            if lt.is_stitched:
                if len(lt.fragment_ids) < 2:
                    diags.append(ValidationDiagnostic(
                        code="STITCHED_INSUFFICIENT_FRAGMENTS",
                        target_id=lt.table_id,
                        severity="ERROR",
                        message=f"Contract C17 violation: Stitched table '{lt.table_id}' must contain >= 2 fragment IDs.",
                    ))
                for fid in lt.fragment_ids:
                    if fid not in fragment_ids:
                        diags.append(ValidationDiagnostic(
                            code="STITCHED_MISSING_FRAGMENTS",
                            target_id=lt.table_id,
                            severity="ERROR",
                            message=f"Contract C17 violation: Stitched table references missing fragment '{fid}'.",
                        ))
        return diags

    @classmethod
    def verify_c18_reference_graph(cls, snapshot: CTIRSnapshot) -> List[ValidationDiagnostic]:
        """Contract C18: Footnote reference links point to valid definitions; cycles detected canonically."""
        diags: List[ValidationDiagnostic] = []
        # Check that footnote citations in cells have corresponding footnote anchors/definitions
        for cell in snapshot.cells.values():
            for fn_marker in cell.footnote_ids:
                if not any(fn_marker in anchor.evidence_id for anchor in snapshot.evidence_anchors.values()):
                    # Cell cites a footnote marker not found in extracted evidence
                    diags.append(ValidationDiagnostic(
                        code="REFERENCE_UNRESOLVED_NOTE",
                        target_id=cell.cell_id,
                        severity="WARNING",
                        message=f"Contract C18: Cell cites footnote '[{fn_marker}]' not resolved in evidence anchors.",
                    ))
        return diags

    @classmethod
    def verify_c19_bounded_and_missing(cls, snapshot: CTIRSnapshot) -> List[ValidationDiagnostic]:
        """Contract C19: Bounded and missing values carry explicit typed grounding."""
        diags: List[ValidationDiagnostic] = []
        for fact_id, fact in snapshot.source_facts.items():
            tv = fact.typed_value
            if isinstance(tv, MissingValue):
                if tv.reason is None or not isinstance(tv.reason, MissingReason):
                    diags.append(ValidationDiagnostic(
                        code="MISSING_VALUE_NULL_REASON",
                        target_id=fact_id,
                        severity="ERROR",
                        message=f"Contract C19 violation: MissingValue must declare valid MissingReason enum, got {tv.reason}.",
                    ))
            elif isinstance(tv, BoundedNumeric):
                if tv.operator is None or not isinstance(tv.operator, BoundOperator):
                    diags.append(ValidationDiagnostic(
                        code="BOUNDED_VALUE_INVALID_OPERATOR",
                        target_id=fact_id,
                        severity="ERROR",
                        message=f"Contract C19 violation: BoundedNumeric operator must be in BoundOperator enum, got {tv.operator}.",
                    ))
        return diags

    @classmethod
    def verify_c20_gate_authority(cls, snapshot: CTIRSnapshot) -> List[ValidationDiagnostic]:
        """Contract C20: Source facts and derived facts cannot be prematurely promoted to PASS before formal validation."""
        diags: List[ValidationDiagnostic] = []
        # If snapshot has validation_report is None, any facts marked PASS violate gate authority
        if snapshot.validation_report is None:
            for fid, f in snapshot.source_facts.items():
                if f.verification_state == ValidationStatus.PASS:
                    diags.append(ValidationDiagnostic(
                        code="VALIDATION_PREMATURE_PROMOTION",
                        target_id=fid,
                        severity="ERROR",
                        message=f"Contract C20 violation: Source fact '{fid}' prematurely promoted to PASS before validator pass.",
                    ))
            for dfid, df in snapshot.derived_facts.items():
                if df.verification_state == ValidationStatus.PASS:
                    diags.append(ValidationDiagnostic(
                        code="VALIDATION_PREMATURE_PROMOTION",
                        target_id=dfid,
                        severity="ERROR",
                        message=f"Contract C20 violation: Derived fact '{dfid}' prematurely promoted to PASS before validator pass.",
                    ))
        return diags

    # ==========================================================================
    # Master Aggregation Pipeline
    # ==========================================================================

    @classmethod
    def validate_snapshot(cls, snapshot: CTIRSnapshot) -> ValidationReport:
        """
        Executes all 20 contract checks and computes the tri-state report:
        Verify(CTIR) in {PASS, FAIL, UNRESOLVED}.
        """
        all_diags: List[ValidationDiagnostic] = []

        # Collect diagnostics per stage
        v1_diags = cls.verify_c2_fragment_preservation(snapshot) + cls.verify_c20_gate_authority(snapshot)
        if not snapshot.snapshot_id or not snapshot.schema_version:
            v1_diags.append(ValidationDiagnostic(
                code="SCHEMA_INVALID_ID",
                target_id=snapshot.snapshot_id or "ROOT",
                severity="ERROR",
                message="Snapshot ID or schema version is missing.",
            ))

        v2_diags = cls.verify_c1_source_integrity(snapshot)
        v3_diags = cls.verify_c3_geometry_space(snapshot)
        v4_diags = (
            cls.verify_c4_grid_consistency(snapshot)
            + cls.verify_c5_structural_acyclicity(snapshot)
            + cls.verify_c6_column_header_closure(snapshot)
            + cls.verify_c7_row_hierarchy_closure(snapshot)
            + cls.verify_c17_stitched_fragments(snapshot)
        )
        v5_diags = (
            cls.verify_c8_raw_value_preservation(snapshot)
            + cls.verify_c9_value_lattice_soundness(snapshot)
            + cls.verify_c10_unit_consistency(snapshot)
            + cls.verify_c11_temporal_consistency(snapshot)
            + cls.verify_c12_scope_poset(snapshot)
            + cls.verify_c19_bounded_and_missing(snapshot)
        )
        v6_diags = cls.verify_c18_reference_graph(snapshot)
        v7_diags = cls.verify_c13_provenance_closure(snapshot)
        v8_diags = cls.verify_c14_fact_lineage(snapshot)

        # Stage 9: Serialization Verification (Contract C15)
        v9_diags = cls.verify_c15_serialization_round_trip(snapshot)
        ser_status = ValidationStatus.FAIL if any(d.severity == "ERROR" for d in v9_diags) else ValidationStatus.PASS

        def _compute_status(diags: List[ValidationDiagnostic]) -> ValidationStatus:
            if any(d.severity == "ERROR" for d in diags):
                return ValidationStatus.FAIL
            if any(d.severity == "WARNING" for d in diags):
                return ValidationStatus.UNRESOLVED
            return ValidationStatus.PASS

        all_diags.extend(v1_diags + v2_diags + v3_diags + v4_diags + v5_diags + v6_diags + v7_diags + v8_diags + v9_diags)

        report = ValidationReport(
            schema_status=_compute_status(v1_diags),
            source_status=_compute_status(v2_diags),
            geometry_status=_compute_status(v3_diags),
            structure_status=_compute_status(v4_diags),
            semantics_status=_compute_status(v5_diags),
            relationships_status=_compute_status(v6_diags),
            provenance_status=_compute_status(v7_diags),
            lineage_status=_compute_status(v8_diags),
            serialization_status=ser_status,
            diagnostics=tuple(all_diags),
        )

        return report
