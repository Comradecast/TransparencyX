import csv
import json
import sys
from io import StringIO

import pytest

from transparencyx.dossier.builder import build_member_dossier_from_profile
from transparencyx.dossier.metadata import (
    MEMBER_METADATA_COLUMNS,
    MemberMetadata,
    apply_member_metadata,
    load_member_metadata,
    render_member_metadata_template_csv,
    write_member_metadata_template_csv,
)
from transparencyx.dossier.render import render_member_dossier_summary


def test_template_header_matches_member_metadata_columns_exactly():
    rows = list(csv.reader(StringIO(render_member_metadata_template_csv())))

    assert rows == [MEMBER_METADATA_COLUMNS]


def test_template_ends_with_newline():
    assert render_member_metadata_template_csv().endswith("\n")


def test_write_template_creates_parent_dirs(tmp_path):
    output_path = tmp_path / "nested" / "member_metadata_template.csv"

    returned_path = write_member_metadata_template_csv(output_path)

    assert returned_path == output_path
    assert output_path.exists()
    assert list(csv.reader(StringIO(output_path.read_text(encoding="utf-8")))) == [
        MEMBER_METADATA_COLUMNS
    ]


def test_write_template_overwrites_deterministically(tmp_path):
    output_path = tmp_path / "member_metadata_template.csv"
    output_path.write_text("old content", encoding="utf-8")

    write_member_metadata_template_csv(output_path)
    first = output_path.read_text(encoding="utf-8")
    write_member_metadata_template_csv(output_path)
    second = output_path.read_text(encoding="utf-8")

    assert first == second
    assert first == render_member_metadata_template_csv()


def test_cli_writes_template(tmp_path, monkeypatch, capsys):
    output_path = tmp_path / "member_metadata_template.csv"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "transparencyx",
            "--write-member-metadata-template",
            str(output_path),
        ],
    )

    from transparencyx.cli import main

    with pytest.raises(SystemExit) as exit_info:
        main()

    captured = capsys.readouterr()

    assert exit_info.value.code == 0
    assert captured.out == f"Wrote member metadata template CSV: {output_path}\n"
    assert list(csv.reader(StringIO(output_path.read_text(encoding="utf-8")))) == [
        MEMBER_METADATA_COLUMNS
    ]


def test_load_csv(tmp_path):
    path = tmp_path / "metadata.csv"
    path.write_text(
        "\n".join([
            "member_id,full_name,chamber,state,district,party",
            "nancy-pelosi,Nancy Pelosi,House,CA,11,Democratic",
        ]),
        encoding="utf-8",
    )

    metadata = load_member_metadata(path)

    assert list(metadata.keys()) == ["nancy-pelosi"]
    assert metadata["nancy-pelosi"].full_name == "Nancy Pelosi"
    assert metadata["nancy-pelosi"].chamber == "House"
    assert metadata["nancy-pelosi"].state == "CA"


def test_load_json_list(tmp_path):
    path = tmp_path / "metadata.json"
    path.write_text(
        json.dumps([
            {
                "member_id": "nancy-pelosi",
                "full_name": "Nancy Pelosi",
            }
        ]),
        encoding="utf-8",
    )

    metadata = load_member_metadata(path)

    assert metadata["nancy-pelosi"].full_name == "Nancy Pelosi"


def test_load_json_members_object(tmp_path):
    path = tmp_path / "metadata.json"
    path.write_text(
        json.dumps({
            "members": [
                {
                    "member_id": "nancy-pelosi",
                    "full_name": "Nancy Pelosi",
                }
            ]
        }),
        encoding="utf-8",
    )

    metadata = load_member_metadata(path)

    assert metadata["nancy-pelosi"].full_name == "Nancy Pelosi"


def test_pipe_delimited_list_parsing(tmp_path):
    path = tmp_path / "metadata.csv"
    path.write_text(
        "\n".join([
            "member_id,full_name,leadership_roles,committee_assignments",
            "nancy-pelosi,Nancy Pelosi,Speaker|Minority Leader,Rules|Budget",
        ]),
        encoding="utf-8",
    )

    metadata = load_member_metadata(path)["nancy-pelosi"]

    assert metadata.leadership_roles == ["Speaker", "Minority Leader"]
    assert metadata.committee_assignments == ["Rules", "Budget"]


def test_official_salary_parsing(tmp_path):
    path = tmp_path / "metadata.csv"
    path.write_text(
        "\n".join([
            "member_id,full_name,official_salary",
            "nancy-pelosi,Nancy Pelosi,174000",
        ]),
        encoding="utf-8",
    )

    metadata = load_member_metadata(path)["nancy-pelosi"]

    assert metadata.official_salary == 174000.0


def test_blank_optional_values(tmp_path):
    path = tmp_path / "metadata.csv"
    path.write_text(
        "\n".join([
            "member_id,full_name,chamber,official_salary,leadership_roles",
            "nancy-pelosi,Nancy Pelosi,,,",
        ]),
        encoding="utf-8",
    )

    metadata = load_member_metadata(path)["nancy-pelosi"]

    assert metadata.chamber is None
    assert metadata.official_salary is None
    assert metadata.leadership_roles == []


