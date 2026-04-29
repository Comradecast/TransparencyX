BAND_ORDER = ["UNKNOWN", "LOW", "MEDIUM", "HIGH", "VERY_HIGH"]


def render_shape_comparison(export_a: dict, export_b: dict) -> str:
    summary_a = export_a["summary"]
    summary_b = export_b["summary"]

    a_band = summary_a["net_worth_band"]
    b_band = summary_b["net_worth_band"]
    band_delta = BAND_ORDER.index(a_band) - BAND_ORDER.index(b_band)

    a_asset_count = summary_a["asset_count"]
    b_asset_count = summary_b["asset_count"]
    asset_count_delta = a_asset_count - b_asset_count

    return "\n".join([
        "FINANCIAL SHAPE COMPARISON",
        "",
        f"Politician A (ID: {export_a['politician_id']}):",
        f"  Net worth band: {a_band}",
        f"  Asset count: {a_asset_count}",
        "",
        f"Politician B (ID: {export_b['politician_id']}):",
        f"  Net worth band: {b_band}",
        f"  Asset count: {b_asset_count}",
        "",
        "Delta:",
        f"  Net worth band: {band_delta:+d} levels",
        f"  Asset count: {asset_count_delta:+d}",
    ])
