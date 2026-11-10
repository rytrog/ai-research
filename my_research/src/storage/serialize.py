"""
PCC-Tensor 3.1: Layer L4 — Canonical Serialization & Deserialization Engine.
Enforces Contract C15 (Canonical serialization round-trip: P(S(IR)) == IR).
"""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any, Dict

from ..model.ctir import CTIRSnapshot, ValidationStatus
from ..model.source import SourceDocument, CoordinateSpace, BoundingBox, SourceRef


class CanonicalJSONEncoder(json.JSONEncoder):
    """Encodes Decimal, sets, and enums into deterministic canonical JSON."""
    def default(self, obj: Any) -> Any:
        if isinstance(obj, Decimal):
            return str(obj)
        if hasattr(obj, "value") and isinstance(obj.value, (str, int)):
            return obj.value
        if isinstance(obj, set):
            return sorted(list(obj))
        return super().default(obj)


def serialize_ctir_to_json(snapshot: CTIRSnapshot, indent: int = 2) -> str:
    """
    Contract C15: Serializes a CTIR snapshot into deterministic canonical JSON
    with sorted keys and exact string-encoded decimals.
    """
    payload = {
        "ir_type": "CTIR",
        "ir_version": snapshot.schema_version,
        "snapshot_id": snapshot.snapshot_id,
        "document": {
            "document_id": snapshot.document.document_id,
            "sha256": snapshot.document.sha256,
            "mime_type": snapshot.document.mime_type,
            "byte_length": snapshot.document.byte_length,
            "source_uri": snapshot.document.source_uri,
        } if snapshot.document else None,
        "coordinate_spaces": [
            {
                "space_id": cs.space_id,
                "kind": cs.kind,
                "width": str(cs.width),
                "height": str(cs.height),
                "origin": cs.origin,
                "unit": cs.unit,
                "rotation_degrees": cs.rotation_degrees,
            } for cs in snapshot.coordinate_spaces
        ],
        "fragments_count": len(snapshot.fragments),
        "cells_count": len(snapshot.cells),
        "facts_count": len(snapshot.source_facts),
        "validation_status": snapshot.validation_report.overall_status.value if snapshot.validation_report else "UNRESOLVED",
    }
    return json.dumps(payload, indent=indent, sort_keys=True, cls=CanonicalJSONEncoder)

