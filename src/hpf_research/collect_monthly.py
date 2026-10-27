"""Fetch and transcribe the 2025 official district tables (stdlib only).

Run with ``python -m hpf_research.collect_monthly``. Never replaces a complete
local snapshot with a failed or incomplete response.
"""
from __future__ import annotations

import argparse
import calendar
import csv
import hashlib
from html.parser import HTMLParser
from urllib.request import Request, urlopen

from .audit import ROOT

BASE = "https://www.shzfgjj.cn/html/newxxgk/ywsjtj/"
PAGE_IDS = {
    2022: (208992, 208996, 209348, 209350, 209550, 210080,
           210399, 210807, 211119, 211592, 212228, 212590),
    2023: (213018, 213599, 214083, 214505, 215083, 215669,
           216213, 216847, 217213, 217797, 218475, 219065),
    2024: (219479, 220043, 220515, 221201, 221946, 222741,
           223387, 224137, 224695, 225290, 225902, 226404),
    2025: (226796, 227332, 227786, 227945, 227993, 228041,
           228069, 228129, 228184, 228222, 228246, 228264),
}
DISTRICTS = ("黄浦", "徐汇", "长宁", "静安", "普陀", "虹口", "杨浦", "闵行",
             "宝山", "嘉定", "浦东", "奉贤", "松江", "金山", "青浦", "崇明")
FIELDS = ("year", "month", "district", "units_10k", "contributors_10k",
          "year_to_date_collection_10k_cny", "year_to_date_withdrawals_10k_cny",
          "as_of", "source_status", "source_url")


class Tables(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tables: list[list[list[str]]] = []
        self.table: list[list[str]] | None = None
        self.row: list[str] | None = None
        self.cell: list[str] | None = None

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self.table = []
        elif tag == "tr" and self.table is not None:
            self.row = []
        elif tag in ("td", "th") and self.row is not None:
            self.cell = []

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.cell is not None and self.row is not None:
            self.row.append("".join(self.cell).strip())
            self.cell = None
        elif tag == "tr" and self.row is not None and self.table is not None:
            self.table.append(self.row)
            self.row = None
        elif tag == "table" and self.table is not None:
            self.tables.append(self.table)
            self.table = None


def parse_page(raw: bytes, year: int, month: int, url: str) -> list[dict[str, str]]:
    parser = Tables()
    parser.feed(raw.decode("gb18030"))
    expected_date = f"{year}-{month:02d}-{calendar.monthrange(year, month)[1]:02d}"
    matches = [[r for r in t if r] for t in parser.tables]
    matches = [t for t in matches if len(t) == 17 and
               [r[0].strip() for r in t[1:]] == list(DISTRICTS)]
    if len(matches) != 1:
        raise ValueError(f"{month}: expected exactly one 16-district table")
    result = []
    for cells in matches[0][1:]:
        if len(cells) != 6 or cells[5] != expected_date:
            raise ValueError(f"{month}: invalid columns or as-of date: {cells}")
        from decimal import Decimal
        for item in cells[1:5]:
            if Decimal(item.replace(",", "")) < 0:
                raise ValueError(f"{month}: negative amount")
        result.append(dict(zip(FIELDS, (str(year), str(month), cells[0], cells[1], cells[2],
                                        cells[3].replace(",", ""), cells[4].replace(",", ""),
                                        cells[5], "verified_original_html", url))))
    return result


def main() -> None:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--year", type=int, choices=sorted(PAGE_IDS), default=2025)
    year = cli.parse_args().year
    rows = []
    pages = []
    for month, page_id in enumerate(PAGE_IDS[year], 1):
        url = f"{BASE}{page_id}.html"
        raw = urlopen(Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=25).read()
        parsed = parse_page(raw, year, month, url)
        rows.extend(parsed)
        pages.append((month, page_id, raw, url))
    if len(rows) != 192:
        raise ValueError(f"Incomplete {year} panel")

    snapshot_dir = ROOT / f"sources/original/monthly_{year}"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    # Never silently overwrite previously archived evidence. Official webpages can change:
    # preserving changed snapshots and manual review takes precedence over convenience.
    for month, page_id, raw, url in pages:
        archive = snapshot_dir / f"{month:02d}_{page_id}.html"
        if archive.is_file() and archive.read_bytes() != raw:
            raise ValueError(f"Publisher source changed: {url}. Preserve the existing "
                             f"snapshot in a dated revision and reconcile before importing.")
    existing_csv = ROOT / f"data/processed/district_monthly_{year}_coverage.csv"
    if existing_csv.exists():
        with existing_csv.open(encoding="utf-8-sig", newline="") as stream:
            existing_rows = list(csv.DictReader(stream))
        if existing_rows != rows:
            raise ValueError(f"{year} collected records differ from committed CSV; "
                             "perform an explicit source-version reconciliation")
    provenance = []
    for month, page_id, raw, url in pages:
        name = f"{month:02d}_{page_id}.html"
        (snapshot_dir / name).write_bytes(raw)
        provenance.append((month, url, f"sources/original/monthly_{year}/{name}",
                           hashlib.sha256(raw).hexdigest(), len(raw)))
    with (ROOT / f"data/processed/district_monthly_{year}_coverage.csv").open(
            "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    with (snapshot_dir / "provenance.csv").open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(("month", "source_url", "snapshot_path", "sha256", "bytes"))
        writer.writerows(provenance)
    print(f"Verified {len(rows)} district-month rows for {year} from {len(pages)} official HTML pages")


if __name__ == "__main__":
    main()
