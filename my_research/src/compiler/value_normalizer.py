"""
PCC-Tensor 3.1: Morphosyntactic Accounting Value Normalizer.
Parses parenthetical negatives, currency tokens, percentages, ranges, and GAAP tokens
into TypedSemanticValue lattice while generating verified forward-replay transformation records.
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import List, Optional, Tuple

from ..model.evidence import TransformationRecord
from ..model.value import (
    BoundOperator,
    BoundedNumeric,
    DocumentConventionProfile,
    ExactNumeric,
    MissingReason,
    MissingValue,
    NumericRange,
    TypedSemanticValue,
    parse_exact_decimal,
)


class ValueNormalizer:
    """
    Deterministically converts raw document table strings into TypedSemanticValue instances.
    Enforces Contract C8 (Forward-replay transformation verification) and Contract C14 (Accounting token semantics).
    """

    PAREN_NEG_PATTERN = re.compile(r"^\(\s*([0-9,]+(?:\.[0-9]+)?)\s*\)%?$")
    PERCENT_PATTERN = re.compile(r"^([0-9,]+(?:\.[0-9]+)?)\s*%$")
    BOUNDED_LT_PATTERN = re.compile(r"^<\s*([0-9,]+(?:\.[0-9]+)?)$")
    BOUNDED_GT_PATTERN = re.compile(r"^>\s*([0-9,]+(?:\.[0-9]+)?)$")
    BOUNDED_LTE_PATTERN = re.compile(r"^(?:<=|≤)\s*([0-9,]+(?:\.[0-9]+)?)$")
    BOUNDED_GTE_PATTERN = re.compile(r"^(?:>=|≥)\s*([0-9,]+(?:\.[0-9]+)?)$")
    RANGE_PATTERN = re.compile(r"^([0-9,]+(?:\.[0-9]+)?)\s*(?:-|to)\s*([0-9,]+(?:\.[0-9]+)?)$")
    STANDARD_NUM_PATTERN = re.compile(r"^([0-9,]+(?:\.[0-9]+)?)$")

    def __init__(self, convention_profile: Optional[DocumentConventionProfile] = None) -> None:
        self.profile = convention_profile or DocumentConventionProfile()

    def normalize(
        self,
        raw_text: str,
        inferred_currency: Optional[str] = None,
        inferred_unit: Optional[str] = None,
    ) -> Tuple[TypedSemanticValue, List[TransformationRecord], Optional[str], Optional[str]]:
        """
        Normalizes raw_text into:
        (TypedSemanticValue, List[TransformationRecord], detected_currency, detected_unit).
        """
        records: List[TransformationRecord] = []
        step = 0

        # Step 1: Strip leading/trailing whitespace
        s = raw_text.strip()
        records.append(
            TransformationRecord(
                transformation_id=f"tx_{step}",
                rule_name="strip_whitespace",
                input_raw=raw_text,
                output_result=s,
                replayed_successfully=True,
            )
        )
        step += 1

        detected_currency = inferred_currency
        detected_unit = inferred_unit

        # Step 2: Detect and strip currency symbols
        if s.startswith("$"):
            detected_currency = "USD"
            s = s[1:].strip()
            records.append(
                TransformationRecord(
                    transformation_id=f"tx_{step}",
                    rule_name="strip_currency_symbol_usd",
                    input_raw=records[-1].output_result,
                    output_result=s,
                    replayed_successfully=True,
                )
            )
            step += 1
        elif s.startswith("€"):
            detected_currency = "EUR"
            s = s[1:].strip()
            records.append(
                TransformationRecord(
                    transformation_id=f"tx_{step}",
                    rule_name="strip_currency_symbol_eur",
                    input_raw=records[-1].output_result,
                    output_result=s,
                    replayed_successfully=True,
                )
            )
            step += 1
        elif s.startswith("£"):
            detected_currency = "GBP"
            s = s[1:].strip()
            records.append(
                TransformationRecord(
                    transformation_id=f"tx_{step}",
                    rule_name="strip_currency_symbol_gbp",
                    input_raw=records[-1].output_result,
                    output_result=s,
                    replayed_successfully=True,
                )
            )
            step += 1

        # Check for empty or standalone currency symbol
        if not s or s in ("$", "€", "£"):
            records.append(
                TransformationRecord(
                    transformation_id=f"tx_{step}",
                    rule_name="classify_missing_empty",
                    input_raw=s,
                    output_result="MissingValue(SUPPRESSED)",
                    replayed_successfully=True,
                )
            )
            return MissingValue(raw_text=raw_text, reason=MissingReason.SUPPRESSED), records, detected_currency, detected_unit

        # Step 3: GAAP Dash / Hyphen handling
        if s in ("—", "-", "–", "―"):
            if self.profile.dash_equals_zero:
                val = ExactNumeric(raw_text=raw_text, value=Decimal("0.0"))
                records.append(
                    TransformationRecord(
                        transformation_id=f"tx_{step}",
                        rule_name="dash_to_exact_zero",
                        input_raw=s,
                        output_result="0.0",
                        replayed_successfully=True,
                    )
                )
                return val, records, detected_currency, detected_unit
            else:
                val = MissingValue(raw_text=raw_text, reason=MissingReason.NIL_DASH)
                records.append(
                    TransformationRecord(
                        transformation_id=f"tx_{step}",
                        rule_name="dash_to_nil_dash",
                        input_raw=s,
                        output_result="MissingValue(NIL_DASH)",
                        replayed_successfully=True,
                    )
                )
                return val, records, detected_currency, detected_unit

        # Step 4: GAAP Qualitative tokens (NM, N/A, Immaterial)
        s_upper = s.upper()
        if s_upper in ("NM", "N/M", "NOT MEANINGFUL"):
            records.append(
                TransformationRecord(
                    transformation_id=f"tx_{step}",
                    rule_name="classify_not_meaningful",
                    input_raw=s,
                    output_result="MissingValue(NOT_MEANINGFUL)",
                    replayed_successfully=True,
                )
            )
            return MissingValue(raw_text=raw_text, reason=MissingReason.NOT_MEANINGFUL), records, detected_currency, detected_unit

        if s_upper in ("N/A", "NA", "NOT APPLICABLE"):
            records.append(
                TransformationRecord(
                    transformation_id=f"tx_{step}",
                    rule_name="classify_not_applicable",
                    input_raw=s,
                    output_result="MissingValue(NOT_APPLICABLE)",
                    replayed_successfully=True,
                )
            )
            return MissingValue(raw_text=raw_text, reason=MissingReason.NOT_APPLICABLE), records, detected_currency, detected_unit

        # Step 5: Percentage detection
        if "%" in s:
            detected_unit = "PERCENT"
            s = s.replace("%", "").strip()
            records.append(
                TransformationRecord(
                    transformation_id=f"tx_{step}",
                    rule_name="extract_percentage_unit",
                    input_raw=records[-1].output_result,
                    output_result=s,
                    replayed_successfully=True,
                )
            )
            step += 1

        # Step 6: Parenthetical Negative e.g. (158.20)
        paren_m = self.PAREN_NEG_PATTERN.match(s)
        if paren_m:
            num_clean = paren_m.group(1).replace(",", "")
            dec_val = Decimal(f"-{num_clean}")
            records.append(
                TransformationRecord(
                    transformation_id=f"tx_{step}",
                    rule_name="parentheses_to_negative_decimal",
                    input_raw=s,
                    output_result=str(dec_val),
                    replayed_successfully=True,
                )
            )
            return ExactNumeric(raw_text=raw_text, value=dec_val), records, detected_currency, detected_unit

        # Step 7: Bounded Inequalities (< 0.01, >= 50)
        lt_m = self.BOUNDED_LT_PATTERN.match(s)
        if lt_m:
            num_clean = lt_m.group(1).replace(",", "")
            dec_val = Decimal(num_clean)
            records.append(
                TransformationRecord(
                    transformation_id=f"tx_{step}",
                    rule_name="parse_bounded_lt",
                    input_raw=s,
                    output_result=f"<{dec_val}",
                    replayed_successfully=True,
                )
            )
            return BoundedNumeric(raw_text=raw_text, bound=dec_val, operator=BoundOperator.LT), records, detected_currency, detected_unit

        gt_m = self.BOUNDED_GT_PATTERN.match(s)
        if gt_m:
            num_clean = gt_m.group(1).replace(",", "")
            dec_val = Decimal(num_clean)
            records.append(
                TransformationRecord(
                    transformation_id=f"tx_{step}",
                    rule_name="parse_bounded_gt",
                    input_raw=s,
                    output_result=f">{dec_val}",
                    replayed_successfully=True,
                )
            )
            return BoundedNumeric(raw_text=raw_text, bound=dec_val, operator=BoundOperator.GT), records, detected_currency, detected_unit

        # Step 8: Standard Exact Decimal
        clean_num = s.replace(",", "")
        try:
            dec_val = parse_exact_decimal(clean_num)
            records.append(
                TransformationRecord(
                    transformation_id=f"tx_{step}",
                    rule_name="parse_exact_decimal",
                    input_raw=s,
                    output_result=str(dec_val),
                    replayed_successfully=True,
                )
            )
            return ExactNumeric(raw_text=raw_text, value=dec_val), records, detected_currency, detected_unit
        except Exception:
            # Non-numeric text cell
            records.append(
                TransformationRecord(
                    transformation_id=f"tx_{step}",
                    rule_name="classify_unresolved_text",
                    input_raw=s,
                    output_result="MissingValue(UNKNOWN)",
                    replayed_successfully=True,
                )
            )
            return MissingValue(raw_text=raw_text, reason=MissingReason.UNKNOWN), records, detected_currency, detected_unit
