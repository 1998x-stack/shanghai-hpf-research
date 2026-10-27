"""Tests include negative controls and exact 16-district panel counts."""
from decimal import Decimal
import pytest
from hpf_research.seasonality import analyze, delta, top_batch_months


def test_complete_2022_2025_panel_has_synchronization():
    district, annual = analyze()
    assert len(district) == 64 and len(annual) == 4
    assert all(x["april_and_september_are_strict_top_two"] == "yes" for x in district)
    assert all(x["districts_with_strict_april_september_top_two"] == "16"
               for x in annual)


def test_two_month_share_and_huangpu_robustness():
    _, annual = analyze()
    assert [x["batch_withdrawals_share_pct"] for x in annual] == [
        "23.160691", "25.551799", "26.193697", "27.852918"]
    y25 = annual[-1]
    assert y25["batch_collection_share_pct"] == "17.000749"
    assert y25["batch_withdrawals_share_without_huangpu_pct"] == "28.820113"
    assert y25["huangpu_annual_withdrawals_share_pct"] == "31.237499"


def test_neither_ties_nor_wrong_month_prove_rule():
    x = [Decimal(1)] * 12
    x[3], x[8] = Decimal(2), Decimal(3)
    assert top_batch_months(x)
    x[1] = Decimal(4)
    assert not top_batch_months(x)
    x[1] = Decimal(1)
    x[3] = Decimal(1)
    assert not top_batch_months(x)


def test_monthly_flow_must_difference_ytd():
    assert delta([Decimal(i) for i in range(1, 13)]) == [Decimal(1)] * 12
    with pytest.raises(ValueError, match="declining cumulative"):
        delta([Decimal(2), Decimal(1)] + [Decimal(3)] * 10)
    with pytest.raises(ValueError, match="Expected 12"):
        delta([Decimal(1)])


def test_outcome_is_not_claimed_as_measured_annual_repayment_amount():
    _, rows = analyze()
    assert all(x["identification_status"].startswith("descriptive_") for x in rows)
    assert all(Decimal(x["district_withdrawals_hhi"]) < 1 for x in rows)
