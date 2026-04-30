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
