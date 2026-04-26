import pytest
import sqlite3
import datetime
from transparencyx.ingest.trades import TradeRecord, normalize_trade_record, insert_trade, get_or_create_politician, ingest_sample_trades

@pytest.fixture
def db_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    # Apply schema
    from transparencyx.db.schema import get_schema_sql
    conn.executescript(get_schema_sql())
    yield conn
    conn.close()

def test_normalize_trade_record():
    record = TradeRecord(
        politician_name="Smith, John",
        trade_date="2023-01-01",
        asset_name="  AAPL  Corp  ",
        transaction_type=" buy ",
        amount_range_text="$1,001 - $15,000"
    )
    
    norm = normalize_trade_record(record)
    
    # Validation
    assert norm["transaction_type"] == "BUY"
    assert norm["asset_name"] == "AAPL Corp"
    assert norm["amount_min"] == 1001
    assert norm["amount_max"] == 15000
    assert norm["amount_mid"] == 8000
    assert norm["politician_name"] == "Smith, John"
    assert norm["trade_date"] == "2023-01-01"

def test_insert_trade_creates_politician(db_conn):
    record = TradeRecord(
        politician_name="Doe, Jane",
        trade_date="2023-01-01",
        asset_name="MSFT",
        transaction_type="SELL",
        amount_range_text="Over $100,000"
    )
    norm = normalize_trade_record(record)
    
    trade_id = insert_trade(db_conn, norm)
    assert trade_id is not None
    
    cursor = db_conn.cursor()
    cursor.execute("SELECT * FROM politicians WHERE full_name = 'Doe, Jane'")
    politician = cursor.fetchone()
    assert politician is not None
    
    cursor.execute("SELECT * FROM trades WHERE id = ?", (trade_id,))
    trade = cursor.fetchone()
    assert trade is not None
    assert trade["politician_id"] == politician["id"]
    assert trade["transaction_type"] == "SELL"
    assert trade["amount_min"] == 100000.0
    assert trade["amount_max"] is None

def test_insert_trade_idempotent(db_conn):
    record = TradeRecord(
        politician_name="Doe, Jane",
        trade_date="2023-01-01",
        asset_name="MSFT",
        transaction_type="SELL",
        amount_range_text="Over $100,000"
    )
    norm = normalize_trade_record(record)
    
    # First insert
    trade_id_1 = insert_trade(db_conn, norm)
    
    # Second insert
    trade_id_2 = insert_trade(db_conn, norm)
    
    assert trade_id_1 == trade_id_2
    
    # Verify count is 1
    cursor = db_conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM trades")
    assert cursor.fetchone()[0] == 1

def test_ingest_sample_trades(db_conn):
    inserted = ingest_sample_trades(db_conn)
    assert inserted == 3
    
    # Try inserting again, should return 0 due to deduplication
    inserted_again = ingest_sample_trades(db_conn)
    assert inserted_again == 0

def test_invalid_transaction_type_raises_error(db_conn):
    record = TradeRecord(
        politician_name="Doe, Jane",
        trade_date="2023-01-01",
        asset_name="MSFT",
        transaction_type="HOLD",
        amount_range_text="Over $100,000"
    )
    
    with pytest.raises(ValueError, match="Invalid transaction type: HOLD. Must be BUY or SELL."):
        normalize_trade_record(record)

    # Ensure nothing was inserted due to failure before insertion
    cursor = db_conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM trades")
    assert cursor.fetchone()[0] == 0
