import re
from html import escape
from pathlib import Path

from transparencyx.dossier.export import dossier_index_sort_key
from transparencyx.dossier.schema import MemberDossier


def _display(value) -> str:
    if value is None or value == "":
        return "Unknown"
    return escape(str(value))


def _display_list(values: list) -> str:
    if not values:
        return "None"
    return ", ".join(escape(str(value)) for value in values)


def _plain_list_section(values: list | None) -> str:
    if not values:
        return "<p>None</p>"
    items = [f"<li>{escape(str(value))}</li>" for value in values]
    return "<ul>\n" + "\n".join(items) + "\n</ul>"


def _display_bool(value) -> str:
    return "Yes" if value else "No"


def _clean_text(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _index_summary(dossiers: list[MemberDossier]) -> dict:
    states = {
        state
        for dossier in dossiers
        if (state := _clean_text(dossier.identity.state)) is not None
    }
    return {
        "total": len(dossiers),
        "house": sum(1 for dossier in dossiers if dossier.identity.chamber == "House"),
        "senate": sum(1 for dossier in dossiers if dossier.identity.chamber == "Senate"),
        "states": ", ".join(sorted(states)) if states else "Unknown",
        "current": sum(
            1
            for dossier in dossiers
            if str(dossier.identity.current_status or "").strip().lower() == "current"
        ),
    }


def _summary_card(label: str, value) -> str:
    return (
        '<div class="summary-card">'
        f"<dt>{escape(label)}</dt>"
        f"<dd>{escape(str(value))}</dd>"
        "</div>"
    )


def _has_parsed_disclosure_data(dossier: MemberDossier) -> bool:
    return any(
        source.source_type == "financial_disclosure_pdf"
        for source in dossier.evidence_sources
    )


def _disclosure_data_status_text(dossier: MemberDossier) -> str:
    if _has_parsed_disclosure_data(dossier):
        return "This dossier includes parsed financial disclosure data from a local source file."
    source_types = {
        source.source_type
        for source in dossier.evidence_sources
        if source.source_type
    }
    if "member_metadata" in source_types:
        return (
            "This demo dossier was generated from seeded member metadata. "
            "No parsed financial disclosure PDF is attached to this dossier."
        )
    return "Disclosure data status is not specified."


def _format_money(value) -> str:
    if value is None or value == "":
        return "Unknown"
    if isinstance(value, bool):
        return "Unknown"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return _display(value)
    if number.is_integer():
        return f"${number:,.0f}"
    return f"${number:,.2f}"


def _format_count(value) -> str:
    if value is None or value == "":
        return "Unknown"
    if isinstance(value, bool):
        return "Unknown"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return _display(value)
    if number.is_integer():
        return str(int(number))
    return str(number)


def _format_range(minimum, maximum) -> str:
    return f"{_format_money(minimum)} - {_format_money(maximum)}"


def _format_linked_transaction_count(value) -> str:
    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        return str(value)
    return "Unknown"


def _asset_summary_rows(asset_summaries: list[dict] | None) -> str:
    if not asset_summaries:
        return ""

    rows = [
        "<h3>Assets</h3>",
        "<table>",
        "<thead><tr><th>Asset</th><th>Linked Transactions</th></tr></thead>",
        "<tbody>",
    ]
    for row in asset_summaries:
        if not isinstance(row, dict):
            continue
        rows.append(
            "<tr>"
            f"{_cell(row.get('asset_name'))}"
            "<td>Linked Transactions: "
            f"{_format_linked_transaction_count(row.get('linked_transaction_count'))}"
            "</td>"
            "</tr>"
        )
    rows.extend(["</tbody>", "</table>"])
    return "\n".join(rows)


def _financial_summary_rows(
    dossier: MemberDossier,
    asset_summaries: list[dict] | None = None,
) -> str:
    if not _has_parsed_disclosure_data(dossier):
        return "<p>No parsed financial disclosure data is attached to this dossier.</p>"

    financials = dossier.financials
    rows = [
        ("Assets", _display(financials.asset_count)),
        ("Income entries", "Unknown"),
        ("Transactions", _display(financials.trade_count)),
        ("Asset range", _format_range(financials.asset_value_min, financials.asset_value_max)),
        ("Income range", _format_range(financials.income_min, financials.income_max)),
    ]
    rendered_rows = [
        f"<tr><th>{escape(label)}</th><td>{value}</td></tr>"
        for label, value in rows
    ]
    summary_table = (
        "<table>\n<tbody>\n" + "\n".join(rendered_rows) + "\n</tbody>\n</table>"
    )
    asset_table = _asset_summary_rows(asset_summaries)
    if asset_table:
        return summary_table + "\n" + asset_table
    return summary_table


def _cell(value) -> str:
    return f"<td>{_display(value)}</td>"


def _bool_cell(value) -> str:
    return f"<td>{_display_bool(bool(value))}</td>"


def _candidate_status(row: dict) -> str:
    status = row.get("match_status") or row.get("status")
    if status == "candidate_review_only":
        return "review-only"
    return status or "Unknown"


def _sum_numeric(rows: list[dict], key: str) -> float:
    total = 0.0
    for row in rows:
        value = row.get(key)
        if isinstance(value, bool):
            continue
        if isinstance(value, int | float):
            total += value
    return total


def _agencies(exposures: list[dict]) -> list[str]:
    agencies = set()
    for exposure in exposures:
        for agency in exposure.get("agencies", []) or []:
            if agency:
                agencies.add(str(agency))
    return sorted(agencies)


def _federal_award_exposure_rows(exposures: list[dict]) -> str:
    if not exposures:
        return "<p>No federal award exposure data available.</p>"

    rows = [
        ("Matched business interests", _format_count(len(exposures))),
        ("Awards found", _format_count(_sum_numeric(exposures, "award_count"))),
        (
            "Total award amount",
            _format_money(_sum_numeric(exposures, "total_award_amount")),
        ),
        ("Agencies", _display_list(_agencies(exposures))),
    ]
    rendered_rows = [
        f"<tr><th>{escape(label)}</th><td>{value}</td></tr>"
        for label, value in rows
    ]
    return "<table>\n<tbody>\n" + "\n".join(rendered_rows) + "\n</tbody>\n</table>"


def _candidate_rows(candidates: list[dict]) -> str:
    if not candidates:
        return "<p>None</p>"

    rows = [
        "<table>",
        "<thead><tr>"
        "<th>original_query</th>"
        "<th>candidate_query</th>"
        "<th>recipient_name</th>"
        "<th>award_count</th>"
        "<th>total_award_amount</th>"
        "<th>status</th>"
        "<th>substring_match</th>"
        "<th>token_overlap</th>"
        "<th>exposure_counted</th>"
        "</tr></thead>",
        "<tbody>",
    ]
    for candidate in candidates:
        rows.append(
            "<tr>"
            f"{_cell(candidate.get('original_query'))}"
            f"{_cell(candidate.get('candidate_query'))}"
            f"{_cell(candidate.get('recipient_name'))}"
            f"{_cell(candidate.get('award_count'))}"
            f"<td>{_format_money(candidate.get('total_award_amount'))}</td>"
            f"{_cell(_candidate_status(candidate))}"
            f"{_bool_cell(candidate.get('substring_match'))}"
            f"{_cell(candidate.get('token_overlap'))}"
            f"{_bool_cell(candidate.get('exposure_counted'))}"
            "</tr>"
        )
    rows.extend(["</tbody>", "</table>"])
    return "\n".join(rows)


def _evidence_rows(dossier: MemberDossier) -> str:
    if not dossier.evidence_sources:
        return "<p>None</p>"

    rows = [
        "<table>",
        "<thead><tr>"
        "<th>source_type</th>"
        "<th>source_name</th>"
        "<th>source_url</th>"
        "<th>retrieved_at</th>"
        "<th>notes</th>"
        "</tr></thead>",
        "<tbody>",
    ]
    for source in dossier.evidence_sources:
        rows.append(
            "<tr>"
            f"{_cell(source.source_type)}"
            f"{_cell(source.source_name)}"
            f"{_cell(source.source_url)}"
            f"{_cell(source.retrieved_at)}"
            f"{_cell(source.notes)}"
            "</tr>"
        )
    rows.extend(["</tbody>", "</table>"])
    return "\n".join(rows)


def render_member_dossier_html(
    dossier: MemberDossier,
    asset_summaries: list[dict] | None = None,
) -> str:
    identity = dossier.identity
    office = dossier.office
    financials = dossier.financials
    exposure = dossier.exposure
    exposure_rows = exposure.federal_award_exposure
    candidates = exposure.recipient_candidates

    document = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>TransparencyX Dossier - {_display(identity.full_name)}</title>
  <style>
    body {{ font-family: Arial, sans-serif; line-height: 1.45; margin: 2rem; color: #1f2933; }}
    main {{ max-width: 980px; margin: 0 auto; }}
    section {{ border-top: 1px solid #d8dee4; padding: 1rem 0; }}
    h1, h2 {{ margin: 0 0 0.75rem; }}
    .nav {{ margin: 0 0 1rem; }}
    .status-banner {{ border: 1px solid #d8dee4; padding: 0.75rem; margin: 0 0 1rem; }}
    .status-banner h2 {{ font-size: 1rem; margin: 0 0 0.35rem; }}
    .status-banner p {{ margin: 0; }}
    dl {{ display: grid; grid-template-columns: 220px 1fr; gap: 0.4rem 1rem; }}
    dt {{ font-weight: 700; }}
    dd {{ margin: 0; }}
    table {{ border-collapse: collapse; width: 100%; font-size: 0.95rem; }}
    th, td {{ border: 1px solid #d8dee4; padding: 0.45rem; text-align: left; vertical-align: top; }}
    th {{ background: #f6f8fa; }}
  </style>
</head>
<body>
<main>
  <nav class="nav"><a href="index.html">Back to index</a></nav>
  <header>
    <h1>{_display(identity.full_name)}</h1>
    <section class="status-banner">
      <h2>Disclosure Data Status</h2>
      <p>{_display(_disclosure_data_status_text(dossier))}</p>
    </section>
    <dl>
      <dt>member id</dt><dd>{_display(identity.member_id)}</dd>
      <dt>chamber</dt><dd>{_display(identity.chamber)}</dd>
      <dt>state</dt><dd>{_display(identity.state)}</dd>
      <dt>district</dt><dd>{_display(identity.district)}</dd>
      <dt>party</dt><dd>{_display(identity.party)}</dd>
      <dt>current status</dt><dd>{_display(identity.current_status)}</dd>
    </dl>
  </header>
  <section>
    <h2>Committee Assignments</h2>
{_plain_list_section(getattr(office, "committee_assignments", None))}
  </section>
  <section>
    <h2>Office</h2>
    <dl>
      <dt>official salary</dt><dd>{_format_money(office.official_salary)}</dd>
      <dt>leadership roles</dt><dd>{_display_list(office.leadership_roles)}</dd>
      <dt>office start</dt><dd>{_display(office.office_start)}</dd>
      <dt>office end</dt><dd>{_display(office.office_end)}</dd>
    </dl>
  </section>
  <section>
    <h2>Financial Summary</h2>
{_financial_summary_rows(dossier, asset_summaries)}
  </section>
  <section>
    <h2>Federal Award Exposure</h2>
{_federal_award_exposure_rows(exposure_rows)}
  </section>
  <section>
    <h2>Recipient Candidates</h2>
    <p>candidate rows count: {len(candidates)}</p>
{_candidate_rows(candidates)}
  </section>
  <section>
    <h2>Evidence Sources</h2>
{_evidence_rows(dossier)}
  </section>
</main>
</body>
</html>
"""
    return document


def write_member_dossier_html(
    dossier: MemberDossier,
    output_path: str | Path,
    asset_summaries: list[dict] | None = None,
) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        render_member_dossier_html(dossier, asset_summaries),
        encoding="utf-8",
    )
    return path


def dossier_html_filename(dossier: MemberDossier) -> str:
    member_id = dossier.identity.member_id.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", member_id).strip("-")
    return f"{slug or 'unknown'}.html"


def _index_table_header() -> str:
    return """<thead>
      <tr>
        <th>full_name</th>
        <th>chamber</th>
        <th>state</th>
        <th>district</th>
        <th>party</th>
        <th>current_status</th>
        <th>file</th>
      </tr>
    </thead>"""


def _index_row(dossier: MemberDossier) -> str:
    identity = dossier.identity
    filename = dossier_html_filename(dossier)
    return (
        "<tr>"
        f"{_cell(identity.full_name)}"
        f"{_cell(identity.chamber)}"
        f"{_cell(identity.state)}"
        f"{_cell(identity.district)}"
        f"{_cell(identity.party)}"
        f"{_cell(identity.current_status)}"
        f'<td><a href="{escape(filename)}">{escape(filename)}</a></td>'
        "</tr>"
    )


def _index_section(title: str, section_id: str, dossiers: list[MemberDossier]) -> str:
    if not dossiers:
        return ""
    rows = "\n".join(_index_row(dossier) for dossier in dossiers)
    return f"""<section class="index-section">
    <h2 id="{escape(section_id)}">{escape(title)}</h2>
    <table>
      {_index_table_header()}
      <tbody>
{rows}
      </tbody>
    </table>
  </section>"""


def _index_groups(dossiers: list[MemberDossier]) -> dict[str, list[MemberDossier]]:
    sorted_dossiers = sorted(dossiers, key=dossier_index_sort_key)
    return {
        "house": [
            dossier
            for dossier in sorted_dossiers
            if dossier.identity.chamber == "House"
        ],
        "senate": [
            dossier
            for dossier in sorted_dossiers
            if dossier.identity.chamber == "Senate"
        ],
        "unknown": [
            dossier
            for dossier in sorted_dossiers
            if dossier.identity.chamber not in {"House", "Senate"}
        ],
    }


def _index_nav(groups: dict[str, list[MemberDossier]]) -> str:
    links = []
    if groups["house"]:
        links.append('<a href="#house">House</a>')
    if groups["senate"]:
        links.append('<a href="#senate">Senate</a>')
    if groups["unknown"]:
        links.append('<a href="#unknown">Unknown</a>')
    if not links:
        return ""
    return '<nav class="index-nav">\n    ' + "\n    ".join(links) + "\n  </nav>"


def write_member_dossiers_html(
    dossiers: list[MemberDossier],
    output_dir: str | Path,
    asset_summaries_by_member_id: dict[str, list[dict]] | None = None,
) -> list[Path]:
    directory = Path(output_dir)
    filenames = [dossier_html_filename(dossier) for dossier in dossiers]
    seen = set()
    for filename in filenames:
        if filename in seen:
            raise ValueError(f"Duplicate dossier filename: {filename}")
        seen.add(filename)

    directory.mkdir(parents=True, exist_ok=True)
    return [
        write_member_dossier_html(
            dossier,
            directory / filename,
            (
                asset_summaries_by_member_id or {}
            ).get(dossier.identity.member_id),
        )
        for dossier, filename in zip(dossiers, filenames)
    ]


def render_dossier_html_index(dossiers: list[MemberDossier]) -> str:
    groups = _index_groups(dossiers)
    sections = "\n".join([
        _index_section("House", "house", groups["house"]),
        _index_section("Senate", "senate", groups["senate"]),
        _index_section("Unknown", "unknown", groups["unknown"]),
    ]).strip()
    summary = _index_summary(dossiers)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>TransparencyX Dossier Index</title>
  <style>
    body {{ font-family: Arial, sans-serif; line-height: 1.45; margin: 2rem; color: #1f2933; }}
    main {{ max-width: 980px; margin: 0 auto; }}
    h1, h2 {{ margin: 0 0 0.75rem; }}
    .intro {{ margin: 0 0 1rem; max-width: 760px; }}
    .index-nav {{ display: flex; gap: 1rem; margin: 0 0 1rem; }}
    .summary {{ margin: 1rem 0; }}
    .summary-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 0.75rem; }}
    .summary-card {{ border: 1px solid #d8dee4; padding: 0.65rem; }}
    .summary-card dt {{ font-weight: 700; margin: 0 0 0.25rem; }}
    .summary-card dd {{ margin: 0; }}
    table {{ border-collapse: collapse; width: 100%; font-size: 0.95rem; }}
    th, td {{ border: 1px solid #d8dee4; padding: 0.45rem; text-align: left; vertical-align: top; }}
    th {{ background: #f6f8fa; }}
  </style>
</head>
<body>
<main>
  <h1>TransparencyX Dossier Index</h1>
  <p class="intro">This is a TransparencyX dossier index. Each row links to a member dossier page. Demo output may be fixture-backed depending on the command used to build the site.</p>
  {_index_nav(groups)}
  <section class="summary">
    <h2>Dataset Summary</h2>
    <dl class="summary-grid">
      {_summary_card("Total dossiers", summary["total"])}
      {_summary_card("House", summary["house"])}
      {_summary_card("Senate", summary["senate"])}
      {_summary_card("States", summary["states"])}
      {_summary_card("Current members", summary["current"])}
    </dl>
  </section>
  <p>total dossier count: {len(dossiers)}</p>
  {sections}
</main>
</body>
</html>
"""


def write_dossier_html_index(
    dossiers: list[MemberDossier],
    output_path: str | Path,
) -> Path:
    path = Path(output_path)
    if path.exists() and path.is_dir():
        path = path / "index.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_dossier_html_index(dossiers), encoding="utf-8")
    return path
