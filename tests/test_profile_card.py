from pathlib import Path

from transparencyx.profile.card import render_federal_award_exposure, render_member_profile_card


def make_shape_export():
    return {
        "politician_id": 1,
        "summary": {
            "politician_id": 1,
            "summary_label": "Very high disclosed wealth, no trading activity",
            "asset_count": 2,
            "asset_value_min": 1001,
            "asset_value_max": 15000,
            "asset_value_midpoint": 8000.5,
            "net_worth_band": "VERY_HIGH",
            "asset_density": "LOW",
            "asset_category_counts": {
                "stock": 2,
                "real_estate": 0,
                "business_interest": 0,
                "bank_account": 0,
                "mutual_fund": 0,
                "option": 0,
                "other": 0,
                "unknown": 0,
            },
            "income_count": 1,
            "income_min": 1,
            "income_max": 200,
            "income_midpoint": 100.5,
            "income_band": "LOW",
            "income_type_counts": {
                "dividends": 1,
                "interest": 0,
                "rent": 0,
                "partnership_income": 0,
                "partnership_loss": 0,
                "capital_gains": 0,
                "other": 0,
            },
            "trade_count": 0,
            "trade_activity": "NONE",
            "trade_volume_band": "UNKNOWN",
        },
        "trace": {
            "assets": {
                "count_rows": [1, 2],
            },
        },
    }


def make_profile():
    return {
        "member_name": "Disclosure, Real",
        "politician_id": 1,
        "filing_year": 2023,
        "source": "validate-real",
        "disclosure_path": "data/raw/house/2023/10059734.pdf",
        "shape_export": make_shape_export(),
    }


def test_profile_card_includes_member_metadata():
    card = render_member_profile_card(make_profile())

    assert "MEMBER PROFILE" in card
    assert "Name: Disclosure, Real" in card
    assert "Politician ID: 1" in card
    assert "Filing Year: 2023" in card
    assert "Source: validate-real" in card
    assert "Disclosure Path: data/raw/house/2023/10059734.pdf" in card


def test_profile_card_missing_metadata_renders_unknown():
    profile = {"shape_export": make_shape_export()}

    card = render_member_profile_card(profile)

    assert "Name: Unknown" in card
    assert "Politician ID: Unknown" in card
    assert "Filing Year: Unknown" in card
    assert "Source: Unknown" in card
    assert "Disclosure Path: Unknown" in card


def test_profile_card_includes_embedded_financial_shape_card():
    card = render_member_profile_card(make_profile())

    assert "FINANCIAL SHAPE CARD" in card
    assert "summary_label: Very high disclosed wealth, no trading activity" in card
    assert "Asset Mix:" in card
    assert "Income:" in card


def test_profile_card_omits_exposure_section_when_missing():
    card = render_member_profile_card(make_profile())

    assert "Federal Award Exposure:" not in card


def test_profile_card_renders_exposure_section_when_provided():
    profile = make_profile()
    profile["federal_award_exposure"] = [
        {
            "award_count": 2,
            "total_award_amount": 100.0,
            "agencies": ["B Agency", "A Agency"],
        },
    ]

    card = render_member_profile_card(profile)

    assert "Federal Award Exposure:" in card
    assert "- queried business interests: 1" in card
    assert "- awards found: 2" in card
    assert "- total award amount: $100" in card
    assert "- agencies: A Agency, B Agency" in card


def test_render_federal_award_exposure_sums_counts_and_amounts():
    section = render_federal_award_exposure([
        {"award_count": 2, "total_award_amount": 100.5, "agencies": []},
        {"award_count": 3, "total_award_amount": 200.0, "agencies": []},
    ])

    assert "- awards found: 5" in section
    assert "- total award amount: $300.5" in section


def test_render_federal_award_exposure_agencies_sorted_and_deduplicated():
    section = render_federal_award_exposure([
        {"award_count": 1, "total_award_amount": 1.0, "agencies": ["Z Agency", "A Agency"]},
        {"award_count": 1, "total_award_amount": 1.0, "agencies": ["A Agency"]},
    ])

    assert "- agencies: A Agency, Z Agency" in section


def test_render_federal_award_exposure_empty_exposures_safe():
    section = render_federal_award_exposure([])

    assert section == "\n".join([
        "Federal Award Exposure:",
        "- queried business interests: 0",
        "- awards found: 0",
        "- total award amount: $0",
        "- agencies: None",
    ])


def test_profile_card_is_deterministic():
    profile = make_profile()

    assert render_member_profile_card(profile) == render_member_profile_card(profile)


def test_profile_card_module_has_no_database_access():
    source = Path("src/transparencyx/profile/card.py").read_text()

    assert "get_connection" not in source
    assert "sqlite" not in source.lower()
