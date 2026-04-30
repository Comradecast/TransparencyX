from copy import deepcopy

from transparencyx.exposure.candidates import (
    build_recipient_candidate_audit,
    build_recipient_candidate_query,
    render_recipient_candidate_audit,
)


def test_build_recipient_candidate_query_removes_trailing_suffix_examples():
    assert build_recipient_candidate_query("REOF XXV, LLC") == "REOF XXV"
    assert build_recipient_candidate_query("AllianceBernstein Holding L.P.") == "AllianceBernstein Holding"
    assert build_recipient_candidate_query("Forty-Five Belden Corporation") == "Forty-Five Belden"
    assert build_recipient_candidate_query("City Car Services LLC") == "City Car Services"
    assert build_recipient_candidate_query("Auberge du Soleil") == "Auberge du Soleil"


def test_build_recipient_candidate_query_blank_input_fail_closed():
    assert build_recipient_candidate_query("") == ""
    assert build_recipient_candidate_query("   ") == ""
    assert build_recipient_candidate_query(None) == ""


def test_build_recipient_candidate_query_does_not_remove_interior_words():
    assert build_recipient_candidate_query("LLC Holdings Company") == "LLC Holdings"
    assert build_recipient_candidate_query("Company Services LLC") == "Company Services"


def test_build_recipient_candidate_audit_marks_rows_review_only(monkeypatch):
    def fake_fetch(candidate_query, limit):
        return [
            {
                "recipient_name": "REOF XXV HOLDINGS LLC",
                "recipient_id": "R1",
                "award_count": "4",
                "total_award_amount": "120000",
            }
        ]

    monkeypatch.setattr("transparencyx.exposure.candidates.fetch_recipient_candidates", fake_fetch)

    candidates = build_recipient_candidate_audit([
        {"query_recipient_name": "REOF XXV, LLC", "award_count": 0, "total_award_amount": 0.0},
    ])

    assert candidates == [
        {
            "original_query": "REOF XXV, LLC",
            "candidate_query": "REOF XXV",
            "recipient_name": "REOF XXV HOLDINGS LLC",
            "recipient_id": "R1",
            "award_count": 4,
            "total_award_amount": 120000.0,
            "match_status": "candidate_review_only",
            "exposure_counted": False,
        }
    ]


def test_build_recipient_candidate_audit_preserves_order_and_limit(monkeypatch):
    calls = []

    def fake_fetch(candidate_query, limit):
        calls.append((candidate_query, limit))
        return [
            {"recipient_name": f"{candidate_query} Candidate A"},
            {"recipient_name": f"{candidate_query} Candidate B"},
        ]

    monkeypatch.setattr("transparencyx.exposure.candidates.fetch_recipient_candidates", fake_fetch)

    candidates = build_recipient_candidate_audit([
        {"query_recipient_name": "Bravo LLC"},
        {"query_recipient_name": "Alpha Inc."},
    ], max_candidates_per_query=1)

    assert calls == [("Bravo", 1), ("Alpha", 1)]
    assert [candidate["recipient_name"] for candidate in candidates] == [
        "Bravo Candidate A",
        "Alpha Candidate A",
    ]


def test_build_recipient_candidate_audit_skips_blank_candidate_queries(monkeypatch):
    def fake_fetch(candidate_query, limit):
        raise AssertionError("recipient search should not be called")

    monkeypatch.setattr("transparencyx.exposure.candidates.fetch_recipient_candidates", fake_fetch)

    candidates = build_recipient_candidate_audit([
        {"query_recipient_name": "LLC"},
        {},
    ])

    assert candidates == []


def test_build_recipient_candidate_audit_fails_closed_on_missing_fields(monkeypatch):
    monkeypatch.setattr(
        "transparencyx.exposure.candidates.fetch_recipient_candidates",
        lambda candidate_query, limit: [{}],
    )

    candidates = build_recipient_candidate_audit([
        {"query_recipient_name": "Example LLC"},
    ])

    assert candidates[0]["recipient_name"] == ""
    assert candidates[0]["recipient_id"] is None
    assert candidates[0]["award_count"] is None
    assert candidates[0]["total_award_amount"] is None
    assert candidates[0]["exposure_counted"] is False


def test_build_recipient_candidate_audit_does_not_modify_exact_exposure_totals(monkeypatch):
    exposures = [
        {"query_recipient_name": "REOF XXV, LLC", "award_count": 2, "total_award_amount": 50.0},
    ]
    original = deepcopy(exposures)
    monkeypatch.setattr(
        "transparencyx.exposure.candidates.fetch_recipient_candidates",
        lambda candidate_query, limit: [{"recipient_name": "REOF XXV HOLDINGS LLC", "award_count": 10}],
    )

    build_recipient_candidate_audit(exposures)

    assert exposures == original


def test_render_recipient_candidate_audit_no_candidates():
    rendered = render_recipient_candidate_audit([])

    assert rendered.splitlines() == [
        "Recipient Candidate Audit:",
        "- candidate rows: 0",
        "- exposure counted: No",
        "- exact exposure results unchanged: Yes",
        "- status: No recipient candidates found",
    ]


def test_render_recipient_candidate_audit_table_formatting():
    rendered = render_recipient_candidate_audit([
        {
            "original_query": "REOF XXV, LLC",
            "candidate_query": "REOF XXV",
            "recipient_name": "REOF XXV HOLDINGS LLC",
            "award_count": 4,
            "total_award_amount": 120000.0,
            "match_status": "candidate_review_only",
            "exposure_counted": False,
        }
    ])

    assert rendered.splitlines() == [
        "Recipient Candidate Audit:",
        "- candidate rows: 1",
        "- exposure counted: No",
        "- exact exposure results unchanged: Yes",
        "",
        "original_query | candidate_query | recipient_name | award_count | total_award_amount | status",
        "REOF XXV, LLC | REOF XXV | REOF XXV HOLDINGS LLC | 4 | $120,000 | candidate_review_only",
    ]


def test_render_recipient_candidate_audit_has_no_forbidden_language():
    rendered = render_recipient_candidate_audit([
        {
            "original_query": "REOF XXV, LLC",
            "candidate_query": "REOF XXV",
            "recipient_name": "REOF XXV HOLDINGS LLC",
            "award_count": 4,
            "total_award_amount": 120000.0,
            "match_status": "candidate_review_only",
        }
    ]).lower()

    assert "corruption" not in rendered
    assert "self-dealing" not in rendered
    assert "insider trading" not in rendered
    assert "conflict confirmed" not in rendered
    assert "misconduct" not in rendered
    assert "suspicious" not in rendered
