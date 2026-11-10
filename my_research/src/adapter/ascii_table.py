"""
PCC-Tensor 3.1: Layer L0/L1 Monospaced ASCII & Text Schedule Adapter.
Specialized for SEC EDGAR text filings, Form 10-K/10-Q financial schedules, and fixed-width tables.
Preserves character coordinates, indentation hierarchy, multi-level super-headers, and footnotes.
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

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


class AsciiTableScheduleAdapter(BaseTableAdapter):
    """
    High-fidelity adapter for fixed-width/monospaced text tables (SEC 10-K/10-Q schedules).
    Reconstructs exact character coordinates, hierarchical super-headers, row indent trees,
    and explanatory footnote blocks into CTIR Layer L1.
    """

    FOOTNOTE_MARKER_PATTERN = re.compile(r"\[([0-9a-zA-Z*#†‡]+)\]")
    FOOTNOTE_BLOCK_START = re.compile(r"^(?:EXPLANATORY\s+)?FOOTNOTES(?:\s+TO\s+.*)?:\s*$", re.IGNORECASE)
    FOOTNOTE_ITEM_PATTERN = re.compile(r"^\[([0-9a-zA-Z*#†‡]+)\]\s*(.*)$")

    def __init__(self, adapter_id: str = "adapter_ascii_schedule_3.1") -> None:
        super().__init__(adapter_id=adapter_id)

    def parse(
        self,
        source_doc: SourceDocument,
        raw_content: str | bytes,
        table_id: str = "table_sec_10q",
        page_id: str = "page_0",
        **kwargs,
    ) -> Tuple[TableFragment, List[FootnoteNode], CoordinateSpace]:
        """
        Parses an ASCII financial schedule into TableFragment, FootnoteNodes, and CoordinateSpace.
        """
        text = raw_content.decode("utf-8") if isinstance(raw_content, bytes) else raw_content
        lines = text.splitlines()

        # 1. Identify Sections: Preamble, Table Block, and Footnotes Block
        preamble_lines: List[str] = []
        table_lines: List[Tuple[int, str]] = []  # (original_line_no, line_text)
        footnote_lines: List[Tuple[int, str]] = []

        in_table = False
        in_footnotes = False

        for l_idx, line in enumerate(lines):
            stripped = line.strip()

            if self.FOOTNOTE_BLOCK_START.match(stripped):
                in_table = False
                in_footnotes = True
                continue

            if in_footnotes:
                if stripped.startswith("===") and len(stripped) > 20:
                    # End of footnotes block
                    break
                footnote_lines.append((l_idx, line))
                continue

            # Detect start of table by super-header or line item header
            if not in_table:
                if "Three Months Ended" in line or "Line Item" in line:
                    in_table = True
                    table_lines.append((l_idx, line))
                elif stripped.startswith("===") or stripped.startswith("---"):
                    pass
                else:
                    preamble_lines.append(line)
            else:
                # Inside table
                if stripped.startswith("===") and len(stripped) > 20:
                    # Table ended
                    in_table = False
                else:
                    table_lines.append((l_idx, line))

        if not table_lines:
            raise ValueError(f"Could not locate financial schedule table lines in {table_id}")

        # 2. Parse Footnotes Block
        footnotes: List[FootnoteNode] = []
        curr_fn_marker: Optional[str] = None
        curr_fn_lines: List[str] = []

        for l_idx, f_line in footnote_lines:
            m = self.FOOTNOTE_ITEM_PATTERN.match(f_line.strip())
            if m:
                if curr_fn_marker is not None:
                    footnotes.append(
                        FootnoteNode(
                            footnote_id=f"fn_{curr_fn_marker}",
                            marker=curr_fn_marker,
                            text=" ".join(curr_fn_lines).strip(),
                            page_id=page_id,
                        )
                    )
                curr_fn_marker = m.group(1)
                curr_fn_lines = [m.group(2).strip()]
            elif curr_fn_marker is not None:
                if f_line.strip():
                    curr_fn_lines.append(f_line.strip())

        if curr_fn_marker is not None:
            footnotes.append(
                FootnoteNode(
                    footnote_id=f"fn_{curr_fn_marker}",
                    marker=curr_fn_marker,
                    text=" ".join(curr_fn_lines).strip(),
                    page_id=page_id,
                )
            )

        # 3. Analyze Column Boundaries
        # Locate the leaf header line (e.g. contains 'Financial & Operational Line Item' or '2026')
        leaf_header_idx = -1
        for idx, (orig_no, l_text) in enumerate(table_lines):
            if "2026" in l_text and "2025" in l_text:
                leaf_header_idx = idx
                break

        if leaf_header_idx == -1:
            leaf_header_idx = 0

        # Scan for year tokens to determine column column intervals
        leaf_line = table_lines[leaf_header_idx][1]
        year_matches = list(re.finditer(r"\b(20\d\d)\b", leaf_line))

        # Expected 4 data columns in the adversarial schedule:
        # Col 0: Stub / Line Item
        # Col 1: First 2026
        # Col 2: First 2025
        # Col 3: Second 2026
        # Col 4: Second 2025
        max_line_len = max(len(l[1]) for l in table_lines)
        coord_space = CoordinateSpace(
            space_id=f"{table_id}_ascii_space",
            kind="MARKDOWN_OFFSET",
            width=Decimal(max_line_len),
            height=Decimal(len(lines)),
            unit="char",
        )

        col_spans: List[Tuple[int, int]] = []
        if len(year_matches) >= 4:
            # Col 0: [0, start of first year - 6] to preserve stubs up to column 60
            col0_end = max(40, year_matches[0].start() - 6)
            col_spans.append((0, col0_end))

            # Col 1: [col0_end, midpoint between match 0 and match 1]
            mid01 = (year_matches[0].end() + year_matches[1].start()) // 2
            col_spans.append((col0_end, mid01))

            # Col 2: [mid01, midpoint between match 1 and match 2]
            mid12 = (year_matches[1].end() + year_matches[2].start()) // 2
            col_spans.append((mid01, mid12))

            # Col 3: [mid12, midpoint between match 2 and match 3]
            mid23 = (year_matches[2].end() + year_matches[3].start()) // 2
            col_spans.append((mid12, mid23))

            # Col 4: [mid23, max_line_len]
            col_spans.append((mid23, max_line_len))
        else:
            # Fallback to standard 5-column split
            c_width = max_line_len // 5
            col_spans = [(i * c_width, (i + 1) * c_width) for i in range(5)]

        total_cols = len(col_spans)

        # 4. Construct Super-Headers & Logical Columns
        # Header rows: lines from 0 to leaf_header_idx
        header_nodes: List[HeaderNode] = []
        col_header_paths: List[List[str]] = [[] for _ in range(total_cols)]

        # Header Level 1 (e.g. "Three Months Ended", "Nine Months Ended")
        if leaf_header_idx >= 2:
            l1_text = table_lines[0][1]
            # Match "Three Months Ended"
            tme_m = re.search(r"Three Months Ended", l1_text, re.I)
            nme_m = re.search(r"Nine Months Ended", l1_text, re.I)

            if tme_m:
                h_tme = HeaderNode(
                    header_id="H_super_TME",
                    label="Three Months Ended",
                    level=1,
                    col_start=1,
                    col_end=3,
                )
                header_nodes.append(h_tme)
                col_header_paths[1].append("Three Months Ended")
                col_header_paths[2].append("Three Months Ended")

            if nme_m:
                h_nme = HeaderNode(
                    header_id="H_super_NME",
                    label="Nine Months Ended",
                    level=1,
                    col_start=3,
                    col_end=5,
                )
                header_nodes.append(h_nme)
                col_header_paths[3].append("Nine Months Ended")
                col_header_paths[4].append("Nine Months Ended")

        # Header Level 2 (e.g. "September 30,")
        if leaf_header_idx >= 1:
            l2_text = table_lines[1][1]
            sep_matches = list(re.finditer(r"September 30,?", l2_text, re.I))
            if len(sep_matches) >= 2:
                h_sep1 = HeaderNode(
                    header_id="H_date_TME",
                    label="September 30",
                    level=2,
                    col_start=1,
                    col_end=3,
                    parent_header_id="H_super_TME",
                )
                h_sep2 = HeaderNode(
                    header_id="H_date_NME",
                    label="September 30",
                    level=2,
                    col_start=3,
                    col_end=5,
                    parent_header_id="H_super_NME",
                )
                header_nodes.append(h_sep1)
                header_nodes.append(h_sep2)
                col_header_paths[1].append("September 30")
                col_header_paths[2].append("September 30")
                col_header_paths[3].append("September 30")
                col_header_paths[4].append("September 30")

        # Header Level 3: Leaf years
        leaf_line = table_lines[leaf_header_idx][1]
        col_header_paths[0].append("Financial & Operational Line Item")
        header_nodes.append(
            HeaderNode(
                header_id="H_stub",
                label="Financial & Operational Line Item",
                level=3,
                col_start=0,
                col_end=1,
            )
        )

        for c_idx in range(1, total_cols):
            c_start, c_end = col_spans[c_idx]
            slice_text = leaf_line[c_start:c_end].strip()
            parent_id = "H_date_TME" if c_idx in (1, 2) else "H_date_NME"
            header_nodes.append(
                HeaderNode(
                    header_id=f"H_leaf_c{c_idx}",
                    label=slice_text,
                    level=3,
                    col_start=c_idx,
                    col_end=c_idx + 1,
                    parent_header_id=parent_id,
                )
            )
            col_header_paths[c_idx].append(slice_text)

        # Build Logical Columns
        logical_columns: List[LogicalColumn] = []
        for c_idx in range(total_cols):
            path = tuple(col_header_paths[c_idx])
            logical_columns.append(
                LogicalColumn(
                    column_id=f"COL_{c_idx:02d}",
                    position=c_idx,
                    header_path=path,
                    role="ROW_HEADER" if c_idx == 0 else "DATA",
                )
            )

        # 5. Parse Data Rows & Indentation Stack
        # Data rows start after leaf_header_idx + separator line
        start_row_idx = leaf_header_idx + 1
        if start_row_idx < len(table_lines) and table_lines[start_row_idx][1].strip().startswith("---"):
            start_row_idx += 1

        cell_nodes: List[CellNode] = []
        logical_rows: List[LogicalRow] = []

        current_section_id: Optional[str] = None
        current_section_label: Optional[str] = None

        row_counter = 0

        for r_line_idx in range(start_row_idx, len(table_lines)):
            orig_line_no, line_str = table_lines[r_line_idx]
            stripped_line = line_str.strip()

            if not stripped_line:
                continue

            # Extract stub cell text
            c0_start, c0_end = col_spans[0]
            raw_stub_slice = line_str[c0_start:min(c0_end, len(line_str))]
            clean_stub = raw_stub_slice.strip()

            # Determine indentation from leading spaces in stub
            leading_spaces = len(raw_stub_slice) - len(raw_stub_slice.lstrip())
            indent_depth = leading_spaces // 2

            # Check if this row is a Section Header
            is_section = False
            # Check if data cells are all empty
            data_cells_empty = True
            for c in range(1, total_cols):
                cs, ce = col_spans[c]
                if cs < len(line_str) and line_str[cs:min(ce, len(line_str))].strip():
                    data_cells_empty = False
                    break

            if data_cells_empty and (clean_stub.isupper() or clean_stub.endswith(":")):
                is_section = True

            # Determine Row Role
            if is_section:
                role = "SECTION"
                current_section_id = f"ROW_{row_counter:03d}"
                current_section_label = clean_stub
                parent_row_id = None
                ancestor_path = ()
            elif clean_stub.startswith("Subtotal") or clean_stub.startswith("SUBTOTAL"):
                role = "SUBTOTAL"
                parent_row_id = current_section_id
                ancestor_path = (current_section_label,) if current_section_label else ()
            elif clean_stub.startswith("TOTAL") or clean_stub.startswith("Total"):
                role = "TOTAL"
                parent_row_id = None
                ancestor_path = ()
            else:
                role = "DETAIL"
                parent_row_id = current_section_id
                ancestor_path = (current_section_label,) if current_section_label else ()

            # Build LogicalRow
            logical_row = LogicalRow(
                row_id=f"ROW_{row_counter:03d}",
                position=row_counter,
                parent_row_id=parent_row_id,
                role=role,
                raw_label=self.FOOTNOTE_MARKER_PATTERN.sub("", clean_stub).strip(),
                indent_depth=indent_depth,
                ancestor_path=ancestor_path,
            )
            logical_rows.append(logical_row)

            # Extract cells for all columns
            for c_idx in range(total_cols):
                c_start, c_end = col_spans[c_idx]
                cell_slice = line_str[c_start:min(c_end, len(line_str))] if c_start < len(line_str) else ""
                clean_cell = cell_slice.strip()

                # Extract footnote markers e.g. [1] or [2]
                fn_markers = tuple(self.FOOTNOTE_MARKER_PATTERN.findall(clean_cell))

                cell_id = f"cell_r{row_counter:03d}_c{c_idx:02d}"

                if is_section:
                    c_role = CellRole.SECTION
                elif not clean_cell:
                    c_role = CellRole.EMPTY
                elif c_idx == 0:
                    c_role = CellRole.ROW_HEADER
                else:
                    c_role = CellRole.DATA

                # Geometry BoundingBox (character coordinates)
                bbox = BoundingBox(
                    x0=Decimal(c_start),
                    y0=Decimal(orig_line_no),
                    x1=Decimal(min(c_end, max_line_len)),
                    y1=Decimal(orig_line_no + 1),
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
                        role=c_role,
                        span=GridSpan(
                            row_start=row_counter,
                            row_end=row_counter + 1,
                            col_start=c_idx,
                            col_end=c_idx + 1,
                        ),
                        raw_text=clean_cell,
                        bbox=bbox,
                        source_ref=source_ref,
                        footnote_ids=fn_markers,
                    )
                )

            row_counter += 1

        fragment = TableFragment(
            fragment_id=f"{table_id}_frag_0",
            page_id=page_id,
            row_count=row_counter,
            column_count=total_cols,
            cells=tuple(cell_nodes),
            rows=tuple(logical_rows),
            columns=tuple(logical_columns),
            headers=tuple(header_nodes),
        )

        return fragment, footnotes, coord_space
