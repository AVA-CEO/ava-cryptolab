"""Synthetic comparison only: agreement is not verified broker reconciliation."""

from copy import deepcopy
from decimal import Decimal

import pytest
from cfd_position_examples import evidence, jpy_position, position_example

from app.analytics.cfd_positions import calculate_position


@pytest.mark.parametrize(
    ("metric", "amount"),
    [
        ("gross_pnl", "26"),
        ("net_pnl", "22"),
        ("adjustments", "-4"),
        ("commission", "-2"),
        ("swap", "-2"),
        ("fee", "0"),
        ("other", "0"),
    ],
)
def test_matching_scope_preserves_calculated_and_reported_values(metric, amount):
    data = position_example(costs=True)
    item = evidence(data, metric=metric, amount=amount)
    data["broker_evidence"] = [item]
    before = deepcopy(data)
    result = calculate_position(data)
    comparison = result.comparisons[0]
    assert comparison.status == "within_tolerance"
    assert comparison.evidence.amount == Decimal(amount)
    assert comparison.calculated.raw == Decimal(amount)
    assert comparison.difference.raw == 0 and comparison.within_tolerance is True
    assert result.native.net_pnl.raw == 22 and data == before


def test_mismatch_reports_difference_without_substituting_broker_pnl():
    data = position_example(costs=True)
    data["broker_evidence"] = [evidence(data, amount="99")]
    result = calculate_position(data)
    comparison = result.comparisons[0]
    assert result.native.net_pnl.raw == 22
    assert comparison.evidence.amount == 99
    assert comparison.difference.raw == -77
    assert comparison.status == "difference" and comparison.within_tolerance is False


@pytest.mark.parametrize(
    "changes",
    [
        {"position_reference": "different"},
        {"account_id": "different"},
        {"instrument_id": "different"},
        {"original_lots": "0.20"},
        {"exited_lots": "0.04"},
        {"original_lots": None},
        {"as_of": "2025-01-04T00:00:00Z"},
        {"state": "partial"},
        {"currency": "USDT"},
        {"recognition_policy": "unknown"},
        {"recognition_policy": "other"},
    ],
)
def test_incomparable_evidence_is_preserved_but_not_compared(changes):
    data = position_example(costs=True)
    data["broker_evidence"] = [evidence(data, **changes)]
    result = calculate_position(data)
    assert result.status == "calculated" and result.native.net_pnl.raw == 22
    comparison = result.comparisons[0]
    assert comparison.status == "unavailable"
    assert comparison.difference.raw is None and comparison.within_tolerance is None
    assert comparison.evidence.amount == 22 and comparison.unavailable_reason


@pytest.mark.parametrize(
    ("amount", "tolerance", "status"),
    [
        ("22.01", "0.01", "within_tolerance"),
        ("22.0101", "0.01", "difference"),
        ("21.99", "0.01", "within_tolerance"),
        ("22.01", "0", "difference"),
    ],
)
def test_explicit_currency_tolerance_is_inclusive(amount, tolerance, status):
    data = position_example(costs=True)
    data["broker_evidence"] = [evidence(data, amount=amount, absolute_tolerance=tolerance)]
    assert calculate_position(data).comparisons[0].status == status


def test_raw_and_display_rounding_bases_are_distinct():
    data = position_example(costs=True)
    data["trade"]["adjustments"][0]["amount"] = "-1.005"
    data["broker_evidence"] = [
        evidence(data, amount="22", comparison_basis="raw", absolute_tolerance="0.001"),
        evidence(
            data,
            evidence_id="display",
            amount="22",
            comparison_basis="display_rounded",
            absolute_tolerance="0",
        ),
    ]
    result = calculate_position(data)
    assert result.native.net_pnl.raw == Decimal("21.995")
    assert result.native.net_pnl.rounded == 22
    assert [item.status for item in result.comparisons] == ["difference", "within_tolerance"]
    assert result.comparisons[0].difference.raw == Decimal("-0.005")


def test_partial_comparison_requires_partial_state_and_same_cutoff():
    data = position_example(costs=True)
    data["as_of"] = "2025-01-04T00:00:00Z"
    data["broker_evidence"] = [evidence(data, state="partial", amount="6.5")]
    assert calculate_position(data).comparisons[0].status == "within_tolerance"


def test_reporting_evidence_can_compare_when_native_net_is_unavailable():
    data = jpy_position(costs=True)
    data["broker_evidence"] = [evidence(data, basis="reporting", amount="13.44")]
    result = calculate_position(data)
    assert result.comparisons[0].status == "within_tolerance"
    data["broker_evidence"][0].update(basis="native", currency="JPY")
    assert calculate_position(data).comparisons[0].status == "unavailable"


@pytest.mark.parametrize(
    "changes",
    [
        {"absolute_tolerance": "-0.01"},
        {"absolute_tolerance": 0.01},
        {"amount": 0.1},
        {"reported_at": "2025-01-04T00:00:00Z"},
        {"source": {"kind": "manual", "reference": ""}},
    ],
)
def test_invalid_evidence_is_rejected(changes):
    data = position_example(costs=True)
    data["broker_evidence"] = [evidence(data, **changes)]
    result = calculate_position(data)
    assert result.status == "unavailable" and result.reason_code == "invalid_input"


def test_duplicate_evidence_ids_are_rejected():
    data = position_example(costs=True)
    data["broker_evidence"] = [evidence(data), evidence(data)]
    assert calculate_position(data).reason_code == "invalid_input"
