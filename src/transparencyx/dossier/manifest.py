import json
import re
from pathlib import Path

from transparencyx.dossier.schema import MemberDossier


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
        entries_by_key[key] = {
            "member_slug": member_slug,
            "chamber": dossier.identity.chamber,
            "state": dossier.identity.state,
            "district": dossier.identity.district,
            "year": year,
            "source_pdf": source_pdf,
            "parsed": _profile_has_summary(profile),
        }

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
