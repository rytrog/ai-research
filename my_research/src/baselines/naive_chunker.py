"""
PCC-Tensor 3.1: Industry Standard Naive Fixed-Window Chunker Baseline.
Simulates standard LangChain / LlamaIndex RecursiveCharacterTextSplitter (512 chars, 64 overlap).
Slices raw documents without table geometry, header restoration, or unit preservation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Tuple


@dataclass(frozen=True)
class NaiveTextChunk:
    chunk_id: str
    chunk_index: int
    text: str
    char_start: int
    char_end: int


class NaiveFixedWindowChunker:
    """
    Simulates standard RAG sliding-window chunking.
    Demonstrates Header Severance, Unit Severance, and Footnote Severance.
    """

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 64) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_text(self, text: str) -> List[NaiveTextChunk]:
        chunks: List[NaiveTextChunk] = []
        start = 0
        text_len = len(text)
        idx = 0

        while start < text_len:
            end = min(start + self.chunk_size, text_len)
            chunk_slice = text[start:end]

            chunks.append(
                NaiveTextChunk(
                    chunk_id=f"naive_chunk_{idx:03d}",
                    chunk_index=idx,
                    text=chunk_slice,
                    char_start=start,
                    char_end=end,
                )
            )
            idx += 1
            if end >= text_len:
                break
            start += self.chunk_size - self.chunk_overlap

        return chunks

    @staticmethod
    def retrieve_top_k(query: str, chunks: List[NaiveTextChunk], top_k: int = 1) -> List[NaiveTextChunk]:
        """Simple lexical overlap retrieval for standard RAG."""
        q_tokens = set(re.findall(r"\w+", query.lower()))
        scored = []
        for ch in chunks:
            ch_tokens = set(re.findall(r"\w+", ch.text.lower()))
            overlap = len(q_tokens.intersection(ch_tokens))
            scored.append((overlap, ch))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [c for _, c in scored[:top_k]]

