import sqlite3
import pytest
from pathlib import Path
import json

from transparencyx.db.schema import get_schema_sql
from transparencyx.shape.summary import (
    build_financial_shape_summary, 
    summary_to_dict,
    compute_asset_category_counts,
    compute_income_shape,
    extract_income_signal,
    get_net_worth_band,
    get_asset_density,
    get_trade_volume_band,
    build_summary_label,
    FinancialShapeSummary
)

@pytest.fixture
def db_path(tmp_path):
    path = tmp_path / "test.sqlite"
    conn = sqlite3.connect(path)
    conn.executescript(get_schema_sql())
    
    # Insert a dummy politician
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO politicians (id, first_name, last_name, full_name, chamber, created_at, updated_at)
        VALUES (1, 'Jane', 'Doe', 'Doe, Jane', 'house', '2023-01-01', '2023-01-01')
    """)
    conn.commit()
    conn.close()
    return path

def test_empty_politician_shape(db_path):
    summary = build_financial_shape_summary(db_path, 1)
    
    assert summary.politician_id == 1
    assert summary.asset_count == 0
    assert summary.asset_value_min is None
    assert summary.asset_value_max is None
    assert summary.asset_value_midpoint is None
    
    assert summary.trade_count == 0
    assert summary.trade_volume_min is None
    assert summary.trade_volume_max is None
    assert summary.trade_volume_midpoint is None
    
    assert summary.trade_activity == "NONE"
    
    assert summary.net_worth_band == "UNKNOWN"
    assert summary.asset_density == "NONE"
    assert summary.trade_volume_band == "UNKNOWN"
    assert summary.summary_label == "No disclosed financial activity"
    assert summary.asset_category_counts == {
        "stock": 0,
        "real_estate": 0,
        "business_interest": 0,
        "bank_account": 0,
        "mutual_fund": 0,
        "option": 0,
        "other": 0,
        "unknown": 0,
    }
    assert summary.income_count == 0
    assert summary.income_min is None
    assert summary.income_max is None
    assert summary.income_midpoint is None
    assert summary.income_type_counts == {
        "dividends": 0,
        "interest": 0,
        "rent": 0,
        "partnership_income": 0,
        "partnership_loss": 0,
        "capital_gains": 0,
        "other": 0,
    }
    assert summary.income_band == "UNKNOWN"

def test_extract_income_signal_extracts_dividends_range_after_keyword():
    signal = extract_income_signal("$1,001 - $15,000 Dividends $5,001 - $15,000")

    assert signal == {
        "income_type": "dividends",
        "income_min": 5001.0,
        "income_max": 15000.0,
        "income_midpoint": 10000.5,
    }

def test_extract_income_signal_does_not_use_asset_value_range():
    signal = extract_income_signal("$100,001 - $250,000 None")

    assert signal is None

def test_extract_income_signal_parses_partnership_loss_without_space_before_dollar():
    signal = extract_income_signal("$15,001 - $50,000Partnership Loss$50,001 - $100,000")

    assert signal == {
        "income_type": "partnership_loss",
        "income_min": 50001.0,
        "income_max": 100000.0,
        "income_midpoint": 75000.5,
    }

def test_compute_income_shape_type_counts_include_all_categories():
    shape = compute_income_shape([
        {"original_value_range": "$1 - $1,000 Dividends $1 - $200"},
        {"original_value_range": "$1 - $1,000 Interest $201 - $1,000"},
        {"original_value_range": "$1 - $1,000 Rent $5,001 - $15,000"},
        {"original_value_range": "$1 - $1,000 Partnership Income $50,001 - $100,000"},
        {"original_value_range": "$1 - $1,000 Partnership Loss$50,001 - $100,000"},
        {"original_value_range": "$1 - $1,000 Capital Gains $100,001 - $1,000,000"},
    ])

    assert shape["income_count"] == 6
    assert shape["income_type_counts"] == {
        "dividends": 1,
        "interest": 1,
        "rent": 1,
        "partnership_income": 1,
        "partnership_loss": 1,
        "capital_gains": 1,
        "other": 0,
    }

def test_compute_income_shape_no_income_returns_unknown_and_none_values():
    shape = compute_income_shape([
        {"original_value_range": "$1,001 - $15,000 None"},
        {"original_value_range": "$5,001 - $15,000 Dividends"},
    ])

    assert shape == {
        "income_count": 0,
        "income_min": None,
        "income_max": None,
        "income_midpoint": None,
        "income_type_counts": {
            "dividends": 0,
            "interest": 0,
            "rent": 0,
            "partnership_income": 0,
            "partnership_loss": 0,
            "capital_gains": 0,
            "other": 0,
        },
        "income_band": "UNKNOWN",
    }

def test_compute_asset_category_counts_correct_counting():
    counts = compute_asset_category_counts([
        {"asset_category": "stock"},
        {"asset_category": "stock"},
        {"asset_category": "real_estate"},
        {"asset_category": "bank_account"},
        {"asset_category": "business_interest"},
        {"asset_category": "mutual_fund"},
        {"asset_category": "option"},
        {"asset_category": "other"},
    ])

    assert counts == {
        "stock": 2,
        "real_estate": 1,
        "business_interest": 1,
        "bank_account": 1,
        "mutual_fund": 1,
        "option": 1,
        "other": 1,
        "unknown": 0,
    }

def test_compute_asset_category_counts_unknown_fallback():
    counts = compute_asset_category_counts([
        {"asset_category": "stock"},
        {"asset_category": "N/A"},
    ])

    assert counts["stock"] == 1
    assert counts["unknown"] == 1

def test_compute_asset_category_counts_all_categories_present():
    counts = compute_asset_category_counts([])

    assert list(counts.keys()) == [
        "stock",
        "real_estate",
        "business_interest",
        "bank_account",
        "mutual_fund",
        "option",
        "other",
        "unknown",
    ]
    assert all(count == 0 for count in counts.values())

def test_assets_aggregate_correctly(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO raw_disclosures (id, source_chamber, source_name, filing_year, retrieved_at, raw_metadata_json, created_at)
        VALUES (1, 'house', 'test', 2023, 'now', '{}', 'now')
    """)
    
    # Insert some assets
    cursor.execute("""
        INSERT INTO normalized_assets (raw_disclosure_id, politician_id, asset_name, asset_category, original_value_range, value_min, value_max, value_midpoint, confidence, created_at)
        VALUES 
        (1, 1, 'A', 'N/A', '1-5', 1, 5, 3, 'HIGH', 'now'),
        (1, 1, 'B', 'N/A', '10-20', 10, 20, 15, 'HIGH', 'now')
    """)
    conn.commit()
    conn.close()
    
    summary = build_financial_shape_summary(db_path, 1)
    
    assert summary.asset_count == 2
    assert summary.asset_value_min == 11.0
    assert summary.asset_value_max == 25.0
    assert summary.asset_value_midpoint == 18.0

