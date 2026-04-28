from transparencyx.cli import (
    format_normalized_asset_audit_table,
    get_normalized_asset_audit_rows,
)
from transparencyx.db.database import get_connection, initialize_database


def test_get_normalized_asset_audit_rows_ordered_by_id(tmp_path):
    db_path = tmp_path / "audit.sqlite"
    initialize_database(db_path)

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        now = "2026-01-01T00:00:00Z"
        cursor.execute(
            """
            INSERT INTO politicians
                (id, first_name, last_name, full_name, chamber, created_at, updated_at)
            VALUES (1, 'Test', 'Member', 'Member, Test', 'house', ?, ?)
            """,
            (now, now),
        )
        cursor.execute(
            """
            INSERT INTO raw_disclosures
                (id, politician_id, source_chamber, source_name, filing_year,
                 retrieved_at, raw_metadata_json, created_at)
            VALUES (1, 1, 'house', 'test', 2023, ?, '{}', ?)
            """,
            (now, now),
        )
        cursor.execute(
            """
            INSERT INTO normalized_assets
                (id, raw_disclosure_id, politician_id, asset_name, asset_category,
                 original_value_range, value_min, value_max, value_midpoint,
                 confidence, created_at)
            VALUES
                (2, 1, 1, 'Second Asset', 'unknown', '$15,001 - $50,000',
                 15001, 50000, 32500, 'medium', ?),
                (1, 1, 1, 'First Asset', 'unknown', '$1,001 - $15,000',
                 1001, 15000, 8000, 'medium', ?)
            """,
            (now, now),
        )

    rows = get_normalized_asset_audit_rows(db_path)

    assert [row["id"] for row in rows] == [1, 2]
    assert rows[0] == {
        "id": 1,
        "asset_name": "First Asset",
        "asset_category": "unknown",
        "original_value_range": "$1,001 - $15,000",
        "value_min": 1001,
        "value_max": 15000,
        "value_midpoint": 8000,
    }


def test_format_normalized_asset_audit_table():
    rows = [
        {
            "id": 1,
            "asset_name": "First Asset",
            "asset_category": "unknown",
            "original_value_range": "$1,001 - $15,000",
            "value_min": 1001,
            "value_max": 15000,
            "value_midpoint": 8000,
        },
        {
            "id": 2,
            "asset_name": "Unparsed Asset",
            "asset_category": "unknown",
            "original_value_range": "$GARBAGE",
            "value_min": None,
            "value_max": None,
            "value_midpoint": None,
        },
    ]

    table = format_normalized_asset_audit_table(rows)

    assert table == (
        "id | asset_name | asset_category | original_value_range | value_min | value_max | value_midpoint\n"
        "1 | First Asset | unknown | $1,001 - $15,000 | 1001 | 15000 | 8000\n"
        "2 | Unparsed Asset | unknown | $GARBAGE |  |  | "
    )
