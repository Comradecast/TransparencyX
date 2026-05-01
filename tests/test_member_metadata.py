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
    build_committee_coverage_report,
    build_metadata_coverage_report,
    load_member_metadata,
    render_committee_coverage_report,
    render_metadata_coverage_report,
    render_member_metadata_template_csv,
    write_committee_coverage_json,
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


def test_metadata_coverage_report_with_full_match():
    dossiers = [
        build_member_dossier_from_profile({"member_name": "Nancy Pelosi"}),
        build_member_dossier_from_profile({"member_name": "Jane Public"}),
    ]
    metadata = {
        "nancy-pelosi": MemberMetadata("nancy-pelosi", "Nancy Pelosi"),
        "jane-public": MemberMetadata("jane-public", "Jane Public"),
    }

    report = build_metadata_coverage_report(dossiers, metadata)

    assert report == {
        "total_dossiers": 2,
        "metadata_records_loaded": 2,
        "matched_dossiers": 2,
        "unmatched_dossiers": 0,
        "matched_member_ids": ["nancy-pelosi", "jane-public"],
        "unmatched_member_ids": [],
    }


def test_metadata_coverage_report_with_partial_match():
    dossiers = [
        build_member_dossier_from_profile({"member_name": "Nancy Pelosi"}),
        build_member_dossier_from_profile({"member_name": "John Doe"}),
    ]
    metadata = {
        "nancy-pelosi": MemberMetadata("nancy-pelosi", "Nancy Pelosi"),
        "jane-public": MemberMetadata("jane-public", "Jane Public"),
    }

    report = build_metadata_coverage_report(dossiers, metadata)

    assert report["metadata_records_loaded"] == 2
    assert report["matched_dossiers"] == 1
    assert report["unmatched_dossiers"] == 1
    assert report["matched_member_ids"] == ["nancy-pelosi"]
    assert report["unmatched_member_ids"] == ["john-doe"]


def test_metadata_coverage_report_with_no_metadata_map():
    dossiers = [
        build_member_dossier_from_profile({"member_name": "Nancy Pelosi"}),
    ]

    report = build_metadata_coverage_report(dossiers, None)

    assert report == {
        "total_dossiers": 1,
        "metadata_records_loaded": 0,
        "matched_dossiers": 0,
        "unmatched_dossiers": 1,
        "matched_member_ids": [],
        "unmatched_member_ids": ["nancy-pelosi"],
    }


def test_metadata_coverage_report_preserves_order():
    dossiers = [
        build_member_dossier_from_profile({"member_name": "John Doe"}),
        build_member_dossier_from_profile({"member_name": "Nancy Pelosi"}),
        build_member_dossier_from_profile({"member_name": "Jane Public"}),
    ]
    metadata = {
        "jane-public": MemberMetadata("jane-public", "Jane Public"),
        "nancy-pelosi": MemberMetadata("nancy-pelosi", "Nancy Pelosi"),
    }

    report = build_metadata_coverage_report(dossiers, metadata)

    assert report["matched_member_ids"] == ["nancy-pelosi", "jane-public"]
    assert report["unmatched_member_ids"] == ["john-doe"]


def test_metadata_coverage_report_lists_have_no_duplicates():
    dossiers = [
        build_member_dossier_from_profile({
            "member_id": "nancy-pelosi",
            "member_name": "Nancy Pelosi",
        }),
        build_member_dossier_from_profile({
            "member_id": "nancy-pelosi",
            "member_name": "Nancy Pelosi",
        }),
        build_member_dossier_from_profile({
            "member_id": "john-doe",
            "member_name": "John Doe",
        }),
        build_member_dossier_from_profile({
            "member_id": "john-doe",
            "member_name": "John Doe",
        }),
    ]
    metadata = {
        "nancy-pelosi": MemberMetadata("nancy-pelosi", "Nancy Pelosi"),
    }

    report = build_metadata_coverage_report(dossiers, metadata)

    assert report["matched_dossiers"] == 2
    assert report["unmatched_dossiers"] == 2
    assert report["matched_member_ids"] == ["nancy-pelosi"]
    assert report["unmatched_member_ids"] == ["john-doe"]


