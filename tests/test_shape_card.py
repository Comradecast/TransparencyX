from transparencyx.shape.card import format_money, render_asset_mix, render_financial_shape_card


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
            "asset_category_counts": {
                "stock": 2,
                "real_estate": 1,
                "business_interest": 0,
                "bank_account": 3,
                "mutual_fund": 0,
                "option": 0,
                "other": 1,
                "unknown": 0,
            },
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
    assert "Asset Mix:" in card
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


def test_render_asset_mix_exact_order():
    lines = render_asset_mix({
        "unknown": 8,
        "other": 7,
        "option": 6,
        "mutual_fund": 5,
        "bank_account": 4,
        "business_interest": 3,
        "real_estate": 2,
        "stock": 1,
    })

    assert lines == [
        "Asset Mix:",
        "- stock: 1",
        "- real_estate: 2",
        "- business_interest: 3",
        "- bank_account: 4",
        "- mutual_fund: 5",
        "- option: 6",
        "- other: 7",
        "- unknown: 8",
    ]


def test_render_asset_mix_defaults_missing_counts_to_zero():
    lines = render_asset_mix(None)

    assert lines == [
        "Asset Mix:",
        "- stock: 0",
        "- real_estate: 0",
        "- business_interest: 0",
        "- bank_account: 0",
        "- mutual_fund: 0",
        "- option: 0",
        "- other: 0",
        "- unknown: 0",
    ]


def test_render_financial_shape_card_missing_asset_category_counts_defaults_to_zero():
    export = make_export()
    del export["summary"]["asset_category_counts"]

    card = render_financial_shape_card(export)

    assert "Asset Mix:" in card
    assert "- stock: 0" in card
    assert "- real_estate: 0" in card
    assert "- business_interest: 0" in card
    assert "- bank_account: 0" in card
    assert "- mutual_fund: 0" in card
    assert "- option: 0" in card
    assert "- other: 0" in card
    assert "- unknown: 0" in card


def test_render_financial_shape_card_zero_count_categories_still_render():
    card = render_financial_shape_card(make_export())

    assert "- business_interest: 0" in card
    assert "- mutual_fund: 0" in card
    assert "- option: 0" in card
    assert "- unknown: 0" in card
