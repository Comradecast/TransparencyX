from transparencyx.profile.exposure_table import render_batch_exposure_table, summarize_profile_exposure


def test_summarize_profile_exposure_missing_exposure_zero_row():
    summary = summarize_profile_exposure({"member_name": "Member A"})

    assert summary == {
        "member_name": "Member A",
        "queried_businesses": 0,
        "awards_found": 0,
        "total_award_amount": 0.0,
        "agencies": [],
    }


def test_summarize_profile_exposure_empty_exposure_list_zero_row():
    summary = summarize_profile_exposure({
        "member_name": "",
        "federal_award_exposure": [],
    })

    assert summary["member_name"] == "Unknown"
    assert summary["queried_businesses"] == 0
    assert summary["awards_found"] == 0
    assert summary["total_award_amount"] == 0.0
    assert summary["agencies"] == []


def test_summarize_profile_exposure_aggregates_counts_and_amounts():
    summary = summarize_profile_exposure({
        "member_name": "Member A",
        "federal_award_exposure": [
            {"award_count": 2, "total_award_amount": 100.5, "agencies": []},
            {"award_count": 3, "total_award_amount": 200.0, "agencies": []},
        ],
    })

    assert summary["queried_businesses"] == 2
    assert summary["awards_found"] == 5
    assert summary["total_award_amount"] == 300.5


def test_summarize_profile_exposure_agencies_sorted_deduplicated_and_blank_ignored():
    summary = summarize_profile_exposure({
        "member_name": "Member A",
        "federal_award_exposure": [
            {"award_count": 1, "total_award_amount": 1, "agencies": ["Z Agency", "", None]},
            {"award_count": 1, "total_award_amount": 1, "agencies": ["A Agency", "Z Agency"]},
        ],
    })

    assert summary["agencies"] == ["A Agency", "Z Agency"]


def test_render_batch_exposure_table_preserves_input_order():
    table = render_batch_exposure_table([
        {"member_name": "Member B", "federal_award_exposure": []},
        {"member_name": "Member A", "federal_award_exposure": []},
    ])

    assert table.splitlines() == [
        "member_name | queried_businesses | awards_found | total_award_amount | agencies",
        "Member B | 0 | 0 | $0 | None",
        "Member A | 0 | 0 | $0 | None",
    ]


def test_render_batch_exposure_table_formats_money():
    table = render_batch_exposure_table([
        {
            "member_name": "Member A",
            "federal_award_exposure": [
                {"award_count": 1, "total_award_amount": 1234.5, "agencies": ["Agency A"]},
            ],
        },
    ])

    assert table.splitlines()[1] == "Member A | 1 | 1 | $1,234.5 | Agency A"


def test_render_batch_exposure_table_has_no_accusation_language():
    table = render_batch_exposure_table([
        {"member_name": "Member A", "federal_award_exposure": []},
    ]).lower()

    assert "corruption" not in table
    assert "self-dealing" not in table
    assert "insider trading" not in table
    assert "conflict confirmed" not in table