def test_render_metadata_coverage_report_formatting():
    report = {
        "total_dossiers": 5,
        "metadata_records_loaded": 3,
        "matched_dossiers": 3,
        "unmatched_dossiers": 2,
        "matched_member_ids": ["nancy-pelosi", "jane-public"],
        "unmatched_member_ids": ["john-doe", "unknown"],
    }

    assert render_metadata_coverage_report(report) == "\n".join([
        "Metadata Coverage Report:",
        "- total dossiers: 5",
        "- metadata records loaded: 3",
        "- matched dossiers: 3",
        "- unmatched dossiers: 2",
        "",
        "matched member ids:",
        "- nancy-pelosi",
        "- jane-public",
        "",
        "unmatched member ids:",
        "- john-doe",
        "- unknown",
    ])


def test_render_metadata_coverage_report_empty_lists_render_none():
    report = {
        "total_dossiers": 0,
        "metadata_records_loaded": 0,
        "matched_dossiers": 0,
        "unmatched_dossiers": 0,
        "matched_member_ids": [],
        "unmatched_member_ids": [],
    }

    rendered = render_metadata_coverage_report(report)

    assert "matched member ids:\nNone" in rendered
    assert "unmatched member ids:\nNone" in rendered


def test_metadata_coverage_report_json_parseable():
    report = build_metadata_coverage_report(
        [build_member_dossier_from_profile({"member_name": "Nancy Pelosi"})],
        {"nancy-pelosi": MemberMetadata("nancy-pelosi", "Nancy Pelosi")},
    )

    parsed = json.loads(json.dumps(report, indent=2))

    assert parsed == report


def test_committee_coverage_report_with_full_coverage():
    dossiers = [
        build_member_dossier_from_profile({
            "member_name": "Alma S. Adams",
            "committee_assignments": ["Committee on Agriculture"],
        }),
        build_member_dossier_from_profile({
            "member_name": "Donald G. Davis",
            "committee_assignments": ["Committee on Armed Services"],
        }),
    ]

    report = build_committee_coverage_report(dossiers)

    assert report == {
        "total_dossiers": 2,
        "rows_with_committees": 2,
        "rows_without_committees": 0,
        "member_ids_with_committees": ["alma-s-adams", "donald-g-davis"],
        "member_ids_without_committees": [],
    }


def test_committee_coverage_report_with_partial_coverage():
    dossiers = [
        build_member_dossier_from_profile({
            "member_name": "Alma S. Adams",
            "committee_assignments": ["Committee on Agriculture"],
        }),
        build_member_dossier_from_profile({"member_name": "Thom Tillis"}),
    ]

    report = build_committee_coverage_report(dossiers)

    assert report["rows_with_committees"] == 1
    assert report["rows_without_committees"] == 1
    assert report["member_ids_with_committees"] == ["alma-s-adams"]
    assert report["member_ids_without_committees"] == ["thom-tillis"]


def test_committee_coverage_report_with_no_coverage():
    dossiers = [
        build_member_dossier_from_profile({"member_name": "Thom Tillis"}),
        build_member_dossier_from_profile({"member_name": "Ted Budd"}),
    ]

    report = build_committee_coverage_report(dossiers)

    assert report["rows_with_committees"] == 0
    assert report["rows_without_committees"] == 2
    assert report["member_ids_with_committees"] == []
    assert report["member_ids_without_committees"] == ["thom-tillis", "ted-budd"]


