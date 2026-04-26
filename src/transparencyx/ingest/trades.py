import hashlib
import re
from dataclasses import dataclass
from typing import Optional

from transparencyx.ranges import parse_range

@dataclass
class TradeRecord:
    politician_name: str
    trade_date: str
    asset_name: str
    transaction_type: str
    amount_range_text: str

def normalize_trade_record(record: TradeRecord) -> dict:
    tx_type = record.transaction_type.strip().upper()
    if tx_type not in ("BUY", "SELL"):
        raise ValueError(f"Invalid transaction type: {tx_type}. Must be BUY or SELL.")
        
    asset_name = re.sub(r'\s+', ' ', record.asset_name.strip())
    
    parsed_range = parse_range(record.amount_range_text)
    
    return {
        "politician_name": record.politician_name,
        "trade_date": record.trade_date,
        "asset_name": asset_name,
        "transaction_type": tx_type,
        "amount_range_text": record.amount_range_text,
        "amount_min": parsed_range.minimum,
        "amount_max": parsed_range.maximum,
        "amount_mid": parsed_range.midpoint,
    }

def get_or_create_politician(conn, full_name: str) -> int:
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM politicians WHERE full_name = ?", (full_name,))
    row = cursor.fetchone()
    if row:
        return row["id"]
    
    import datetime
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    cursor.execute("""
        INSERT INTO politicians (
            first_name, last_name, full_name, chamber, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?)
    """, ("Unknown", "Unknown", full_name, "unknown", now, now))
    return cursor.lastrowid

def insert_trade(conn, normalized_record: dict) -> Optional[int]:
    cursor = conn.cursor()
    
    # Compute deterministic source_hash
    hash_input = (
        f"{normalized_record['politician_name']}|"
        f"{normalized_record['trade_date']}|"
        f"{normalized_record['asset_name']}|"
        f"{normalized_record['transaction_type']}|"
        f"{normalized_record['amount_range_text']}"
    )
    source_hash = hashlib.sha256(hash_input.encode('utf-8')).hexdigest()
    
    # Enforce idempotency
    cursor.execute("SELECT id FROM trades WHERE source_hash = ?", (source_hash,))
    existing = cursor.fetchone()
    if existing:
        return existing["id"]
        
    politician_id = get_or_create_politician(conn, normalized_record["politician_name"])
    
    cursor.execute("""
        INSERT INTO trades (
            politician_id,
            trade_date,
            asset_name,
            transaction_type,
            amount_range_text,
            amount_min,
            amount_max,
            amount_mid,
            source_hash
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        politician_id,
        normalized_record["trade_date"],
        normalized_record["asset_name"],
        normalized_record["transaction_type"],
        normalized_record["amount_range_text"],
        normalized_record["amount_min"],
        normalized_record["amount_max"],
        normalized_record["amount_mid"],
        source_hash
    ))
    return cursor.lastrowid

def ingest_sample_trades(conn) -> int:
    samples = [
        TradeRecord(
            politician_name="Pelosi, Nancy",
            trade_date="2023-01-15",
            asset_name="AAPL",
            transaction_type="BUY",
            amount_range_text="$15,001 - $50,000"
        ),
        TradeRecord(
            politician_name="Pelosi, Nancy",
            trade_date="2023-02-10",
            asset_name="MSFT",
            transaction_type="SELL",
            amount_range_text="Over $100,000"
        ),
        TradeRecord(
            politician_name="Tuberville, Tommy",
            trade_date="2023-03-05",
            asset_name="  Corn  Futures  ",
            transaction_type=" buy ",
            amount_range_text="$1,001 - $15,000"
        )
    ]
    
    inserted = 0
    for sample in samples:
        norm = normalize_trade_record(sample)
        
        cursor = conn.cursor()
        cursor.execute("SELECT count(*) as c FROM trades")
        before = cursor.fetchone()["c"]
        
        insert_trade(conn, norm)
        
        cursor.execute("SELECT count(*) as c FROM trades")
        after = cursor.fetchone()["c"]
        if after > before:
            inserted += 1
            
    return inserted
