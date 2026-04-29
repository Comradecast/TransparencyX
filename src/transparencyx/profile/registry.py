from pathlib import Path

from transparencyx.extract.registry import get_extractor_for_source
from transparencyx.profile.identity import extract_member_identity
from transparencyx.sources.registry import get_registered_sources


def _extract_text_from_pdf(pdf_path: Path) -> str | None:
    source = get_registered_sources().get("house")
    if source is None:
        return None

    extractor = get_extractor_for_source(source, pdf_path.suffix.lstrip("."))
    if extractor is None:
        return None

    result = extractor.extract(pdf_path, source)
    if not result.success:
        return None

    return result.extracted_text


def build_member_record(pdf_path: Path) -> dict:
    extracted_text = _extract_text_from_pdf(pdf_path)
    identity = extract_member_identity(extracted_text or "")

    return {
        "member_name": identity.get("member_name", "Unknown"),
        "politician_id": None,
        "filing_year": None,
        "source": "house",
        "disclosure_path": str(pdf_path),
    }


def build_registry(pdf_paths: list[Path]) -> list[dict]:
    return [
        build_member_record(pdf_path)
        for pdf_path in sorted(pdf_paths, key=lambda path: str(path))
    ]
