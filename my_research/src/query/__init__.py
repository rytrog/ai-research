"""
PCC-Tensor 3.1: Query Package.
Provides coordinate-aware, interval-disambiguating retrieval over CTIRSnapshots.
"""

from .engine import CTIRQueryEngine, QueryResult

__all__ = ["CTIRQueryEngine", "QueryResult"]

