"""
PCC-Tensor 3.1: Adapter Package.
Provides format-specific adapters converting raw documents (Markdown, HTML, PDF, ASCII)
into standardized CTIR Layer L0/L1 TableFragments.
"""

from .base import BaseTableAdapter
from .markdown_lexer import MarkdownTableLexer
from .html_dom import HtmlDomAdapter
from .pdf_adapter import PdfGeometryAdapter
from .ascii_table import AsciiTableScheduleAdapter

__all__ = [
    "BaseTableAdapter",
    "MarkdownTableLexer",
    "HtmlDomAdapter",
    "PdfGeometryAdapter",
    "AsciiTableScheduleAdapter",
]

