from transparencyx.dossier.builder import build_member_dossier_from_profile
from transparencyx.dossier.render import render_member_dossier_summary


def test_basic_profile_mapping():
    dossier = build_member_dossier_from_profile({
        "member_id": "nancy-pelosi",
        "member_name": "Nancy Pelosi",
        "chamber": "House",
        "state": "CA",
        "district": "11",
        "party": "Democratic",
        "current_status": "Current",
    })

    assert dossier.identity.member_id == "nancy-pelosi"
    assert dossier.identity.full_name == "Nancy Pelosi"
    assert dossier.identity.chamber == "House"
    assert dossier.identity.state == "CA"
    assert dossier.identity.district == "11"
    assert dossier.identity.party == "Democratic"
    assert dossier.identity.current_status == "Current"


def test_slug_fallback_from_member_name():
    dossier = build_member_dossier_from_profile({"member_name": "  Jane Q. Public  "})

    assert dossier.identity.member_id == "jane-q-public"
    assert dossier.identity.full_name == "Jane Q. Public"


def test_unknown_fallback():
    dossier = build_member_dossier_from_profile({})

    assert dossier.identity.member_id == "unknown"
    assert dossier.identity.full_name == "Unknown"


def test_office_mapping():
    dossier = build_member_dossier_from_profile({
        "member_name": "Nancy Pelosi",
        "official_salary": 174000.0,
        "leadership_roles": ["Speaker Emerita"],
        "committee_assignments": ["Appropriations"],
        "office_start": "1987-06-02",
        "office_end": None,
    })

    assert dossier.office.official_salary == 174000.0
    assert dossier.office.leadership_roles == ["Speaker Emerita"]
    assert dossier.office.committee_assignments == ["Appropriations"]
    assert dossier.office.office_start == "1987-06-02"
    assert dossier.office.office_end is None


def test_financial_shape_mapping():
    dossier = build_member_dossier_from_profile({
        "member_name": "Nancy Pelosi",
        "financial_shape": {
            "asset_count": 5,
            "asset_value_min": 1000.0,
            "asset_value_max": 5000.0,
        },
        "income_shape": {
            "income_min": 10.0,
            "income_max": 100.0,
        },
        "trade_count": 2,
        "liability_count": 1,
    })

    assert dossier.financials.asset_count == 5
    assert dossier.financials.asset_value_min == 1000.0
    assert dossier.financials.asset_value_max == 5000.0
    assert dossier.financials.income_min == 10.0
    assert dossier.financials.income_max == 100.0
    assert dossier.financials.trade_count == 2
    assert dossier.financials.liability_count == 1


def test_shape_export_summary_mapping():
    dossier = build_member_dossier_from_profile({
        "member_name": "Nancy Pelosi",
        "shape_export": {
            "summary": {
                "asset_count": 3,
                "asset_value_min": 100.0,
                "asset_value_max": 200.0,
                "income_min": 1.0,
                "income_max": 2.0,
            },
        },
    })

    assert dossier.financials.asset_count == 3
    assert dossier.financials.asset_value_min == 100.0
    assert dossier.financials.asset_value_max == 200.0
    assert dossier.financials.income_min == 1.0
    assert dossier.financials.income_max == 2.0


def test_disclosure_year_single_int_to_list():
    dossier = build_member_dossier_from_profile({
        "member_name": "Nancy Pelosi",
        "disclosure_year": 2023,
    })

    assert dossier.financials.disclosure_years == [2023]


def test_business_interests_direct_list():
    dossier = build_member_dossier_from_profile({
        "member_name": "Nancy Pelosi",
        "business_interests": ["Example Holdings", "Example Partners"],
    })

    assert dossier.financials.business_interests == [
        "Example Holdings",
        "Example Partners",
    ]


def test_business_interests_derived_from_federal_award_exposure():
    dossier = build_member_dossier_from_profile({
        "member_name": "Nancy Pelosi",
        "federal_award_exposure": [
            {"original_query_name": "Example Holdings"},
            {"cleaned_query_name": "Example Partners"},
            {"original_query_name": "Example Holdings"},
        ],
    })

    assert dossier.financials.business_interests == [
        "Example Holdings",
        "Example Partners",
    ]


def test_exposure_counted_true_only_when_award_count_positive():
    empty = build_member_dossier_from_profile({
        "member_name": "Nancy Pelosi",
        "federal_award_exposure": [{"award_count": 0}, {"award_count": None}],
    })
    populated = build_member_dossier_from_profile({
        "member_name": "Nancy Pelosi",
        "federal_award_exposure": [{"award_count": 0}, {"award_count": 2}],
    })

    assert empty.exposure.exposure_counted is False
    assert populated.exposure.exposure_counted is True


def test_recipient_candidates_mapping():
    direct = build_member_dossier_from_profile({
        "member_name": "Nancy Pelosi",
        "recipient_candidates": [{"recipient": "A"}],
    })
    audit = build_member_dossier_from_profile({
        "member_name": "Nancy Pelosi",
        "recipient_candidate_audit": [{"recipient": "B"}],
    })

    assert direct.exposure.recipient_candidates == [{"recipient": "A"}]
    assert audit.exposure.recipient_candidates == [{"recipient": "B"}]


def test_evidence_source_from_source_pdf_source_path_source_url():
    dossier = build_member_dossier_from_profile({
        "member_name": "Nancy Pelosi",
        "source_pdf": "data/raw/house/sample.pdf",
        "source_path": "data/raw/house/other.pdf",
        "disclosure_path": "data/raw/house/local.pdf",
        "source_url": "https://example.test/disclosure.pdf",
    })

    assert [source.source_name for source in dossier.evidence_sources] == [
        "sample.pdf",
        "other.pdf",
        "local.pdf",
        "disclosure.pdf",
    ]
    assert [source.source_url for source in dossier.evidence_sources] == [
        None,
        None,
        None,
        "https://example.test/disclosure.pdf",
    ]
    assert all(
        source.source_type == "financial_disclosure_pdf"
        for source in dossier.evidence_sources
    )


def test_fail_closed_missing_and_malformed_fields():
    dossier = build_member_dossier_from_profile({
        "member_name": "",
        "member_id": "",
        "leadership_roles": "Speaker",
        "committee_assignments": [1, None],
        "disclosure_years": [2023, "2024", True],
        "asset_count": "5",
        "asset_value_min": "100",
        "trade_count": True,
        "business_interests": [1, None],
        "federal_award_exposure": "bad",
        "recipient_candidates": "bad",
        "source_pdf": "",
    })

    assert dossier.identity.member_id == "unknown"
    assert dossier.identity.full_name == "Unknown"
    assert dossier.office.leadership_roles == []
    assert dossier.office.committee_assignments == []
    assert dossier.financials.disclosure_years == [2023]
    assert dossier.financials.asset_count is None
    assert dossier.financials.asset_value_min is None
    assert dossier.financials.trade_count is None
    assert dossier.financials.business_interests == []
    assert dossier.exposure.federal_award_exposure == []
    assert dossier.exposure.recipient_candidates == []
    assert dossier.evidence_sources == []


def test_forbidden_language_absent():
    dossier = build_member_dossier_from_profile({
        "member_name": "Nancy Pelosi",
        "federal_award_exposure": [{"award_count": 1}],
    })
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
