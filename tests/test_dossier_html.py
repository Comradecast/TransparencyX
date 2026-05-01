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


def test_member_page_links_back_to_index():
    dossier = create_empty_member_dossier("nancy-pelosi", "Nancy Pelosi")

    html = render_member_dossier_html(dossier)

    assert '<a href="index.html">Back to index</a>' in html
    assert html.index('<a href="index.html">Back to index</a>') < html.index(
        "<h1>Nancy Pelosi</h1>"
    )


def test_member_page_renders_parsed_disclosure_status():
    dossier = create_empty_member_dossier("nancy-pelosi", "Nancy Pelosi")
    dossier.evidence_sources.append(
        EvidenceSource(
            source_type="financial_disclosure_pdf",
            source_name="sample.pdf",
        )
    )

    html = render_member_dossier_html(dossier)

    assert "<h2>Disclosure Data Status</h2>" in html
    assert (
        "This dossier includes parsed financial disclosure data from a local source file."
        in html
    )


def test_member_page_renders_metadata_only_disclosure_status():
    dossier = create_empty_member_dossier("alma-s-adams", "Alma S. Adams")
    dossier.evidence_sources.append(
        EvidenceSource(
            source_type="member_metadata",
            source_name="House Clerk Member Profile",
        )
    )

    html = render_member_dossier_html(dossier)

    assert (
        "This demo dossier was generated from seeded member metadata. "
        "No parsed financial disclosure PDF is attached to this dossier."
    ) in html


def test_member_page_renders_unspecified_disclosure_status():
    dossier = create_empty_member_dossier("nancy-pelosi", "Nancy Pelosi")

    html = render_member_dossier_html(dossier)

    assert "Disclosure data status is not specified." in html


def test_disclosure_status_appears_before_financial_sections():
    dossier = create_empty_member_dossier("nancy-pelosi", "Nancy Pelosi")

    html = render_member_dossier_html(dossier)

    assert html.index("<h2>Disclosure Data Status</h2>") < html.index(
        "<h2>Financial Summary</h2>"
    )


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
    assert "No parsed financial disclosure data is attached to this dossier." in html


def test_empty_lists_render_none():
    dossier = create_empty_member_dossier("nancy-pelosi", "Nancy Pelosi")

    html = render_member_dossier_html(dossier)

    assert "<dt>leadership roles</dt><dd>None</dd>" in html
    assert "<h2>Committee Assignments</h2>\n<p>None</p>" in html
    assert "No federal award exposure data available." in html
    assert "<h2>Evidence Sources</h2>\n<p>None</p>" in html


def test_metadata_only_financial_summary_renders_empty_state():
    dossier = create_empty_member_dossier("alma-s-adams", "Alma S. Adams")
    dossier.evidence_sources.append(
        EvidenceSource(
            source_type="member_metadata",
            source_name="House Clerk Member Profile",
        )
    )

    html = render_member_dossier_html(dossier)

    assert "<h2>Financial Summary</h2>" in html
    assert "No parsed financial disclosure data is attached to this dossier." in html


def test_parsed_disclosure_financial_summary_renders_existing_values():
    dossier = MemberDossier(
        identity=MemberIdentity("nancy-pelosi", "Nancy Pelosi"),
        office=MemberOffice(),
        financials=DossierFinancials(
            asset_count=5,
            asset_value_min=1001.0,
            asset_value_max=15000.0,
            income_min=10.0,
            income_max=100.0,
            trade_count=2,
        ),
        exposure=DossierExposure(),
        evidence_sources=[
            EvidenceSource(
                source_type="financial_disclosure_pdf",
                source_name="sample.pdf",
            )
        ],
    )

    html = render_member_dossier_html(dossier)

    assert "<tr><th>Assets</th><td>5</td></tr>" in html
    assert "<tr><th>Income entries</th><td>Unknown</td></tr>" in html
    assert "<tr><th>Transactions</th><td>2</td></tr>" in html
    assert "<tr><th>Asset range</th><td>$1,001 - $15,000</td></tr>" in html
    assert "<tr><th>Income range</th><td>$10 - $100</td></tr>" in html


