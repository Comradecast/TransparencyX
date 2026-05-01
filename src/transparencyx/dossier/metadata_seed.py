import csv
from pathlib import Path
from urllib.parse import urlparse

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


def summarize_member_metadata_seed(path: str | Path) -> dict:
    metadata = load_member_metadata(Path(path))
    states = sorted({
        item.state
        for item in metadata.values()
        if item.state
    })

    return {
        "records": len(metadata),
        "house": sum(1 for item in metadata.values() if item.chamber == "House"),
        "senate": sum(1 for item in metadata.values() if item.chamber == "Senate"),
        "states": states,
    }


def _district_sort_key(district: str) -> tuple[int, str]:
    try:
        return (0, f"{int(district):03d}")
    except ValueError:
        return (1, district)


def summarize_member_metadata_by_state(path: str | Path, state: str) -> dict:
    metadata = load_member_metadata(Path(path))
    state_code = state.strip().upper()
    rows = [
        item
        for item in metadata.values()
        if item.state == state_code
    ]
    house_rows = [
        item
        for item in rows
        if item.chamber == "House"
    ]
    senate_rows = [
        item
        for item in rows
        if item.chamber == "Senate"
    ]

    return {
        "state": state_code,
        "records": len(rows),
        "house_records": len(house_rows),
        "senate_records": len(senate_rows),
        "house_districts": sorted(
            [item.district for item in house_rows if item.district],
            key=_district_sort_key,
        ),
        "senators": sorted(item.full_name for item in senate_rows),
    }


def summarize_committee_assignment_coverage_by_state(path: str | Path, state: str) -> dict:
    metadata = load_member_metadata(Path(path))
    state_code = state.strip().upper()
    rows = [
        item
        for item in metadata.values()
        if item.state == state_code
    ]
    rows_with_committees = [
        item
        for item in rows
        if item.committee_assignments
    ]

    return {
        "state": state_code,
        "records": len(rows),
        "rows_with_committees": len(rows_with_committees),
        "rows_without_committees": len(rows) - len(rows_with_committees),
        "member_ids_without_committees": [
            item.member_id
            for item in rows
            if not item.committee_assignments
        ],
    }


def classify_metadata_source(source_url: str | None) -> str:
    if source_url is None or not source_url.strip():
        return "unknown"

    parsed = urlparse(source_url.strip())
    path = parsed.path.rstrip("/")
    lower_path = path.lower()
    segments = [
        segment
        for segment in lower_path.split("/")
        if segment
    ]

    if "clerk.house.gov" in parsed.netloc.lower():
        if lower_path in {"/members", "/members/viewmemberlist"}:
            return "list"
        if len(segments) > 1 and segments[0] == "members":
            return "profile"

    if "senate.gov" in parsed.netloc.lower():
        if parsed.netloc.lower().endswith(".senate.gov") and parsed.netloc.lower() != "www.senate.gov":
            return "profile"
        if lower_path in {"/senators", "/senators/index.htm"}:
            return "list"
        if len(segments) > 1 and segments[0] == "states":
            return "list"
        if len(segments) > 1 and segments[0] == "senators":
            return "profile"

    return "unknown"


def _source_quality_report_from_items(items) -> dict:
    breakdown = [
        {
            "member_id": item.member_id,
            "source_type": classify_metadata_source(item.source_url),
        }
        for item in items
    ]

    return {
        "records": len(breakdown),
        "profile_sources": sum(1 for item in breakdown if item["source_type"] == "profile"),
        "list_sources": sum(1 for item in breakdown if item["source_type"] == "list"),
        "unknown_sources": sum(1 for item in breakdown if item["source_type"] == "unknown"),
        "member_breakdown": breakdown,
    }


def build_metadata_source_quality_report(path: str | Path) -> dict:
    metadata = load_member_metadata(Path(path))
    return _source_quality_report_from_items(metadata.values())


def build_metadata_source_quality_report_by_state(path: str | Path, state: str) -> dict:
    metadata = load_member_metadata(Path(path))
    state_code = state.strip().upper()
    return _source_quality_report_from_items(
        item
        for item in metadata.values()
        if item.state == state_code
    )


def render_metadata_source_quality_report(report: dict) -> str:
    lines = [
        "Metadata Source Quality Report:",
        f"- records: {report['records']}",
        f"- profile sources: {report['profile_sources']}",
        f"- list sources: {report['list_sources']}",
        f"- unknown sources: {report['unknown_sources']}",
        "",
        "member breakdown:",
    ]
    if report["member_breakdown"]:
        lines.extend(
            f"- {item['member_id']}: {item['source_type']}"
            for item in report["member_breakdown"]
        )
    else:
        lines.append("None")
    return "\n".join(lines) + "\n"


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
