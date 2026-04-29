ASSET_CATEGORY_ORDER = [
    "stock",
    "real_estate",
    "business_interest",
    "bank_account",
    "mutual_fund",
    "option",
    "other",
    "unknown",
]

TABLE_COLUMNS = [
    "member_name",
    "net_worth_band",
    "asset_count",
    "income_band",
    "income_count",
    "top_asset_category",
]


def get_top_asset_category(asset_category_counts: dict) -> str:
    counts = asset_category_counts or {}
    top_category = "unknown"
    top_count = 0

    for category in ASSET_CATEGORY_ORDER:
        count = counts.get(category, 0)
        if count > top_count:
            top_category = category
            top_count = count

    if top_count == 0:
        return "unknown"

    return top_category


def _display_value(value) -> str:
    if value is None or value == "":
        return "Unknown"
    return str(value)


def render_batch_summary_table(profiles: list[dict]) -> str:
    lines = [" | ".join(TABLE_COLUMNS)]

    for profile in profiles:
        summary = profile.get("shape_export", {}).get("summary", {})
        row = [
            _display_value(profile.get("member_name")),
            _display_value(summary.get("net_worth_band")),
            _display_value(summary.get("asset_count")),
            _display_value(summary.get("income_band")),
            _display_value(summary.get("income_count")),
            get_top_asset_category(summary.get("asset_category_counts", {})),
        ]
        lines.append(" | ".join(row))

    return "\n".join(lines)
