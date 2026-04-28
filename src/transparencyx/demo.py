"""
Demo runner for TransparencyX.

Creates a small demonstration database and produces a shape export,
without modifying any existing logic.
"""
from pathlib import Path

from transparencyx.db.database import get_connection
from transparencyx.db.schema import get_schema_sql
from transparencyx.shape.export import build_financial_shape_export


def create_demo_database(db_path: Path) -> None:
    """
    Create a self-contained demo SQLite database with one politician,
    a mix of complete and partial asset rows, and a mix of complete
    and partial trade rows.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = get_connection(db_path)
    conn.executescript(get_schema_sql())

    cursor = conn.cursor()

    # Politician
    cursor.execute("""
        INSERT OR IGNORE INTO politicians
            (id, first_name, last_name, full_name, chamber, created_at, updated_at)
        VALUES
            (1, 'Demo', 'Politician', 'Politician, Demo', 'house', '2024-01-01', '2024-01-01')
    """)

    # Raw disclosure (needed as FK for normalized_assets)
    cursor.execute("""
        INSERT OR IGNORE INTO raw_disclosures
            (id, source_chamber, source_name, filing_year, retrieved_at, raw_metadata_json, created_at)
        VALUES
            (1, 'house', 'demo', 2024, '2024-01-01', '{}', '2024-01-01')
    """)

    # Normalized assets: 1 complete range, 1 partial (max NULL), 1 complete range
    cursor.execute("""
        INSERT OR IGNORE INTO normalized_assets
            (id, raw_disclosure_id, politician_id, asset_name, asset_category,
             original_value_range, value_min, value_max, value_midpoint, confidence, created_at)
        VALUES
            (1, 1, 1, 'US Treasury Bonds', 'Government Securities',
             '$1,001 - $15,000', 1001, 15000, 8000, 'HIGH', '2024-01-01'),
            (2, 1, 1, 'Private Equity Fund', 'Investment Fund',
             'Over $50,000', 50000, NULL, 50000, 'LOW', '2024-01-01'),
            (3, 1, 1, 'Municipal Bond Fund', 'Government Securities',
             '$15,001 - $50,000', 15001, 50000, 32500, 'HIGH', '2024-01-01')
    """)

    # Trades: 1 complete range, 1 partial (max NULL)
    cursor.execute("""
        INSERT OR IGNORE INTO trades
            (id, politician_id, asset_name, transaction_type,
             amount_range_text, amount_min, amount_max, amount_mid)
        VALUES
            (1, 1, 'US Treasury Bonds', 'BUY',
             '$1,001 - $15,000', 1001, 15000, 8000),
            (2, 1, 'Private Equity Fund', 'BUY',
             'Over $50,000', 50000, NULL, 50000)
    """)

    conn.commit()
    conn.close()


def run_demo(db_path: Path) -> dict:
    """
    Create the demo database and return the shape export for politician 1.
    """
    create_demo_database(db_path)
    return build_financial_shape_export(db_path, 1)
