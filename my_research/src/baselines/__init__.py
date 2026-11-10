"""
PCC-Tensor 3.1: Baselines Package.
Provides industry standard naive sliding-window and markdown row-group chunkers.
"""

from .naive_chunker import NaiveFixedWindowChunker, NaiveTextChunk
from .markdown_chunker import MarkdownRowGroupChunker, MarkdownRowChunk

__all__ = [
    "NaiveFixedWindowChunker",
    "NaiveTextChunk",
    "MarkdownRowGroupChunker",
    "MarkdownRowChunk",
]

