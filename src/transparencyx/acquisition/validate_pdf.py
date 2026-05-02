from pathlib import Path


def validate_disclosure_pdf(path: Path, expected_doc_id: str) -> bool:
    expected_name = f"{expected_doc_id}.pdf"
    if path.name != expected_name:
        return False
    if not path.exists() or not path.is_file():
        return False
    if path.stat().st_size <= 0:
        return False
    try:
        data = path.read_bytes()
    except OSError:
        return False
    if not data.startswith(b"%PDF"):
        return False
    return b"%%EOF" in data
