"""
PCC-Tensor 3.1: Grid Geometry & Cell Span Invariants.
Enforces Contract C4 (Grid consistency) and prevents cell overlap.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GridSpan:
    """
    Rectangular span of a cell within a table grid [row_start, row_end) x [col_start, col_end).
    0-indexed, half-open interval.
    """
    row_start: int
    row_end: int
    col_start: int
    col_end: int

    def __post_init__(self) -> None:
        if self.row_start < 0 or self.col_start < 0:
            raise ValueError(f"Span coordinates must be non-negative: ({self.row_start}, {self.col_start})")
        if self.row_start >= self.row_end:
            raise ValueError(f"Invalid row span: row_start ({self.row_start}) >= row_end ({self.row_end})")
        if self.col_start >= self.col_end:
            raise ValueError(f"Invalid col span: col_start ({self.col_start}) >= col_end ({self.col_end})")

    @property
    def row_count(self) -> int:
        return self.row_end - self.row_start

    @property
    def col_count(self) -> int:
        return self.col_end - self.col_start

    def contains_slot(self, row: int, col: int) -> bool:
        return self.row_start <= row < self.row_end and self.col_start <= col < self.col_end


def spans_overlap(s1: GridSpan, s2: GridSpan) -> bool:
    """
    Contract C4: Two distinct source cells in the same grid cannot overlap:
    Span(c_i) ∩ Span(c_j) = ∅
    """
    row_overlap = max(s1.row_start, s2.row_start) < min(s1.row_end, s2.row_end)
    col_overlap = max(s1.col_start, s2.col_start) < min(s1.col_end, s2.col_end)
    return row_overlap and col_overlap

