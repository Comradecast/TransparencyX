from pathlib import Path

from transparencyx.acquisition.house_identity import (
    HouseDocIdIdentityResolver,
    apply_house_doc_id_identity_resolution,
    extract_house_doc_id_from_pdf_path,
)
from transparencyx.dossier.builder import build_member_dossier_from_profile


def _resolver(index_rows=None, acquisition_entries=None):
    return HouseDocIdIdentityResolver(
        index_rows=[
            {
                "doc_id": "8220486",
                "year": "2023",
                "filing_type": "O",
                "state_dst": "NH02",
            }
        ]
        if index_rows is None
        else index_rows,
        acquisition_entries=[
            {
                "doc_id": "8220486",
                "year": 2023,
                "filing_type": "O",
                "member_slug": "ann-m-kuster",
                "full_name": "Ann M. Kuster",
                "chamber": "House",
                "state": "NH",
                "district": "2",
            }
        ]
        if acquisition_entries is None
        else acquisition_entries,
    )


def test_extracts_doc_id_only_from_house_raw_pdf_path():
    assert extract_house_doc_id_from_pdf_path(
        Path("data/raw/house/2023/8220486.pdf")
    ) == (2023, "8220486")
    assert extract_house_doc_id_from_pdf_path(
        Path("data/raw/senate/2023/8220486.pdf")
    ) is None
    assert extract_house_doc_id_from_pdf_path(
        Path("data/raw/house/2023/8220486-print.pdf")
    ) is None


def test_parser_unknown_resolves_only_through_exact_doc_id():
    profile = {
        "member_name": "Unknown",
        "disclosure_path": "data/raw/house/2023/8220486.pdf",
    }

    resolved = apply_house_doc_id_identity_resolution(profile, _resolver())

    assert resolved["member_id"] == "ann-m-kuster"
    assert resolved["member_name"] == "Ann M. Kuster"
    assert resolved["chamber"] == "House"
    assert resolved["state"] == "NH"
    assert resolved["district"] == "2"
    assert resolved["identity_resolution"]["identity_resolution_source"] == (
        "house_doc_id_manifest"
    )
    assert resolved["identity_resolution"]["identity_resolution_doc_id"] == "8220486"
    assert resolved["identity_resolution"]["parsed_identity_original"] == {
        "member_id": None,
        "member_name": "Unknown",
        "chamber": None,
        "state": None,
        "district": None,
    }
    assert resolved["identity_resolution"]["identity_resolution_status"] == "resolved"


def test_unknown_is_not_globally_mapped_without_exact_doc_id():
    profile = {
        "member_name": "Unknown",
        "disclosure_path": "data/raw/house/2023/99999999.pdf",
    }

    resolved = apply_house_doc_id_identity_resolution(profile, _resolver())

    assert resolved is profile
    dossier = build_member_dossier_from_profile(resolved)
    assert dossier.identity.member_id == "unknown"


def test_missing_doc_id_fails_closed():
    resolver = _resolver(index_rows=[])

    assert resolver.resolve_pdf_path("data/raw/house/2023/8220486.pdf") is None


def test_duplicate_doc_id_fails_closed():
    resolver = _resolver(
        index_rows=[
            {
                "doc_id": "8220486",
                "year": "2023",
                "filing_type": "O",
                "state_dst": "NH02",
            },
            {
                "doc_id": "8220486",
                "year": "2023",
                "filing_type": "O",
                "state_dst": "NH02",
            },
        ]
    )

    assert resolver.resolve_pdf_path("data/raw/house/2023/8220486.pdf") is None


def test_duplicate_acquisition_doc_id_fails_closed():
    entry = {
        "doc_id": "8220486",
        "year": 2023,
        "filing_type": "O",
        "member_slug": "ann-m-kuster",
        "full_name": "Ann M. Kuster",
        "chamber": "House",
        "state": "NH",
        "district": "2",
    }
    resolver = _resolver(acquisition_entries=[entry, dict(entry)])

    assert resolver.resolve_pdf_path("data/raw/house/2023/8220486.pdf") is None


def test_filing_type_x_is_rejected():
    resolver = _resolver(
        index_rows=[
            {
                "doc_id": "30021294",
                "year": "2023",
                "filing_type": "X",
                "state_dst": "NH01",
            }
        ],
        acquisition_entries=[
            {
                "doc_id": "30021294",
                "year": 2023,
                "filing_type": "X",
                "member_slug": "chris-pappas",
                "full_name": "Chris Pappas",
                "chamber": "House",
                "state": "NH",
                "district": "1",
            }
        ],
    )

    assert resolver.resolve_pdf_path("data/raw/house/2023/30021294.pdf") is None


def test_identity_replacement_preserves_summary_metrics_and_trace():
    shape_export = {
        "summary": {
            "asset_count": 5,
            "transaction_count": 2,
            "linked_transaction_count": 1,
            "unlinked_transaction_count": 1,
        },
        "transaction_trace": [
            {"row": 1, "raw": "unchanged"},
        ],
    }
    profile = {
        "member_name": "Unknown",
        "disclosure_path": "data/raw/house/2023/8220486.pdf",
        "shape_export": shape_export,
    }

    resolved = apply_house_doc_id_identity_resolution(profile, _resolver())

    assert resolved["shape_export"] == shape_export
    assert resolved["shape_export"]["transaction_trace"] == [
        {"row": 1, "raw": "unchanged"},
    ]
    dossier = build_member_dossier_from_profile(resolved)
    assert dossier.financials.asset_count == 5
    assert dossier.financials.trade_count == 2
    assert dossier.financials.linked_transaction_count == 1
    assert dossier.financials.unlinked_transaction_count == 1


def test_public_docs_have_no_unknown_house_bucket_after_resolution():
    assert not Path("docs/unknown.json").exists()
    assert not Path("docs/unknown.html").exists()
