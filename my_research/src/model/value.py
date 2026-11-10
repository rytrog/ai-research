"""
PCC-Tensor 3.1: Layer L2 — Typed Semantic Value Lattice & Exact Decimal Arithmetic.
Enforces Contract C8 (Raw-value preservation) and Contract C9 (Typed-value validity).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, Context, ROUND_HALF_EVEN
from enum import Enum
from typing import Optional, Union

# Global Accounting Decimal Context (28 decimal places, Banker's Rounding)
DECIMAL_CONTEXT = Context(prec=28, rounding=ROUND_HALF_EVEN)


def parse_exact_decimal(raw: str) -> Decimal:
    """Parses a cleaned numeric string into a Decimal within the canonical context."""
    cleaned = raw.replace(",", "").strip()
    return DECIMAL_CONTEXT.create_decimal(cleaned)


class BoundOperator(str, Enum):
    LT = "LT"   # <
    LE = "LE"   # <=
    GT = "GT"   # >
    GE = "GE"   # >=


class MissingReason(str, Enum):
    NIL_DASH = "NIL_DASH"              # "—" or "-" symbol (document-convention dependent)
    REPORTED_ZERO = "REPORTED_ZERO"    # Explicit "0", "0.00"
    NOT_APPLICABLE = "NOT_APPLICABLE"  # "N/A"
    NOT_MEANINGFUL = "NOT_MEANINGFUL"  # "NM" (ratio base zero or negative)
    IMMATERIAL = "IMMATERIAL"          # Confirmed immaterial disclosure
    SUPPRESSED = "SUPPRESSED"          # Confidential or redacted "***"
    UNKNOWN = "UNKNOWN"                # Unresolved non-numeric text


@dataclass(frozen=True)
class ExactNumeric:
    """Exact numerical quantity with preserved raw verbatim representation."""
    raw_text: str
    value: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.value, Decimal):
            raise TypeError(f"Value must be a decimal.Decimal instance, got {type(self.value)}")


@dataclass(frozen=True)
class BoundedNumeric:
    """Inequality-bounded numerical measurement (e.g., '< 0.01')."""
    raw_text: str
    bound: Decimal
    operator: BoundOperator

    def __post_init__(self) -> None:
        if not isinstance(self.bound, Decimal):
            raise TypeError(f"Bound must be a decimal.Decimal instance, got {type(self.bound)}")


@dataclass(frozen=True)
class NumericRange:
    """Interval of values (e.g., '10.5 - 12.0'). Lower <= Upper required."""
    raw_text: str
    lower_bound: Decimal
    upper_bound: Decimal
    lower_inclusive: bool = True
    upper_inclusive: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.lower_bound, Decimal) or not isinstance(self.upper_bound, Decimal):
            raise TypeError("Bounds must be decimal.Decimal instances.")
        if self.lower_bound > self.upper_bound:
            raise ValueError(f"Contract C9 violation: lower ({self.lower_bound}) > upper ({self.upper_bound})")


@dataclass(frozen=True)
class MissingValue:
    """Non-numeric or non-disclosed cell status."""
    raw_text: str
    reason: MissingReason
    convention_note: Optional[str] = None


@dataclass(frozen=True)
class DocumentConventionProfile:
    """Declares explicit filing/report interpretation rules."""
    dash_equals_zero: bool = False
    asterisk_is_footnote: bool = True
    parentheses_are_negative: bool = True
    default_currency: str = "USD"
    default_scale_exponent: int = 6  # Default 10^6 ($ Millions) for SEC schedules
    locale_decimal_separator: str = "."
    locale_grouping_separator: str = ","


# Tagged Union for all parsed cell semantics
TypedSemanticValue = Union[ExactNumeric, BoundedNumeric, NumericRange, MissingValue]
