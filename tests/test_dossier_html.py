import sys

import pytest

from transparencyx.dossier.html import (
    dossier_html_filename,
    render_dossier_html_index,
    render_member_dossier_html,
    write_dossier_html_index,
    write_member_dossier_html,
    write_member_dossiers_html,
)
from transparencyx.dossier.schema import (
    DossierExposure,
    DossierFinancials,
    EvidenceSource,
    MemberDossier,
    MemberIdentity,
    MemberOffice,
    create_empty_member_dossier,
)


def test_complete_html_document():
    dossier = create_empty_member_dossier("nancy-pelosi", "Nancy Pelosi")

    html = render_member_dossier_html(dossier)

    assert html.startswith("<!doctype html>\n<html")
    assert "<head>" in html
    assert "<body>" in html
    assert "</html>\n" in html
    assert html.endswith("\n")
    assert "<title>TransparencyX Dossier - Nancy Pelosi</title>" in html


def test_escaped_member_and_data_values():
    dossier = MemberDossier(
        identity=MemberIdentity(
            member_id="member-1",
            full_name="<Nancy & Pelosi>",
            chamber="House",
        ),
        office=MemberOffice(leadership_roles=["Lead <Role>"]),
        financials=DossierFinancials(business_interests=["A & B"]),
        exposure=DossierExposure(),
        evidence_sources=[
            EvidenceSource(
                source_type="metadata",
                source_name="<Roster>",
                source_url="https://example.test?a=1&b=2",
            )
        ],
    )

    html = render_member_dossier_html(dossier)

    assert "&lt;Nancy &amp; Pelosi&gt;" in html
    assert "Lead &lt;Role&gt;" in html
    assert "&lt;Roster&gt;" in html
    assert "https://example.test?a=1&amp;b=2" in html
    assert "<Nancy & Pelosi>" not in html


def test_missing_values_render_unknown():
    dossier = create_empty_member_dossier("nancy-pelosi", "Nancy Pelosi")

    html = render_member_dossier_html(dossier)

    assert "<dt>chamber</dt><dd>Unknown</dd>" in html
    assert "<dt>official salary</dt><dd>Unknown</dd>" in html
    assert "<dt>asset count</dt><dd>Unknown</dd>" in html


def test_empty_lists_render_none():
    dossier = create_empty_member_dossier("nancy-pelosi", "Nancy Pelosi")

    html = render_member_dossier_html(dossier)

    assert "<dt>leadership roles</dt><dd>None</dd>" in html
    assert "<dt>committee assignments</dt><dd>None</dd>" in html
    assert "<dt>agencies found</dt><dd>None</dd>" in html
    assert "<h2>Evidence Sources</h2>\n<p>None</p>" in html


def test_money_formatting():
    dossier = MemberDossier(
        identity=MemberIdentity("nancy-pelosi", "Nancy Pelosi"),
        office=MemberOffice(official_salary=174000.0),
        financials=DossierFinancials(
            asset_value_min=1001.0,
            asset_value_max=15000.5,
            income_min=0.0,
            income_max=2500.25,
        ),
        exposure=DossierExposure(
            federal_award_exposure=[
                {"total_award_amount": 1234.5},
            ]
        ),
    )

    html = render_member_dossier_html(dossier)

    assert "<dt>official salary</dt><dd>$174,000</dd>" in html
    assert "<dt>asset value range</dt><dd>$1,001 - $15,000.50</dd>" in html
    assert "<dt>income range</dt><dd>$0 - $2,500.25</dd>" in html
    assert "<dt>total award amount</dt><dd>$1,234.50</dd>" in html


def test_boolean_yes_no():
    dossier = MemberDossier(
        identity=MemberIdentity("nancy-pelosi", "Nancy Pelosi"),
        office=MemberOffice(),
        financials=DossierFinancials(),
        exposure=DossierExposure(exposure_counted=True),
    )

    html = render_member_dossier_html(dossier)

    assert "<dt>exposure counted</dt><dd>Yes</dd>" in html

    dossier.exposure.exposure_counted = False
    assert "<dt>exposure counted</dt><dd>No</dd>" in render_member_dossier_html(dossier)


