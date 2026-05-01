from pathlib import Path

from transparencyx.profile.batch import (
    _build_shape_export_from_text,
    _extract_text_from_pdf,
    build_profile_for_pdf,
    build_profiles_for_directory,
)
from transparencyx.audit.real_batch import build_real_batch_audit_rows


PELOSI_PDF = Path("data/raw/house/2023/10059734.pdf")


def test_build_profiles_for_directory_finds_pdfs(tmp_path, monkeypatch):
    (tmp_path / "a.pdf").write_bytes(b"")
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "b.pdf").write_bytes(b"")
    (tmp_path / "notes.txt").write_text("ignore")

    monkeypatch.setattr(
        "transparencyx.profile.batch.build_profile_for_pdf",
        lambda pdf_path: {"disclosure_path": str(pdf_path)},
    )

    profiles = build_profiles_for_directory(tmp_path)

    assert len(profiles) == 2
    assert all(profile["disclosure_path"].endswith(".pdf") for profile in profiles)


def test_build_profiles_for_directory_deterministic_ordering(tmp_path, monkeypatch):
    (tmp_path / "z.pdf").write_bytes(b"")
    (tmp_path / "a.pdf").write_bytes(b"")
    (tmp_path / "m.pdf").write_bytes(b"")

    monkeypatch.setattr(
        "transparencyx.profile.batch.build_profile_for_pdf",
        lambda pdf_path: {"disclosure_path": pdf_path.name},
    )

    profiles = build_profiles_for_directory(tmp_path)

    assert [profile["disclosure_path"] for profile in profiles] == [
        "a.pdf",
        "m.pdf",
        "z.pdf",
    ]


def test_build_profile_for_pdf_contains_required_fields(monkeypatch):
    monkeypatch.setattr(
        "transparencyx.profile.batch._extract_text_from_pdf",
        lambda pdf_path: "Name: Hon. Nancy Pelosi\n",
    )
    monkeypatch.setattr(
        "transparencyx.profile.batch._build_shape_export_from_text",
        lambda pdf_path, extracted_text: {"politician_id": 1, "summary": {}, "trace": {}},
    )

    profile = build_profile_for_pdf(Path("sample.pdf"))

    assert profile == {
        "member_name": "Nancy Pelosi",
        "disclosure_path": "sample.pdf",
        "shape_export": {"politician_id": 1, "summary": {}, "trace": {}},
    }


def test_build_profiles_for_directory_empty_directory_returns_empty_list(tmp_path):
    assert build_profiles_for_directory(tmp_path) == []


def test_pelosi_schedule_b_transactions_flow_to_shape_summary():
    profile = build_profile_for_pdf(PELOSI_PDF)
    summary = profile["shape_export"]["summary"]

    assert summary["asset_count"] == 56
    assert summary["transaction_count"] == 7


def test_pelosi_shape_export_from_text_has_expected_transaction_count():
    extracted_text = _extract_text_from_pdf(PELOSI_PDF)
    export = _build_shape_export_from_text(PELOSI_PDF, extracted_text or "")

    assert export["summary"]["transaction_count"] == 7
    assert len(export["trace"]["trades"]["count_rows"]) == 7


def test_real_batch_audit_uses_shape_summary_transaction_count():
    profile = build_profile_for_pdf(PELOSI_PDF)
    rows = build_real_batch_audit_rows([profile], metadata_by_id={}, aliases={})

    assert rows[0]["transaction_count"] == str(
        profile["shape_export"]["summary"]["transaction_count"]
    )
