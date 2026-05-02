from transparencyx.dossier.schema import MemberDossier

def validate_dataset_scale_metrics(dossiers: list[MemberDossier]) -> dict:
    total_dossiers = len(dossiers)
    dossiers_with_financials = 0
    dossiers_without_financials = 0
    total_assets = 0
    total_transactions = 0
    total_linked_transactions = 0
    total_unlinked_transactions = 0
    dossiers_with_transaction_count_gt_0 = 0
    dossiers_with_transaction_count_0 = 0

    for dossier in dossiers:
        if dossier.financials.asset_count is None:
            dossiers_without_financials += 1
            continue

        dossiers_with_financials += 1
        total_assets += dossier.financials.asset_count or 0
        
        t_count = dossier.financials.trade_count or 0
        linked = dossier.financials.linked_transaction_count or 0
        unlinked = dossier.financials.unlinked_transaction_count or 0
        ratio = dossier.financials.linked_transaction_coverage_ratio

        if linked + unlinked != t_count:
            raise ValueError(f"Dataset validation failed: Dossier {dossier.identity.member_id} has count mismatch (linked {linked} + unlinked {unlinked} != total {t_count})")

        if t_count > 0:
            dossiers_with_transaction_count_gt_0 += 1
            expected_ratio = linked / t_count
            if ratio is None or abs(expected_ratio - ratio) >= 1e-12:
                raise ValueError(f"Dataset validation failed: Dossier {dossier.identity.member_id} has ratio mismatch (expected {expected_ratio}, got {ratio})")
        else:
            dossiers_with_transaction_count_0 += 1
            if ratio is not None:
                raise ValueError(f"Dataset validation failed: Dossier {dossier.identity.member_id} coverage ratio must be None when transaction count is 0")

        total_transactions += t_count
        total_linked_transactions += linked
        total_unlinked_transactions += unlinked

    return {
        "total_dossiers": total_dossiers,
        "dossiers_with_parsed_financials": dossiers_with_financials,
        "dossiers_without_parsed_financials": dossiers_without_financials,
        "total_assets": total_assets,
        "total_transactions": total_transactions,
        "total_linked_transactions": total_linked_transactions,
        "total_unlinked_transactions": total_unlinked_transactions,
        "dossiers_with_transaction_count_gt_0": dossiers_with_transaction_count_gt_0,
        "dossiers_with_transaction_count_0": dossiers_with_transaction_count_0,
    }
