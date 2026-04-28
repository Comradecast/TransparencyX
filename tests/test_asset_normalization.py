import pytest
from transparencyx.parse.sections import Section
from transparencyx.normalize.assets import extract_asset_candidates, insert_normalized_assets, process_assets_for_disclosure, clean_asset_name, is_valid_asset_name, contains_asset_anchor, parse_value_range
from transparencyx.db.database import get_connection, initialize_database


def test_clean_asset_name():
    # Trailing punctuation
    assert clean_asset_name("Apple Inc -") == "Apple Inc"
    assert clean_asset_name("Apple Inc:") == "Apple Inc"
    assert clean_asset_name("Apple Inc -:") == "Apple Inc"
    
    # Whitespace collapse
    assert clean_asset_name("  Apple    Inc  ") == "Apple Inc"
    
    # Combined
    assert clean_asset_name("  Google  Corp  - :  ") == "Google Corp"
    
    # Income suffixes
    assert clean_asset_name("Matthews International Mutual Fund [MF] SP Dividends") == "Matthews International Mutual Fund [MF] SP"
    assert clean_asset_name("City National Bank - Checking Account [BA] SP Interest") == "City National Bank - Checking Account [BA] SP"
    assert clean_asset_name("Borel Real Estate Company [OL] SP Partnership Loss") == "Borel Real Estate Company [OL] SP"
    assert clean_asset_name("Roblox Corporation Class A (RBLX) [OP] SP None Capital Loss") == "Roblox Corporation Class A (RBLX) [OP] SP"
    assert clean_asset_name("Roblox Corporation Class A (RBLX) [OP] SP Capital Loss") == "Roblox Corporation Class A (RBLX) [OP] SP"
    assert clean_asset_name("Borel Real Estate Company [OL] SP Partnership Loss,") == "Borel Real Estate Company [OL] SP"

def test_is_valid_asset_name_rejects_explicit_income_labels():
    assert not is_valid_asset_name("Dividends")
    assert not is_valid_asset_name("Interest")
    assert not is_valid_asset_name("Rent")
    assert not is_valid_asset_name("Partnership Loss")
    assert not is_valid_asset_name("Capital Loss")

def test_is_valid_asset_name_rejects_detail_rows():
    assert not is_valid_asset_name("D: Purchased 50 call options")
    assert not is_valid_asset_name("C: 100 call options expired")

def test_is_valid_asset_name_rejects_transaction_rows():
    assert not is_valid_asset_name("Apple Inc. (AAPL) [ST] SP 03/17/2023 P")
    assert not is_valid_asset_name("REOF XXV, LLC [AB] SP 03/9/2023 P")
    assert not is_valid_asset_name("Roblox Corporation Class A (RBLX) [OP] SP 01/20/2023 S")

def test_is_valid_asset_name_rejects_short_names():
    assert not is_valid_asset_name("ABCD")

def test_is_valid_asset_name_requires_asset_marker():
    assert not is_valid_asset_name("Apple Inc Stock")
    assert is_valid_asset_name("Apple Inc. (AAPL)")
    assert is_valid_asset_name("Apple Inc. [ST]")
    assert is_valid_asset_name("Apple Inc. - Class A")

def test_contains_asset_anchor():
    assert contains_asset_anchor("Apple Inc. (AAPL) [ST] SP")
    assert contains_asset_anchor("Bank of America - Checking Account [BA] SP")
    assert not contains_asset_anchor("Apple Inc. (AAPL) SP")
    assert not contains_asset_anchor("Lowercase [st] SP")

def test_parse_value_range_full_range():
    assert parse_value_range("$1,001 - $15,000") == (1001, 15000, 8000.5)

def test_parse_value_range_open_ended_range():
    assert parse_value_range("$5,000,001 -") == (5000001, None, None)

def test_parse_value_range_over_range():
    assert parse_value_range("Over $50,000,000") == (50000000, None, None)

def test_parse_value_range_ignores_none_and_trailing_text():
    assert parse_value_range("$15,001 - $50,000None D: San Francisco, CA") == (15001, 50000, 32500.5)

def test_parse_value_range_invalid_value():
    assert parse_value_range("$GARBAGE") == (None, None, None)

def test_parse_value_range_ignores_non_range_text():
    assert parse_value_range("$100 to $200") == (None, None, None)

