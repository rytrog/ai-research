"""
PCC-Tensor 3.1: Layer L0/L1 HTML DOM Table Adapter.
Extracts complex HTML tables with rowspan, colspan, CSS hierarchical indentation,
and nested sub-headers into CTIR TableFragment and Footnote nodes.
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Dict, List, Optional, Set, Tuple
from bs4 import BeautifulSoup, Tag

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


class HtmlDomAdapter(BaseTableAdapter):
    """
    Native HTML Table parser for SEC EDGAR, HTML 5, and web documents.
    Accurately tracks 2D slot occupancy across arbitrary rowspan and colspan combinations.
    """

    FOOTNOTE_PATTERN = re.compile(r"\[(?:\^)?([0-9a-zA-Z*#†‡]+)\]")
    INDENT_PX_PATTERN = re.compile(r"padding-left:\s*([0-9.]+)px", re.IGNORECASE)
    INDENT_PT_PATTERN = re.compile(r"padding-left:\s*([0-9.]+)pt", re.IGNORECASE)
    TEXT_INDENT_PATTERN = re.compile(r"text-indent:\s*([0-9.]+)pt", re.IGNORECASE)

    def __init__(self, adapter_id: str = "adapter_html_dom_3.1") -> None:
        super().__init__(adapter_id=adapter_id)

    @classmethod
    def _extract_indent_depth(cls, tag: Tag, raw_text: str) -> int:
        """Computes hierarchical indentation level from CSS styles and non-breaking spaces."""
        # 1. Non-breaking spaces at start of text
        nbsp_count = 0
        for ch in raw_text:
            if ch in ('\xa0', ' '):
                nbsp_count += 1
            else:
                break
        if nbsp_count >= 2:
            return nbsp_count // 2

        # 2. CSS style inspection
        style = tag.get("style", "")
        if style:
            px_m = cls.INDENT_PX_PATTERN.search(style)
            if px_m:
                px = float(px_m.group(1))
                return max(0, int(px // 10))

            pt_m = cls.INDENT_PT_PATTERN.search(style)
            if pt_m:
                pt = float(pt_m.group(1))
                return max(0, int(pt // 7))

            ti_m = cls.TEXT_INDENT_PATTERN.search(style)
            if ti_m:
                ti = float(ti_m.group(1))
                return max(0, int(ti // 7))

        return 0

    def parse(
        self,
        source_doc: SourceDocument,
        raw_content: str | bytes,
        table_id: str = "table_0",
        page_id: str = "page_0",
        **kwargs,
    ) -> Tuple[TableFragment, List[FootnoteNode], CoordinateSpace]:
        """
        Parses HTML string/bytes containing a <table> element into TableFragment, Footnotes, and CoordinateSpace.
        """
        html_str = raw_content.decode("utf-8") if isinstance(raw_content, bytes) else raw_content
        soup = BeautifulSoup(html_str, "html.parser")

        table_tag = soup.find("table")
        if table_tag is None or not isinstance(table_tag, Tag):
            raise ValueError(f"No <table> tag found in input for {table_id}")

        # Footnote definitions extraction (if present in <tfoot> or note elements)
        footnotes: List[FootnoteNode] = []
        for fn_p in soup.find_all(["p", "div"], class_=re.compile("footnote|note", re.I)):
            text = fn_p.get_text().strip()
            fn_m = self.FOOTNOTE_PATTERN.search(text)
            if fn_m:
                marker = fn_m.group(1)
                footnotes.append(
                    FootnoteNode(
                        footnote_id=f"fn_{marker}",
                        marker=marker,
                        text=text,
                        page_id=page_id,
                    )
                )

        # 2D Grid Occupancy Tracker: (row, col) -> bool
        occupied: Dict[Tuple[int, int], bool] = {}

        # Raw cell items: (r_start, r_end, c_start, c_end, text, tag, is_header)
        parsed_cells: List[Tuple[int, int, int, int, str, Tag, bool]] = []

        all_trs = table_tag.find_all("tr")
        max_col_found = 0

        for r_idx, tr in enumerate(all_trs):
            c_idx = 0
            cells_in_tr = tr.find_all(["th", "td"])

            for cell_tag in cells_in_tr:
                # Find next unoccupied column slot in this row
                while occupied.get((r_idx, c_idx), False):
                    c_idx += 1

                try:
                    rowspan = int(cell_tag.get("rowspan", 1))
                except (ValueError, TypeError):
                    rowspan = 1
                try:
                    colspan = int(cell_tag.get("colspan", 1))
                except (ValueError, TypeError):
                    colspan = 1

                rowspan = max(1, rowspan)
                colspan = max(1, colspan)

                r_start = r_idx
                r_end = r_idx + rowspan
                c_start = c_idx
                c_end = c_idx + colspan

                # Mark occupied slots
                for dr in range(rowspan):
                    for dc in range(colspan):
                        occupied[(r_idx + dr, c_idx + dc)] = True

                cell_text = cell_tag.get_text(separator=" ", strip=True)
                is_th = cell_tag.name.lower() == "th" or tr.find_parent("thead") is not None

                parsed_cells.append((r_start, r_end, c_start, c_end, cell_text, cell_tag, is_th))

                c_idx += colspan
                if c_end > max_col_found:
                    max_col_found = c_end

        total_rows = len(all_trs)
        total_cols = max_col_found if max_col_found > 0 else 1

        # Coordinate Space
        coord_space = CoordinateSpace(
            space_id=f"{table_id}_html_space",
            kind="HTML_DOM",
            width=Decimal(max(total_cols * 100, 100)),
            height=Decimal(max(total_rows * 30, 30)),
            unit="px",
        )

        # Detect Header Rows (rows that consist of <th> or are inside <thead>)
        header_rows_set: Set[int] = set()
        for r_start, r_end, c_start, c_end, text, tag, is_th in parsed_cells:
            if is_th:
                for r in range(r_start, r_end):
                    header_rows_set.add(r)

        # If no explicit <th> was found, default row 0 as header
        if not header_rows_set and total_rows > 0:
            header_rows_set.add(0)

        # Build HeaderNodes & Column Ancestry
        header_nodes: List[HeaderNode] = []
        col_header_paths: List[List[str]] = [[] for _ in range(total_cols)]

        for r_start, r_end, c_start, c_end, text, tag, is_th in parsed_cells:
            if r_start in header_rows_set:
                fn_markers = tuple(self.FOOTNOTE_PATTERN.findall(text))
                clean_text = self.FOOTNOTE_PATTERN.sub("", text).strip()
                h_id = f"H_r{r_start}_c{c_start}"

                # Link parent header if higher level header exists above
                parent_h_id = None
                for higher_h in header_nodes:
                    if higher_h.col_start <= c_start and higher_h.col_end >= c_end and higher_h.level < (r_start + 1):
                        parent_h_id = higher_h.header_id

                h_node = HeaderNode(
                    header_id=h_id,
                    label=clean_text,
                    level=r_start + 1,
                    col_start=c_start,
                    col_end=c_end,
                    parent_header_id=parent_h_id,
                    footnote_ids=fn_markers,
                )
                header_nodes.append(h_node)

                # Record into column paths
                for c in range(c_start, min(c_end, total_cols)):
                    col_header_paths[c].append(clean_text)

        # Build Logical Columns
        logical_columns: List[LogicalColumn] = []
        for c_idx in range(total_cols):
            path = tuple(col_header_paths[c_idx]) if col_header_paths[c_idx] else (f"Column_{c_idx}",)
            logical_columns.append(
                LogicalColumn(
                    column_id=f"COL_{c_idx:02d}",
                    position=c_idx,
                    header_path=path,
                    role="ROW_HEADER" if c_idx == 0 else "DATA",
                )
            )

        # Build Logical Rows
        logical_rows: List[LogicalRow] = []
        for r_idx in range(total_rows):
            is_header = r_idx in header_rows_set
            # Find the stub cell for this row
            stub_text = ""
            indent_depth = 0
            for r_s, r_e, c_s, c_e, text, tag, is_th in parsed_cells:
                if r_s == r_idx and c_s == 0:
                    stub_text = text
                    indent_depth = self._extract_indent_depth(tag, text)
                    break

            logical_rows.append(
                LogicalRow(
                    row_id=f"ROW_{r_idx:03d}",
                    position=r_idx,
                    parent_row_id=None,
                    role="HEADER" if is_header else "DETAIL",
                    raw_label=self.FOOTNOTE_PATTERN.sub("", stub_text).strip(),
                    indent_depth=indent_depth,
                    ancestor_path=(),
                )
            )

        # Build CellNodes
        cell_nodes: List[CellNode] = []
        for r_start, r_end, c_start, c_end, text, tag, is_th in parsed_cells:
            cell_id = f"cell_r{r_start:03d}_c{c_start:02d}"
            fn_markers = tuple(self.FOOTNOTE_PATTERN.findall(text))
            cleaned_text = text.strip()

            if r_start in header_rows_set:
                role = CellRole.HEADER
            elif not cleaned_text:
                role = CellRole.EMPTY
            elif c_start == 0:
                role = CellRole.ROW_HEADER
            else:
                role = CellRole.DATA

            bbox = BoundingBox(
                x0=Decimal(c_start * 100),
                y0=Decimal(r_start * 30),
                x1=Decimal(c_end * 100),
                y1=Decimal(r_end * 30),
                coordinate_space_id=coord_space.space_id,
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
                        row_start=r_start,
                        row_end=r_end,
                        col_start=c_start,
                        col_end=c_end,
                    ),
                    raw_text=cleaned_text,
                    bbox=bbox,
                    source_ref=source_ref,
                    footnote_ids=fn_markers,
                )
            )

        fragment = TableFragment(
            fragment_id=f"{table_id}_frag_0",
            page_id=page_id,
            row_count=total_rows,
            column_count=total_cols,
            cells=tuple(cell_nodes),
            rows=tuple(logical_rows),
            columns=tuple(logical_columns),
            headers=tuple(header_nodes),
        )

        return fragment, footnotes, coord_space

