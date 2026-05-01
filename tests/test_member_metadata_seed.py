import csv
import sys
from pathlib import Path

import pytest

from transparencyx.dossier.metadata import load_member_metadata
from transparencyx.dossier.metadata_seed import (
    build_metadata_source_quality_report,
    build_metadata_source_quality_report_by_state,
    classify_metadata_source,
    render_metadata_source_quality_report,
    render_member_metadata_seed_validation,
    summarize_committee_assignment_coverage_by_state,
    summarize_member_metadata_by_state,
    summarize_member_metadata_seed,
    validate_member_metadata_seed,
)


SEED_PATH = Path("data/seed/member_metadata_seed.csv")
PLAN_PATH = Path("docs/member_metadata_expansion_plan.md")


def _seed_rows():
    with SEED_PATH.open(newline="", encoding="utf-8") as csv_file:
        return list(csv.DictReader(csv_file))


def test_seed_file_exists():
    assert SEED_PATH.exists()


def test_plan_file_exists():
    assert PLAN_PATH.exists()


def test_plan_contains_key_sections():
    plan = PLAN_PATH.read_text(encoding="utf-8")

    assert "## Section 1 - Scope" in plan
    assert "## Section 2 - Required Fields (Authoritative)" in plan
    assert "## Section 3 - Approved Data Sources" in plan
    assert "## Section 5 - Update Workflow" in plan
    assert "## Section 7 - Expansion Targets" in plan
    assert "Full coverage of current U.S. House (435) and Senate (100)" in plan
    assert "No Wikipedia as primary source" in plan


def test_classify_metadata_source_list_urls():
    assert classify_metadata_source("https://clerk.house.gov/Members") == "list"
    assert classify_metadata_source("https://clerk.house.gov/Members/ViewMemberList") == "list"
    assert classify_metadata_source("https://www.senate.gov/senators/") == "list"
    assert classify_metadata_source("https://www.senate.gov/states/NC/intro.htm") == "list"


def test_classify_metadata_source_profile_like_urls():
    assert classify_metadata_source("https://clerk.house.gov/Members/A000370") == "profile"
    assert classify_metadata_source("https://www.senate.gov/senators/member-name.htm") == "profile"
    assert classify_metadata_source("https://www.tillis.senate.gov/") == "profile"


def test_classify_metadata_source_unknown():
    assert classify_metadata_source(None) == "unknown"
    assert classify_metadata_source("") == "unknown"
    assert classify_metadata_source("https://example.test/member") == "unknown"


def test_seed_file_loads_with_load_member_metadata():
    metadata = load_member_metadata(SEED_PATH)

    assert metadata
    assert "thom-tillis" in metadata


def test_seed_has_at_least_10_records():
    assert len(load_member_metadata(SEED_PATH)) >= 10


def test_seed_includes_house_and_senate_records():
    metadata = load_member_metadata(SEED_PATH)
    chambers = {item.chamber for item in metadata.values()}

    assert "House" in chambers
    assert "Senate" in chambers


def test_seed_includes_north_carolina_member():
    metadata = load_member_metadata(SEED_PATH)

    assert any(item.state == "NC" for item in metadata.values())


def test_nc_has_complete_expected_count():
    summary = summarize_member_metadata_by_state(SEED_PATH, "NC")

    assert summary["records"] == 16


def test_nc_has_14_house_records():
    summary = summarize_member_metadata_by_state(SEED_PATH, "NC")

    assert summary["house_records"] == 14


def test_nc_has_2_senate_records():
    summary = summarize_member_metadata_by_state(SEED_PATH, "NC")

    assert summary["senate_records"] == 2


def test_nc_house_districts_include_1_through_14():
    summary = summarize_member_metadata_by_state(SEED_PATH, "NC")

    assert summary["house_districts"] == [
        str(district)
        for district in range(1, 15)
    ]


def test_nc_senate_rows_have_blank_district():
    metadata = load_member_metadata(SEED_PATH)
    nc_senators = [
        item
        for item in metadata.values()
        if item.state == "NC" and item.chamber == "Senate"
    ]

    assert len(nc_senators) == 2
    assert all(item.district is None for item in nc_senators)


def test_nc_has_at_least_one_row_with_committee_assignments():
    summary = summarize_committee_assignment_coverage_by_state(SEED_PATH, "NC")

    assert summary["rows_with_committees"] > 0


def test_nc_committee_assignments_parse_as_list():
    metadata = load_member_metadata(SEED_PATH)

    assert metadata["alma-s-adams"].committee_assignments == [
        "Committee on Agriculture",
        "Committee on Education and Workforce",
    ]
    assert metadata["deborah-k-ross"].committee_assignments == [
        "Committee on Ethics",
        "Committee on Science, Space, and Technology",
        "Committee on the Judiciary",
    ]


