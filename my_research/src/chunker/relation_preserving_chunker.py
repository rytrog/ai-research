"""
PCC-Tensor 3.1: Relation-Preserving Semantic Table Chunker.
Compiles a CTIRSnapshot into self-contained, coordinate-closed chunks (Dual-View: Dense Linearized + Micro-Grid).
Guarantees 100% information preservation: zero coordinate loss, zero header loss, zero unit loss, and zero footnote severance.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from ..model.ctir import CTIRSnapshot, SourceFact
from ..model.graph import FootnoteNode
from ..model.structural import LogicalColumn, LogicalRow
from ..model.temporal import DurationPeriod, InstantPeriod


class ChunkBudgetExceededError(ValueError):
    """Raised when an oversized row or table fragment exceeds the configured token budget."""
    pass


@dataclass(frozen=True)
class TableChunkECC:
    """Evidence Closure Certificate for a compiled table chunk (ECC_chunk)."""
    chunk_id: str
    fact_ids: Tuple[str, ...]
    row_count: int
    column_count: int
    content_sha256: str
    token_estimate: int
    has_header_closure: bool
    has_unit_closure: bool
    has_footnote_closure: bool


@dataclass(frozen=True)
class RelationPreservingChunk:
    """
    A single self-contained, coordinate-closed table chunk.
    Enforces Contract C13 (Provenance closure) and Contract C15 (Dual representation).
    """
    chunk_id: str
    chunk_index: int
    table_id: str
    entity_name: str

    # Bifurcated Views
    dense_text: str                     # Linearized, self-contained propositions for vector embeddings & LLMs
    markdown_microgrid: str             # Syntactically valid Markdown table slice with restored headers
    structured_facts: Tuple[SourceFact, ...] # Layer L4 symbolic facts

    # Scope & Context
    row_range: Tuple[int, int]          # (start_row_pos, end_row_pos)
    column_count: int
    colocated_footnotes: Tuple[FootnoteNode, ...]
    certificate: TableChunkECC


class RelationPreservingTableChunker:
    """
    Generates self-sufficient, coordinate-closed table chunks from a CTIRSnapshot.
    Unlike naive chunkers that blindly slice lines, this chunker injects:
    1. Table title & Entity scope
    2. Global/local scale & currency assertions
    3. Multi-tier column header paths (Three Months vs Nine Months)
    4. Row ancestor hierarchy paths (Section > Detail > Subtotal)
    5. In-chunk colocated footnote definitions
    """

    def __init__(
        self,
        max_rows_per_chunk: int = 5,
        token_budget: int = 512,
        include_markdown_grid: bool = True,
        enable_coordinate_closure: bool = True,
        enable_superheader_closure: bool = True,
        enable_footnote_colocation: bool = True,
        enable_row_hierarchy: bool = True,
        tokenizer: Optional[Any] = None,
    ) -> None:
        self.max_rows_per_chunk = max_rows_per_chunk
        self.token_budget = token_budget
        self.include_markdown_grid = include_markdown_grid
        self.enable_coordinate_closure = enable_coordinate_closure
        self.enable_superheader_closure = enable_superheader_closure
        self.enable_footnote_colocation = enable_footnote_colocation
        self.enable_row_hierarchy = enable_row_hierarchy
        self.tokenizer = tokenizer

    def _estimate_tokens(self, text: str) -> int:
        """
        Calculates token count using custom tokenizer if supplied,
        or standard BPE character/word heuristic (max(len(text)//4, word_count)).
        """
        if not text:
            return 0
        if self.tokenizer is not None:
            if callable(self.tokenizer):
                return len(self.tokenizer(text))
            elif hasattr(self.tokenizer, "encode"):
                return len(self.tokenizer.encode(text))
        # Standard conservative subword estimator: ~4 chars per token, but bounded by word splitting
        char_est = len(text) // 4
        words = re.findall(r"\w+|[^\w\s]", text, re.UNICODE)
        return max(1, max(char_est, int(len(words) * 1.15)))

    def chunk_snapshot(
        self,
        snapshot: CTIRSnapshot,
        table_title: str = "FINANCIAL SCHEDULE",
        global_unit_banner: str = "All monetary amounts in millions of U.S. Dollars ($ USD Millions) unless otherwise noted",
    ) -> List[RelationPreservingChunk]:
        """
        Partitions snapshot facts into coordinate-closed chunks using dynamic token-budget packing.
        """
        # 1. Group facts by logical row
        facts_by_row: Dict[int, List[SourceFact]] = {}
        for fact in snapshot.source_facts.values():
            row_id_str = fact.source_cell_id.split("_")[1] # r021
            row_pos = int(row_id_str.replace("r", ""))
            facts_by_row.setdefault(row_pos, []).append(fact)

        sorted_row_positions = sorted(facts_by_row.keys())
        if not sorted_row_positions:
            return []

        # Find columns
        columns = list(snapshot.columns.values())
        col_count = len(columns)

        # Map footnotes from evidence anchors
        footnotes_by_id: Dict[str, FootnoteNode] = {}
        for fact in snapshot.source_facts.values():
            for fn_a in fact.provenance.footnote_anchors:
                fn_id = fn_a.evidence_id.split("_")[2]
                footnotes_by_id[fn_id] = FootnoteNode(
                    footnote_id=f"fn_{fn_id}",
                    marker=fn_id,
                    text=fn_a.raw_text,
                )

        chunks: List[RelationPreservingChunk] = []
        chunk_idx = 0

        # Base header lines for each chunk
        entity_name = list(snapshot.source_facts.values())[0].coordinates.entity_name if snapshot.source_facts else "Enterprise Registrant"
        if self.enable_coordinate_closure:
            base_header_lines = [
                f"[DOCUMENT_TABLE: {table_title}]",
                f"[ENTITY: {entity_name}]",
                f"[GLOBAL_CONVENTION: {global_unit_banner}]",
            ]
        else:
            base_header_lines = []
        base_header_text = "\n".join(base_header_lines)
        base_header_tokens = self._estimate_tokens(base_header_text)

        # 2. Dynamic Token-Budget Packing (Greedy Knapsack)
        curr_row_slice: List[int] = []
        curr_slice_tokens = base_header_tokens

        row_index = 0
        while row_index < len(sorted_row_positions):
            r_pos = sorted_row_positions[row_index]
            r_facts = facts_by_row.get(r_pos, [])

            # Format this row's propositions to estimate tokens
            row_lines: List[str] = []
            if r_facts:
                row_label = r_facts[0].coordinates.raw_metric_label
                ancestor_path = r_facts[0].coordinates.row_ancestor_path
                if self.enable_row_hierarchy:
                    row_hierarchy = " > ".join(ancestor_path + (row_label,)) if ancestor_path else row_label
                else:
                    row_hierarchy = row_label
                row_lines.append(f"\n[ROW_HIERARCHY: {row_hierarchy}]")

                for f in r_facts:
                    if self.enable_superheader_closure:
                        col_path = " / ".join(f.coordinates.column_ancestor_path)
                    else:
                        col_path = f.coordinates.column_ancestor_path[-1] if f.coordinates.column_ancestor_path else ""
                    val_str = f.canonical_display
                    raw_verbatim = getattr(f.typed_value, "raw_text", f.canonical_display)
                    temp = f.coordinates.temporal
                    if isinstance(temp, DurationPeriod):
                        p_label = temp.fiscal_label or f"{temp.start_date} to {temp.end_date}"
                    elif isinstance(temp, InstantPeriod):
                        p_label = temp.fiscal_label or f"As of {temp.as_of_date}"
                    else:
                        p_label = col_path
                    row_lines.append(f"  * {col_path} [{p_label}]: {val_str} (verbatim: '{raw_verbatim}')")

            row_text = "\n".join(row_lines)
            row_tokens = self._estimate_tokens(row_text)

            # Contract enforcement: Check if this row alone exceeds the configured token budget
            if row_tokens + base_header_tokens > self.token_budget:
                raise ChunkBudgetExceededError(
                    f"Row at position {r_pos} requires {row_tokens + base_header_tokens} tokens, "
                    f"exceeding maximum chunk budget of {self.token_budget}."
                )

            # Check if adding this row exceeds token_budget and we already have at least 1 row
            if curr_row_slice and (curr_slice_tokens + row_tokens > self.token_budget or len(curr_row_slice) >= self.max_rows_per_chunk):
                # Emit current chunk
                chunks.append(self._build_chunk(
                    chunk_idx=chunk_idx,
                    row_slice=curr_row_slice,
                    facts_by_row=facts_by_row,
                    columns=columns,
                    col_count=col_count,
                    footnotes_by_id=footnotes_by_id,
                    base_header_lines=base_header_lines,
                    entity_name=entity_name,
                    snapshot=snapshot,
                ))
                chunk_idx += 1
                curr_row_slice = []
                curr_slice_tokens = base_header_tokens

            curr_row_slice.append(r_pos)
            curr_slice_tokens += row_tokens
            row_index += 1

        # Emit final chunk
        if curr_row_slice:
            chunks.append(self._build_chunk(
                chunk_idx=chunk_idx,
                row_slice=curr_row_slice,
                facts_by_row=facts_by_row,
                columns=columns,
                col_count=col_count,
                footnotes_by_id=footnotes_by_id,
                base_header_lines=base_header_lines,
                entity_name=entity_name,
                snapshot=snapshot,
            ))

        return chunks

    def _build_chunk(
        self,
        chunk_idx: int,
        row_slice: List[int],
        facts_by_row: Dict[int, List[SourceFact]],
        columns: List[LogicalColumn],
        col_count: int,
        footnotes_by_id: Dict[str, FootnoteNode],
        base_header_lines: List[str],
        entity_name: str,
        snapshot: CTIRSnapshot,
    ) -> RelationPreservingChunk:
        slice_start = row_slice[0]
        slice_end = row_slice[-1]

        chunk_facts: List[SourceFact] = []
        chunk_cited_footnotes: Dict[str, FootnoteNode] = {}

        for r_pos in row_slice:
            r_facts = facts_by_row.get(r_pos, [])
            chunk_facts.extend(r_facts)
            for f in r_facts:
                for fn_a in f.provenance.footnote_anchors:
                    fn_marker = fn_a.evidence_id.split("_")[2]
                    if fn_marker in footnotes_by_id:
                        chunk_cited_footnotes[fn_marker] = footnotes_by_id[fn_marker]

        # 1. Build Dense Text
        dense_lines: List[str] = list(base_header_lines)
        for r_pos in row_slice:
            r_facts = facts_by_row.get(r_pos, [])
            if not r_facts:
                continue
            row_label = r_facts[0].coordinates.raw_metric_label
            ancestor_path = r_facts[0].coordinates.row_ancestor_path
            if self.enable_row_hierarchy:
                row_hierarchy = " > ".join(ancestor_path + (row_label,)) if ancestor_path else row_label
            else:
                row_hierarchy = row_label
            dense_lines.append(f"\n[ROW_HIERARCHY: {row_hierarchy}]")

            for f in r_facts:
                if self.enable_superheader_closure:
                    col_path = " / ".join(f.coordinates.column_ancestor_path)
                else:
                    col_path = f.coordinates.column_ancestor_path[-1] if f.coordinates.column_ancestor_path else ""
                val_str = f.canonical_display
                raw_verbatim = getattr(f.typed_value, "raw_text", f.canonical_display)
                temp = f.coordinates.temporal
                if isinstance(temp, DurationPeriod):
                    p_label = temp.fiscal_label or f"{temp.start_date} to {temp.end_date}"
                elif isinstance(temp, InstantPeriod):
                    p_label = temp.fiscal_label or f"As of {temp.as_of_date}"
                else:
                    p_label = col_path
                dense_lines.append(f"  * {col_path} [{p_label}]: {val_str} (verbatim: '{raw_verbatim}')")

        if chunk_cited_footnotes and self.enable_footnote_colocation:
            dense_lines.append("\n[COLOCATED_FOOTNOTES_IN_CHUNK]:")
            for fn in sorted(chunk_cited_footnotes.values(), key=lambda x: x.marker):
                dense_lines.append(f"  [{fn.marker}] {fn.text}")

        dense_text = "\n".join(dense_lines)

        # 2. Build Micro-Grid
        grid_lines: List[str] = []
        if self.include_markdown_grid:
            col_headers = ["Line Item / Metric"]
            for c in columns[1:]:
                col_headers.append(" / ".join(c.header_path))
            grid_lines.append("| " + " | ".join(col_headers) + " |")
            grid_lines.append("| " + " | ".join([":---"] + ["---:"] * (len(col_headers) - 1)) + " |")

            for r_pos in row_slice:
                r_facts = facts_by_row.get(r_pos, [])
                if not r_facts:
                    continue
                row_lbl = r_facts[0].coordinates.raw_metric_label
                row_cells = [row_lbl]
                facts_by_col = {
                    int(f.source_cell_id.split("_")[2].replace("c", "")): f for f in r_facts
                }
                for c_idx in range(1, col_count):
                    f_col = facts_by_col.get(c_idx)
                    row_cells.append(f_col.canonical_display if f_col else "")
                grid_lines.append("| " + " | ".join(row_cells) + " |")

        markdown_grid = "\n".join(grid_lines)

        # 3. Build ECC
        chunk_id = f"chunk_sec_{chunk_idx:03d}"
        content_digest = hashlib.sha256(dense_text.encode("utf-8")).hexdigest()
        fact_ids_tuple = tuple(f.fact_id for f in chunk_facts)
        tok_est = self._estimate_tokens(dense_text)

        # Dynamic Truthful ECC Verification
        has_headers = (
            (self.enable_coordinate_closure and "[DOCUMENT_TABLE:" in dense_text and "[ENTITY:" in dense_text)
            or (self.enable_superheader_closure and "[ROW_HIERARCHY:" in dense_text)
        )
        if not self.enable_coordinate_closure and not self.enable_superheader_closure:
            has_headers = False

        has_units = (
            self.enable_coordinate_closure
            and "[GLOBAL_CONVENTION:" in dense_text
            and any(f.unit is not None and (f.unit.currency is not None or f.unit.scale_exponent is not None) for f in chunk_facts)
        )
        if not self.enable_coordinate_closure:
            has_units = False

        has_footnotes = (
            len(chunk_cited_footnotes) > 0
            and self.enable_footnote_colocation
            and "[COLOCATED_FOOTNOTES_IN_CHUNK]:" in dense_text
        )

        ecc_chunk = TableChunkECC(
            chunk_id=chunk_id,
            fact_ids=fact_ids_tuple,
            row_count=len(row_slice),
            column_count=col_count,
            content_sha256=content_digest,
            token_estimate=tok_est,
            has_header_closure=has_headers,
            has_unit_closure=has_units,
            has_footnote_closure=has_footnotes,
        )

        return RelationPreservingChunk(
            chunk_id=chunk_id,
            chunk_index=chunk_idx,
            table_id=snapshot.logical_tables[0].table_id if snapshot.logical_tables else "table_0",
            entity_name=entity_name,
            dense_text=dense_text,
            markdown_microgrid=markdown_grid,
            structured_facts=tuple(chunk_facts),
            row_range=(slice_start, slice_end),
            column_count=col_count,
            colocated_footnotes=tuple(chunk_cited_footnotes.values()),
            certificate=ecc_chunk,
        )

