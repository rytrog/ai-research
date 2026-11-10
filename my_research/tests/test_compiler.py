"""
PCC-Tensor 3.1: Unit & Integration Tests for Semantic Compiler & Poset Resolution.
Validates Row Hierarchy, Value Normalizer, Scope Resolver, and End-to-End Table Compilation.
"""

from __future__ import annotations

import datetime
import pathlib
from decimal import Decimal
import pytest

from my_research.src.adapter.ascii_table import AsciiTableScheduleAdapter
from my_research.src.adapter.base import BaseTableAdapter

DATA_DIR = pathlib.Path(__file__).resolve().parent.parent / "data"
from my_research.src.compiler.row_hierarchy import RowHierarchyBuilder
from my_research.src.compiler.scope_resolver import ScopeResolver
from my_research.src.compiler.table_compiler import TableCompiler
from my_research.src.compiler.value_normalizer import ValueNormalizer
from my_research.src.model.ctir import ValidationStatus
from my_research.src.model.structural import LogicalRow
from my_research.src.model.temporal import DurationPeriod, InstantPeriod
from my_research.src.model.value import (
    BoundOperator,
    BoundedNumeric,
    DocumentConventionProfile,
    ExactNumeric,
    MissingReason,
    MissingValue,
)


# ==============================================================================
# Row Hierarchy Builder Tests
# ==============================================================================
def test_row_hierarchy_builder():
    rows = [
        LogicalRow(row_id="R0", position=0, parent_row_id=None, role="SECTION", raw_label="REVENUE", indent_depth=0),
        LogicalRow(row_id="R1", position=1, parent_row_id=None, role="DETAIL", raw_label="Product A", indent_depth=1),
        LogicalRow(row_id="R2", position=2, parent_row_id=None, role="DETAIL", raw_label="Product B", indent_depth=1),
        LogicalRow(row_id="R3", position=3, parent_row_id=None, role="SUBTOTAL", raw_label="Subtotal Products", indent_depth=2),
        LogicalRow(row_id="R4", position=4, parent_row_id=None, role="TOTAL", raw_label="TOTAL REVENUE", indent_depth=0),
    ]

    builder = RowHierarchyBuilder()
    refined_rows, graph = builder.build_hierarchy(rows)

    assert len(refined_rows) == 5
    # Product A parent is REVENUE
    assert refined_rows[1].parent_row_id == "R0"
    assert refined_rows[1].ancestor_path == ("REVENUE",)

    # Subtotal parent is R0 or R2
    assert refined_rows[3].ancestor_path == ("REVENUE",)

    # Total row resets
    assert refined_rows[4].parent_row_id is None
    assert refined_rows[4].ancestor_path == ()

    is_dag, err = graph.validate_acyclic_dag()
    assert is_dag is True


# ==============================================================================
# Value Normalizer Tests
# ==============================================================================
def test_value_normalizer_parenthetical_negatives():
    norm = ValueNormalizer()
    val, records, curr, unit = norm.normalize("(158.20)")

    assert isinstance(val, ExactNumeric)
    assert val.value == Decimal("-158.20")
    assert len(records) >= 2


def test_value_normalizer_currency_and_percentages():
    norm = ValueNormalizer()

    val_curr, recs1, curr1, unit1 = norm.normalize("$  274.80")
    assert isinstance(val_curr, ExactNumeric)
    assert val_curr.value == Decimal("274.80")
    assert curr1 == "USD"

    val_pct, recs2, curr2, unit2 = norm.normalize("34.92%")
    assert isinstance(val_pct, ExactNumeric)
    assert val_pct.value == Decimal("34.92")
    assert unit2 == "PERCENT"

    val_pct_neg, recs3, curr3, unit3 = norm.normalize("(24.05)%")
    assert isinstance(val_pct_neg, ExactNumeric)
    assert val_pct_neg.value == Decimal("-24.05")
    assert unit3 == "PERCENT"


def test_value_normalizer_bounded_and_gaap_tokens():
    norm = ValueNormalizer()

    val_lt, _, _, _ = norm.normalize("< 0.01")
    assert isinstance(val_lt, BoundedNumeric)
    assert val_lt.operator == BoundOperator.LT
    assert val_lt.bound == Decimal("0.01")

    val_nm, _, _, _ = norm.normalize("NM")
    assert isinstance(val_nm, MissingValue)
    assert val_nm.reason == MissingReason.NOT_MEANINGFUL

    # Test convention profile dash as ZERO
    norm_dash_zero = ValueNormalizer(DocumentConventionProfile(dash_equals_zero=True))
    val_dash, _, _, _ = norm_dash_zero.normalize("—")
    assert isinstance(val_dash, ExactNumeric)
    assert val_dash.value == Decimal("0.0")


# ==============================================================================
# Scope Resolver Tests
# ==============================================================================
def test_scope_resolver_temporal_interval_disambiguation():
    tme_headers = ("Three Months Ended", "September 30", "2026")
    nme_headers = ("Nine Months Ended", "September 30", "2026")

    p_tme = ScopeResolver.resolve_period_from_headers(tme_headers)
    p_nme = ScopeResolver.resolve_period_from_headers(nme_headers)

    assert isinstance(p_tme, DurationPeriod)
    assert isinstance(p_nme, DurationPeriod)

    assert p_tme.start_date == datetime.date(2026, 7, 1)
    assert p_tme.end_date == datetime.date(2026, 9, 30)

    assert p_nme.start_date == datetime.date(2026, 1, 1)
    assert p_nme.end_date == datetime.date(2026, 9, 30)

    # Three Months duration != Nine Months duration
    assert p_tme.duration_days < p_nme.duration_days


