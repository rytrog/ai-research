"""
PCC-Tensor 3.1: Layer L1 — Structural IR & Table Topology Models.
Enforces Contract C4 (Grid consistency), Contract C6 (Header closure), and Contract C7 (Row closure).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Tuple

from .geometry import GridSpan
from .source import BoundingBox, SourceRef


class CellRole(str, Enum):
    DATA = "DATA"
    HEADER = "HEADER"
    ROW_HEADER = "ROW_HEADER"
    SECTION = "SECTION"
    SUBTOTAL = "SUBTOTAL"
    TOTAL = "TOTAL"
    ANNOTATION = "ANNOTATION"
    EMPTY = "EMPTY"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class CellNode:
    """A physical source cell in the table grid."""
    cell_id: str
    role: CellRole
    span: GridSpan
    raw_text: str
    bbox: Optional[BoundingBox]
    source_ref: SourceRef
    footnote_ids: Tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class LogicalRow:
    """A logical row in the table with role classification and hierarchy path."""
    row_id: str
    position: int
    parent_row_id: Optional[str]
    role: str = "DETAIL"                 # HEADER | DETAIL | SECTION | SUBTOTAL | TOTAL
    raw_label: str = ""
    indent_depth: int = 0
    ancestor_path: Tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class LogicalColumn:
    """A logical column with ordered canonical header ancestry path."""
    column_id: str
    position: int
    header_path: Tuple[str, ...]         # Contract C6: Complete ordered header ancestry
    role: str = "DATA"                   # ROW_HEADER | DATA | UNIT | ANNOTATION
    data_type: Optional[str] = "NUMERIC"


@dataclass(frozen=True)
class HeaderNode:
    """A single hierarchical header block in the column tree."""
    header_id: str
    label: str
    level: int                           # 1 = root super-header, 2 = sub-header, etc.
    col_start: int
    col_end: int
    parent_header_id: Optional[str] = None
    footnote_ids: Tuple[str, ...] = field(default_factory=tuple)
    bbox: Optional[BoundingBox] = None


@dataclass(frozen=True)
class TableFragment:
    """A physical table fragment located on a specific document page."""
    fragment_id: str
    page_id: str
    row_count: int
    column_count: int
    cells: Tuple[CellNode, ...] = field(default_factory=tuple)
    rows: Tuple[LogicalRow, ...] = field(default_factory=tuple)
    columns: Tuple[LogicalColumn, ...] = field(default_factory=tuple)
    headers: Tuple[HeaderNode, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class LogicalTable:
    """
    Contract C17: Validated multi-fragment logical table assembly.
    Preserves original physical fragments while providing an assembled view.
    """
    table_id: str
    fragment_ids: Tuple[str, ...]
    is_stitched: bool = False
    continuation_evidence_id: Optional[str] = None

