"""
PCC-Tensor 3.1: Formal Temporal Interval Algebra & Scope Closure.
Enforces Contract C11 (Temporal consistency) and prevents instant/duration conflation.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Union


class PeriodType(str, Enum):
    INSTANT = "instant"        # Point in time (Balance Sheet, Share Count at period end)
    DURATION = "duration"      # Flow over time (Income Statement, Cash Flow)


class TemporalRelation(str, Enum):
    EQUALS = "EQUALS"                  # p1 == p2
    CONTAINS = "CONTAINS"              # p1 strictly contains p2
    CONTAINED_BY = "CONTAINED_BY"      # p1 is contained within p2
    OVERLAPS = "OVERLAPS"              # p1 overlaps with p2 without containment
    BEFORE = "BEFORE"                  # p1 strictly before p2
    AFTER = "AFTER"                    # p1 strictly after p2


@dataclass(frozen=True)
class DurationPeriod:
    """Flow over an explicit calendar interval [start_date, end_date]."""
    start_date: datetime.date
    end_date: datetime.date
    calendar_id: str = "GREGORIAN"
    fiscal_year: Optional[int] = None
    fiscal_quarter: Optional[int] = None
    fiscal_label: Optional[str] = None

    def __post_init__(self) -> None:
        if self.start_date > self.end_date:
            raise ValueError(f"Contract C11 violation: start_date ({self.start_date}) > end_date ({self.end_date})")

    @property
    def duration_days(self) -> int:
        return (self.end_date - self.start_date).days + 1


@dataclass(frozen=True)
class InstantPeriod:
    """Point-in-time assertion (e.g. as of September 30, 2026)."""
    as_of_date: datetime.date
    calendar_id: str = "GREGORIAN"
    fiscal_year: Optional[int] = None
    fiscal_quarter: Optional[int] = None
    fiscal_label: Optional[str] = None


TemporalCoordinate = Union[DurationPeriod, InstantPeriod]


def evaluate_temporal_relation(p1: DurationPeriod, p2: DurationPeriod) -> TemporalRelation:
    """
    Evaluates the formal interval relationship between two duration periods.
    Fixes the false-disjointness bug: Duration(3M) in Duration(9M) yields CONTAINED_BY.
    """
    if p1.start_date == p2.start_date and p1.end_date == p2.end_date:
        return TemporalRelation.EQUALS
    if p1.start_date <= p2.start_date and p1.end_date >= p2.end_date:
        return TemporalRelation.CONTAINS
    if p1.start_date >= p2.start_date and p1.end_date <= p2.end_date:
        return TemporalRelation.CONTAINED_BY
    if p1.end_date < p2.start_date:
        return TemporalRelation.BEFORE
    if p1.start_date > p2.end_date:
        return TemporalRelation.AFTER
    return TemporalRelation.OVERLAPS

