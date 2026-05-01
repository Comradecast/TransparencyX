from pathlib import Path

from transparencyx.profile.batch import (
    _build_shape_export_from_text,
    _extract_text_from_pdf,
    build_profile_for_pdf,
    build_profiles_for_directory,
)
from transparencyx.audit.real_batch import build_real_batch_audit_rows


PELOSI_PDF = Path("data/raw/house/2023/10059734.pdf")
FOXX_PDF = Path("data/raw/house/2023/10059335.pdf")
TRADE_DETAIL_ROW_KEYS = {
    "id",
    "asset_name",
    "trade_date",
    "transaction_type",
    "amount_range_text",
    "amount_min",
    "amount_max",
    "transaction_type_label",
    "linked_asset_id",
    "linked_asset_name",
}
ASSET_SUMMARY_ROW_KEYS = {
    "asset_id",
    "asset_name",
    "linked_transaction_count",
}


def _assert_asset_summaries_contract(asset_summaries):
    for row in asset_summaries:
        assert set(row) == ASSET_SUMMARY_ROW_KEYS
        assert isinstance(row["linked_transaction_count"], int)
        assert not isinstance(row["linked_transaction_count"], bool)
        assert row["linked_transaction_count"] >= 0


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
    linked_count_total = sum(
        row["linked_transaction_count"]
        for row in summary["asset_summaries"]
    )

    assert summary["asset_count"] == 56
    assert summary["transaction_count"] == 7
    assert len(summary["asset_summaries"]) == 56
    assert linked_count_total <= 7
    assert linked_count_total == 1
    _assert_asset_summaries_contract(summary["asset_summaries"])


def test_pelosi_shape_export_from_text_has_expected_transaction_count():
    extracted_text = _extract_text_from_pdf(PELOSI_PDF)
    export = _build_shape_export_from_text(PELOSI_PDF, extracted_text or "")

    assert export["summary"]["transaction_count"] == 7
    assert len(export["trace"]["trades"]["count_rows"]) == 7
    assert len(export["trace"]["trades"]["detail_rows"]) == 7
    assert all(
        set(row) == TRADE_DETAIL_ROW_KEYS
        for row in export["trace"]["trades"]["detail_rows"]
    )
    assert export["trace"]["trades"]["detail_rows"][0] == {
        "id": export["trace"]["trades"]["count_rows"][0],
        "asset_name": "Apple Inc. (AAPL)",
        "trade_date": "03/17/2023",
        "transaction_type": "P",
        "transaction_type_label": "Purchase",
        "amount_range_text": "$500,001 - $1,000,000",
        "amount_min": 500001.0,
        "amount_max": 1000000.0,
        "linked_asset_id": None,
        "linked_asset_name": None,
    }
    assert any(
        row["linked_asset_id"] is not None
        for row in export["trace"]["trades"]["detail_rows"]
    )


def test_foxx_shape_export_from_text_has_expected_trade_trace_rows():
    extracted_text = _extract_text_from_pdf(FOXX_PDF)
    export = _build_shape_export_from_text(FOXX_PDF, extracted_text or "")

    assert export["summary"]["transaction_count"] == 74
    _assert_asset_summaries_contract(export["summary"]["asset_summaries"])
    assert sum(
        row["linked_transaction_count"]
        for row in export["summary"]["asset_summaries"]
    ) == 48
    assert any(
        row["linked_transaction_count"] > 1
        for row in export["summary"]["asset_summaries"]
    )
    assert len(export["trace"]["trades"]["count_rows"]) == 74
    assert len(export["trace"]["trades"]["detail_rows"]) == 74
    assert all(
        set(row) == TRADE_DETAIL_ROW_KEYS
        for row in export["trace"]["trades"]["detail_rows"]
    )
    assert export["trace"]["trades"]["detail_rows"][0] == {
        "id": export["trace"]["trades"]["count_rows"][0],
        "asset_name": "Altria Group, Inc. (MO)",
        "trade_date": "01/17/2023",
        "transaction_type": "P",
        "transaction_type_label": "Purchase",
        "amount_range_text": "$1,001 - $15,000",
        "amount_min": 1001.0,
        "amount_max": 15000.0,
        "linked_asset_id": 1,
        "linked_asset_name": "Altria Group, Inc. (MO) [ST]",
    }
    assert any(
        row["linked_asset_id"] is not None
        for row in export["trace"]["trades"]["detail_rows"]
    )


def test_real_batch_audit_uses_shape_summary_transaction_count():
    profile = build_profile_for_pdf(PELOSI_PDF)
    rows = build_real_batch_audit_rows([profile], metadata_by_id={}, aliases={})

    assert rows[0]["transaction_count"] == str(
        profile["shape_export"]["summary"]["transaction_count"]
    )
