import json
import re
from pathlib import Path

from transparencyx.dossier.schema import MemberDossier


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


def dossier_filename(dossier: MemberDossier) -> str:
    member_id = dossier.identity.member_id.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", member_id).strip("-")
    return f"{slug or 'unknown'}.json"
