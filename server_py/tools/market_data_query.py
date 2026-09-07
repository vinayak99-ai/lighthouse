"""Resamples daily bars from the market-data API (data/market_data_api.py)
into the same { data: [{x, <series>}], series: [...] } shape every other
tool returns, so render_chart/chart_validator/the frontend need no special
case for this data source. Two metrics:

- "level": each bucket's period-end close (for a price trend line/area).
- "return_pct": % change from the PRIOR bucket's period-end close (for a
  "weekly/monthly/quarterly performance" bar chart) -- the first bucket is
  dropped since it has no prior period to compare against.

Granularity bucketing is done here in Python rather than SQL since this
data isn't in a database -- same idea as query_engine.py's bucket_expr,
just over an in-memory list instead of a SQL GROUP BY.
"""

from __future__ import annotations

from datetime import date, timedelta


def _bucket_key(day: str, granularity: str) -> str:
    d = date.fromisoformat(day)
    if granularity == "week":
        monday = d - timedelta(days=d.weekday())
        return monday.isoformat()
    if granularity == "month":
        return d.replace(day=1).isoformat()
    if granularity == "quarter":
        quarter_start_month = (d.month - 1) // 3 * 3 + 1
        return d.replace(month=quarter_start_month, day=1).isoformat()
    return day


def resample(bars: list[dict], *, granularity: str, metric: str, series_name: str) -> dict:
    """`bars` must be ascending by date (fetch_daily_bars already returns
    them that way)."""
    period_end_close: dict[str, float] = {}
    order: list[str] = []
    for bar in bars:
        key = _bucket_key(bar["date"], granularity)
        if key not in period_end_close:
            order.append(key)
        period_end_close[key] = bar["close"]  # last write per period wins -- bars are ascending

    if metric == "return_pct":
        data = []
        prev = None
        for key in order:
            close = period_end_close[key]
            if prev is not None:
                data.append({"x": key, series_name: round((close - prev) / prev * 100, 2)})
            prev = close
    else:
        data = [{"x": key, series_name: period_end_close[key]} for key in order]

    return {"data": data, "series": [series_name]}
