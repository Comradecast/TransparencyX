import csv
from pathlib import Path


def load_member_aliases(path: str | Path) -> dict[str, str]:
    alias_path = Path(path)
    if not alias_path.exists():
        return {}

    with alias_path.open(newline="", encoding="utf-8") as csv_file:
        rows = list(csv.DictReader(csv_file))

    if not rows:
        return {}

    required_cols = ["parsed_member_id", "canonical_member_id", "source_name", "source_url", "notes"]
    for col in required_cols:
        if col not in rows[0]:
            raise ValueError(f"Missing required alias column: {col}")

    aliases = {}
    for row in rows:
        parsed_id = row.get("parsed_member_id", "").strip()
        canonical_id = row.get("canonical_member_id", "").strip()

        if not parsed_id or not canonical_id:
            raise ValueError("empty parsed_member_id or canonical_member_id not allowed")

        if parsed_id in aliases:
            raise ValueError(f"duplicate parsed_member_id: {parsed_id}")

        aliases[parsed_id] = canonical_id

    return aliases
