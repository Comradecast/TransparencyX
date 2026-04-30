import json
import urllib.error
import urllib.request

from transparencyx.spending.usaspending import normalize_award_result, summarize_award_exposure

USASPENDING_AWARD_SEARCH_URL = "https://api.usaspending.gov/api/v2/search/spending_by_award/"
FETCH_TIMEOUT_SECONDS = 5


def _query_recipient_name_from_link(link: dict) -> str:
    if link.get("query_recipient_name"):
        return link["query_recipient_name"]

    recipient_search_text = link.get("payload", {}).get("filters", {}).get("recipient_search_text", [])
    if recipient_search_text:
        return recipient_search_text[0]

    return ""


def _empty_exposure_summary(query_recipient_name: str) -> dict:
    return summarize_award_exposure(query_recipient_name, [])


def fetch_award_exposure(link: dict) -> dict:
    query_recipient_name = _query_recipient_name_from_link(link)
    payload = link.get("payload")
    if not isinstance(payload, dict):
        return _empty_exposure_summary(query_recipient_name)

    request = urllib.request.Request(
        USASPENDING_AWARD_SEARCH_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=FETCH_TIMEOUT_SECONDS) as response:
            response_data = json.loads(response.read().decode("utf-8"))
    except (TimeoutError, urllib.error.URLError, json.JSONDecodeError, OSError):
        return _empty_exposure_summary(query_recipient_name)

    raw_results = response_data.get("results", [])
    if not isinstance(raw_results, list):
        return _empty_exposure_summary(query_recipient_name)

    awards = []
    for raw_result in raw_results:
        if not isinstance(raw_result, dict):
            continue
        raw_award = dict(raw_result)
        raw_award["query_recipient_name"] = query_recipient_name
        awards.append(normalize_award_result(raw_award))

    return summarize_award_exposure(query_recipient_name, awards)
