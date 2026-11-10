"""
PCC-Tensor 3.1: Unit & Integration Tests for Format Adapters.
Tests Markdown Lexer, HTML DOM, PDF Geometry, and ASCII Schedule Adapters.
"""

from __future__ import annotations

import io
import pathlib
from decimal import Decimal
import pytest
import pymupdf

DATA_DIR = pathlib.Path(__file__).resolve().parent.parent / "data"

from my_research.src.adapter.base import BaseTableAdapter
from my_research.src.adapter.markdown_lexer import MarkdownTableLexer
from my_research.src.adapter.html_dom import HtmlDomAdapter
from my_research.src.adapter.pdf_adapter import PdfGeometryAdapter
from my_research.src.adapter.ascii_table import AsciiTableScheduleAdapter
from my_research.src.model.source import SourceDocument
from my_research.src.model.structural import CellRole
from my_research.src.model.geometry import spans_overlap


# ==============================================================================
# Markdown Lexer Tests
# ==============================================================================
def test_markdown_lexer_escaped_pipes_and_math():
    raw_md = """
| Metric | Formula \\| Details | Target |
| :--- | :---: | ---: |
| Revenue | $|x| + |y|$ | $100M [1] |
| Net Income | `code | pipe` | $10M |

[1]: Verified audited revenues.
"""
    doc, _ = BaseTableAdapter.create_source_document("doc_md_01", raw_md, "text/markdown")
    adapter = MarkdownTableLexer()
    frag, footnotes, coord_space = adapter.parse(doc, raw_md, table_id="t_md_01")

    assert coord_space is not None and coord_space.kind == "MARKDOWN_OFFSET"
    assert frag.column_count == 3
    assert frag.row_count == 3  # 1 header + 2 data rows
    assert len(frag.cells) == 9

    # Check escaped pipe handled without creating extra columns
    header_cells = [c for c in frag.cells if c.span.row_start == 0]
    assert len(header_cells) == 3
    assert "Formula \\| Details" in header_cells[1].raw_text

    # Check math and code span preserved
    r1_cells = [c for c in frag.cells if c.span.row_start == 1]
    assert r1_cells[1].raw_text == "$|x| + |y|$"
    assert "1" in r1_cells[2].footnote_ids

    # Check footnote definition extracted
    assert len(footnotes) == 1
    assert footnotes[0].marker == "1"
    assert "audited revenues" in footnotes[0].text


def test_markdown_lexer_bounding_boxes():
    raw_md = "| A | B |\n|---|---|\n| 1 | 2 |"
    doc, _ = BaseTableAdapter.create_source_document("doc_md_02", raw_md, "text/markdown")
    adapter = MarkdownTableLexer()
    frag, _, coord_space = adapter.parse(doc, raw_md, table_id="t_md_02")
    assert coord_space is not None

    for cell in frag.cells:
        assert cell.bbox is not None
        assert cell.bbox.x0 < cell.bbox.x1
        assert cell.bbox.y0 < cell.bbox.y1


# ==============================================================================
# HTML DOM Adapter Tests
# ==============================================================================
def test_html_dom_rowspan_and_colspan_occupancy():
    html_content = """
    <table>
      <thead>
        <tr>
          <th rowspan="2">Category</th>
          <th colspan="2">2026 Performance</th>
        </tr>
        <tr>
          <th>Q1</th>
          <th>Q2</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td style="padding-left: 20px;">Product A [1]</td>
          <td>150</td>
          <td>200</td>
        </tr>
      </tbody>
    </table>
    <div class="footnote">[1] Audited product numbers.</div>
    """
    doc, _ = BaseTableAdapter.create_source_document("doc_html_01", html_content, "text/html")
    adapter = HtmlDomAdapter()
    frag, footnotes, coord_space = adapter.parse(doc, html_content, table_id="t_html_01")

    assert coord_space is not None and coord_space.kind == "HTML_DOM"
    assert frag.column_count == 3
    assert frag.row_count == 3

    # Check Category cell span (rowspan=2, colspan=1)
    cat_cell = next(c for c in frag.cells if "Category" in c.raw_text)
    assert cat_cell.span.row_start == 0
    assert cat_cell.span.row_end == 2
    assert cat_cell.span.col_start == 0
    assert cat_cell.span.col_end == 1

    # Check 2026 Performance cell span (rowspan=1, colspan=2)
    perf_cell = next(c for c in frag.cells if "2026 Performance" in c.raw_text)
    assert perf_cell.span.row_start == 0
    assert perf_cell.span.row_end == 1
    assert perf_cell.span.col_start == 1
    assert perf_cell.span.col_end == 3

    # Check Q1 and Q2 in row 1
    q1_cell = next(c for c in frag.cells if c.raw_text == "Q1")
    assert q1_cell.span.row_start == 1
    assert q1_cell.span.col_start == 1

    # Check that no two cells overlap
    for i, c1 in enumerate(frag.cells):
        for j, c2 in enumerate(frag.cells):
            if i != j:
                assert not spans_overlap(c1.span, c2.span), f"Overlap between {c1.cell_id} and {c2.cell_id}"

    # Check indentation depth on Product A
    row_2 = next(r for r in frag.rows if r.position == 2)
    assert row_2.indent_depth >= 1

    # Check footnote citation
    cell_prod = next(c for c in frag.cells if "Product A" in c.raw_text)
    assert "1" in cell_prod.footnote_ids
    assert len(footnotes) == 1
    assert footnotes[0].marker == "1"


