import json
import sys

import pytest

from transparencyx.dossier.validate_site import validate_dossier_site


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
    assert (output_dir / "build_manifest.json").exists()
    assert (output_dir / "README.txt").exists()
    assert not (output_dir / "metadata_coverage.json").exists()
    assert not (output_dir / "committee_coverage.json").exists()
    assert captured.out == "\n".join([
        f"Wrote member dossier JSON files: 2 to {output_dir}",
        f"Wrote dossier index JSON: {output_dir / 'index.json'}",
        f"Wrote member dossier HTML files: 2 to {output_dir}",
        f"Wrote dossier HTML index: {output_dir / 'index.html'}",
        f"Wrote site build manifest JSON: {output_dir / 'build_manifest.json'}",
        f"Wrote generated site README: {output_dir / 'README.txt'}",
        f"Validation hint: python -m transparencyx --validate-dossier-site {output_dir}",
        "",
    ])


def test_documented_local_demo_site_build_path(tmp_path, monkeypatch, capsys):
    output_dir = tmp_path / "site"
    _patch_profiles(
        monkeypatch,
        profiles=[
            {
                "member_name": "Thom Tillis",
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
            "data/raw",
            "--output-dir",
            str(output_dir),
            "--use-default-member-metadata",
        ],
    )

    from transparencyx.cli import main

    with pytest.raises(SystemExit) as exit_info:
        main()

    captured = capsys.readouterr()
    html_pages = [
        path for path in output_dir.glob("*.html")
        if path.name != "index.html"
    ]
    json_pages = [
        path for path in output_dir.glob("*.json")
        if path.name not in {
            "index.json",
            "build_manifest.json",
            "metadata_coverage.json",
            "committee_coverage.json",
        }
    ]
    validation = validate_dossier_site(output_dir)

    assert exit_info.value.code == 0
    assert (output_dir / "index.html").exists()
    assert (output_dir / "index.json").exists()
    assert (output_dir / "build_manifest.json").exists()
    assert (output_dir / "README.txt").exists()
    assert html_pages
    assert json_pages
    assert validation["passed"] is True
    assert f"Validation hint: python -m transparencyx --validate-dossier-site {output_dir}" in captured.out


def test_nc_demo_site_build_produces_valid_seeded_delegation(tmp_path, monkeypatch, capsys):
    output_dir = tmp_path / "site"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "transparencyx",
            "--build-nc-demo-site",
            "--output-dir",
            str(output_dir),
        ],
    )

    from transparencyx.cli import main

    with pytest.raises(SystemExit) as exit_info:
        main()

    captured = capsys.readouterr()
    index = json.loads((output_dir / "index.json").read_text(encoding="utf-8"))
    validation = validate_dossier_site(output_dir)
    html_pages = [
        path for path in output_dir.glob("*.html")
        if path.name != "index.html"
    ]
    json_pages = [
        path for path in output_dir.glob("*.json")
        if path.name not in {
            "index.json",
            "build_manifest.json",
            "metadata_coverage.json",
            "committee_coverage.json",
        }
    ]

    assert exit_info.value.code == 0
    assert index["dossier_count"] == 16
    assert len(html_pages) == 16
    assert len(json_pages) == 16
    assert validation["passed"] is True
    assert "Built NC delegation demo fixture site:" in captured.out
    assert (output_dir / "metadata_coverage.json").exists()
    assert (output_dir / "committee_coverage.json").exists()


def test_nc_demo_site_index_rows_include_house_and_senate_metadata(
    tmp_path,
    monkeypatch,
):
    output_dir = tmp_path / "site"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "transparencyx",
            "--build-nc-demo-site",
            "--output-dir",
            str(output_dir),
        ],
    )

    from transparencyx.cli import main

    with pytest.raises(SystemExit):
        main()

    index = json.loads((output_dir / "index.json").read_text(encoding="utf-8"))
    rows_by_id = {
        row["member_id"]: row
        for row in index["dossiers"]
    }

    assert rows_by_id["alma-s-adams"] == {
        "member_id": "alma-s-adams",
        "full_name": "Alma S. Adams",
        "chamber": "House",
        "state": "NC",
        "district": "12",
        "party": "Democratic",
        "current_status": "current",
        "file": "alma-s-adams.json",
    }
    assert rows_by_id["thom-tillis"] == {
        "member_id": "thom-tillis",
        "full_name": "Thom Tillis",
        "chamber": "Senate",
        "state": "NC",
        "district": None,
        "party": "Republican",
        "current_status": "current",
        "file": "thom-tillis.json",
    }


