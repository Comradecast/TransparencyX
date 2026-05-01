import csv
import sys
from pathlib import Path

import pytest

from transparencyx.dossier.metadata import load_member_metadata
from transparencyx.dossier.metadata_seed import (
    render_member_metadata_seed_validation,
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


def test_every_nc_row_has_source_name_or_source_url():
    for row in _seed_rows():
        if row["state"] == "NC":
            assert row["source_name"].strip() or row["source_url"].strip()


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
