import re
from pathlib import Path

from transparencyx.dossier.schema import (
    DossierExposure,
    DossierFinancials,
    EvidenceSource,
    MemberDossier,
    MemberIdentity,
    MemberOffice,
)


def _slug_member_id(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "unknown"


def _first_text(profile: dict, *keys: str) -> str | None:
    for key in keys:
        value = profile.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _optional_text(profile: dict, key: str) -> str | None:
    value = profile.get(key)
    if isinstance(value, str):
        return value
    return None


def _list_of_strings(value) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _list_of_ints(value) -> list[int]:
    if not isinstance(value, list):
        return []
    return [
        item
        for item in value
        if isinstance(item, int) and not isinstance(item, bool)
    ]


def _list_of_dicts(value) -> list[dict]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _int_or_none(value) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return None


def _number_or_none(value) -> float | int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return value
    return None


def _nested_dict(profile: dict, key: str) -> dict:
    value = profile.get(key)
    if isinstance(value, dict):
        return value
    return {}


def _shape_summary(profile: dict) -> dict:
    shape_export = _nested_dict(profile, "shape_export")
    summary = shape_export.get("summary")
    if isinstance(summary, dict):
        return summary
    return {}


def _first_int(profile: dict, top_key: str, nested: dict, nested_key: str) -> int | None:
    top_value = _int_or_none(profile.get(top_key))
    if top_value is not None:
        return top_value
    return _int_or_none(nested.get(nested_key))


def _first_number(
    profile: dict,
    top_key: str,
    nested: dict,
    nested_key: str,
) -> float | int | None:
    top_value = _number_or_none(profile.get(top_key))
    if top_value is not None:
        return top_value
    return _number_or_none(nested.get(nested_key))


def _query_name_from_exposure(row: dict) -> str | None:
    for key in (
        "original_query_name",
        "cleaned_query_name",
        "query_name",
        "original_name",
        "clean_name",
        "business_interest",
    ):
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _business_interests(profile: dict, exposures: list[dict]) -> list[str]:
    direct = _list_of_strings(profile.get("business_interests"))
    if direct:
        return direct

    interests = []
    seen = set()
    for row in exposures:
        name = _query_name_from_exposure(row)
        if name is not None and name not in seen:
            interests.append(name)
            seen.add(name)
    return interests


def _exposure_counted(exposures: list[dict]) -> bool:
    total = 0
    for row in exposures:
        award_count = row.get("award_count", 0)
        if isinstance(award_count, bool):
            continue
        if isinstance(award_count, int | float):
            total += award_count
    return total > 0


def _source_name(value: str) -> str:
    basename = Path(value).name
    return basename or value


def _evidence_sources(profile: dict) -> list[EvidenceSource]:
    sources = []

    source_pdf = _first_text(profile, "source_pdf")
    if source_pdf is not None:
        sources.append(
            EvidenceSource(
                source_type="financial_disclosure_pdf",
                source_name=_source_name(source_pdf),
                source_url=None,
            )
        )

    source_path = _first_text(profile, "source_path")
    if source_path is not None:
        sources.append(
            EvidenceSource(
                source_type="financial_disclosure_pdf",
                source_name=_source_name(source_path),
                source_url=None,
            )
        )

    disclosure_path = _first_text(profile, "disclosure_path")
    if disclosure_path is not None:
        sources.append(
            EvidenceSource(
                source_type="financial_disclosure_pdf",
                source_name=_source_name(disclosure_path),
                source_url=None,
            )
        )

    source_url = _first_text(profile, "source_url")
    if source_url is not None:
        sources.append(
            EvidenceSource(
                source_type="financial_disclosure_pdf",
                source_name=_source_name(source_url),
                source_url=source_url,
            )
        )

    return sources


def build_member_dossier_from_profile(profile: dict) -> MemberDossier:
    if not isinstance(profile, dict):
        profile = {}

    full_name = _first_text(profile, "member_name", "name") or "Unknown"
    member_id = _first_text(profile, "member_id") or _slug_member_id(full_name)

    financial_shape = _nested_dict(profile, "financial_shape")
    income_shape = _nested_dict(profile, "income_shape")
    summary = _shape_summary(profile)
    if not financial_shape:
        financial_shape = summary
    if not income_shape:
        income_shape = summary

    disclosure_years = _list_of_ints(profile.get("disclosure_years"))
    if not disclosure_years:
        disclosure_year = _int_or_none(profile.get("disclosure_year"))
        if disclosure_year is None:
            disclosure_year = _int_or_none(profile.get("filing_year"))
        if disclosure_year is not None:
            disclosure_years = [disclosure_year]

    federal_award_exposure = _list_of_dicts(profile.get("federal_award_exposure"))
    recipient_candidates = _list_of_dicts(profile.get("recipient_candidates"))
    if not recipient_candidates:
        recipient_candidates = _list_of_dicts(profile.get("recipient_candidate_audit"))

    return MemberDossier(
        identity=MemberIdentity(
            member_id=member_id,
            full_name=full_name,
            chamber=_optional_text(profile, "chamber"),
            state=_optional_text(profile, "state"),
            district=_optional_text(profile, "district"),
            party=_optional_text(profile, "party"),
            current_status=_optional_text(profile, "current_status"),
        ),
        office=MemberOffice(
            official_salary=_number_or_none(profile.get("official_salary")),
            leadership_roles=_list_of_strings(profile.get("leadership_roles")),
            committee_assignments=_list_of_strings(
                profile.get("committee_assignments")
            ),
            office_start=_optional_text(profile, "office_start"),
            office_end=_optional_text(profile, "office_end"),
        ),
        financials=DossierFinancials(
            disclosure_years=disclosure_years,
            asset_count=_first_int(
                profile,
                "asset_count",
                financial_shape,
                "asset_count",
            ),
            asset_value_min=_first_number(
                profile,
                "asset_value_min",
                financial_shape,
                "asset_value_min",
            ),
            asset_value_max=_first_number(
                profile,
                "asset_value_max",
                financial_shape,
                "asset_value_max",
            ),
            income_min=_first_number(profile, "income_min", income_shape, "income_min"),
            income_max=_first_number(profile, "income_max", income_shape, "income_max"),
            trade_count=_int_or_none(profile.get("trade_count")),
            liability_count=_int_or_none(profile.get("liability_count")),
            business_interests=_business_interests(profile, federal_award_exposure),
        ),
        exposure=DossierExposure(
            federal_award_exposure=federal_award_exposure,
            recipient_candidates=recipient_candidates,
            exposure_counted=_exposure_counted(federal_award_exposure),
        ),
        evidence_sources=_evidence_sources(profile),
    )
