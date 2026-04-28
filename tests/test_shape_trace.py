import sqlite3
import pytest
from pathlib import Path

from transparencyx.db.schema import get_schema_sql
from transparencyx.shape.trace import build_financial_shape_trace
from transparencyx.shape.summary import build_financial_shape_summary


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
    conn.commit()
    conn.close()
    return path


def test_trace_keeps_all_asset_rows_when_summary_filters_noise(db_path):
    """Trace asset rows stay unfiltered while summary counts only usable assets."""
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
        (1, 1, 'NVIDIA [OP] SP', 'N/A', '$10-$20', 10, 20, 15, 'HIGH', 'now')
    """)

    cursor.execute("""
        INSERT INTO trades (politician_id, asset_name, transaction_type, amount_range_text, amount_min, amount_max, amount_mid)
        VALUES
        (1, 'X', 'BUY', '$1-$5', 1, 5, 3),
        (1, 'Y', 'SELL', '$10-$20', 10, 20, 15),
        (1, 'Z', 'BUY', 'Over $50,000', 50000, NULL, 50000)
    """)
    conn.commit()
    conn.close()

    summary = build_financial_shape_summary(db_path, 1)
    trace = build_financial_shape_trace(db_path, 1)

    assert trace["politician_id"] == 1

    # Lists, not integers
    assert isinstance(trace["assets"]["count_rows"], list)
    assert isinstance(trace["trades"]["count_rows"], list)

    # Trace keeps all asset rows, summary filters parser-noise assets.
    assert len(trace["assets"]["count_rows"]) == 2
    assert summary.asset_count == 1
    assert len(trace["trades"]["count_rows"]) == summary.trade_count

    # All returned values are ints (row IDs)
    assert all(isinstance(i, int) for i in trace["assets"]["count_rows"])
    assert all(isinstance(i, int) for i in trace["trades"]["count_rows"])


def test_trace_bounds_filters_correctly(db_path):
    """bounds_rows must exclude row IDs where min or max is NULL."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO raw_disclosures (id, source_chamber, source_name, filing_year, retrieved_at, raw_metadata_json, created_at)
        VALUES (1, 'house', 'test', 2023, 'now', '{}', 'now')
    """)

    # Asset: 2 complete, 1 missing max
    cursor.execute("""
        INSERT INTO normalized_assets (raw_disclosure_id, politician_id, asset_name, asset_category, original_value_range, value_min, value_max, value_midpoint, confidence, created_at)
        VALUES
        (1, 1, 'A', 'N/A', '$1-$5', 1, 5, 3, 'HIGH', 'now'),
        (1, 1, 'B', 'N/A', '$10-$20', 10, 20, 15, 'HIGH', 'now'),
        (1, 1, 'C', 'N/A', 'Over $50,000', 50000, NULL, 50000, 'LOW', 'now')
    """)

    # Trades: 1 complete, 2 missing max
    cursor.execute("""
        INSERT INTO trades (politician_id, asset_name, transaction_type, amount_range_text, amount_min, amount_max, amount_mid)
        VALUES
        (1, 'X', 'BUY', '$1-$5', 1, 5, 3),
        (1, 'Y', 'BUY', 'Over $50,000', 50000, NULL, 50000),
        (1, 'Z', 'BUY', 'Over $100,000', 100000, NULL, 100000)
    """)
    conn.commit()

    # Capture the auto-assigned IDs
    cursor.execute("SELECT id FROM normalized_assets ORDER BY id ASC")
    asset_ids = [row[0] for row in cursor.fetchall()]

    cursor.execute("SELECT id FROM trades ORDER BY id ASC")
    trade_ids = [row[0] for row in cursor.fetchall()]
    conn.close()

    trace = build_financial_shape_trace(db_path, 1)

    # count_rows includes all
    assert trace["assets"]["count_rows"] == asset_ids
    assert trace["trades"]["count_rows"] == trade_ids

    # bounds_rows excludes NULL-max rows
    assert len(trace["assets"]["bounds_rows"]) == 2
    assert asset_ids[2] not in trace["assets"]["bounds_rows"]

    assert len(trace["trades"]["bounds_rows"]) == 1
    assert trade_ids[1] not in trace["trades"]["bounds_rows"]
    assert trade_ids[2] not in trace["trades"]["bounds_rows"]


def test_trace_midpoint_includes_partial_rows(db_path):
    """midpoint_rows must include row IDs with a midpoint even if bounds are incomplete."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO raw_disclosures (id, source_chamber, source_name, filing_year, retrieved_at, raw_metadata_json, created_at)
        VALUES (1, 'house', 'test', 2023, 'now', '{}', 'now')
    """)

    # 2 assets with midpoints (one has NULL max), 1 asset with NULL midpoint
    cursor.execute("""
        INSERT INTO normalized_assets (raw_disclosure_id, politician_id, asset_name, asset_category, original_value_range, value_min, value_max, value_midpoint, confidence, created_at)
        VALUES
        (1, 1, 'A', 'N/A', '$1-$5', 1, 5, 3, 'HIGH', 'now'),
        (1, 1, 'B', 'N/A', 'Over $50,000', 50000, NULL, 50000, 'LOW', 'now'),
        (1, 1, 'C', 'N/A', 'N/A', NULL, NULL, NULL, 'LOW', 'now')
    """)

    # 3 trades: 2 with midpoints (one has NULL max), 1 with NULL midpoint
    cursor.execute("""
        INSERT INTO trades (politician_id, asset_name, transaction_type, amount_range_text, amount_min, amount_max, amount_mid)
        VALUES
        (1, 'X', 'BUY', '$1-$5', 1, 5, 3),
        (1, 'Y', 'BUY', 'Over $50,000', 50000, NULL, 50000),
        (1, 'Z', 'BUY', 'N/A', NULL, NULL, NULL)
    """)
    conn.commit()

    # Capture IDs
    cursor.execute("SELECT id FROM normalized_assets ORDER BY id ASC")
    asset_ids = [row[0] for row in cursor.fetchall()]

    cursor.execute("SELECT id FROM trades ORDER BY id ASC")
    trade_ids = [row[0] for row in cursor.fetchall()]
    conn.close()

    trace = build_financial_shape_trace(db_path, 1)

    # count_rows = all 3
    assert len(trace["assets"]["count_rows"]) == 3
    assert len(trace["trades"]["count_rows"]) == 3

    # bounds_rows = only row A (complete bounds)
    assert trace["assets"]["bounds_rows"] == [asset_ids[0]]
    assert trace["trades"]["bounds_rows"] == [trade_ids[0]]

    # midpoint_rows = rows A and B (both have midpoints), excludes C (NULL midpoint)
    assert trace["assets"]["midpoint_rows"] == [asset_ids[0], asset_ids[1]]
    assert trace["trades"]["midpoint_rows"] == [trade_ids[0], trade_ids[1]]

    # Partial row B: in midpoint_rows but NOT in bounds_rows
    assert asset_ids[1] in trace["assets"]["midpoint_rows"]
    assert asset_ids[1] not in trace["assets"]["bounds_rows"]
    assert trade_ids[1] in trace["trades"]["midpoint_rows"]
    assert trade_ids[1] not in trace["trades"]["bounds_rows"]
