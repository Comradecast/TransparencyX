import re
from dataclasses import dataclass
from typing import List, Optional
from pathlib import Path

from transparencyx.parse.sections import Section, detect_sections
from transparencyx.db.database import get_connection
from transparencyx.normalize.assets import clean_asset_name, contains_asset_anchor, parse_value_range


SCHEDULE_B_SECTION_NAMES = {"SCHEDULE B", "S B: T"}
TRANSACTION_ROW_PATTERN = re.compile(
    r"(?P<asset>.+?)\s+"
    r"\[[A-Z]{2}\]\s*"
    r"(?:(?P<owner>SP|JT|DC)\s+)?"
    r"(?P<trade_date>\d{1,2}/\d{1,2}/\d{4})\s+"
    r"(?P<transaction_type>S\s*\(partial\)|[PSE])\s+"
    r"(?P<amount_range>"
    r"(?:\$[\d,]+(?:\.\d+)?\s*-\s*\$[\d,]+(?:\.\d+)?)"
    r"|(?:Over\s+\$[\d,]+(?:\.\d+)?)"
    r"|(?:\$[\d,]+(?:\.\d+)?)"
    r")",
    re.IGNORECASE,
)


@dataclass
class TradeCandidate:
    raw_line: str
    asset_name: str
    owner: Optional[str]
    trade_date: str
    transaction_type: str
    amount_range_text: str


def extract_transaction_candidates(section: Section) -> List[TradeCandidate]:
    if section.name not in SCHEDULE_B_SECTION_NAMES:
        return []

    candidates = []
    lines = section.raw_text.split("\n")
    
    seen = set()
    buffer = []
    in_transaction = False

    def process_group(raw_str: str) -> None:
        for match in TRANSACTION_ROW_PATTERN.finditer(raw_str):
            asset_name = clean_asset_name(match.group("asset"))
            if not asset_name:
                continue

            amount_range = " ".join(match.group("amount_range").split())

            tx_type = " ".join(match.group("transaction_type").split())
            key = (asset_name, match.group("trade_date"), tx_type, amount_range)
            if key not in seen:
                seen.add(key)
                candidates.append(
                    TradeCandidate(
                        raw_line=match.group(0),
                        asset_name=asset_name,
                        owner=match.group("owner"),
                        trade_date=match.group("trade_date"),
                        transaction_type=tx_type,
                        amount_range_text=amount_range,
                    )
                )

    for line in lines:
        raw_line = " ".join(line.split())
        if not raw_line:
            continue

        is_new_tx = contains_asset_anchor(raw_line) and re.search(r"\d{1,2}/\d{1,2}/\d{4}", raw_line)
        is_comment = raw_line.startswith("D:") or raw_line.startswith("C:") or raw_line.startswith("*")
        
        if re.match(r"^(Schedule\s+[C-Z]|S\s+[C-Z]:)", raw_line, re.IGNORECASE):
            break

        if is_new_tx:
            if buffer:
                process_group(" ".join(buffer))
            buffer = [raw_line]
            in_transaction = True
        elif in_transaction:
            if is_comment:
                in_transaction = False
                if buffer:
                    process_group(" ".join(buffer))
                    buffer = []
            else:
                buffer.append(raw_line)

    if buffer:
        process_group(" ".join(buffer))

    return candidates


def insert_normalized_transactions(
    db_path: Path,
    raw_disclosure_id: int,
    politician_id: int,
    candidates: List[TradeCandidate]
) -> int:
    inserted_count = 0

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        
        # Use existing rows for deterministic idempotency within the same disclosure.
        cursor.execute(
            """
            SELECT asset_name, trade_date, transaction_type, amount_range_text
            FROM trades
            WHERE raw_disclosure_id = ?
            """,
            (raw_disclosure_id,)
        )
        existing_trades = set(
            (
                row["asset_name"],
                row["trade_date"],
                row["transaction_type"],
                row["amount_range_text"],
            )
            for row in cursor.fetchall()
        )

        for candidate in candidates:
            if not candidate.asset_name or not candidate.trade_date:
                continue

            key = (
                candidate.asset_name,
                candidate.trade_date,
                candidate.transaction_type,
                candidate.amount_range_text,
            )
            if key in existing_trades:
                continue

            amount_min, amount_max, amount_mid = parse_value_range(candidate.amount_range_text)

            cursor.execute(
                """
                INSERT INTO trades (
                    politician_id,
                    raw_disclosure_id,
                    trade_date,
                    asset_name,
                    transaction_type,
                    amount_range_text,
                    amount_min,
                    amount_max,
                    amount_mid
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    politician_id,
                    raw_disclosure_id,
                    candidate.trade_date,
                    candidate.asset_name,
                    candidate.transaction_type,
                    candidate.amount_range_text,
                    amount_min,
                    amount_max,
                    amount_mid
                )
            )
            existing_trades.add(key)
            inserted_count += 1

    return inserted_count


def process_transactions_for_disclosure(
    db_path: Path,
    raw_disclosure_id: int,
    politician_id: int,
    extracted_text: str
) -> int:
    sections = detect_sections(extracted_text)
    
    inserted = 0
    for section in sections:
        if section.name in SCHEDULE_B_SECTION_NAMES:
            candidates = extract_transaction_candidates(section)
            if candidates:
                inserted += insert_normalized_transactions(
                    db_path=db_path,
                    raw_disclosure_id=raw_disclosure_id,
                    politician_id=politician_id,
                    candidates=candidates
                )
    
    return inserted
