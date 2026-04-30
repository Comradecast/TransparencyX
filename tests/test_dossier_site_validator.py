import json
import sys

import pytest

from transparencyx.dossier.validate_site import (
    render_dossier_site_validation,
    validate_dossier_site,
)


def _write_valid_site(path):
    path.mkdir()
    (path / "nancy-pelosi.json").write_text("{}", encoding="utf-8")
    (path / "nancy-pelosi.html").write_text("<!doctype html>\n", encoding="utf-8")
    (path / "index.json").write_text(
        json.dumps({
            "dossier_count": 1,
            "dossiers": [
                {
                    "member_id": "nancy-pelosi",
                    "full_name": "Nancy Pelosi",
                    "file": "nancy-pelosi.json",
                }
            ],
        }),
        encoding="utf-8",
    )
    (path / "index.html").write_text(
        '<!doctype html><a href="nancy-pelosi.html">Nancy Pelosi</a>',
        encoding="utf-8",
    )
    (path / "build_manifest.json").write_text(
        json.dumps({
            "build_type": "dossier_site",
            "counts": {
                "json_dossiers": 1,
                "html_dossiers": 1,
            },
            "artifacts": {
                "json_index": "index.json",
                "html_index": "index.html",
                "metadata_coverage": None,
                "dossier_json_files": ["nancy-pelosi.json"],
                "dossier_html_files": ["nancy-pelosi.html"],
            },
        }),
        encoding="utf-8",
    )
    (path / "README.txt").write_text("Generated artifacts\n", encoding="utf-8")


def test_valid_site_passes(tmp_path):
    site = tmp_path / "site"
    _write_valid_site(site)

    report = validate_dossier_site(site)

    assert report["passed"] is True
    assert report["json_dossiers"] == 1
    assert report["html_dossiers"] == 1
    assert report["checked_index_json_files"] == 1
    assert report["checked_html_links"] == 1
    assert report["errors"] == []


def test_missing_required_file_fails(tmp_path):
    site = tmp_path / "site"
    _write_valid_site(site)
    (site / "README.txt").unlink()

    report = validate_dossier_site(site)

    assert report["passed"] is False
    assert report["required_files"]["README.txt"] is False
    assert "missing required file: README.txt" in report["errors"]


def test_invalid_index_json_fails(tmp_path):
    site = tmp_path / "site"
    _write_valid_site(site)
    (site / "index.json").write_text("{", encoding="utf-8")

    report = validate_dossier_site(site)

    assert report["passed"] is False
    assert "index.json is not valid JSON" in report["errors"]


def test_index_json_missing_referenced_file_fails(tmp_path):
    site = tmp_path / "site"
    _write_valid_site(site)
    (site / "nancy-pelosi.json").unlink()

    report = validate_dossier_site(site)

    assert report["passed"] is False
    assert "index.json references missing file: nancy-pelosi.json" in report["errors"]


def test_duplicate_index_json_file_reference_fails(tmp_path):
    site = tmp_path / "site"
    _write_valid_site(site)
    index = json.loads((site / "index.json").read_text(encoding="utf-8"))
    index["dossiers"].append(index["dossiers"][0])
    (site / "index.json").write_text(json.dumps(index), encoding="utf-8")

    report = validate_dossier_site(site)

    assert report["passed"] is False
    assert "index.json duplicate dossier file reference: nancy-pelosi.json" in report["errors"]
    assert report["checked_index_json_files"] == 2


def test_broken_html_link_fails(tmp_path):
    site = tmp_path / "site"
    _write_valid_site(site)
    (site / "index.html").write_text(
        '<a href="nancy-pelosi.html">ok</a><a href="missing.html">missing</a>',
        encoding="utf-8",
    )

    report = validate_dossier_site(site)

    assert report["passed"] is False
    assert "index.html references missing file: missing.html" in report["errors"]
    assert report["checked_html_links"] == 2


def test_invalid_build_manifest_json_fails(tmp_path):
    site = tmp_path / "site"
    _write_valid_site(site)
    (site / "build_manifest.json").write_text("{", encoding="utf-8")

    report = validate_dossier_site(site)

    assert report["passed"] is False
    assert "build_manifest.json is not valid JSON" in report["errors"]
    assert report["json_dossiers"] == 0
    assert report["html_dossiers"] == 0


def test_manifest_listed_artifact_missing_fails(tmp_path):
    site = tmp_path / "site"
    _write_valid_site(site)
    (site / "nancy-pelosi.html").unlink()

    report = validate_dossier_site(site)

    assert report["passed"] is False
    assert "build_manifest.json references missing file: nancy-pelosi.html" in report["errors"]


def test_metadata_coverage_json_invalid_fails(tmp_path):
    site = tmp_path / "site"
    _write_valid_site(site)
    manifest = json.loads((site / "build_manifest.json").read_text(encoding="utf-8"))
    manifest["artifacts"]["metadata_coverage"] = "metadata_coverage.json"
    (site / "build_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (site / "metadata_coverage.json").write_text("{", encoding="utf-8")

    report = validate_dossier_site(site)

    assert report["passed"] is False
    assert "metadata_coverage.json is not valid JSON" in report["errors"]


def test_render_pass():
    report = {
        "passed": True,
        "json_dossiers": 2,
        "html_dossiers": 2,
        "checked_index_json_files": 2,
        "checked_html_links": 2,
        "errors": [],
    }

    assert render_dossier_site_validation(report) == "\n".join([
        "Site Validation: PASS",
        "- json dossiers: 2",
        "- html dossiers: 2",
        "- index.json dossier files checked: 2",
        "- index.html links checked: 2",
        "",
    ])


def test_render_fail_with_errors():
    report = {
        "passed": False,
        "json_dossiers": 2,
        "html_dossiers": 1,
        "checked_index_json_files": 2,
        "checked_html_links": 2,
        "errors": [
            "missing required file: README.txt",
            "index.json references missing file: jane-public.json",
        ],
    }

    assert render_dossier_site_validation(report) == "\n".join([
        "Site Validation: FAIL",
        "- json dossiers: 2",
        "- html dossiers: 1",
        "- index.json dossier files checked: 2",
        "- index.html links checked: 2",
        "",
        "errors:",
        "- missing required file: README.txt",
        "- index.json references missing file: jane-public.json",
        "",
    ])


def test_cli_validation_command(tmp_path, monkeypatch, capsys):
    site = tmp_path / "site"
    _write_valid_site(site)
    monkeypatch.setattr(
        sys,
        "argv",
        ["transparencyx", "--validate-dossier-site", str(site)],
    )

    from transparencyx.cli import main

    with pytest.raises(SystemExit) as exit_info:
        main()

    captured = capsys.readouterr()

    assert exit_info.value.code == 0
    assert "Site Validation: PASS\n" in captured.out


def test_validator_does_not_create_or_modify_files(tmp_path):
    site = tmp_path / "site"
    _write_valid_site(site)
    before = {
        path.name: path.read_text(encoding="utf-8")
        for path in site.iterdir()
        if path.is_file()
    }

    validate_dossier_site(site)

    after = {
        path.name: path.read_text(encoding="utf-8")
        for path in site.iterdir()
        if path.is_file()
    }
    assert after == before


def test_forbidden_language_absent(tmp_path):
    site = tmp_path / "site"
    _write_valid_site(site)
    rendered = render_dossier_site_validation(validate_dossier_site(site)).lower()
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
