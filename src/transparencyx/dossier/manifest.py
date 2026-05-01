import json
from pathlib import Path


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
