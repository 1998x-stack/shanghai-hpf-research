"""Cross-source triangulation; not an estimate of causal policy effects."""
from __future__ import annotations

from decimal import Decimal
from .audit import records


def evidence_rows():
    rows = records("data/external/observations_2024_2025.csv")
    keys = [(int(r["year"]), r["metric"]) for r in rows]
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate observations; annual statistic not uniquely identified")
    if any(not r["unit"] or not r["source_url"].startswith("https://") for r in rows):
        raise ValueError("Missing unit or original source")
    return {(int(r["year"]), r["metric"]): r for r in rows}


def triangulate() -> dict:
    data = evidence_rows()

    def n(y, k, unit):
        obs = data[(y, k)]
        if obs["unit"] != unit:
            raise ValueError(f"Unexpected units for {y}/{k}: {obs['unit']}")
        return Decimal(obs["value"])

    def yoy(k, unit):
        return 100 * (n(2025, k, unit) / n(2024, k, unit) - 1)

    res_area_yoy = yoy("new_residential_sales_area", "10000_m2")
    stock_area_yoy = yoy("existing_property_transfer_area", "10000_m2")
    new_loan_counts = {
        y: n(y, "hpf_loan_issued_count", "10000_loans")
           * n(y, "hpf_new_home_loan_share", "percent") / 100
        for y in (2024, 2025)
    }
    resale_loan_counts = {
        y: n(y, "hpf_loan_issued_count", "10000_loans")
           * n(y, "hpf_resale_home_loan_share", "percent") / 100
        for y in (2024, 2025)
    }
    total = n(2025, "hpf_center_total_budget", "CNY")
    fiscal = n(2025, "hpf_center_fiscal_appropriation_budget", "CNY")
    other = n(2025, "hpf_center_other_income_budget", "CNY")
    if fiscal + other != total:
        raise ValueError("Institutional budget fails the source-book identity")

    complaints = n(2025, "complaints_received", "cases")
    resolved = n(2025, "complaints_resolved_before_filing", "cases")
    published = n(2025, "published_prefiling_resolution_rate", "percent")
    direct_rate = 100 * resolved / complaints
    if abs(direct_rate - published) <= Decimal("0.5"):
        raise ValueError("Reported rate discrepancy unexpectedly vanished; re-review wording")

    return {
        "market": {
            "new_residential_sales_area_yoy_pct": float(res_area_yoy),
            "existing_property_registered_area_yoy_pct": float(stock_area_yoy),
            "hpf_new_home_loans_2024_10k_est": float(new_loan_counts[2024]),
            "hpf_new_home_loans_2025_10k_est": float(new_loan_counts[2025]),
            "hpf_new_home_loan_count_yoy_est_pct": float(100 * (
                new_loan_counts[2025] / new_loan_counts[2024] - 1)),
            "hpf_resale_loans_2024_10k_est": float(resale_loan_counts[2024]),
            "hpf_resale_loans_2025_10k_est": float(resale_loan_counts[2025]),
            "hpf_resale_loan_count_yoy_est_pct": float(100 * (
                resale_loan_counts[2025] / resale_loan_counts[2024] - 1)),
            "warning": "New-residential developer-sales AREA, existing-property ALL-TYPE registration AREA, "
                       "and HPF LOAN COUNTS refer to different populations and units. "
                       "No conversion to take-up or causal effects is valid.",
        },
        "fiscal_bridge": {
            "center_total_budget_cny": int(total),
            "center_fiscal_appropriation_budget_cny": int(fiscal),
            "center_other_income_budget_cny": int(other),
            "appropriation_share_of_center_planned_budget_pct": float(100 * fiscal / total),
            "center_employer_hpf_budget_cny": int(
                n(2025, "hpf_center_employer_hpf_budget", "CNY")),
            "actual_management_cost_reported_cny": int(
                n(2025, "management_cost_actual_reported", "100m_CNY") * 100_000_000),
            "warning": "The government unit BUDGET and HPF annual-report ACTUAL expenses "
                       "are different ledgers/bases: do not add or infer fiscal subsidies from the comparison.",
        },
        "enforcement": {
            "reported_prefiling_resolution_rate_pct": float(published),
            "simple_2413_div_4441_rate_pct": float(direct_rate),
            "difference_percentage_points": float(published - direct_rate),
            "status": "Denominator or event-cohort definition unresolved; not evidence of misreporting.",
        },
    }