def test_member_html_renders_asset_linked_transaction_counts():
    dossier = MemberDossier(
        identity=MemberIdentity("nancy-pelosi", "Nancy Pelosi"),
        office=MemberOffice(),
        financials=DossierFinancials(asset_count=2, trade_count=1),
        exposure=DossierExposure(),
        evidence_sources=[
            EvidenceSource(
                source_type="financial_disclosure_pdf",
                source_name="sample.pdf",
            )
        ],
    )
    asset_summaries = [
        {
            "asset_id": 1,
            "asset_name": "REOF XXV, LLC [AB] SP",
            "linked_transaction_count": 1,
        },
        {
            "asset_id": 2,
            "asset_name": "Apple Inc. (AAPL) [ST] SP",
            "linked_transaction_count": 0,
        },
    ]

    html = render_member_dossier_html(dossier, asset_summaries=asset_summaries)

    assert "<h3>Assets</h3>" in html
    assert "<td>REOF XXV, LLC [AB] SP</td>" in html
    assert "<td>Linked Transactions: 1</td>" in html
    assert "<td>Apple Inc. (AAPL) [ST] SP</td>" in html
    assert "<td>Linked Transactions: 0</td>" in html


def test_member_html_escapes_asset_summary_values():
    dossier = MemberDossier(
        identity=MemberIdentity("nancy-pelosi", "Nancy Pelosi"),
        office=MemberOffice(),
        financials=DossierFinancials(asset_count=1, trade_count=1),
        exposure=DossierExposure(),
        evidence_sources=[
            EvidenceSource(
                source_type="financial_disclosure_pdf",
                source_name="sample.pdf",
            )
        ],
    )

    html = render_member_dossier_html(
        dossier,
        asset_summaries=[
            {
                "asset_id": 1,
                "asset_name": "A & B <Holding>",
                "linked_transaction_count": 1,
            }
        ],
    )

    assert "A &amp; B &lt;Holding&gt;" in html
    assert "A & B <Holding>" not in html


def test_committee_assignments_render_when_present():
    dossier = create_empty_member_dossier("nancy-pelosi", "Nancy Pelosi")
    dossier.office.committee_assignments = [
        "Committee on Appropriations",
        "Committee on Rules",
    ]

    html = render_member_dossier_html(dossier)

    assert "<h2>Committee Assignments</h2>" in html
    assert "<li>Committee on Appropriations</li>" in html
    assert "<li>Committee on Rules</li>" in html
    assert html.index("<li>Committee on Appropriations</li>") < html.index(
        "<li>Committee on Rules</li>"
    )


def test_empty_committee_assignments_render_none():
    dossier = create_empty_member_dossier("nancy-pelosi", "Nancy Pelosi")
    dossier.office.committee_assignments = []

    html = render_member_dossier_html(dossier)

    assert "<h2>Committee Assignments</h2>\n<p>None</p>" in html


def test_none_committee_assignments_render_none():
    dossier = create_empty_member_dossier("nancy-pelosi", "Nancy Pelosi")
    dossier.office.committee_assignments = None

    html = render_member_dossier_html(dossier)

    assert "<h2>Committee Assignments</h2>\n<p>None</p>" in html


def test_committee_assignments_are_html_escaped():
    dossier = create_empty_member_dossier("nancy-pelosi", "Nancy Pelosi")
    dossier.office.committee_assignments = ["Committee <A&B>"]

    html = render_member_dossier_html(dossier)

    assert "<li>Committee &lt;A&amp;B&gt;</li>" in html
    assert "Committee <A&B>" not in html


def test_committee_assignments_section_precedes_financial_summary():
    dossier = create_empty_member_dossier("nancy-pelosi", "Nancy Pelosi")

    html = render_member_dossier_html(dossier)

    assert html.index("<h2>Committee Assignments</h2>") < html.index(
        "<h2>Financial Summary</h2>"
    )


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
        evidence_sources=[
            EvidenceSource(
                source_type="financial_disclosure_pdf",
                source_name="sample.pdf",
            )
        ],
    )

    html = render_member_dossier_html(dossier)

    assert "<dt>official salary</dt><dd>$174,000</dd>" in html
    assert "<tr><th>Asset range</th><td>$1,001 - $15,000.50</td></tr>" in html
    assert "<tr><th>Income range</th><td>$0 - $2,500.25</td></tr>" in html
    assert "<tr><th>Total award amount</th><td>$1,234.50</td></tr>" in html


