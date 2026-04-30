from transparencyx.shape.card import render_financial_shape_card
from transparencyx.shape.card import format_money


def _display_value(value) -> str:
    if value is None or value == "":
        return "Unknown"
    return str(value)


def render_federal_award_exposure(exposures: list[dict]) -> str:
    award_count = sum(exposure.get("award_count", 0) or 0 for exposure in exposures)
    total_award_amount = sum(exposure.get("total_award_amount", 0) or 0 for exposure in exposures)
    agencies = sorted({
        agency
        for exposure in exposures
        for agency in exposure.get("agencies", [])
        if agency
    })

    lines = [
        "Federal Award Exposure:",
        f"- queried business interests: {len(exposures)}",
        f"- awards found: {award_count}",
        f"- total award amount: {format_money(total_award_amount)}",
        f"- agencies: {', '.join(agencies) if agencies else 'None'}",
    ]

    return "\n".join(lines)


def render_member_profile_card(profile: dict) -> str:
    lines = [
        "MEMBER PROFILE",
        "",
        f"Name: {_display_value(profile.get('member_name'))}",
        f"Politician ID: {_display_value(profile.get('politician_id'))}",
        f"Filing Year: {_display_value(profile.get('filing_year'))}",
        f"Source: {_display_value(profile.get('source'))}",
        f"Disclosure Path: {_display_value(profile.get('disclosure_path'))}",
        "",
        render_financial_shape_card(profile["shape_export"]),
    ]

    if "federal_award_exposure" in profile:
        lines.extend([
            "",
            render_federal_award_exposure(profile["federal_award_exposure"]),
        ])

    return "\n".join(lines)
