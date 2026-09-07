"""Registry of tickers available through the (currently mocked) market-data
API integration -- server_py/data/market_data_api.py.

Mirrors data/entities.py's DOMAINS pattern: a fixed, enum-constrained list
so the model can only ever request a real, known ticker -- it never has to
guess or hallucinate raw ticker syntax. The model picks a display name
(the dict key) and the tool resolves it to the `code` your real API will
eventually expect; swapping the mock for a real HTTP client only touches
market_data_api.py, not this registry or the tool schema in tools.py.
"""

from .entities import END_DATE

MARKET_TICKERS = {
    "Nasdaq Composite": {"code": "^IXIC", "base_level": 18000.0, "daily_vol_pct": 1.1},
    "Nasdaq 100": {"code": "^NDX", "base_level": 20500.0, "daily_vol_pct": 1.15},
    "S&P 500": {"code": "^GSPC", "base_level": 5800.0, "daily_vol_pct": 0.9},
    "Dow Jones Industrial Average": {"code": "^DJI", "base_level": 42000.0, "daily_vol_pct": 0.8},
    "Russell 2000": {"code": "^RUT", "base_level": 2200.0, "daily_vol_pct": 1.3},
    "Apple": {"code": "AAPL", "base_level": 225.0, "daily_vol_pct": 1.8},
    "Microsoft": {"code": "MSFT", "base_level": 420.0, "daily_vol_pct": 1.6},
}

TICKER_BY_CODE = {info["code"]: {**info, "name": name} for name, info in MARKET_TICKERS.items()}

# Market data gets its own (longer) history than the on-chain DOMAINS dataset
# -- "last one year" of index data should mean something -- but shares the
# same "today", END_DATE, so every stubbed dataset in the app agrees on the
# current date.
MARKET_DATA_START_DATE = "2024-01-01"
MARKET_DATA_END_DATE = END_DATE
