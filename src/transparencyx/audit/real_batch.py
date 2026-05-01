from pathlib import Path

from transparencyx.dossier.builder import build_member_dossier_from_profile
from transparencyx.dossier.metadata import apply_member_metadata, load_member_metadata
from transparencyx.profile.batch import build_profiles_for_directory


TABLE_COLUMNS = [
    "member_id",
    "source_pdf",
    "asset_count",
    "income_count",
    "transaction_count",
    "asset_range",
    "income_range",
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
) -> list[dict]:
    metadata_by_id = metadata_by_id or {}
    rows = []

    for profile in profiles:
        dossier = build_member_dossier_from_profile(profile)
        metadata = metadata_by_id.get(dossier.identity.member_id)
        metadata_attached = metadata is not None
        if metadata is not None:
            apply_member_metadata(dossier, metadata)

        summary = _shape_summary(profile)
        rows.append(
            {
                "member_id": dossier.identity.member_id,
                "source_pdf": _display(profile.get("disclosure_path")),
                "asset_count": _display(dossier.financials.asset_count),
                "income_count": _display(summary.get("income_count")),
                "transaction_count": _display(summary.get("trade_count")),
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


def audit_real_batch(data_dir: str | Path, metadata_by_id: dict | None = None) -> str:
    profiles = build_profiles_for_directory(Path(data_dir))
    if metadata_by_id is None:
        metadata_by_id = load_default_member_metadata()
    rows = build_real_batch_audit_rows(profiles, metadata_by_id)
    return render_real_batch_audit_table(rows)
