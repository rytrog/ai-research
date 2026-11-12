"""
PCC-Tensor 3.1: Canonical Table Intermediate Representation (CTIR) Top-Level Snapshot.
Immutable, versioned canonical representation binding source evidence, structural topology,
semantic assertions, facts, and validation state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any

from .source import SourceDocument, CoordinateSpace, BoundingBox, SourceRef
from .structural import TableFragment, LogicalTable, CellNode, LogicalRow, LogicalColumn, HeaderNode
from .value import TypedSemanticValue
from .temporal import TemporalCoordinate
from .semantic import UnitAssertion, SemanticAssertion, ResolutionStatus
from .evidence import EvidenceAnchor, MultiSourceProvenanceBundle, TransformationRecord


class ValidationStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNRESOLVED = "UNRESOLVED"


@dataclass(frozen=True)
class ValidationDiagnostic:
    code: str
    target_id: str
    severity: str  # ERROR | WARNING | INFO
    message: str


@dataclass(frozen=True)
class ValidationReport:
    schema_status: ValidationStatus = ValidationStatus.UNRESOLVED
    source_status: ValidationStatus = ValidationStatus.UNRESOLVED
    geometry_status: ValidationStatus = ValidationStatus.UNRESOLVED
    structure_status: ValidationStatus = ValidationStatus.UNRESOLVED
    semantics_status: ValidationStatus = ValidationStatus.UNRESOLVED
    relationships_status: ValidationStatus = ValidationStatus.UNRESOLVED
    provenance_status: ValidationStatus = ValidationStatus.UNRESOLVED
    lineage_status: ValidationStatus = ValidationStatus.UNRESOLVED
    serialization_status: ValidationStatus = ValidationStatus.UNRESOLVED
    diagnostics: Tuple[ValidationDiagnostic, ...] = field(default_factory=tuple)

    @property
    def overall_status(self) -> ValidationStatus:
        statuses = [
            self.schema_status,
            self.source_status,
            self.geometry_status,
            self.structure_status,
            self.semantics_status,
            self.relationships_status,
            self.provenance_status,
            self.lineage_status,
            self.serialization_status,
        ]
        if any(s == ValidationStatus.FAIL for s in statuses):
            return ValidationStatus.FAIL
        if any(s == ValidationStatus.UNRESOLVED for s in statuses):
            return ValidationStatus.UNRESOLVED
        return ValidationStatus.PASS


@dataclass(frozen=True)
class FactCoordinates:
    entity_id: str
    entity_name: str
    metric_id: str
    raw_metric_label: str
    row_ancestor_path: Tuple[str, ...]
    column_ancestor_path: Tuple[str, ...]
    temporal: Optional[TemporalCoordinate]
    qualifiers: Dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class SourceFact:
    """
    Contract C14: A directly reported factual assertion pointing to source evidence.
    """
    fact_id: str
    source_cell_id: str
    coordinates: FactCoordinates
    typed_value: TypedSemanticValue
    unit: Optional[UnitAssertion]
    canonical_display: str
    provenance: MultiSourceProvenanceBundle
    verification_state: ValidationStatus = ValidationStatus.UNRESOLVED
    transformations: Tuple[TransformationRecord, ...] = field(default_factory=tuple)
    certificate: Optional[Any] = None

    @property
    def canonical_display_value(self) -> str:
        """Alias for canonical_display for backward compatibility."""
        return self.canonical_display

    @property
    def temporal(self) -> Optional[TemporalCoordinate]:
        """Direct access to temporal coordinate."""
        return self.coordinates.temporal



@dataclass(frozen=True)
class DerivedFact:
    """
    Contract C14: A calculated factual assertion with explicit execution lineage.
    Never conflated with a reported source fact.
    """
    fact_id: str
    expression_name: str                 # e.g. 'SUBTRACT'
    input_fact_ids: Tuple[str, ...]      # Lineage inputs (e.g. ('F_REV', 'F_COGS'))
    result_value: TypedSemanticValue
    unit: Optional[UnitAssertion]
    canonical_display: str
    execution_engine: str = "DECIMAL_KERNEL"
    verification_state: ValidationStatus = ValidationStatus.UNRESOLVED


@dataclass(frozen=True)
class CTIRSnapshot:
    """
    The immutable, versioned Canonical Table IR snapshot.
    The single source of truth for PCC-Tensor compilation.
    """
    snapshot_id: str
    schema_version: str = "3.1.0"
    document: SourceDocument = field(default=None)  # type: ignore
    coordinate_spaces: Tuple[CoordinateSpace, ...] = field(default_factory=tuple)
    fragments: Tuple[TableFragment, ...] = field(default_factory=tuple)
    logical_tables: Tuple[LogicalTable, ...] = field(default_factory=tuple)

    # Fast indexed views
    cells: Dict[str, CellNode] = field(default_factory=dict)
    rows: Dict[str, LogicalRow] = field(default_factory=dict)
    columns: Dict[str, LogicalColumn] = field(default_factory=dict)
    headers: Dict[str, HeaderNode] = field(default_factory=dict)
    typed_values: Dict[str, TypedSemanticValue] = field(default_factory=dict)
    semantic_assertions: Tuple[SemanticAssertion, ...] = field(default_factory=tuple)

    # Facts & Lineage
    source_facts: Dict[str, SourceFact] = field(default_factory=dict)
    derived_facts: Dict[str, DerivedFact] = field(default_factory=dict)
    evidence_anchors: Dict[str, EvidenceAnchor] = field(default_factory=dict)

    # Validation
    validation_report: Optional[ValidationReport] = None

