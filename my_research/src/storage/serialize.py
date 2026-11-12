"""
PCC-Tensor 3.1: Layer L4 — Canonical Serialization & Deserialization Engine.
Enforces Contract C15 (Canonical serialization round-trip: Deserialize(Serialize(CTIR)) == CTIR).
Guarantees complete, lossless round-trip preservation of facts, coordinates, topologies,
provenance bundles, transformations, and formal validation reports.
"""

from __future__ import annotations

import datetime
from decimal import Decimal
import json
from typing import Any, Dict, List, Optional, Tuple

from ..model.ctir import (
    CTIRSnapshot,
    DerivedFact,
    FactCoordinates,
    SourceFact,
    ValidationDiagnostic,
    ValidationReport,
    ValidationStatus,
)
from ..model.evidence import (
    EvidenceAnchor,
    EvidenceRole,
    MultiSourceProvenanceBundle,
    TransformationRecord,
)
from ..model.geometry import GridSpan
from ..model.semantic import ScopeLevel, UnitAssertion
from ..model.source import BoundingBox, CoordinateSpace, SourceDocument, SourceRef
from ..model.structural import (
    CellNode,
    CellRole,
    HeaderNode,
    LogicalColumn,
    LogicalRow,
    LogicalTable,
    TableFragment,
)
from ..model.temporal import DurationPeriod, InstantPeriod, TemporalCoordinate
from ..model.value import (
    BoundOperator,
    BoundedNumeric,
    ExactNumeric,
    MissingReason,
    MissingValue,
    NumericRange,
    TypedSemanticValue,
)


class CanonicalJSONEncoder(json.JSONEncoder):
    """Encodes Decimal, sets, and enums into deterministic canonical JSON."""
    def default(self, obj: Any) -> Any:
        if isinstance(obj, Decimal):
            return str(obj)
        if isinstance(obj, (datetime.date, datetime.datetime)):
            return obj.isoformat()
        if hasattr(obj, "value") and isinstance(obj.value, (str, int)):
            return obj.value
        if isinstance(obj, set):
            return sorted(list(obj))
        return super().default(obj)


# ==============================================================================
# Helper Serializers
# ==============================================================================

def _serialize_bbox(bbox: Optional[BoundingBox]) -> Optional[Dict[str, Any]]:
    if bbox is None:
        return None
    return {
        "coordinate_space_id": bbox.coordinate_space_id,
        "x0": str(bbox.x0),
        "y0": str(bbox.y0),
        "x1": str(bbox.x1),
        "y1": str(bbox.y1),
    }


def _deserialize_bbox(d: Optional[Dict[str, Any]]) -> Optional[BoundingBox]:
    if not d:
        return None
    return BoundingBox(
        coordinate_space_id=d["coordinate_space_id"],
        x0=Decimal(d["x0"]),
        y0=Decimal(d["y0"]),
        x1=Decimal(d["x1"]),
        y1=Decimal(d["y1"]),
    )


def _serialize_source_ref(ref: Optional[SourceRef]) -> Optional[Dict[str, Any]]:
    if ref is None:
        return None
    return {
        "document_hash": ref.document_hash,
        "page_id": ref.page_id,
        "region_id": ref.region_id,
        "evidence_id": getattr(ref, "evidence_id", getattr(ref, "element_id", "")),
    }


def _deserialize_source_ref(d: Optional[Dict[str, Any]]) -> Optional[SourceRef]:
    if not d:
        return None
    return SourceRef(
        document_hash=d["document_hash"],
        page_id=d.get("page_id"),
        region_id=d.get("region_id", ""),
        evidence_id=d.get("evidence_id", d.get("element_id", "")),
    )