def test_assets_aggregate_only_usable_assets(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO raw_disclosures (id, source_chamber, source_name, filing_year, retrieved_at, raw_metadata_json, created_at)
        VALUES (1, 'house', 'test', 2023, 'now', '{}', 'now')
    """)
    
    cursor.execute("""
        INSERT INTO normalized_assets (raw_disclosure_id, politician_id, asset_name, asset_category, original_value_range, value_min, value_max, value_midpoint, confidence, created_at)
        VALUES 
        (1, 1, 'Apple Inc. (AAPL) [ST] SP', 'N/A', '$1-$5', 1, 5, 3, 'HIGH', 'now'),
        (1, 1, 'NVIDIA [OP] SP', 'N/A', '$10-$20 Dividends $1 - $200', 10, 20, 15, 'HIGH', 'now'),
        (1, 1, 'Amazon.com, Inc. (AMZN) [ST] SP Asset Owner', 'N/A', '$100-$200 Interest $201 - $1,000', 100, 200, 150, 'HIGH', 'now'),
        (1, 1, 'Apple Inc. (AAPL) [ST] SP 05/8/2023 S', 'N/A', '$500-$1000 Rent $5,001 - $15,000', 500, 1000, 750, 'HIGH', 'now'),
        (1, 1, 'Microsoft Corporation (MSFT) [ST] SP', 'N/A', '$10-$20', NULL, NULL, NULL, 'LOW', 'now')
    """)
    conn.commit()
    conn.close()
    
    summary = build_financial_shape_summary(db_path, 1)
    
    assert summary.asset_count == 1
    assert summary.asset_value_min == 1.0
    assert summary.asset_value_max == 5.0
    assert summary.asset_value_midpoint == 3.0
    assert summary.asset_density == "LOW"
    assert summary.asset_category_counts == {
        "stock": 0,
        "real_estate": 0,
        "business_interest": 0,
        "bank_account": 0,
        "mutual_fund": 0,
        "option": 0,
        "other": 0,
        "unknown": 1,
    }
    assert summary.income_count == 0
    assert summary.income_band == "UNKNOWN"

def test_trades_aggregate_correctly(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Insert some trades
    cursor.execute("""
        INSERT INTO trades (politician_id, asset_name, transaction_type, amount_range_text, amount_min, amount_max, amount_mid)
        VALUES 
        (1, 'A', 'BUY', '1-5', 1, 5, 3),
        (1, 'B', 'SELL', '10-20', 10, 20, 15),
        (1, 'C', 'BUY', 'NullMax', 100, NULL, 100)
    """)
    conn.commit()
    conn.close()
    
    summary = build_financial_shape_summary(db_path, 1)
    
    assert summary.trade_count == 3
    assert summary.trade_volume_min == 11.0
    assert summary.trade_volume_max == 25.0
    assert summary.trade_volume_midpoint == 118.0
    assert summary.trade_activity == "LOW"

def test_trade_bounds_ignore_null_max(db_path):
    """Rows with NULL max must be excluded from bounds but still counted."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO trades (politician_id, asset_name, transaction_type, amount_range_text, amount_min, amount_max, amount_mid)
        VALUES 
        (1, 'X', 'BUY', '$1,001-$15,000', 1001, 15000, 8000),
        (1, 'Y', 'BUY', 'Over $50,000', 50000, NULL, 50000)
    """)
    conn.commit()
    conn.close()

    summary = build_financial_shape_summary(db_path, 1)

    assert summary.trade_count == 2
    # Only row X has complete bounds
    assert summary.trade_volume_min == 1001.0
    assert summary.trade_volume_max == 15000.0
    # Midpoint includes both rows
    assert summary.trade_volume_midpoint == 58000.0
    # Invariant: min <= max
    assert summary.trade_volume_min <= summary.trade_volume_max

def test_trade_bounds_all_null_max(db_path):
    """When every row has NULL max, bounds must be None."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO trades (politician_id, asset_name, transaction_type, amount_range_text, amount_min, amount_max, amount_mid)
        VALUES 
        (1, 'A', 'BUY', 'Over $50,000', 50000, NULL, 50000),
        (1, 'B', 'SELL', 'Over $100,000', 100000, NULL, 100000)
    """)
    conn.commit()
    conn.close()

    summary = build_financial_shape_summary(db_path, 1)

    assert summary.trade_count == 2
    assert summary.trade_volume_min is None
    assert summary.trade_volume_max is None
    # Midpoint still aggregates
    assert summary.trade_volume_midpoint == 150000.0

def test_trade_midpoint_independent_of_bounds(db_path):
    """Midpoint aggregation must include all rows regardless of bound completeness."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO trades (politician_id, asset_name, transaction_type, amount_range_text, amount_min, amount_max, amount_mid)
        VALUES 
        (1, 'A', 'BUY', '$1-$5', 1, 5, 3),
        (1, 'B', 'BUY', 'Over $1,000', 1000, NULL, 1000),
        (1, 'C', 'SELL', '$10-$20', 10, 20, 15)
    """)
    conn.commit()
    conn.close()

    summary = build_financial_shape_summary(db_path, 1)

    # Bounds only from rows A and C (complete bounds)
    assert summary.trade_volume_min == 11.0
    assert summary.trade_volume_max == 25.0
    # Midpoint from all three rows
    assert summary.trade_volume_midpoint == 1018.0
    # Invariant
    assert summary.trade_volume_min <= summary.trade_volume_max

@pytest.mark.parametrize("trade_count, expected_activity", [
    (0, "NONE"),
    (1, "LOW"),
    (5, "LOW"),
    (6, "MEDIUM"),
    (20, "MEDIUM"),
    (21, "HIGH"),
    (100, "HIGH")
])
def test_trade_activity_thresholds(db_path, trade_count, expected_activity):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    for i in range(trade_count):
        cursor.execute(f"""
            INSERT INTO trades (politician_id, asset_name, transaction_type, amount_range_text, amount_min, amount_max, amount_mid)
            VALUES (1, 'A{i}', 'BUY', '1-5', 1, 5, 3)
        """)
    conn.commit()
    conn.close()
    
    summary = build_financial_shape_summary(db_path, 1)
    assert summary.trade_activity == expected_activity

def test_summary_to_dict(db_path):
    summary = build_financial_shape_summary(db_path, 1)
    d = summary_to_dict(summary)
    
    assert isinstance(d, dict)
    assert d["politician_id"] == 1
    assert d["asset_count"] == 0
    assert d["asset_value_min"] is None
    assert d["trade_activity"] == "NONE"
    assert d["net_worth_band"] == "UNKNOWN"
    assert d["asset_density"] == "NONE"
    assert d["trade_volume_band"] == "UNKNOWN"
    assert d["summary_label"] == "No disclosed financial activity"
    assert d["asset_category_counts"] == {
        "stock": 0,
        "real_estate": 0,
        "business_interest": 0,
        "bank_account": 0,
        "mutual_fund": 0,
        "option": 0,
        "other": 0,
        "unknown": 0,
    }
    assert d["income_count"] == 0
    assert d["income_min"] is None
    assert d["income_max"] is None
    assert d["income_midpoint"] is None
    assert d["income_type_counts"] == {
        "dividends": 0,
        "interest": 0,
        "rent": 0,
        "partnership_income": 0,
        "partnership_loss": 0,
        "capital_gains": 0,
        "other": 0,
    }
    assert d["income_band"] == "UNKNOWN"
    
    # Ensure it's json serializable
    json.dumps(d)

@pytest.mark.parametrize("val, expected", [
    (None, "UNKNOWN"),
    (0, "LOW"),
    (249_999, "LOW"),
    (250_000, "MODERATE"),
    (999_999, "MODERATE"),
    (1_000_000, "HIGH"),
    (4_999_999, "HIGH"),
    (5_000_000, "VERY_HIGH"),
    (100_000_000, "VERY_HIGH"),
])
def test_net_worth_band(val, expected):
    assert get_net_worth_band(val) == expected

@pytest.mark.parametrize("val, expected", [
    (0, "NONE"),
    (1, "LOW"),
    (5, "LOW"),
    (6, "MEDIUM"),
    (20, "MEDIUM"),
    (21, "HIGH"),
])
def test_asset_density_band(val, expected):
    assert get_asset_density(val) == expected

@pytest.mark.parametrize("val, expected", [
    (None, "UNKNOWN"),
    (0, "LOW"),
    (49_999, "LOW"),
    (50_000, "MODERATE"),
    (249_999, "MODERATE"),
    (250_000, "HIGH"),
    (999_999, "HIGH"),
    (1_000_000, "VERY_HIGH"),
])
def test_trade_volume_band(val, expected):
    assert get_trade_volume_band(val) == expected

def test_build_summary_label():
    def make_summary(ac, tc, ta, nwb, ad):
        return FinancialShapeSummary(
            politician_id=1, asset_count=ac, asset_value_min=None, asset_value_max=None, asset_value_midpoint=None,
            trade_count=tc, transaction_count=tc, trade_volume_min=None, trade_volume_max=None, trade_volume_midpoint=None,
            trade_activity=ta, net_worth_band=nwb, asset_density=ad, trade_volume_band="UNKNOWN", summary_label=""
        )
    
    # Empty
    assert build_summary_label(make_summary(0, 0, "NONE", "UNKNOWN", "NONE")) == "No disclosed financial activity"
    
    # Assets only
    assert build_summary_label(make_summary(1, 0, "NONE", "LOW", "LOW")) == "Low asset complexity, no trading activity"
    assert build_summary_label(make_summary(10, 0, "NONE", "MODERATE", "MEDIUM")) == "Medium asset complexity, no trading activity"
    assert build_summary_label(make_summary(25, 0, "NONE", "HIGH", "HIGH")) == "High disclosed wealth, no trading activity"
    assert build_summary_label(make_summary(5, 0, "NONE", "VERY_HIGH", "LOW")) == "Very high disclosed wealth, no trading activity"
    
    # Trades only
    assert build_summary_label(make_summary(0, 5, "LOW", "UNKNOWN", "NONE")) == "No disclosed assets, low trading activity"
    
    # Both
    assert build_summary_label(make_summary(5, 10, "MEDIUM", "VERY_HIGH", "LOW")) == "Very high disclosed wealth, medium trading activity"
