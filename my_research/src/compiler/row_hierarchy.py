"""
PCC-Tensor 3.1: Hierarchical Row Stub Tree Builder (\u03a3_stub).
Constructs strict DAG hierarchy from row stub indentation, role semantics,
and computes complete ancestry paths for every logical row.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from ..model.structural import LogicalRow
from ..model.graph import StructuralGraph


class RowHierarchyBuilder:
    """
    Constructs and validates the hierarchical row stub tree (\u03a3_stub).
    Enforces Contract C5 (acyclic DAG) and Contract C7 (row closure).
    """

    def __init__(self, step_spaces: int = 2) -> None:
        self.step_spaces = step_spaces

    def build_hierarchy(
        self,
        rows: List[LogicalRow],
    ) -> Tuple[List[LogicalRow], StructuralGraph]:
        """
        Processes logical rows, assigning parent_row_id and complete ancestor_path
        based on indentation depth and role semantics (SECTION -> DETAIL -> SUBTOTAL -> TOTAL).
        """
        updated_rows: List[LogicalRow] = []
        graph = StructuralGraph()

        # Stack holds (indent_depth, row_id, label)
        stack: List[Tuple[int, str, str]] = []

        for row in rows:
            depth = row.indent_depth
            role = row.role

            # TOTAL rows reset hierarchy (no parent)
            if role == "TOTAL":
                stack.clear()
                updated_row = LogicalRow(
                    row_id=row.row_id,
                    position=row.position,
                    parent_row_id=None,
                    role=role,
                    raw_label=row.raw_label,
                    indent_depth=0,
                    ancestor_path=(),
                )
                updated_rows.append(updated_row)
                graph.add_row(updated_row)
                continue

            # SECTION rows at depth 0 start a new section
            if role == "SECTION" and depth == 0:
                stack.clear()
                updated_row = LogicalRow(
                    row_id=row.row_id,
                    position=row.position,
                    parent_row_id=None,
                    role=role,
                    raw_label=row.raw_label,
                    indent_depth=0,
                    ancestor_path=(),
                )
                updated_rows.append(updated_row)
                graph.add_row(updated_row)
                stack.append((depth, row.row_id, row.raw_label))
                continue

            # Pop stack while top has depth >= current depth
            while stack and stack[-1][0] >= depth:
                stack.pop()

            parent_id: Optional[str] = stack[-1][1] if stack else None
            ancestor_path: Tuple[str, ...] = tuple(item[2] for item in stack)

            updated_row = LogicalRow(
                row_id=row.row_id,
                position=row.position,
                parent_row_id=parent_id,
                role=role,
                raw_label=row.raw_label,
                indent_depth=depth,
                ancestor_path=ancestor_path,
            )
            updated_rows.append(updated_row)
            graph.add_row(updated_row)

            # If this row is a section or subtotal with children, it can be a parent
            if role in ("SECTION", "SUBTOTAL"):
                stack.append((depth, row.row_id, row.raw_label))

        # Validate DAG
        is_dag, err = graph.validate_acyclic_dag()
        if not is_dag:
            raise ValueError(f"Contract C5 violation in row hierarchy: {err}")

        return updated_rows, graph