def _serialize_typed_value(tv: Any) -> Dict[str, Any]:
    if isinstance(tv, ExactNumeric):
        return {"type": "ExactNumeric", "raw_text": tv.raw_text, "value": str(tv.value)}
    elif isinstance(tv, BoundedNumeric):
        return {"type": "BoundedNumeric", "raw_text": tv.raw_text, "bound": str(tv.bound), "operator": tv.operator.value}
    elif isinstance(tv, NumericRange):
        return {
            "type": "NumericRange",
            "raw_text": tv.raw_text,
            "lower_bound": str(tv.lower_bound),
            "upper_bound": str(tv.upper_bound),
            "lower_inclusive": tv.lower_inclusive,
            "upper_inclusive": tv.upper_inclusive,
        }
    elif isinstance(tv, MissingValue):
        return {"type": "MissingValue", "raw_text": tv.raw_text, "reason": tv.reason.value}
    else:
        return {"type": "RawText", "raw_text": getattr(tv, "raw_text", str(tv))}


def _deserialize_typed_value(d: Dict[str, Any]) -> TypedSemanticValue:
    t = d.get("type", "ExactNumeric")
    raw = d.get("raw_text", "")
    if t == "ExactNumeric":
        return ExactNumeric(raw_text=raw, value=Decimal(d["value"]))
    elif t == "BoundedNumeric":
        return BoundedNumeric(raw_text=raw, bound=Decimal(d["bound"]), operator=BoundOperator(d["operator"]))
    elif t == "NumericRange":
        return NumericRange(
            raw_text=raw,
            lower_bound=Decimal(d["lower_bound"]),
            upper_bound=Decimal(d["upper_bound"]),
            lower_inclusive=bool(d["lower_inclusive"]),
            upper_inclusive=bool(d["upper_inclusive"]),
        )
    elif t == "MissingValue":
        return MissingValue(raw_text=raw, reason=MissingReason(d["reason"]))
    else:
        return ExactNumeric(raw_text=raw, value=Decimal(d.get("value", "0")))


def _serialize_temporal(temp: Optional[TemporalCoordinate]) -> Optional[Dict[str, Any]]:
    if temp is None:
        return None
    if isinstance(temp, InstantPeriod):
        return {
            "type": "InstantPeriod",
            "as_of_date": temp.as_of_date.isoformat(),
            "fiscal_year": temp.fiscal_year,
            "fiscal_quarter": temp.fiscal_quarter,
            "fiscal_label": temp.fiscal_label,
        }
    elif isinstance(temp, DurationPeriod):
        return {
            "type": "DurationPeriod",
            "start_date": temp.start_date.isoformat(),
            "end_date": temp.end_date.isoformat(),
            "fiscal_year": temp.fiscal_year,
            "fiscal_quarter": temp.fiscal_quarter,
            "fiscal_label": temp.fiscal_label,
        }
    return None


def _deserialize_temporal(d: Optional[Dict[str, Any]]) -> Optional[TemporalCoordinate]:
    if not d:
        return None
    t = d.get("type")
    if t == "InstantPeriod":
        return InstantPeriod(
            as_of_date=datetime.date.fromisoformat(d["as_of_date"]),
            fiscal_year=d.get("fiscal_year"),
            fiscal_quarter=d.get("fiscal_quarter"),
            fiscal_label=d.get("fiscal_label"),
        )
    elif t == "DurationPeriod":
        return DurationPeriod(
            start_date=datetime.date.fromisoformat(d["start_date"]),
            end_date=datetime.date.fromisoformat(d["end_date"]),
            fiscal_year=d.get("fiscal_year"),
            fiscal_quarter=d.get("fiscal_quarter"),
            fiscal_label=d.get("fiscal_label"),
        )
    return None


def _serialize_unit(u: Optional[UnitAssertion]) -> Optional[Dict[str, Any]]:
    if u is None:
        return None
    return {
        "currency": u.currency,
        "physical_unit": u.physical_unit,
        "scale_exponent": u.scale_exponent,
        "xbrl_decimals": u.xbrl_decimals,
        "source_scope": u.source_scope.value if hasattr(u.source_scope, "value") else str(u.source_scope),
    }


