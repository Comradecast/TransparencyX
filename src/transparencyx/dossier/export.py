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


def dossier_filename(dossier: MemberDossier) -> str:
    member_id = dossier.identity.member_id.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", member_id).strip("-")
    return f"{slug or 'unknown'}.json"
