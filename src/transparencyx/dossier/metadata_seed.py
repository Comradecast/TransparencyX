import csv
from pathlib import Path

from transparencyx.dossier.metadata import load_member_metadata


def _raw_rows(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as csv_file:
        return list(csv.DictReader(csv_file))


def validate_member_metadata_seed(path: str | Path) -> dict:
    seed_path = Path(path)
    errors = []
    rows = []
    metadata = {}
    duplicate_member_ids = []
    seen = set()
    missing_required_rows = 0
    missing_source_rows = 0

    try:
        rows = _raw_rows(seed_path)
    except OSError as error:
        errors.append(f"seed file could not be read: {error}")

    for index, row in enumerate(rows, start=1):
        member_id = (row.get("member_id") or "").strip()
        full_name = (row.get("full_name") or "").strip()
        source_name = (row.get("source_name") or "").strip()
        source_url = (row.get("source_url") or "").strip()

        if not member_id or not full_name:
            missing_required_rows += 1
            errors.append(f"missing required fields in row: {index}")
        if not source_name and not source_url:
            missing_source_rows += 1
            errors.append(f"missing source in row: {index}")
        if member_id:
            if member_id in seen and member_id not in duplicate_member_ids:
                duplicate_member_ids.append(member_id)
            seen.add(member_id)

    try:
        metadata = load_member_metadata(seed_path)
    except ValueError as error:
        errors.append(str(error))

    duplicate_member_ids.sort()
    house_records = sum(1 for item in metadata.values() if item.chamber == "House")
    senate_records = sum(1 for item in metadata.values() if item.chamber == "Senate")

    return {
        "path": str(seed_path),
        "records": len(metadata),
        "house_records": house_records,
        "senate_records": senate_records,
        "missing_source_rows": missing_source_rows,
        "missing_required_rows": missing_required_rows,
        "duplicate_member_ids": duplicate_member_ids,
        "errors": errors,
        "passed": len(errors) == 0,
    }


def render_member_metadata_seed_validation(report: dict) -> str:
    status = "PASS" if report["passed"] else "FAIL"
    duplicate_member_ids = report["duplicate_member_ids"]
    lines = [
        f"Member Metadata Seed Validation: {status}",
        f"- records: {report['records']}",
        f"- House records: {report['house_records']}",
        f"- Senate records: {report['senate_records']}",
        f"- missing source rows: {report['missing_source_rows']}",
        f"- missing required rows: {report['missing_required_rows']}",
        (
            "- duplicate member ids: "
            f"{', '.join(duplicate_member_ids) if duplicate_member_ids else 'None'}"
        ),
    ]
    if report["errors"]:
        lines.extend(["", "errors:"])
        lines.extend(f"- {error}" for error in report["errors"])
    return "\n".join(lines) + "\n"