# ==============================================================================
# PDF Geometry Adapter Tests
# ==============================================================================
def test_pdf_geometry_adapter():
    # Build a synthetic PDF in memory with PyMuPDF
    pdf_doc = pymupdf.open()
    page = pdf_doc.new_page(width=612, height=792)  # Standard Letter size

    # Draw a table with lines
    page.draw_rect(pymupdf.Rect(50, 50, 450, 150))
    page.draw_line(pymupdf.Point(50, 80), pymupdf.Point(450, 80))
    page.draw_line(pymupdf.Point(200, 50), pymupdf.Point(200, 150))

    page.insert_text((60, 70), "Line Item")
    page.insert_text((220, 70), "Value 2026")
    page.insert_text((60, 110), "Revenues")
    page.insert_text((220, 110), "945.10")

    pdf_bytes = pdf_doc.tobytes()
    pdf_doc.close()

    doc, _ = BaseTableAdapter.create_source_document("doc_pdf_01", pdf_bytes, "application/pdf")
    adapter = PdfGeometryAdapter()
    frag, footnotes, coord_space = adapter.parse(doc, pdf_bytes, table_id="t_pdf_01")

    assert coord_space is not None and coord_space.kind == "PDF_POINT"
    assert frag.row_count >= 2
    assert frag.column_count >= 2
    for cell in frag.cells:
        if cell.bbox is not None:
            assert cell.bbox.x0 < cell.bbox.x1
            assert cell.bbox.y0 < cell.bbox.y1


# ==============================================================================
# ASCII Schedule Adapter Tests on SEC 10-K Adversarial Schedule
# ==============================================================================
def test_ascii_schedule_adapter_on_adversarial_schedule():
    schedule_path = DATA_DIR / "sec_10k_adversarial_schedule.txt"
    with open(schedule_path, "r", encoding="utf-8") as f:
        content = f.read()

    doc, _ = BaseTableAdapter.create_source_document("doc_sec_01", content, "text/plain")
    adapter = AsciiTableScheduleAdapter()
    frag, footnotes, coord_space = adapter.parse(doc, content, table_id="sec_10q_adversarial")

    assert coord_space is not None and coord_space.kind == "MARKDOWN_OFFSET"
    assert frag.column_count == 5
    assert frag.row_count > 40

    # 1. Verify Super-Header Structure & Disambiguation
    # Col 1: Three Months Ended September 30 2026
    # Col 2: Three Months Ended September 30 2025
    # Col 3: Nine Months Ended September 30 2026
    # Col 4: Nine Months Ended September 30 2025
    col1 = frag.columns[1]
    col2 = frag.columns[2]
    col3 = frag.columns[3]
    col4 = frag.columns[4]

    assert "Three Months Ended" in col1.header_path
    assert "2026" in col1.header_path
    assert "Three Months Ended" in col2.header_path
    assert "2025" in col2.header_path

    assert "Nine Months Ended" in col3.header_path
    assert "2026" in col3.header_path
    assert "Nine Months Ended" in col4.header_path
    assert "2025" in col4.header_path

    # Verify Col 1 != Col 3 even though both have year 2026!
    assert col1.header_path != col3.header_path

    # 2. Verify Footnotes extraction
    assert len(footnotes) == 5
    fn_markers = [fn.marker for fn in footnotes]
    assert "1" in fn_markers
    assert "2" in fn_markers
    assert "3" in fn_markers
    assert "4" in fn_markers
    assert "5" in fn_markers

    # 3. Verify Footnote [1] contains royalty drop text
    fn_1 = next(fn for fn in footnotes if fn.marker == "1")
    assert "Amended IP Master Agreement" in fn_1.text
    assert "6.25% to 1.80%" in fn_1.text

    # 4. Verify Footnote [2] contains lithography arbitration
    fn_2 = next(fn for fn in footnotes if fn.marker == "2")
    assert "lithography photomask recalibration" in fn_2.text

    # 5. Check in-cell footnote links
    # Royalty row should link to footnote 1
    royalty_cell = next(c for c in frag.cells if "Royalty & IP Licensing Income" in c.raw_text)
    assert "1" in royalty_cell.footnote_ids

    # Photomask row should link to footnote 2
    photomask_cell = next(c for c in frag.cells if "Lithography Photomask Recalibration" in c.raw_text)
    assert "2" in photomask_cell.footnote_ids

    # 6. Check Section & Indentation hierarchy
    sec_rows = [r for r in frag.rows if r.role == "SECTION"]
    assert len(sec_rows) >= 5

    subtotal_rows = [r for r in frag.rows if r.role == "SUBTOTAL"]
    assert len(subtotal_rows) >= 2
    for s_row in subtotal_rows:
        assert s_row.parent_row_id is not None

