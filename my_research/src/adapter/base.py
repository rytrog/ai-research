"""
PCC-Tensor 3.1: Base Table Adapter & Common Adapter Protocols.
Provides shared utilities, coordinate spaces, and abstract interface for all input adapters.
"""

from __future__ import annotations

import abc
import hashlib
from typing import List, Optional, Tuple

from ..model.source import BoundingBox, CoordinateSpace, SourceDocument, SourceRef
from ..model.structural import LogicalTable, TableFragment
from ..model.graph import FootnoteNode


class BaseTableAdapter(abc.ABC):
    """
    Abstract interface for document format adapters.
    Each adapter ingests raw format content and emits validated TableFragments and Footnotes.
    """

    def __init__(self, adapter_id: str) -> None:
        self.adapter_id = adapter_id

    @abc.abstractmethod
    def parse(
        self,
        source_doc: SourceDocument,
        raw_content: str | bytes,
        table_id: str = "table_0",
        page_id: str = "page_0",
        **kwargs,
    ) -> Tuple[TableFragment, List[FootnoteNode], CoordinateSpace]:
        """
        Parse raw table representation into a CTIR TableFragment, footnotes, and genuine CoordinateSpace.
        """
        raise NotImplementedError

    @staticmethod
    def create_source_document(
        document_id: str,
        content: str | bytes,
        mime_type: str,
        source_uri: Optional[str] = None,
    ) -> Tuple[SourceDocument, bytes]:
        """Utility to construct a SourceDocument with verified SHA-256 hash."""
        raw_bytes = content.encode("utf-8") if isinstance(content, str) else content
        doc = SourceDocument.from_bytes(
            document_id=document_id,
            raw_bytes=raw_bytes,
            mime_type=mime_type,
            source_uri=source_uri,
        )
        return doc, raw_bytes

    @staticmethod
    def build_source_ref(
        doc_hash: str,
        page_id: Optional[str],
        region_id: str,
        evidence_id: str,
    ) -> SourceRef:
        """Utility to construct an immutable SourceRef."""
        return SourceRef(
            document_hash=doc_hash,
            page_id=page_id,
            region_id=region_id,
            evidence_id=evidence_id,
        )

