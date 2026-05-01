import json
import re
from pathlib import Path

from transparencyx.dossier.schema import MemberDossier


def _clean_sort_text(value) -> str:
    if value is None:
        return ""
    return str(value).strip().casefold()


def _district_sort_value(value) -> int:
    if value is None:
        return 1_000_000
    try:
        return int(str(value).strip())
    except ValueError:
        return 1_000_000


def _chamber_sort_group(dossier: MemberDossier) -> int:
    if dossier.identity.chamber == "House":
        return 0
    if dossier.identity.chamber == "Senate":
        return 1
    return 2


def dossier_index_sort_key(dossier: MemberDossier) -> tuple:
    group = _chamber_sort_group(dossier)
    name = _clean_sort_text(dossier.identity.full_name)
    if group == 0:
        return (group, _district_sort_value(dossier.identity.district), name)
    return (group, name)


def render_member_dossier_json(dossier: MemberDossier) -> str:
    return (
        json.dumps(
            dossier.to_dict(),
            indent=2,
            sort_keys=False,
            ensure_ascii=False,
        )
        + "\n"
    )


def write_member_dossier_json(
    dossier: MemberDossier,
    output_path: str | Path,
) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_member_dossier_json(dossier), encoding="utf-8")
    return path


def write_member_dossiers_json(
    dossiers: list[MemberDossier],
    output_dir: str | Path,
) -> list[Path]:
    directory = Path(output_dir)
    filenames = [dossier_filename(dossier) for dossier in dossiers]
    seen = set()
    for filename in filenames:
        if filename in seen:
            raise ValueError(f"Duplicate dossier filename: {filename}")
        seen.add(filename)

    directory.mkdir(parents=True, exist_ok=True)
    return [
        write_member_dossier_json(dossier, directory / filename)
        for dossier, filename in zip(dossiers, filenames)
    ]


def build_dossier_index(
    dossiers: list[MemberDossier],
    written_paths: list[Path],
) -> dict:
    if len(dossiers) != len(written_paths):
        raise ValueError("dossiers and written_paths lengths must match")

    sorted_pairs = sorted(
        zip(dossiers, written_paths),
        key=lambda item: dossier_index_sort_key(item[0]),
    )

    return {
        "dossier_count": len(dossiers),
        "dossiers": [
            {
                "member_id": dossier.identity.member_id,
                "full_name": dossier.identity.full_name,
                "chamber": dossier.identity.chamber,
                "state": dossier.identity.state,
                "district": dossier.identity.district,
                "party": dossier.identity.party,
                "current_status": dossier.identity.current_status,
                "file": Path(path).name,
            }
            for dossier, path in sorted_pairs
        ],
    }


def render_dossier_index_json(index: dict) -> str:
    return (
        json.dumps(
            index,
            indent=2,
            ensure_ascii=False,
            sort_keys=False,
        )
        + "\n"
    )


def write_dossier_index_json(index: dict, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_dossier_index_json(index), encoding="utf-8")
    return path


def dossier_filename(dossier: MemberDossier) -> str:
    member_id = dossier.identity.member_id.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", member_id).strip("-")
    return f"{slug or 'unknown'}.json"
