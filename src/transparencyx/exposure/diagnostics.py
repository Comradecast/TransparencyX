from transparencyx.shape.card import format_money

FORBIDDEN_LANGUAGE = [
    "corruption",
    "self-dealing",
    "insider trading",
    "conflict confirmed",
    "misconduct",
    "suspicious",
]


def _numeric_value(value) -> float:
    if isinstance(value, bool) or value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    return 0.0


def _query_name(exposure: dict) -> str:
    value = exposure.get("query_recipient_name")
    if value is None:
        return ""
    return str(value)


def _query_length_stats(query_names: list[str]) -> dict:
    lengths = [len(query_name) for query_name in query_names]
    if not lengths:
        return {"shortest": 0, "longest": 0, "average": 0.0}

    return {
        "shortest": min(lengths),
        "longest": max(lengths),
        "average": round(sum(lengths) / len(lengths), 1),
    }


def _diagnostic_notes(awards_found: int, queries_with_results: int, queries_without_results: int) -> list[str]:
    notes = []
    if awards_found == 0:
        notes.append("No awards were found for the queried business interests.")
    if queries_without_results > 0 and queries_with_results == 0:
        notes.append("All queried business interests returned zero awards.")
    if queries_with_results > 0:
        notes.append("Some queried business interests returned federal award results.")
    notes.append("Exposure results depend on exact recipient-name search behavior.")
    return notes


def build_exposure_diagnostics(exposures: list[dict]) -> dict:
    query_names = [_query_name(exposure) for exposure in exposures]
    awards_found = sum(int(_numeric_value(exposure.get("award_count"))) for exposure in exposures)
    total_award_amount = sum(_numeric_value(exposure.get("total_award_amount")) for exposure in exposures)
    queries_with_results = sum(1 for exposure in exposures if _numeric_value(exposure.get("award_count")) > 0)
    queries_without_results = sum(1 for exposure in exposures if _numeric_value(exposure.get("award_count")) == 0)
    agencies_found = sorted({
        agency
        for exposure in exposures
        for agency in exposure.get("agencies", [])
        if agency
    })
    no_result_queries = [
        _query_name(exposure)
        for exposure in exposures
        if _numeric_value(exposure.get("award_count")) == 0 and _query_name(exposure)
    ]

    return {
        "business_interests_queried": len(exposures),
        "awards_found": awards_found,
        "total_award_amount": float(total_award_amount),
        "queries_with_results": queries_with_results,
        "queries_without_results": queries_without_results,
        "agencies_found": agencies_found,
        "no_result_queries": no_result_queries,
        "query_length": _query_length_stats(query_names),
        "diagnostic_notes": _diagnostic_notes(awards_found, queries_with_results, queries_without_results),
    }


def render_exposure_diagnostics(exposures: list[dict]) -> str:
    diagnostics = build_exposure_diagnostics(exposures)
    query_length = diagnostics["query_length"]
    lines = [
        "Federal Award Exposure Diagnostics:",
        f"- business interests queried: {diagnostics['business_interests_queried']}",
        f"- awards found: {diagnostics['awards_found']}",
        f"- total award amount: {format_money(diagnostics['total_award_amount'])}",
        f"- queries with results: {diagnostics['queries_with_results']}",
        f"- queries without results: {diagnostics['queries_without_results']}",
        f"- agencies found: {', '.join(diagnostics['agencies_found']) if diagnostics['agencies_found'] else 'None'}",
        f"- shortest query length: {query_length['shortest']}",
        f"- longest query length: {query_length['longest']}",
        f"- average query length: {query_length['average']}",
        "- diagnostic notes:",
    ]

    for note in diagnostics["diagnostic_notes"]:
        lines.append(f"  - {note}")

    if diagnostics["no_result_queries"]:
        lines.append("- sample no-result queries:")
        for query in diagnostics["no_result_queries"][:10]:
            lines.append(f"  - {query}")

    return "\n".join(lines)