def test_candidate_table_renders_review_only_and_not_counted():
    dossier = MemberDossier(
        identity=MemberIdentity("nancy-pelosi", "Nancy Pelosi"),
        office=MemberOffice(),
        financials=DossierFinancials(),
        exposure=DossierExposure(
            recipient_candidates=[
                {
                    "original_query": "Example Holdings",
                    "candidate_query": "Example",
                    "recipient_name": "Example Recipient",
                    "award_count": 2,
                    "total_award_amount": 100.0,
                    "match_status": "candidate_review_only",
                    "substring_match": True,
                    "token_overlap": 1,
                    "exposure_counted": False,
                }
            ]
        ),
    )

    html = render_member_dossier_html(dossier)

    assert "<th>original_query</th>" in html
    assert "<td>review-only</td>" in html
    assert "<td>No</td>" in html
    assert "<p>candidate rows count: 1</p>" in html


def test_evidence_source_table():
    dossier = create_empty_member_dossier("nancy-pelosi", "Nancy Pelosi")
    dossier.evidence_sources.append(
        EvidenceSource(
            source_type="member_metadata",
            source_name="Office roster",
            source_url="https://example.test/roster",
            retrieved_at="2026-04-30",
            notes="Public record",
        )
    )

    html = render_member_dossier_html(dossier)

    assert "<th>source_type</th>" in html
    assert "<td>member_metadata</td>" in html
    assert "<td>Office roster</td>" in html
    assert "<td>https://example.test/roster</td>" in html
    assert "<td>2026-04-30</td>" in html
    assert "<td>Public record</td>" in html


def test_write_creates_parent_dirs(tmp_path):
    dossier = create_empty_member_dossier("nancy-pelosi", "Nancy Pelosi")
    output_path = tmp_path / "nested" / "nancy-pelosi.html"

    returned = write_member_dossier_html(dossier, output_path)

    assert returned == output_path
    assert output_path.exists()
    assert output_path.read_text(encoding="utf-8").startswith("<!doctype html>")


def test_html_filename_slug_behavior():
    dossier = create_empty_member_dossier(" Nancy Pelosi ", "Nancy Pelosi")

    assert dossier_html_filename(dossier) == "nancy-pelosi.html"


def test_batch_write_duplicate_filename_fails_closed(tmp_path):
    dossiers = [
        create_empty_member_dossier("Nancy Pelosi", "Nancy Pelosi"),
        create_empty_member_dossier("nancy-pelosi", "Nancy Pelosi"),
    ]

    with pytest.raises(ValueError, match="Duplicate dossier filename: nancy-pelosi.html"):
        write_member_dossiers_html(dossiers, tmp_path)

    assert list(tmp_path.glob("*.html")) == []


def test_cli_single_html_export(tmp_path, monkeypatch, capsys):
    class FakeExtraction:
        success = True
        extracted_text = "Name: Hon. Nancy Pelosi\nASSETS\nNone"
        error = None

    class FakeExtractor:
        def extract(self, pdf_path, source):
            return FakeExtraction()

    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF")
    output_path = tmp_path / "dossiers" / "nancy-pelosi.html"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "transparencyx",
            "validate-real",
            "--pdf",
            str(pdf_path),
            "--dossier-html",
            str(output_path),
        ],
    )
    monkeypatch.setattr("transparencyx.cli.get_registered_sources", lambda: {"house": object()})
    monkeypatch.setattr(
        "transparencyx.cli.get_extractor_for_source",
        lambda source, file_ext: FakeExtractor(),
    )
    monkeypatch.setattr(
        "transparencyx.cli.process_assets_for_disclosure",
        lambda db_path, raw_disclosure_id, politician_id, extracted_text: 0,
    )
    monkeypatch.setattr(
        "transparencyx.shape.export.build_financial_shape_export",
        lambda db_path, politician_id: {
            "politician_id": politician_id,
            "summary": {},
            "trace": {},
        },
    )

    from transparencyx.cli import main

    main()

    captured = capsys.readouterr()

    assert f"Wrote member dossier HTML: {output_path}" in captured.out
    assert output_path.exists()
    assert "Nancy Pelosi" in output_path.read_text(encoding="utf-8")


