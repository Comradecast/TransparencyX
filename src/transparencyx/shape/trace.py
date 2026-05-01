from pathlib import Path
from typing import List

from transparencyx.db.database import get_connection


def _fetch_ids(cursor, query: str, params: tuple) -> List[int]:
    """Execute a query and return a flat list of IDs from the first column."""
    cursor.execute(query, params)
    return [row[0] for row in cursor.fetchall()]


def _fetch_trade_detail_rows(cursor, politician_id: int) -> list[dict]:
    cursor.execute(
        """
        SELECT
            id,
            asset_name,
            trade_date,
            transaction_type,
            amount_range_text,
            amount_min,
            amount_max
        FROM trades
        WHERE politician_id = ?
        ORDER BY id ASC
        """,
        (politician_id,),
    )
    return [dict(row) for row in cursor.fetchall()]


def build_financial_shape_trace(db_path: Path, politician_id: int) -> dict:
    """
    Returns traceability metadata listing the source row IDs
    that contributed to each component of the financial shape summary.

    For each domain (assets, trades):
      - count_rows: all row IDs for the politician
      - bounds_rows: row IDs where both min and max are non-null
      - midpoint_rows: row IDs where midpoint is non-null
      - detail_rows: factual trade row fields used for trace review

    All lists are ordered by id ASC.
    """
    with get_connection(db_path) as conn:
        cursor = conn.cursor()

        # Asset traces
        asset_count_rows = _fetch_ids(cursor,
            "SELECT id FROM normalized_assets WHERE politician_id = ? ORDER BY id ASC",
            (politician_id,))

        asset_bounds_rows = _fetch_ids(cursor,
            "SELECT id FROM normalized_assets WHERE politician_id = ? AND value_min IS NOT NULL AND value_max IS NOT NULL ORDER BY id ASC",
            (politician_id,))

        asset_midpoint_rows = _fetch_ids(cursor,
            "SELECT id FROM normalized_assets WHERE politician_id = ? AND value_midpoint IS NOT NULL ORDER BY id ASC",
            (politician_id,))

        # Trade traces
        trade_count_rows = _fetch_ids(cursor,
            "SELECT id FROM trades WHERE politician_id = ? ORDER BY id ASC",
            (politician_id,))

        trade_bounds_rows = _fetch_ids(cursor,
            "SELECT id FROM trades WHERE politician_id = ? AND amount_min IS NOT NULL AND amount_max IS NOT NULL ORDER BY id ASC",
            (politician_id,))

        trade_midpoint_rows = _fetch_ids(cursor,
            "SELECT id FROM trades WHERE politician_id = ? AND amount_mid IS NOT NULL ORDER BY id ASC",
            (politician_id,))

        trade_detail_rows = _fetch_trade_detail_rows(cursor, politician_id)

        return {
            "politician_id": politician_id,
            "assets": {
                "count_rows": asset_count_rows,
                "bounds_rows": asset_bounds_rows,
                "midpoint_rows": asset_midpoint_rows,
            },
            "trades": {
                "count_rows": trade_count_rows,
                "bounds_rows": trade_bounds_rows,
                "midpoint_rows": trade_midpoint_rows,
                "detail_rows": trade_detail_rows,
            },
        }
