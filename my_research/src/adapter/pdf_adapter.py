"""
PCC-Tensor 3.1: Layer L0/L1 PDF Geometry Table Adapter.
Extracts tabular structures from digital PDFs using PyMuPDF, preserving typographic point
bounding boxes, multi-line headers, and footnote citations into CTIR Layer L1.
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import List, Optional, Tuple
import pymupdf

from ..model.geometry import GridSpan
from ..model.graph import FootnoteNode
from ..model.source import BoundingBox, CoordinateSpace, SourceDocument, SourceRef
from ..model.structural import (
    CellNode,
    CellRole,
    HeaderNode,
    LogicalColumn,
    LogicalRow,
    TableFragment,
)
from .base import BaseTableAdapter


class PdfGeometryAdapter(BaseTableAdapter):
    """
    Geometry-preserving PDF Table Adapter.
    Extracts cell coordinates directly in point space (72 pt/inch) adhering to Contract C3.
    """

    FOOTNOTE_PATTERN = re.compile(r"\[(?:\^)?([0-9a-zA-Z*#†‡]+)\]")

    def __init__(self, adapter_id: str = "adapter_pymupdf_geometry_3.1") -> None:
        super().__init__(adapter_id=adapter_id)

    def parse(
        self,
        source_doc: SourceDocument,
        raw_content: str | bytes,
        table_id: str = "table_0",
        page_id: str = "page_0",
        page_number: int = 0,
        **kwargs,
    ) -> Tuple[TableFragment, List[FootnoteNode], CoordinateSpace]:
        """
        Parses a PDF byte stream or path, extracting the table on page_number into a TableFragment, Footnotes, and CoordinateSpace.
        """
        if isinstance(raw_content, str):
            doc = pymupdf.open(raw_content)
        else:
            doc = pymupdf.open(stream=raw_content, filetype="pdf")

        if page_number >= len(doc):
            raise IndexError(f"Page number {page_number} exceeds PDF page count {len(doc)}")

        page = doc[page_number]
        rect = page.rect
        page_w = Decimal(str(round(rect.width, 2)))
        page_h = Decimal(str(round(rect.height, 2)))

        coord_space = CoordinateSpace(
            space_id=f"{table_id}_pdf_space",
            kind="PDF_POINT",
            width=page_w,
            height=page_h,
            unit="pt",
        )

        # 1. Attempt table extraction via PyMuPDF TableFinder
        tables = page.find_tables()
        footnotes: List[FootnoteNode] = []

        if tables.tables:
            # Use detected vector table
            t = tables[0]
            extracted_matrix = t.extract()
            row_count = len(t.rows)
            col_count = t.col_count

            cell_nodes: List[CellNode] = []
            logical_rows: List[LogicalRow] = []
            logical_cols: List[LogicalColumn] = []
            header_nodes: List[HeaderNode] = []

            # First row as header by default unless specified
            header_row_count = 1

            # Build columns
            for c in range(col_count):
                h_text = extracted_matrix[0][c] if extracted_matrix and c < len(extracted_matrix[0]) and extracted_matrix[0][c] else f"Col_{c}"
                clean_h = self.FOOTNOTE_PATTERN.sub("", h_text).strip()
                logical_cols.append(
                    LogicalColumn(
                        column_id=f"COL_{c:02d}",
                        position=c,
                        header_path=(clean_h,),
                        role="ROW_HEADER" if c == 0 else "DATA",
                    )
                )
                header_nodes.append(
                    HeaderNode(
                        header_id=f"H_0_c{c}",
                        label=clean_h,
                        level=1,
                        col_start=c,
                        col_end=c + 1,
                    )
                )

            # Build rows and cells
            for r_idx, row in enumerate(t.rows):
                row_raw_label = ""
                if extracted_matrix and r_idx < len(extracted_matrix) and extracted_matrix[r_idx]:
                    row_raw_label = extracted_matrix[r_idx][0] or ""

                logical_rows.append(
                    LogicalRow(
                        row_id=f"ROW_{r_idx:03d}",
                        position=r_idx,
                        parent_row_id=None,
                        role="HEADER" if r_idx < header_row_count else "DETAIL",
                        raw_label=self.FOOTNOTE_PATTERN.sub("", row_raw_label).strip(),
                    )
                )

                for c_idx, cell_bbox in enumerate(row.cells):
                    raw_val = ""
                    if extracted_matrix and r_idx < len(extracted_matrix) and c_idx < len(extracted_matrix[r_idx]):
                        raw_val = extracted_matrix[r_idx][c_idx] or ""

                    cell_id = f"cell_r{r_idx:03d}_c{c_idx:02d}"
                    fn_markers = tuple(self.FOOTNOTE_PATTERN.findall(raw_val))
                    clean_val = raw_val.strip()

                    bbox = None
                    if cell_bbox is not None:
                        # PyMuPDF bbox: (x0, y0, x1, y1)
                        bx0 = max(Decimal(0), min(Decimal(str(round(cell_bbox[0], 2))), page_w - Decimal("0.01")))
                        by0 = max(Decimal(0), min(Decimal(str(round(cell_bbox[1], 2))), page_h - Decimal("0.01")))
                        bx1 = min(page_w, max(bx0 + Decimal("0.01"), Decimal(str(round(cell_bbox[2], 2)))))
                        by1 = min(page_h, max(by0 + Decimal("0.01"), Decimal(str(round(cell_bbox[3], 2)))))
                        bbox = BoundingBox(
                            x0=bx0,
                            y0=by0,
                            x1=bx1,
                            y1=by1,
                            coordinate_space_id=coord_space.space_id,
                        )

                    role = CellRole.HEADER if r_idx < header_row_count else (
                        CellRole.ROW_HEADER if c_idx == 0 else (
                            CellRole.EMPTY if not clean_val else CellRole.DATA
                        )
                    )

                    source_ref = self.build_source_ref(
                        doc_hash=source_doc.sha256,
                        page_id=page_id,
                        region_id=table_id,
                        evidence_id=cell_id,
                    )

                    cell_nodes.append(
                        CellNode(
                            cell_id=cell_id,
                            role=role,
                            span=GridSpan(
                                row_start=r_idx,
                                row_end=r_idx + 1,
                                col_start=c_idx,
                                col_end=c_idx + 1,
                            ),
                            raw_text=clean_val,
                            bbox=bbox,
                            source_ref=source_ref,
                            footnote_ids=fn_markers,
                        )
                    )

            fragment = TableFragment(
                fragment_id=f"{table_id}_frag_0",
                page_id=page_id,
                row_count=row_count,
                column_count=col_count,
                cells=tuple(cell_nodes),
                rows=tuple(logical_rows),
                columns=tuple(logical_cols),
                headers=tuple(header_nodes),
            )
            doc.close()
            return fragment, footnotes, coord_space

        # 2. Fallback: Word clustering when no line borders exist
        words = page.get_text("words")
        # Sort words primarily by vertical y0, secondarily by x0
        words_sorted = sorted(words, key=lambda w: (round(w[1] / 8) * 8, w[0]))

        # Group words into visual lines
        lines: List[List[Tuple[float, float, float, float, str]]] = []
        curr_line: List[Tuple[float, float, float, float, str]] = []
        curr_y: Optional[float] = None
        y_tolerance = 4.0

        for w in words_sorted:
            x0, y0, x1, y1, text = w[0], w[1], w[2], w[3], w[4]
            if curr_y is None or abs(y0 - curr_y) <= y_tolerance:
                curr_line.append((x0, y0, x1, y1, text))
                if curr_y is None:
                    curr_y = y0
            else:
                lines.append(curr_line)
                curr_line = [(x0, y0, x1, y1, text)]
                curr_y = y0
        if curr_line:
            lines.append(curr_line)

        # Basic tabular grid creation from lines
        cell_nodes_fb: List[CellNode] = []
        logical_rows_fb: List[LogicalRow] = []
        header_nodes_fb: List[HeaderNode] = []
        logical_cols_fb: List[LogicalColumn] = []

        total_r = len(lines)
        max_c = max((len(l) for l in lines), default=1)

        for c in range(max_c):
            logical_cols_fb.append(
                LogicalColumn(
                    column_id=f"COL_{c:02d}",
                    position=c,
                    header_path=(f"Column_{c}",),
                    role="ROW_HEADER" if c == 0 else "DATA",
                )
            )

        for r_idx, line_words in enumerate(lines):
            row_label = line_words[0][4] if line_words else ""
            logical_rows_fb.append(
                LogicalRow(
                    row_id=f"ROW_{r_idx:03d}",
                    position=r_idx,
                    parent_row_id=None,
                    role="HEADER" if r_idx == 0 else "DETAIL",
                    raw_label=row_label,
                )
            )

            for c_idx in range(max_c):
                cell_id = f"cell_r{r_idx:03d}_c{c_idx:02d}"
                if c_idx < len(line_words):
                    wx0, wy0, wx1, wy1, wtext = line_words[c_idx]
                    bbox = BoundingBox(
                        x0=Decimal(str(round(wx0, 2))),
                        y0=Decimal(str(round(wy0, 2))),
                        x1=Decimal(str(round(wx1, 2))),
                        y1=Decimal(str(round(wy1, 2))),
                        coordinate_space_id=coord_space.space_id,
                    )
                    cell_text = wtext
                else:
                    bbox = None
                    cell_text = ""

                source_ref = self.build_source_ref(
                    doc_hash=source_doc.sha256,
                    page_id=page_id,
                    region_id=table_id,
                    evidence_id=cell_id,
                )

                cell_nodes_fb.append(
                    CellNode(
                        cell_id=cell_id,
                        role=CellRole.HEADER if r_idx == 0 else (CellRole.ROW_HEADER if c_idx == 0 else CellRole.DATA),
                        span=GridSpan(
                            row_start=r_idx,
                            row_end=r_idx + 1,
                            col_start=c_idx,
                            col_end=c_idx + 1,
                        ),
                        raw_text=cell_text,
                        bbox=bbox,
                        source_ref=source_ref,
                    )
                )

        fragment = TableFragment(
            fragment_id=f"{table_id}_frag_0",
            page_id=page_id,
            row_count=total_r,
            column_count=max_c,
            cells=tuple(cell_nodes_fb),
            rows=tuple(logical_rows_fb),
            columns=tuple(logical_cols_fb),
            headers=tuple(header_nodes_fb),
        )

        doc.close()
        return fragment, footnotes, coord_space

