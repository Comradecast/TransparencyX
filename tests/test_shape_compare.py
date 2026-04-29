from transparencyx.shape.compare import render_shape_comparison


def make_export(politician_id, net_worth_band, asset_count):
    return {
        "politician_id": politician_id,
        "summary": {
            "net_worth_band": net_worth_band,
            "asset_count": asset_count,
        },
    }


def test_band_delta_correctness_positive():
    comparison = render_shape_comparison(
        make_export(1, "VERY_HIGH", 56),
        make_export(2, "MEDIUM", 18),
    )

    assert "  Net worth band: +2 levels" in comparison


def test_band_delta_correctness_negative():
    comparison = render_shape_comparison(
        make_export(1, "LOW", 56),
        make_export(2, "HIGH", 18),
    )

    assert "  Net worth band: -2 levels" in comparison


def test_asset_count_delta():
    comparison = render_shape_comparison(
        make_export(1, "VERY_HIGH", 56),
        make_export(2, "MEDIUM", 18),
    )

    assert "  Asset count: +38" in comparison


def test_output_structure():
    comparison = render_shape_comparison(
        make_export(1, "VERY_HIGH", 56),
        make_export(2, "MEDIUM", 18),
    )

    assert "FINANCIAL SHAPE COMPARISON" in comparison
    assert "Politician A (ID: 1):" in comparison
    assert "Politician B (ID: 2):" in comparison
    assert "Delta:" in comparison


def test_deterministic_formatting():
    export_a = make_export(1, "VERY_HIGH", 56)
    export_b = make_export(2, "MEDIUM", 18)

    assert render_shape_comparison(export_a, export_b) == render_shape_comparison(export_a, export_b)
