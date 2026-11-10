"""
PCC-Tensor 3.1: Chunker Package.
Provides relation-preserving semantic table chunking with coordinate closure and dual representation.
"""

from .relation_preserving_chunker import (
    RelationPreservingTableChunker,
    RelationPreservingChunk,
    TableChunkECC,
)

__all__ = [
    "RelationPreservingTableChunker",
    "RelationPreservingChunk",
    "TableChunkECC",
]

