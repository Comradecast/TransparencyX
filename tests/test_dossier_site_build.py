import json
import sys

import pytest


def _patch_profiles(monkeypatch, profiles=None):
    monkeypatch.setattr(
        "transparencyx.profile.batch.build_profiles_for_directory",
        lambda directory: profiles or [
            {
                "member_name": "Nancy Pelosi",
                "chamber": "House",
                "state": "CA",
                "district": "11",
                "party": "Democratic",
                "disclosure_year": 2023,
            },
            {
                "member_name": "Jane Public",
                "chamber": "Senate",
                "state": "WA",
                "disclosure_year": 2024,
            },
        ],
    )


def test_site_build_produces_expected_files(tmp_path, monkeypatch, capsys):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "site"
    input_dir.mkdir()
    _patch_profiles(monkeypatch)
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

    assert exit_info.value.code == 0
    assert (output_dir / "nancy-pelosi.json").exists()
    assert (output_dir / "jane-public.json").exists()
    assert (output_dir / "nancy-pelosi.html").exists()
    assert (output_dir / "jane-public.html").exists()
    assert (output_dir / "index.json").exists()
    assert (output_dir / "index.html").exists()
    assert not (output_dir / "metadata_coverage.json").exists()
    assert captured.out == "\n".join([
        f"Wrote member dossier JSON files: 2 to {output_dir}",
        f"Wrote dossier index JSON: {output_dir / 'index.json'}",
        f"Wrote member dossier HTML files: 2 to {output_dir}",
        f"Wrote dossier HTML index: {output_dir / 'index.html'}",
        "",
    ])


def test_site_build_json_files_exist_and_parse(tmp_path, monkeypatch):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "site"
    input_dir.mkdir()
    _patch_profiles(monkeypatch)
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

    with pytest.raises(SystemExit):
        main()

    dossier = json.loads((output_dir / "nancy-pelosi.json").read_text(encoding="utf-8"))
    index = json.loads((output_dir / "index.json").read_text(encoding="utf-8"))

    assert dossier["identity"]["member_id"] == "nancy-pelosi"
    assert index["dossier_count"] == 2


def test_site_build_html_files_exist(tmp_path, monkeypatch):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "site"
    input_dir.mkdir()
    _patch_profiles(monkeypatch)
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

    with pytest.raises(SystemExit):
        main()

    assert "Nancy Pelosi" in (output_dir / "nancy-pelosi.html").read_text(
        encoding="utf-8"
    )
    assert "TransparencyX Dossier Index" in (output_dir / "index.html").read_text(
        encoding="utf-8"
    )


def test_site_build_metadata_coverage_file_exists_when_metadata_provided(
    tmp_path,
    monkeypatch,
    capsys,
):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "site"
    metadata_path = tmp_path / "metadata.csv"
    input_dir.mkdir()
    metadata_path.write_text(
        "\n".join([
            "member_id,full_name,chamber",
            "nancy-pelosi,Nancy Pelosi,House",
        ]),
        encoding="utf-8",
    )
    _patch_profiles(monkeypatch)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "transparencyx",
            "--build-dossier-site",
            str(input_dir),
            "--output-dir",
            str(output_dir),
            "--member-metadata",
            str(metadata_path),
        ],
    )

    from transparencyx.cli import main

    with pytest.raises(SystemExit) as exit_info:
        main()

    captured = capsys.readouterr()
    report = json.loads((output_dir / "metadata_coverage.json").read_text(
        encoding="utf-8"
    ))

    assert exit_info.value.code == 0
    assert report["matched_member_ids"] == ["nancy-pelosi"]
    assert report["unmatched_member_ids"] == ["jane-public"]
    assert f"Wrote metadata coverage JSON: {output_dir / 'metadata_coverage.json'}" in captured.out


def test_site_build_no_metadata_coverage_file_without_metadata(tmp_path, monkeypatch):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "site"
    input_dir.mkdir()
    _patch_profiles(monkeypatch)
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

    with pytest.raises(SystemExit):
        main()

    assert not (output_dir / "metadata_coverage.json").exists()


def test_site_build_missing_output_dir_fails_closed(tmp_path, monkeypatch, capsys):
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "transparencyx",
            "--build-dossier-site",
            str(input_dir),
        ],
    )

    from transparencyx.cli import main

    with pytest.raises(SystemExit) as exit_info:
        main()

    captured = capsys.readouterr()

    assert exit_info.value.code == 2
    assert "--output-dir is required" in captured.err


def test_site_build_invalid_metadata_fails_closed(tmp_path, monkeypatch, capsys):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "site"
    metadata_path = tmp_path / "metadata.csv"
    input_dir.mkdir()
    metadata_path.write_text(
        "\n".join([
            "member_id,full_name",
            "nancy-pelosi,",
        ]),
        encoding="utf-8",
    )
    _patch_profiles(monkeypatch)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "transparencyx",
            "--build-dossier-site",
            str(input_dir),
            "--output-dir",
            str(output_dir),
            "--member-metadata",
            str(metadata_path),
        ],
    )

    from transparencyx.cli import main

    with pytest.raises(SystemExit) as exit_info:
        main()

    captured = capsys.readouterr()

    assert exit_info.value.code == 1
    assert "full_name is required" in captured.out
    assert not output_dir.exists()


def test_site_build_candidate_audit_without_exposure_fails_closed(
    tmp_path,
    monkeypatch,
    capsys,
):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "site"
    input_dir.mkdir()
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "transparencyx",
            "--build-dossier-site",
            str(input_dir),
            "--output-dir",
            str(output_dir),
            "--recipient-candidate-audit",
        ],
    )

    from transparencyx.cli import main

    with pytest.raises(SystemExit) as exit_info:
        main()

    captured = capsys.readouterr()

    assert exit_info.value.code == 0
    assert captured.out == (
        "Recipient candidate audit requires fetched federal award exposure results.\n"
    )
    assert not output_dir.exists()


def test_site_build_forbidden_language_absent(tmp_path, monkeypatch):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "site"
    input_dir.mkdir()
    _patch_profiles(monkeypatch)
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

    with pytest.raises(SystemExit):
        main()

    combined = "\n".join(
        path.read_text(encoding="utf-8").lower()
        for path in output_dir.glob("*")
        if path.is_file()
    )
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
