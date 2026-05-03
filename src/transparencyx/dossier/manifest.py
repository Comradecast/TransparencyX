import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from transparencyx.dossier.schema import MemberDossier


ACQUISITION_SOURCE_MEMBER_ALIASES = {
    "don-davis": "donald-g-davis",
    "greg-murphy": "gregory-f-murphy",
}


def _clean_text(value) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def _source_pdf_from_profile(profile: dict) -> str | None:
    for key in ("disclosure_path", "source_pdf", "source_path"):
        value = _clean_text(profile.get(key))
        if value is not None:
            return Path(value).as_posix()
    return None


def _year_from_path(value: str | None) -> int | None:
    if value is None:
        return None
    for part in Path(value).as_posix().split("/"):
        if re.fullmatch(r"\d{4}", part):
            return int(part)
    return None


def _year_from_profile(profile: dict) -> int | None:
    for key in ("disclosure_year", "filing_year", "year"):
        value = profile.get(key)
        if isinstance(value, int) and not isinstance(value, bool):
            return value
    return None


def _year_from_dossier(dossier: MemberDossier) -> int | None:
    for year in dossier.financials.disclosure_years:
        if isinstance(year, int) and not isinstance(year, bool):
            return year
    return None


def _profile_has_summary(profile: dict) -> bool:
    shape_export = profile.get("shape_export")
    if not isinstance(shape_export, dict):
        return False
    return isinstance(shape_export.get("summary"), dict)


def _source_manifest_sort_key(key: tuple[str, int | None, str | None]) -> tuple:
    member_slug, year, source_pdf = key
    return (
        member_slug,
        -1 if year is None else year,
        "" if source_pdf is None else source_pdf,
    )


def build_source_manifest(
    profiles: list[dict],
    dossiers: list[MemberDossier],
) -> dict:
    entries_by_key = {}
    for profile, dossier in zip(profiles, dossiers):
        if not isinstance(profile, dict):
            profile = {}
        member_slug = dossier.identity.member_id
        source_pdf = _source_pdf_from_profile(profile)
        year = (
            _year_from_path(source_pdf)
            or _year_from_profile(profile)
            or _year_from_dossier(dossier)
        )
        key = (member_slug, year, source_pdf)
        entry = {
            "member_slug": member_slug,
            "chamber": dossier.identity.chamber,
            "state": dossier.identity.state,
            "district": dossier.identity.district,
            "year": year,
            "source_pdf": source_pdf,
            "parsed": _profile_has_summary(profile),
        }
        identity_resolution = profile.get("identity_resolution")
        if isinstance(identity_resolution, dict):
            for field in (
                "identity_resolution_source",
                "identity_resolution_doc_id",
                "parsed_identity_original",
                "identity_resolution_status",
            ):
                if field in identity_resolution:
                    entry[field] = identity_resolution[field]
        entries_by_key[key] = entry

    entries = [
        entries_by_key[key]
        for key in sorted(entries_by_key, key=_source_manifest_sort_key)
    ]
    return {
        "source_count": len(entries),
        "sources": entries,
    }


def render_source_manifest_json(manifest: dict) -> str:
    return json.dumps(
        manifest,
        indent=2,
        ensure_ascii=False,
        sort_keys=False,
    ) + "\n"


def write_source_manifest_json(manifest: dict, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_source_manifest_json(manifest), encoding="utf-8")
    return path


def _xml_child_text(element: ET.Element, tag: str) -> str | None:
    child = element.find(tag)
    if child is None or child.text is None:
        return None
    text = child.text.strip()
    return text or None


def _normalize_last_name(value: str | None) -> str | None:
    text = _clean_text(value)
    if text is None:
        return None
    normalized = re.sub(r"[^A-Za-z]", "", text).upper()
    return normalized or None


def _expected_last_name(entry: dict) -> str | None:
    full_name = _clean_text(entry.get("full_name"))
    if full_name is None:
        return None
    parts = full_name.split()
    if not parts:
        return None
    return _normalize_last_name(parts[-1])


