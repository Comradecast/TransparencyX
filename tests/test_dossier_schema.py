import json
from dataclasses import fields

import pytest

from transparencyx.dossier.render import render_member_dossier_summary
from transparencyx.dossier.schema import (
    DossierExposure,
    DossierFinancials,
    EvidenceSource,
    MemberDossier,
    MemberIdentity,
    MemberOffice,
    create_empty_member_dossier,
)


def test_empty_dossier_creation_strips_required_identity():
    dossier = create_empty_member_dossier(" nancy-pelosi ", " Nancy Pelosi ")

    assert dossier.identity.member_id == "nancy-pelosi"
    assert dossier.identity.full_name == "Nancy Pelosi"
    assert dossier.office == MemberOffice()
    assert dossier.financials == DossierFinancials()
    assert dossier.exposure == DossierExposure()
    assert dossier.evidence_sources == []


def test_blank_member_id_raises_value_error():
    with pytest.raises(ValueError, match="member_id"):
        create_empty_member_dossier("   ", "Nancy Pelosi")


def test_blank_full_name_raises_value_error():
    with pytest.raises(ValueError, match="full_name"):
        create_empty_member_dossier("nancy-pelosi", "   ")


def test_list_defaults_are_not_shared():
    first = create_empty_member_dossier("one", "One Member")
    second = create_empty_member_dossier("two", "Two Member")

    first.office.leadership_roles.append("Speaker")
    first.financials.business_interests.append("Example Holdings")
    first.exposure.federal_award_exposure.append({"recipient": "Example"})
    first.evidence_sources.append(EvidenceSource("disclosure", "Example source"))

    assert second.office.leadership_roles == []
    assert second.financials.business_interests == []
    assert second.exposure.federal_award_exposure == []
    assert second.evidence_sources == []


def test_to_dict_is_json_serializable():
    dossier = create_empty_member_dossier("nancy-pelosi", "Nancy Pelosi")
    dossier.evidence_sources.append(
        EvidenceSource(
            source_type="profile",
            source_name="Official biography",
            source_url="https://example.test/member",
        )
    )

    encoded = json.dumps(dossier.to_dict())

    assert json.loads(encoded)["evidence_sources"][0]["source_name"] == (
        "Official biography"
    )


def test_to_dict_uses_deterministic_keys():
    dossier = create_empty_member_dossier("nancy-pelosi", "Nancy Pelosi")
    dossier_dict = dossier.to_dict()

    assert [field.name for field in fields(MemberDossier)] == [
        "identity",
        "office",
        "financials",
        "exposure",
        "evidence_sources",
    ]
    assert [field.name for field in fields(DossierFinancials)] == [
        "disclosure_years",
        "asset_count",
        "asset_value_min",
        "asset_value_max",
        "income_min",
        "income_max",
        "trade_count",
        "linked_transaction_count",
        "unlinked_transaction_count",
        "linked_transaction_coverage_ratio",
        "liability_count",
        "business_interests",
    ]
    assert list(dossier_dict.keys()) == [
        "identity",
        "office",
        "financials",
        "exposure",
        "evidence_sources",
    ]
    assert list(dossier_dict["identity"].keys()) == [
        "member_id",
        "full_name",
        "chamber",
        "state",
        "district",
        "party",
        "current_status",
    ]
    assert list(dossier_dict["financials"].keys()) == [
        "disclosure_years",
        "asset_count",
        "asset_value_min",
        "asset_value_max",
        "income_min",
        "income_max",
        "trade_count",
        "linked_transaction_count",
        "unlinked_transaction_count",
        "linked_transaction_coverage_ratio",
        "liability_count",
        "business_interests",
    ]
    assert "asset_summaries" not in dossier_dict
    assert "asset_summaries" not in dossier_dict["financials"]


def test_render_missing_values():
    dossier = create_empty_member_dossier("nancy-pelosi", "Nancy Pelosi")

    assert render_member_dossier_summary(dossier) == "\n".join([
        "Member Dossier:",
        "- name: Nancy Pelosi",
        "- member id: nancy-pelosi",
        "- chamber: Unknown",
        "- state: Unknown",
        "- district: Unknown",
        "- party: Unknown",
        "- official salary: Unknown",
        "- leadership roles: None",
        "- committee assignments: None",
        "- disclosure years: None",
        "- disclosed business interests: 0",
        "- federal award exposure rows: 0",
        "- recipient candidate rows: 0",
        "- evidence sources: 0",
    ])


def test_render_populated_values():
    dossier = MemberDossier(
        identity=MemberIdentity(
            member_id="nancy-pelosi",
            full_name="Nancy Pelosi",
            chamber="House",
            state="CA",
            district="11",
            party="Democratic",
        ),
        office=MemberOffice(
            official_salary=174000.0,
            leadership_roles=["Speaker Emerita"],
            committee_assignments=["Appropriations"],
        ),
        financials=DossierFinancials(
            disclosure_years=[2022, 2023],
            business_interests=["Example Holdings", "Example Partners"],
        ),
        exposure=DossierExposure(
            federal_award_exposure=[{"row": 1}],
            recipient_candidates=[{"row": 1}, {"row": 2}],
        ),
        evidence_sources=[
            EvidenceSource(source_type="profile", source_name="Official biography")
        ],
    )

    summary = render_member_dossier_summary(dossier)

    assert "- chamber: House" in summary
    assert "- state: CA" in summary
    assert "- district: 11" in summary
    assert "- party: Democratic" in summary
    assert "- official salary: 174000.0" in summary
    assert "- leadership roles: Speaker Emerita" in summary
    assert "- committee assignments: Appropriations" in summary
    assert "- disclosure years: 2022, 2023" in summary
    assert "- disclosed business interests: 2" in summary
    assert "- federal award exposure rows: 1" in summary
    assert "- recipient candidate rows: 2" in summary
    assert "- evidence sources: 1" in summary


def test_restricted_language_absent():
    dossier = create_empty_member_dossier("nancy-pelosi", "Nancy Pelosi")
    summary = render_member_dossier_summary(dossier).lower()
    restricted_terms = [
        "cor" + "ruption",
        "self-" + "dealing",
        "insider trading " + "confirmed",
        "conflict " + "confirmed",
        "mis" + "conduct",
        "sus" + "picious",
    ]

    for term in restricted_terms:
        assert term not in summary
