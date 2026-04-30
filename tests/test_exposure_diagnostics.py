from transparencyx.exposure.diagnostics import build_exposure_diagnostics, render_exposure_diagnostics


def test_build_exposure_diagnostics_empty_exposures():
    diagnostics = build_exposure_diagnostics([])

    assert diagnostics == {
        "business_interests_queried": 0,
        "awards_found": 0,
        "total_award_amount": 0.0,
        "queries_with_results": 0,
        "queries_without_results": 0,
        "agencies_found": [],
        "no_result_queries": [],
        "query_length": {
            "shortest": 0,
            "longest": 0,
            "average": 0.0,
        },
        "diagnostic_notes": [
            "No awards were found for the queried business interests.",
            "Exposure results depend on exact recipient-name search behavior.",
        ],
    }


def test_build_exposure_diagnostics_all_zero_results():
    diagnostics = build_exposure_diagnostics([
        {"query_recipient_name": "REOF XXV, LLC", "award_count": 0, "total_award_amount": 0.0, "agencies": []},
        {"query_recipient_name": "Example Holdings LLC", "award_count": 0, "total_award_amount": 0.0, "agencies": []},
    ])

    assert diagnostics["business_interests_queried"] == 2
    assert diagnostics["awards_found"] == 0
    assert diagnostics["queries_with_results"] == 0
    assert diagnostics["queries_without_results"] == 2
    assert diagnostics["no_result_queries"] == ["REOF XXV, LLC", "Example Holdings LLC"]
    assert "All queried business interests returned zero awards." in diagnostics["diagnostic_notes"]


def test_build_exposure_diagnostics_mixed_zero_and_nonzero_results():
    diagnostics = build_exposure_diagnostics([
        {"query_recipient_name": "No Result LLC", "award_count": 0, "total_award_amount": 0.0, "agencies": []},
        {"query_recipient_name": "Result LLC", "award_count": 2, "total_award_amount": 50.0, "agencies": ["B Agency"]},
    ])

    assert diagnostics["awards_found"] == 2
    assert diagnostics["total_award_amount"] == 50.0
    assert diagnostics["queries_with_results"] == 1
    assert diagnostics["queries_without_results"] == 1
    assert diagnostics["no_result_queries"] == ["No Result LLC"]
    assert "Some queried business interests returned federal award results." in diagnostics["diagnostic_notes"]


def test_build_exposure_diagnostics_missing_fields_fail_closed():
    diagnostics = build_exposure_diagnostics([{}])

    assert diagnostics["business_interests_queried"] == 1
    assert diagnostics["awards_found"] == 0
    assert diagnostics["total_award_amount"] == 0.0
    assert diagnostics["queries_without_results"] == 1
    assert diagnostics["no_result_queries"] == []


def test_build_exposure_diagnostics_agency_sorting_and_deduplication():
    diagnostics = build_exposure_diagnostics([
        {"query_recipient_name": "A", "award_count": 1, "total_award_amount": 1.0, "agencies": ["Z Agency", "", None]},
        {"query_recipient_name": "B", "award_count": 1, "total_award_amount": 1.0, "agencies": ["A Agency", "Z Agency"]},
    ])

    assert diagnostics["agencies_found"] == ["A Agency", "Z Agency"]


def test_build_exposure_diagnostics_query_length_stats():
    diagnostics = build_exposure_diagnostics([
        {"query_recipient_name": "Short", "award_count": 0},
        {"query_recipient_name": "Longer Query", "award_count": 0},
    ])

    assert diagnostics["query_length"] == {
        "shortest": 5,
        "longest": 12,
        "average": 8.5,
    }


def test_render_exposure_diagnostics_formatting():
    rendered = render_exposure_diagnostics([
        {"query_recipient_name": "REOF XXV, LLC", "award_count": 0, "total_award_amount": 0.0, "agencies": []},
    ])

    assert "Federal Award Exposure Diagnostics:" in rendered
    assert "- business interests queried: 1" in rendered
    assert "- awards found: 0" in rendered
    assert "- total award amount: $0" in rendered
    assert "- agencies found: None" in rendered
    assert "- diagnostic notes:" in rendered
    assert "- sample no-result queries:" in rendered
    assert "  - REOF XXV, LLC" in rendered


def test_render_exposure_diagnostics_omits_no_result_section_when_none():
    rendered = render_exposure_diagnostics([
        {"query_recipient_name": "Result LLC", "award_count": 1, "total_award_amount": 1.0, "agencies": []},
    ])

    assert "- sample no-result queries:" not in rendered


def test_render_exposure_diagnostics_limits_sample_no_result_queries_to_ten():
    rendered = render_exposure_diagnostics([
        {"query_recipient_name": f"Query {index}", "award_count": 0}
        for index in range(12)
    ])

    assert "  - Query 0" in rendered
    assert "  - Query 9" in rendered
    assert "  - Query 10" not in rendered


def test_render_exposure_diagnostics_has_no_forbidden_language():
    rendered = render_exposure_diagnostics([
        {"query_recipient_name": "REOF XXV, LLC", "award_count": 0}
    ]).lower()

    assert "corruption" not in rendered
    assert "self-dealing" not in rendered
    assert "insider trading" not in rendered
    assert "conflict confirmed" not in rendered
    assert "misconduct" not in rendered
    assert "suspicious" not in rendered
