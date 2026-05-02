import json
from pathlib import Path

from transparencyx.acquisition.senate import (
    SENATE_EXPECTED_SOURCE_KEYS,
    build_senate_acquisition_plan,
    load_senate_expected_sources,
    senate_manifest_source_ids,
    validate_senate_pdf_source,
)


VALID_PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF\n"
SENATE_MANIFEST_PATH = Path(
    "docs/acquisition_plans/nc_2023_senate_expected_sources.json"
)
SENATE_PLAN_PATH = Path(
    "docs/acquisition_plans/nc_2023_senate_acquisition_plan.json"
)


def _senate_manifest(source_id="SENATE-NC-2023-BUDD"):
    local_path = (
        f"data/raw/senate/2023/{source_id}.pdf"
        if source_id is not None
        else None
    )
    return {
        "manifest_type": "senate_expected_sources",
        "state": "NC",
        "year": 2023,
        "entries": [
            {
                "member_slug": "ted-budd",
                "full_name": "Ted Budd",
                "chamber": "Senate",
                "state": "NC",
                "year": 2023,
                "source_id": source_id,
                "source_url": "https://efdsearch.senate.gov/search/view/paper/test/"
                if source_id is not None
                else None,
                "local_path": local_path,
                "source_authority": "Official Senate financial disclosure system",
                "acquisition_status": "identified"
                if source_id is not None
                else "pending",
                "notes": None,
            }
        ],
    }


def test_nc_senate_expected_manifest_exists_with_pending_entries():
    manifest = load_senate_expected_sources(SENATE_MANIFEST_PATH)

    assert manifest["manifest_type"] == "senate_expected_sources"
    assert manifest["state"] == "NC"
    assert manifest["year"] == 2023
    assert [entry["member_slug"] for entry in manifest["entries"]] == [
        "ted-budd",
        "thom-tillis",
    ]
    for entry in manifest["entries"]:
        assert set(entry) == SENATE_EXPECTED_SOURCE_KEYS
        assert entry["chamber"] == "Senate"
        assert entry["source_id"] is None
        assert entry["source_url"] is None
        assert entry["local_path"] is None
        assert entry["acquisition_status"] == "pending"


def test_nc_senate_acquisition_plan_reports_missing_not_parsing_failure():
    plan = json.loads(SENATE_PLAN_PATH.read_text(encoding="utf-8"))

    assert plan["plan_type"] == "senate_acquisition_plan"
    assert plan["total_expected"] == 2
    assert plan["total_acquired"] == 0
    assert plan["total_missing"] == 2
    assert plan["total_pending"] == 2
    assert plan["total_ambiguous"] == 0
    assert {
        entry["acquisition_status"]
        for entry in plan["entries"]
    } == {"pending"}
    assert {
        entry["acquired"]
        for entry in plan["entries"]
    } == {False}


def test_house_and_senate_acquisition_accounting_stay_separate():
    senate_plan = json.loads(SENATE_PLAN_PATH.read_text(encoding="utf-8"))
    house_index_plan = json.loads(
        Path("docs/acquisition_plans/nc_2023_index_acquisition_manifest.json")
        .read_text(encoding="utf-8")
    )

    assert senate_plan["plan_type"] == "senate_acquisition_plan"
    assert senate_plan["total_expected"] == 2
    assert house_index_plan["total_expected"] == 16
    assert all(
        entry["chamber"] == "Senate"
        for entry in senate_plan["entries"]
    )
    assert any(
        entry["chamber"] == "House"
        for entry in house_index_plan["entries"]
    )


def test_senate_acquisition_plan_can_mark_manifest_backed_pdf_acquired(tmp_path):
    source_id = "SENATE-NC-2023-BUDD"
    manifest = _senate_manifest(source_id)
    pdf_path = tmp_path / "data" / "raw" / "senate" / "2023" / f"{source_id}.pdf"
    pdf_path.parent.mkdir(parents=True)
    pdf_path.write_bytes(VALID_PDF_BYTES)
    manifest["entries"][0]["local_path"] = pdf_path.as_posix()

    plan = build_senate_acquisition_plan(
        manifest,
        raw_root=tmp_path / "data" / "raw" / "senate",
    )

    assert plan["total_expected"] == 1
    assert plan["total_acquired"] == 1
    assert plan["total_missing"] == 0
    assert plan["entries"][0]["acquired"] is True


def test_senate_pdf_must_live_under_senate_raw_path(tmp_path):
    source_id = "SENATE-NC-2023-BUDD"
    manifest_path = tmp_path / "senate.json"
    wrong_path = tmp_path / "data" / "raw" / "house" / "2023" / f"{source_id}.pdf"
    wrong_path.parent.mkdir(parents=True)
    wrong_path.write_bytes(VALID_PDF_BYTES)
    manifest = _senate_manifest(source_id)
    manifest["entries"][0]["local_path"] = wrong_path.as_posix()
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    assert validate_senate_pdf_source(
        wrong_path,
        source_id,
        manifest_path,
    ) is False


def test_senate_pdf_requires_known_source_id_and_exact_filename(tmp_path):
    source_id = "SENATE-NC-2023-BUDD"
    manifest_path = tmp_path / "senate.json"
    pdf_path = tmp_path / "data" / "raw" / "senate" / "2023" / f"{source_id}.pdf"
    pdf_path.parent.mkdir(parents=True)
    pdf_path.write_bytes(VALID_PDF_BYTES)
    manifest = _senate_manifest(source_id)
    manifest["entries"][0]["local_path"] = pdf_path.as_posix()
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    assert validate_senate_pdf_source(pdf_path, source_id, manifest_path) is True
    assert validate_senate_pdf_source(
        pdf_path,
        "SENATE-NC-2023-TILLIS",
        manifest_path,
    ) is False


def test_senate_pdf_rejects_unknown_filename_even_when_pdf_is_valid(tmp_path):
    source_id = "SENATE-NC-2023-BUDD"
    unknown_id = "SENATE-NC-2023-UNKNOWN"
    manifest_path = tmp_path / "senate.json"
    pdf_path = (
        tmp_path / "data" / "raw" / "senate" / "2023" / f"{unknown_id}.pdf"
    )
    pdf_path.parent.mkdir(parents=True)
    pdf_path.write_bytes(VALID_PDF_BYTES)
    manifest_path.write_text(json.dumps(_senate_manifest(source_id)), encoding="utf-8")

    assert validate_senate_pdf_source(pdf_path, unknown_id, manifest_path) is False


def test_senate_source_id_matching_is_explicit_not_fuzzy():
    manifest = _senate_manifest("SENATE-NC-2023-THOM-TILLIS")

    assert "SENATE-NC-2023-TILLIS" not in senate_manifest_source_ids(manifest)
    assert "SENATE-NC-2023-THOM-TILLIS" in senate_manifest_source_ids(manifest)
