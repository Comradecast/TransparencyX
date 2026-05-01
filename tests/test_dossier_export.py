import json
import sys
from pathlib import Path

import pytest

from transparencyx.dossier.builder import build_member_dossier_from_profile
from transparencyx.dossier.export import (
    build_dossier_index,
    dossier_filename,
    render_dossier_index_json,
    render_member_dossier_json,
    write_dossier_index_json,
    write_member_dossiers_json,
    write_member_dossier_json,
)
from transparencyx.dossier.schema import create_empty_member_dossier


def test_render_member_dossier_json_pretty_output():
    dossier = create_empty_member_dossier("nancy-pelosi", "Nancy Pelosi")

    rendered = render_member_dossier_json(dossier)

    assert rendered.startswith("{\n")
    assert '  "identity": {' in rendered
    assert '    "member_id": "nancy-pelosi",' in rendered
    assert json.loads(rendered)["identity"]["full_name"] == "Nancy Pelosi"


def test_render_member_dossier_json_ends_with_newline():
    dossier = create_empty_member_dossier("nancy-pelosi", "Nancy Pelosi")

    assert render_member_dossier_json(dossier).endswith("\n")


def test_write_creates_parent_directories(tmp_path):
    dossier = create_empty_member_dossier("nancy-pelosi", "Nancy Pelosi")
    output_path = tmp_path / "nested" / "dossiers" / "nancy-pelosi.json"

    returned_path = write_member_dossier_json(dossier, output_path)

    assert returned_path == output_path
    assert output_path.exists()
    assert json.loads(output_path.read_text(encoding="utf-8"))["identity"][
        "member_id"
    ] == "nancy-pelosi"


def test_write_overwrites_deterministically(tmp_path):
    dossier = create_empty_member_dossier("nancy-pelosi", "Nancy Pelosi")
    output_path = tmp_path / "nancy-pelosi.json"
    output_path.write_text("old content", encoding="utf-8")

    write_member_dossier_json(dossier, output_path)
    first = output_path.read_text(encoding="utf-8")
    write_member_dossier_json(dossier, output_path)
    second = output_path.read_text(encoding="utf-8")

    assert first == second
    assert first == render_member_dossier_json(dossier)


def test_batch_helper_writes_multiple_files(tmp_path):
    dossiers = [
        create_empty_member_dossier("nancy-pelosi", "Nancy Pelosi"),
        create_empty_member_dossier("jane-public", "Jane Public"),
    ]

    paths = write_member_dossiers_json(dossiers, tmp_path)

    assert paths == [
        tmp_path / "nancy-pelosi.json",
        tmp_path / "jane-public.json",
    ]
    assert json.loads(paths[0].read_text(encoding="utf-8"))["identity"][
        "full_name"
    ] == "Nancy Pelosi"
    assert json.loads(paths[1].read_text(encoding="utf-8"))["identity"][
        "full_name"
    ] == "Jane Public"


def test_batch_helper_creates_output_directory(tmp_path):
    output_dir = tmp_path / "nested" / "dossiers"
    dossier = create_empty_member_dossier("nancy-pelosi", "Nancy Pelosi")

    paths = write_member_dossiers_json([dossier], output_dir)

    assert paths == [output_dir / "nancy-pelosi.json"]
    assert paths[0].exists()


def test_batch_helper_uses_deterministic_filenames(tmp_path):
    dossiers = [
        create_empty_member_dossier("Jane Public", "Jane Public"),
        create_empty_member_dossier("Nancy Pelosi", "Nancy Pelosi"),
    ]

    paths = write_member_dossiers_json(dossiers, tmp_path)

    assert [path.name for path in paths] == [
        "jane-public.json",
        "nancy-pelosi.json",
    ]


def test_batch_helper_duplicate_filename_fails_closed(tmp_path):
    dossiers = [
        create_empty_member_dossier("Nancy Pelosi", "Nancy Pelosi"),
        create_empty_member_dossier("nancy-pelosi", "Nancy Pelosi"),
    ]

    with pytest.raises(ValueError, match="Duplicate dossier filename: nancy-pelosi.json"):
        write_member_dossiers_json(dossiers, tmp_path)

    assert list(tmp_path.glob("*.json")) == []


