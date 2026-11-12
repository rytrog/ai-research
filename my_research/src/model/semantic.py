"""
PCC-Tensor 3.1: Scope-Aware Unit & Context Algebra (SUCA / SCRA).
Enforces Contract C10 (Unit consistency) and Contract C12 (Scope resolution via Poset).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any

from .source import SourceRef


class ResolutionStatus(str, Enum):
    RESOLVED = "RESOLVED"
    INFERRED = "INFERRED"
    AMBIGUOUS = "AMBIGUOUS"
    CONFLICT = "CONFLICT"
    UNRESOLVED = "UNRESOLVED"


class ScopeLevel(str, Enum):
    CELL = "CELL"
    ROW = "ROW"
    COLUMN = "COLUMN"
    SECTION = "SECTION"
    TABLE = "TABLE"
    DOCUMENT = "DOCUMENT"


@dataclass(frozen=True)
class ScopeRef:
    level: ScopeLevel
    scope_id: str


@dataclass(frozen=True)
class UnitAssertion:
    """
    Decoupled measurement scale, physical dimension, and currency definition.
    Contract C10: Scale is an integer exponent s in 10^s (None = unspecified/inheritable).
    """
    currency: Optional[str] = None          # ISO 4217 (e.g., 'USD', 'EUR')
    physical_unit: Optional[str] = None     # UCUM code (e.g., 'shares', '1/cm2', '%', 'USD/share')
    scale_exponent: Optional[int] = None    # s in 10^s (None = unspecified, 0 = 10^0 = 1, 3 = thousands, 6 = millions)
    xbrl_decimals: Optional[int] = None     # Reported numerical precision
    source_scope: ScopeLevel = ScopeLevel.TABLE
    source_ref: Optional[SourceRef] = None

    @property
    def scale_multiplier(self) -> Optional[Decimal]:
        """Returns exact Decimal multiplier (e.g. 10^6 -> Decimal('1000000'), 10^0 -> 1) or None if scale_exponent is None."""
        if self.scale_exponent is None:
            return None
        elif self.scale_exponent == 0:
            return Decimal(1)
        elif self.scale_exponent > 0:
            return Decimal(10 ** self.scale_exponent)
        else:
            return Decimal(1) / Decimal(10 ** abs(self.scale_exponent))


@dataclass(frozen=True)
class Quantity:
    """A fully contextualized physical or monetary quantity."""
    raw_text: str
    numeric_value: Decimal
    currency: Optional[str] = None
    physical_unit: Optional[str] = None
    scale_exponent: Optional[int] = None
    canonical_amount: Optional[Decimal] = None
    reported_decimals: Optional[int] = None


@dataclass(frozen=True)
class SemanticAssertion:
    """An explicit contextual claim attached to a scope (entity, unit, period, basis)."""
    assertion_id: str
    property_name: str                     # 'currency', 'scale_exponent', 'period', 'entity'
    value: Any
    scope: ScopeRef
    source_ref: SourceRef
    status: ResolutionStatus = ResolutionStatus.RESOLVED


class ScopeConflictResolver:
    """
    Scope Conflict Resolution Algebra (SCRA):
    Resolves assertions over an orthogonal partial-order poset (Document -> Table -> (Row, Column) -> Cell).
    Fixes the broken linear hierarchy and bug where Row blindly preempted Column.
    """

    @staticmethod
    def resolve_unit_assertions(
        cell_unit: Optional[UnitAssertion],
        row_unit: Optional[UnitAssertion],
        col_unit: Optional[UnitAssertion],
        table_unit: Optional[UnitAssertion],
    ) -> Tuple[ResolutionStatus, Optional[UnitAssertion], Optional[str]]:
        """
        Contract C12: Independent partial-order property resolution.
        Resolves U = (currency, physical_unit, scale_exponent, xbrl_decimals)
        where Cell > (Row x Col) > Table.
        A cell-level assertion on currency does NOT erase a row/column physical unit!
        """
        # Check if any unit assertions exist across scopes
        units = [u for u in (cell_unit, row_unit, col_unit, table_unit) if u is not None]
        has_any_property = any(
            u.currency is not None or u.physical_unit is not None or u.scale_exponent is not None or u.xbrl_decimals is not None
            for u in units
        )
        if not has_any_property:
            return (
                ResolutionStatus.UNRESOLVED,
                None,
                "No unit assertions declared in any applicable scope",
            )

        # Check conflict between orthogonal Row and Column scopes
        if row_unit is not None and col_unit is not None:
            if row_unit.currency and col_unit.currency and row_unit.currency != col_unit.currency:
                return (
                    ResolutionStatus.CONFLICT,
                    None,
                    f"Conflicting currency assertions: Row ({row_unit.currency}) vs Col ({col_unit.currency})",
                )
            if row_unit.scale_exponent is not None and col_unit.scale_exponent is not None:
                if row_unit.scale_exponent != col_unit.scale_exponent:
                    return (
                        ResolutionStatus.CONFLICT,
                        None,
                        f"Conflicting scale assertions: Row (10^{row_unit.scale_exponent}) vs Col (10^{col_unit.scale_exponent})",
                    )

        # 1. Resolve Currency
        cell_curr = cell_unit.currency if cell_unit else None
        row_curr = row_unit.currency if row_unit else None
        col_curr = col_unit.currency if col_unit else None
        table_curr = table_unit.currency if table_unit else None

        # Determine if row or column is explicitly non-monetary
        has_non_monetary_phys = False
        for u in (cell_unit, row_unit, col_unit):
            if u and u.physical_unit and not u.currency:
                if u.physical_unit.lower() not in ("usd/share", "eur/share", "per share"):
                    has_non_monetary_phys = True
                    break

        if has_non_monetary_phys:
            resolved_currency = cell_curr or row_curr or col_curr or None
        else:
            resolved_currency = cell_curr or row_curr or col_curr or table_curr

        # 2. Resolve Physical Unit
        cell_phys = cell_unit.physical_unit if cell_unit else None
        row_phys = row_unit.physical_unit if row_unit else None
        col_phys = col_unit.physical_unit if col_unit else None
        table_phys = table_unit.physical_unit if table_unit else None
        resolved_physical_unit = cell_phys or row_phys or col_phys or table_phys

        # 3. Resolve Scale Exponent (Preserve None if unknown; never silently assume 10^0)
        cell_scale = cell_unit.scale_exponent if (cell_unit and cell_unit.scale_exponent is not None) else None
        row_scale = row_unit.scale_exponent if (row_unit and row_unit.scale_exponent is not None) else None
        col_scale = col_unit.scale_exponent if (col_unit and col_unit.scale_exponent is not None) else None
        table_scale = table_unit.scale_exponent if (table_unit and table_unit.scale_exponent is not None) else None

        if cell_scale is not None:
            resolved_scale = cell_scale
        elif row_scale is not None:
            resolved_scale = row_scale
        elif col_scale is not None:
            resolved_scale = col_scale
        elif table_scale is not None:
            resolved_scale = table_scale
        else:
            resolved_scale = None

        # 4. Resolve Reported Decimals / Precision
        cell_dec = cell_unit.xbrl_decimals if cell_unit else None
        row_dec = row_unit.xbrl_decimals if row_unit else None
        col_dec = col_unit.xbrl_decimals if col_unit else None
        table_dec = table_unit.xbrl_decimals if table_unit else None
        resolved_decimals = cell_dec or row_dec or col_dec or table_dec

        # If after resolution neither currency, physical unit, nor scale exponent is known:
        if resolved_currency is None and resolved_physical_unit is None and resolved_scale is None:
            return (
                ResolutionStatus.UNRESOLVED,
                None,
                "Unit assertions lack valid currency, physical unit, or scale",
            )

        # Determine source scope of composite resolution
        if cell_unit is not None:
            src_scope = ScopeLevel.CELL
        elif row_unit is not None:
            src_scope = ScopeLevel.ROW
        elif col_unit is not None:
            src_scope = ScopeLevel.COLUMN
        elif table_unit is not None:
            src_scope = ScopeLevel.TABLE
        else:
            src_scope = ScopeLevel.DOCUMENT

        resolved = UnitAssertion(
            currency=resolved_currency,
            physical_unit=resolved_physical_unit,
            scale_exponent=resolved_scale,
            xbrl_decimals=resolved_decimals,
            source_scope=src_scope,
        )

        return ResolutionStatus.RESOLVED, resolved, None

