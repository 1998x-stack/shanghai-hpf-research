from decimal import Decimal
import pytest
from hpf_research.external import evidence_rows, triangulate

def test_cross_source_evidence_unique_and_unitized():
    observed = evidence_rows()
    assert (2025, "hpf_center_total_budget") in observed
    assert len(observed) == 22

def test_property_market_uses_distinct_denominators():
    r = triangulate()["market"]
    assert r["new_residential_sales_area_yoy_pct"] == pytest.approx(-9.71453, abs=0.001)
    assert r["existing_property_registered_area_yoy_pct"] == pytest.approx(15.08008, abs=0.001)
    assert r["hpf_new_home_loan_count_yoy_est_pct"] == pytest.approx(-31.58138, abs=0.001)
    assert r["hpf_resale_loan_count_yoy_est_pct"] == pytest.approx(-5.75525, abs=0.001)
    assert "different populations" in r["warning"]

def test_center_budget_accounting_is_not_hpf_fund_accounting():
    r = triangulate()["fiscal_bridge"]
    assert r["center_total_budget_cny"] == 212355400
    assert r["center_fiscal_appropriation_budget_cny"] + r["center_other_income_budget_cny"] == 212355400
    assert r["center_employer_hpf_budget_cny"] == 5554200
    assert r["actual_management_cost_reported_cny"] == 208000000
    assert "different ledgers" in r["warning"]

def test_published_enforcement_ratio_flags_unidentified_denominator():
    r = triangulate()["enforcement"]
    assert r["simple_2413_div_4441_rate_pct"] == pytest.approx(54.334609, abs=0.0001)
    assert r["reported_prefiling_resolution_rate_pct"] == 55.86
    assert r["difference_percentage_points"] > 1.5
    assert r["status"].startswith("Denominator")

def test_external_metrics_source_urls_are_public_authorities():
    rows = evidence_rows()
    allowed = ("tjj.sh.gov.cn", "www.shzfgjj.cn", "zjw.sh.gov.cn")
    assert all(any(domain in r["source_url"] for domain in allowed)
               for r in rows.values())
