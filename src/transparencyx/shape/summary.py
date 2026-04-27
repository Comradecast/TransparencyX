from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from transparencyx.db.database import get_connection

@dataclass
class FinancialShapeSummary:
    politician_id: int
    asset_count: int
    asset_value_min: Optional[float]
    asset_value_max: Optional[float]
    asset_value_midpoint: Optional[float]
    trade_count: int
    trade_volume_min: Optional[float]
    trade_volume_max: Optional[float]
    trade_volume_midpoint: Optional[float]
    trade_activity: str
    net_worth_band: str
    asset_density: str
    trade_volume_band: str
    summary_label: str

def get_trade_activity(count: int) -> str:
    """
    Deterministic thresholds for trade activity:
    - NONE: 0 trades
    - LOW: 1-5 trades
    - MEDIUM: 6-20 trades
    - HIGH: >20 trades
    """
    if count == 0:
        return "NONE"
    elif 1 <= count <= 5:
        return "LOW"
    elif 6 <= count <= 20:
        return "MEDIUM"
    else:
        return "HIGH"

def get_net_worth_band(asset_value_midpoint: Optional[float]) -> str:
    if asset_value_midpoint is None:
        return "UNKNOWN"
    elif asset_value_midpoint < 250_000:
        return "LOW"
    elif asset_value_midpoint < 1_000_000:
        return "MODERATE"
    elif asset_value_midpoint < 5_000_000:
        return "HIGH"
    else:
        return "VERY_HIGH"

def get_asset_density(asset_count: int) -> str:
    if asset_count == 0:
        return "NONE"
    elif 1 <= asset_count <= 5:
        return "LOW"
    elif 6 <= asset_count <= 20:
        return "MEDIUM"
    else:
        return "HIGH"

def get_trade_volume_band(trade_volume_midpoint: Optional[float]) -> str:
    if trade_volume_midpoint is None:
        return "UNKNOWN"
    elif trade_volume_midpoint < 50_000:
        return "LOW"
    elif trade_volume_midpoint < 250_000:
        return "MODERATE"
    elif trade_volume_midpoint < 1_000_000:
        return "HIGH"
    else:
        return "VERY_HIGH"

def build_summary_label(summary: FinancialShapeSummary) -> str:
    if summary.asset_count == 0 and summary.trade_count == 0:
        return "No disclosed financial activity"
        
    asset_str = "No disclosed assets"
    if summary.asset_count > 0:
        if summary.net_worth_band == "VERY_HIGH":
            asset_str = "Very high disclosed wealth"
        elif summary.net_worth_band == "HIGH":
            asset_str = "High disclosed wealth"
        else:
            density_map = {
                "LOW": "Low asset complexity",
                "MEDIUM": "Medium asset complexity",
                "HIGH": "High asset complexity"
            }
            asset_str = density_map.get(summary.asset_density, "Disclosed assets")

    trade_str = "no trading activity"
    if summary.trade_activity != "NONE":
        trade_str = f"{summary.trade_activity.lower()} trading activity"
        
    return f"{asset_str}, {trade_str}"

def build_financial_shape_summary(db_path: Path, politician_id: int) -> FinancialShapeSummary:
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        
        # Aggregate normalized assets
        cursor.execute("""
            SELECT 
                COUNT(*) as asset_count,
                SUM(value_min) as total_value_min,
                SUM(value_max) as total_value_max,
                SUM(value_midpoint) as total_value_mid
            FROM normalized_assets
            WHERE politician_id = ?
        """, (politician_id,))
        assets_row = cursor.fetchone()
        
        asset_count = assets_row["asset_count"] or 0
        asset_value_min = float(assets_row["total_value_min"]) if assets_row["total_value_min"] is not None else None
        asset_value_max = float(assets_row["total_value_max"]) if assets_row["total_value_max"] is not None else None
        asset_value_midpoint = float(assets_row["total_value_mid"]) if assets_row["total_value_mid"] is not None else None

        # Aggregate trades
        cursor.execute("""
            SELECT 
                COUNT(*) as trade_count,
                SUM(amount_min) as total_amount_min,
                SUM(amount_max) as total_amount_max,
                SUM(amount_mid) as total_amount_mid
            FROM trades
            WHERE politician_id = ?
        """, (politician_id,))
        trades_row = cursor.fetchone()
        
        trade_count = trades_row["trade_count"] or 0
        trade_volume_min = float(trades_row["total_amount_min"]) if trades_row["total_amount_min"] is not None else None
        trade_volume_max = float(trades_row["total_amount_max"]) if trades_row["total_amount_max"] is not None else None
        trade_volume_midpoint = float(trades_row["total_amount_mid"]) if trades_row["total_amount_mid"] is not None else None

        trade_activity = get_trade_activity(trade_count)
        net_worth_band = get_net_worth_band(asset_value_midpoint)
        asset_density = get_asset_density(asset_count)
        trade_volume_band = get_trade_volume_band(trade_volume_midpoint)
        
        summary = FinancialShapeSummary(
            politician_id=politician_id,
            asset_count=asset_count,
            asset_value_min=asset_value_min,
            asset_value_max=asset_value_max,
            asset_value_midpoint=asset_value_midpoint,
            trade_count=trade_count,
            trade_volume_min=trade_volume_min,
            trade_volume_max=trade_volume_max,
            trade_volume_midpoint=trade_volume_midpoint,
            trade_activity=trade_activity,
            net_worth_band=net_worth_band,
            asset_density=asset_density,
            trade_volume_band=trade_volume_band,
            summary_label=""
        )
        summary.summary_label = build_summary_label(summary)
        return summary

def summary_to_dict(summary: FinancialShapeSummary) -> dict:
    return {
        "politician_id": summary.politician_id,
        "asset_count": summary.asset_count,
        "asset_value_min": summary.asset_value_min,
        "asset_value_max": summary.asset_value_max,
        "asset_value_midpoint": summary.asset_value_midpoint,
        "trade_count": summary.trade_count,
        "trade_volume_min": summary.trade_volume_min,
        "trade_volume_max": summary.trade_volume_max,
        "trade_volume_midpoint": summary.trade_volume_midpoint,
        "trade_activity": summary.trade_activity,
        "net_worth_band": summary.net_worth_band,
        "asset_density": summary.asset_density,
        "trade_volume_band": summary.trade_volume_band,
        "summary_label": summary.summary_label
    }
