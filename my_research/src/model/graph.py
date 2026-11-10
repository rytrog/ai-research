"""
PCC-Tensor 3.1: Hierarchical Table Structural Graph (G_T) & Graph Validation.
Enforces Contract C5 (Structural acyclicity) while supporting cyclic citation references.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from .structural import HeaderNode, LogicalRow, CellNode


@dataclass(frozen=True)
class FootnoteNode:
    """Footnote definition node."""
    footnote_id: str
    marker: str
    text: str
    page_id: Optional[str] = None
    target_scope: str = "TABLE"


class StructuralGraph:
    """
    G_structure: Strict Acyclic Directed Graph (DAG).
    Header tree containment + Row hierarchy containment.
    """

    def __init__(self) -> None:
        self.headers: Dict[str, HeaderNode] = {}
        self.rows: Dict[str, LogicalRow] = {}

    def add_header(self, header: HeaderNode) -> None:
        self.headers[header.header_id] = header

    def add_row(self, row: LogicalRow) -> None:
        self.rows[row.row_id] = row

    def validate_acyclic_dag(self) -> Tuple[bool, Optional[str]]:
        """
        Contract C5: Verifies that header tree and row hierarchy form strict DAGs.
        Returns (True, None) if acyclic; (False, error_msg) if a cycle is detected.
        """
        # 1. Header Hierarchy Cycle Check
        for h_id, h in self.headers.items():
            curr = h
            visited = {h_id}
            while curr.parent_header_id is not None:
                p_id = curr.parent_header_id
                if p_id in visited:
                    return False, f"Contract C5 violation: Header cycle detected: {h_id} -> {p_id}"
                visited.add(p_id)
                curr = self.headers.get(p_id)
                if curr is None:
                    break

        # 2. Row Hierarchy Cycle Check
        for r_id, r in self.rows.items():
            curr_r = r
            visited_r = {r_id}
            while curr_r.parent_row_id is not None:
                p_id = curr_r.parent_row_id
                if p_id in visited_r:
                    return False, f"Contract C5 violation: Row cycle detected: {r_id} -> {p_id}"
                visited_r.add(p_id)
                curr_r = self.rows.get(p_id)
                if curr_r is None:
                    break

        return True, None


class ReferenceGraph:
    """
    G_references: Footnote, citation, and formula reference graph.
    Cycles are detected and recorded without crashing or infinite loops.
    """

    def __init__(self) -> None:
        self.footnotes: Dict[str, FootnoteNode] = {}
        self.reference_edges: Set[Tuple[str, str]] = set()  # (source_id, target_footnote_id)
        self.note_to_note_edges: Set[Tuple[str, str]] = set()  # (note_a, note_b)

    def add_footnote(self, footnote: FootnoteNode) -> None:
        self.footnotes[footnote.footnote_id] = footnote

    def add_reference(self, source_id: str, footnote_id: str) -> None:
        self.reference_edges.add((source_id, footnote_id))

    def add_note_link(self, from_note_id: str, to_note_id: str) -> None:
        self.note_to_note_edges.add((from_note_id, to_note_id))

    def detect_reference_cycles(self) -> List[Tuple[str, ...]]:
        """
        Detects all directed cycles in the reference graph (e.g. Note A -> Note B -> Note C -> Note A).
        Uses pruned depth-first search from each canonical start node to find all elementary cycles.
        """
        adj: Dict[str, List[str]] = {}
        all_nodes: Set[str] = set()
        for u, v in self.note_to_note_edges:
            adj.setdefault(u, []).append(v)
            all_nodes.add(u)
            all_nodes.add(v)

        cycles: List[Tuple[str, ...]] = []
        nodes_sorted = sorted(all_nodes)

        for i, start_node in enumerate(nodes_sorted):
            # Only search among nodes >= start_node to ensure each cycle is found once in canonical form
            valid_nodes = set(nodes_sorted[i:])

            def dfs(curr: str, path: List[str], visited: Set[str]) -> None:
                for neighbor in adj.get(curr, []):
                    if neighbor == start_node and len(path) >= 1:
                        cycles.append(tuple(path))
                    elif neighbor in valid_nodes and neighbor not in visited:
                        visited.add(neighbor)
                        dfs(neighbor, path + [neighbor], visited)
                        visited.remove(neighbor)

            dfs(start_node, [start_node], {start_node})

        return cycles
