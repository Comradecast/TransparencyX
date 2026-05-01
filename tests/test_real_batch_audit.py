import sys

import pytest

from transparencyx.audit.real_batch import (
    build_real_batch_audit_rows,
    build_unattached_identity_rows,
    render_real_batch_audit_report,
    render_real_batch_audit_table,
    render_unattached_identity_table,
)
from transparencyx.dossier.metadata import MemberMetadata


def _profile(member_name="Jane Public"):
    return {
        "member_name": member_name,
        "disclosure_path": "data/raw/house/2023/jane-public.pdf",
        "shape_export": {
            "summary": {
                "asset_count": 3,
                "asset_value_min": 1001.0,
                "asset_value_max": 15000.0,
                "income_count": 2,
                "income_min": 201.0,
                "income_max": 1000.0,
                "trade_count": 1,
            }
        },
    }


def test_real_batch_audit_table_includes_expected_fields():
    table = render_real_batch_audit_table([])

    assert table == (
        "member_id | canonical_member_id | alias_applied | source_pdf | asset_count | income_count | "
        "transaction_count | asset_range | income_range | metadata_attached"
    )


def test_real_batch_audit_rows_collect_existing_profile_summary_values():
    rows = build_real_batch_audit_rows([_profile()])

    assert rows == [
        {
            "member_id": "jane-public",
            "canonical_member_id": "jane-public",
            "alias_applied": "No",
            "display_name": "Jane Public",
            "source_pdf": "data/raw/house/2023/jane-public.pdf",
            "asset_count": "3",
            "income_count": "2",
            "transaction_count": "1",
            "asset_range": "$1,001 - $15,000",
            "income_range": "$201 - $1,000",
            "metadata_attached": "No",
        }
    ]


def test_real_batch_audit_rows_report_metadata_attached():
    metadata = MemberMetadata(
        member_id="jane-public",
        full_name="Jane Public",
        chamber="House",
        state="NC",
        district="1",
        party="Independent",
        current_status="current",
    )

    rows = build_real_batch_audit_rows(
        [_profile()],
        metadata_by_id={"jane-public": metadata},
    )

    assert rows[0]["metadata_attached"] == "Yes"


def test_real_batch_identity_audit_identifies_metadata_unattached_profiles():
    rows = build_real_batch_audit_rows(
        [_profile("Jane Public"), _profile("Mapped Member")],
        metadata_by_id={
            "mapped-member": MemberMetadata(
                member_id="mapped-member",
                full_name="Mapped Member",
            )
        },
    )

    identity_rows = build_unattached_identity_rows(rows)

    assert identity_rows == [
        {
            "parsed_member_id": "jane-public",
            "canonical_member_id": "jane-public",
            "alias_applied": "No",
            "parsed_display_name": "Jane Public",
            "source_pdf": "data/raw/house/2023/jane-public.pdf",
            "metadata_attached": "No",
        }
    ]


def test_real_batch_identity_audit_rendering_is_deterministic():
    rendered = render_unattached_identity_table(
        [
            {
                "parsed_member_id": "alpha",
                "canonical_member_id": "alpha",
                "alias_applied": "No",
                "parsed_display_name": "Alpha Member",
                "source_pdf": "a.pdf",
                "metadata_attached": "No",
            },
            {
                "parsed_member_id": "beta",
                "canonical_member_id": "beta",
                "alias_applied": "No",
                "parsed_display_name": "Beta Member",
                "source_pdf": "b.pdf",
                "metadata_attached": "No",
            },
        ]
    )

    assert rendered.splitlines() == [
        "Metadata Unattached Parsed Profiles",
        "parsed_member_id | canonical_member_id | alias_applied | parsed_display_name | source_pdf | metadata_attached",
        "alpha | alpha | No | Alpha Member | a.pdf | No",
        "beta | beta | No | Beta Member | b.pdf | No",
    ]


def test_real_batch_identity_audit_no_unattached_rows_renders_none():
    rendered = render_unattached_identity_table([])

    assert rendered.splitlines() == [
        "Metadata Unattached Parsed Profiles",
        "parsed_member_id | canonical_member_id | alias_applied | parsed_display_name | source_pdf | metadata_attached",
        "None",
    ]


def test_real_batch_audit_report_has_no_suggestion_or_matching_language():
    report = render_real_batch_audit_report(
        build_real_batch_audit_rows([_profile("Jane Public")])
    ).lower()
    restricted_terms = [
        "suggest",
        "suggestion",
        "fuzzy",
        "match candidate",
        "likely",
        "auto-correct",
        "infer",
    ]

    for term in restricted_terms:
        assert term not in report


def test_real_batch_audit_cli_runs_without_error(monkeypatch, capsys):
    monkeypatch.setattr(
        sys,
        "argv",
        ["transparencyx", "--audit-real-batch", "data/raw"],
    )
    monkeypatch.setattr(
        "transparencyx.audit.real_batch.build_profiles_for_directory",
        lambda directory: [_profile("Jane Public")],
    )
    monkeypatch.setattr(
        "transparencyx.audit.real_batch.load_default_member_metadata",
        lambda: {},
    )
    monkeypatch.setattr(
        "transparencyx.audit.real_batch.load_member_aliases",
        lambda path: {},
    )

    from transparencyx.cli import main

    with pytest.raises(SystemExit) as exit_info:
        main()

    captured = capsys.readouterr()

    assert exit_info.value.code == 0
    assert "member_id | canonical_member_id | alias_applied | source_pdf | asset_count | income_count" in captured.out
    assert (
        "jane-public | jane-public | No | data/raw/house/2023/jane-public.pdf | 3 | 2 | 1"
        in captured.out
    )
    assert "Metadata Unattached Parsed Profiles" in captured.out
    assert (
        "jane-public | jane-public | No | Jane Public | data/raw/house/2023/jane-public.pdf | No"
        in captured.out
    )
