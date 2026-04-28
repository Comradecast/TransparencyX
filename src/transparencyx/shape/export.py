from pathlib import Path

from transparencyx.shape.summary import build_financial_shape_summary, summary_to_dict
from transparencyx.shape.trace import build_financial_shape_trace


def build_financial_shape_export(db_path: Path, politician_id: int) -> dict:
    """
    Builds a deterministic export object combining the financial shape
    summary and its source-row traceability data.

    No aggregation logic is performed here; this is purely a composition
    of build_financial_shape_summary and build_financial_shape_trace.
    """
    summary = build_financial_shape_summary(db_path, politician_id)
    summary_dict = summary_to_dict(summary)
    trace_dict = build_financial_shape_trace(db_path, politician_id)

    return {
        "politician_id": politician_id,
        "summary": summary_dict,
        "trace": trace_dict,
    }
