from transparencyx.dossier.schema import MemberDossier


def _display_value(value) -> str:
    if value is None or value == "":
        return "Unknown"
    return str(value)


def _display_list(values: list) -> str:
    if not values:
        return "None"
    return ", ".join(str(value) for value in values)


def render_member_dossier_summary(dossier: MemberDossier) -> str:
    return "\n".join([
        "Member Dossier:",
        f"- name: {_display_value(dossier.identity.full_name)}",
        f"- member id: {_display_value(dossier.identity.member_id)}",
        f"- chamber: {_display_value(dossier.identity.chamber)}",
        f"- state: {_display_value(dossier.identity.state)}",
        f"- district: {_display_value(dossier.identity.district)}",
        f"- party: {_display_value(dossier.identity.party)}",
        f"- official salary: {_display_value(dossier.office.official_salary)}",
        f"- leadership roles: {_display_list(dossier.office.leadership_roles)}",
        f"- committee assignments: {_display_list(dossier.office.committee_assignments)}",
        f"- disclosure years: {_display_list(dossier.financials.disclosure_years)}",
        (
            "- disclosed business interests: "
            f"{len(dossier.financials.business_interests)}"
        ),
        (
            "- federal award exposure rows: "
            f"{len(dossier.exposure.federal_award_exposure)}"
        ),
        f"- recipient candidate rows: {len(dossier.exposure.recipient_candidates)}",
        f"- evidence sources: {len(dossier.evidence_sources)}",
    ])
