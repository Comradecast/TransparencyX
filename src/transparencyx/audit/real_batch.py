from pathlib import Path

from transparencyx.dossier.builder import build_member_dossier_from_profile
from transparencyx.dossier.metadata import apply_member_metadata, load_member_metadata
from transparencyx.dossier.aliases import load_member_aliases
from transparencyx.profile.batch import build_profiles_for_directory


TABLE_COLUMNS = [
    "member_id",
    "canonical_member_id",
    "alias_applied",
    "source_pdf",
    "asset_count",
    "income_count",
    "transaction_count",
    "asset_range",
    "income_range",
    "metadata_attached",
]

IDENTITY_AUDIT_COLUMNS = [
    "parsed_member_id",
    "canonical_member_id",
    "alias_applied",
    "parsed_display_name",
    "source_pdf",
    "metadata_attached",
]


def _display(value) -> str:
    if value is None or value == "":
        return "Unknown"
    return str(value)


def _format_money(value) -> str:
    if value is None or value == "":
        return "Unknown"
    if isinstance(value, bool):
        return "Unknown"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return _display(value)
    if number.is_integer():
        return f"${number:,.0f}"
    return f"${number:,.2f}"


def _format_range(minimum, maximum) -> str:
    if minimum is None and maximum is None:
        return "Unknown"
    return f"{_format_money(minimum)} - {_format_money(maximum)}"


def _shape_summary(profile: dict) -> dict:
    shape_export = profile.get("shape_export")
    if not isinstance(shape_export, dict):
        return {}
    summary = shape_export.get("summary")
    if isinstance(summary, dict):
        return summary
    return {}


def load_default_member_metadata(
    seed_path: str | Path = "data/seed/member_metadata_seed.csv",
) -> dict:
    path = Path(seed_path)
    if not path.exists():
        return {}
    return load_member_metadata(path)


def build_real_batch_audit_rows(
    profiles: list[dict],
    metadata_by_id: dict | None = None,
    aliases: dict[str, str] | None = None,
) -> list[dict]:
    metadata_by_id = metadata_by_id or {}
    aliases = aliases or {}
    rows = []

    for profile in profiles:
        dossier = build_member_dossier_from_profile(profile)
        parsed_id = dossier.identity.member_id
        canonical_id = aliases.get(parsed_id, parsed_id)
        alias_applied = canonical_id != parsed_id

        if alias_applied:
            dossier.identity.member_id = canonical_id

        metadata = metadata_by_id.get(dossier.identity.member_id)
        metadata_attached = metadata is not None
        if metadata is not None:
            apply_member_metadata(dossier, metadata)

        summary = _shape_summary(profile)
        rows.append(
            {
                "member_id": parsed_id,
                "canonical_member_id": canonical_id,
                "alias_applied": "Yes" if alias_applied else "No",
                "display_name": _display(dossier.identity.full_name),
                "source_pdf": _display(profile.get("disclosure_path")),
                "asset_count": _display(dossier.financials.asset_count),
                "income_count": _display(summary.get("income_count")),
                "transaction_count": _display(summary.get("transaction_count")),
                "asset_range": _format_range(
                    dossier.financials.asset_value_min,
                    dossier.financials.asset_value_max,
                ),
                "income_range": _format_range(
                    dossier.financials.income_min,
                    dossier.financials.income_max,
                ),
                "metadata_attached": "Yes" if metadata_attached else "No",
            }
        )

    return rows


def render_real_batch_audit_table(rows: list[dict]) -> str:
    lines = [" | ".join(TABLE_COLUMNS)]
    for row in rows:
        lines.append(" | ".join(_display(row.get(column)) for column in TABLE_COLUMNS))
    return "\n".join(lines)


def build_unattached_identity_rows(rows: list[dict]) -> list[dict]:
    return [
        {
            "parsed_member_id": row.get("member_id"),
            "canonical_member_id": row.get("canonical_member_id"),
            "alias_applied": row.get("alias_applied"),
            "parsed_display_name": row.get("display_name"),
            "source_pdf": row.get("source_pdf"),
            "metadata_attached": row.get("metadata_attached"),
        }
        for row in rows
        if row.get("metadata_attached") == "No"
    ]


def render_unattached_identity_table(rows: list[dict]) -> str:
    lines = ["Metadata Unattached Parsed Profiles", " | ".join(IDENTITY_AUDIT_COLUMNS)]
    for row in rows:
        lines.append(
            " | ".join(_display(row.get(column)) for column in IDENTITY_AUDIT_COLUMNS)
        )
    if not rows:
        lines.append("None")
    return "\n".join(lines)


def render_real_batch_audit_report(rows: list[dict]) -> str:
    identity_rows = build_unattached_identity_rows(rows)
    return "\n\n".join(
        [
            render_real_batch_audit_table(rows),
            render_unattached_identity_table(identity_rows),
        ]
    )


def audit_real_batch(data_dir: str | Path, metadata_by_id: dict | None = None) -> str:
    profiles = build_profiles_for_directory(Path(data_dir))
    if metadata_by_id is None:
        metadata_by_id = load_default_member_metadata()
    aliases = load_member_aliases("data/seed/member_id_aliases.csv")
    rows = build_real_batch_audit_rows(profiles, metadata_by_id, aliases)
    return render_real_batch_audit_report(rows)
