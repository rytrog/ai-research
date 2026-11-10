"""
PCC-Tensor 3.1: Unified Model Re-Export & Compatibility Layer.
Eliminates duplicate model stacks (Problem A) by making types.py re-export
the authoritative Layer L0-L4 CTIR definitions.
"""

from __future__ import annotations

# L0 Source & Geometry
from .source import (
    SourceDocument,
    CoordinateSpace,
    BoundingBox,
    SourceRef,
)
from .geometry import (
    GridSpan,
    spans_overlap,
)

# L1 Structural
from .structural import (
    CellRole,
    CellNode,
    LogicalRow,
    LogicalColumn,
    HeaderNode,
    TableFragment,
    LogicalTable,
)

# L2 Value Lattice & Conventions
from .value import (
    BoundOperator,
    MissingReason,
    ExactNumeric,
    BoundedNumeric,
    NumericRange,
    MissingValue,
    TypedSemanticValue,
    DocumentConventionProfile,
    DECIMAL_CONTEXT,
    parse_exact_decimal,
)

# L2 Temporal Interval Algebra
from .temporal import (
    PeriodType,
    TemporalRelation,
    DurationPeriod,
    InstantPeriod,
    TemporalCoordinate,
    evaluate_temporal_relation,
)

# L2 Semantic Context & Units
from .semantic import (
    ScopeLevel,
    ScopeRef,
    ResolutionStatus,
    UnitAssertion,
    Quantity,
    SemanticAssertion,
    ScopeConflictResolver,
)

# L3 Multi-Source Evidence Provenance
from .evidence import (
    EvidenceRole,
    EvidenceAnchor,
    MultiSourceProvenanceBundle,
    TransformationRecord,
)

# L3 Graph Topology
from .graph import (
    FootnoteNode,
    StructuralGraph,
    ReferenceGraph,
)

# L4 Top-Level CTIR & Facts
from .ctir import (
    ValidationStatus,
    ValidationDiagnostic,
    ValidationReport,
    FactCoordinates,
    SourceFact,
    DerivedFact,
    CTIRSnapshot,
)

from dataclasses import dataclass, field
from enum import Enum
from decimal import Decimal
from typing import Optional, Tuple, Dict, Any


class BalanceType(str, Enum):
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"
    NEUTRAL = "NEUTRAL"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class EntityCoordinate:
    canonical_id: str
    display_name: str
    cik: Optional[str] = None
    segment_path: Tuple[str, ...] = field(default_factory=tuple)
    is_consolidated: bool = True
    confidence: float = 1.0


@dataclass(frozen=True)
class MetricCoordinate:
    canonical_id: str
    raw_label: str
    ancestor_path: Tuple[str, ...] = field(default_factory=tuple)
    balance_type: BalanceType = BalanceType.UNKNOWN
    statement_type: str = "UNKNOWN"


class ProvenanceAnchor(EvidenceAnchor):
    """Compatibility adapter for legacy ProvenanceAnchor instantiation."""
    def __new__(
        cls,
        doc_sha256: str = "",
        page_id: int | str = 0,
        bbox_pts: Tuple[float, float, float, float] = (0.0, 0.0, 1.0, 1.0),
        raw_text: str = "",
        evidence_role: str = "VALUE",
        adapter_id: str = "native",
        **kwargs,
    ):
        hash_64 = doc_sha256 if len(doc_sha256) == 64 else doc_sha256.ljust(64, "0")
        bbox = BoundingBox(
            x0=Decimal(str(bbox_pts[0])),
            y0=Decimal(str(bbox_pts[1])),
            x1=Decimal(str(bbox_pts[2])),
            y1=Decimal(str(bbox_pts[3])),
            coordinate_space_id=kwargs.get("coordinate_space_id", "test_space"),
        )
        role = EvidenceRole(evidence_role) if evidence_role in EvidenceRole.__members__ else EvidenceRole.VALUE
        return EvidenceAnchor(
            evidence_id=kwargs.get("evidence_id", "ev_legacy"),
            document_hash=hash_64,
            page_id=str(page_id),
            region_id=kwargs.get("region_id", "region_0"),
            bbox=bbox,
            raw_text=raw_text,
            evidence_role=role,
            extraction_method=adapter_id,
        )


