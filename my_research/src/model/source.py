"""
PCC-Tensor 3.1: Layer L0 — Source Evidence & Coordinate System Models.
Mathematical contracts for immutable source documents, coordinate spaces, and bounding boxes.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional, Tuple


@dataclass(frozen=True)
class SourceDocument:
    """Immutable original source document specification."""
    document_id: str
    sha256: str
    mime_type: str
    byte_length: int
    source_uri: Optional[str] = None
    schema_version: str = "3.1.0"

    @classmethod
    def from_bytes(cls, document_id: str, raw_bytes: bytes, mime_type: str, source_uri: Optional[str] = None) -> SourceDocument:
        digest = hashlib.sha256(raw_bytes).hexdigest()
        return cls(
            document_id=document_id,
            sha256=digest,
            mime_type=mime_type,
            byte_length=len(raw_bytes),
            source_uri=source_uri,
        )


@dataclass(frozen=True)
class CoordinateSpace:
    """
    Explicit geometric coordinate space definition.
    Supported kinds: PDF_POINT, IMAGE_PIXEL, NORMALIZED_PAGE, HTML_DOM, MARKDOWN_OFFSET.
    """
    space_id: str
    kind: str
    width: Decimal
    height: Decimal
    origin: str = "TOP_LEFT"  # TOP_LEFT or BOTTOM_LEFT
    unit: str = "pt"          # pt, px, norm, char
    rotation_degrees: int = 0
    transform_id: Optional[str] = None

    def __post_init__(self) -> None:
        if self.width <= Decimal(0) or self.height <= Decimal(0):
            raise ValueError(f"CoordinateSpace bounds must be positive: ({self.width}, {self.height})")


@dataclass(frozen=True)
class BoundingBox:
    """
    Geometric bounding box adhering to Contract C3:
    x0 < x1, y0 < y1, strictly contained within its CoordinateSpace.
    """
    x0: Decimal
    y0: Decimal
    x1: Decimal
    y1: Decimal
    coordinate_space_id: str

    def __post_init__(self) -> None:
        if self.x0 >= self.x1:
            raise ValueError(f"Invalid bounding box: x0 ({self.x0}) >= x1 ({self.x1})")
        if self.y0 >= self.y1:
            raise ValueError(f"Invalid bounding box: y0 ({self.y0}) >= y1 ({self.y1})")

    @property
    def width(self) -> Decimal:
        return self.x1 - self.x0

    @property
    def height(self) -> Decimal:
        return self.y1 - self.y0

    def is_contained_within(self, space: CoordinateSpace) -> bool:
        """Contract C3: Bounding box must lie within its declared coordinate-space bounds."""
        if self.coordinate_space_id != space.space_id:
            return False
        return (
            self.x0 >= Decimal(0) and
            self.y0 >= Decimal(0) and
            self.x1 <= space.width and
            self.y1 <= space.height
        )

    def to_tuple(self) -> Tuple[float, float, float, float]:
        return (float(self.x0), float(self.y0), float(self.x1), float(self.y1))


@dataclass(frozen=True)
class SourceRef:
    """Immutable link back to original document evidence."""
    document_hash: str
    page_id: Optional[str]
    region_id: str
    evidence_id: str

