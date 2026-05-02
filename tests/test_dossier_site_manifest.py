import json
import sys
from pathlib import Path

import pytest

from transparencyx.dossier.manifest import (
    build_source_manifest,
    build_site_manifest,
    render_source_manifest_json,
    render_site_manifest_json,
    write_source_manifest_json,
    write_site_manifest_json,
)
from transparencyx.dossier.schema import (
    DossierExposure,
    DossierFinancials,
    MemberDossier,
    MemberIdentity,
    MemberOffice,
)


SOURCE_MANIFEST_TEMPLATE_PATH = Path("docs/source_manifest_template.json")
NC_EXPECTED_SOURCE_MANIFEST_PATH = Path(
    "docs/source_manifests/nc_2023_expected_sources.json"
)
SOURCE_GAP_REPORT_PATH = Path("docs/source_gap_report.json")
SOURCE_MANIFEST_TEMPLATE_KEYS = {
    "member_slug",
    "full_name",
    "chamber",
    "state",
    "district",
    "year",
    "source_pdf",
    "source_url",
    "expected",
    "acquired",
    "parsed",
    "notes",
}
SOURCE_GAP_REPORT_KEYS = {
    "member_slug",
    "year",
    "expected",
    "acquired",
    "parsed",
    "source_pdf",
}


def _dossier(
    member_id: str,
    chamber: str | None = "House",
    state: str | None = "CA",
    district: str | None = None,
    years: list[int] | None = None,
) -> MemberDossier:
    return MemberDossier(
        identity=MemberIdentity(
            member_id=member_id,
            full_name=member_id.replace("-", " ").title(),
            chamber=chamber,
            state=state,
            district=district,
        ),
        office=MemberOffice(),
        financials=DossierFinancials(disclosure_years=years or []),
        exposure=DossierExposure(),
        evidence_sources=[],
    )


def test_source_manifest_template_json_exists():
    assert SOURCE_MANIFEST_TEMPLATE_PATH.exists()


def test_source_manifest_template_json_parses():
    template = json.loads(SOURCE_MANIFEST_TEMPLATE_PATH.read_text(encoding="utf-8"))

    assert template["template_type"] == "state_source_manifest"
    assert isinstance(template["sources"], list)
    assert template["sources"]


def test_source_manifest_template_entries_have_required_keys():
    template = json.loads(SOURCE_MANIFEST_TEMPLATE_PATH.read_text(encoding="utf-8"))

    for entry in template["sources"]:
        assert set(entry) == SOURCE_MANIFEST_TEMPLATE_KEYS


def test_source_manifest_template_status_fields_are_booleans():
    template = json.loads(SOURCE_MANIFEST_TEMPLATE_PATH.read_text(encoding="utf-8"))

    for entry in template["sources"]:
        assert isinstance(entry["expected"], bool)
        assert isinstance(entry["acquired"], bool)
        assert isinstance(entry["parsed"], bool)


def test_nc_expected_source_manifest_exists():
    assert NC_EXPECTED_SOURCE_MANIFEST_PATH.exists()


def test_nc_expected_source_manifest_json_parses():
    manifest = json.loads(
        NC_EXPECTED_SOURCE_MANIFEST_PATH.read_text(encoding="utf-8")
    )

    assert manifest["template_type"] == "state_source_manifest"
    assert isinstance(manifest["sources"], list)
    assert manifest["sources"]


def test_nc_expected_source_manifest_entries_have_required_keys():
    manifest = json.loads(
        NC_EXPECTED_SOURCE_MANIFEST_PATH.read_text(encoding="utf-8")
    )

    for entry in manifest["sources"]:
        assert set(entry) == SOURCE_MANIFEST_TEMPLATE_KEYS


def test_nc_expected_source_manifest_entries_have_state_and_year():
    manifest = json.loads(
        NC_EXPECTED_SOURCE_MANIFEST_PATH.read_text(encoding="utf-8")
    )

    for entry in manifest["sources"]:
        assert entry["state"] == "NC"
        assert entry["year"] == 2023


