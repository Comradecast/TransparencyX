import json
import sys
from pathlib import Path

import pytest

from transparencyx.dossier.manifest import (
    build_site_manifest,
    render_site_manifest_json,
    write_site_manifest_json,
)


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
