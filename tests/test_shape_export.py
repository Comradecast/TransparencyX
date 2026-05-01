import sqlite3
import json
import pytest
from pathlib import Path

from transparencyx.db.schema import get_schema_sql
from transparencyx.shape.export import build_financial_shape_export


ASSET_SUMMARY_ROW_KEYS = {
    "asset_id",
    "asset_name",
    "linked_transaction_count",
}


@pytest.fixture
def db_path(tmp_path):
    path = tmp_path / "test.sqlite"
    conn = sqlite3.connect(path)
    conn.executescript(get_schema_sql())

    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO politicians (id, first_name, last_name, full_name, chamber, created_at, updated_at)
        VALUES (1, 'Jane', 'Doe', 'Doe, Jane', 'house', '2023-01-01', '2023-01-01')
    """)

    cursor.execute("""
        INSERT INTO raw_disclosures (id, source_chamber, source_name, filing_year, retrieved_at, raw_metadata_json, created_at)
        VALUES (1, 'house', 'test', 2023, 'now', '{}', 'now')
    """)

    cursor.execute("""
        INSERT INTO normalized_assets (raw_disclosure_id, politician_id, asset_name, asset_category, original_value_range, value_min, value_max, value_midpoint, confidence, created_at)
        VALUES
        (1, 1, 'StockA', 'N/A', '$1,001-$15,000', 1001, 15000, 8000, 'HIGH', 'now')
    """)

    cursor.execute("""
        INSERT INTO trades (politician_id, asset_name, transaction_type, amount_range_text, amount_min, amount_max, amount_mid)
        VALUES
        (1, 'StockA', 'BUY', '$1,001-$15,000', 1001, 15000, 8000)
    """)

    conn.commit()
    conn.close()
    return path


def test_shape_export_contains_summary_and_trace(db_path):
    """Export must contain both summary and trace dicts with expected keys."""
    export = build_financial_shape_export(db_path, 1)

    assert "politician_id" in export
    assert "summary" in export
    assert "trace" in export

    # Summary keys
    summary = export["summary"]
    assert "asset_count" in summary
    assert "transaction_count" in summary
    assert "asset_summaries" in summary
    assert "trade_count" in summary
    assert "net_worth_band" in summary
    assert "summary_label" in summary
    assert summary["asset_summaries"] == [
        {
            "asset_id": 1,
            "asset_name": "StockA",
            "linked_transaction_count": 1,
        }
    ]
    for row in summary["asset_summaries"]:
        assert set(row) == ASSET_SUMMARY_ROW_KEYS
        assert isinstance(row["linked_transaction_count"], int)
        assert not isinstance(row["linked_transaction_count"], bool)
        assert row["linked_transaction_count"] >= 0

    # Trace keys
    trace = export["trace"]
    assert "assets" in trace
    assert "trades" in trace
    assert isinstance(trace["assets"]["count_rows"], list)
    assert isinstance(trace["trades"]["count_rows"], list)


def test_shape_export_is_json_serializable(db_path):
    """The entire export dict must be JSON serializable."""
    export = build_financial_shape_export(db_path, 1)
    serialized = json.dumps(export)
    assert isinstance(serialized, str)
    roundtrip = json.loads(serialized)
    assert roundtrip == export


def test_shape_export_ids_are_consistent(db_path):
    """politician_id must be consistent across the top level, summary, and trace."""
    export = build_financial_shape_export(db_path, 1)

    assert export["politician_id"] == 1
    assert export["summary"]["politician_id"] == 1
    assert export["trace"]["politician_id"] == 1
