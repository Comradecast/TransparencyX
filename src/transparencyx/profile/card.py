from transparencyx.shape.card import render_financial_shape_card


def _display_value(value) -> str:
    if value is None or value == "":
        return "Unknown"
    return str(value)


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

    return "\n".join(lines)
