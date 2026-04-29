from transparencyx.profile.table import get_top_asset_category, render_batch_summary_table


def test_get_top_asset_category():
    category = get_top_asset_category({
        "stock": 2,
        "real_estate": 5,
        "business_interest": 3,
    })

    assert category == "real_estate"


def test_get_top_asset_category_deterministic_tie_break():
    category = get_top_asset_category({
        "business_interest": 4,
        "real_estate": 4,
        "stock": 4,
    })

    assert category == "stock"


def test_get_top_asset_category_missing_counts():
    assert get_top_asset_category({}) == "unknown"
    assert get_top_asset_category(None) == "unknown"
    assert get_top_asset_category({"stock": 0, "real_estate": 0}) == "unknown"


def test_render_batch_summary_table_includes_expected_columns():
    table = render_batch_summary_table([])

    assert table == "member_name | net_worth_band | asset_count | income_band | income_count | top_asset_category"


def test_render_batch_summary_table_renders_multiple_profiles_in_order():
    profiles = [
        {
            "member_name": "Alpha Member",
            "shape_export": {
                "summary": {
                    "net_worth_band": "HIGH",
                    "asset_count": 3,
                    "income_band": "LOW",
                    "income_count": 1,
                    "asset_category_counts": {
                        "stock": 2,
                        "real_estate": 1,
                    },
                },
            },
        },
        {
            "member_name": "Beta Member",
            "shape_export": {
                "summary": {
                    "net_worth_band": "VERY_HIGH",
                    "asset_count": 9,
                    "income_band": "MODERATE",
                    "income_count": 4,
                    "asset_category_counts": {
                        "business_interest": 6,
                        "stock": 1,
                    },
                },
            },
        },
    ]

    table = render_batch_summary_table(profiles)

    assert table.splitlines() == [
        "member_name | net_worth_band | asset_count | income_band | income_count | top_asset_category",
        "Alpha Member | HIGH | 3 | LOW | 1 | stock",
        "Beta Member | VERY_HIGH | 9 | MODERATE | 4 | business_interest",
    ]


def test_render_batch_summary_table_missing_values_render_unknown():
    table = render_batch_summary_table([{}])

    assert table.splitlines()[1] == "Unknown | Unknown | Unknown | Unknown | Unknown | unknown"