def test_nc_demo_site_index_summary_counts(tmp_path, monkeypatch):
    output_dir = tmp_path / "site"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "transparencyx",
            "--build-nc-demo-site",
            "--output-dir",
            str(output_dir),
        ],
    )

    from transparencyx.cli import main

    with pytest.raises(SystemExit):
        main()

    html = (output_dir / "index.html").read_text(encoding="utf-8")

    assert "<h2>Dataset Summary</h2>" in html
    assert "<dt>Total dossiers</dt><dd>16</dd>" in html
    assert "<dt>House</dt><dd>14</dd>" in html
    assert "<dt>Senate</dt><dd>2</dd>" in html
    assert "<dt>States</dt><dd>NC</dd>" in html
    assert "<dt>Current members</dt><dd>16</dd>" in html


def test_nc_demo_site_index_json_order_matches_html_order(tmp_path, monkeypatch):
    output_dir = tmp_path / "site"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "transparencyx",
            "--build-nc-demo-site",
            "--output-dir",
            str(output_dir),
        ],
    )

    from transparencyx.cli import main

    with pytest.raises(SystemExit):
        main()

    index = json.loads((output_dir / "index.json").read_text(encoding="utf-8"))
    html = (output_dir / "index.html").read_text(encoding="utf-8")
    files = [row["file"].replace(".json", ".html") for row in index["dossiers"]]

    assert files[:4] == [
        "donald-g-davis.html",
        "deborah-k-ross.html",
        "gregory-f-murphy.html",
        "valerie-p-foushee.html",
    ]
    assert files[-2:] == ["ted-budd.html", "thom-tillis.html"]
    html_positions = [html.index(filename) for filename in files]
    assert html_positions == sorted(html_positions)


def test_nc_demo_site_member_pages_render_metadata_only_status(tmp_path, monkeypatch):
    output_dir = tmp_path / "site"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "transparencyx",
            "--build-nc-demo-site",
            "--output-dir",
            str(output_dir),
        ],
    )

    from transparencyx.cli import main

    with pytest.raises(SystemExit):
        main()

    html = (output_dir / "alma-s-adams.html").read_text(encoding="utf-8")

    assert "<h2>Disclosure Data Status</h2>" in html
    assert (
        "This demo dossier was generated from seeded member metadata. "
        "No parsed financial disclosure PDF is attached to this dossier."
    ) in html
    assert validate_dossier_site(output_dir)["passed"] is True


def test_nc_demo_site_member_pages_render_no_parsed_financial_summary(
    tmp_path,
    monkeypatch,
):
    output_dir = tmp_path / "site"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "transparencyx",
            "--build-nc-demo-site",
            "--output-dir",
            str(output_dir),
        ],
    )

    from transparencyx.cli import main

    with pytest.raises(SystemExit):
        main()

    html = (output_dir / "alma-s-adams.html").read_text(encoding="utf-8")

    assert "<h2>Financial Summary</h2>" in html
    assert "No parsed financial disclosure data is attached to this dossier." in html


def test_nc_demo_site_readme_labels_fixture_dataset(tmp_path, monkeypatch):
    output_dir = tmp_path / "site"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "transparencyx",
            "--build-nc-demo-site",
            "--output-dir",
            str(output_dir),
        ],
    )

    from transparencyx.cli import main

    with pytest.raises(SystemExit):
        main()

    readme = (output_dir / "README.txt").read_text(encoding="utf-8")

    assert "Demo Dataset:" in readme
    assert "NC delegation fixture built from data/seed/member_metadata_seed.csv" in readme
    assert "Open index.html in a browser" in readme


def test_nc_demo_site_generation_is_deterministic(tmp_path, monkeypatch):
    output_dir = tmp_path / "site"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "transparencyx",
            "--build-nc-demo-site",
            "--output-dir",
            str(output_dir),
        ],
    )

    from transparencyx.cli import main

    with pytest.raises(SystemExit):
        main()

    first = {
        path.relative_to(output_dir).as_posix(): path.read_text(encoding="utf-8")
        for path in sorted(output_dir.glob("*"))
        if path.is_file()
    }

    with pytest.raises(SystemExit):
        main()

    second = {
        path.relative_to(output_dir).as_posix(): path.read_text(encoding="utf-8")
        for path in sorted(output_dir.glob("*"))
        if path.is_file()
    }

    assert second == first


