from decimal import Decimal
import pytest

from hpf_research.audit import records, reconcile

def test_yearly_fund_and_loan_flows():
    audit = reconcile()
    assert audit["flow_checks_all_pass"]
    assert len(audit["annual_flow_checks"]) == 10

def test_2016_securitization_adjustment_is_explicit():
    audit = reconcile()
    y2016 = next(v for v in audit["annual_flow_checks"] if v["year"] == 2016)
    assert y2016["securitization_outflow_100m"] == 312.02
    assert abs(y2016["loan_residual_100m"]) < 0.021

def test_2025_net_loan_increase():
    assert reconcile()["net_lending_2025_100m"] == pytest.approx(5.99)

def test_missing_months_do_not_gain_fake_numbers():
    audit = reconcile()
    assert audit["district_month_coverage"] == {
        "expected": 192, "verified": 16, "ratio_pct": 8.33
    }
    rows = records("data/processed/district_monthly_2025_coverage.csv")
    assert all(not row["year_to_date_collection_10k_cny"]
               for row in rows if row["source_status"] == "not_obtained")

def test_annual_records_provide_official_provenance():
    years = records("data/raw/annual_2015_2025.csv")
    assert len(years) == 11
    assert all("shzfgjj.cn" in r["source_url"] for r in years)

def test_accounting_income_identity():
    audit = reconcile()
    assert all(abs(v) < 0.021 for v in audit["income_residuals_100m"].values())

def test_monthly_cross_section_is_cumulative_not_current_month():
    rows = records("data/processed/district_monthly_2025_coverage.csv")
    aug = [r for r in rows if r["month"] == "8"]
    assert len(aug) == 16
    assert sum((Decimal(r["year_to_date_collection_10k_cny"]) for r in aug),
               Decimal(0)) / 10000 == Decimal("1659.604849")
    assert sum((Decimal(r["year_to_date_withdrawals_10k_cny"]) for r in aug),
               Decimal(0)) / 10000 == Decimal("1165.444434")
