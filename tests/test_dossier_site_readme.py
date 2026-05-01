import sys

import pytest

from transparencyx.dossier.readme import render_site_readme, write_site_readme


def test_render_contains_required_artifact_names():
    readme = render_site_readme()

    assert "index.html" in readme
    assert "index.json" in readme
    assert "build_manifest.json" in readme
    assert "metadata_coverage.json" in readme
    assert "Individual .json files" in readme
    assert "Individual .html files" in readme


def test_render_explains_how_to_open_site():
    readme = render_site_readme()

    assert "Open index.html in a browser" in readme


def test_render_explains_recipient_candidates_review_only():
    readme = render_site_readme()

    assert "Recipient candidate rows are review-only" in readme
    assert "not counted as exposure" in readme


def test_render_explains_no_accusations_or_legal_conclusions():
    readme = render_site_readme()

    assert "does not make accusations or legal conclusions" in readme


def test_render_ends_with_newline():
    assert render_site_readme().endswith("\n")


def test_write_creates_readme_txt(tmp_path):
    path = write_site_readme(tmp_path / "site")

    assert path == tmp_path / "site" / "README.txt"
    assert path.exists()
    assert path.read_text(encoding="utf-8") == render_site_readme()


def test_site_build_creates_readme_txt(tmp_path, monkeypatch, capsys):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "site"
    input_dir.mkdir()
    monkeypatch.setattr(
        "transparencyx.profile.batch.build_profiles_for_directory",
        lambda directory: [{"member_name": "Nancy Pelosi"}],
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
    readme_path = output_dir / "README.txt"

    assert exit_info.value.code == 0
    assert readme_path.exists()
    assert readme_path.read_text(encoding="utf-8") == render_site_readme()
    assert f"Wrote generated site README: {readme_path}" in captured.out


def test_forbidden_language_absent():
    readme = render_site_readme().lower()
    restricted_terms = [
        "cor" + "ruption",
        "self-" + "dealing",
        "insider trading " + "confirmed",
        "conflict " + "confirmed",
        "mis" + "conduct",
        "sus" + "picious",
    ]

    for term in restricted_terms:
        assert term not in readme