def test_nc_expected_source_manifest_status_fields_are_booleans():
    manifest = json.loads(
        NC_EXPECTED_SOURCE_MANIFEST_PATH.read_text(encoding="utf-8")
    )

    for entry in manifest["sources"]:
        assert isinstance(entry["expected"], bool)
        assert isinstance(entry["acquired"], bool)
        assert isinstance(entry["parsed"], bool)


def test_nc_expected_source_manifest_ordering_is_deterministic():
    manifest = json.loads(
        NC_EXPECTED_SOURCE_MANIFEST_PATH.read_text(encoding="utf-8")
    )
    entries = manifest["sources"]
    house_entries = [
        entry
        for entry in entries
        if entry["chamber"] == "House"
    ]
    senate_entries = [
        entry
        for entry in entries
        if entry["chamber"] == "Senate"
    ]

    assert entries == house_entries + senate_entries
    assert [
        int(entry["district"])
        for entry in house_entries
    ] == sorted(int(entry["district"]) for entry in house_entries)
    assert [
        entry["member_slug"]
        for entry in senate_entries
    ] == sorted(entry["member_slug"] for entry in senate_entries)


def test_source_gap_report_exists():
    assert SOURCE_GAP_REPORT_PATH.exists()


def test_source_gap_report_totals():
    report = json.loads(SOURCE_GAP_REPORT_PATH.read_text(encoding="utf-8"))

    assert report["total_expected"] == 16
    assert report["total_acquired"] == 5
    assert report["total_missing"] == 11
    assert report["total_parsed"] == 5
    assert len(report["entries"]) == 16


def test_source_gap_report_entries_have_required_keys():
    report = json.loads(SOURCE_GAP_REPORT_PATH.read_text(encoding="utf-8"))

    for entry in report["entries"]:
        assert set(entry) == SOURCE_GAP_REPORT_KEYS


def test_source_gap_report_known_member_statuses():
    report = json.loads(SOURCE_GAP_REPORT_PATH.read_text(encoding="utf-8"))
    entries = {
        entry["member_slug"]: entry
        for entry in report["entries"]
    }

    assert entries["alma-s-adams"] == {
        "member_slug": "alma-s-adams",
        "year": 2023,
        "expected": True,
        "acquired": True,
        "parsed": True,
        "source_pdf": "data/raw/house/2023/10059952.pdf",
    }
    assert entries["donald-g-davis"] == {
        "member_slug": "donald-g-davis",
        "year": 2023,
        "expected": True,
        "acquired": False,
        "parsed": False,
        "source_pdf": None,
    }


def test_source_gap_report_order_matches_expected_manifest():
    expected_manifest = json.loads(
        NC_EXPECTED_SOURCE_MANIFEST_PATH.read_text(encoding="utf-8")
    )
    report = json.loads(SOURCE_GAP_REPORT_PATH.read_text(encoding="utf-8"))

    assert [
        (entry["member_slug"], entry["year"])
        for entry in report["entries"]
    ] == [
        (entry["member_slug"], entry["year"])
        for entry in expected_manifest["sources"]
    ]


def test_source_gap_report_matches_actual_sources_by_member_and_year():
    source_manifest = json.loads(Path("docs/source_manifest.json").read_text(
        encoding="utf-8"
    ))
    report = json.loads(SOURCE_GAP_REPORT_PATH.read_text(encoding="utf-8"))
    actual_sources = {
        (entry["member_slug"], entry["year"]): entry
        for entry in source_manifest["sources"]
    }

    for entry in report["entries"]:
        actual = actual_sources.get((entry["member_slug"], entry["year"]))
        assert entry["acquired"] is (actual is not None)
        assert entry["parsed"] is (actual["parsed"] if actual is not None else False)
        assert entry["source_pdf"] == (
            actual["source_pdf"] if actual is not None else None
        )