def test_nc_committee_coverage_summary_works():
    summary = summarize_committee_assignment_coverage_by_state(SEED_PATH, "nc")

    assert summary["state"] == "NC"
    assert summary["records"] == 16
    assert summary["rows_with_committees"] == 6
    assert summary["rows_without_committees"] == 10
    assert summary["member_ids_without_committees"] == [
        "addison-p-mcdowell",
        "david-rouzer",
        "mark-harris",
        "richard-hudson",
        "pat-harrigan",
        "chuck-edwards",
        "brad-knott",
        "tim-moore",
        "thom-tillis",
        "ted-budd",
    ]


def test_nc_committee_rows_have_source_name_or_source_url():
    metadata = load_member_metadata(SEED_PATH)
    rows = [
        item
        for item in metadata.values()
        if item.state == "NC" and item.committee_assignments
    ]

    assert rows
    for item in rows:
        assert item.source_name or item.source_url


def test_no_subcommittee_names_are_required():
    metadata = load_member_metadata(SEED_PATH)
    all_nc_committees = [
        committee
        for item in metadata.values()
        if item.state == "NC"
        for committee in item.committee_assignments
    ]

    assert "Nutrition and Foreign Agriculture" not in all_nc_committees
    assert "Readiness" not in all_nc_committees
    assert "Energy" not in all_nc_committees


def test_nc_leadership_roles_remain_blank():
    metadata = load_member_metadata(SEED_PATH)

    assert all(
        not item.leadership_roles
        for item in metadata.values()
        if item.state == "NC"
    )


def test_non_nc_rows_committee_assignments_unchanged():
    metadata = load_member_metadata(SEED_PATH)
    non_nc_rows = [
        item
        for item in metadata.values()
        if item.state != "NC"
    ]

    assert [item.member_id for item in non_nc_rows] == [
        "alex-padilla",
        "adam-schiff",
    ]
    assert all(not item.committee_assignments for item in non_nc_rows)


def test_every_nc_row_has_source_name_or_source_url():
    for row in _seed_rows():
        if row["state"] == "NC":
            assert row["source_name"].strip() or row["source_url"].strip()


def test_nc_source_quality_has_profile_sources():
    report = build_metadata_source_quality_report_by_state(SEED_PATH, "NC")

    assert report["records"] == 16
    assert report["profile_sources"] == 16
    assert report["list_sources"] == 0
    assert report["unknown_sources"] == 0


def test_nc_house_rows_use_house_clerk_profile_urls():
    metadata = load_member_metadata(SEED_PATH)
    nc_house_rows = [
        item
        for item in metadata.values()
        if item.state == "NC" and item.chamber == "House"
    ]

    assert len(nc_house_rows) == 14
    for item in nc_house_rows:
        assert item.source_name == "House Clerk Member Profile"
        assert item.source_url.startswith("https://clerk.house.gov/members/")
        assert classify_metadata_source(item.source_url) == "profile"


def test_nc_senate_rows_use_official_senator_websites_or_senate_nc_source():
    metadata = load_member_metadata(SEED_PATH)
    nc_senate_rows = [
        item
        for item in metadata.values()
        if item.state == "NC" and item.chamber == "Senate"
    ]

    assert len(nc_senate_rows) == 2
    for item in nc_senate_rows:
        assert item.source_name in {
            "Official Senate Member Website",
            "Senate.gov North Carolina Senators",
        }
        assert item.source_url.startswith("https://www.tillis.senate.gov/") or item.source_url.startswith("https://www.budd.senate.gov/") or item.source_url == "https://www.senate.gov/states/NC/intro.htm"


def test_non_nc_rows_remain_list_sources():
    metadata = load_member_metadata(SEED_PATH)
    non_nc_rows = [
        item
        for item in metadata.values()
        if item.state != "NC"
    ]

    assert [item.member_id for item in non_nc_rows] == [
        "alex-padilla",
        "adam-schiff",
    ]
    for item in non_nc_rows:
        assert item.source_name == "Senate.gov Senators"
        assert item.source_url == "https://www.senate.gov/senators/"
        assert classify_metadata_source(item.source_url) == "list"


def test_every_seed_row_has_source_name_or_source_url():
    for row in _seed_rows():
        assert row["source_name"].strip() or row["source_url"].strip()


def test_seed_has_no_duplicate_member_id():
    member_ids = [row["member_id"] for row in _seed_rows()]

    assert len(member_ids) == len(set(member_ids))


