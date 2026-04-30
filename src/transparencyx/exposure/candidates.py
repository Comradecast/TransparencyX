import csv
import io
import json
import re
import socket
import string
import urllib.error
import urllib.request

from transparencyx.shape.card import format_money

USASPENDING_RECIPIENT_AUTOCOMPLETE_URL = "https://api.usaspending.gov/api/v2/autocomplete/recipient/"
CANDIDATE_FETCH_TIMEOUT_SECONDS = 5
LEGAL_SUFFIX_PATTERN = re.compile(
    r"(?i)(^|[\s,])("
    r"L\.L\.C|LLC|"
    r"L\.L\.P|LLP|"
    r"L\.P|LP|"
    r"INC|CORP|CORPORATION|CO|COMPANY|LTD|LIMITED"
    r")$"
)
PUNCTUATION_TRANSLATION = str.maketrans({character: " " for character in string.punctuation})


def _collapse_whitespace(value: str) -> str:
    return " ".join(value.split())


def _strip_trailing_punctuation(value: str) -> str:
    return value.rstrip(" .,")


def build_recipient_candidate_query(cleaned_query: str) -> str:
    candidate_query = _strip_trailing_punctuation(_collapse_whitespace(cleaned_query or ""))
    if not candidate_query:
        return ""

    while True:
        match = LEGAL_SUFFIX_PATTERN.search(candidate_query)
        if not match:
            break
        candidate_query = _strip_trailing_punctuation(candidate_query[:match.start()])
        if not candidate_query:
            return ""

    return candidate_query


def normalize_candidate_name(value: str) -> str:
    normalized = (value or "").strip().lower()
    if not normalized:
        return ""

    normalized = normalized.translate(PUNCTUATION_TRANSLATION)
    return _collapse_whitespace(normalized)


def candidate_name_tokens(value: str) -> list[str]:
    return [token for token in normalize_candidate_name(value).split() if token]


def build_candidate_signals(original_query: str, candidate_query: str, recipient_name: str) -> dict:
    normalized_original = normalize_candidate_name(original_query)
    normalized_candidate_query = normalize_candidate_name(candidate_query)
    normalized_recipient = normalize_candidate_name(recipient_name)
    candidate_tokens = sorted(set(candidate_name_tokens(candidate_query)))
    recipient_tokens = set(candidate_name_tokens(recipient_name))
    shared_tokens = sorted(token for token in candidate_tokens if token in recipient_tokens)
    token_overlap_total = len(candidate_tokens)
    token_overlap_count = len(shared_tokens)

    return {
        "normalized_original": normalized_original,
        "normalized_candidate_query": normalized_candidate_query,
        "normalized_recipient": normalized_recipient,
        "substring_match": bool(
            normalized_candidate_query
            and normalized_candidate_query in normalized_recipient
        ),
        "normalized_name_match": bool(
            normalized_candidate_query
            and normalized_candidate_query == normalized_recipient
        ),
        "token_overlap_count": token_overlap_count,
        "token_overlap_total": token_overlap_total,
        "token_overlap_ratio": token_overlap_count / token_overlap_total if token_overlap_total else 0.0,
        "shared_tokens": shared_tokens,
    }


def _safe_int(value) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_float(value) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _recipient_candidate_payload(candidate_query: str, limit: int) -> dict:
    return {
        "search_text": candidate_query,
        "limit": limit,
    }


def fetch_recipient_candidates(candidate_query: str, limit: int = 5) -> list[dict]:
    if not candidate_query:
        return []

    request = urllib.request.Request(
        USASPENDING_RECIPIENT_AUTOCOMPLETE_URL,
        data=json.dumps(_recipient_candidate_payload(candidate_query, limit)).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=CANDIDATE_FETCH_TIMEOUT_SECONDS) as response:
            response_data = json.loads(response.read().decode("utf-8"))
    except (TimeoutError, socket.timeout, urllib.error.URLError, json.JSONDecodeError, OSError):
        return []

    raw_results = response_data.get("results", [])
    if not isinstance(raw_results, list):
        return []

    return [raw_result for raw_result in raw_results[:limit] if isinstance(raw_result, dict)]


