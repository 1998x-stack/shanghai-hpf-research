"""Reconcile calendar-year district collection with June-account interest settlements.

A June settlement is NOT the same metric as calendar-year interest expense.
Residuals are descriptive differences, not yet proven accounting adjustments.
"""
from __future__ import annotations

from decimal import Decimal
import json

from .audit import records


def settlement_bridge() -> list[dict]:
    bridge = {int(r["year"]): r
              for r in records("data/processed/annual_district_bridge_2022_2025.csv")}
    annual = {int(r["year"]): r
              for r in records("data/raw/annual_2015_2025.csv")}
    notice_rows = records("data/external/account_interest_settlement_2022_2025.csv")
    if len(notice_rows) != 4:
        raise ValueError("Expected four published settlement observations")
    if sorted(bridge) != [2022, 2023, 2024, 2025]:
        raise ValueError("Unexpected bridge years")
    results = []
    for notice in notice_rows:
        year = int(notice["settlement_calendar_year"])
        if int(notice["interest_year_label"]) != year - 1:
            raise ValueError("Interest-year label is not calendar settlement year minus one")
        if notice["settlement_date"] != f"{year}-06-30":
            raise ValueError("Settlement date does not align with the current calendar year")
        if not notice["source_url"].startswith("https://www.shzfgjj.cn/"):
            raise ValueError("Missing official source")
        annual_gap = Decimal(bridge[year]["gap_100m"])
        settlement = Decimal(notice["interest_paid_100m"])
        interest_expense = Decimal(bridge[year]["contributor_interest_expense_100m"])
        contributors = Decimal(annual[year]["contributors_10k"])
        accounts = Decimal(notice["credited_accounts_10k"])
        results.append({
            "year": year,
            "gap_100m": str(annual_gap),
            "settled_account_interest_100m": str(settlement),
            "gap_minus_settled_interest_100m": str(annual_gap - settlement),
            "annual_business_interest_expense_100m": str(interest_expense),
            "gap_minus_business_interest_expense_100m": str(annual_gap - interest_expense),
            "interest_credited_accounts_10k": str(accounts),
            "annual_active_contributors_10k": str(contributors),
            "account_to_active_ratio": str(accounts / contributors),
            "warning": "Credited accounts on June 30 versus people with >=1 annual contribution "
                       "are different populations and dates. The difference is NOT a "
                       "verified count of inactive persons.",
            "source_url": notice["source_url"],
        })
    return results


if __name__ == "__main__":
    print(json.dumps(settlement_bridge(), ensure_ascii=False, indent=2))