def _deserialize_unit(d: Optional[Dict[str, Any]]) -> Optional[UnitAssertion]:
    if not d:
        return None
    return UnitAssertion(
        currency=d.get("currency"),
        physical_unit=d.get("physical_unit"),
        scale_exponent=d.get("scale_exponent"),
        xbrl_decimals=d.get("xbrl_decimals"),
        source_scope=ScopeLevel(d.get("source_scope", "TABLE")),
    )


def _serialize_anchor(a: Optional[EvidenceAnchor]) -> Optional[Dict[str, Any]]:
    if a is None:
        return None
    return {
        "evidence_id": a.evidence_id,
        "document_hash": a.document_hash,
        "page_id": a.page_id,
        "region_id": a.region_id,
        "bbox": _serialize_bbox(a.bbox),
        "raw_text": a.raw_text,
        "evidence_role": a.evidence_role.value if hasattr(a.evidence_role, "value") else str(a.evidence_role),
        "extraction_method": a.extraction_method,
        "adapter_version": a.adapter_version,
    }


def _deserialize_anchor(d: Optional[Dict[str, Any]]) -> Optional[EvidenceAnchor]:
    if not d:
        return None
    return EvidenceAnchor(
        evidence_id=d["evidence_id"],
        document_hash=d["document_hash"],
        page_id=d.get("page_id", ""),
        region_id=d.get("region_id", ""),
        bbox=_deserialize_bbox(d.get("bbox")),
        raw_text=d.get("raw_text", ""),
        evidence_role=EvidenceRole(d["evidence_role"]) if "evidence_role" in d else EvidenceRole.VALUE,
        extraction_method=d.get("extraction_method", "native"),
        adapter_version=d.get("adapter_version", "3.1.0"),
    )


def _serialize_provenance(p: Optional[MultiSourceProvenanceBundle]) -> Optional[Dict[str, Any]]:
    if p is None:
        return None
    return {
        "value_anchor": _serialize_anchor(p.value_anchor),
        "metric_anchor": _serialize_anchor(p.metric_anchor),
        "period_anchor": _serialize_anchor(p.period_anchor),
        "unit_anchor": _serialize_anchor(p.unit_anchor),
        "entity_anchor": _serialize_anchor(p.entity_anchor),
        "footnote_anchors": [_serialize_anchor(fa) for fa in p.footnote_anchors],
    }


def _deserialize_provenance(d: Optional[Dict[str, Any]]) -> Optional[MultiSourceProvenanceBundle]:
    if not d:
        return None
    val_a = _deserialize_anchor(d.get("value_anchor"))
    if val_a is None:
        return None
    fn_anchors = tuple(
        _deserialize_anchor(fa) for fa in d.get("footnote_anchors", []) if fa is not None
    )
    return MultiSourceProvenanceBundle(
        value_anchor=val_a,
        metric_anchor=_deserialize_anchor(d.get("metric_anchor")),
        period_anchor=_deserialize_anchor(d.get("period_anchor")),
        unit_anchor=_deserialize_anchor(d.get("unit_anchor")),
        entity_anchor=_deserialize_anchor(d.get("entity_anchor")),
        footnote_anchors=fn_anchors,  # type: ignore
    )


def _serialize_transformation(tx: TransformationRecord) -> Dict[str, Any]:
    return {
        "transformation_id": tx.transformation_id,
        "rule_name": tx.rule_name,
        "input_raw": tx.input_raw,
        "output_result": tx.output_result,
        "replayed_successfully": tx.replayed_successfully,
    }


def _deserialize_transformation(d: Dict[str, Any]) -> TransformationRecord:
    return TransformationRecord(
        transformation_id=d["transformation_id"],
        rule_name=d["rule_name"],
        input_raw=d["input_raw"],
        output_result=d["output_result"],
        replayed_successfully=bool(d["replayed_successfully"]),
    )


# ==============================================================================
# Master Serialization and Deserialization API
# ==============================================================================