def test_source_manifest_entries_are_deterministic_and_structured():
    manifest = build_source_manifest(
        profiles=[
            {
                "disclosure_path": "data/raw/house/2023/b.pdf",
                "shape_export": {"summary": {}},
            },
            {
                "disclosure_path": "data/raw/house/2024/a.pdf",
            },
        ],
        dossiers=[
            _dossier("z-member", district="2"),
            _dossier("a-member", state="NC", district=None, years=[2022]),
        ],
    )

    assert manifest == {
        "source_count": 2,
        "sources": [
            {
                "member_slug": "a-member",
                "chamber": "House",
                "state": "NC",
                "district": None,
                "year": 2024,
                "source_pdf": "data/raw/house/2024/a.pdf",
                "parsed": False,
            },
            {
                "member_slug": "z-member",
                "chamber": "House",
                "state": "CA",
                "district": "2",
                "year": 2023,
                "source_pdf": "data/raw/house/2023/b.pdf",
                "parsed": True,
            },
        ],
    }


def test_source_manifest_deduplicates_same_member_same_source():
    manifest = build_source_manifest(
        profiles=[
            {
                "disclosure_path": "data/raw/house/2023/a.pdf",
                "shape_export": {"summary": {}},
            },
            {
                "disclosure_path": "data/raw/house/2023/a.pdf",
                "shape_export": {"summary": {}},
            },
        ],
        dossiers=[
            _dossier("same-member"),
            _dossier("same-member"),
        ],
    )

    assert manifest["source_count"] == 1
    assert len(manifest["sources"]) == 1


def test_source_manifest_keeps_same_member_different_source_pdf():
    manifest = build_source_manifest(
        profiles=[
            {
                "disclosure_path": "data/raw/house/2023/a.pdf",
                "shape_export": {"summary": {}},
            },
            {
                "disclosure_path": "data/raw/house/2023/b.pdf",
                "shape_export": {"summary": {}},
            },
        ],
        dossiers=[
            _dossier("same-member"),
            _dossier("same-member"),
        ],
    )

    assert manifest["source_count"] == 2
    assert [
        entry["source_pdf"]
        for entry in manifest["sources"]
    ] == [
        "data/raw/house/2023/a.pdf",
        "data/raw/house/2023/b.pdf",
    ]


def test_source_manifest_keeps_same_member_different_years():
    manifest = build_source_manifest(
        profiles=[
            {
                "disclosure_path": "data/raw/house/no-year/a.pdf",
                "disclosure_year": 2023,
                "shape_export": {"summary": {}},
            },
            {
                "disclosure_path": "data/raw/house/no-year/a.pdf",
                "disclosure_year": 2024,
                "shape_export": {"summary": {}},
            },
        ],
        dossiers=[
            _dossier("same-member"),
            _dossier("same-member"),
        ],
    )

    assert manifest["source_count"] == 2
    assert [
        entry["year"]
        for entry in manifest["sources"]
    ] == [2023, 2024]


def test_source_manifest_current_dataset_count_remains_six():
    members = [
        ("alma-s-adams", "NC", "12", "data/raw/house/2023/10059952.pdf"),
        ("chuck-edwards", "NC", "11", "data/raw/house/2023/10059419.pdf"),
        ("deborah-k-ross", "NC", "2", "data/raw/house/2023/10059715.pdf"),
        ("nancy-pelosi", "CA", "11", "data/raw/house/2023/10059734.pdf"),
        ("valerie-p-foushee", "NC", "4", "data/raw/house/2023/10057344.pdf"),
        ("virginia-foxx", "NC", "5", "data/raw/house/2023/10059335.pdf"),
    ]

    manifest = build_source_manifest(
        profiles=[
            {
                "disclosure_path": source_pdf,
                "shape_export": {"summary": {}},
            }
            for _, _, _, source_pdf in members
        ],
        dossiers=[
            _dossier(member_id, state=state, district=district)
            for member_id, state, district, _ in members
        ],
    )

    assert manifest["source_count"] == 6
    assert len(manifest["sources"]) == 6


def test_source_manifest_year_falls_back_to_profile_then_dossier():
    manifest = build_source_manifest(
        profiles=[
            {"disclosure_path": "data/raw/house/no-year/a.pdf", "filing_year": 2021},
            {"disclosure_path": "data/raw/house/no-year/b.pdf"},
        ],
        dossiers=[
            _dossier("profile-year", years=[2020]),
            _dossier("dossier-year", years=[2019]),
        ],
    )

    entries = {
        entry["member_slug"]: entry
        for entry in manifest["sources"]
    }
    assert entries["profile-year"]["year"] == 2021
    assert entries["dossier-year"]["year"] == 2019


