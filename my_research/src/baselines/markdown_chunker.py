"""
PCC-Tensor 3.1: Standard Markdown Row-Group Chunker Baseline.
Slices Markdown table rows in small windows without reproducing global preambles,
multi-level superheaders, or bottom explanatory footnotes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Tuple


@dataclass(frozen=True)
class MarkdownRowChunk:
    chunk_id: str
    chunk_index: int
    text: str
    row_start: int
    row_end: int


class MarkdownRowGroupChunker:
    """
    Standard tabular chunker that splits tables by row count.
    Lacks multi-tier superheader reproduction, unit propagation, and footnote binding.
    """

    def __init__(self, rows_per_chunk: int = 5) -> None:
        self.rows_per_chunk = rows_per_chunk

    def chunk_markdown(self, markdown_text: str) -> List[MarkdownRowChunk]:
        lines = [l for l in markdown_text.splitlines() if l.strip()]
        # Filter table lines
        table_lines = [l for l in lines if "|" in l and not re.match(r"^\s*\|?\s*:?-+:?\s*\|?", l)]

        if not table_lines:
            return []

        chunks: List[MarkdownRowChunk] = []
        c_idx = 0

        for i in range(0, len(table_lines), self.rows_per_chunk):
            slice_lines = table_lines[i:i + self.rows_per_chunk]
            chunk_str = "\n".join(slice_lines)

            chunks.append(
                MarkdownRowChunk(
                    chunk_id=f"md_row_chunk_{c_idx:03d}",
                    chunk_index=c_idx,
                    text=chunk_str,
                    row_start=i,
                    row_end=min(i + self.rows_per_chunk, len(table_lines)),
                )
            )
            c_idx += 1

        return chunks

    @staticmethod
    def retrieve_top_k(query: str, chunks: List[MarkdownRowChunk], top_k: int = 1) -> List[MarkdownRowChunk]:
        """Lexical overlap retrieval for row chunks."""
        q_tokens = set(re.findall(r"\w+", query.lower()))
        scored = []
        for ch in chunks:
            ch_tokens = set(re.findall(r"\w+", ch.text.lower()))
            overlap = len(q_tokens.intersection(ch_tokens))
            scored.append((overlap, ch))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [c for _, c in scored[:top_k]]