def test_committee_coverage_report_lists_have_no_duplicates():
    dossiers = [
        build_member_dossier_from_profile({
            "member_id": "alma-s-adams",
            "member_name": "Alma S. Adams",
            "committee_assignments": ["Committee on Agriculture"],
        }),
        build_member_dossier_from_profile({
            "member_id": "alma-s-adams",
            "member_name": "Alma S. Adams",
            "committee_assignments": ["Committee on Agriculture"],
        }),
        build_member_dossier_from_profile({"member_id": "ted-budd", "member_name": "Ted Budd"}),
        build_member_dossier_from_profile({"member_id": "ted-budd", "member_name": "Ted Budd"}),
    ]

    report = build_committee_coverage_report(dossiers)

    assert report["rows_with_committees"] == 2
    assert report["rows_without_committees"] == 2
    assert report["member_ids_with_committees"] == ["alma-s-adams"]
    assert report["member_ids_without_committees"] == ["ted-budd"]


def test_render_committee_coverage_report_formatting():
    report = {
        "total_dossiers": 3,
        "rows_with_committees": 2,
        "rows_without_committees": 1,
        "member_ids_with_committees": ["alma-s-adams", "donald-g-davis"],
        "member_ids_without_committees": ["thom-tillis"],
    }

    assert render_committee_coverage_report(report) == "\n".join([
        "Committee Coverage Report:",
        "- total dossiers: 3",
        "- rows with committees: 2",
        "- rows without committees: 1",
        "",
        "member ids with committees:",
        "- alma-s-adams",
        "- donald-g-davis",
        "",
        "member ids without committees:",
        "- thom-tillis",
        "",
    ])


def test_render_committee_coverage_report_empty_lists_render_none():
    report = {
        "total_dossiers": 0,
        "rows_with_committees": 0,
        "rows_without_committees": 0,
        "member_ids_with_committees": [],
        "member_ids_without_committees": [],
    }

    rendered = render_committee_coverage_report(report)

    assert rendered.endswith("\n")
    assert "member ids with committees:\nNone" in rendered
    assert "member ids without committees:\nNone" in rendered


def test_write_committee_coverage_json(tmp_path):
    report = {
        "total_dossiers": 1,
        "rows_with_committees": 1,
        "rows_without_committees": 0,
        "member_ids_with_committees": ["alma-s-adams"],
        "member_ids_without_committees": [],
    }
    path = tmp_path / "nested" / "committee_coverage.json"

    returned = write_committee_coverage_json(report, path)

    assert returned == path
    assert path.read_text(encoding="utf-8").endswith("\n")
    assert json.loads(path.read_text(encoding="utf-8")) == report


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


def test_cli_metadata_coverage_report_and_json(tmp_path, monkeypatch, capsys):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "dossiers"
    coverage_dir = tmp_path / "coverage"
    metadata_path = tmp_path / "metadata.csv"
    input_dir.mkdir()
    coverage_dir.mkdir()
    metadata_path.write_text(
        "\n".join([
            "member_id,full_name,chamber",
            "nancy-pelosi,Nancy Pelosi,House",
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
            "--metadata-coverage-json",
            str(coverage_dir),
        ],
    )
    monkeypatch.setattr(
        "transparencyx.profile.batch.build_profiles_for_directory",
        lambda directory: [
            {"member_name": "Nancy Pelosi"},
            {"member_name": "John Doe"},
        ],
    )

    from transparencyx.cli import main

    with pytest.raises(SystemExit) as exit_info:
        main()

    captured = capsys.readouterr()
    coverage_path = coverage_dir / "metadata_coverage.json"
    report = json.loads(coverage_path.read_text(encoding="utf-8"))

    assert exit_info.value.code == 0
    assert "Metadata Coverage Report:\n" in captured.out
    assert "- matched dossiers: 1\n" in captured.out
    assert "- unmatched dossiers: 1\n" in captured.out
    assert f"Wrote metadata coverage JSON: {coverage_path}\n" in captured.out
    assert report == {
        "total_dossiers": 2,
        "metadata_records_loaded": 1,
        "matched_dossiers": 1,
        "unmatched_dossiers": 1,
        "matched_member_ids": ["nancy-pelosi"],
        "unmatched_member_ids": ["john-doe"],
    }


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
        + render_metadata_coverage_report(
            build_metadata_coverage_report([dossier], {"nancy-pelosi": MemberMetadata(
                "nancy-pelosi",
                "Nancy Pelosi",
            )})
        )
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
