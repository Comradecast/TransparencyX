CONTRACT_AWARD_TYPE_CODES = ["A", "B", "C", "D"]

AWARD_FIELDS = [
    "Award ID",
    "Recipient Name",
    "Start Date",
    "Award Amount",
    "Awarding Agency",
    "Contract Award Type",
    "Award Type",
]


def build_award_search_payload(recipient_name: str) -> dict:
    return {
        "subawards": False,
        "limit": 10,
        "page": 1,
        "sort": "Award ID",
        "order": "asc",
        "filters": {
            "recipient_search_text": [recipient_name],
            "award_type_codes": CONTRACT_AWARD_TYPE_CODES,
        },
        "fields": AWARD_FIELDS,
    }


def _safe_float(value) -> float | None:
    if value is None or isinstance(value, bool):
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_award_result(raw: dict) -> dict:
    return {
        "query_recipient_name": raw.get("query_recipient_name"),
        "recipient_name": raw.get("Recipient Name"),
        "award_id": raw.get("Award ID"),
        "awarding_agency": raw.get("Awarding Agency"),
        "award_amount": _safe_float(raw.get("Award Amount")),
        "award_date": raw.get("Start Date"),
        "award_type": raw.get("Contract Award Type") or raw.get("Award Type"),
        "signal": "possible_recipient_match",
    }


def summarize_award_exposure(query_recipient_name: str, awards: list[dict]) -> dict:
    numeric_amounts = [
        award["award_amount"]
        for award in awards
        if isinstance(award.get("award_amount"), (int, float)) and not isinstance(award.get("award_amount"), bool)
    ]
    agencies = sorted({
        award["awarding_agency"]
        for award in awards
        if award.get("awarding_agency")
    })
    dates = sorted(
        award["award_date"]
        for award in awards
        if award.get("award_date")
    )

    return {
        "query_recipient_name": query_recipient_name,
        "award_count": len(awards),
        "total_award_amount": float(sum(numeric_amounts)),
        "agencies": agencies,
        "date_min": dates[0] if dates else None,
        "date_max": dates[-1] if dates else None,
        "signal": "federal_award_exposure",
    }