def test_official_salary_parses_as_float_where_present():
    metadata = load_member_metadata(SEED_PATH)

    for item in metadata.values():
        if item.official_salary is not None:
            assert isinstance(item.official_salary, float)


def test_validator_pass():
    report = validate_member_metadata_seed(SEED_PATH)

    assert report["passed"] is True
    assert report["records"] >= 10
    assert report["house_records"] > 0
    assert report["senate_records"] > 0
    assert report["missing_source_rows"] == 0
    assert report["missing_required_rows"] == 0
    assert report["duplicate_member_ids"] == []
    assert report["errors"] == []


def test_summarize_member_metadata_seed():
    summary = summarize_member_metadata_seed(SEED_PATH)

    assert summary["records"] >= 10
    assert summary["house"] > 0
    assert summary["senate"] > 0
    assert "NC" in summary["states"]
    assert summary["states"] == sorted(summary["states"])


def test_summarize_member_metadata_by_state():
    summary = summarize_member_metadata_by_state(SEED_PATH, "nc")

    assert summary == {
        "state": "NC",
        "records": 16,
        "house_records": 14,
        "senate_records": 2,
        "house_districts": [
            str(district)
            for district in range(1, 15)
        ],
        "senators": ["Ted Budd", "Thom Tillis"],
    }


def test_metadata_source_quality_report_counts_match():
    report = build_metadata_source_quality_report(SEED_PATH)

    assert report["records"] == (
        report["profile_sources"]
        + report["list_sources"]
        + report["unknown_sources"]
    )
    assert report["profile_sources"] == 16
    assert report["list_sources"] == 2
    assert report["unknown_sources"] == 0


def test_metadata_source_quality_breakdown_order_preserved():
    report = build_metadata_source_quality_report(SEED_PATH)
    seed_member_ids = [row["member_id"] for row in _seed_rows()]

    assert [
        item["member_id"]
        for item in report["member_breakdown"]
    ] == seed_member_ids


def test_render_metadata_source_quality_report():
    report = {
        "records": 2,
        "profile_sources": 1,
        "list_sources": 1,
        "unknown_sources": 0,
        "member_breakdown": [
            {"member_id": "alma-s-adams", "source_type": "list"},
            {"member_id": "example-member", "source_type": "profile"},
        ],
    }

    assert render_metadata_source_quality_report(report) == "\n".join([
        "Metadata Source Quality Report:",
        "- records: 2",
        "- profile sources: 1",
        "- list sources: 1",
        "- unknown sources: 0",
        "",
        "member breakdown:",
        "- alma-s-adams: list",
        "- example-member: profile",
        "",
    ])


def test_cli_metadata_source_quality(monkeypatch, capsys):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "transparencyx",
            "--metadata-source-quality",
            str(SEED_PATH),
        ],
    )

    from transparencyx.cli import main

    with pytest.raises(SystemExit) as exit_info:
        main()

    captured = capsys.readouterr()

    assert exit_info.value.code == 0
    assert "Metadata Source Quality Report:\n" in captured.out
    assert "- list sources: " in captured.out


def test_render_output():
    report = validate_member_metadata_seed(SEED_PATH)
    rendered = render_member_metadata_seed_validation(report)

    assert rendered.startswith("Member Metadata Seed Validation: PASS\n")
    assert "- records: " in rendered
    assert "- House records: " in rendered
    assert "- Senate records: " in rendered
    assert "- duplicate member ids: None\n" in rendered


def test_cli_validate_member_metadata_seed(monkeypatch, capsys):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "transparencyx",
            "--validate-member-metadata-seed",
            str(SEED_PATH),
        ],
    )

    from transparencyx.cli import main

    with pytest.raises(SystemExit) as exit_info:
        main()

    captured = capsys.readouterr()

    assert exit_info.value.code == 0
    assert "Member Metadata Seed Validation: PASS\n" in captured.out


def test_forbidden_language_absent():
    combined = SEED_PATH.read_text(encoding="utf-8").lower()
    combined += PLAN_PATH.read_text(encoding="utf-8").lower()
    combined += render_member_metadata_seed_validation(
        validate_member_metadata_seed(SEED_PATH)
    ).lower()
    combined += render_metadata_source_quality_report(
        build_metadata_source_quality_report(SEED_PATH)
    ).lower()
    restricted_terms = [
        "cor" + "ruption",
        "self-" + "dealing",
        "insider trading " + "confirmed",
        "conflict " + "confirmed",
        "mis" + "conduct",
        "sus" + "picious",
    ]

    for term in restricted_terms:
        assert term not in combined
