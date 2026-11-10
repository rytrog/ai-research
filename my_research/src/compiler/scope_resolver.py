"""
PCC-Tensor 3.1: Scope-Aware Contextual & Poset Resolver (SCRA).
Extracts, resolves, and binds temporal intervals, measurement scales, currencies,
and entity scopes across Document -> Table -> Section -> (Row x Col) -> Cell.
"""

from __future__ import annotations

import datetime
import re
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from ..model.semantic import (
    Quantity,
    ResolutionStatus,
    ScopeConflictResolver,
    ScopeLevel,
    UnitAssertion,
)
from ..model.structural import LogicalColumn, LogicalRow
from ..model.temporal import DurationPeriod, InstantPeriod, TemporalCoordinate


class ScopeResolver:
    """
    Resolves multi-level contextual assertions across hierarchical table scopes.
    Enforces Contract C10 (Unit consistency), Contract C11 (Temporal algebra),
    and Contract C12 (Poset scope resolution).
    """

    MONTH_MAP = {
        "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
        "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
    }

    def __init__(self, table_default_unit: Optional[UnitAssertion] = None) -> None:
        self.table_default_unit = table_default_unit or UnitAssertion(
            currency="USD",
            scale_exponent=6,  # Default $ Millions
            source_scope=ScopeLevel.TABLE,
        )

    @classmethod
    def resolve_period_from_headers(
        cls,
        header_path: Tuple[str, ...],
        row_label: str = "",
    ) -> Optional[TemporalCoordinate]:
        """
        Infers DurationPeriod or InstantPeriod from header ancestry and row semantics.
        Disambiguates 'Three Months Ended' vs 'Nine Months Ended'.
        """
        combined_headers = " ".join(header_path).lower()

        # Check year
        year_m = re.search(r"\b(20\d\d)\b", combined_headers)
        if not year_m:
            return None
        year = int(year_m.group(1))

        # Check month and day
        month = 12
        day = 31
        for m_name, m_val in cls.MONTH_MAP.items():
            if m_name in combined_headers:
                month = m_val
                # Search for day e.g. "September 30"
                day_m = re.search(rf"{m_name}\s+(\d{{1,2}})", combined_headers)
                if day_m:
                    day = int(day_m.group(1))
                break

        end_date = datetime.date(year, month, day)

        # Check if row is an instant/point-in-time balance sheet or headcount item
        is_instant = False
        row_lower = row_label.lower()
        if any(term in row_lower for term in ("headcount", "employees", "at september 30", "as of", "ending balance")):
            is_instant = True

        if is_instant:
            return InstantPeriod(
                as_of_date=end_date,
                fiscal_year=year,
                fiscal_label=f"As of {end_date.isoformat()}",
            )

        # Check duration (Three Months vs Nine Months vs Full Year)
        if "three months" in combined_headers or "quarter ended" in combined_headers:
            # 3 Months duration: start date is approx 3 months prior (first day of quarter)
            if month == 9 and day == 30:
                start_date = datetime.date(year, 7, 1)
            elif month == 6 and day == 30:
                start_date = datetime.date(year, 4, 1)
            elif month == 3 and day == 31:
                start_date = datetime.date(year, 1, 1)
            else:
                start_date = datetime.date(year, 10, 1) if month == 12 else datetime.date(year, max(1, month - 2), 1)

            q_num = (month + 2) // 3
            return DurationPeriod(
                start_date=start_date,
                end_date=end_date,
                fiscal_year=year,
                fiscal_quarter=q_num,
                fiscal_label=f"Q{q_num} {year} (Three Months Ended {end_date.isoformat()})",
            )

        elif "nine months" in combined_headers:
            start_date = datetime.date(year, 1, 1)
            return DurationPeriod(
                start_date=start_date,
                end_date=end_date,
                fiscal_year=year,
                fiscal_quarter=3,
                fiscal_label=f"9M {year} (Nine Months Ended {end_date.isoformat()})",
            )

        elif "six months" in combined_headers:
            start_date = datetime.date(year, 1, 1)
            return DurationPeriod(
                start_date=start_date,
                end_date=end_date,
                fiscal_year=year,
                fiscal_quarter=2,
                fiscal_label=f"6M {year} (Six Months Ended {end_date.isoformat()})",
            )

        # Fallback to annual or instant
        return DurationPeriod(
            start_date=datetime.date(year, 1, 1),
            end_date=end_date,
            fiscal_year=year,
            fiscal_label=f"Year Ended {end_date.isoformat()}",
        )

    def extract_row_unit_assertion(self, row: LogicalRow) -> Optional[UnitAssertion]:
        """Extracts unit overrides declared in row labels (e.g. 'in Thousands', 'EPS in USD')."""
        label = row.raw_label.lower()

        # Shares in thousands
        if "in thousands" in label or "(in thousands)" in label:
            return UnitAssertion(
                currency=None,
                physical_unit="shares",
                scale_exponent=3,  # 10^3
                source_scope=ScopeLevel.ROW,
            )

        # EPS in USD / per share
        if "per share" in label or "eps" in label:
            return UnitAssertion(
                currency="USD",
                physical_unit="USD/share",
                scale_exponent=0,  # 10^0 = 1
                source_scope=ScopeLevel.ROW,
            )

        # Percentages
        if "%" in label or "percentage" in label:
            return UnitAssertion(
                currency=None,
                physical_unit="PERCENT",
                scale_exponent=0,
                source_scope=ScopeLevel.ROW,
            )

        # Headcount
        if "headcount" in label or "employees" in label:
            return UnitAssertion(
                currency=None,
                physical_unit="Headcount Units",
                scale_exponent=0,
                source_scope=ScopeLevel.ROW,
            )

        # Defect density
        if "defect density" in label or "defects / cm2" in label:
            return UnitAssertion(
                currency=None,
                physical_unit="defects/cm2",
                scale_exponent=0,
                source_scope=ScopeLevel.ROW,
            )

        return None

    def resolve_cell_quantity(
        self,
        raw_text: str,
        numeric_val: Decimal,
        row: LogicalRow,
        column: LogicalColumn,
        cell_detected_currency: Optional[str] = None,
        cell_detected_unit: Optional[str] = None,
    ) -> Tuple[Quantity, UnitAssertion]:
        """
        Resolves the exact Quantity and canonical amount using poset scope resolution.
        """
        row_unit = self.extract_row_unit_assertion(row)

        cell_unit = None
        if cell_detected_currency or cell_detected_unit:
            cell_unit = UnitAssertion(
                currency=cell_detected_currency,
                physical_unit=cell_detected_unit,
                scale_exponent=0 if cell_detected_unit == "PERCENT" else (row_unit.scale_exponent if row_unit else self.table_default_unit.scale_exponent),
                source_scope=ScopeLevel.CELL,
            )

        # Poset resolution
        status, resolved_unit, _ = ScopeConflictResolver.resolve_unit_assertions(
            cell_unit=cell_unit,
            row_unit=row_unit,
            col_unit=None,
            table_unit=self.table_default_unit,
        )

        final_unit = resolved_unit or self.table_default_unit
        multiplier = final_unit.scale_multiplier
        canonical_amount = numeric_val * multiplier

        quantity = Quantity(
            raw_text=raw_text,
            numeric_value=numeric_val,
            currency=final_unit.currency,
            physical_unit=final_unit.physical_unit,
            scale_exponent=final_unit.scale_exponent,
            canonical_amount=canonical_amount,
        )

        return quantity, final_unit

