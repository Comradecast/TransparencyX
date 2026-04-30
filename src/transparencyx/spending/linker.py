import re

from transparencyx.spending.usaspending import build_award_search_payload

DISCLOSURE_CODE_PATTERN = re.compile(r"\[(AB|OL|ST|RP|BA|MF|OP|PS)\]")
TRAILING_METADATA_TOKENS = {"SP", "JT", "DC", "P", "S"}


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


def clean_recipient_query_name(asset_name: str) -> str:
    cleaned = " ".join(asset_name.split())
    cleaned = DISCLOSURE_CODE_PATTERN.sub("", cleaned)
    cleaned = " ".join(cleaned.split())

    if cleaned.endswith("S (partial)"):
        cleaned = cleaned[:-len("S (partial)")].strip()

    parts = cleaned.split()
    while parts and parts[-1].rstrip(".,") in TRAILING_METADATA_TOKENS:
        parts.pop()

    cleaned = " ".join(parts).strip()
    while cleaned.endswith(".") or cleaned.endswith(","):
        cleaned = cleaned[:-1].strip()

    return cleaned


def build_exposure_link(disclosed_asset_name: str) -> dict:
    query_recipient_name = clean_recipient_query_name(disclosed_asset_name)
    if not query_recipient_name:
        return {}

    return {
        "disclosed_asset_name": disclosed_asset_name,
        "query_recipient_name": query_recipient_name,
        "signal": "federal_award_exposure",
        "match_type": "exact_query",
        "payload": build_award_search_payload(query_recipient_name),
    }


def link_business_interests_to_award_exposure(asset_rows: list[dict]) -> list[dict]:
    links = []
    for asset_name in extract_business_interest_assets(asset_rows):
        link = build_exposure_link(asset_name)
        if link:
            links.append(link)

    return links
