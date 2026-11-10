"""
PCC-Tensor 3.1: Layer L3 — Multi-Source Evidence Provenance (MSEP) & Transformation Ledger.
Enforces Contract C1 (Source integrity) and Contract C13 (Provenance closure).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Tuple

from .source import BoundingBox, SourceRef


class EvidenceRole(str, Enum):
    VALUE = "VALUE"
    METRIC_LABEL = "METRIC_LABEL"
    ROW_CONTEXT = "ROW_CONTEXT"
    COLUMN_HEADER = "COLUMN_HEADER"
    ENTITY_IDENTITY = "ENTITY_IDENTITY"
    UNIT_DECLARATION = "UNIT_DECLARATION"
    PERIOD_DECLARATION = "PERIOD_DECLARATION"
    FOOTNOTE = "FOOTNOTE"
    ACCOUNTING_BASIS = "ACCOUNTING_BASIS"


@dataclass(frozen=True)
class EvidenceAnchor:
    """An independently addressable source evidence region."""
    evidence_id: str
    document_hash: str
    page_id: Optional[str]
    region_id: Optional[str]
    bbox: Optional[BoundingBox]
    raw_text: str
    evidence_role: EvidenceRole
    extraction_method: str = "native"
    adapter_version: str = "3.1.0"


@dataclass(frozen=True)
class MultiSourceProvenanceBundle:
    """
    Contract C13: A fact is supported by a bundle of distinct evidence anchors,
    each responsible for a particular semantic coordinate.
    """
    value_anchor: EvidenceAnchor
    metric_anchor: Optional[EvidenceAnchor] = None
    period_anchor: Optional[EvidenceAnchor] = None
    unit_anchor: Optional[EvidenceAnchor] = None
    entity_anchor: Optional[EvidenceAnchor] = None
    footnote_anchors: Tuple[EvidenceAnchor, ...] = field(default_factory=tuple)

    def is_evidence_closed(self, requires_unit: bool = True, requires_period: bool = True) -> bool:
        """Verifies whether all required coordinate anchors are bound and valid."""
        if not self.value_anchor or not self.value_anchor.raw_text:
            return False
        if requires_unit and not self.unit_anchor:
            return False
        if requires_period and not self.period_anchor:
            return False
        return True


@dataclass(frozen=True)
class TransformationRecord:
    """Forward-replay ledger record for semantic normalizations."""
    transformation_id: str
    rule_name: str
    input_raw: str
    output_result: str
    replayed_successfully: bool


# ==============================================================================
# Executable Deterministic Transformation Registry
# ==============================================================================
import re
from decimal import Decimal
from typing import Callable, Dict, Any


def rule_strip_whitespace(s: str) -> str:
    return s.strip()


def rule_strip_currency_usd(s: str) -> str:
    s = s.strip()
    return s[1:].strip() if s.startswith("$") else s


def rule_strip_currency_eur(s: str) -> str:
    s = s.strip()
    return s[1:].strip() if s.startswith("€") else s


def rule_strip_currency_gbp(s: str) -> str:
    s = s.strip()
    return s[1:].strip() if s.startswith("£") else s


def rule_extract_percentage(s: str) -> str:
    return s.replace("%", "").strip()


def rule_parentheses_to_negative_decimal(s: str) -> str:
    s_clean = s.strip()
    m = re.match(r"^\(\s*([0-9,]+(?:\.[0-9]+)?)\s*\)%?$", s_clean)
    if m:
        num = m.group(1).replace(",", "")
        return f"-{num}"
    raise ValueError(f"Invalid parenthetical negative: '{s}'")


def rule_parse_exact_decimal(s: str) -> str:
    clean = s.replace(",", "").strip()
    d = Decimal(clean)
    return str(d)


def rule_dash_to_exact_zero(s: str) -> str:
    if s.strip() in ("—", "-", "–", "―"):
        return "0.0"
    raise ValueError(f"Not a dash: '{s}'")


def rule_dash_to_nil_dash(s: str) -> str:
    if s.strip() in ("—", "-", "–", "―"):
        return "MissingValue(NIL_DASH)"
    raise ValueError(f"Not a dash: '{s}'")


def rule_classify_not_meaningful(s: str) -> str:
    if s.strip().upper() in ("NM", "N/M", "NOT MEANINGFUL"):
        return "MissingValue(NOT_MEANINGFUL)"
    raise ValueError(f"Not NM: '{s}'")


def rule_classify_not_applicable(s: str) -> str:
    if s.strip().upper() in ("N/A", "NA", "NOT APPLICABLE"):
        return "MissingValue(NOT_APPLICABLE)"
    raise ValueError(f"Not N/A: '{s}'")


def rule_classify_missing_empty(s: str) -> str:
    return "MissingValue(SUPPRESSED)"


def rule_parse_bounded_lt(s: str) -> str:
    m = re.match(r"^<\s*([0-9,]+(?:\.[0-9]+)?)$", s.strip())
    if m:
        num = m.group(1).replace(",", "")
        return f"<{num}"
    raise ValueError(f"Not bounded LT: '{s}'")


def rule_parse_bounded_gt(s: str) -> str:
    m = re.match(r"^>\s*([0-9,]+(?:\.[0-9]+)?)$", s.strip())
    if m:
        num = m.group(1).replace(",", "")
        return f">{num}"
    raise ValueError(f"Not bounded GT: '{s}'")


def rule_parse_bounded_lte(s: str) -> str:
    m = re.match(r"^(?:<=|≤)\s*([0-9,]+(?:\.[0-9]+)?)$", s.strip())
    if m:
        num = m.group(1).replace(",", "")
        return f"<={num}"
    raise ValueError(f"Not bounded LTE: '{s}'")


def rule_parse_bounded_gte(s: str) -> str:
    m = re.match(r"^(?:>=|≥)\s*([0-9,]+(?:\.[0-9]+)?)$", s.strip())
    if m:
        num = m.group(1).replace(",", "")
        return f">={num}"
    raise ValueError(f"Not bounded GTE: '{s}'")


def rule_non_numeric_text(s: str) -> str:
    return "MissingValue(UNKNOWN)"


TRANSFORMATION_REGISTRY: Dict[str, Callable[[str], str]] = {
    "strip_whitespace": rule_strip_whitespace,
    "strip_currency_symbol_usd": rule_strip_currency_usd,
    "strip_currency_symbol_eur": rule_strip_currency_eur,
    "strip_currency_symbol_gbp": rule_strip_currency_gbp,
    "strip_currency": rule_strip_currency_usd,
    "extract_percentage_unit": rule_extract_percentage,
    "parentheses_to_negative_decimal": rule_parentheses_to_negative_decimal,
    "PAREN_NEG": rule_parentheses_to_negative_decimal,
    "parse_exact_decimal": rule_parse_exact_decimal,
    "dash_to_exact_zero": rule_dash_to_exact_zero,
    "dash_to_nil_dash": rule_dash_to_nil_dash,
    "classify_not_meaningful": rule_classify_not_meaningful,
    "classify_not_applicable": rule_classify_not_applicable,
    "classify_missing_empty": rule_classify_missing_empty,
    "parse_bounded_lt": rule_parse_bounded_lt,
    "parse_bounded_gt": rule_parse_bounded_gt,
    "parse_bounded_lte": rule_parse_bounded_lte,
    "parse_bounded_gte": rule_parse_bounded_gte,
    "non_numeric_text": rule_non_numeric_text,
}


def verify_transformation_chain(
    initial_text: str,
    transformations: Tuple[TransformationRecord, ...],
    expected_value: Any,
) -> Tuple[bool, Optional[str], str]:
    """
    Independently executes and verifies a chain of transformations.
    Returns (success: bool, error_code: Optional[str], error_message: str).
    """
    if not transformations:
        return True, None, ""

    first_tx = transformations[0]
    if (
        first_tx.input_raw != initial_text
        and first_tx.input_raw.strip() != initial_text.strip()
        and first_tx.output_result != initial_text
        and first_tx.output_result.strip() != initial_text.strip()
    ):
        return False, "TRANSFORMATION_CHAIN_BROKEN", f"First transformation input '{first_tx.input_raw}' != raw evidence '{initial_text}'."

    curr_str = first_tx.input_raw

    for i, tx in enumerate(transformations):
        # 1. Continuity check
        if tx.input_raw != curr_str:
            return False, "TRANSFORMATION_CHAIN_BROKEN", f"Chain broken at step {i}: input '{tx.input_raw}' != previous output '{curr_str}'."

        # 2. Replay success flag check
        if not tx.replayed_successfully:
            return False, "TRANSFORMATION_REPLAY_MISMATCH", f"Transformation '{tx.rule_name}' at step {i} declared failed."

        # 3. Rule registered check
        rule_fn = TRANSFORMATION_REGISTRY.get(tx.rule_name)
        if rule_fn is None:
            return False, "TRANSFORMATION_REPLAY_MISMATCH", f"Unknown/unregistered transformation rule '{tx.rule_name}'."

        # 4. Execute rule
        try:
            computed = rule_fn(tx.input_raw)
        except Exception as e:
            return False, "TRANSFORMATION_REPLAY_MISMATCH", f"Rule '{tx.rule_name}' execution failed: {e}"

        # 5. Output match check
        if computed != tx.output_result:
            return False, "TRANSFORMATION_REPLAY_MISMATCH", f"Rule '{tx.rule_name}' produced '{computed}', but claimed '{tx.output_result}'."

        curr_str = computed

    # 6. Verify final computed result against expected_value
    from .value import ExactNumeric, BoundedNumeric, MissingValue
    if isinstance(expected_value, ExactNumeric):
        try:
            d = Decimal(curr_str)
            if d != expected_value.value:
                return False, "TRANSFORMATION_REPLAY_MISMATCH", f"Final result '{curr_str}' ({d}) != stored Decimal '{expected_value.value}'."
        except Exception as e:
            return False, "TRANSFORMATION_REPLAY_MISMATCH", f"Cannot convert final result '{curr_str}' to Decimal: {e}"
    elif isinstance(expected_value, BoundedNumeric):
        try:
            clean_bound = curr_str.lstrip("<>=≤≥ ")
            d = Decimal(clean_bound)
            if d != expected_value.bound:
                return False, "TRANSFORMATION_REPLAY_MISMATCH", f"Final bound {d} != stored bound {expected_value.bound}."
        except Exception as e:
            return False, "TRANSFORMATION_REPLAY_MISMATCH", f"Cannot parse final bounded value '{curr_str}': {e}"
    elif isinstance(expected_value, MissingValue):
        if not (curr_str.startswith("MissingValue") or curr_str == "0.0"):
            return False, "TRANSFORMATION_REPLAY_MISMATCH", f"Final result '{curr_str}' is not a valid MissingValue representation."

    return True, None, ""

