"""Mock external market-data API client -- stands in for a real HTTP
integration (a vendor's REST API keyed by ticker symbol). Swap
`fetch_daily_bars` for a real `requests`/`httpx` call against your actual
provider and nothing else in the app needs to change: the tool layer
(tools.py) and the resampling logic (tools/market_data_query.py) only
depend on this function's signature and its return shape -- a list of
{date, open, high, low, close, volume} dicts, ascending by date.

Data is generated on the fly with a seeded random walk (business days
only -- markets don't trade weekends) rather than stored anywhere, to
mimic what a real "give me a ticker and a date range, get bars back" API
call feels like. The full history is always generated first and then
sliced to the requested window (rather than generating only the requested
range) so a given date's price is stable no matter what date range it's
queried within -- the same guarantee a real API gives you, and the same
reason seed.py's stub data is generated once and stored rather than
regenerated per query.
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from functools import lru_cache

from .market_tickers import MARKET_DATA_END_DATE, MARKET_DATA_START_DATE, TICKER_BY_CODE


def _business_days(start_date: str, end_date: str) -> list[str]:
    start, end = date.fromisoformat(start_date), date.fromisoformat(end_date)
    days = []
    d = start
    while d <= end:
        if d.weekday() < 5:  # Mon-Fri
            days.append(d.isoformat())
        d += timedelta(days=1)
    return days


@lru_cache(maxsize=None)
def _full_history(ticker_code: str) -> tuple[dict, ...]:
    info = TICKER_BY_CODE[ticker_code]
    rng = random.Random(ticker_code)
    level = info["base_level"]
    vol = info["daily_vol_pct"] / 100
    bars = []
    for day in _business_days(MARKET_DATA_START_DATE, MARKET_DATA_END_DATE):
        level = max(level * (1 + (rng.random() - 0.49) * vol), info["base_level"] * 0.2)
        open_px = level * (1 + (rng.random() - 0.5) * vol * 0.3)
        high = max(open_px, level) * (1 + rng.random() * vol * 0.4)
        low = min(open_px, level) * (1 - rng.random() * vol * 0.4)
        volume = int(rng.uniform(0.7, 1.3) * 5_000_000)
        bars.append(
            {
                "date": day,
                "open": round(open_px, 2),
                "high": round(high, 2),
                "low": round(low, 2),
                "close": round(level, 2),
                "volume": volume,
            }
        )
    return tuple(bars)


def fetch_daily_bars(ticker_code: str, start_date: str | None = None, end_date: str | None = None) -> list[dict]:
    """Mimics calling a real market-data API: given a ticker CODE (display
    -> code resolution happens in the tool layer, see tools.py) and an
    optional date range, returns daily OHLCV bars. Raises ValueError for an
    unknown ticker, the way a real API would 404."""
    if ticker_code not in TICKER_BY_CODE:
        raise ValueError(f"Unknown ticker: {ticker_code}")

    start_date = start_date or MARKET_DATA_START_DATE
    end_date = end_date or MARKET_DATA_END_DATE
    return [bar for bar in _full_history(ticker_code) if start_date <= bar["date"] <= end_date]