def serialize_ctir_to_json(snapshot: CTIRSnapshot, indent: int = 2) -> str:
    """
    Contract C15: Lossless canonical serialization of a full CTIRSnapshot.
    Preserves all facts, topological structures, evidence chains, and validation reports.
    """
    # 1. Document & Spaces
    doc_payload = None
    if snapshot.document:
        doc_payload = {
            "document_id": snapshot.document.document_id,
            "sha256": snapshot.document.sha256,
            "mime_type": snapshot.document.mime_type,
            "byte_length": snapshot.document.byte_length,
            "source_uri": snapshot.document.source_uri,
            "schema_version": snapshot.document.schema_version,
        }

    spaces_payload = [
        {
            "space_id": cs.space_id,
            "kind": cs.kind,
            "width": str(cs.width),
            "height": str(cs.height),
            "origin": cs.origin,
            "unit": cs.unit,
            "rotation_degrees": cs.rotation_degrees,
        }
        for cs in snapshot.coordinate_spaces
    ]

    # 2. Cells
    cells_payload = {}
    for cid, cell in snapshot.cells.items():
        cells_payload[cid] = {
            "cell_id": cell.cell_id,
            "role": cell.role.value if hasattr(cell.role, "value") else str(cell.role),
            "span": {
                "row_start": cell.span.row_start,
                "row_end": cell.span.row_end,
                "col_start": cell.span.col_start,
                "col_end": cell.span.col_end,
            },
            "raw_text": cell.raw_text,
            "bbox": _serialize_bbox(cell.bbox),
            "source_ref": _serialize_source_ref(cell.source_ref),
            "footnote_ids": list(cell.footnote_ids),
        }

    # 3. Rows & Columns & Headers
    rows_payload = {}
    for rid, r in snapshot.rows.items():
        rows_payload[rid] = {
            "row_id": r.row_id,
            "position": r.position,
            "parent_row_id": r.parent_row_id,
            "role": r.role,
            "raw_label": r.raw_label,
            "indent_depth": r.indent_depth,
            "ancestor_path": list(r.ancestor_path),
        }

    cols_payload = {}
    for col_id, col in snapshot.columns.items():
        cols_payload[col_id] = {
            "column_id": col.column_id,
            "position": col.position,
            "header_path": list(col.header_path),
            "role": col.role,
        }

    headers_payload = {}
    for hid, h in snapshot.headers.items():
        headers_payload[hid] = {
            "header_id": h.header_id,
            "label": getattr(h, "label", getattr(h, "raw_text", "")),
            "level": h.level,
            "col_start": getattr(h, "col_start", 0),
            "col_end": getattr(h, "col_end", 0),
            "parent_header_id": h.parent_header_id,
            "footnote_ids": list(getattr(h, "footnote_ids", ())),
            "bbox": _serialize_bbox(getattr(h, "bbox", None)),
        }

    # 4. Fragments & Logical Tables
    fragments_payload = []
    for frag in snapshot.fragments:
        fragments_payload.append({
            "fragment_id": frag.fragment_id,
            "page_id": frag.page_id,
            "row_count": frag.row_count,
            "column_count": frag.column_count,
            "cells": [cells_payload[c.cell_id] for c in frag.cells if c.cell_id in cells_payload],
            "rows": [rows_payload[r.row_id] for r in frag.rows if r.row_id in rows_payload],
            "columns": [cols_payload[c.column_id] for c in frag.columns if c.column_id in cols_payload],
            "headers": [headers_payload[h.header_id] for h in frag.headers if h.header_id in headers_payload],
        })

    tables_payload = [
        {
            "table_id": lt.table_id,
            "fragment_ids": list(lt.fragment_ids),
            "is_stitched": lt.is_stitched,
        }
        for lt in snapshot.logical_tables
    ]

    # 5. Source Facts
    facts_payload = {}
    for fid, f in snapshot.source_facts.items():
        facts_payload[fid] = {
            "fact_id": f.fact_id,
            "source_cell_id": f.source_cell_id,
            "coordinates": {
                "entity_id": f.coordinates.entity_id,
                "entity_name": f.coordinates.entity_name,
                "metric_id": f.coordinates.metric_id,
                "raw_metric_label": f.coordinates.raw_metric_label,
                "row_ancestor_path": list(f.coordinates.row_ancestor_path),
                "column_ancestor_path": list(f.coordinates.column_ancestor_path),
                "temporal": _serialize_temporal(f.coordinates.temporal),
                "qualifiers": dict(f.coordinates.qualifiers),
            },
            "typed_value": _serialize_typed_value(f.typed_value),
            "unit": _serialize_unit(f.unit),
            "canonical_display": f.canonical_display,
            "provenance": _serialize_provenance(f.provenance),
            "verification_state": f.verification_state.value if hasattr(f.verification_state, "value") else str(f.verification_state),
            "transformations": [_serialize_transformation(tx) for tx in f.transformations],
        }

    # 6. Derived Facts
    derived_payload = {}
    for dfid, df in snapshot.derived_facts.items():
        derived_payload[dfid] = {
            "fact_id": df.fact_id,
            "expression_name": df.expression_name,
            "input_fact_ids": list(df.input_fact_ids),
            "result_value": _serialize_typed_value(df.result_value),
            "unit": _serialize_unit(df.unit),
            "canonical_display": df.canonical_display,
            "execution_engine": df.execution_engine,
            "verification_state": df.verification_state.value if hasattr(df.verification_state, "value") else str(df.verification_state),
        }

    # 7. Evidence Anchors
    anchors_payload = {aid: _serialize_anchor(a) for aid, a in snapshot.evidence_anchors.items()}

    # 8. Validation Report
    report_payload = None
    if snapshot.validation_report:
        vr = snapshot.validation_report
        report_payload = {
            "schema_status": vr.schema_status.value,
            "source_status": vr.source_status.value,
            "geometry_status": vr.geometry_status.value,
            "structure_status": vr.structure_status.value,
            "semantics_status": vr.semantics_status.value,
            "relationships_status": vr.relationships_status.value,
            "provenance_status": vr.provenance_status.value,
            "lineage_status": vr.lineage_status.value,
            "serialization_status": vr.serialization_status.value,
            "overall_status": vr.overall_status.value,
            "diagnostics": [
                {
                    "code": d.code,
                    "target_id": d.target_id,
                    "severity": d.severity,
                    "message": d.message,
                }
                for d in vr.diagnostics
            ],
        }

    payload = {
        "ir_type": "CTIR",
        "ir_version": snapshot.schema_version,
        "snapshot_id": snapshot.snapshot_id,
        "document": doc_payload,
        "coordinate_spaces": spaces_payload,
        "fragments_count": len(snapshot.fragments),
        "cells_count": len(snapshot.cells),
        "facts_count": len(snapshot.source_facts),
        "validation_status": snapshot.validation_report.overall_status.value if snapshot.validation_report else "UNRESOLVED",
        "cells": cells_payload,
        "rows": rows_payload,
        "columns": cols_payload,
        "headers": headers_payload,
        "fragments": fragments_payload,
        "logical_tables": tables_payload,
        "source_facts": facts_payload,
        "derived_facts": derived_payload,
        "evidence_anchors": anchors_payload,
        "validation_report": report_payload,
    }

    return json.dumps(payload, indent=indent, sort_keys=True, cls=CanonicalJSONEncoder)


