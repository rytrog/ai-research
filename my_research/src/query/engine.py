"""
PCC-Tensor 3.1: Symbolic & Coordinate-Aware CTIR Query Engine.
Executes deterministic fact retrieval over CTIRSnapshots with interval temporal matching,
metric label disambiguation, unit preservation, and footnote provenance binding.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from ..compiler.scope_resolver import ScopeResolver
from ..model.ctir import CTIRSnapshot, SourceFact
from ..model.graph import FootnoteNode
from ..model.temporal import DurationPeriod, InstantPeriod, TemporalCoordinate


@dataclass(frozen=True)
class QueryResult:
    """Retrieved factual answer with complete mathematical and evidential closure."""
    fact: SourceFact
    canonical_answer: str
    numeric_value: Optional[Decimal]
    unit_str: str
    period_str: str
    footnote_texts: Tuple[str, ...]
    relevance_score: float


class CTIRQueryEngine:
    """
    High-precision query engine operating directly on validated CTIRSnapshots.
    Eliminates embedding centroid dilution and chunk-boundary severance on financial tables.
    """

    def __init__(self, snapshot: CTIRSnapshot) -> None:
        self.snapshot = snapshot
        self.facts: List[SourceFact] = list(snapshot.source_facts.values())

    @staticmethod
    def _normalize_tokens(text: str) -> List[str]:
        cleaned = re.sub(r"[^a-zA-Z0-9\s]", " ", text.lower())
        return [tok for tok in cleaned.split() if len(tok) > 1]

    def query(
        self,
        question: str,
        target_metric: Optional[str] = None,
        target_period: Optional[str] = None,
        top_k: int = 3,
    ) -> List[QueryResult]:
        """
        Executes coordinate-aware retrieval over CTIR facts.
        """
        # Determine query search terms
        search_metric = (target_metric or question).lower()
        search_period = (target_period or question).lower()

        q_metric_tokens = set(self._normalize_tokens(search_metric))

        # Check temporal requirements in query
        wants_three_months = any(term in search_period for term in ("three months", "q3", "third quarter"))
        wants_nine_months = any(term in search_period for term in ("nine months", "9m"))
        wants_2026 = "2026" in search_period
        wants_2025 = "2025" in search_period

        scored_candidates: List[Tuple[float, SourceFact]] = []

        for fact in self.facts:
            score = 0.0

            # 1. Metric Label Matching
            metric_label = fact.coordinates.raw_metric_label.lower()
            metric_tokens = set(self._normalize_tokens(metric_label))

            overlap = q_metric_tokens.intersection(metric_tokens)
            if not overlap:
                # Also check row ancestor path
                ancestor_str = " ".join(fact.coordinates.row_ancestor_path).lower()
                overlap = q_metric_tokens.intersection(set(self._normalize_tokens(ancestor_str)))
                if not overlap:
                    continue
                score += len(overlap) * 5.0
            else:
                score += len(overlap) * 10.0

            # Exact substring match bonus
            if target_metric and target_metric.lower() in metric_label:
                score += 50.0

            # 2. Temporal Interval Matching & Disambiguation
            col_path = " ".join(fact.coordinates.column_ancestor_path).lower()
            temp = fact.coordinates.temporal

            # Year matching
            if wants_2026 and "2026" in col_path:
                score += 30.0
            elif wants_2026 and "2026" not in col_path:
                score -= 40.0

            if wants_2025 and "2025" in col_path:
                score += 30.0
            elif wants_2025 and "2025" not in col_path:
                score -= 40.0

            # Duration matching
            if wants_three_months and wants_nine_months:
                # Comparative query: disambiguate primary subject by order of appearance
                idx_3m = search_period.find("three months")
                if idx_3m == -1:
                    idx_3m = search_period.find("q3")
                idx_9m = search_period.find("nine months")
                if idx_9m == -1:
                    idx_9m = search_period.find("9m")

                if idx_9m != -1 and (idx_3m == -1 or idx_9m < idx_3m):
                    # Primary subject is 9M
                    if "nine months" in col_path or (isinstance(temp, DurationPeriod) and temp.duration_days > 200):
                        score += 50.0
                    else:
                        score += 10.0
                else:
                    # Primary subject is 3M
                    if "three months" in col_path or (isinstance(temp, DurationPeriod) and temp.duration_days < 100):
                        score += 50.0
                    else:
                        score += 10.0
            elif wants_three_months:
                if "three months" in col_path or (isinstance(temp, DurationPeriod) and temp.duration_days < 100):
                    score += 40.0
                else:
                    score -= 50.0
            elif wants_nine_months:
                if "nine months" in col_path or (isinstance(temp, DurationPeriod) and temp.duration_days > 200):
                    score += 40.0
                else:
                    score -= 50.0

            scored_candidates.append((score, fact))

        scored_candidates.sort(key=lambda x: x[0], reverse=True)

        results: List[QueryResult] = []
        for score, fact in scored_candidates[:top_k]:
            # Extract numeric value
            num_val = getattr(fact.typed_value, "value", None)

            # Extract footnote texts from provenance bundle
            fn_texts = tuple(fn_anchor.raw_text for fn_anchor in fact.provenance.footnote_anchors)

            # Format unit
            unit_str = f"{fact.unit.currency or ''} 10^{fact.unit.scale_exponent} {fact.unit.physical_unit or ''}".strip()

            # Format period
            if isinstance(fact.coordinates.temporal, DurationPeriod):
                p_str = fact.coordinates.temporal.fiscal_label or f"{fact.coordinates.temporal.start_date} to {fact.coordinates.temporal.end_date}"
            elif isinstance(fact.coordinates.temporal, InstantPeriod):
                p_str = fact.coordinates.temporal.fiscal_label or f"As of {fact.coordinates.temporal.as_of_date}"
            else:
                p_str = " / ".join(fact.coordinates.column_ancestor_path)

            results.append(
                QueryResult(
                    fact=fact,
                    canonical_answer=fact.canonical_display,
                    numeric_value=num_val,
                    unit_str=unit_str,
                    period_str=p_str,
                    footnote_texts=fn_texts,
                    relevance_score=score,
                )
            )

        return results
