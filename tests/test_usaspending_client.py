from pathlib import Path

from transparencyx.spending.usaspending import (
    build_award_search_payload,
    normalize_award_result,
    summarize_award_exposure,
)


def test_build_award_search_payload_uses_exact_recipient_name():
    payload = build_award_search_payload("REOF XXV, LLC")

    assert payload["filters"]["recipient_search_text"] == ["REOF XXV, LLC"]


def test_build_award_search_payload_includes_official_contract_filter():
    payload = build_award_search_payload("REOF XXV, LLC")

    assert payload["filters"]["award_type_codes"] == ["A", "B", "C", "D"]
    assert payload["limit"] == 10
    assert payload["sort"] == "Award ID"
    assert payload["order"] == "asc"


def test_normalize_award_result_handles_missing_fields():
    normalized = normalize_award_result({})

    assert normalized == {
        "query_recipient_name": None,
        "recipient_name": None,
        "award_id": None,
        "awarding_agency": None,
        "award_amount": None,
        "award_date": None,
        "award_type": None,
        "signal": "possible_recipient_match",
    }


def test_normalize_award_result_handles_bad_award_amount():
    normalized = normalize_award_result({
        "query_recipient_name": "REOF XXV, LLC",
        "Recipient Name": "REOF XXV LLC",
        "Award Amount": "not-a-number",
    })

    assert normalized["award_amount"] is None


def test_normalize_award_result_maps_official_fields():
    normalized = normalize_award_result({
        "query_recipient_name": "REOF XXV, LLC",
        "Recipient Name": "REOF XXV LLC",
        "Award ID": "ABC123",
        "Awarding Agency": "Department of Test",
        "Award Amount": "12.50",
        "Start Date": "2023-01-02",
        "Contract Award Type": "Definitive Contract",
    })

    assert normalized == {
        "query_recipient_name": "REOF XXV, LLC",
        "recipient_name": "REOF XXV LLC",
        "award_id": "ABC123",
        "awarding_agency": "Department of Test",
        "award_amount": 12.5,
        "award_date": "2023-01-02",
        "award_type": "Definitive Contract",
        "signal": "possible_recipient_match",
    }


def test_summarize_award_exposure_totals_deterministically():
    summary = summarize_award_exposure("REOF XXV, LLC", [
        {"award_amount": 10.0, "awarding_agency": "B Agency", "award_date": "2022-01-01"},
        {"award_amount": None, "awarding_agency": "A Agency", "award_date": "2020-01-01"},
        {"award_amount": 5.5, "awarding_agency": "B Agency", "award_date": "2024-01-01"},
    ])

    assert summary["award_count"] == 3
    assert summary["total_award_amount"] == 15.5


def test_summarize_award_exposure_agency_list_is_sorted():
    summary = summarize_award_exposure("REOF XXV, LLC", [
        {"award_amount": 1.0, "awarding_agency": "Z Agency", "award_date": None},
        {"award_amount": 1.0, "awarding_agency": None, "award_date": None},
        {"award_amount": 1.0, "awarding_agency": "A Agency", "award_date": None},
    ])

    assert summary["agencies"] == ["A Agency", "Z Agency"]


def test_summarize_award_exposure_date_range_works():
    summary = summarize_award_exposure("REOF XXV, LLC", [
        {"award_amount": 1.0, "awarding_agency": "A", "award_date": "2023-01-01"},
        {"award_amount": 1.0, "awarding_agency": "A", "award_date": ""},
        {"award_amount": 1.0, "awarding_agency": "A", "award_date": "2021-01-01"},
    ])

    assert summary == {
        "query_recipient_name": "REOF XXV, LLC",
        "award_count": 3,
        "total_award_amount": 3.0,
        "agencies": ["A"],
        "date_min": "2021-01-01",
        "date_max": "2023-01-01",
        "signal": "federal_award_exposure",
    }


def test_usaspending_module_has_no_live_network_calls():
    source = Path("src/transparencyx/spending/usaspending.py").read_text()

    assert "requests" not in source
    assert "urllib" not in source
    assert "http.client" not in source
