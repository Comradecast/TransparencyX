ASSET_MIX_ORDER = [
    "stock",
    "real_estate",
    "business_interest",
    "bank_account",
    "mutual_fund",
    "option",
    "other",
    "unknown",
]


def format_money(value) -> str:
    if value is None:
        return "Unknown"
        
    if isinstance(value, float) and not value.is_integer():
        return f"${value:,.2f}".rstrip("0").rstrip(".")
        
    return f"${value:,.0f}"


def render_asset_mix(category_counts: dict[str, int] | None) -> list[str]:
    counts = category_counts or {}
    lines = ["Asset Mix:"]

    for category in ASSET_MIX_ORDER:
        lines.append(f"- {category}: {counts.get(category, 0)}")

    return lines


def render_financial_shape_card(export: dict) -> str:
    summary = export["summary"]
    trace = export["trace"]
    trace_asset_count = len(trace["assets"]["count_rows"])
    
    lines = [
        "FINANCIAL SHAPE CARD",
        f"politician_id: {export['politician_id']}",
        f"summary_label: {summary['summary_label']}",
        f"asset_count: {summary['asset_count']}",
        f"asset_value_min: {format_money(summary['asset_value_min'])}",
        f"asset_value_max: {format_money(summary['asset_value_max'])}",
        f"asset_value_midpoint: {format_money(summary['asset_value_midpoint'])}",
        f"net_worth_band: {summary['net_worth_band']}",
        f"asset_density: {summary['asset_density']}",
        *render_asset_mix(summary.get("asset_category_counts")),
        f"trade_count: {summary['trade_count']}",
        f"trade_activity: {summary['trade_activity']}",
        f"trade_volume_band: {summary['trade_volume_band']}",
        f"trace_raw_normalized_asset_row_count: {trace_asset_count}",
        f"trace_usable_asset_count: {summary['asset_count']}",
    ]
    
    return "\n".join(lines)
