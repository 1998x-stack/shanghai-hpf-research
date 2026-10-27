from decimal import Decimal
from hashlib import sha256
from pathlib import Path
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

def test_all_official_months_are_verified():
    audit = reconcile()
    assert audit["district_month_coverage"] == {
        "expected": 192, "verified": 192, "ratio_pct": 100.0
    }
    rows = records("data/processed/district_monthly_2025_coverage.csv")
    assert all(row["source_status"] == "verified_original_html" for row in rows)
    assert all(row["year_to_date_collection_10k_cny"] and row["source_url"]
               for row in rows)

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

def test_monthly_snapshots_match_provenance():
    root = Path(__file__).resolve().parents[1]
    pages = records("sources/original/monthly_2025/provenance.csv")
    assert len(pages) == 12
    for page in pages:
        raw = (root / page["snapshot_path"]).read_bytes()
        assert sha256(raw).hexdigest() == page["sha256"]
