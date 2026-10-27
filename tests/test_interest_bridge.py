from decimal import Decimal

from hpf_research.interest_bridge import settlement_bridge


def test_interest_settlement_years_are_aligned_to_june_calendar_year():
    rows = settlement_bridge()
    assert [r["year"] for r in rows] == [2022, 2023, 2024, 2025]
    assert [Decimal(r["settled_account_interest_100m"]) for r in rows] == [
        Decimal("90.98"), Decimal("103.00"), Decimal("115.92"), Decimal("129.27"),
    ]


def test_public_settlement_is_distinct_from_calendar_expense():
    for r in settlement_bridge():
        assert Decimal(r["settled_account_interest_100m"]) != Decimal(
            r["annual_business_interest_expense_100m"])
        gap = Decimal(r["gap_100m"])
        assert (gap - Decimal(r["settled_account_interest_100m"])
                == Decimal(r["gap_minus_settled_interest_100m"]))


def test_no_improper_dormant_person_count_is_inferred():
    for r in settlement_bridge():
        assert Decimal(r["account_to_active_ratio"]) > 1
        assert "NOT a" in r["warning"]


def test_residual_is_reported_not_forced_to_zero():
    assert all(Decimal(r["gap_minus_settled_interest_100m"]) != 0
               for r in settlement_bridge())


def test_settlement_manifest_is_schema_complete():
    from hpf_research.audit import records
    rows = records("sources/manifest.csv")
    selected = [r for r in rows if r["id"].startswith("SETTLEMENT-")]
    assert len(selected) == 4
    for row in selected:
        assert None not in row
        assert all(row[k] for k in ("publication_date", "period", "retrieved_date",
                                    "version_note", "topic", "review_status",
                                    "snapshot_status", "original_sha256"))
