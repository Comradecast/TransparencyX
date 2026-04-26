import sqlite3
import pytest
from pathlib import Path
import json

from transparencyx.db.schema import get_schema_sql
from transparencyx.shape.summary import build_financial_shape_summary, summary_to_dict

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
    assert summary.trade_volume_min == 111.0
    assert summary.trade_volume_max == 25.0
    assert summary.trade_volume_midpoint == 118.0
    assert summary.trade_activity == "LOW"

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
    
    # Ensure it's json serializable
    json.dumps(d)
