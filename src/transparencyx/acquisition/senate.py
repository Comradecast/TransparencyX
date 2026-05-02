import json
from pathlib import Path


SENATE_EXPECTED_SOURCE_KEYS = {
    "member_slug",
    "full_name",
    "display_name",
    "chamber",
    "state",
    "year",
    "filing_type",
    "filing_date",
    "source_id",
    "source_url",
    "pdf_url",
    "local_path",
    "source_authority",
    "source_authority_url",
    "acquisition_status",
    "notes",
}

SENATE_ACQUISITION_PLAN_KEYS = {
    "member_slug",
    "full_name",
    "display_name",
    "chamber",
    "state",
    "year",
    "filing_type",
    "filing_date",
    "source_id",
    "source_url",
    "pdf_url",
    "local_path",
    "source_authority",
    "source_authority_url",
    "acquisition_status",
    "acquired",
    "notes",
}

SENATE_METADATA_INDEX_KEYS = {
    "member_slug",
    "full_name",
    "display_name",
    "chamber",
    "state",
    "year",
    "filing_type",
    "filing_date",
    "source_authority",
    "source_authority_url",
    "source_url",
    "pdf_available",
    "parsed_financials_available",
    "acquisition_status",
    "notes",
}

DEFAULT_SENATE_MANIFEST_PATH = Path(
    "docs/acquisition_plans/nc_2023_senate_expected_sources.json"
)


def _clean_text(value) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def load_senate_expected_sources(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def senate_manifest_entries(manifest: dict) -> list[dict]:
    entries = manifest.get("entries", [])
    if not isinstance(entries, list):
        return []
    return [
        entry
        for entry in entries
        if isinstance(entry, dict)
    ]


def senate_manifest_source_ids(manifest: dict) -> set[str]:
    return {
        source_id
        for entry in senate_manifest_entries(manifest)
        for source_id in [_clean_text(entry.get("source_id"))]
        if source_id is not None
    }


def _path_parts(path: Path) -> tuple[str, ...]:
    return tuple(part.lower() for part in path.parts)


def is_senate_raw_pdf_path(path: Path) -> bool:
    parts = _path_parts(path)
    return (
        len(parts) >= 5
        and parts[-5:-2] == ("data", "raw", "senate")
        and parts[-2].isdigit()
        and path.suffix.lower() == ".pdf"
    )


def _senate_manifest_entry_for_source_id(
    manifest: dict,
    source_id: str,
) -> dict | None:
    for entry in senate_manifest_entries(manifest):
        if _clean_text(entry.get("source_id")) == source_id:
            return entry
    return None


def validate_senate_pdf_source(
    path: str | Path,
    expected_source_id: str,
    manifest_path: str | Path = DEFAULT_SENATE_MANIFEST_PATH,
) -> bool:
    pdf_path = Path(path)
    if not is_senate_raw_pdf_path(pdf_path):
        return False
    if pdf_path.name != f"{expected_source_id}.pdf":
        return False

    manifest_file = Path(manifest_path)
    if not manifest_file.exists():
        return False
    manifest = load_senate_expected_sources(manifest_file)
    entry = _senate_manifest_entry_for_source_id(manifest, expected_source_id)
    if entry is None:
        return False

    year = pdf_path.parts[-2]
    if str(entry.get("year")) != year:
        return False
    local_path = _clean_text(entry.get("local_path"))
    if local_path is None:
        return False
    return Path(local_path).as_posix() == pdf_path.as_posix()


def build_senate_acquisition_plan(
    manifest: dict,
    raw_root: str | Path = "data/raw/senate",
) -> dict:
    raw_path = Path(raw_root)
    entries = []
    for source in senate_manifest_entries(manifest):
        entry = {
            key: source.get(key)
            for key in SENATE_ACQUISITION_PLAN_KEYS
            if key not in {"acquired"}
        }
        local_path = _clean_text(source.get("local_path"))
        source_id = _clean_text(source.get("source_id"))
        expected_path = Path(local_path) if local_path is not None else None
        acquired = (
            source_id is not None
            and expected_path is not None
            and expected_path.exists()
            and raw_path.as_posix() in expected_path.as_posix()
        )
        entry["acquired"] = acquired
        entries.append(entry)

    return {
        "plan_type": "senate_acquisition_plan",
        "state": manifest.get("state"),
        "year": manifest.get("year"),
        "total_expected": len(entries),
        "total_acquired": sum(1 for entry in entries if entry["acquired"]),
        "total_missing": sum(1 for entry in entries if not entry["acquired"]),
        "total_resolved_record_url_only": sum(
            1
            for entry in entries
            if entry.get("acquisition_status") == "resolved_record_url_only"
        ),
        "total_pending_record_url": sum(
            1
            for entry in entries
            if entry.get("acquisition_status") == "pending_record_url"
        ),
        "total_pdf_blocked_no_endpoint": sum(
            1
            for entry in entries
            if _clean_text(entry.get("source_url")) is not None
            and _clean_text(entry.get("pdf_url")) is None
            and _clean_text(entry.get("local_path")) is None
        ),
        "total_ambiguous": sum(
            1
            for entry in entries
            if entry.get("acquisition_status") == "ambiguous"
        ),
        "entries": entries,
    }


def render_senate_acquisition_plan_json(plan: dict) -> str:
    return json.dumps(plan, indent=2, ensure_ascii=False) + "\n"


def build_senate_metadata_index(manifest: dict) -> dict:
    entries = []
    for source in senate_manifest_entries(manifest):
        pdf_available = _clean_text(source.get("pdf_url")) is not None
        parsed_financials_available = _clean_text(source.get("local_path")) is not None
        entries.append(
            {
                "member_slug": source.get("member_slug"),
                "full_name": source.get("full_name"),
                "display_name": source.get("display_name"),
                "chamber": source.get("chamber"),
                "state": source.get("state"),
                "year": source.get("year"),
                "filing_type": source.get("filing_type"),
                "filing_date": source.get("filing_date"),
                "source_authority": source.get("source_authority"),
                "source_authority_url": source.get("source_authority_url"),
                "source_url": source.get("source_url"),
                "pdf_available": pdf_available,
                "parsed_financials_available": parsed_financials_available,
                "acquisition_status": source.get("acquisition_status"),
                "notes": source.get("notes"),
            }
        )

    return {
        "manifest_type": "senate_metadata_index",
        "state": manifest.get("state"),
        "year": manifest.get("year"),
        "total_entries": len(entries),
        "entries": entries,
    }


def render_senate_metadata_index_json(index: dict) -> str:
    return json.dumps(index, indent=2, ensure_ascii=False) + "\n"
