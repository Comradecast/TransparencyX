import datetime
import hashlib
from pathlib import Path

from transparencyx.db.database import get_connection, initialize_database
from transparencyx.extract.registry import get_extractor_for_source
from transparencyx.normalize.assets import process_assets_for_disclosure
from transparencyx.profile.identity import extract_member_identity
from transparencyx.shape.export import build_financial_shape_export
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


def _db_path_for_pdf(pdf_path: Path) -> Path:
    digest = hashlib.sha1(str(pdf_path).encode("utf-8")).hexdigest()
    return Path("data/profile_batch") / f"{digest}.sqlite"


def _build_shape_export_from_text(pdf_path: Path, extracted_text: str) -> dict:
    db_path = _db_path_for_pdf(pdf_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    politician_id = 1
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    initialize_database(db_path)

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO politicians
                (id, first_name, last_name, full_name, chamber, created_at, updated_at)
            VALUES (?, 'Batch', 'Disclosure', 'Disclosure, Batch', 'house', ?, ?)
        """, (politician_id, now, now))
        cursor.execute("""
            INSERT INTO raw_disclosures
                (id, politician_id, source_chamber, source_name, filing_year,
                 retrieved_at, raw_metadata_json, local_path, created_at)
            VALUES (1, ?, 'house', 'batch-profile', 2023, ?, '{}', ?, ?)
        """, (politician_id, now, str(pdf_path), now))
        conn.commit()

    process_assets_for_disclosure(
        db_path=db_path,
        raw_disclosure_id=1,
        politician_id=politician_id,
        extracted_text=extracted_text,
    )

    return build_financial_shape_export(db_path, politician_id)


def build_profile_for_pdf(pdf_path: Path) -> dict:
    extracted_text = _extract_text_from_pdf(pdf_path) or ""
    identity = extract_member_identity(extracted_text)

    return {
        "member_name": identity.get("member_name", "Unknown"),
        "disclosure_path": str(pdf_path),
        "shape_export": _build_shape_export_from_text(pdf_path, extracted_text),
    }


def build_profiles_for_directory(directory: Path) -> list[dict]:
    pdf_paths = sorted(directory.rglob("*.pdf"), key=lambda path: str(path))
    return [build_profile_for_pdf(pdf_path) for pdf_path in pdf_paths]