def test_extract_asset_candidates_success():
    raw_text = """
    Apple Inc. (AAPL) [ST]   $1,001 - $15,000
    Google Corp [ST]       Over $50,000,000
    Treasury Bonds    None
    Checking Account  N/A
    Duplicate Asset [ST] - Class A   $1 - $500
    Duplicate Asset [ST] - Class A   $1 - $500
    """
    section = Section(name="ASSETS", start_index=0, end_index=100, raw_text=raw_text)
    
    candidates = extract_asset_candidates(section)
    
    # We should only get lines with $ or Over $, and None/N/A should be skipped. 
    # The duplicate should be removed.
    assert len(candidates) == 3
    
    assert candidates[0].cleaned_name == "Apple Inc. (AAPL) [ST]"
    assert candidates[0].value_range_text == "$1,001 - $15,000"
    
    assert candidates[1].cleaned_name == "Google Corp [ST]"
    assert candidates[1].value_range_text == "Over $50,000,000 Treasury Bonds None Checking Account N/A"
    
    assert candidates[2].cleaned_name == "Duplicate Asset [ST] - Class A"
    assert candidates[2].value_range_text == "$1 - $500"

def test_extract_asset_candidates_groups_until_next_anchor():
    raw_text = """
    Apple Inc. (AAPL) [ST] SP
    $1,001 - $15,000
    This continuation stays with Apple
    Bank of America - Checking Account [BA] SP
    Over $50,000,000
    """
    section = Section(name="ASSETS", start_index=0, end_index=100, raw_text=raw_text)

    candidates = extract_asset_candidates(section)

    assert len(candidates) == 2
    assert candidates[0].raw_line == "Apple Inc. (AAPL) [ST] SP $1,001 - $15,000 This continuation stays with Apple"
    assert candidates[0].cleaned_name == "Apple Inc. (AAPL) [ST] SP"
    assert candidates[0].value_range_text == "$1,001 - $15,000 This continuation stays with Apple"
    assert candidates[1].raw_line == "Bank of America - Checking Account [BA] SP Over $50,000,000"
    assert candidates[1].cleaned_name == "Bank of America - Checking Account [BA] SP"
    assert candidates[1].value_range_text == "Over $50,000,000"

def test_extract_asset_candidates_reconstructs_multiline_rows():
    raw_text = """
    Apple Inc. (AAPL) [ST] SP
    $1,001 - $15,000
    Bank of America - Checking Account [BA] SP
    Over $50,000,000
    """
    section = Section(name="ASSETS", start_index=0, end_index=100, raw_text=raw_text)

    candidates = extract_asset_candidates(section)

    assert len(candidates) == 2
    assert candidates[0].raw_line == "Apple Inc. (AAPL) [ST] SP $1,001 - $15,000"
    assert candidates[0].cleaned_name == "Apple Inc. (AAPL) [ST] SP"
    assert candidates[0].value_range_text == "$1,001 - $15,000"
    assert candidates[1].raw_line == "Bank of America - Checking Account [BA] SP Over $50,000,000"
    assert candidates[1].cleaned_name == "Bank of America - Checking Account [BA] SP"
    assert candidates[1].value_range_text == "Over $50,000,000"

def test_extract_asset_candidates_ignores_leftover_buffer_without_value_signal():
    raw_text = """
    Apple Inc. (AAPL) [ST] SP
    """
    section = Section(name="ASSETS", start_index=0, end_index=100, raw_text=raw_text)

    candidates = extract_asset_candidates(section)

    assert candidates == []

def test_extract_asset_candidates_filters_invalid_asset_names():
    raw_text = """
    D: [ST] Purchased call options with a strike price of $120
    C: [ST] Option expired with a total loss of $100
    Apple Inc. (AAPL) [ST] $1,001 - $15,000
    """
    section = Section(name="ASSETS", start_index=0, end_index=100, raw_text=raw_text)

    candidates = extract_asset_candidates(section)

    assert len(candidates) == 1
    assert candidates[0].cleaned_name == "Apple Inc. (AAPL) [ST]"

def test_extract_asset_candidates_strips_income_suffix_before_storage():
    raw_text = """
    Matthews International Mutual Fund [MF] SP Dividends $201 - $1,000
    City National Bank - Checking Account [BA] SP Interest $1 - $200
    Borel Real Estate Company [OL] SP Partnership Loss $50,001 - $100,000
    Roblox Corporation Class A (RBLX) [OP] SP None Capital Loss $100,001 -
    """
    section = Section(name="ASSETS", start_index=0, end_index=100, raw_text=raw_text)

    candidates = extract_asset_candidates(section)

    assert [candidate.cleaned_name for candidate in candidates] == [
        "Matthews International Mutual Fund [MF] SP",
        "City National Bank - Checking Account [BA] SP",
        "Borel Real Estate Company [OL] SP",
        "Roblox Corporation Class A (RBLX) [OP] SP",
    ]

