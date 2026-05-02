import json
from pathlib import Path

from transparencyx.acquisition.senate import (
    SENATE_EXPECTED_SOURCE_KEYS,
    SENATE_METADATA_INDEX_KEYS,
    build_senate_acquisition_plan,
    build_senate_metadata_index,
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
SENATE_METADATA_INDEX_PATH = Path("docs/senate_metadata_index.json")


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
                "display_name": "Budd, Ted (Senator)",
                "chamber": "Senate",
                "state": "NC",
                "year": 2023,
                "filing_type": "Annual Report for CY 2023",
                "filing_date": "2024-08-13",
                "source_id": source_id,
                "source_url": "https://efdsearch.senate.gov/search/view/paper/test/"
                if source_id is not None
                else None,
                "pdf_url": None,
                "local_path": local_path,
                "source_authority": "United States Senate eFD",
                "source_authority_url": "https://efdsearch.senate.gov/",
                "acquisition_status": "identified"
                if source_id is not None
                else "pending",
                "notes": None,
            }
        ],
    }


def test_nc_senate_expected_manifest_exists_with_metadata_only_entries():
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
        assert entry["source_authority"] == "United States Senate eFD"
        assert entry["source_authority_url"] == "https://efdsearch.senate.gov/"
        assert entry["filing_type"] == "Annual Report for CY 2023"
        assert entry["pdf_url"] is None
        assert entry["local_path"] is None

    budd = manifest["entries"][0]
    assert budd["display_name"] == "Budd, Ted (Senator)"
    assert budd["filing_date"] == "2024-08-13"
    assert budd["source_id"] == "ac4f24bc-25fa-4821-80ca-0aa41539710d"
    assert budd["source_url"] == (
        "https://efdsearch.senate.gov/search/view/annual/"
        "ac4f24bc-25fa-4821-80ca-0aa41539710d/"
    )
    assert budd["acquisition_status"] == "resolved_record_url_only"

    tillis = manifest["entries"][1]
    assert tillis["display_name"] == "Tillis, Thom (Senator)"
    assert tillis["filing_date"] == "2024-08-09"
    assert tillis["source_id"] is None
    assert tillis["source_url"] is None
    assert tillis["acquisition_status"] == "pending_record_url"


def test_nc_senate_acquisition_plan_reports_missing_not_parsing_failure():
    plan = json.loads(SENATE_PLAN_PATH.read_text(encoding="utf-8"))

    assert plan["plan_type"] == "senate_acquisition_plan"
    assert plan["total_expected"] == 2
    assert plan["total_acquired"] == 0
    assert plan["total_missing"] == 2
    assert plan["total_resolved_record_url_only"] == 1
    assert plan["total_pending_record_url"] == 1
    assert plan["total_pdf_blocked_no_endpoint"] == 1
    assert plan["total_ambiguous"] == 0
    assert {
        entry["acquisition_status"]
        for entry in plan["entries"]
    } == {"resolved_record_url_only", "pending_record_url"}
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
    assert plan["total_pdf_blocked_no_endpoint"] == 0
    assert plan["entries"][0]["acquired"] is True


def test_senate_resolved_record_url_does_not_count_as_acquired_pdf():
    manifest = _senate_manifest("ac4f24bc-25fa-4821-80ca-0aa41539710d")
    manifest["entries"][0]["source_url"] = (
        "https://efdsearch.senate.gov/search/view/annual/"
        "ac4f24bc-25fa-4821-80ca-0aa41539710d/"
    )
    manifest["entries"][0]["local_path"] = None
    manifest["entries"][0]["acquisition_status"] = "resolved_record_url_only"

    plan = build_senate_acquisition_plan(manifest)

    assert plan["total_acquired"] == 0
    assert plan["total_missing"] == 1
    assert plan["total_resolved_record_url_only"] == 1
    assert plan["total_pdf_blocked_no_endpoint"] == 1


def test_senate_metadata_index_is_metadata_only_and_not_a_dossier():
    site_index = json.loads(Path("docs/index.json").read_text(encoding="utf-8"))
    metadata_index = json.loads(
        SENATE_METADATA_INDEX_PATH.read_text(encoding="utf-8")
    )

    assert all(
        dossier["member_id"] not in {"ted-budd", "thom-tillis"}
        for dossier in site_index["dossiers"]
    )
    assert metadata_index["manifest_type"] == "senate_metadata_index"
    assert metadata_index["total_entries"] == 2
    assert {
        entry["member_slug"]
        for entry in metadata_index["entries"]
    } == {"ted-budd", "thom-tillis"}
    assert all(
        set(entry) == SENATE_METADATA_INDEX_KEYS
        for entry in metadata_index["entries"]
    )
    assert all(
        entry["pdf_available"] is False
        for entry in metadata_index["entries"]
    )
    assert all(
        entry["parsed_financials_available"] is False
        for entry in metadata_index["entries"]
    )
    for entry in metadata_index["entries"]:
        assert entry["display_name"]
        assert entry["year"] == 2023
        assert entry["source_authority"] == "United States Senate eFD"
        assert entry["source_authority_url"] == "https://efdsearch.senate.gov/"
        assert "Print Report produced no network request" in entry["notes"]


def test_senate_metadata_flags_follow_pdf_url_and_local_path():
    manifest = _senate_manifest("SENATE-NC-2023-BUDD")
    manifest["entries"][0]["pdf_url"] = None
    manifest["entries"][0]["local_path"] = None

    index = build_senate_metadata_index(manifest)

    assert index["entries"][0]["pdf_available"] is False
    assert index["entries"][0]["parsed_financials_available"] is False


def test_browser_rendered_print_pdf_is_not_authoritative_acquisition(tmp_path):
    source_id = "ac4f24bc-25fa-4821-80ca-0aa41539710d"
    manifest_path = tmp_path / "senate.json"
    print_path = tmp_path / "data" / "raw" / "senate" / "2023" / f"{source_id}.pdf"
    print_path.parent.mkdir(parents=True)
    print_path.write_bytes(VALID_PDF_BYTES)
    manifest = _senate_manifest(source_id)
    manifest["entries"][0]["source_url"] = (
        "https://efdsearch.senate.gov/search/view/annual/"
        "ac4f24bc-25fa-4821-80ca-0aa41539710d/"
    )
    manifest["entries"][0]["pdf_url"] = None
    manifest["entries"][0]["local_path"] = None
    manifest["entries"][0]["acquisition_status"] = "resolved_record_url_only"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    assert validate_senate_pdf_source(print_path, source_id, manifest_path) is False


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