def _expected_state_dst(entry: dict) -> str | None:
    state = _clean_text(entry.get("state"))
    district = _clean_text(entry.get("district"))
    if state is None or district is None:
        return None
    try:
        district_number = int(district)
    except ValueError:
        return None
    return f"{state.upper()}{district_number:02d}"


def load_house_disclosure_index_xml(path: str | Path) -> list[dict]:
    root = ET.parse(path).getroot()
    rows = []
    for member in root.findall("Member"):
        row = {
            "last": _xml_child_text(member, "Last"),
            "first": _xml_child_text(member, "First"),
            "filing_type": _xml_child_text(member, "FilingType"),
            "state_dst": _xml_child_text(member, "StateDst"),
            "year": _xml_child_text(member, "Year"),
            "filing_date": _xml_child_text(member, "FilingDate"),
            "doc_id": _xml_child_text(member, "DocID"),
        }
        rows.append(row)
    return rows


def _index_candidate(row: dict) -> dict:
    return {
        "doc_id": row.get("doc_id"),
        "filing_type": row.get("filing_type"),
        "state_dst": row.get("state_dst"),
        "last": row.get("last"),
    }


def _matching_house_index_rows(entry: dict, index_rows: list[dict]) -> list[dict]:
    state_dst = _expected_state_dst(entry)
    last_name = _expected_last_name(entry)
    year = entry.get("year")
    if state_dst is None or last_name is None:
        return []
    matches = [
        row
        for row in index_rows
        if row.get("year") == str(year)
        and row.get("state_dst") == state_dst
        and _normalize_last_name(row.get("last")) == last_name
        and row.get("doc_id") is not None
    ]
    return sorted(
        matches,
        key=lambda row: (
            row.get("filing_type") or "",
            row.get("doc_id") or "",
        ),
    )


def _select_house_index_match(matches: list[dict]) -> tuple[str, dict | None, list[dict], str | None]:
    official_matches = [
        row
        for row in matches
        if row.get("filing_type") == "O"
    ]
    candidate_matches = [
        row
        for row in matches
        if row.get("filing_type") == "C"
    ]
    if len(official_matches) == 1:
        return "identified", official_matches[0], [], None
    if len(official_matches) > 1:
        return "ambiguous", None, official_matches, None
    if len(candidate_matches) == 1:
        return (
            "identified",
            candidate_matches[0],
            [],
            "Official index contains FilingType C and no FilingType O record for this expected member/year/district.",
        )
    if len(candidate_matches) > 1:
        return "ambiguous", None, candidate_matches, None
    return "missing", None, [], None


def canonical_acquisition_source_member_slug(member_slug: str | None) -> str | None:
    if member_slug is None:
        return None
    return ACQUISITION_SOURCE_MEMBER_ALIASES.get(member_slug, member_slug)


def acquisition_source_key(entry: dict) -> tuple[str | None, int | None]:
    return (
        canonical_acquisition_source_member_slug(entry.get("member_slug")),
        entry.get("year"),
    )


