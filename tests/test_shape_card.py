from transparencyx.shape.card import format_money, render_financial_shape_card


def make_export():
    return {
        "politician_id": 1,
        "summary": {
            "politician_id": 1,
            "summary_label": "Very high disclosed wealth, no trading activity",
            "asset_count": 2,
            "asset_value_min": 1001,
            "asset_value_max": 15000,
            "asset_value_midpoint": 8000.5,
            "net_worth_band": "VERY_HIGH",
            "asset_density": "LOW",
            "trade_count": 0,
            "trade_activity": "NONE",
            "trade_volume_band": "UNKNOWN",
        },
        "trace": {
            "assets": {
                "count_rows": [1, 2, 3],
            },
        },
    }


def test_format_money():
    assert format_money(None) == "Unknown"
    assert format_money(1000) == "$1,000"
    assert format_money(1000.0) == "$1,000"
    assert format_money(8000.5) == "$8,000.5"


def test_render_financial_shape_card_includes_required_sections():
    card = render_financial_shape_card(make_export())

    assert "FINANCIAL SHAPE CARD" in card
    assert "politician_id: 1" in card
    assert "summary_label: Very high disclosed wealth, no trading activity" in card
    assert "asset_count: 2" in card
    assert "asset_value_min: $1,001" in card
    assert "asset_value_max: $15,000" in card
    assert "asset_value_midpoint: $8,000.5" in card
    assert "net_worth_band: VERY_HIGH" in card
    assert "asset_density: LOW" in card
    assert "trade_count: 0" in card
    assert "trade_activity: NONE" in card
    assert "trade_volume_band: UNKNOWN" in card


def test_render_financial_shape_card_unknown_values():
    export = make_export()
    export["summary"]["asset_value_min"] = None
    export["summary"]["asset_value_max"] = None
    export["summary"]["asset_value_midpoint"] = None

    card = render_financial_shape_card(export)

    assert "asset_value_min: Unknown" in card
    assert "asset_value_max: Unknown" in card
    assert "asset_value_midpoint: Unknown" in card


def test_render_financial_shape_card_trace_counts():
    card = render_financial_shape_card(make_export())

    assert "trace_raw_normalized_asset_row_count: 3" in card
    assert "trace_usable_asset_count: 2" in card
