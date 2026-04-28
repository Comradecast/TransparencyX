from transparencyx.normalize.assets import classify_asset_quality


def asset_row(asset_name, value_min=1001, value_max=15000):
    return {
        "asset_name": asset_name,
        "value_min": value_min,
        "value_max": value_max,
    }


def test_classify_asset_quality_rejects_options_assets():
    row = asset_row("NVIDIA [OP] SP", 1000001, 5000000)

    assert classify_asset_quality(row) == "parser_noise"


def test_classify_asset_quality_rejects_rows_without_bounds():
    row = asset_row("Apple Inc. (AAPL) [ST] SP", None, None)

    assert classify_asset_quality(row) == "parser_noise"


def test_classify_asset_quality_rejects_embedded_header_text():
    assert classify_asset_quality(asset_row("Asset Owner Value of Asset")) == "parser_noise"
    assert classify_asset_quality(asset_row("Income Type details")) == "parser_noise"
    assert classify_asset_quality(asset_row("Tx. marker")) == "parser_noise"


def test_classify_asset_quality_rejects_transaction_text():
    row = asset_row("Apple Inc. (AAPL) [ST] SP 05/8/2023 S")

    assert classify_asset_quality(row) == "parser_noise"


def test_classify_asset_quality_rejects_partial_sale_text():
    row = asset_row("Apple Inc. (AAPL) [ST] SP S (partial)")

    assert classify_asset_quality(row) == "parser_noise"


def test_classify_asset_quality_accepts_usable_asset():
    row = asset_row("Apple Inc. (AAPL) [ST] SP", 1001, 15000)

    assert classify_asset_quality(row) == "usable_asset"