def test_batch_json_files_parse_correctly(tmp_path):
    dossiers = [
        build_member_dossier_from_profile({
            "member_name": "Nancy Pelosi",
            "disclosure_year": 2023,
        }),
        build_member_dossier_from_profile({
            "member_name": "Jane Public",
            "disclosure_year": 2024,
        }),
    ]

    paths = write_member_dossiers_json(dossiers, tmp_path)
    parsed = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in paths
    ]

    assert parsed[0]["financials"]["disclosure_years"] == [2023]
    assert parsed[1]["financials"]["disclosure_years"] == [2024]


def test_build_dossier_index_basic_output():
    dossiers = [
        build_member_dossier_from_profile({
            "member_id": "nancy-pelosi",
            "member_name": "Nancy Pelosi",
            "chamber": "House",
            "state": "CA",
            "district": "11",
            "party": "Democratic",
            "current_status": "current",
        })
    ]
    paths = [Path("out/dossiers/nancy-pelosi.json")]

    index = build_dossier_index(dossiers, paths)

    assert index == {
        "dossier_count": 1,
        "dossiers": [
            {
                "member_id": "nancy-pelosi",
                "full_name": "Nancy Pelosi",
                "chamber": "House",
                "state": "CA",
                "district": "11",
                "party": "Democratic",
                "current_status": "current",
                "file": "nancy-pelosi.json",
            }
        ],
    }


def test_build_dossier_index_uses_file_basename_only():
    dossier = create_empty_member_dossier("nancy-pelosi", "Nancy Pelosi")

    index = build_dossier_index(
        [dossier],
        [Path("nested/dossiers/nancy-pelosi.json")],
    )

    assert index["dossiers"][0]["file"] == "nancy-pelosi.json"


def test_build_dossier_index_preserves_order(tmp_path):
    dossiers = [
        create_empty_member_dossier("jane-public", "Jane Public"),
        create_empty_member_dossier("nancy-pelosi", "Nancy Pelosi"),
    ]
    paths = [
        tmp_path / "jane-public.json",
        tmp_path / "nancy-pelosi.json",
    ]

    index = build_dossier_index(dossiers, paths)

    assert [row["member_id"] for row in index["dossiers"]] == [
        "jane-public",
        "nancy-pelosi",
    ]
    assert [row["file"] for row in index["dossiers"]] == [
        "jane-public.json",
        "nancy-pelosi.json",
    ]


def test_build_dossier_index_length_mismatch_raises_value_error(tmp_path):
    dossier = create_empty_member_dossier("nancy-pelosi", "Nancy Pelosi")

    with pytest.raises(ValueError, match="lengths must match"):
        build_dossier_index([dossier], [])


def test_render_dossier_index_json_parseable():
    index = {
        "dossier_count": 1,
        "dossiers": [
            {
                "member_id": "nancy-pelosi",
                "full_name": "Nancy Pelosi",
                "chamber": "House",
                "state": "CA",
                "district": "11",
                "party": "Democratic",
                "file": "nancy-pelosi.json",
            }
        ],
    }

    parsed = json.loads(render_dossier_index_json(index))

    assert parsed == index


def test_render_dossier_index_json_ends_with_newline():
    assert render_dossier_index_json({"dossier_count": 0, "dossiers": []}).endswith(
        "\n"
    )


def test_write_dossier_index_json_creates_parent_dirs(tmp_path):
    output_path = tmp_path / "nested" / "index" / "index.json"
    index = {"dossier_count": 0, "dossiers": []}

    returned_path = write_dossier_index_json(index, output_path)

    assert returned_path == output_path
    assert json.loads(output_path.read_text(encoding="utf-8")) == index


def test_dossier_filename_slug_behavior():
    dossier = create_empty_member_dossier(" Nancy Pelosi ", "Nancy Pelosi")

    assert dossier_filename(dossier) == "nancy-pelosi.json"


def test_dossier_filename_fallback():
    dossier = create_empty_member_dossier("placeholder", "Placeholder")
    dossier.identity.member_id = "   "

    assert dossier_filename(dossier) == "unknown.json"


