import re
from html import escape
from pathlib import Path

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


def _format_range(minimum, maximum) -> str:
    return f"{_format_money(minimum)} - {_format_money(maximum)}"


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


def render_member_dossier_html(dossier: MemberDossier) -> str:
    identity = dossier.identity
    office = dossier.office
    financials = dossier.financials
    exposure = dossier.exposure
    exposure_rows = exposure.federal_award_exposure
    candidates = exposure.recipient_candidates
    agencies = _agencies(exposure_rows)

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
  <header>
    <h1>{_display(identity.full_name)}</h1>
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
    <dl>
      <dt>disclosure years</dt><dd>{_display_list(financials.disclosure_years)}</dd>
      <dt>asset count</dt><dd>{_display(financials.asset_count)}</dd>
      <dt>asset value range</dt><dd>{_format_range(financials.asset_value_min, financials.asset_value_max)}</dd>
      <dt>income range</dt><dd>{_format_range(financials.income_min, financials.income_max)}</dd>
      <dt>trade count</dt><dd>{_display(financials.trade_count)}</dd>
      <dt>liability count</dt><dd>{_display(financials.liability_count)}</dd>
      <dt>business interests count</dt><dd>{len(financials.business_interests)}</dd>
    </dl>
  </section>
  <section>
    <h2>Federal Award Exposure</h2>
    <dl>
      <dt>exposure rows count</dt><dd>{len(exposure_rows)}</dd>
      <dt>exposure counted</dt><dd>{_display_bool(exposure.exposure_counted)}</dd>
      <dt>total awards found</dt><dd>{_display(_sum_numeric(exposure_rows, "award_count"))}</dd>
      <dt>total award amount</dt><dd>{_format_money(_sum_numeric(exposure_rows, "total_award_amount"))}</dd>
      <dt>agencies found</dt><dd>{_display_list(agencies)}</dd>
    </dl>
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
) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_member_dossier_html(dossier), encoding="utf-8")
    return path


def dossier_html_filename(dossier: MemberDossier) -> str:
    member_id = dossier.identity.member_id.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", member_id).strip("-")
    return f"{slug or 'unknown'}.html"


def write_member_dossiers_html(
    dossiers: list[MemberDossier],
    output_dir: str | Path,
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
        write_member_dossier_html(dossier, directory / filename)
        for dossier, filename in zip(dossiers, filenames)
    ]


def render_dossier_html_index(dossiers: list[MemberDossier]) -> str:
    rows = []
    for dossier in dossiers:
        identity = dossier.identity
        filename = dossier_html_filename(dossier)
        rows.append(
            "<tr>"
            f"{_cell(identity.full_name)}"
            f"{_cell(identity.chamber)}"
            f"{_cell(identity.state)}"
            f"{_cell(identity.district)}"
            f"{_cell(identity.party)}"
            f'<td><a href="{escape(filename)}">{escape(filename)}</a></td>'
            "</tr>"
        )

    table_rows = "\n".join(rows)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>TransparencyX Dossier Index</title>
  <style>
    body {{ font-family: Arial, sans-serif; line-height: 1.45; margin: 2rem; color: #1f2933; }}
    main {{ max-width: 980px; margin: 0 auto; }}
    h1 {{ margin: 0 0 0.75rem; }}
    table {{ border-collapse: collapse; width: 100%; font-size: 0.95rem; }}
    th, td {{ border: 1px solid #d8dee4; padding: 0.45rem; text-align: left; vertical-align: top; }}
    th {{ background: #f6f8fa; }}
  </style>
</head>
<body>
<main>
  <h1>TransparencyX Dossier Index</h1>
  <p>total dossier count: {len(dossiers)}</p>
  <table>
    <thead>
      <tr>
        <th>full_name</th>
        <th>chamber</th>
        <th>state</th>
        <th>district</th>
        <th>party</th>
        <th>file</th>
      </tr>
    </thead>
    <tbody>
{table_rows}
    </tbody>
  </table>
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