def test_scope_resolver_instant_headcount():
    headers = ("Three Months Ended", "September 30", "2026")
    p_headcount = ScopeResolver.resolve_period_from_headers(headers, row_label="Total Global Full-Time Employees (Headcount Units)")

    assert isinstance(p_headcount, InstantPeriod)
    assert p_headcount.as_of_date == datetime.date(2026, 9, 30)


# ==============================================================================
# End-to-End Compilation & Formal Validation on SEC Adversarial Schedule
# ==============================================================================
def test_end_to_end_compiler_on_sec_adversarial_schedule():
    schedule_path = DATA_DIR / "sec_10k_adversarial_schedule.txt"
    with open(schedule_path, "r", encoding="utf-8") as f:
        content = f.read()

    doc, _ = BaseTableAdapter.create_source_document("doc_sec_10q", content, "text/plain")
    adapter = AsciiTableScheduleAdapter()
    frag, footnotes, coord_space = adapter.parse(doc, content, table_id="t_sec_10q")

    compiler = TableCompiler()
    snapshot = compiler.compile(
        source_doc=doc,
        fragment=frag,
        footnotes=footnotes,
        entity_name="Chronos Technologies Group Inc.",
        snapshot_id="snap_sec_10q_01",
        coordinate_space=coord_space,
    )

    # 1. Formal Validation Gate Check
    assert snapshot.validation_report is not None
    assert snapshot.validation_report.schema_status == ValidationStatus.PASS
    assert snapshot.validation_report.source_status == ValidationStatus.PASS
    assert snapshot.validation_report.geometry_status == ValidationStatus.PASS
    assert snapshot.validation_report.structure_status == ValidationStatus.PASS
    assert snapshot.validation_report.provenance_status == ValidationStatus.PASS
    assert len(snapshot.coordinate_spaces) == 1
    assert snapshot.coordinate_spaces[0].kind == "MARKDOWN_OFFSET"

    # 2. Check Fact Extractions
    facts = list(snapshot.source_facts.values())
    assert len(facts) > 100

    # 3. Check Kronos-7 Revenue Fact (Row 21 in schedule, Col 1: Three Months Ended Sept 30, 2026)
    k7_fact = next(
        f for f in facts
        if "Optical Interconnect" in f.coordinates.raw_metric_label
        and "Three Months Ended" in f.coordinates.column_ancestor_path
        and "2026" in f.coordinates.column_ancestor_path
    )
    assert isinstance(k7_fact.typed_value, ExactNumeric)
    assert k7_fact.typed_value.value == Decimal("274.80")
    # Multiplied by $ Millions scale (10^6)
    assert k7_fact.canonical_display == "USD 274,800,000.00"

    # 4. Check Operating Loss Fact (Parenthetical negative (158.20))
    ebit_fact = next(
        f for f in facts
        if "OPERATING INCOME / (LOSS)" in f.coordinates.raw_metric_label
        and "Three Months Ended" in f.coordinates.column_ancestor_path
        and "2026" in f.coordinates.column_ancestor_path
    )
    assert isinstance(ebit_fact.typed_value, ExactNumeric)
    assert ebit_fact.typed_value.value == Decimal("-158.20")
    assert ebit_fact.canonical_display == "USD -158,200,000.00"

    # 5. Check Diluted Shares Fact (in thousands -> scale 10^3)
    shares_fact = next(
        f for f in facts
        if "Diluted" in f.coordinates.raw_metric_label
        and "Shares" in f.coordinates.raw_metric_label
        and "Three Months Ended" in f.coordinates.column_ancestor_path
        and "2026" in f.coordinates.column_ancestor_path
    )
    assert isinstance(shares_fact.typed_value, ExactNumeric)
    assert shares_fact.typed_value.value == Decimal("120000")
    assert shares_fact.unit.scale_exponent == 3
    assert shares_fact.canonical_display == "120,000,000.00 shares"

    # 6. Check Diluted EPS Fact (in $ per share -> scale 10^0)
    eps_fact = next(
        f for f in facts
        if "Diluted Earnings / (Loss) Per Share" in f.coordinates.raw_metric_label
        and "Three Months Ended" in f.coordinates.column_ancestor_path
        and "2026" in f.coordinates.column_ancestor_path
    )
    assert isinstance(eps_fact.typed_value, ExactNumeric)
    assert eps_fact.typed_value.value == Decimal("-1.32")
    assert eps_fact.unit.scale_exponent == 0
    assert eps_fact.canonical_display == "USD -1.32 per share"

    # 7. Check Footnote Provenance Binding (Photomask Reserve row links to Footnote 2)
    photo_fact = next(
        f for f in facts
        if "Lithography Photomask" in f.coordinates.raw_metric_label
        and "Three Months Ended" in f.coordinates.column_ancestor_path
        and "2026" in f.coordinates.column_ancestor_path
    )
    assert len(photo_fact.provenance.footnote_anchors) >= 1
    fn_text = photo_fact.provenance.footnote_anchors[0].raw_text
    assert "lithography photomask recalibration" in fn_text
