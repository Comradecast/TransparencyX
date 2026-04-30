import csv
import sys
from pathlib import Path

import pytest

from transparencyx.dossier.metadata import load_member_metadata
from transparencyx.dossier.metadata_seed import (
    render_member_metadata_seed_validation,
    validate_member_metadata_seed,
)


SEED_PATH = Path("data/seed/member_metadata_seed.csv")


def _seed_rows():
    with SEED_PATH.open(newline="", encoding="utf-8") as csv_file:
        return list(csv.DictReader(csv_file))


def test_seed_file_exists():
    assert SEED_PATH.exists()


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