def test_cli_writes_json_file_from_validate_real_path(
    tmp_path,
    monkeypatch,
    capsys,
):
    class FakeExtraction:
        success = True
        extracted_text = "Name: Hon. Nancy Pelosi\nASSETS\nNone"
        error = None

    class FakeExtractor:
        def extract(self, pdf_path, source):
            return FakeExtraction()

    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF")
    output_dir = tmp_path / "dossiers"
    output_dir.mkdir()

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "transparencyx",
            "validate-real",
            "--pdf",
            str(pdf_path),
            "--dossier-json",
            str(output_dir),
        ],
    )
    monkeypatch.setattr("transparencyx.cli.get_registered_sources", lambda: {"house": object()})
    monkeypatch.setattr(
        "transparencyx.cli.get_extractor_for_source",
        lambda source, file_ext: FakeExtractor(),
    )
    monkeypatch.setattr(
        "transparencyx.cli.process_assets_for_disclosure",
        lambda db_path, raw_disclosure_id, politician_id, extracted_text: 0,
    )
    monkeypatch.setattr(
        "transparencyx.shape.export.build_financial_shape_export",
        lambda db_path, politician_id: {
            "politician_id": politician_id,
            "summary": {
                "asset_count": 0,
                "asset_value_min": None,
                "asset_value_max": None,
            },
            "trace": {},
        },
    )

    from transparencyx.cli import main

    main()

    captured = capsys.readouterr()
    output_path = output_dir / "nancy-pelosi.json"
    data = json.loads(output_path.read_text(encoding="utf-8"))

    assert f"Wrote member dossier JSON: {output_path}" in captured.out
    assert data["identity"]["member_id"] == "nancy-pelosi"
    assert data["identity"]["full_name"] == "Nancy Pelosi"
    assert data["financials"]["asset_count"] == 0


def test_cli_batch_dossier_export_summary_message(
    tmp_path,
    monkeypatch,
    capsys,
):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "dossiers"
    input_dir.mkdir()

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "transparencyx",
            "--batch-dossier-json",
            str(input_dir),
            "--output-dir",
            str(output_dir),
        ],
    )
    monkeypatch.setattr(
        "transparencyx.profile.batch.build_profiles_for_directory",
        lambda directory: [
            {
                "member_name": "Nancy Pelosi",
                "disclosure_year": 2023,
            },
            {
                "member_name": "Jane Public",
                "disclosure_year": 2024,
            },
        ],
    )

    from transparencyx.cli import main

    with pytest.raises(SystemExit) as exit_info:
        main()

    captured = capsys.readouterr()

    assert exit_info.value.code == 0
    assert captured.out == (
        f"Wrote member dossier JSON files: 2 to {output_dir}\n"
    )
    assert json.loads((output_dir / "nancy-pelosi.json").read_text(
        encoding="utf-8"
    ))["identity"]["full_name"] == "Nancy Pelosi"
    assert json.loads((output_dir / "jane-public.json").read_text(
        encoding="utf-8"
    ))["identity"]["full_name"] == "Jane Public"


def test_cli_batch_dossier_index_summary_message(
    tmp_path,
    monkeypatch,
    capsys,
):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "dossiers"
    index_dir = tmp_path / "manifest"
    input_dir.mkdir()
    index_dir.mkdir()

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "transparencyx",
            "--batch-dossier-json",
            str(input_dir),
            "--output-dir",
            str(output_dir),
            "--index-json",
            str(index_dir),
        ],
    )
    monkeypatch.setattr(
        "transparencyx.profile.batch.build_profiles_for_directory",
        lambda directory: [
            {
                "member_name": "Nancy Pelosi",
                "chamber": "House",
                "state": "CA",
            },
        ],
    )

    from transparencyx.cli import main

    with pytest.raises(SystemExit) as exit_info:
        main()

    captured = capsys.readouterr()
    index_path = index_dir / "index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))

    assert exit_info.value.code == 0
    assert captured.out == (
        f"Wrote member dossier JSON files: 1 to {output_dir}\n"
        f"Wrote dossier index JSON: {index_path}\n"
    )
    assert index == {
        "dossier_count": 1,
        "dossiers": [
            {
                "member_id": "nancy-pelosi",
                "full_name": "Nancy Pelosi",
                "chamber": "House",
                "state": "CA",
                "district": None,
                "party": None,
                "current_status": None,
                "file": "nancy-pelosi.json",
            }
        ],
    }


def test_json_is_parseable():
    dossier = build_member_dossier_from_profile({
        "member_name": "Nancy Pelosi",
        "disclosure_year": 2023,
    })

    data = json.loads(render_member_dossier_json(dossier))

    assert data["identity"]["member_id"] == "nancy-pelosi"
    assert data["financials"]["disclosure_years"] == [2023]


def test_forbidden_language_absent():
    dossier = create_empty_member_dossier("nancy-pelosi", "Nancy Pelosi")
    index = build_dossier_index([dossier], [Path("nancy-pelosi.json")])
    rendered = (
        render_member_dossier_json(dossier)
        + render_dossier_index_json(index)
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
