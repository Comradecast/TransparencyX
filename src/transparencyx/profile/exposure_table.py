from transparencyx.shape.card import format_money

TABLE_COLUMNS = [
    "member_name",
    "queried_businesses",
    "awards_found",
    "total_award_amount",
    "agencies",
]


def _display_member_name(value) -> str:
    if value is None or value == "":
        return "Unknown"
    return str(value)


def summarize_profile_exposure(profile: dict) -> dict:
    exposures = profile.get("federal_award_exposure") or []
    agencies = sorted({
        agency
        for exposure in exposures
        for agency in exposure.get("agencies", [])
        if agency
    })

    return {
        "member_name": _display_member_name(profile.get("member_name")),
        "queried_businesses": len(exposures),
        "awards_found": sum(exposure.get("award_count", 0) or 0 for exposure in exposures),
        "total_award_amount": float(sum(exposure.get("total_award_amount", 0) or 0 for exposure in exposures)),
        "agencies": agencies,
    }


def render_batch_exposure_table(profiles: list[dict]) -> str:
    lines = [" | ".join(TABLE_COLUMNS)]

    for profile in profiles:
        summary = summarize_profile_exposure(profile)
        row = [
            summary["member_name"],
            str(summary["queried_businesses"]),
            str(summary["awards_found"]),
            format_money(summary["total_award_amount"]),
            ", ".join(summary["agencies"]) if summary["agencies"] else "None",
        ]
        lines.append(" | ".join(row))

    return "\n".join(lines)
