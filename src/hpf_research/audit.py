"""Auditable Shanghai HPF accounting checks; Python >= 3.10, stdlib only."""
from __future__ import annotations

import csv
import json
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
Y = Decimal("0.01")
ROUNDING_TOLERANCE = Decimal("0.021")
SECURITIZATION_TRANSFER_2016 = Decimal("312.02")


def records(relative_path: str) -> list[dict[str, str]]:
    path = ROOT / relative_path
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def value(row: dict[str, str], field: str) -> Decimal:
    return Decimal(row[field])


def reconcile() -> dict:
    annual = {int(r["year"]): r for r in records("data/raw/annual_2015_2025.csv")}
    if sorted(annual) != list(range(2015, 2026)):
        raise ValueError("Annual coverage is incomplete")
    rows = []
    for year in range(2016, 2026):
        now, prev = annual[year], annual[year - 1]
        fund_delta = (value(now, "fund_balance_100m")
                      - value(prev, "fund_balance_100m")
                      - value(now, "contributions_100m")
                      + value(now, "withdrawals_100m"))
        transfer = SECURITIZATION_TRANSFER_2016 if year == 2016 else Decimal(0)
        loan_delta = (value(now, "loan_balance_100m")
                      - value(prev, "loan_balance_100m")
                      - value(now, "loan_issued_100m")
                      + value(now, "loan_recovered_100m")
                      + transfer)
        rows.append({"year": year, "fund_residual_100m": float(fund_delta),
                     "loan_residual_100m": float(loan_delta),
                     "securitization_outflow_100m": float(transfer),
                     "passes": abs(fund_delta) <= ROUNDING_TOLERANCE
                     and abs(loan_delta) <= ROUNDING_TOLERANCE})
    verified_all = []
    yearly_coverage = {}
    for district_year in range(2022, 2026):
        coverage = records(f"data/processed/district_monthly_{district_year}_coverage.csv")
        unique = {(r["year"], r["month"], r["district"]) for r in coverage}
        verified = [r for r in coverage if r["source_status"] in
                    ("verified_index_table", "verified_original_html")]
        if len(unique) != 192 or len(coverage) != 192:
            raise ValueError(f"Expected exactly 192 unique {district_year} district-month records")
        if any(r["year_to_date_collection_10k_cny"] or r["year_to_date_withdrawals_10k_cny"]
               for r in coverage if r["source_status"] == "not_obtained"):
            raise ValueError("Missing records contain invented amount(s)")
        if any(int(r["year"]) != district_year or
               not r["as_of"].startswith(str(district_year)) or
               not r["source_url"].startswith("https://www.shzfgjj.cn/")
               for r in coverage):
            raise ValueError(f"Invalid {district_year} record provenance")
        for district in {r["district"] for r in coverage}:
            series = sorted((r for r in verified if r["district"] == district),
                            key=lambda r: int(r["month"]))
            for field in ("year_to_date_collection_10k_cny", "year_to_date_withdrawals_10k_cny"):
                if any(value(b, field) < value(a, field) for a, b in zip(series, series[1:])):
                    raise ValueError(f"Cumulative {field} decreases in {district}/{district_year}")
        december = [r for r in verified if r["month"] == "12"]
        district_withdrawals = sum((value(r, "year_to_date_withdrawals_10k_cny")
                                    for r in december), Decimal(0)) / 10000
        if abs(district_withdrawals - value(annual[district_year], "withdrawals_100m")) > Decimal("0.005"):
            raise ValueError(f"{district_year} district withdrawals disagree with annual report")
        verified_all.extend(verified)
        yearly_coverage[str(district_year)] = len(verified)
    fin = {(r["metric"], int(r["year"])): value(r, "amount_100m")
           for r in records("data/raw/financial_items_2024_2025.csv")}
    income_residuals = {
        str(year): float(fin["business_income", year] - fin["business_expense", year]
                         - fin["added_value_income", year])
        for year in (2024, 2025)
    }
    net_lending = value(annual[2025], "loan_issued_100m") - value(annual[2025], "loan_recovered_100m")
    return {
        "years": [2015, 2025],
        "loan_rate_pct_2025": float(value(annual[2025], "loan_balance_100m")
                                    / value(annual[2025], "fund_balance_100m") * 100),
        "net_lending_2025_100m": float(net_lending),
        "annual_flow_checks": rows,
        "flow_checks_all_pass": all(r["passes"] for r in rows),
        "district_month_coverage": {"expected": 192, "verified": yearly_coverage["2025"],
                                    "ratio_pct": round(100 * yearly_coverage["2025"] / 192, 2)},
        "multi_year_district_coverage": {"expected": 768, "verified": len(verified_all),
                                         "by_year": yearly_coverage},
        "income_residuals_100m": income_residuals,
    }


def main() -> None:
    result = reconcile()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["flow_checks_all_pass"]:
        raise SystemExit("ERROR: an accounting identity exceeds tolerance")
    if any(abs(v) > 0.021 for v in result["income_residuals_100m"].values()):
        raise SystemExit("ERROR: financial-income reconciliation failure")


if __name__ == "__main__":
    main()
