"""Codifies the same chart-design rules the system prompt asks the model to
follow (system_prompt.py) and the dataviz skill's choosing-a-form.md
documents, as an enforced backend check rather than prose the model might
not perfectly follow. Direct port of server/src/tools/chartValidator.js.

Used two ways:
1. The LLM provider (chat/providers/*.py) runs this right after a
   render_chart tool call, BEFORE showing anything to the user. A failure
   never reaches the chat -- it goes back to the model as a corrective tool
   result so it can retry with a fixed chart_type or re-bucketed data, all
   within the same turn. The user only ever sees the corrected result.
2. The offline fallback router (if ported) asserts its own output always
   passes this as a regression guard.
"""

MAX_SERIES = 8
STACKED_BAR_BAR_LIMIT = 16
LINE_OVERLAY_SERIES_LIMIT = 6


def validate_chart(chart: dict | None) -> dict:
    issues: list[str] = []

    if not isinstance(chart, dict):
        return {"valid": False, "issues": ["render_chart received no chart object."]}

    chart_type = chart.get("chart_type")
    series = chart.get("series")
    data = chart.get("data")

    if not isinstance(series, list) or len(series) == 0:
        issues.append("`series` is empty -- there's nothing to render. Include at least one series.")
        return {"valid": False, "issues": issues}  # nothing else is checkable without series

    if not isinstance(data, list) or len(data) == 0:
        issues.append("`data` is empty -- there are no points to plot. Re-check the tool result before calling render_chart.")
        return {"valid": False, "issues": issues}

    if len(series) > MAX_SERIES:
        issues.append(
            f"`series` has {len(series)} entries, over the {MAX_SERIES}-series cap. "
            'Keep the largest ones and fold the rest into "Other".'
        )

    if chart_type == "area" and len(series) > 1:
        issues.append(
            "chart_type 'area' with more than one independent series overlaps into a muddy band "
            "(or misrepresents the entities if stacked). Use 'line' for a multi-entity trend instead."
        )

    if chart_type == "stacked_bar" and len(data) > STACKED_BAR_BAR_LIMIT:
        issues.append(
            f"stacked_bar has {len(data)} bars, which reads as an unreadable barcode past "
            f"~{STACKED_BAR_BAR_LIMIT}. Re-query with a coarser granularity (week or month)."
        )

    if chart_type == "line" and len(series) > LINE_OVERLAY_SERIES_LIMIT:
        issues.append(
            f"A line chart with {len(series)} overlapping series is hard to read past "
            f"~{LINE_OVERLAY_SERIES_LIMIT}. Use chart_type 'small_multiples' instead so each entity "
            "gets its own small chart."
        )

    series_with_no_data = [name for name in series if not any(row.get(name) is not None for row in data)]
    if series_with_no_data:
        issues.append(
            "These series never appear with a value in any data row, so they'd render as empty: "
            f"{', '.join(series_with_no_data)}. Remove them or check the data mapping."
        )

    return {"valid": len(issues) == 0, "issues": issues}