def test_render_source_manifest_json_parseable_and_newline():
    manifest = build_source_manifest(
        profiles=[],
        dossiers=[],
    )

    rendered = render_source_manifest_json(manifest)

    assert json.loads(rendered) == manifest
    assert rendered.endswith("\n")


def test_write_source_manifest_json_creates_parent_dirs(tmp_path):
    path = tmp_path / "nested" / "source_manifest.json"
    manifest = build_source_manifest(
        profiles=[],
        dossiers=[],
    )

    returned = write_source_manifest_json(manifest, path)

    assert returned == path
    assert json.loads(path.read_text(encoding="utf-8")) == manifest


def test_manifest_without_metadata():
    manifest = build_site_manifest(
        input_directory="data/raw/house/2023",
        output_directory="out/site",
        options={
            "member_metadata": False,
            "fetch_exposure": False,
            "recipient_candidate_audit": False,
        },
        profiles_count=1,
        dossiers_count=1,
        json_paths=[Path("out/site/nancy-pelosi.json")],
        html_paths=[Path("out/site/nancy-pelosi.html")],
        metadata_report=None,
    )

    assert manifest == {
        "build_type": "dossier_site",
        "input_directory": "data/raw/house/2023",
        "output_directory": "out/site",
        "options": {
            "member_metadata": False,
            "fetch_exposure": False,
            "recipient_candidate_audit": False,
        },
        "counts": {
            "profiles": 1,
            "dossiers": 1,
            "json_dossiers": 1,
            "html_dossiers": 1,
            "metadata_records_loaded": 0,
            "metadata_matched_dossiers": 0,
            "metadata_unmatched_dossiers": 0,
            "committee_rows_with_assignments": 0,
            "committee_rows_without_assignments": 0,
        },
        "artifacts": {
            "json_index": "index.json",
            "html_index": "index.html",
            "metadata_coverage": None,
            "committee_coverage": None,
            "dossier_json_files": ["nancy-pelosi.json"],
            "dossier_html_files": ["nancy-pelosi.html"],
        },
    }


def test_manifest_with_metadata_report():
    report = {
        "total_dossiers": 2,
        "metadata_records_loaded": 2,
        "matched_dossiers": 1,
        "unmatched_dossiers": 1,
        "matched_member_ids": ["nancy-pelosi"],
        "unmatched_member_ids": ["jane-public"],
    }

    manifest = build_site_manifest(
        input_directory="input",
        output_directory="out",
        options={
            "member_metadata": True,
            "fetch_exposure": True,
            "recipient_candidate_audit": True,
        },
        profiles_count=2,
        dossiers_count=2,
        json_paths=[Path("out/nancy-pelosi.json"), Path("out/jane-public.json")],
        html_paths=[Path("out/nancy-pelosi.html"), Path("out/jane-public.html")],
        metadata_report=report,
    )

    assert manifest["options"] == {
        "member_metadata": True,
        "fetch_exposure": True,
        "recipient_candidate_audit": True,
    }
    assert manifest["counts"]["metadata_records_loaded"] == 2
    assert manifest["counts"]["metadata_matched_dossiers"] == 1
    assert manifest["counts"]["metadata_unmatched_dossiers"] == 1
    assert manifest["artifacts"]["metadata_coverage"] == "metadata_coverage.json"
    assert manifest["artifacts"]["committee_coverage"] is None


def test_manifest_with_committee_report():
    committee_report = {
        "total_dossiers": 2,
        "rows_with_committees": 1,
        "rows_without_committees": 1,
        "member_ids_with_committees": ["alma-s-adams"],
        "member_ids_without_committees": ["thom-tillis"],
    }

    manifest = build_site_manifest(
        input_directory="input",
        output_directory="out",
        options={"member_metadata": True},
        profiles_count=2,
        dossiers_count=2,
        json_paths=[Path("out/alma-s-adams.json"), Path("out/thom-tillis.json")],
        html_paths=[Path("out/alma-s-adams.html"), Path("out/thom-tillis.html")],
        metadata_report=None,
        committee_report=committee_report,
    )

    assert manifest["counts"]["committee_rows_with_assignments"] == 1
    assert manifest["counts"]["committee_rows_without_assignments"] == 1
    assert manifest["artifacts"]["committee_coverage"] == "committee_coverage.json"


