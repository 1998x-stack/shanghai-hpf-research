"""Strict offline source validation for archived Shanghai HPF annual/monthly reports.

Do not interpret textual proximity or a SHA-256 digest alone as field verification.
Values must come from the intended annual business subsection and unit, or
from the intended row of the official district table. Fail closed.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from decimal import Decimal
from html.parser import HTMLParser
from pathlib import Path

from .audit import ROOT, records
from .collect_monthly import PAGE_IDS, parse_page

FIELD_RULES = {
    "units_10k": ("deposit", r"实缴单位\s*([\d,.]+)\s*万家"),
    "contributors_10k": ("deposit", r"实缴(?:职工|人数)\s*([\d,.]+)\s*万人"),
    "contributions_100m": ("deposit", r"缴存额\s*([\d,.]+)\s*亿元"),
    "fund_balance_100m": ("deposit", r"缴存余额\s*([\d,.]+)\s*亿元"),
    "withdrawals_100m": ("withdrawal", r"提取(?:额)?\s*([\d,.]+)\s*亿元"),
    "loan_count_10k": ("loan", r"发放个人住房贷款\s*([\d,.]+)\s*万笔"),
    "loan_issued_100m": (
        "loan", r"发放个人住房贷款\s*[\d,.]+\s*万笔(?:，\s*金额)?\s*([\d,.]+)\s*亿元",
    ),
    "loan_recovered_100m": ("loan", r"回收个人住房贷款\s*([\d,.]+)\s*亿元"),
    "loan_balance_100m": ("loan", r"贷款余额\s*([\d,.]+)\s*亿元"),
}
SECTION_MARKERS = (
    re.compile(r"（\s*一\s*）\s*缴存\s*[:：]?"),
    re.compile(r"（\s*二\s*）\s*提取\s*[:：]?"),
    re.compile(r"（\s*三\s*）\s*贷款\s*[:：]?"),
)


class BodyText(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.fragments: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self.skip += 1
        elif tag in {"p", "div", "table", "tr", "td", "br", "h2", "h3"}:
            self.fragments.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"}:
            self.skip -= 1
        elif tag in {"p", "div", "table", "tr", "td", "br", "h2", "h3"}:
            self.fragments.append(" ")

    def handle_data(self, data: str) -> None:
        if not self.skip:
            self.fragments.append(data)


def body_text(raw: bytes) -> str:
    parser = BodyText()
    parser.feed(raw.decode("gb18030"))
    return re.sub(r"\s+", " ", "".join(parser.fragments))


def extract_annual_fields(text: str) -> dict[str, Decimal]:
    # The section headings identify the intended population and accounting period.
    # Matching the same amount elsewhere in a chart or cumulative table is not valid.
    heading = text.find("二、业务运行情况")
    if heading < 0:
        raise ValueError("Missing annual-business-report heading")
    business = text[heading:]
    indices = []
    for marker in SECTION_MARKERS:
        found = marker.search(business)
        if not found:
            raise ValueError(f"Missing annual-business subsection {marker.pattern}")
        indices.append(found.start())
    if not indices[0] < indices[1] < indices[2]:
        raise ValueError("Annual subsections are out of order")
    sections = {
        "deposit": business[indices[0]:indices[1]],
        "withdrawal": business[indices[1]:indices[2]],
        "loan": business[indices[2]:],
    }
    result = {}
    for key, (segment, pattern) in FIELD_RULES.items():
        match = re.search(pattern, sections[segment])
        if not match:
            raise ValueError(f"Missing {key} in expected '{segment}' subsection")
        result[key] = Decimal(match.group(1).replace(",", ""))
    return result


def validate_manifest() -> dict[str, dict[str, str]]:
    path = ROOT / "sources/manifest.csv"
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        names = reader.fieldnames or []
        if names != [
            "id", "title", "publisher", "url", "publication_date", "period",
            "retrieved_date", "version_note", "topic", "review_status",
            "snapshot_status", "original_sha256",
        ]:
            raise ValueError(f"Source manifest schema changed: {names}")
        rows = list(reader)
    seen = set()
    archive_count = 0
    for row in rows:
        if None in row or None in row.values() or any(not v for v in row.values()):
            raise ValueError(f"Source manifest missing columns/values: {row.get('id')}")
        if row["id"] in seen:
            raise ValueError(f"Duplicate source ID: {row['id']}")
        seen.add(row["id"])
        if not row["url"].startswith("https://"):
            raise ValueError(f"Missing HTTPS provenance for {row['id']}")
        if row["original_sha256"] == "unavailable":
            if row["snapshot_status"].startswith("sources/original/"):
                raise ValueError(f"Archived source marked unavailable: {row['id']}")
            continue
        snapshot = Path(row["snapshot_status"])
        if not snapshot.as_posix().startswith("sources/original/") or ".." in snapshot.parts:
            raise ValueError(f"Unsafe snapshot path: {row['id']}")
        file = ROOT / snapshot
        if not file.is_file():
            raise ValueError(f"Archived source missing: {row['id']}")
        if hashlib.sha256(file.read_bytes()).hexdigest() != row["original_sha256"]:
            raise ValueError(f"Source hash mismatch: {row['id']}")
        archive_count += 1
    if not rows:
        raise ValueError("Empty provenance registry")
    return {r["id"]: r for r in rows}


def validate_annual() -> int:
    by_id = validate_manifest()
    annual = records("data/raw/annual_2015_2025.csv")
    if len(annual) != 11 or [int(x["year"]) for x in annual] != list(range(2015, 2026)):
        raise ValueError("Missing annual years")
    for row in annual:
        year = int(row["year"])
        entry = by_id[f"ANNUAL-{year}"]
        if row["source_url"] != entry["url"]:
            raise ValueError(f"Annual {year}: URL provenance mismatch")
        fields = extract_annual_fields(body_text((ROOT / entry["snapshot_status"]).read_bytes()))
        for key, original in fields.items():
            expected = Decimal(row[key])
            if original != expected:
                raise ValueError(
                    f"Annual {year}/{key}: archived official subsection={original} "
                    f"versus transcription={expected}",
                )
    return len(annual) * len(FIELD_RULES)


def validate_monthly() -> int:
    entries = validate_manifest()
    validated = 0
    for year, page_ids in PAGE_IDS.items():
        observed = records(f"data/processed/district_monthly_{year}_coverage.csv")
        grouped: dict[int, list[dict[str, str]]] = {}
        for row in observed:
            if int(row["year"]) != year:
                raise ValueError("District year mismatch")
            grouped.setdefault(int(row["month"]), []).append(row)
        if set(grouped) != set(range(1, 13)):
            raise ValueError(f"Missing months in {year}")
        for month, page_id in enumerate(page_ids, 1):
            source_url = f"https://www.shzfgjj.cn/html/newxxgk/ywsjtj/{page_id}.html"
            entry = entries[f"MONTH-{year}-{month:02d}"]
            if entry["url"] != source_url:
                raise ValueError(f"{year}/{month} registry URL mismatch")
            parsed = parse_page((ROOT / entry["snapshot_status"]).read_bytes(), year, month, source_url)
            if len(parsed) != 16:
                raise ValueError(f"{year}/{month}: not 16 districts")
            if parsed != grouped[month]:
                raise ValueError(f"{year}/{month}: saved CSV does not match original HTML")
            validated += 16
    return validated


def main() -> None:
    cli = argparse.ArgumentParser()
    cli.add_argument("--check", choices=("all", "manifest", "annual", "monthly"), default="all")
    args = cli.parse_args()
    results: dict[str, int] = {}
    if args.check in ("all", "manifest"):
        results["manifest_entries"] = len(validate_manifest())
    if args.check in ("all", "annual"):
        results["annual_fields"] = validate_annual()
    if args.check in ("all", "monthly"):
        results["monthly_district_cells"] = validate_monthly()
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