def test_nc_demo_site_removes_stale_generated_site_files(tmp_path, monkeypatch):
    output_dir = tmp_path / "site"
    output_dir.mkdir()
    (output_dir / "nancy-pelosi.html").write_text("stale", encoding="utf-8")
    (output_dir / "nancy-pelosi.json").write_text("{}", encoding="utf-8")
    (output_dir / "notes.txt").write_text("keep", encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "transparencyx",
            "--build-nc-demo-site",
            "--output-dir",
            str(output_dir),
        ],
    )

    from transparencyx.cli import main

    with pytest.raises(SystemExit):
        main()

    assert not (output_dir / "nancy-pelosi.html").exists()
    assert not (output_dir / "nancy-pelosi.json").exists()
    assert (output_dir / "notes.txt").read_text(encoding="utf-8") == "keep"


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
            "member_id,full_name,chamber,committee_assignments",
            "nancy-pelosi,Nancy Pelosi,House,Committee on Rules",
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
    committee_report = json.loads((output_dir / "committee_coverage.json").read_text(
        encoding="utf-8"
    ))
    manifest = json.loads((output_dir / "build_manifest.json").read_text(
        encoding="utf-8"
    ))

    assert exit_info.value.code == 0
    assert report["matched_member_ids"] == ["nancy-pelosi"]
    assert report["unmatched_member_ids"] == ["jane-public"]
    assert committee_report["rows_with_committees"] == 1
    assert committee_report["rows_without_committees"] == 1
    assert committee_report["member_ids_with_committees"] == ["nancy-pelosi"]
    assert manifest["counts"]["committee_rows_with_assignments"] == 1
    assert manifest["counts"]["committee_rows_without_assignments"] == 1
    assert manifest["artifacts"]["committee_coverage"] == "committee_coverage.json"
    assert f"Wrote metadata coverage JSON: {output_dir / 'metadata_coverage.json'}" in captured.out
    assert f"Wrote committee coverage JSON: {output_dir / 'committee_coverage.json'}" in captured.out


def test_site_build_with_default_member_metadata(tmp_path, monkeypatch, capsys):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "site"
    input_dir.mkdir()
    _patch_profiles(
        monkeypatch,
        profiles=[
            {
                "member_name": "Thom Tillis",
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
            "--use-default-member-metadata",
        ],
    )

    from transparencyx.cli import main

    with pytest.raises(SystemExit) as exit_info:
        main()

    captured = capsys.readouterr()
    dossier = json.loads((output_dir / "thom-tillis.json").read_text(encoding="utf-8"))
    manifest = json.loads((output_dir / "build_manifest.json").read_text(
        encoding="utf-8"
    ))
    coverage = json.loads((output_dir / "metadata_coverage.json").read_text(
        encoding="utf-8"
    ))
    committee_coverage = json.loads((output_dir / "committee_coverage.json").read_text(
        encoding="utf-8"
    ))

    assert exit_info.value.code == 0
    assert "Loaded member metadata records: " in captured.out
    assert dossier["identity"]["chamber"] == "Senate"
    assert dossier["identity"]["state"] == "NC"
    assert manifest["options"]["member_metadata"] is True
    assert coverage["matched_member_ids"] == ["thom-tillis"]
    assert committee_coverage["member_ids_without_committees"] == ["thom-tillis"]


def test_site_build_default_and_explicit_metadata_fail_closed(
    tmp_path,
    monkeypatch,
    capsys,
):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "site"
    metadata_path = tmp_path / "metadata.csv"
    input_dir.mkdir()
    metadata_path.write_text(
        "member_id,full_name\nnancy-pelosi,Nancy Pelosi\n",
        encoding="utf-8",
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
            "--member-metadata",
            str(metadata_path),
            "--use-default-member-metadata",
        ],
    )

    from transparencyx.cli import main

    with pytest.raises(SystemExit) as exit_info:
        main()

    captured = capsys.readouterr()

    assert exit_info.value.code == 1
    assert captured.out == (
        "Use either --member-metadata or --use-default-member-metadata, not both.\n"
    )
    assert not output_dir.exists()


def test_default_metadata_flag_outside_site_build_fails_closed(
    monkeypatch,
    capsys,
):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "transparencyx",
            "--batch-profile",
            "input",
            "--use-default-member-metadata",
        ],
    )

    from transparencyx.cli import main

    with pytest.raises(SystemExit) as exit_info:
        main()

    captured = capsys.readouterr()

    assert exit_info.value.code == 1
    assert captured.out == (
        "Default member metadata can only be used with dossier site builds.\n"
    )


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
    assert not (output_dir / "committee_coverage.json").exists()


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
