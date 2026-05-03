import csv
import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


HOUSE_IDENTITY_RESOLUTION_SOURCE = "house_doc_id_manifest"
DEFAULT_HOUSE_INDEX_PATH = Path("data/source_indexes/house/2023FD.xml")
DEFAULT_ACQUISITION_PLAN_DIR = Path("docs/acquisition_plans")
DEFAULT_NC_EXPECTED_SOURCE_PATH = Path(
    "docs/source_manifests/nc_2023_expected_sources.json"
)
DEFAULT_MEMBER_METADATA_PATH = Path("data/seed/member_metadata_seed.csv")


@dataclass(frozen=True)
class HouseIdentityResolution:
    member_slug: str
    full_name: str
    chamber: str
    state: str
    district: str
    year: int
    doc_id: str
    source: str = HOUSE_IDENTITY_RESOLUTION_SOURCE
    status: str = "resolved"


def _clean_text(value) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _xml_child_text(element: ET.Element, tag: str) -> str | None:
    child = element.find(tag)
    if child is None:
        return None
    return _clean_text(child.text)


def extract_house_doc_id_from_pdf_path(path: str | Path) -> tuple[int, str] | None:
    pdf_path = Path(path)
    parts = tuple(part.lower() for part in pdf_path.parts)
    if (
        len(parts) < 5
        or parts[-5:-2] != ("data", "raw", "house")
        or not parts[-2].isdigit()
        or pdf_path.suffix.lower() != ".pdf"
        or not pdf_path.stem.isdigit()
    ):
        return None
    return int(parts[-2]), pdf_path.stem


def _load_house_index_rows(index_path: str | Path) -> list[dict]:
    root = ET.parse(index_path).getroot()
    rows = []
    for member in root.findall("Member"):
        rows.append(
            {
                "first": _xml_child_text(member, "First"),
                "last": _xml_child_text(member, "Last"),
                "filing_type": _xml_child_text(member, "FilingType"),
                "state_dst": _xml_child_text(member, "StateDst"),
                "year": _xml_child_text(member, "Year"),
                "doc_id": _xml_child_text(member, "DocID"),
            }
        )
    return rows


