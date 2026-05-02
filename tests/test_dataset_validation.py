import pytest
from transparencyx.dossier.dataset_validation import validate_dataset_scale_metrics
from transparencyx.dossier.schema import MemberDossier, MemberIdentity, DossierFinancials, MemberOffice, DossierExposure

def _make_dossier(member_id: str, assets: int, transactions: int, linked: int) -> MemberDossier:
    ratio = linked / transactions if transactions > 0 else None
    unlinked = transactions - linked
    
    identity = MemberIdentity(
        member_id=member_id,
        full_name="Test Member",
    )
    financials = DossierFinancials(
        asset_count=assets,
        trade_count=transactions,
        linked_transaction_count=linked,
        unlinked_transaction_count=unlinked,
        linked_transaction_coverage_ratio=ratio,
    )
    return MemberDossier(
        identity=identity,
        office=MemberOffice(),
        financials=financials,
        exposure=DossierExposure(),
        evidence_sources=[]
    )

def test_validate_dataset_scale_metrics_correct():
    d1 = _make_dossier("d1", 10, 7, 1) # like pelosi
    d2 = _make_dossier("d2", 20, 74, 48) # like foxx
    d3 = _make_dossier("d3", 5, 0, 0) # zero case
    
    report = validate_dataset_scale_metrics([d1, d2, d3])
    
    assert report["total_dossiers"] == 3
    assert report["dossiers_with_parsed_financials"] == 3
    assert report["dossiers_without_parsed_financials"] == 0
    assert report["total_assets"] == 35
    assert report["total_transactions"] == 81
    assert report["total_linked_transactions"] == 49
    assert report["total_unlinked_transactions"] == 32
    assert report["dossiers_with_transaction_count_gt_0"] == 2
    assert report["dossiers_with_transaction_count_0"] == 1

def test_validate_dataset_scale_metrics_count_mismatch():
    d1 = _make_dossier("d1", 10, 7, 1)
    # forcefully break unlinked count
    d1.financials.unlinked_transaction_count = 100
    
    with pytest.raises(ValueError, match="has count mismatch"):
        validate_dataset_scale_metrics([d1])

def test_validate_dataset_scale_metrics_ratio_mismatch():
    d1 = _make_dossier("d1", 10, 7, 1)
    # forcefully break ratio
    d1.financials.linked_transaction_coverage_ratio = 0.5
    
    with pytest.raises(ValueError, match="has ratio mismatch"):
        validate_dataset_scale_metrics([d1])

def test_validate_dataset_scale_metrics_zero_case_mismatch():
    d1 = _make_dossier("d1", 10, 0, 0)
    # forcefully break ratio for zero case
    d1.financials.linked_transaction_coverage_ratio = 0.0
    
    with pytest.raises(ValueError, match="coverage ratio must be None when transaction count is 0"):
        validate_dataset_scale_metrics([d1])
