"""Pre-specified April/September housing-withdrawal seasonality audit.

Aggregate withdrawals are NOT identifiable as amounts from annual repayment.
Years 2022-2025 reflect observed data; policy evidence explicitly identifies
April/September annual-repayment batches in 2022 and the 2023 onward rules.
"""
from __future__ import annotations

import csv
import json
from decimal import Decimal, ROUND_HALF_UP

from .audit import ROOT, records
from .collect_monthly import DISTRICTS

YEARS = tuple(range(2022, 2026))
BATCH_MONTHS = (4, 9)
SCALE = Decimal("0.000001")


def fmt(value: Decimal) -> str:
    return str(value.quantize(SCALE, rounding=ROUND_HALF_UP))


def delta(ytd: list[Decimal]) -> list[Decimal]:
    if len(ytd) != 12:
        raise ValueError("Expected 12 cumulative observations")
    values = [n - (ytd[i - 1] if i else Decimal(0)) for i, n in enumerate(ytd)]
    if min(values) < 0:
        raise ValueError("Negative monthly flow: declining cumulative series")
    return values


def top_batch_months(flows: list[Decimal]) -> bool:
    if len(flows) != 12:
        raise ValueError("Expected 12 monthly flows")
    # Strict threshold: ties do not prove the two batch months are top two.
    return min(flows[3], flows[8]) > max(
        n for i, n in enumerate(flows, 1) if i not in BATCH_MONTHS
    )


def analyze() -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    district_results, yearly_results = [], []
    for year in YEARS:
        rows = records(f"data/processed/district_monthly_{year}_coverage.csv")
        if len(rows) != 192:
            raise ValueError(f"{year}: expected 192 district-month records")
        grouped = {district: {} for district in DISTRICTS}
        for row in rows:
            place, month = row["district"], int(row["month"])
            if place not in grouped or int(row["year"]) != year or not 1 <= month <= 12:
                raise ValueError(f"{year}: unexpected region or month")
            if month in grouped[place]:
                raise ValueError(f"{year}/{place}/{month}: duplicate")
            grouped[place][month] = row

        annual_w = annual_c = batches_w = batches_c = Decimal(0)
        without_huangpu_w = without_huangpu_batch = huangpu_w = Decimal(0)
        total_match = 0
        district_annual = []
        for place in DISTRICTS:
            if set(grouped[place]) != set(range(1, 13)):
                raise ValueError(f"Missing month: {year}/{place}")
            r = [grouped[place][m] for m in range(1, 13)]
            w = delta([Decimal(x["year_to_date_withdrawals_10k_cny"]) / 10000 for x in r])
            c = delta([Decimal(x["year_to_date_collection_10k_cny"]) / 10000 for x in r])
            total_w, total_c = sum(w), sum(c)
            selected_w, selected_c = w[3] + w[8], c[3] + c[8]
            other_avg = sum(n for i, n in enumerate(w, 1) if i not in BATCH_MONTHS) / 10
            if total_w <= 0 or total_c <= 0 or other_avg <= 0:
                raise ValueError(f"Missing denominator: {year}/{place}")
            match = top_batch_months(w)
            total_match += int(match)
            annual_w += total_w
            annual_c += total_c
            batches_w += selected_w
            batches_c += selected_c
            district_annual.append(total_w)
            if place == "黄浦":
                huangpu_w = total_w
            else:
                without_huangpu_w += total_w
                without_huangpu_batch += selected_w
            district_results.append({
                "year": str(year), "district": place,
                "annual_withdrawals_100m": fmt(total_w),
                "april_withdrawals_100m": fmt(w[3]),
                "september_withdrawals_100m": fmt(w[8]),
                "april_over_other_ten_month_mean": fmt(w[3] / other_avg),
                "september_over_other_ten_month_mean": fmt(w[8] / other_avg),
                "april_and_september_are_strict_top_two": "yes" if match else "no",
                "source_panel": f"data/processed/district_monthly_{year}_coverage.csv",
            })
        yearly_results.append({
            "year": str(year),
            "districts_with_strict_april_september_top_two": str(total_match),
            "district_count": str(len(DISTRICTS)),
            "annual_withdrawals_100m": fmt(annual_w),
            "april_september_withdrawals_100m": fmt(batches_w),
            "batch_withdrawals_share_pct": fmt(100 * batches_w / annual_w),
            "batch_collection_share_pct": fmt(100 * batches_c / annual_c),
            "batch_withdrawals_share_without_huangpu_pct":
                fmt(100 * without_huangpu_batch / without_huangpu_w),
            "huangpu_annual_withdrawals_share_pct": fmt(100 * huangpu_w / annual_w),
            "district_withdrawals_hhi": fmt(
                sum((a / annual_w) ** 2 for a in district_annual)
            ),
            "identification_status": "descriptive_consistent_with_annual_repayment_rules",
        })
    return district_results, yearly_results


def write_outputs() -> None:
    outputs = analyze()
    paths = (
        "data/processed/repayment_seasonality_district_2022_2025.csv",
        "data/processed/repayment_seasonality_yearly_2022_2025.csv",
    )
    for rows, path in zip(outputs, paths):
        with (ROOT / path).open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    if args.write:
        write_outputs()
    print(json.dumps(analyze()[1], ensure_ascii=False, indent=2))