def test_federal_award_exposure_renders_existing_results():
    dossier = MemberDossier(
        identity=MemberIdentity("nancy-pelosi", "Nancy Pelosi"),
        office=MemberOffice(),
        financials=DossierFinancials(),
        exposure=DossierExposure(
            federal_award_exposure=[
                {
                    "award_count": 2,
                    "total_award_amount": 100.5,
                    "agencies": ["Z Agency", "A Agency"],
                },
                {
                    "award_count": 3,
                    "total_award_amount": 200.0,
                    "agencies": ["A Agency"],
                },
            ]
        ),
    )

    html = render_member_dossier_html(dossier)

    assert "<h2>Federal Award Exposure</h2>" in html
    assert "<tr><th>Matched business interests</th><td>2</td></tr>" in html
    assert "<tr><th>Awards found</th><td>5</td></tr>" in html
    assert "<tr><th>Total award amount</th><td>$300.50</td></tr>" in html
    assert "<tr><th>Agencies</th><td>A Agency, Z Agency</td></tr>" in html


def test_federal_award_exposure_empty_state_renders_when_none_exists():
    dossier = create_empty_member_dossier("nancy-pelosi", "Nancy Pelosi")

    html = render_member_dossier_html(dossier)

    assert "<h2>Federal Award Exposure</h2>" in html
    assert "No federal award exposure data available." in html


def test_boolean_yes_no():
    dossier = MemberDossier(
        identity=MemberIdentity("nancy-pelosi", "Nancy Pelosi"),
        office=MemberOffice(),
        financials=DossierFinancials(),
        exposure=DossierExposure(
            recipient_candidates=[{"exposure_counted": True}]
        ),
    )

    html = render_member_dossier_html(dossier)

    assert "<td>Yes</td>" in html

    dossier.exposure.recipient_candidates = [{"exposure_counted": False}]
    assert "<td>No</td>" in render_member_dossier_html(dossier)


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
    html = output_path.read_text(encoding="utf-8")
    assert "Nancy Pelosi" in html
    assert (
        "This dossier includes parsed financial disclosure data from a local source file."
        in html
    )


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


def test_html_index_contains_intro_text():
    dossiers = [create_empty_member_dossier("nancy-pelosi", "Nancy Pelosi")]

    html = render_dossier_html_index(dossiers)

    assert (
        '<p class="intro">This is a TransparencyX dossier index. '
        "Each row links to a member dossier page. "
        "Demo output may be fixture-backed depending on the command used to build the site.</p>"
    ) in html


def test_html_index_renders_dataset_summary():
    dossiers = [
        MemberDossier(
            identity=MemberIdentity(
                "alma-s-adams",
                "Alma S. Adams",
                chamber="House",
                state="NC",
                district="12",
                party="Democratic",
                current_status="current",
            ),
            office=MemberOffice(),
            financials=DossierFinancials(),
            exposure=DossierExposure(),
        ),
        MemberDossier(
            identity=MemberIdentity(
                "thom-tillis",
                "Thom Tillis",
                chamber="Senate",
                state="NC",
                party="Republican",
                current_status="current",
            ),
            office=MemberOffice(),
            financials=DossierFinancials(),
            exposure=DossierExposure(),
        ),
    ]

    html = render_dossier_html_index(dossiers)

    assert "<h2>Dataset Summary</h2>" in html
    assert "<dt>Total dossiers</dt><dd>2</dd>" in html
    assert "<dt>House</dt><dd>1</dd>" in html
    assert "<dt>Senate</dt><dd>1</dd>" in html
    assert "<dt>States</dt><dd>NC</dd>" in html
    assert "<dt>Current members</dt><dd>2</dd>" in html


