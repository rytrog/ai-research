"""
PCC-Tensor 3.1: Grammar-Aware Markdown Table Lexer & Structural Adapter.
Parses complex Markdown tables preserving character coordinates, escaped characters,
math expressions, alignments, multi-level headers, and footnote citations into CTIR Layer L1.
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import List, Optional, Tuple

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


class MarkdownTableLexer(BaseTableAdapter):
    """
    Grammar-aware Markdown table lexer.
    Correctly parses escaped pipes (\\|), backtick code spans (`|`), and math environments ($|x|$).
    """

    FOOTNOTE_PATTERN = re.compile(r"\[(?:\^)?([0-9a-zA-Z*#†‡]+)\]")
    FOOTNOTE_DEF_PATTERN = re.compile(r"^\[(?:\^)?([0-9a-zA-Z*#†‡]+)\]:\s*(.*)$")
    DELIMITER_CELL_PATTERN = re.compile(r"^\s*:?-{1,}:?\s*$")

    def __init__(self, adapter_id: str = "adapter_markdown_gfm_3.1") -> None:
        super().__init__(adapter_id=adapter_id)

    @staticmethod
    def _lex_row_pipes(line: str) -> List[Tuple[int, int, str]]:
        """
        Scans a single line character-by-character, splitting into cell tokens
        only on unescaped, unquoted, non-math pipe '|' characters.
        Correctly handles multi-backtick spans (``code | pipe``) and multi-dollar math ($${x | y}$$).
        Returns a list of (start_col, end_col, cell_content).
        """
        cells: List[Tuple[int, int, str]] = []
        n = len(line)
        code_fence_len = 0
        math_delimiter_len = 0
        escaped = False

        delimiter_indices: List[int] = []
        i = 0
        while i < n:
            char = line[i]

            if escaped:
                escaped = False
                i += 1
                continue

            if char == "\\":
                escaped = True
                i += 1
                continue

            # Check backtick code span
            if char == "`":
                # Count consecutive backticks
                run_len = 0
                while (i + run_len) < n and line[i + run_len] == "`":
                    run_len += 1

                if code_fence_len == 0:
                    # Enter code span of length run_len
                    code_fence_len = run_len
                elif run_len == code_fence_len:
                    # Exit code span
                    code_fence_len = 0
                i += run_len
                continue

            # Check math delimiter ($ or $$) if not in code
            if char == "$" and code_fence_len == 0:
                dollar_run = 0
                while (i + dollar_run) < n and line[i + dollar_run] == "$":
                    dollar_run += 1

                if math_delimiter_len == 0:
                    math_delimiter_len = dollar_run
                elif dollar_run == math_delimiter_len:
                    math_delimiter_len = 0
                i += dollar_run
                continue

            # Check pipe delimiter outside code and math
            if char == "|" and code_fence_len == 0 and math_delimiter_len == 0:
                delimiter_indices.append(i)

            i += 1

        if not delimiter_indices:
            return [(0, n, line)]

        # Handle leading/trailing pipes
        has_leading = (delimiter_indices[0] == 0 or line[:delimiter_indices[0]].strip() == "")
        has_trailing = (delimiter_indices[-1] == n - 1 or line[delimiter_indices[-1] + 1:].strip() == "")

        indices = delimiter_indices[:]
        if not has_leading:
            indices = [-1] + indices
        if not has_trailing:
            indices = indices + [n]

        for idx in range(len(indices) - 1):
            c_start = indices[idx] + 1
            c_end = indices[idx + 1]
            raw_slice = line[c_start:c_end]
            cells.append((c_start, c_end, raw_slice))

        return cells

    @classmethod
    def _is_delimiter_row(cls, cells: List[Tuple[int, int, str]]) -> bool:
        """Determines if a row consists entirely of Markdown table separator patterns (e.g. :---:)."""
        if not cells:
            return False
        return all(cls.DELIMITER_CELL_PATTERN.match(cell[2]) for cell in cells)

    @staticmethod
    def _get_column_alignment(cell_str: str) -> str:
        s = cell_str.strip()
        starts_colon = s.startswith(":")
        ends_colon = s.endswith(":")
        if starts_colon and ends_colon:
            return "CENTER"
        if ends_colon:
            return "RIGHT"
        return "LEFT"

    def parse(
        self,
        source_doc: SourceDocument,
        raw_content: str | bytes,
        table_id: str = "table_0",
        page_id: str = "page_0",
        **kwargs,
    ) -> Tuple[TableFragment, List[FootnoteNode], CoordinateSpace]:
        """
        Parses Markdown text into a validated TableFragment, list of FootnoteNodes, and CoordinateSpace.
        """
        text = raw_content.decode("utf-8") if isinstance(raw_content, bytes) else raw_content
        lines = text.splitlines()

        table_lines: List[Tuple[int, str]] = []  # (line_no, line_text)
        footnote_defs: List[FootnoteNode] = []

        # 1. Separate table lines from trailing footnote definitions
        in_table = False
        for line_no, line in enumerate(lines):
            # Check for footnote definitions e.g. [1]: Footnote explanation
            fn_match = self.FOOTNOTE_DEF_PATTERN.match(line.strip())
            if fn_match:
                marker = fn_match.group(1)
                fn_text = fn_match.group(2).strip()
                footnote_defs.append(
                    FootnoteNode(
                        footnote_id=f"fn_{marker}",
                        marker=marker,
                        text=fn_text,
                        page_id=page_id,
                    )
                )
                continue

            # Detect lines containing table pipe markers
            if "|" in line:
                in_table = True
                table_lines.append((line_no, line))
            elif in_table and line.strip() == "":
                # Table block terminated by blank line; subsequent lines may have footnote definitions
                in_table = False

        if not table_lines:
            raise ValueError(f"No valid Markdown table lines found in input for {table_id}")

        # 2. Setup CoordinateSpace
        max_line_len = max(len(l) for _, l in table_lines) if table_lines else 80
        total_lines = len(lines)
        coord_space = CoordinateSpace(
            space_id=f"{table_id}_markdown_space",
            kind="MARKDOWN_OFFSET",
            width=Decimal(max(max_line_len, 1)),
            height=Decimal(max(total_lines, 1)),
            unit="char",
        )

        # 3. Lex all table rows
        raw_rows: List[Tuple[int, List[Tuple[int, int, str]]]] = []
        delimiter_row_index: Optional[int] = None

        for r_idx, (line_no, line_str) in enumerate(table_lines):
            tokens = self._lex_row_pipes(line_str)
            if delimiter_row_index is None and self._is_delimiter_row(tokens):
                delimiter_row_index = r_idx
            raw_rows.append((line_no, tokens))

        # Determine column count
        column_count = max(len(tokens) for _, tokens in raw_rows if not self._is_delimiter_row(tokens))

        # Alignments
        alignments: List[str] = ["LEFT"] * column_count
        if delimiter_row_index is not None:
            sep_tokens = raw_rows[delimiter_row_index][1]
            for c_idx in range(min(column_count, len(sep_tokens))):
                alignments[c_idx] = self._get_column_alignment(sep_tokens[c_idx][2])

        # Rows prior to delimiter are headers; if no delimiter, row 0 is header
        if delimiter_row_index is not None:
            header_row_indices = set(range(delimiter_row_index))
            body_row_indices = [i for i in range(len(raw_rows)) if i > delimiter_row_index]
        else:
            header_row_indices = {0}
            body_row_indices = list(range(1, len(raw_rows)))

        # 4. Extract headers & column ancestry
        # Accumulate header paths per column
        header_nodes: List[HeaderNode] = []
        col_header_paths: List[List[str]] = [[] for _ in range(column_count)]

        for h_row_idx in sorted(header_row_indices):
            line_no, tokens = raw_rows[h_row_idx]
            for c_idx in range(column_count):
                cell_text = tokens[c_idx][2].strip() if c_idx < len(tokens) else ""
                if cell_text:
                    h_id = f"H_r{h_row_idx}_c{c_idx}"
                    # Find footnote citations in header
                    fn_markers = tuple(self.FOOTNOTE_PATTERN.findall(cell_text))
                    clean_label = self.FOOTNOTE_PATTERN.sub("", cell_text).strip()
                    parent_id = None
                    if h_row_idx > 0 and col_header_paths[c_idx]:
                        parent_id = f"H_r{h_row_idx-1}_c{c_idx}"

                    h_node = HeaderNode(
                        header_id=h_id,
                        label=clean_label,
                        level=h_row_idx + 1,
                        col_start=c_idx,
                        col_end=c_idx + 1,
                        parent_header_id=parent_id,
                        footnote_ids=fn_markers,
                    )
                    header_nodes.append(h_node)
                    col_header_paths[c_idx].append(clean_label)

        # Build LogicalColumns
        logical_columns: List[LogicalColumn] = []
        for c_idx in range(column_count):
            path = tuple(col_header_paths[c_idx]) if col_header_paths[c_idx] else (f"Column_{c_idx}",)
            logical_columns.append(
                LogicalColumn(
                    column_id=f"COL_{c_idx:02d}",
                    position=c_idx,
                    header_path=path,
                    role="ROW_HEADER" if c_idx == 0 else "DATA",
                )
            )

        # 5. Extract cells and logical rows
        cell_nodes: List[CellNode] = []
        logical_rows: List[LogicalRow] = []

        # Process all rows (including headers and body, assigning grid row coordinates)
        logical_row_idx = 0
        for orig_r_idx, (line_no, tokens) in enumerate(raw_rows):
            if orig_r_idx == delimiter_row_index:
                continue

            is_header_row = orig_r_idx in header_row_indices
            row_label = ""
            if tokens:
                first_cell_raw = tokens[0][2].strip()
                row_label = self.FOOTNOTE_PATTERN.sub("", first_cell_raw).strip()

            logical_row = LogicalRow(
                row_id=f"ROW_{logical_row_idx:03d}",
                position=logical_row_idx,
                parent_row_id=None,
                role="HEADER" if is_header_row else "DETAIL",
                raw_label=row_label,
                indent_depth=0,
                ancestor_path=(),
            )
            logical_rows.append(logical_row)

            # Process cells in this row
            for c_idx in range(column_count):
                if c_idx < len(tokens):
                    start_char, end_char, cell_str = tokens[c_idx]
                else:
                    start_char, end_char, cell_str = max_line_len, max_line_len, ""

                trimmed = cell_str.strip()
                cell_id = f"cell_r{logical_row_idx:03d}_c{c_idx:02d}"

                # Footnotes
                fn_markers = tuple(self.FOOTNOTE_PATTERN.findall(trimmed))

                # Role classification
                if is_header_row:
                    role = CellRole.HEADER
                elif not trimmed:
                    role = CellRole.EMPTY
                elif c_idx == 0:
                    role = CellRole.ROW_HEADER
                else:
                    role = CellRole.DATA

                # Geometry BoundingBox (char units)
                bbox = None
                if end_char > start_char:
                    bbox = BoundingBox(
                        x0=Decimal(start_char),
                        y0=Decimal(line_no),
                        x1=Decimal(end_char),
                        y1=Decimal(line_no + 1),
                        coordinate_space_id=coord_space.space_id,
                    )
                else:
                    # Point dummy box for empty/synthetic cell
                    bbox = BoundingBox(
                        x0=Decimal(start_char),
                        y0=Decimal(line_no),
                        x1=Decimal(start_char + 1),
                        y1=Decimal(line_no + 1),
                        coordinate_space_id=coord_space.space_id,
                    )

                source_ref = self.build_source_ref(
                    doc_hash=source_doc.sha256,
                    page_id=page_id,
                    region_id=table_id,
                    evidence_id=cell_id,
                )

                cell_node = CellNode(
                    cell_id=cell_id,
                    role=role,
                    span=GridSpan(
                        row_start=logical_row_idx,
                        row_end=logical_row_idx + 1,
                        col_start=c_idx,
                        col_end=c_idx + 1,
                    ),
                    raw_text=trimmed,
                    bbox=bbox,
                    source_ref=source_ref,
                    footnote_ids=fn_markers,
                )
                cell_nodes.append(cell_node)

            logical_row_idx += 1

        fragment = TableFragment(
            fragment_id=f"{table_id}_frag_0",
            page_id=page_id,
            row_count=logical_row_idx,
            column_count=column_count,
            cells=tuple(cell_nodes),
            rows=tuple(logical_rows),
            columns=tuple(logical_columns),
            headers=tuple(header_nodes),
        )

        return fragment, footnote_defs, coord_space