def test_manifest_artifact_basenames_only():
    manifest = build_site_manifest(
        input_directory="input",
        output_directory="out",
        options={},
        profiles_count=1,
        dossiers_count=1,
        json_paths=[Path("nested/out/nancy-pelosi.json")],
        html_paths=[Path("nested/out/nancy-pelosi.html")],
        metadata_report=None,
    )

    assert manifest["artifacts"]["dossier_json_files"] == ["nancy-pelosi.json"]
    assert manifest["artifacts"]["dossier_html_files"] == ["nancy-pelosi.html"]


def test_manifest_counts_reflect_inputs():
    manifest = build_site_manifest(
        input_directory="input",
        output_directory="out",
        options={},
        profiles_count=3,
        dossiers_count=2,
        json_paths=[Path("a.json"), Path("b.json")],
        html_paths=[Path("a.html")],
        metadata_report=None,
    )

    assert manifest["counts"]["profiles"] == 3
    assert manifest["counts"]["dossiers"] == 2
    assert manifest["counts"]["json_dossiers"] == 2
    assert manifest["counts"]["html_dossiers"] == 1


def test_render_site_manifest_json_parseable():
    manifest = build_site_manifest(
        input_directory="input",
        output_directory="out",
        options={},
        profiles_count=0,
        dossiers_count=0,
        json_paths=[],
        html_paths=[],
        metadata_report=None,
    )

    assert json.loads(render_site_manifest_json(manifest)) == manifest


def test_render_site_manifest_json_ends_with_newline():
    manifest = build_site_manifest(
        input_directory="input",
        output_directory="out",
        options={},
        profiles_count=0,
        dossiers_count=0,
        json_paths=[],
        html_paths=[],
        metadata_report=None,
    )

    assert render_site_manifest_json(manifest).endswith("\n")


def test_write_site_manifest_json_creates_parent_dirs(tmp_path):
    path = tmp_path / "nested" / "build_manifest.json"
    manifest = build_site_manifest(
        input_directory="input",
        output_directory="out",
        options={},
        profiles_count=0,
        dossiers_count=0,
        json_paths=[],
        html_paths=[],
        metadata_report=None,
    )

    returned = write_site_manifest_json(manifest, path)

    assert returned == path
    assert json.loads(path.read_text(encoding="utf-8")) == manifest


def test_site_build_creates_build_manifest_json(tmp_path, monkeypatch, capsys):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "site"
    input_dir.mkdir()
    monkeypatch.setattr(
        "transparencyx.profile.batch.build_profiles_for_directory",
        lambda directory: [
            {
                "member_name": "Nancy Pelosi",
                "disclosure_year": 2023,
            }
        ],
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "transparencyx",
            "--build-dossier-site",
            str(input_dir),
            "--output-dir",
            str(output_dir),
        ],
    )

    from transparencyx.cli import main

    with pytest.raises(SystemExit) as exit_info:
        main()

    captured = capsys.readouterr()
    manifest_path = output_dir / "build_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert exit_info.value.code == 0
    assert f"Wrote site build manifest JSON: {manifest_path}" in captured.out
    assert manifest["build_type"] == "dossier_site"
    assert manifest["counts"]["profiles"] == 1
    assert manifest["counts"]["dossiers"] == 1
    assert manifest["artifacts"]["dossier_json_files"] == ["nancy-pelosi.json"]
    assert manifest["artifacts"]["dossier_html_files"] == ["nancy-pelosi.html"]


def test_manifest_forbidden_language_absent():
    manifest = build_site_manifest(
        input_directory="input",
        output_directory="out",
        options={},
        profiles_count=0,
        dossiers_count=0,
        json_paths=[],
        html_paths=[],
        metadata_report=None,
    )
    rendered = render_site_manifest_json(manifest).lower()
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
