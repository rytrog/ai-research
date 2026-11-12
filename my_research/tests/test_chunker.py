"""
PCC-Tensor 3.1: Unit & Integration Tests for Relation-Preserving Table Chunker & Baselines.
Validates Invariant 1 (Coordinate Closure), Invariant 2 (Bifurcated Dual View),
Invariant 3 (Footnote Colocation), and Invariant 4 (Chunk Certificate ECC).
"""

from __future__ import annotations

import pathlib
from decimal import Decimal
import pytest

from my_research.src.adapter.ascii_table import AsciiTableScheduleAdapter
from my_research.src.adapter.base import BaseTableAdapter
from my_research.src.baselines.markdown_chunker import MarkdownRowGroupChunker
from my_research.src.baselines.naive_chunker import NaiveFixedWindowChunker
from my_research.src.chunker.relation_preserving_chunker import RelationPreservingTableChunker
from my_research.src.compiler.table_compiler import TableCompiler
from my_research.src.model.semantic import ScopeLevel, UnitAssertion

DATA_DIR = pathlib.Path(__file__).resolve().parent.parent / "data"


@pytest.fixture
def compiled_sec_snapshot():
    schedule_path = DATA_DIR / "sec_10k_adversarial_schedule.txt"
    with open(schedule_path, "r", encoding="utf-8") as f:
        content = f.read()

    doc, _ = BaseTableAdapter.create_source_document("doc_sec_test", content, "text/plain")
    adapter = AsciiTableScheduleAdapter()
    frag, footnotes, coord_space = adapter.parse(doc, content, table_id="t_sec_test")
    compiler = TableCompiler(
        table_default_unit=UnitAssertion(currency="USD", scale_exponent=6, source_scope=ScopeLevel.TABLE)
    )
    return compiler.compile(
        source_doc=doc,
        fragment=frag,
        footnotes=footnotes,
        entity_name="Chronos Technologies Group Inc.",
        snapshot_id="snap_chunker_test",
        coordinate_space=coord_space,
    )


# ==============================================================================
# Relation-Preserving Chunker Tests
# ==============================================================================
def test_relation_preserving_chunker_invariants(compiled_sec_snapshot):
    chunker = RelationPreservingTableChunker(max_rows_per_chunk=5, token_budget=512)
    chunks = chunker.chunk_snapshot(compiled_sec_snapshot)

    assert len(chunks) > 5

    for chunk in chunks:
        # Invariant 1: Complete Coordinate Closure
        assert "[DOCUMENT_TABLE:" in chunk.dense_text
        assert "[ENTITY: Chronos Technologies Group Inc.]" in chunk.dense_text
        assert "[GLOBAL_CONVENTION:" in chunk.dense_text
        assert "[ROW_HIERARCHY:" in chunk.dense_text

        # Invariant 2: Micro-Grid View with Re-injected Headers
        assert "| Line Item / Metric |" in chunk.markdown_microgrid
        assert "Three Months Ended" in chunk.markdown_microgrid
        assert "Nine Months Ended" in chunk.markdown_microgrid

        # Invariant 4: Chunk Certificate ECC
        assert chunk.certificate is not None
        assert len(chunk.certificate.content_sha256) == 64
        assert chunk.certificate.has_header_closure is True
        assert chunk.certificate.has_unit_closure is True
        assert chunk.certificate.token_estimate < 600


def test_footnote_colocation_in_relation_preserving_chunk(compiled_sec_snapshot):
    chunker = RelationPreservingTableChunker(max_rows_per_chunk=5)
    chunks = chunker.chunk_snapshot(compiled_sec_snapshot)

    # Find the chunk containing Lithography Photomask Recalibration Reserve (cites Footnote 2)
    photomask_chunk = next(
        ch for ch in chunks
        if any("Lithography Photomask" in f.coordinates.raw_metric_label for f in ch.structured_facts)
    )

    # Footnote 2 MUST be colocated directly in this chunk!
    assert len(photomask_chunk.colocated_footnotes) >= 1
    fn2 = next(fn for fn in photomask_chunk.colocated_footnotes if fn.marker == "2")
    assert "lithography photomask recalibration" in fn2.text
    assert "[COLOCATED_FOOTNOTES_IN_CHUNK]:" in photomask_chunk.dense_text
    assert "[2] Represents accrual for reimbursable lithography" in photomask_chunk.dense_text


def test_naive_chunker_header_severance():
    schedule_path = DATA_DIR / "sec_10k_adversarial_schedule.txt"
    with open(schedule_path, "r", encoding="utf-8") as f:
        content = f.read()

    naive = NaiveFixedWindowChunker(chunk_size=512, chunk_overlap=64)
    chunks = naive.chunk_text(content)

    assert len(chunks) > 10

    # Retrieve chunk for Operating Income
    retrieved = naive.retrieve_top_k("Operating Income Loss EBIT", chunks, top_k=1)
    assert len(retrieved) == 1
    top_chunk = retrieved[0]

    # Fatal Naive Defect: The retrieved chunk does NOT have the column headers!
    assert "Three Months Ended" not in top_chunk.text
    assert "Nine Months Ended" not in top_chunk.text
    # Fatal Naive Defect: The retrieved chunk does NOT have the scale declaration!
    assert "in millions of U.S. Dollars" not in top_chunk.text