def build_index_acquisition_manifest(
    expected_manifest: dict,
    source_manifest: dict,
    index_rows: list[dict],
) -> dict:
    actual_sources = {
        acquisition_source_key(entry): entry
        for entry in source_manifest.get("sources", [])
        if isinstance(entry, dict)
    }
    entries = []
    for expected in expected_manifest.get("sources", []):
        if not isinstance(expected, dict):
            continue
        key = (expected.get("member_slug"), expected.get("year"))
        actual = actual_sources.get(key)
        matches = (
            _matching_house_index_rows(expected, index_rows)
            if expected.get("chamber") == "House"
            else []
        )
        acquisition_status, match, candidate_rows, resolution_note = (
            _select_house_index_match(matches)
        )
        if match is not None:
            doc_id = match.get("doc_id")
            filing_type = match.get("filing_type")
            source_pdf = f"data/raw/house/2023/{doc_id}.pdf"
        else:
            doc_id = None
            filing_type = None
            source_pdf = actual.get("source_pdf") if actual is not None else expected.get("source_pdf")
        candidates = [_index_candidate(row) for row in candidate_rows]

        acquired = actual is not None
        parsed = bool(actual.get("parsed")) if actual is not None else False
        entries.append({
            "member_slug": expected.get("member_slug"),
            "year": expected.get("year"),
            "chamber": expected.get("chamber"),
            "state": expected.get("state"),
            "district": expected.get("district"),
            "expected": bool(expected.get("expected")),
            "acquired": acquired,
            "parsed": parsed,
            "doc_id": doc_id,
            "filing_type": filing_type,
            "source_pdf": actual.get("source_pdf") if actual is not None else source_pdf,
            "acquisition_status": acquisition_status,
            "resolution_note": resolution_note,
            "candidates": candidates,
        })

    return {
        "total_expected": len(entries),
        "identified_count": sum(
            1
            for entry in entries
            if entry["acquisition_status"] == "identified"
        ),
        "acquired_count": sum(1 for entry in entries if entry["acquired"]),
        "missing_count": sum(
            1
            for entry in entries
            if entry["acquisition_status"] == "missing"
        ),
        "ambiguous_count": sum(
            1
            for entry in entries
            if entry["acquisition_status"] == "ambiguous"
        ),
        "entries": entries,
    }


def render_index_acquisition_manifest_json(manifest: dict) -> str:
    return json.dumps(
        manifest,
        indent=2,
        ensure_ascii=False,
        sort_keys=False,
    ) + "\n"


def build_site_manifest(
    input_directory: str,
    output_directory: str,
    options: dict,
    profiles_count: int,
    dossiers_count: int,
    json_paths: list[Path],
    html_paths: list[Path],
    metadata_report: dict | None,
    committee_report: dict | None = None,
) -> dict:
    metadata_present = bool(options.get("member_metadata"))
    metadata_coverage = "metadata_coverage.json" if metadata_present else None
    committee_coverage = "committee_coverage.json" if committee_report is not None else None

    return {
        "build_type": "dossier_site",
        "input_directory": input_directory,
        "output_directory": output_directory,
        "options": {
            "member_metadata": metadata_present,
            "fetch_exposure": bool(options.get("fetch_exposure")),
            "recipient_candidate_audit": bool(options.get("recipient_candidate_audit")),
        },
        "counts": {
            "profiles": profiles_count,
            "dossiers": dossiers_count,
            "json_dossiers": len(json_paths),
            "html_dossiers": len(html_paths),
            "metadata_records_loaded": (
                metadata_report["metadata_records_loaded"]
                if metadata_report is not None
                else 0
            ),
            "metadata_matched_dossiers": (
                metadata_report["matched_dossiers"]
                if metadata_report is not None
                else 0
            ),
            "metadata_unmatched_dossiers": (
                metadata_report["unmatched_dossiers"]
                if metadata_report is not None
                else 0
            ),
            "committee_rows_with_assignments": (
                committee_report["rows_with_committees"]
                if committee_report is not None
                else 0
            ),
            "committee_rows_without_assignments": (
                committee_report["rows_without_committees"]
                if committee_report is not None
                else 0
            ),
        },
        "artifacts": {
            "json_index": "index.json",
            "html_index": "index.html",
            "metadata_coverage": metadata_coverage,
            "committee_coverage": committee_coverage,
            "dossier_json_files": [Path(path).name for path in json_paths],
            "dossier_html_files": [Path(path).name for path in html_paths],
        },
    }


def render_site_manifest_json(manifest: dict) -> str:
    return json.dumps(
        manifest,
        indent=2,
        ensure_ascii=False,
        sort_keys=False,
    ) + "\n"


def write_site_manifest_json(manifest: dict, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_site_manifest_json(manifest), encoding="utf-8")
    return path
