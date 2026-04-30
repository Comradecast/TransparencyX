from copy import deepcopy

from transparencyx.exposure.candidates import (
    build_recipient_candidate_audit,
    build_recipient_candidate_query,
    build_candidate_signals,
    candidate_name_tokens,
    normalize_candidate_name,
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


def test_normalize_candidate_name_lowercases_and_removes_punctuation():
    assert normalize_candidate_name("REOF XXV, LLC") == "reof xxv llc"
    assert normalize_candidate_name("  AllianceBernstein Holding L.P.  ") == "alliancebernstein holding l p"


def test_normalize_candidate_name_blank_input_fail_closed():
    assert normalize_candidate_name("") == ""
    assert normalize_candidate_name("   ") == ""
    assert normalize_candidate_name(None) == ""


def test_candidate_name_tokens_preserve_order():
    assert candidate_name_tokens("REOF XXV, LLC") == ["reof", "xxv", "llc"]


def test_candidate_name_tokens_blank_input():
    assert candidate_name_tokens("") == []


def test_build_candidate_signals_substring_and_exact_match():
    signals = build_candidate_signals("REOF XXV, LLC", "REOF XXV", "REOF XXV")

    assert signals["normalized_original"] == "reof xxv llc"
    assert signals["normalized_candidate_query"] == "reof xxv"
    assert signals["normalized_recipient"] == "reof xxv"
    assert signals["substring_match"] is True
    assert signals["normalized_name_match"] is True


def test_build_candidate_signals_token_overlap_and_ratio():
    signals = build_candidate_signals("REOF XXV, LLC", "REOF XXV", "REOF Holdings LLC")

    assert signals["token_overlap_count"] == 1
    assert signals["token_overlap_total"] == 2
    assert signals["token_overlap_ratio"] == 0.5
    assert signals["shared_tokens"] == ["reof"]


def test_build_candidate_signals_shared_tokens_sorted():
    signals = build_candidate_signals("Query", "Zulu Alpha", "Alpha Zulu Holdings")

    assert signals["shared_tokens"] == ["alpha", "zulu"]


def test_build_candidate_signals_blank_input_behavior():
    signals = build_candidate_signals("", "", "")

    assert signals["normalized_original"] == ""
    assert signals["normalized_candidate_query"] == ""
    assert signals["normalized_recipient"] == ""
    assert signals["substring_match"] is False
    assert signals["normalized_name_match"] is False
    assert signals["token_overlap_count"] == 0
    assert signals["token_overlap_total"] == 0
    assert signals["token_overlap_ratio"] == 0.0
    assert signals["shared_tokens"] == []


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
            "candidate_signals": {
                "normalized_original": "reof xxv llc",
                "normalized_candidate_query": "reof xxv",
                "normalized_recipient": "reof xxv holdings llc",
                "substring_match": True,
                "normalized_name_match": False,
                "token_overlap_count": 2,
                "token_overlap_total": 2,
                "token_overlap_ratio": 1.0,
                "shared_tokens": ["reof", "xxv"],
            },
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
    assert candidates[0]["candidate_signals"]["token_overlap_total"] == 1


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
            "candidate_signals": {
                "substring_match": True,
                "token_overlap_count": 2,
                "token_overlap_total": 2,
            },
        }
    ])

    assert rendered.splitlines() == [
        "Recipient Candidate Audit:",
        "- candidate rows: 1",
        "- exposure counted: No",
        "- exact exposure results unchanged: Yes",
        "",
        "original_query | candidate_query | recipient_name | award_count | total_award_amount | status | substring_match | token_overlap",
        "REOF XXV, LLC | REOF XXV | REOF XXV HOLDINGS LLC | 4 | $120,000 | candidate_review_only | Yes | 2/2",
    ]


def test_render_recipient_candidate_audit_defaults_missing_signals():
    rendered = render_recipient_candidate_audit([
        {
            "original_query": "REOF XXV, LLC",
            "candidate_query": "REOF XXV",
            "recipient_name": "REOF XXV HOLDINGS LLC",
            "award_count": 4,
            "total_award_amount": 120000.0,
            "match_status": "candidate_review_only",
        }
    ])

    assert rendered.splitlines()[-1].endswith("candidate_review_only | No | 0/0")


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
