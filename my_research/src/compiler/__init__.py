"""
PCC-Tensor 3.1: Semantic Compiler Package.
Provides row hierarchy reconstruction, morphosyntactic accounting value normalization,
partial-order scope poset resolution, and end-to-end table compilation into validated CTIR snapshots.
"""

from .row_hierarchy import RowHierarchyBuilder
from .value_normalizer import ValueNormalizer
from .scope_resolver import ScopeResolver
from .table_compiler import TableCompiler

__all__ = [
    "RowHierarchyBuilder",
    "ValueNormalizer",
    "ScopeResolver",
    "TableCompiler",
]

