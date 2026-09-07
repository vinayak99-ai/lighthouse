"""Sanity-checks raw query results before they reach the model -- the
choke point between a data source (SQLite today, Snowflake once it's
connected) returning rows and the tool layer handing them to the LLM as
a tool result. Wired into tools/query_engine.py's run_grouped_time_series,
the single place every data tool's rows pass through regardless of which
adapter served them.

Two different failure modes get two different responses, matching the
rest of this app's "structural problems fail loud, data-quality concerns
get flagged" philosophy:

- A runaway row count -- a forgotten filter, an unexpectedly wide join,
  a query wider than intended -- raises ValueError. query_engine.py turns
  this into a ToolInputError, the same self-correcting path an unknown
  entity name takes: the model sees an actionable message and can retry
  with a coarser granularity or a narrower date range within the same
  turn, rather than the raw rows blowing up its context.
- Null-heavy or stale results are real possibilities in a live warehouse
  (a broken upstream ETL job, a newly-listed entity with a short
  history) that don't mean the query itself was wrong. These don't block
  the result -- they come back as a warning string the tool result
  carries alongside the data (system_prompt.py tells the model to
  mention it), so the model can caveat its answer ("data looks
  incomplete after <date>") instead of presenting a silently degraded
  chart as if it were complete.
"""

from __future__ import annotations

from datetime import date

ROW_COUNT_LIMIT = 5000
NULL_RATIO_WARNING_THRESHOLD = 0.3
STALENESS_WARNING_DAYS = 7


def check_result_sanity(rows: list[dict], *, value_col: str = "value", end_date: str | None = None) -> str | None:
    """Returns a warning string to surface to the model, or None if the
    result looks healthy. Raises ValueError if the result is too large to
    hand to the model at all -- callers should translate that into
    whatever "bad tool input" error their own layer uses."""
    if len(rows) > ROW_COUNT_LIMIT:
        raise ValueError(
            f"Query returned {len(rows)} rows, over the {ROW_COUNT_LIMIT}-row safety cap -- re-query with a "
            "coarser granularity or a narrower date range."
        )

    if not rows:
        return None

    warnings: list[str] = []

    null_count = sum(1 for row in rows if row.get(value_col) is None)
    null_ratio = null_count / len(rows)
    if null_ratio >= NULL_RATIO_WARNING_THRESHOLD:
        warnings.append(
            f"{null_count} of {len(rows)} rows ({null_ratio:.0%}) have no value -- the underlying data may be incomplete."
        )

    dates = [row["bucket"] for row in rows if row.get("bucket")]
    if dates and end_date:
        most_recent = max(dates)
        staleness = (date.fromisoformat(end_date) - date.fromisoformat(most_recent)).days
        if staleness > STALENESS_WARNING_DAYS:
            warnings.append(
                f"Most recent data point is {most_recent}, {staleness} days before the requested end date -- "
                "the underlying table may not be up to date."
            )

    return " ".join(warnings) if warnings else None