def _entries_from_json_file(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    entries = data.get("entries", [])
    if not isinstance(entries, list):
        return []
    return [entry for entry in entries if isinstance(entry, dict)]


def _load_acquisition_entries(plan_dir: str | Path) -> list[dict]:
    base = Path(plan_dir)
    entries = []
    for path in sorted(base.glob("*_2023_expected_sources.json")):
        entries.extend(_entries_from_json_file(path))
    nc_index_path = base / "nc_2023_index_acquisition_manifest.json"
    if nc_index_path.exists():
        entries.extend(_entries_from_json_file(nc_index_path))
    return entries


def _load_slug_names_from_expected_sources(path: str | Path) -> dict[str, str]:
    source_path = Path(path)
    if not source_path.exists():
        return {}
    data = json.loads(source_path.read_text(encoding="utf-8"))
    sources = data.get("sources", [])
    if not isinstance(sources, list):
        return {}
    names = {}
    for source in sources:
        if not isinstance(source, dict):
            continue
        member_slug = _clean_text(source.get("member_slug"))
        full_name = _clean_text(source.get("full_name"))
        if member_slug is not None and full_name is not None:
            names[member_slug] = full_name
    return names


def _load_metadata_names(path: str | Path) -> dict[str, str]:
    metadata_path = Path(path)
    if not metadata_path.exists():
        return {}
    with metadata_path.open(newline="", encoding="utf-8") as csv_file:
        rows = csv.DictReader(csv_file)
        return {
            row["member_id"].strip(): row["full_name"].strip()
            for row in rows
            if row.get("member_id", "").strip()
            and row.get("full_name", "").strip()
        }


def _title_from_slug(member_slug: str) -> str:
    return " ".join(part.capitalize() for part in member_slug.split("-"))


def _district_from_state_dst(value: str | None) -> str | None:
    state_dst = _clean_text(value)
    if state_dst is None:
        return None
    match = re.fullmatch(r"[A-Z]{2}(\d{2})", state_dst)
    if match is None:
        return None
    return str(int(match.group(1)))


def _state_from_state_dst(value: str | None) -> str | None:
    state_dst = _clean_text(value)
    if state_dst is None or len(state_dst) < 2:
        return None
    return state_dst[:2]


def _entry_year(entry: dict) -> int | None:
    value = entry.get("year")
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


class HouseDocIdIdentityResolver:
    def __init__(
        self,
        index_rows: list[dict],
        acquisition_entries: list[dict],
        slug_names: dict[str, str] | None = None,
    ):
        self._index_rows = index_rows
        self._acquisition_entries = acquisition_entries
        self._slug_names = slug_names or {}

    @classmethod
    def from_default_paths(cls) -> "HouseDocIdIdentityResolver":
        slug_names = _load_metadata_names(DEFAULT_MEMBER_METADATA_PATH)
        slug_names.update(_load_slug_names_from_expected_sources(DEFAULT_NC_EXPECTED_SOURCE_PATH))
        return cls(
            index_rows=_load_house_index_rows(DEFAULT_HOUSE_INDEX_PATH),
            acquisition_entries=_load_acquisition_entries(DEFAULT_ACQUISITION_PLAN_DIR),
            slug_names=slug_names,
        )

    def resolve_pdf_path(self, path: str | Path) -> HouseIdentityResolution | None:
        extracted = extract_house_doc_id_from_pdf_path(path)
        if extracted is None:
            return None
        path_year, doc_id = extracted
        index_matches = [
            row
            for row in self._index_rows
            if row.get("doc_id") == doc_id
            and row.get("year") == str(path_year)
        ]
        if len(index_matches) != 1:
            return None
        index_row = index_matches[0]
        if index_row.get("filing_type") != "O":
            return None

        acquisition_matches = [
            entry
            for entry in self._acquisition_entries
            if _clean_text(entry.get("doc_id")) == doc_id
            and _entry_year(entry) == path_year
        ]
        if len(acquisition_matches) != 1:
            return None
        entry = acquisition_matches[0]
        if entry.get("filing_type") != "O":
            return None

        member_slug = _clean_text(entry.get("member_slug"))
        if member_slug is None:
            return None
        state = _clean_text(entry.get("state")) or _state_from_state_dst(index_row.get("state_dst"))
        district = _clean_text(entry.get("district")) or _district_from_state_dst(index_row.get("state_dst"))
        if state is None or district is None:
            return None
        full_name = (
            _clean_text(entry.get("full_name"))
            or self._slug_names.get(member_slug)
            or _title_from_slug(member_slug)
        )
        return HouseIdentityResolution(
            member_slug=member_slug,
            full_name=full_name,
            chamber="House",
            state=state,
            district=district,
            year=path_year,
            doc_id=doc_id,
        )


def _parsed_identity_from_profile(profile: dict) -> dict:
    return {
        "member_id": _clean_text(profile.get("member_id")),
        "member_name": _clean_text(profile.get("member_name")),
        "chamber": _clean_text(profile.get("chamber")),
        "state": _clean_text(profile.get("state")),
        "district": _clean_text(profile.get("district")),
    }


def _slug_from_member_name(value: str | None) -> str:
    text = _clean_text(value)
    if text is None:
        return "unknown"
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "unknown"


def apply_house_doc_id_identity_resolution(
    profile: dict,
    resolver: HouseDocIdIdentityResolver,
) -> dict:
    if not isinstance(profile, dict):
        return profile
    source_path = _clean_text(profile.get("disclosure_path"))
    if source_path is None:
        return profile
    resolution = resolver.resolve_pdf_path(source_path)
    if resolution is None:
        return profile

    parsed_member_id = _clean_text(profile.get("member_id")) or _slug_from_member_name(
        _clean_text(profile.get("member_name"))
    )
    needs_resolution = (
        parsed_member_id == "unknown"
        or parsed_member_id != resolution.member_slug
        or _clean_text(profile.get("chamber")) != resolution.chamber
        or _clean_text(profile.get("state")) != resolution.state
        or _clean_text(profile.get("district")) != resolution.district
    )
    if not needs_resolution:
        return profile

    resolved = dict(profile)
    resolved["member_id"] = resolution.member_slug
    resolved["member_name"] = resolution.full_name
    resolved["chamber"] = resolution.chamber
    resolved["state"] = resolution.state
    resolved["district"] = resolution.district
    resolved["disclosure_year"] = resolution.year
    resolved["identity_resolution"] = {
        "identity_resolution_source": resolution.source,
        "identity_resolution_doc_id": resolution.doc_id,
        "parsed_identity_original": _parsed_identity_from_profile(profile),
        "identity_resolution_status": resolution.status,
    }
    return resolved


def apply_house_doc_id_identity_resolution_to_profiles(
    profiles: list[dict],
    resolver: HouseDocIdIdentityResolver | None = None,
) -> list[dict]:
    identity_resolver = resolver or HouseDocIdIdentityResolver.from_default_paths()
    return [
        apply_house_doc_id_identity_resolution(profile, identity_resolver)
        for profile in profiles
    ]
