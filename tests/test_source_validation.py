"""Adversarial validation: passing the accounting check alone is insufficient."""
import csv
from decimal import Decimal
from pathlib import Path

import pytest
from hpf_research.audit import ROOT, records
from hpf_research.collect_monthly import parse_page
from hpf_research.source_validation import (
    body_text, extract_annual_fields, validate_annual, validate_manifest, validate_monthly,
)


def test_99_annual_fields_from_correct_business_sections():
    assert validate_annual() == 99


def test_768_district_rows_reparsed_against_archived_official_tables():
    assert validate_monthly() == 768


def test_manifest_schema_and_archives():
    registry = validate_manifest()
    assert "ANNUAL-2025" in registry
    assert "MONTH-2025-12" in registry
    assert "SETTLEMENT-2025" in registry
    assert registry["SETTLEMENT-2025"]["original_sha256"] == "unavailable"


def test_primary_amount_mutation_fails_even_when_value_repeats_elsewhere():
    source = (ROOT / "sources/original/annual_2025.html").read_bytes()
    content = body_text(source)
    assert extract_annual_fields(content)["contributions_100m"] == Decimal("2663.65")
    assert "缴存额2663.65亿元" in content
    malicious = content.replace("缴存额2663.65亿元", "缴存额9999.99亿元", 1)
    malicious += " 缴存额2663.65亿元 "
    assert extract_annual_fields(malicious)["contributions_100m"] == Decimal("9999.99")
    assert extract_annual_fields(malicious)["contributions_100m"] != Decimal("2663.65")


def test_changed_unit_rejected():
    content = body_text((ROOT / "sources/original/annual_2025.html").read_bytes())
    malicious = content.replace("缴存额2663.65亿元", "缴存额2663.65万元", 1)
    with pytest.raises(ValueError, match="contributions_100m"):
        extract_annual_fields(malicious)


def test_same_amount_in_wrong_report_section_does_not_pass():
    content = body_text((ROOT / "sources/original/annual_2025.html").read_bytes())
    doctored = content.replace("缴存额2663.65亿元", "缴存额9999.99亿元", 1)
    doctored += " 附录：当年缴存额2663.65亿元 "
    assert extract_annual_fields(doctored)["contributions_100m"] != Decimal("2663.65")


def test_monthly_duplicate_district_row_rejected():
    from hpf_research.collect_monthly import PAGE_IDS
    source = ROOT / f"sources/original/monthly_2025/08_{PAGE_IDS[2025][7]}.html"
    raw = source.read_bytes()
    url = f"https://www.shzfgjj.cn/html/newxxgk/ywsjtj/{PAGE_IDS[2025][7]}.html"
    clean = parse_page(raw, 2025, 8, url)
    assert len(clean) == 16
    mutated = raw.replace("黄浦".encode("gb18030"), "徐汇".encode("gb18030"), 1)
    with pytest.raises(ValueError):
        parse_page(mutated, 2025, 8, url)


def test_monthly_date_mutation_rejected():
    from hpf_research.collect_monthly import PAGE_IDS
    source = ROOT / f"sources/original/monthly_2025/08_{PAGE_IDS[2025][7]}.html"
    raw = source.read_bytes()
    url = f"https://www.shzfgjj.cn/html/newxxgk/ywsjtj/{PAGE_IDS[2025][7]}.html"
    assert parse_page(raw, 2025, 8, url)
    mutated = raw.replace(b"2025-08-31", b"2025-09-30", 1)
    # Date occurs in the actual table; must invalidate at least one row.
    with pytest.raises(ValueError):
        parse_page(mutated, 2025, 8, url)
