"""
PCC-Tensor 3.1: Layer L4 Canonical Table IR Compiler Engine.
Transforms Layer L1 TableFragments into fully verified Layer L4 CTIRSnapshots
with bound facts, multi-source provenance bundles, temporal coordinates, and acyclic graphs.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from ..model.ctir import (
    CTIRSnapshot,
    DerivedFact,
    FactCoordinates,
    SourceFact,
    ValidationStatus,
)
from ..model.evidence import (
    EvidenceAnchor,
    EvidenceRole,
    MultiSourceProvenanceBundle,
    TransformationRecord,
)
from ..model.graph import FootnoteNode, StructuralGraph, ReferenceGraph
from ..model.semantic import ScopeLevel, UnitAssertion
from ..model.source import CoordinateSpace, SourceDocument
from ..model.structural import (
    CellNode,
    CellRole,
    HeaderNode,
    LogicalColumn,
    LogicalRow,
    LogicalTable,
    TableFragment,
)
from ..model.value import (
    DocumentConventionProfile,
    ExactNumeric,
    BoundedNumeric,
    NumericRange,
    MissingValue,
    TypedSemanticValue,
)
from ..verifier.validate import CTIRValidator
from .row_hierarchy import RowHierarchyBuilder
from .scope_resolver import ScopeResolver
from .value_normalizer import ValueNormalizer


class TableCompiler:
    """
    Core compiler for PCC-Tensor 3.1.
    Translates raw fragments and footnotes into verified, source-preserving CTIRSnapshots.
    """

    def __init__(
        self,
        convention_profile: Optional[DocumentConventionProfile] = None,
        table_default_unit: Optional[UnitAssertion] = None,
    ) -> None:
        self.profile = convention_profile or DocumentConventionProfile()
        self.scope_resolver = ScopeResolver(table_default_unit=table_default_unit)
        self.value_normalizer = ValueNormalizer(convention_profile=self.profile)
        self.row_builder = RowHierarchyBuilder()

    def compile(
        self,
        source_doc: SourceDocument,
        fragment: TableFragment,
        footnotes: List[FootnoteNode],
        entity_name: str = "Enterprise Registrant",
        snapshot_id: str = "ctir_snap_0",
        coordinate_space: Optional[CoordinateSpace] = None,
    ) -> CTIRSnapshot:
        """
        Compiles a TableFragment into an immutable, validated CTIRSnapshot.
        """
        # 1. Refine Row Hierarchy and compute ancestor paths
        refined_rows, structural_graph = self.row_builder.build_hierarchy(list(fragment.rows))
        rows_map: Dict[str, LogicalRow] = {r.row_id: r for r in refined_rows}
        cols_map: Dict[str, LogicalColumn] = {c.column_id: c for c in fragment.columns}
        headers_map: Dict[str, HeaderNode] = {h.header_id: h for h in fragment.headers}

        # Build Footnote Reference Graph
        ref_graph = ReferenceGraph()
        footnotes_map: Dict[str, FootnoteNode] = {}
        for fn in footnotes:
            ref_graph.add_footnote(fn)
            footnotes_map[fn.marker] = fn

        # Precompute Temporal Coordinates per Column
        col_temporals: Dict[int, Optional[object]] = {}
        for c in fragment.columns:
            # Infer period from column headers
            col_temporals[c.position] = self.scope_resolver.resolve_period_from_headers(c.header_path)

        # 2. Build Cell Maps & Extract Facts
        cells_map: Dict[str, CellNode] = {}
        typed_values_map: Dict[str, TypedSemanticValue] = {}
        evidence_anchors_map: Dict[str, EvidenceAnchor] = {}
        source_facts: Dict[str, SourceFact] = {}

        # Coordinate Space default
        if coordinate_space is None:
            # Fallback to existing cell bbox space
            first_bbox = next((c.bbox for c in fragment.cells if c.bbox is not None), None)
            space_id = first_bbox.coordinate_space_id if first_bbox else f"{snapshot_id}_space"
            coordinate_space = CoordinateSpace(
                space_id=space_id,
                kind="NORMALIZED_PAGE",
                width=Decimal("1000"),
                height=Decimal("1000"),
            )

        for cell in fragment.cells:
            cells_map[cell.cell_id] = cell

            # Connect footnote citations to reference graph
            for fn_m in cell.footnote_ids:
                if fn_m in footnotes_map:
                    ref_graph.add_reference(cell.cell_id, footnotes_map[fn_m].footnote_id)

            # Skip header cells, row header stub cells, and section banner cells for fact extraction
            row_idx = cell.span.row_start
            col_idx = cell.span.col_start

            if col_idx == 0 or cell.role in (CellRole.HEADER, CellRole.ROW_HEADER, CellRole.SECTION):
                continue

            current_row = rows_map.get(f"ROW_{row_idx:03d}")
            current_col = cols_map.get(f"COL_{col_idx:02d}")
            if current_row is None or current_col is None:
                continue

            # Check if row is a section break
            if current_row.role == "SECTION":
                continue

            # Normalize cell value
            typed_val, transforms, det_curr, det_unit = self.value_normalizer.normalize(
                cell.raw_text,
                inferred_currency=None,
                inferred_unit=None,
            )
            typed_values_map[cell.cell_id] = typed_val

            # Resolve Unit & Quantity
            if isinstance(typed_val, ExactNumeric):
                num_amount = typed_val.value
            elif isinstance(typed_val, BoundedNumeric):
                num_amount = typed_val.bound
            else:
                num_amount = Decimal("0")

            quantity, resolved_unit = self.scope_resolver.resolve_cell_quantity(
                raw_text=cell.raw_text,
                numeric_val=num_amount,
                row=current_row,
                column=current_col,
                cell_detected_currency=det_curr,
                cell_detected_unit=det_unit,
            )

            # Resolve Temporal Coordinate (row may override to Instant if headcount/employees)
            temporal_coord = self.scope_resolver.resolve_period_from_headers(
                current_col.header_path,
                row_label=current_row.raw_label,
            )

            # 3. Build Multi-Source Provenance Bundle (MSEP)
            val_anchor_id = f"ev_val_{cell.cell_id}"
            value_anchor = EvidenceAnchor(
                evidence_id=val_anchor_id,
                document_hash=source_doc.sha256,
                page_id=fragment.page_id,
                region_id=fragment.fragment_id,
                bbox=cell.bbox,
                raw_text=cell.raw_text,
                evidence_role=EvidenceRole.VALUE,
            )
            evidence_anchors_map[val_anchor_id] = value_anchor

            # Metric Anchor (from row stub)
            metric_anchor_id = f"ev_metric_{current_row.row_id}"
            stub_cell = next((c for c in fragment.cells if c.span.row_start == row_idx and c.span.col_start == 0), None)
            metric_anchor = EvidenceAnchor(
                evidence_id=metric_anchor_id,
                document_hash=source_doc.sha256,
                page_id=fragment.page_id,
                region_id=fragment.fragment_id,
                bbox=stub_cell.bbox if stub_cell else None,
                raw_text=current_row.raw_label,
                evidence_role=EvidenceRole.METRIC_LABEL,
            )
            evidence_anchors_map[metric_anchor_id] = metric_anchor

            # Period Anchor (from column header)
            period_anchor_id = f"ev_period_{current_col.column_id}"
            period_anchor = EvidenceAnchor(
                evidence_id=period_anchor_id,
                document_hash=source_doc.sha256,
                page_id=fragment.page_id,
                region_id=fragment.fragment_id,
                bbox=None,
                raw_text=" / ".join(current_col.header_path),
                evidence_role=EvidenceRole.PERIOD_DECLARATION,
            )
            evidence_anchors_map[period_anchor_id] = period_anchor

            # Unit Anchor
            unit_anchor_id = f"ev_unit_{current_row.row_id}_{current_col.column_id}"
            unit_anchor = EvidenceAnchor(
                evidence_id=unit_anchor_id,
                document_hash=source_doc.sha256,
                page_id=fragment.page_id,
                region_id=fragment.fragment_id,
                bbox=None,
                raw_text=f"{resolved_unit.currency or ''} 10^{resolved_unit.scale_exponent} {resolved_unit.physical_unit or ''}".strip(),
                evidence_role=EvidenceRole.UNIT_DECLARATION,
            )
            evidence_anchors_map[unit_anchor_id] = unit_anchor

            # Footnote Anchors
            fn_anchors: List[EvidenceAnchor] = []
            # Check cell footnotes
            for fn_m in cell.footnote_ids:
                if fn_m in footnotes_map:
                    fn_node = footnotes_map[fn_m]
                    fn_a_id = f"ev_fn_{fn_m}_{cell.cell_id}"
                    fn_a = EvidenceAnchor(
                        evidence_id=fn_a_id,
                        document_hash=source_doc.sha256,
                        page_id=fragment.page_id,
                        region_id=fragment.fragment_id,
                        bbox=None,
                        raw_text=fn_node.text,
                        evidence_role=EvidenceRole.FOOTNOTE,
                    )
                    evidence_anchors_map[fn_a_id] = fn_a
                    fn_anchors.append(fn_a)

            # Check row stub footnotes
            if stub_cell:
                for fn_m in stub_cell.footnote_ids:
                    if fn_m in footnotes_map and fn_m not in cell.footnote_ids:
                        fn_node = footnotes_map[fn_m]
                        fn_a_id = f"ev_fn_{fn_m}_{stub_cell.cell_id}"
                        fn_a = EvidenceAnchor(
                            evidence_id=fn_a_id,
                            document_hash=source_doc.sha256,
                            page_id=fragment.page_id,
                            region_id=fragment.fragment_id,
                            bbox=None,
                            raw_text=fn_node.text,
                            evidence_role=EvidenceRole.FOOTNOTE,
                        )
                        evidence_anchors_map[fn_a_id] = fn_a
                        fn_anchors.append(fn_a)

            # Entity Anchor
            entity_anchor_id = f"ev_entity_{current_row.row_id}_{current_col.column_id}"
            entity_anchor = EvidenceAnchor(
                evidence_id=entity_anchor_id,
                document_hash=source_doc.sha256,
                page_id=fragment.page_id,
                region_id=fragment.fragment_id,
                bbox=None,
                raw_text=entity_name,
                evidence_role=EvidenceRole.ENTITY_IDENTITY,
            )
            evidence_anchors_map[entity_anchor_id] = entity_anchor

            provenance_bundle = MultiSourceProvenanceBundle(
                value_anchor=value_anchor,
                metric_anchor=metric_anchor,
                period_anchor=period_anchor,
                unit_anchor=unit_anchor,
                entity_anchor=entity_anchor,
                footnote_anchors=tuple(fn_anchors),
            )

            # 4. Construct Canonical Display String
            if isinstance(typed_val, ExactNumeric):
                if resolved_unit.physical_unit in ("USD/share", "per share", "USD per share"):
                    canonical_disp = f"{resolved_unit.currency or 'USD'} {quantity.canonical_amount:,.2f} per share"
                elif resolved_unit.currency and not resolved_unit.physical_unit:
                    canonical_disp = f"{resolved_unit.currency} {quantity.canonical_amount:,.2f}"
                elif resolved_unit.physical_unit == "PERCENT":
                    canonical_disp = f"{quantity.numeric_value:,.2f}%"
                else:
                    canonical_disp = f"{quantity.canonical_amount:,.2f} {resolved_unit.physical_unit or ''}".strip()
            elif isinstance(typed_val, BoundedNumeric):
                canonical_disp = f"{typed_val.operator.value}{typed_val.bound}"
            elif isinstance(typed_val, MissingValue):
                canonical_disp = f"[{typed_val.reason.value}]"
            else:
                canonical_disp = cell.raw_text

            # 5. Build SourceFact (Contract C14 & C8: Persist transformations & initialize as UNRESOLVED)
            fact_id = f"fact_{cell.cell_id}"
            coordinates = FactCoordinates(
                entity_id="entity_0",
                entity_name=entity_name,
                metric_id=f"metric_r{row_idx:03d}",
                raw_metric_label=current_row.raw_label,
                row_ancestor_path=current_row.ancestor_path,
                column_ancestor_path=current_col.header_path,
                temporal=temporal_coord,
            )

            source_fact = SourceFact(
                fact_id=fact_id,
                source_cell_id=cell.cell_id,
                coordinates=coordinates,
                typed_value=typed_val,
                unit=resolved_unit,
                canonical_display=canonical_disp,
                provenance=provenance_bundle,
                verification_state=ValidationStatus.UNRESOLVED,
                transformations=tuple(transforms),
            )
            source_facts[fact_id] = source_fact

        # 6. Assemble Updated Fragment with Refined Rows
        updated_fragment = TableFragment(
            fragment_id=fragment.fragment_id,
            page_id=fragment.page_id,
            row_count=fragment.row_count,
            column_count=fragment.column_count,
            cells=fragment.cells,
            rows=tuple(refined_rows),
            columns=fragment.columns,
            headers=fragment.headers,
        )

        logical_table = LogicalTable(
            table_id=f"table_{snapshot_id}",
            fragment_ids=(updated_fragment.fragment_id,),
            is_stitched=False,
        )

        # 6. Compile Derived Facts (e.g. Free Cash Flow = Operating Cash Flow + CapEx Outflow)
        derived_facts: Dict[str, DerivedFact] = {}
        for col_id, col in cols_map.items():
            if col.position == 0:
                continue
            ocf_fact = None
            capex_fact = None
            for f in source_facts.values():
                if f.source_cell_id.endswith(f"c{col.position:02d}"):
                    label = f.coordinates.raw_metric_label.lower()
                    if "operating cash flow" in label or "operating activities" in label:
                        ocf_fact = f
                    elif "capital expenditure" in label or "purchase of property" in label or "capex" in label:
                        capex_fact = f
            if ocf_fact and capex_fact:
                if isinstance(ocf_fact.typed_value, ExactNumeric) and isinstance(capex_fact.typed_value, ExactNumeric):
                    fcf_val = ocf_fact.typed_value.value + capex_fact.typed_value.value
                    scale = ocf_fact.unit.scale_multiplier
                    fcf_canonical = fcf_val * scale
                    fcf_id = f"derived_fcf_c{col.position:02d}"
                    derived_fact = DerivedFact(
                        fact_id=fcf_id,
                        expression_name="ADD_OUTFLOW",
                        input_fact_ids=(ocf_fact.fact_id, capex_fact.fact_id),
                        result_value=ExactNumeric(raw_text=f"{fcf_val}", value=fcf_val),
                        unit=ocf_fact.unit,
                        canonical_display=f"{ocf_fact.unit.currency or 'USD'} {fcf_canonical:,.2f}",
                        execution_engine="DECIMAL_KERNEL",
                        verification_state=ValidationStatus.PASS,
                    )
                    derived_facts[fcf_id] = derived_fact

        # 7. Construct Initial CTIRSnapshot
        snapshot = CTIRSnapshot(
            snapshot_id=snapshot_id,
            schema_version="3.1.0",
            document=source_doc,
            coordinate_spaces=(coordinate_space,) if coordinate_space is not None else (),
            fragments=(updated_fragment,),
            logical_tables=(logical_table,),
            cells=cells_map,
            rows=rows_map,
            columns=cols_map,
            headers=headers_map,
            typed_values=typed_values_map,
            source_facts=source_facts,
            derived_facts=derived_facts,
            evidence_anchors=evidence_anchors_map,
        )

        # 8. Validate Snapshot via CTIRValidator
        validation_report = CTIRValidator.validate_snapshot(snapshot)

        # 9. Elevate source fact verification status based on validation report
        target_state = ValidationStatus.PASS if validation_report.overall_status == ValidationStatus.PASS else ValidationStatus.FAIL
        final_facts: Dict[str, SourceFact] = {}
        for fid, fact in source_facts.items():
            final_facts[fid] = SourceFact(
                fact_id=fact.fact_id,
                source_cell_id=fact.source_cell_id,
                coordinates=fact.coordinates,
                typed_value=fact.typed_value,
                unit=fact.unit,
                canonical_display=fact.canonical_display,
                provenance=fact.provenance,
                verification_state=target_state,
                transformations=fact.transformations,
                certificate=fact.certificate,
            )

        # Return final snapshot with validated facts and validation report attached
        final_snapshot = CTIRSnapshot(
            snapshot_id=snapshot.snapshot_id,
            schema_version=snapshot.schema_version,
            document=snapshot.document,
            coordinate_spaces=snapshot.coordinate_spaces,
            fragments=snapshot.fragments,
            logical_tables=snapshot.logical_tables,
            cells=snapshot.cells,
            rows=snapshot.rows,
            columns=snapshot.columns,
            headers=snapshot.headers,
            typed_values=snapshot.typed_values,
            source_facts=final_facts,
            derived_facts=derived_facts,
            evidence_anchors=snapshot.evidence_anchors,
            validation_report=validation_report,
        )

        return final_snapshot
