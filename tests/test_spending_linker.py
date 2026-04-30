from pathlib import Path

from transparencyx.spending.linker import (
    build_exposure_link,
    clean_recipient_query_name,
    extract_business_interest_assets,
    link_business_interests_to_award_exposure,
)


def test_extract_business_interest_assets_selects_only_business_interest_rows():
    asset_names = extract_business_interest_assets([
        {"asset_name": "Business A [OL] SP", "asset_category": "business_interest"},
        {"asset_name": "Apple Inc. [ST] SP", "asset_category": "stock"},
        {"asset_name": "Business B [AB] SP", "asset_category": "business_interest"},
    ])

    assert asset_names == ["Business A [OL] SP", "Business B [AB] SP"]


def test_extract_business_interest_assets_ignores_non_business_categories():
    asset_names = extract_business_interest_assets([
        {"asset_name": "Account [BA] SP", "asset_category": "bank_account"},
        {"asset_name": "Property [RP] SP", "asset_category": "real_estate"},
        {"asset_name": "Fund [MF] SP", "asset_category": "mutual_fund"},
    ])

    assert asset_names == []


def test_extract_business_interest_assets_skips_blank_or_missing_asset_name():
    asset_names = extract_business_interest_assets([
        {"asset_name": "", "asset_category": "business_interest"},
        {"asset_category": "business_interest"},
        {"asset_name": None, "asset_category": "business_interest"},
        {"asset_name": "Business A [OL] SP", "asset_category": "business_interest"},
    ])

    assert asset_names == ["Business A [OL] SP"]


def test_extract_business_interest_assets_preserves_names_exactly():
    name = "REOF XXV, LLC [AB] SP"

    asset_names = extract_business_interest_assets([
        {"asset_name": name, "asset_category": "business_interest"},
    ])

    assert asset_names == [name]


def test_link_business_interests_to_award_exposure_preserves_order():
    links = link_business_interests_to_award_exposure([
        {"asset_name": "Business Z [OL] SP", "asset_category": "business_interest"},
        {"asset_name": "Business A [AB] SP", "asset_category": "business_interest"},
    ])

    assert [link["query_recipient_name"] for link in links] == [
        "Business Z",
        "Business A",
    ]


def test_build_exposure_link_includes_federal_award_exposure_signal():
    link = build_exposure_link("REOF XXV, LLC [AB] SP")

    assert link["signal"] == "federal_award_exposure"
    assert link["match_type"] == "exact_query"


def test_build_exposure_link_includes_possible_usaspending_payload():
    link = build_exposure_link("REOF XXV, LLC [AB] SP")

    assert link["payload"]["filters"]["recipient_search_text"] == ["REOF XXV, LLC"]
    assert link["payload"]["filters"]["award_type_codes"] == ["A", "B", "C", "D"]


def test_clean_recipient_query_name_strips_disclosure_code_and_owner_suffix():
    assert clean_recipient_query_name("REOF XXV, LLC [AB] SP") == "REOF XXV, LLC"
    assert clean_recipient_query_name("City Car Services LLC [OL] SP") == "City Car Services LLC"
    assert clean_recipient_query_name("Bank of America - Checking Account [BA] JT") == "Bank of America - Checking Account"


def test_clean_recipient_query_name_strips_transaction_status_tokens():
    assert clean_recipient_query_name("Example LLC [AB] S (partial)") == "Example LLC"
    assert clean_recipient_query_name("Example LLC [AB] P") == "Example LLC"
    assert clean_recipient_query_name("Example LLC [AB] S") == "Example LLC"


def test_clean_recipient_query_name_blank_or_metadata_only_returns_empty():
    assert clean_recipient_query_name("") == ""
    assert clean_recipient_query_name("[AB] SP") == ""
    assert clean_recipient_query_name("  [OL]   JT,  ") == ""


def test_build_exposure_link_preserves_disclosed_asset_name():
    link = build_exposure_link("REOF XXV, LLC [AB] SP")

    assert link["disclosed_asset_name"] == "REOF XXV, LLC [AB] SP"
    assert link["query_recipient_name"] == "REOF XXV, LLC"


def test_link_business_interests_to_award_exposure_skips_empty_cleaned_names():
    links = link_business_interests_to_award_exposure([
        {"asset_name": "[AB] SP", "asset_category": "business_interest"},
        {"asset_name": "Business A [AB] SP", "asset_category": "business_interest"},
    ])

    assert len(links) == 1
    assert links[0]["query_recipient_name"] == "Business A"


def test_build_exposure_link_produces_no_fuzzy_variants():
    link = build_exposure_link("REOF XXV, LLC [AB] SP")

    assert "variants" not in link
    assert link["payload"]["filters"]["recipient_search_text"] == ["REOF XXV, LLC"]


def test_spending_linker_has_no_live_network_calls():
    source = Path("src/transparencyx/spending/linker.py").read_text()

    assert "requests" not in source
    assert "urllib" not in source
    assert "http.client" not in source