def test_extract_asset_candidates_wrong_section():
    raw_text = "Apple Inc. (AAPL)   $1,001 - $15,000"
    section = Section(name="INCOME", start_index=0, end_index=100, raw_text=raw_text)
    
    candidates = extract_asset_candidates(section)
    assert len(candidates) == 0

@pytest.fixture
def test_db(tmp_path):
    db_path = tmp_path / "test.sqlite"
    initialize_database(db_path)
    
    # We need a dummy politician and raw_disclosure to satisfy foreign keys
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        now = "2023-01-01T00:00:00Z"
        
        cursor.execute("""
            INSERT INTO politicians (first_name, last_name, full_name, chamber, created_at, updated_at) 
            VALUES ('John', 'Doe', 'John Doe', 'house', ?, ?)
        """, (now, now))
        pol_id = cursor.lastrowid
        
        cursor.execute("""
            INSERT INTO raw_disclosures (politician_id, source_chamber, source_name, filing_year, retrieved_at, raw_metadata_json, created_at) 
            VALUES (?, 'house', 'test', 2023, ?, '{}', ?)
        """, (pol_id, now, now))
        raw_id = cursor.lastrowid
        
    return db_path, pol_id, raw_id

def test_insert_normalized_assets(test_db):
    db_path, pol_id, raw_id = test_db
    
    raw_text = """
    Apple Inc. (AAPL) [ST]   $1,001 - $15,000
    Missing bounds [ST] - Asset    $100 to $200
    Garbage line [ST]      $GARBAGE
    """
    section = Section(name="ASSETS", start_index=0, end_index=100, raw_text=raw_text)
    candidates = extract_asset_candidates(section)
    
    inserted = insert_normalized_assets(db_path, raw_id, pol_id, candidates)
    
    assert inserted == 3
    
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM normalized_assets ORDER BY id ASC")
        rows = cursor.fetchall()
        
        assert len(rows) == 3
        
        assert rows[0]["asset_name"] == "Apple Inc. (AAPL) [ST]"
        assert rows[0]["original_value_range"] == "$1,001 - $15,000"
        assert rows[0]["value_min"] == 1001
        assert rows[0]["value_max"] == 15000
        assert rows[0]["value_midpoint"] == 8000.5
        assert rows[0]["confidence"] == "medium"
        assert rows[0]["asset_category"] == "unknown"
        
        assert rows[1]["asset_name"] == "Missing bounds [ST] - Asset"
        assert rows[1]["value_min"] is None
        assert rows[1]["confidence"] == "low"
        
        assert rows[2]["asset_name"] == "Garbage line [ST]"
        assert rows[2]["value_min"] is None
        assert rows[2]["confidence"] == "low"
        

def test_insert_prevents_db_duplicates(test_db):
    db_path, pol_id, raw_id = test_db
    
    raw_text = """
    Apple Inc. (AAPL) [ST]   $1,001 - $15,000
    """
    section = Section(name="ASSETS", start_index=0, end_index=100, raw_text=raw_text)
    
    # First insert
    candidates1 = extract_asset_candidates(section)
    inserted1 = insert_normalized_assets(db_path, raw_id, pol_id, candidates1)
    assert inserted1 == 1
    
    # Second insert of same candidate should be skipped
    candidates2 = extract_asset_candidates(section)
    inserted2 = insert_normalized_assets(db_path, raw_id, pol_id, candidates2)
    assert inserted2 == 0

def test_process_assets_pipeline(test_db):
    db_path, pol_id, raw_id = test_db
    
    full_text = """
    Header info
    
    ASSETS
    Asset 1 [ST]  $1,001 - $15,000
    Asset 2 [ST] - Class A  Over $50,000,000
    Asset 3  None
    
    INCOME
    Income 1 [ST]  $1,001 - $15,000
    """
    
    inserted = process_assets_for_disclosure(db_path, raw_id, pol_id, full_text)
    assert inserted == 2
    
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT asset_name FROM normalized_assets")
        names = [row["asset_name"] for row in cursor.fetchall()]
        
        assert "Asset 1 [ST]" in names
        assert "Asset 2 [ST] - Class A" in names
        assert "Asset 3" not in names
        assert "Income 1 [ST]" not in names
