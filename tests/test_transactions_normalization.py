from transparencyx.parse.sections import Section
from transparencyx.normalize.transactions import extract_transaction_candidates

def test_extract_transaction_candidates_ignores_non_schedule_b():
    section = Section("ASSETS", 0, 100, "Some text")
    candidates = extract_transaction_candidates(section)
    assert len(candidates) == 0


def test_extract_transaction_candidates_extracts_clean_row():
    text = "Apple Inc. (AAPL) [ST] SP 03/17/2023 P $500,001 - $1,000,000"
    section = Section("SCHEDULE B", 0, 100, text)
    candidates = extract_transaction_candidates(section)

    assert len(candidates) == 1
    assert candidates[0].asset_name == "Apple Inc. (AAPL)"
    assert candidates[0].owner == "SP"
    assert candidates[0].trade_date == "03/17/2023"
    assert candidates[0].transaction_type == "P"
    assert candidates[0].amount_range_text == "$500,001 - $1,000,000"


def test_extract_transaction_candidates_extracts_multi_line_row():
    text = "Apple Inc. (AAPL) [ST] SP 05/8/2023 S\n(partial)\n$500,001 -\n$1,000,000"
    section = Section("S B: T", 0, 100, text)
    candidates = extract_transaction_candidates(section)

    assert len(candidates) == 1
    assert candidates[0].asset_name == "Apple Inc. (AAPL)"
    assert candidates[0].owner == "SP"
    assert candidates[0].trade_date == "05/8/2023"
    assert candidates[0].transaction_type == "S (partial)"
    assert candidates[0].amount_range_text == "$500,001 - $1,000,000"


def test_extract_transaction_candidates_ignores_descriptions():
    text = (
        "Apple Inc. (AAPL) [ST] SP 03/17/2023 P $500,001 - $1,000,000\n"
        "D: Exercised 100 call options purchased 5/13/22.\n"
        "NVIDIA Corporation (NVDA) [OP] SP 11/22/2023 P $1,000,001 - $5,000,000"
    )
    section = Section("SCHEDULE B", 0, 100, text)
    candidates = extract_transaction_candidates(section)

    assert len(candidates) == 2
    assert candidates[0].asset_name == "Apple Inc. (AAPL)"
    assert candidates[1].asset_name == "NVIDIA Corporation (NVDA)"
    assert "Exercised 100 call options" not in candidates[0].amount_range_text


def test_extract_transaction_candidates_no_owner():
    text = "Roblox Corporation Class A (RBLX) [OP] 01/20/2023 S $1.00"
    section = Section("SCHEDULE B", 0, 100, text)
    candidates = extract_transaction_candidates(section)

    assert len(candidates) == 1
    assert candidates[0].asset_name == "Roblox Corporation Class A (RBLX)"
    assert candidates[0].owner is None
    assert candidates[0].trade_date == "01/20/2023"
    assert candidates[0].transaction_type == "S"
    assert candidates[0].amount_range_text == "$1.00"


def test_extract_transaction_candidates_requires_amount():
    text = "Roblox Corporation Class A (RBLX) [OP] 01/20/2023 S"
    section = Section("SCHEDULE B", 0, 100, text)
    candidates = extract_transaction_candidates(section)

    assert candidates == []


def test_extract_transaction_candidates_ignores_generic_transactions_section():
    text = "Apple Inc. (AAPL) [ST] SP 03/17/2023 P $500,001 - $1,000,000"
    section = Section("TRANSACTIONS", 0, 100, text)
    candidates = extract_transaction_candidates(section)

    assert candidates == []


def test_extract_transaction_candidates_splits_adjacent_rows():
    text = (
        "Altria Group, Inc. (MO) [ST] JT 10/11/2023 P $1,001 - $15,000 "
        "Apollo Asset Management, Inc. 6.375% Series A Preferred Stock "
        "(AAM$A) [ST] JT 09/22/2023 S $15,001 - $50,000"
    )
    section = Section("SCHEDULE B", 0, 100, text)
    candidates = extract_transaction_candidates(section)

    assert len(candidates) == 2
    assert candidates[0].asset_name == "Altria Group, Inc. (MO)"
    assert candidates[0].amount_range_text == "$1,001 - $15,000"
    assert candidates[1].asset_name == (
        "Apollo Asset Management, Inc. 6.375% Series A Preferred Stock (AAM$A)"
    )
    assert candidates[1].amount_range_text == "$15,001 - $50,000"
