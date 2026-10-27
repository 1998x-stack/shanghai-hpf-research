"""Check each core annual transcription against labelled official HTML text.

This is a source-location audit, not an independent external accounting audit.
Each output row contains the matched local context for human inspection.
"""
from __future__ import annotations

import csv
import re
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIELDS = {
    "contributors_10k": ("实缴职工", "实缴人数"),
    "contributions_100m": ("缴存额",),
    "withdrawals_100m": ("提取",),
    "fund_balance_100m": ("缴存余额",),
    "loan_issued_100m": ("发放个人住房贷款",),
    "loan_recovered_100m": ("回收个人住房贷款",),
    "loan_balance_100m": ("贷款余额",),
}


class Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def main() -> None:
    with (ROOT / "data/raw/annual_2015_2025.csv").open(encoding="utf-8", newline="") as f:
        annual = list(csv.DictReader(f))
    output = []
    for row in annual:
        year = row["year"]
        parser = Text()
        parser.feed((ROOT / f"sources/original/annual_{year}.html").read_bytes().decode("gb18030"))
        compact = re.sub(r"[\s，,]", "", "".join(parser.parts))
        for field, labels in FIELDS.items():
            value = row[field].rstrip("0").rstrip(".")
            hit = None
            trailing_zeros = "0*" if "." in value else ""
            for match in re.finditer(rf"(?<![\d.]){re.escape(value)}{trailing_zeros}(?!\d)", compact):
                context = compact[max(0, match.start() - 55):match.end() + 20]
                if any(label in compact[max(0, match.start() - 55):match.start()] for label in labels):
                    hit = context
                    break
            output.append({"year": year, "field": field, "transcribed_value": row[field],
                           "label_match": "yes" if hit else "no", "source_context": hit or "",
                           "source_url": row["source_url"]})
    path = ROOT / "data/processed/annual_source_audit.csv"
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=output[0])
        writer.writeheader()
        writer.writerows(output)
    failures = [r for r in output if r["label_match"] != "yes"]
    print(f"{len(output)-len(failures)}/{len(output)} annual core values matched near a label")
    if failures:
        raise SystemExit(f"Unmatched source values: {[(r['year'], r['field']) for r in failures]}")


if __name__ == "__main__":
    main()
