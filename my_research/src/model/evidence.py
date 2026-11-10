"""
PCC-Tensor 3.1: Layer L3 — Multi-Source Evidence Provenance (MSEP) & Transformation Ledger.
Enforces Contract C1 (Source integrity) and Contract C13 (Provenance closure).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Tuple

from .source import BoundingBox, SourceRef


class EvidenceRole(str, Enum):
    VALUE = "VALUE"
    METRIC_LABEL = "METRIC_LABEL"
    ROW_CONTEXT = "ROW_CONTEXT"
    COLUMN_HEADER = "COLUMN_HEADER"
    ENTITY_IDENTITY = "ENTITY_IDENTITY"
    UNIT_DECLARATION = "UNIT_DECLARATION"
    PERIOD_DECLARATION = "PERIOD_DECLARATION"
    FOOTNOTE = "FOOTNOTE"
    ACCOUNTING_BASIS = "ACCOUNTING_BASIS"


@dataclass(frozen=True)
class EvidenceAnchor:
    """An independently addressable source evidence region."""
    evidence_id: str
    document_hash: str
    page_id: Optional[str]
    region_id: Optional[str]
    bbox: Optional[BoundingBox]
    raw_text: str
    evidence_role: EvidenceRole
    extraction_method: str = "native"
    adapter_version: str = "3.1.0"


@dataclass(frozen=True)
class MultiSourceProvenanceBundle:
    """
    Contract C13: A fact is supported by a bundle of distinct evidence anchors,
    each responsible for a particular semantic coordinate.
    """
    value_anchor: EvidenceAnchor
    metric_anchor: Optional[EvidenceAnchor] = None
    period_anchor: Optional[EvidenceAnchor] = None
    unit_anchor: Optional[EvidenceAnchor] = None
    entity_anchor: Optional[EvidenceAnchor] = None
    footnote_anchors: Tuple[EvidenceAnchor, ...] = field(default_factory=tuple)

    def is_evidence_closed(self, requires_unit: bool = True, requires_period: bool = True) -> bool:
        """Verifies whether all required coordinate anchors are bound and valid."""
        if not self.value_anchor or not self.value_anchor.raw_text:
            return False
        if requires_unit and not self.unit_anchor:
            return False
        if requires_period and not self.period_anchor:
            return False
        return True


@dataclass(frozen=True)
class TransformationRecord:
    """Forward-replay ledger record for semantic normalizations."""
    transformation_id: str
    rule_name: str
    input_raw: str
    output_result: str
    replayed_successfully: bool