def test_html_index_summary_renders_unknown_for_missing_states():
    dossier = create_empty_member_dossier("nancy-pelosi", "Nancy Pelosi")

    html = render_dossier_html_index([dossier])

    assert "<dt>States</dt><dd>Unknown</dd>" in html


def test_html_index_links_to_dossier_html_filenames():
    dossiers = [
        create_empty_member_dossier("Nancy Pelosi", "Nancy Pelosi"),
        create_empty_member_dossier("Jane Public", "Jane Public"),
    ]

    html = render_dossier_html_index(dossiers)

    assert '<a href="nancy-pelosi.html">nancy-pelosi.html</a>' in html
    assert '<a href="jane-public.html">jane-public.html</a>' in html


def test_html_index_renders_chamber_anchor_navigation():
    dossiers = [
        MemberDossier(
            identity=MemberIdentity("house", "House Member", chamber="House"),
            office=MemberOffice(),
            financials=DossierFinancials(),
            exposure=DossierExposure(),
        ),
        MemberDossier(
            identity=MemberIdentity("senate", "Senate Member", chamber="Senate"),
            office=MemberOffice(),
            financials=DossierFinancials(),
            exposure=DossierExposure(),
        ),
    ]

    html = render_dossier_html_index(dossiers)

    assert '<nav class="index-nav">' in html
    assert '<a href="#house">House</a>' in html
    assert '<a href="#senate">Senate</a>' in html


def test_html_index_renders_house_before_senate():
    dossiers = [
        MemberDossier(
            identity=MemberIdentity("senate", "Senate Member", chamber="Senate"),
            office=MemberOffice(),
            financials=DossierFinancials(),
            exposure=DossierExposure(),
        ),
        MemberDossier(
            identity=MemberIdentity("house", "House Member", chamber="House"),
            office=MemberOffice(),
            financials=DossierFinancials(),
            exposure=DossierExposure(),
        ),
    ]

    html = render_dossier_html_index(dossiers)

    assert html.index('<h2 id="house">House</h2>') < html.index(
        '<h2 id="senate">Senate</h2>'
    )


def test_html_index_sorts_house_rows_by_numeric_district():
    dossiers = [
        MemberDossier(
            identity=MemberIdentity("house-10", "House Ten", chamber="House", district="10"),
            office=MemberOffice(),
            financials=DossierFinancials(),
            exposure=DossierExposure(),
        ),
        MemberDossier(
            identity=MemberIdentity("house-2", "House Two", chamber="House", district="2"),
            office=MemberOffice(),
            financials=DossierFinancials(),
            exposure=DossierExposure(),
        ),
    ]

    html = render_dossier_html_index(dossiers)

    assert html.index("house-2.html") < html.index("house-10.html")


def test_html_index_sorts_senate_rows_by_name():
    dossiers = [
        MemberDossier(
            identity=MemberIdentity("senator-b", "Senator B", chamber="Senate"),
            office=MemberOffice(),
            financials=DossierFinancials(),
            exposure=DossierExposure(),
        ),
        MemberDossier(
            identity=MemberIdentity("senator-a", "Senator A", chamber="Senate"),
            office=MemberOffice(),
            financials=DossierFinancials(),
            exposure=DossierExposure(),
        ),
    ]

    html = render_dossier_html_index(dossiers)

    assert html.index("senator-a.html") < html.index("senator-b.html")


def test_html_index_includes_current_status():
    dossier = create_empty_member_dossier("nancy-pelosi", "Nancy Pelosi")
    dossier.identity.current_status = "current"

    html = render_dossier_html_index([dossier])

    assert "<th>current_status</th>" in html
    assert "<td>current</td>" in html


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
        "accusation",
        "cor" + "ruption",
        "conflict",
        "influence",
        "ranking",
        "risk",
        "score",
        "self-" + "dealing",
        "insider trading " + "confirmed",
        "mis" + "conduct",
        "sus" + "picious",
        "wrongdoing",
    ]

    for term in restricted_terms:
        assert term not in html