def test_missing_required_fields_fail(tmp_path):
    path = tmp_path / "metadata.csv"
    path.write_text(
        "\n".join([
            "member_id,full_name",
            "nancy-pelosi,",
        ]),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="full_name is required"):
        load_member_metadata(path)


def test_duplicate_member_id_fail(tmp_path):
    path = tmp_path / "metadata.json"
    path.write_text(
        json.dumps([
            {"member_id": "nancy-pelosi", "full_name": "Nancy Pelosi"},
            {"member_id": "nancy-pelosi", "full_name": "Nancy Pelosi"},
        ]),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="Duplicate member metadata member_id: nancy-pelosi",
    ):
        load_member_metadata(path)


def test_unsupported_extension_fail(tmp_path):
    path = tmp_path / "metadata.txt"
    path.write_text("", encoding="utf-8")

    with pytest.raises(ValueError, match=".csv or .json"):
        load_member_metadata(path)


def test_apply_metadata_updates_identity_and_office():
    dossier = build_member_dossier_from_profile({"member_name": "Nancy Pelosi"})
    metadata = MemberMetadata(
        member_id="nancy-pelosi",
        full_name="Nancy Pelosi",
        chamber="House",
        state="CA",
        district="11",
        party="Democratic",
        current_status="Current",
        official_salary=174000.0,
        leadership_roles=["Speaker Emerita"],
        committee_assignments=["Appropriations"],
        office_start="1987-06-02",
        office_end=None,
    )

    apply_member_metadata(dossier, metadata)

    assert dossier.identity.full_name == "Nancy Pelosi"
    assert dossier.identity.chamber == "House"
    assert dossier.identity.state == "CA"
    assert dossier.identity.district == "11"
    assert dossier.identity.party == "Democratic"
    assert dossier.identity.current_status == "Current"
    assert dossier.office.official_salary == 174000.0
    assert dossier.office.leadership_roles == ["Speaker Emerita"]
    assert dossier.office.committee_assignments == ["Appropriations"]
    assert dossier.office.office_start == "1987-06-02"
    assert dossier.office.office_end is None


def test_apply_metadata_does_not_alter_financials_or_exposure():
    dossier = build_member_dossier_from_profile({
        "member_name": "Nancy Pelosi",
        "disclosure_year": 2023,
        "federal_award_exposure": [{"award_count": 1}],
    })
    original_financials = dossier.financials
    original_exposure = dossier.exposure

    apply_member_metadata(
        dossier,
        MemberMetadata(member_id="nancy-pelosi", full_name="Nancy Pelosi"),
    )

    assert dossier.financials is original_financials
    assert dossier.exposure is original_exposure
    assert dossier.financials.disclosure_years == [2023]
    assert dossier.exposure.federal_award_exposure == [{"award_count": 1}]


def test_apply_metadata_adds_evidence_source():
    dossier = build_member_dossier_from_profile({"member_name": "Nancy Pelosi"})
    metadata = MemberMetadata(
        member_id="nancy-pelosi",
        full_name="Nancy Pelosi",
        source_name="Office roster",
        source_url="https://example.test/roster",
    )

    apply_member_metadata(dossier, metadata)

    assert dossier.evidence_sources[-1].source_type == "member_metadata"
    assert dossier.evidence_sources[-1].source_name == "Office roster"
    assert dossier.evidence_sources[-1].source_url == "https://example.test/roster"


def test_cli_batch_export_with_metadata(tmp_path, monkeypatch, capsys):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "dossiers"
    metadata_path = tmp_path / "metadata.csv"
    input_dir.mkdir()
    metadata_path.write_text(
        "\n".join([
            "member_id,full_name,chamber,state,district,party,official_salary,source_name",
            "nancy-pelosi,Nancy Pelosi,House,CA,11,Democratic,174000,Office roster",
        ]),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "transparencyx",
            "--batch-dossier-json",
            str(input_dir),
            "--output-dir",
            str(output_dir),
            "--member-metadata",
            str(metadata_path),
        ],
    )
    monkeypatch.setattr(
        "transparencyx.profile.batch.build_profiles_for_directory",
        lambda directory: [
            {
                "member_name": "Nancy Pelosi",
                "disclosure_year": 2023,
            }
        ],
    )

    from transparencyx.cli import main

    with pytest.raises(SystemExit) as exit_info:
        main()

    captured = capsys.readouterr()
    data = json.loads((output_dir / "nancy-pelosi.json").read_text(encoding="utf-8"))

    assert exit_info.value.code == 0
    assert "Loaded member metadata records: 1\n" in captured.out
    assert data["identity"]["chamber"] == "House"
    assert data["identity"]["state"] == "CA"
    assert data["identity"]["district"] == "11"
    assert data["identity"]["party"] == "Democratic"
    assert data["office"]["official_salary"] == 174000.0
    assert data["evidence_sources"][-1]["source_type"] == "member_metadata"


def test_forbidden_language_absent():
    dossier = build_member_dossier_from_profile({"member_name": "Nancy Pelosi"})
    apply_member_metadata(
        dossier,
        MemberMetadata(
            member_id="nancy-pelosi",
            full_name="Nancy Pelosi",
            chamber="House",
            source_name="Office roster",
        ),
    )

    rendered = (
        render_member_dossier_summary(dossier)
        + render_member_metadata_template_csv()
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
        assert term not in rendered
