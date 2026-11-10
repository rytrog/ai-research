"""
PCC-Tensor 3.1: Academic Evaluation Metrics Suite.
Standardized mathematical metrics for tabular fact retrieval and coordinate preservation
designed for peer-reviewed publication (ACL / NeurIPS / SIGMOD).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence


@dataclass(frozen=True)
class QueryEvaluationResult:
    """Individual query evaluation entry across all academic dimensions."""
    query_id: str
    target_metric: str
    target_period: str
    trap_type: str

    # Ground-truth targets
    gold_num: Optional[Decimal]
    gold_answer: str

    # System outputs
    retrieved_text: str
    retrieved_num: Optional[Decimal]
    retrieved_unit: Optional[str]
    retrieved_period: Optional[str]
    retrieved_footnotes: Sequence[str]

    # Metric scores
    has_coordinate_preservation: bool  # CPR: entity + metric + period + row hierarchy all intact
    has_numerical_accuracy: bool       # NVA: exact signed decimal value matches target
    has_unit_disambiguation: bool      # UDA: scale (e.g. 10^6 vs 10^3 vs 10^0) and currency correctly applied
    has_provenance_completeness: bool   # PCR: source coordinates and footnotes correctly colocated
    latency_ms: float                  # End-to-end execution latency


@dataclass(frozen=True)
class BenchmarkAggregateSummary:
    """Aggregated publication-grade metrics for a system or ablation configuration."""
    system_name: str
    total_queries: int

    # Percentages [0.0, 100.0]
    cpr: float  # Coordinate Preservation Rate (%)
    nva: float  # Numerical Value Accuracy (%)
    uda: float  # Unit Disambiguation Accuracy (%)
    pcr: float  # Provenance Completeness Rate (%)

    avg_latency_ms: float
    p95_latency_ms: float

    def to_markdown_row(self) -> str:
        return (
            f"| **{self.system_name}** "
            f"| {self.cpr:.1f}% "
            f"| {self.nva:.1f}% "
            f"| {self.uda:.1f}% "
            f"| {self.pcr:.1f}% "
            f"| {self.avg_latency_ms:.2f} ms |"
        )

    def to_latex_row(self) -> str:
        return (
            f"\\textbf{{{self.system_name}}} & "
            f"{self.cpr:.1f}\\% & "
            f"{self.nva:.1f}\\% & "
            f"{self.uda:.1f}\\% & "
            f"{self.pcr:.1f}\\% & "
            f"{self.avg_latency_ms:.2f}\\,\\text{{ms}} \\\\"
        )

