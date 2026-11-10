"""
PCC-Tensor 3.1: Canonical Table IR (CTIR) Core Model Package.
"""

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
from .value import (
    BoundOperator,
    MissingReason,
    ExactNumeric,
    BoundedNumeric,
    NumericRange,
    MissingValue,
    DocumentConventionProfile,
    TypedSemanticValue,
    DECIMAL_CONTEXT,
    parse_exact_decimal,
)
from .temporal import (
    PeriodType,
    DurationPeriod,
    InstantPeriod,
    TemporalRelation,
    TemporalCoordinate,
    evaluate_temporal_relation,
)
from .semantic import (
    UnitAssertion,
    Quantity,
    ScopeLevel,
    ScopeRef,
    ResolutionStatus,
    SemanticAssertion,
    ScopeConflictResolver,
)
from .evidence import (
    EvidenceRole,
    EvidenceAnchor,
    MultiSourceProvenanceBundle,
    TransformationRecord,
)
from .structural import (
    CellRole,
    CellNode,
    LogicalRow,
    LogicalColumn,
    HeaderNode,
    TableFragment,
    LogicalTable,
)
from .graph import (
    FootnoteNode,
    StructuralGraph,
    ReferenceGraph,
)
from .types import (
    ProvenanceAnchor,
    EntityCoordinate,
    MetricCoordinate,
    BalanceType,
    STESFact,
)
from .ctir import (
    ValidationStatus,
    ValidationDiagnostic,
    ValidationReport,
    FactCoordinates,
    SourceFact,
    DerivedFact,
    CTIRSnapshot,
)

__all__ = [
    "SourceDocument",
    "CoordinateSpace",
    "BoundingBox",
    "SourceRef",
    "GridSpan",
    "spans_overlap",
    "BoundOperator",
    "MissingReason",
    "ExactNumeric",
    "BoundedNumeric",
    "NumericRange",
    "MissingValue",
    "TypedSemanticValue",
    "DECIMAL_CONTEXT",
    "parse_exact_decimal",
    "PeriodType",
    "DurationPeriod",
    "InstantPeriod",
    "TemporalRelation",
    "TemporalCoordinate",
    "evaluate_temporal_relation",
    "UnitAssertion",
    "Quantity",
    "ScopeLevel",
    "ScopeRef",
    "ResolutionStatus",
    "SemanticAssertion",
    "ScopeConflictResolver",
    "EvidenceRole",
    "EvidenceAnchor",
    "MultiSourceProvenanceBundle",
    "TransformationRecord",
    "CellRole",
    "CellNode",
    "LogicalRow",
    "LogicalColumn",
    "HeaderNode",
    "TableFragment",
    "LogicalTable",
    "FootnoteNode",
    "StructuralGraph",
    "ReferenceGraph",
    "ValidationStatus",
    "ValidationDiagnostic",
    "ValidationReport",
    "FactCoordinates",
    "SourceFact",
    "DerivedFact",
    "CTIRSnapshot",
]