class STESFact(SourceFact):
    """Compatibility adapter for legacy STESFact instantiation."""
    def __new__(
        cls,
        fact_id: str,
        entity: EntityCoordinate,
        metric: MetricCoordinate,
        temporal: TemporalCoordinate,
        typed_value: TypedSemanticValue,
        unit: UnitAssertion,
        provenance: MultiSourceProvenanceBundle,
        qualifiers: Optional[Dict[str, str]] = None,
        source_cell_id: str = "cell_test",
        canonical_display: Optional[str] = None,
        verification_state: ValidationStatus = ValidationStatus.UNRESOLVED,
        transformations: Tuple[TransformationRecord, ...] = (),
        certificate: Optional[Any] = None,
        **kwargs,
    ):
        coords = FactCoordinates(
            entity_id=entity.canonical_id,
            entity_name=entity.display_name,
            metric_id=metric.canonical_id,
            raw_metric_label=metric.raw_label,
            row_ancestor_path=metric.ancestor_path,
            column_ancestor_path=(),
            temporal=temporal,
            qualifiers=qualifiers or {},
        )
        if canonical_display is None:
            if isinstance(typed_value, ExactNumeric):
                val = typed_value.value
                mult = unit.scale_multiplier
                total = val * mult
                curr = f"{unit.currency} " if unit.currency else ""
                phys = f" {unit.physical_unit}" if unit.physical_unit else ""
                canonical_display = f"{curr}{total:,.2f}{phys}".strip()
            else:
                canonical_display = getattr(typed_value, "raw_text", "")

        return SourceFact(
            fact_id=fact_id,
            source_cell_id=source_cell_id,
            coordinates=coords,
            typed_value=typed_value,
            unit=unit,
            canonical_display=canonical_display,
            provenance=provenance,
            verification_state=verification_state,
            transformations=transformations,
            certificate=certificate,
        )


__all__ = [
    # L0
    "SourceDocument",
    "CoordinateSpace",
    "BoundingBox",
    "SourceRef",
    "GridSpan",
    "spans_overlap",
    # L1
    "CellRole",
    "CellNode",
    "LogicalRow",
    "LogicalColumn",
    "HeaderNode",
    "TableFragment",
    "LogicalTable",
    # L2
    "BoundOperator",
    "MissingReason",
    "ExactNumeric",
    "BoundedNumeric",
    "NumericRange",
    "MissingValue",
    "TypedSemanticValue",
    "DocumentConventionProfile",
    "DECIMAL_CONTEXT",
    "parse_exact_decimal",
    "PeriodType",
    "TemporalRelation",
    "DurationPeriod",
    "InstantPeriod",
    "TemporalCoordinate",
    "evaluate_temporal_relation",
    "ScopeLevel",
    "ScopeRef",
    "ResolutionStatus",
    "UnitAssertion",
    "Quantity",
    "SemanticAssertion",
    "ScopeConflictResolver",
    # L3
    "EvidenceRole",
    "EvidenceAnchor",
    "MultiSourceProvenanceBundle",
    "TransformationRecord",
    "FootnoteNode",
    "StructuralGraph",
    "ReferenceGraph",
    # L4
    "ValidationStatus",
    "ValidationDiagnostic",
    "ValidationReport",
    "FactCoordinates",
    "SourceFact",
    "DerivedFact",
    "CTIRSnapshot",
    "BalanceType",
    "EntityCoordinate",
    "MetricCoordinate",
    # Aliases
    "STESFact",
    "ProvenanceAnchor",
]
