from transparencyx.spending.usaspending import build_award_search_payload


def extract_business_interest_assets(asset_rows: list[dict]) -> list[str]:
    business_interest_assets = []

    for row in asset_rows:
        if row.get("asset_category") != "business_interest":
            continue

        asset_name = row.get("asset_name")
        if not asset_name:
            continue

        business_interest_assets.append(asset_name)

    return business_interest_assets


def build_exposure_link(query_recipient_name: str) -> dict:
    return {
        "query_recipient_name": query_recipient_name,
        "signal": "federal_award_exposure",
        "match_type": "exact_query",
        "payload": build_award_search_payload(query_recipient_name),
    }


def link_business_interests_to_award_exposure(asset_rows: list[dict]) -> list[dict]:
    return [
        build_exposure_link(asset_name)
        for asset_name in extract_business_interest_assets(asset_rows)
    ]
