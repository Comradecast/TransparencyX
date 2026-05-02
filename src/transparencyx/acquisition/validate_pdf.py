from pathlib import Path

from transparencyx.acquisition.senate import (
    is_senate_raw_pdf_path,
    validate_senate_pdf_source,
)


def _validate_pdf_bytes(path: Path) -> bool:
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


def validate_disclosure_pdf(path: Path, expected_doc_id: str) -> bool:
    expected_name = f"{expected_doc_id}.pdf"
    if path.name != expected_name:
        return False
    if not _validate_pdf_bytes(path):
        return False
    if is_senate_raw_pdf_path(path):
        return validate_senate_pdf_source(path, expected_doc_id)
    return True