def _candidate_recipient_name(raw_candidate: dict) -> str:
    value = raw_candidate.get("recipient_name") or raw_candidate.get("name")
    if value is None:
        return ""
    return str(value)


def _candidate_recipient_id(raw_candidate: dict) -> str | None:
    value = raw_candidate.get("recipient_id") or raw_candidate.get("recipient_hash") or raw_candidate.get("id")
    if value is None:
        return None
    return str(value)


def build_recipient_candidate_audit(exposures: list[dict], max_candidates_per_query: int = 5) -> list[dict]:
    candidate_rows = []

    for exposure in exposures:
        original_query = str(exposure.get("query_recipient_name") or "")
        candidate_query = build_recipient_candidate_query(original_query)
        if not candidate_query:
            continue

        raw_candidates = fetch_recipient_candidates(candidate_query, max_candidates_per_query)
        for raw_candidate in raw_candidates[:max_candidates_per_query]:
            recipient_name = _candidate_recipient_name(raw_candidate)
            candidate_rows.append({
                "original_query": original_query,
                "candidate_query": candidate_query,
                "recipient_name": recipient_name,
                "recipient_id": _candidate_recipient_id(raw_candidate),
                "award_count": _safe_int(raw_candidate.get("award_count")),
                "total_award_amount": _safe_float(raw_candidate.get("total_award_amount")),
                "match_status": "candidate_review_only",
                "exposure_counted": False,
                "candidate_signals": build_candidate_signals(original_query, candidate_query, recipient_name),
            })

    return candidate_rows


def render_recipient_candidate_audit(candidates: list[dict]) -> str:
    lines = [
        "Recipient Candidate Audit:",
        f"- candidate rows: {len(candidates)}",
        "- exposure counted: No",
        "- exact exposure results unchanged: Yes",
    ]

    if not candidates:
        lines.append("- status: No recipient candidates found")
        return "\n".join(lines)

    lines.extend([
        "",
        "original_query | candidate_query | recipient_name | award_count | total_award_amount | status | substring_match | token_overlap",
    ])

    for candidate in candidates:
        amount = candidate.get("total_award_amount")
        signals = candidate.get("candidate_signals") or {}
        token_overlap_count = signals.get("token_overlap_count", 0)
        token_overlap_total = signals.get("token_overlap_total", 0)
        row = [
            str(candidate.get("original_query") or ""),
            str(candidate.get("candidate_query") or ""),
            str(candidate.get("recipient_name") or ""),
            "" if candidate.get("award_count") is None else str(candidate["award_count"]),
            "Unknown" if amount is None else format_money(amount),
            str(candidate.get("match_status") or "candidate_review_only"),
            "Yes" if signals.get("substring_match") else "No",
            f"{token_overlap_count}/{token_overlap_total}",
        ]
        lines.append(" | ".join(row))

    return "\n".join(lines)


def render_recipient_candidate_audit_csv(candidates: list[dict]) -> str:
    output = io.StringIO()
    columns = [
        "original_query",
        "candidate_query",
        "recipient_name",
        "recipient_id",
        "award_count",
        "total_award_amount",
        "status",
        "substring_match",
        "token_overlap",
        "exposure_counted",
    ]
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(columns)

    for candidate in candidates:
        signals = candidate.get("candidate_signals") or {}
        token_overlap_count = signals.get("token_overlap_count", 0)
        token_overlap_total = signals.get("token_overlap_total", 0)
        writer.writerow([
            candidate.get("original_query") or "",
            candidate.get("candidate_query") or "",
            candidate.get("recipient_name") or "",
            candidate.get("recipient_id") or "",
            "" if candidate.get("award_count") is None else candidate["award_count"],
            "" if candidate.get("total_award_amount") is None else candidate["total_award_amount"],
            candidate.get("match_status") or "candidate_review_only",
            "Yes" if signals.get("substring_match") else "No",
            f"{token_overlap_count}/{token_overlap_total}",
            False,
        ])

    return output.getvalue()