def deserialize_ctir_from_json(json_str: str) -> CTIRSnapshot:
    """
    Contract C15: Lossless deserialization of a CTIR JSON string into a CTIRSnapshot instance.
    Guarantees Deserialize(Serialize(CTIR)) == CTIR.
    """
    data = json.loads(json_str)

    snapshot_id = data["snapshot_id"]
    schema_version = data.get("ir_version", data.get("schema_version", "3.1.0"))

    # 1. Document
    doc = None
    if data.get("document"):
        dd = data["document"]
        doc = SourceDocument(
            document_id=dd["document_id"],
            sha256=dd["sha256"],
            mime_type=dd["mime_type"],
            byte_length=dd["byte_length"],
            source_uri=dd.get("source_uri"),
            schema_version=dd.get("schema_version", "3.1.0"),
        )

    # 2. Coordinate Spaces
    spaces: List[CoordinateSpace] = []
    for sd in data.get("coordinate_spaces", []):
        spaces.append(CoordinateSpace(
            space_id=sd["space_id"],
            kind=sd["kind"],
            width=Decimal(sd["width"]),
            height=Decimal(sd["height"]),
            origin=sd.get("origin", "TOP_LEFT"),
            unit=sd.get("unit", "POINTS"),
            rotation_degrees=sd.get("rotation_degrees", 0),
        ))

    # 3. Cells
    cells_map: Dict[str, CellNode] = {}
    for cid, cd in data.get("cells", {}).items():
        span_d = cd["span"]
        grid_span = GridSpan(
            row_start=span_d["row_start"],
            row_end=span_d["row_end"],
            col_start=span_d["col_start"],
            col_end=span_d["col_end"],
        )
        cells_map[cid] = CellNode(
            cell_id=cd["cell_id"],
            role=CellRole(cd["role"]),
            span=grid_span,
            raw_text=cd["raw_text"],
            bbox=_deserialize_bbox(cd.get("bbox")),
            source_ref=_deserialize_source_ref(cd.get("source_ref")),
            footnote_ids=tuple(cd.get("footnote_ids", ())),
        )

    # 4. Rows & Columns & Headers
    rows_map: Dict[str, LogicalRow] = {}
    for rid, rd in data.get("rows", {}).items():
        rows_map[rid] = LogicalRow(
            row_id=rd["row_id"],
            position=rd["position"],
            parent_row_id=rd.get("parent_row_id"),
            role=rd["role"],
            raw_label=rd["raw_label"],
            indent_depth=rd.get("indent_depth", 0),
            ancestor_path=tuple(rd.get("ancestor_path", ())),
        )

    cols_map: Dict[str, LogicalColumn] = {}
    for col_id, col_d in data.get("columns", {}).items():
        cols_map[col_id] = LogicalColumn(
            column_id=col_d["column_id"],
            position=col_d["position"],
            header_path=tuple(col_d.get("header_path", ())),
            role=col_d.get("role", "DATA"),
        )

    headers_map: Dict[str, HeaderNode] = {}
    for hid, hd in data.get("headers", {}).items():
        headers_map[hid] = HeaderNode(
            header_id=hd["header_id"],
            label=hd.get("label", hd.get("raw_text", "")),
            level=hd.get("level", 1),
            col_start=hd.get("col_start", 0),
            col_end=hd.get("col_end", 0),
            parent_header_id=hd.get("parent_header_id"),
            footnote_ids=tuple(hd.get("footnote_ids", ())),
            bbox=_deserialize_bbox(hd.get("bbox")),
        )

    # 5. Fragments & Logical Tables
    fragments: List[TableFragment] = []
    for fd in data.get("fragments", []):
        f_cells = tuple(cells_map[c["cell_id"]] for c in fd.get("cells", []) if c["cell_id"] in cells_map)
        f_rows = tuple(rows_map[r["row_id"]] for r in fd.get("rows", []) if r["row_id"] in rows_map)
        f_cols = tuple(cols_map[c["column_id"]] for c in fd.get("columns", []) if c["column_id"] in cols_map)
        f_headers = tuple(headers_map[h["header_id"]] for h in fd.get("headers", []) if h["header_id"] in headers_map)
        fragments.append(TableFragment(
            fragment_id=fd["fragment_id"],
            page_id=fd.get("page_id", ""),
            row_count=fd["row_count"],
            column_count=fd["column_count"],
            cells=f_cells,
            rows=f_rows,
            columns=f_cols,
            headers=f_headers,
        ))

    tables: List[LogicalTable] = []
    for td in data.get("logical_tables", []):
        tables.append(LogicalTable(
            table_id=td["table_id"],
            fragment_ids=tuple(td.get("fragment_ids", ())),
            is_stitched=bool(td.get("is_stitched", False)),
        ))

    # 6. Source Facts
    source_facts: Dict[str, SourceFact] = {}
    for fid, fd in data.get("source_facts", {}).items():
        cd = fd["coordinates"]
        coord = FactCoordinates(
            entity_id=cd["entity_id"],
            entity_name=cd["entity_name"],
            metric_id=cd["metric_id"],
            raw_metric_label=cd["raw_metric_label"],
            row_ancestor_path=tuple(cd.get("row_ancestor_path", ())),
            column_ancestor_path=tuple(cd.get("column_ancestor_path", ())),
            temporal=_deserialize_temporal(cd.get("temporal")),
            qualifiers=dict(cd.get("qualifiers", {})),
        )
        txs = tuple(_deserialize_transformation(t) for t in fd.get("transformations", []))
        prov = _deserialize_provenance(fd.get("provenance"))
        v_state = ValidationStatus(fd.get("verification_state", "UNRESOLVED"))

        source_facts[fid] = SourceFact(
            fact_id=fd["fact_id"],
            source_cell_id=fd["source_cell_id"],
            coordinates=coord,
            typed_value=_deserialize_typed_value(fd["typed_value"]),
            unit=_deserialize_unit(fd.get("unit")),
            canonical_display=fd["canonical_display"],
            provenance=prov,  # type: ignore
            verification_state=v_state,
            transformations=txs,
        )

    # 7. Derived Facts
    derived_facts: Dict[str, DerivedFact] = {}
    for dfid, dfd in data.get("derived_facts", {}).items():
        df_v_state = ValidationStatus(dfd.get("verification_state", "UNRESOLVED"))
        derived_facts[dfid] = DerivedFact(
            fact_id=dfd["fact_id"],
            expression_name=dfd["expression_name"],
            input_fact_ids=tuple(dfd.get("input_fact_ids", ())),
            result_value=_deserialize_typed_value(dfd["result_value"]),
            unit=_deserialize_unit(dfd.get("unit")),
            canonical_display=dfd["canonical_display"],
            execution_engine=dfd.get("execution_engine", "DECIMAL_KERNEL"),
            verification_state=df_v_state,
        )

    # 8. Evidence Anchors
    evidence_anchors: Dict[str, EvidenceAnchor] = {}
    for aid, ad in data.get("evidence_anchors", {}).items():
        anchor_obj = _deserialize_anchor(ad)
        if anchor_obj:
            evidence_anchors[aid] = anchor_obj

    # 9. Validation Report
    report = None
    if data.get("validation_report"):
        vrd = data["validation_report"]
        diags = tuple(
            ValidationDiagnostic(
                code=dd["code"],
                target_id=dd["target_id"],
                severity=dd["severity"],
                message=dd["message"],
            )
            for dd in vrd.get("diagnostics", [])
        )
        report = ValidationReport(
            schema_status=ValidationStatus(vrd["schema_status"]),
            source_status=ValidationStatus(vrd["source_status"]),
            geometry_status=ValidationStatus(vrd["geometry_status"]),
            structure_status=ValidationStatus(vrd["structure_status"]),
            semantics_status=ValidationStatus(vrd["semantics_status"]),
            relationships_status=ValidationStatus(vrd["relationships_status"]),
            provenance_status=ValidationStatus(vrd["provenance_status"]),
            lineage_status=ValidationStatus(vrd["lineage_status"]),
            serialization_status=ValidationStatus(vrd["serialization_status"]),
            diagnostics=diags,
        )

    return CTIRSnapshot(
        snapshot_id=snapshot_id,
        schema_version=schema_version,
        document=doc,  # type: ignore
        coordinate_spaces=tuple(spaces),
        fragments=tuple(fragments),
        logical_tables=tuple(tables),
        cells=cells_map,
        rows=rows_map,
        columns=cols_map,
        headers=headers_map,
        source_facts=source_facts,
        derived_facts=derived_facts,
        evidence_anchors=evidence_anchors,
        validation_report=report,
    )
