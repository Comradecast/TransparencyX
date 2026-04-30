import csv
import json
from dataclasses import dataclass, field
from io import StringIO
from pathlib import Path

from transparencyx.dossier.schema import EvidenceSource, MemberDossier


MEMBER_METADATA_COLUMNS = [
    "member_id",
    "full_name",
    "chamber",
    "state",
    "district",
    "party",
    "current_status",
    "official_salary",
    "leadership_roles",
    "committee_assignments",
    "office_start",
    "office_end",
    "source_name",
    "source_url",
]


@dataclass
class MemberMetadata:
    member_id: str
    full_name: str
    chamber: str | None = None
    state: str | None = None
    district: str | None = None
    party: str | None = None
    current_status: str | None = None
    official_salary: float | None = None
    leadership_roles: list[str] = field(default_factory=list)
    committee_assignments: list[str] = field(default_factory=list)
    office_start: str | None = None
    office_end: str | None = None
    source_name: str | None = None
    source_url: str | None = None


def _clean_required(row: dict, key: str) -> str:
    value = row.get(key)
    if value is None:
        raise ValueError(f"{key} is required")
    clean_value = str(value).strip()
    if not clean_value:
        raise ValueError(f"{key} is required")
    return clean_value


def _clean_optional(row: dict, key: str) -> str | None:
    value = row.get(key)
    if value is None:
        return None
    clean_value = str(value).strip()
    return clean_value or None


def _clean_list(row: dict, key: str) -> list[str]:
    value = row.get(key)
    if value is None:
        return []
    if isinstance(value, list):
        return [
            str(item).strip()
            for item in value
            if str(item).strip()
        ]
    return [
        item.strip()
        for item in str(value).split("|")
        if item.strip()
    ]


def _clean_salary(row: dict) -> float | None:
    value = row.get("official_salary")
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None
    return float(value)


def _metadata_from_row(row: dict) -> MemberMetadata:
    if not isinstance(row, dict):
        raise ValueError("member metadata rows must be objects")

    return MemberMetadata(
        member_id=_clean_required(row, "member_id"),
        full_name=_clean_required(row, "full_name"),
        chamber=_clean_optional(row, "chamber"),
        state=_clean_optional(row, "state"),
        district=_clean_optional(row, "district"),
        party=_clean_optional(row, "party"),
        current_status=_clean_optional(row, "current_status"),
        official_salary=_clean_salary(row),
        leadership_roles=_clean_list(row, "leadership_roles"),
        committee_assignments=_clean_list(row, "committee_assignments"),
        office_start=_clean_optional(row, "office_start"),
        office_end=_clean_optional(row, "office_end"),
        source_name=_clean_optional(row, "source_name"),
        source_url=_clean_optional(row, "source_url"),
    )


def _load_json_rows(path: Path) -> list[dict]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(loaded, dict):
        members = loaded.get("members")
        if isinstance(members, list):
            return members
    if isinstance(loaded, list):
        return loaded
    raise ValueError("member metadata JSON must be a list or contain a members list")


def load_member_metadata(path: str | Path) -> dict[str, MemberMetadata]:
    metadata_path = Path(path)
    suffix = metadata_path.suffix.lower()

    if suffix == ".csv":
        with metadata_path.open(newline="", encoding="utf-8") as csv_file:
            rows = list(csv.DictReader(csv_file))
    elif suffix == ".json":
        rows = _load_json_rows(metadata_path)
    else:
        raise ValueError("member metadata must be a .csv or .json file")

    metadata_by_id = {}
    for row in rows:
        metadata = _metadata_from_row(row)
        if metadata.member_id in metadata_by_id:
            raise ValueError(f"Duplicate member metadata member_id: {metadata.member_id}")
        metadata_by_id[metadata.member_id] = metadata

    return metadata_by_id


def render_member_metadata_template_csv() -> str:
    output = StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(MEMBER_METADATA_COLUMNS)
    return output.getvalue()


def write_member_metadata_template_csv(output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_member_metadata_template_csv(), encoding="utf-8")
    return path


def build_metadata_coverage_report(
    dossiers: list[MemberDossier],
    metadata_map: dict[str, MemberMetadata] | None,
) -> dict:
    metadata = metadata_map or {}
    matched_member_ids = []
    unmatched_member_ids = []
    matched_seen = set()
    unmatched_seen = set()
    matched_count = 0
    unmatched_count = 0

    for dossier in dossiers:
        member_id = dossier.identity.member_id
        if member_id in metadata:
            matched_count += 1
            if member_id not in matched_seen:
                matched_member_ids.append(member_id)
                matched_seen.add(member_id)
        else:
            unmatched_count += 1
            if member_id not in unmatched_seen:
                unmatched_member_ids.append(member_id)
                unmatched_seen.add(member_id)

    return {
        "total_dossiers": len(dossiers),
        "metadata_records_loaded": len(metadata),
        "matched_dossiers": matched_count,
        "unmatched_dossiers": unmatched_count,
        "matched_member_ids": matched_member_ids,
        "unmatched_member_ids": unmatched_member_ids,
    }


def _render_member_id_list(title: str, member_ids: list[str]) -> list[str]:
    lines = [title]
    if not member_ids:
        lines.append("None")
    else:
        lines.extend(f"- {member_id}" for member_id in member_ids)
    return lines


def render_metadata_coverage_report(report: dict) -> str:
    lines = [
        "Metadata Coverage Report:",
        f"- total dossiers: {report['total_dossiers']}",
        f"- metadata records loaded: {report['metadata_records_loaded']}",
        f"- matched dossiers: {report['matched_dossiers']}",
        f"- unmatched dossiers: {report['unmatched_dossiers']}",
        "",
        *_render_member_id_list(
            "matched member ids:",
            report["matched_member_ids"],
        ),
        "",
        *_render_member_id_list(
            "unmatched member ids:",
            report["unmatched_member_ids"],
        ),
    ]
    return "\n".join(lines)


def apply_member_metadata(
    dossier: MemberDossier,
    metadata: MemberMetadata,
) -> MemberDossier:
    dossier.identity.full_name = metadata.full_name
    dossier.identity.chamber = metadata.chamber
    dossier.identity.state = metadata.state
    dossier.identity.district = metadata.district
    dossier.identity.party = metadata.party
    dossier.identity.current_status = metadata.current_status

    dossier.office.official_salary = metadata.official_salary
    dossier.office.leadership_roles = list(metadata.leadership_roles)
    dossier.office.committee_assignments = list(metadata.committee_assignments)
    dossier.office.office_start = metadata.office_start
    dossier.office.office_end = metadata.office_end

    if metadata.source_name or metadata.source_url:
        dossier.evidence_sources.append(
            EvidenceSource(
                source_type="member_metadata",
                source_name=metadata.source_name or "member_metadata",
                source_url=metadata.source_url,
            )
        )

    return dossier