def test_html_index_complete_document():
    dossiers = [create_empty_member_dossier("nancy-pelosi", "Nancy Pelosi")]

    html = render_dossier_html_index(dossiers)

    assert html.startswith("<!doctype html>\n<html")
    assert "<title>TransparencyX Dossier Index</title>" in html
    assert "<h1>TransparencyX Dossier Index</h1>" in html
    assert "</html>\n" in html
    assert html.endswith("\n")


def test_html_index_total_dossier_count():
    dossiers = [
        create_empty_member_dossier("nancy-pelosi", "Nancy Pelosi"),
        create_empty_member_dossier("jane-public", "Jane Public"),
    ]

    html = render_dossier_html_index(dossiers)

    assert "<p>total dossier count: 2</p>" in html


def test_html_index_links_to_dossier_html_filenames():
    dossiers = [
        create_empty_member_dossier("Nancy Pelosi", "Nancy Pelosi"),
        create_empty_member_dossier("Jane Public", "Jane Public"),
    ]

    html = render_dossier_html_index(dossiers)

    assert '<a href="nancy-pelosi.html">nancy-pelosi.html</a>' in html
    assert '<a href="jane-public.html">jane-public.html</a>' in html


def test_html_index_escapes_data_values():
    dossier = MemberDossier(
        identity=MemberIdentity(
            member_id="member-1",
            full_name="<Jane & Public>",
            chamber="<House>",
            state="A&B",
        ),
        office=MemberOffice(),
        financials=DossierFinancials(),
        exposure=DossierExposure(),
    )

    html = render_dossier_html_index([dossier])

    assert "&lt;Jane &amp; Public&gt;" in html
    assert "&lt;House&gt;" in html
    assert "A&amp;B" in html
    assert "<Jane & Public>" not in html


def test_html_index_missing_values_render_unknown():
    dossier = create_empty_member_dossier("nancy-pelosi", "Nancy Pelosi")

    html = render_dossier_html_index([dossier])

    assert "<td>Unknown</td>" in html


def test_write_html_index_supports_directory_target(tmp_path):
    dossier = create_empty_member_dossier("nancy-pelosi", "Nancy Pelosi")
    output_dir = tmp_path / "site"
    output_dir.mkdir()

    path = write_dossier_html_index([dossier], output_dir)

    assert path == output_dir / "index.html"
    assert path.exists()
    assert "TransparencyX Dossier Index" in path.read_text(encoding="utf-8")


def test_cli_html_index_without_html_fails_closed(monkeypatch, capsys):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "transparencyx",
            "--batch-dossier-json",
            "input",
            "--output-dir",
            "out",
            "--html-index",
        ],
    )

    from transparencyx.cli import main

    with pytest.raises(SystemExit) as exit_info:
        main()

    captured = capsys.readouterr()

    assert exit_info.value.code == 0
    assert captured.out == "HTML index requires HTML dossier export.\n"


def test_cli_html_index_success(tmp_path, monkeypatch, capsys):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "dossiers"
    input_dir.mkdir()

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "transparencyx",
            "--batch-dossier-json",
            str(input_dir),
            "--output-dir",
            str(output_dir),
            "--html",
            "--html-index",
        ],
    )
    monkeypatch.setattr(
        "transparencyx.profile.batch.build_profiles_for_directory",
        lambda directory: [
            {
                "member_name": "Nancy Pelosi",
                "chamber": "House",
            }
        ],
    )

    from transparencyx.cli import main

    with pytest.raises(SystemExit) as exit_info:
        main()

    captured = capsys.readouterr()
    index_path = output_dir / "index.html"

    assert exit_info.value.code == 0
    assert f"Wrote dossier HTML index: {index_path}\n" in captured.out
    assert index_path.exists()
    assert '<a href="nancy-pelosi.html">nancy-pelosi.html</a>' in index_path.read_text(
        encoding="utf-8"
    )


def test_forbidden_language_absent():
    dossier = create_empty_member_dossier("nancy-pelosi", "Nancy Pelosi")
    html = (
        render_member_dossier_html(dossier)
        + render_dossier_html_index([dossier])
    ).lower()
    restricted_terms = [
        "cor" + "ruption",
        "self-" + "dealing",
        "insider trading " + "confirmed",
        "conflict " + "confirmed",
        "mis" + "conduct",
        "sus" + "picious",
    ]

    for term in restricted_terms:
        assert term not in html
