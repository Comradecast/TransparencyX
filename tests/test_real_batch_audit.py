import sys

import pytest

from transparencyx.audit.real_batch import (
    build_real_batch_audit_rows,
    render_real_batch_audit_table,
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
        "member_id | source_pdf | asset_count | income_count | "
        "transaction_count | asset_range | income_range | metadata_attached"
    )


def test_real_batch_audit_rows_collect_existing_profile_summary_values():
    rows = build_real_batch_audit_rows([_profile()])

    assert rows == [
        {
            "member_id": "jane-public",
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

    from transparencyx.cli import main

    with pytest.raises(SystemExit) as exit_info:
        main()

    captured = capsys.readouterr()

    assert exit_info.value.code == 0
    assert "member_id | source_pdf | asset_count | income_count" in captured.out
    assert (
        "jane-public | data/raw/house/2023/jane-public.pdf | 3 | 2 | 1"
        in captured.out
    )
