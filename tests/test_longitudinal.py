"""Independent checks of source snapshots and cross-year bridge arithmetic."""
import csv
import hashlib
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def rows(path):
    with (ROOT / path).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def test_all_48_monthly_sources_are_archived_and_hashed():
    sources = rows("sources/manifest.csv")
    pages = [r for r in sources if r["id"].startswith("MONTH-")]
    assert len(pages) == 48
    for page in pages:
        data = (ROOT / page["snapshot_status"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == page["original_sha256"]
        assert page["publication_date"] and page["retrieved_date"]


def test_four_year_withdrawals_reconcile_independently():
    annual = {int(r["year"]): r for r in rows("data/raw/annual_2015_2025.csv")}
    for year in range(2022, 2026):
        district = rows(f"data/processed/district_monthly_{year}_coverage.csv")
        assert len(district) == 192
        december = [r for r in district if r["month"] == "12"]
        total = sum((Decimal(r["year_to_date_withdrawals_10k_cny"])
                     for r in december), Decimal(0)) / 10000
        assert abs(total - Decimal(annual[year]["withdrawals_100m"])) < Decimal("0.005")


def test_interest_is_close_to_but_not_identical_with_collection_gap():
    annual = {int(r["year"]): r for r in rows("data/raw/annual_2015_2025.csv")}
    interest = {int(r["year"]): r for r in rows("data/raw/interest_expense_2022_2025.csv")}
    for year in range(2022, 2026):
        district = rows(f"data/processed/district_monthly_{year}_coverage.csv")
        collection = sum((Decimal(r["year_to_date_collection_10k_cny"])
                          for r in district if r["month"] == "12"), Decimal(0)) / 10000
        gap = Decimal(annual[year]["contributions_100m"]) - collection
        remainder = gap - Decimal(interest[year]["contributor_interest_expense_100m"])
        assert Decimal("-7") < remainder < Decimal("-6")


def test_risk_allocation_2021_2025_near_80_percent():
    for r in rows("data/raw/reserve_allocation_2015_2025.csv"):
        if int(r["year"]) >= 2021:
            ratio = Decimal(r["risk_provision_100m"]) / Decimal(r["hpf_added_value_100m"])
            assert abs(ratio - Decimal("0.8")) < Decimal("0.0001")


def test_annual_core_transcriptions_have_labelled_source_locations():
    audit = rows("data/processed/annual_source_audit.csv")
    assert len(audit) == 77
    assert all(r["label_match"] == "yes" and r["source_context"] and r["source_url"]
               for r in audit)


def test_pre_policy_april_and_september_peaks_exist():
    for year in (2023, 2024, 2025):
        district = rows(f"data/processed/district_monthly_{year}_coverage.csv")
        cumulative = {month: sum((Decimal(r["year_to_date_withdrawals_10k_cny"])
                                  for r in district if r["month"] == str(month)), Decimal(0))
                      for month in range(1, 13)}
        flows = {month: cumulative[month] - cumulative.get(month - 1, Decimal(0))
                 for month in range(1, 13)}
        for month in (4, 9):
            assert flows[month] > flows[month - 1] * Decimal("1.5")
            assert flows[month] > flows[month + 1] * Decimal("1.5")


def test_fiscal_appropriations_are_within_annual_management_fee_rounding():
    fiscal = {(int(r["year"]), r["basis"], r["metric"]): Decimal(r["value_10k_cny"])
              for r in rows("data/raw/center_fiscal_2024_2025.csv")}
    for year, rounded_fee_10k in [(2024, Decimal("20200")), (2025, Decimal("20800"))]:
        actual = fiscal[(year, "unit_final_accounts", "fiscal_appropriation_income")]
        assert abs(actual - rounded_fee_10k) <= Decimal("50")
    assert fiscal[(2025, "unit_final_accounts", "total_income")] - \
        fiscal[(2025, "unit_budget", "total_income")] == Decimal("113.04")
