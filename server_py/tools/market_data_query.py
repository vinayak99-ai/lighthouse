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

resample_multi() merges more than one ticker's bars into a single wide
table (one column per ticker, aligned by period) -- the same shape
tools/query_engine.py's pivot_by_entity() produces for the on-chain
tools, so a chart comparing several tickers is built the same way a
chart comparing several protocols is.
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


def _period_values(bars: list[dict], *, granularity: str, metric: str) -> dict[str, float]:
    """`bars` must be ascending by date (fetch_daily_bars already returns
    them that way). Returns {period_key: value} for one ticker."""
    period_end_close: dict[str, float] = {}
    order: list[str] = []
    for bar in bars:
        key = _bucket_key(bar["date"], granularity)
        if key not in period_end_close:
            order.append(key)
        period_end_close[key] = bar["close"]  # last write per period wins -- bars are ascending

    if metric != "return_pct":
        return dict(period_end_close)

    values: dict[str, float] = {}
    prev = None
    for key in order:
        close = period_end_close[key]
        if prev is not None:
            values[key] = round((close - prev) / prev * 100, 2)
        prev = close
    return values


def resample_multi(bars_by_ticker: dict[str, list[dict]], *, granularity: str, metric: str) -> dict:
    """`bars_by_ticker`: {ticker display name: ascending daily bars}, one
    entry per ticker the caller asked for (one is the common case, but any
    number works identically). Merges each ticker's resampled series into
    one wide table keyed by period, so render_chart/chart_validator see the
    same { data, series } shape whether the question was about one ticker
    or several."""
    per_ticker_values = {name: _period_values(bars, granularity=granularity, metric=metric) for name, bars in bars_by_ticker.items()}

    ordered_keys: list[str] = []
    seen = set()
    for values in per_ticker_values.values():
        for key in values:
            if key not in seen:
                seen.add(key)
                ordered_keys.append(key)
    ordered_keys.sort()

    series = list(bars_by_ticker.keys())
    data = []
    for key in ordered_keys:
        row: dict = {"x": key}
        for name in series:
            if key in per_ticker_values[name]:
                row[name] = per_ticker_values[name][key]
        data.append(row)

    return {"data": data, "series": series}


def resample(bars: list[dict], *, granularity: str, metric: str, series_name: str) -> dict:
    """Single-ticker convenience wrapper around resample_multi()."""
    return resample_multi({series_name: bars}, granularity=granularity, metric=metric)
