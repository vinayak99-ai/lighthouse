import pytest

from ..data.market_data_api import fetch_daily_bars
from ..data.market_tickers import MARKET_DATA_END_DATE, MARKET_DATA_START_DATE, MARKET_TICKERS
from ..tools.chart_validator import validate_chart
from ..tools.market_data_query import resample, resample_multi
from ..tools.tools import ToolInputError, run_tool


def test_fetch_daily_bars_covers_only_business_days():
    bars = fetch_daily_bars("^IXIC", "2026-08-17", "2026-08-23")  # Mon..Sun
    dates = [b["date"] for b in bars]
    assert dates == ["2026-08-17", "2026-08-18", "2026-08-19", "2026-08-20", "2026-08-21"]


def test_fetch_daily_bars_unknown_ticker_raises():
    with pytest.raises(ValueError):
        fetch_daily_bars("NOT_A_REAL_TICKER")


def test_fetch_daily_bars_is_date_stable_regardless_of_query_window():
    """A real API returns the same close for a given date no matter what
    date range you ask for -- this stub must too (see market_data_api.py's
    full-history-then-slice design)."""
    full = {b["date"]: b["close"] for b in fetch_daily_bars("^IXIC", MARKET_DATA_START_DATE, MARKET_DATA_END_DATE)}
    narrow = fetch_daily_bars("^IXIC", "2026-06-01", "2026-06-10")
    assert narrow
    assert all(full[b["date"]] == b["close"] for b in narrow)


def test_resample_level_takes_period_end_close():
    bars = [
        {"date": "2026-08-03", "close": 100.0},  # Mon (week of Aug 3)
        {"date": "2026-08-04", "close": 101.0},
        {"date": "2026-08-10", "close": 110.0},  # Mon (week of Aug 10)
    ]
    result = resample(bars, granularity="week", metric="level", series_name="X")
    assert result["series"] == ["X"]
    assert result["data"] == [{"x": "2026-08-03", "X": 101.0}, {"x": "2026-08-10", "X": 110.0}]


def test_resample_return_pct_drops_first_period_and_computes_pct_change():
    bars = [
        {"date": "2026-01-01", "close": 100.0},
        {"date": "2026-02-01", "close": 110.0},
        {"date": "2026-03-01", "close": 99.0},
    ]
    result = resample(bars, granularity="month", metric="return_pct", series_name="X")
    assert result["data"] == [
        {"x": "2026-02-01", "X": 10.0},
        {"x": "2026-03-01", "X": -10.0},
    ]


def test_resample_quarter_buckets_by_calendar_quarter():
    bars = [
        {"date": "2026-01-15", "close": 100.0},
        {"date": "2026-02-15", "close": 105.0},
        {"date": "2026-04-15", "close": 110.0},
    ]
    result = resample(bars, granularity="quarter", metric="level", series_name="X")
    assert result["data"] == [{"x": "2026-01-01", "X": 105.0}, {"x": "2026-04-01", "X": 110.0}]


@pytest.mark.parametrize("ticker", list(MARKET_TICKERS.keys()))
def test_query_market_data_level_for_every_ticker(ticker):
    result = run_tool("query_market_data", {"tickers": [ticker], "metric": "level", "granularity": "month"})
    assert result["row_count"] > 0
    assert result["series"] == [ticker]
    chart = {"chart_type": "line", "title": "t", "series": result["series"], "data": result["data"]}
    assert validate_chart(chart)["valid"]


def test_query_market_data_weekly_return_pairs_with_bar_chart():
    result = run_tool(
        "query_market_data",
        {"tickers": ["Nasdaq Composite"], "metric": "return_pct", "granularity": "week", "start_date": "2026-01-01", "end_date": "2026-08-22"},
    )
    assert result["point_count"] > 0
    chart = {"chart_type": "bar", "title": "t", "series": result["series"], "data": result["data"]}
    assert validate_chart(chart)["valid"]


def test_query_market_data_defaults_granularity_by_metric():
    level = run_tool("query_market_data", {"tickers": ["Apple"], "metric": "level"})
    assert len(level["data"]) > 100  # default day granularity over the full stub history
    ret = run_tool("query_market_data", {"tickers": ["Apple"], "metric": "return_pct"})
    assert len(ret["data"]) < 40  # default month granularity


def test_query_market_data_unknown_ticker_raises_tool_input_error():
    with pytest.raises(ToolInputError):
        run_tool("query_market_data", {"tickers": ["Not A Real Index"]})


def test_query_market_data_empty_tickers_raises_tool_input_error():
    with pytest.raises(ToolInputError):
        run_tool("query_market_data", {"tickers": []})


def test_query_market_data_partially_unknown_tickers_raises_tool_input_error():
    with pytest.raises(ToolInputError, match="Not A Real Index"):
        run_tool("query_market_data", {"tickers": ["Apple", "Not A Real Index"]})


def test_resample_multi_merges_two_tickers_aligned_by_period():
    bars_a = [{"date": "2026-08-03", "close": 100.0}, {"date": "2026-08-10", "close": 110.0}]
    bars_b = [{"date": "2026-08-03", "close": 50.0}, {"date": "2026-08-10", "close": 45.0}]
    result = resample_multi({"A": bars_a, "B": bars_b}, granularity="week", metric="level")
    assert result["series"] == ["A", "B"]
    assert result["data"] == [
        {"x": "2026-08-03", "A": 100.0, "B": 50.0},
        {"x": "2026-08-10", "A": 110.0, "B": 45.0},
    ]


def test_query_market_data_compares_multiple_tickers_on_one_chart():
    result = run_tool(
        "query_market_data",
        {"tickers": ["Nasdaq Composite", "S&P 500"], "metric": "level", "granularity": "month"},
    )
    assert result["series"] == ["Nasdaq Composite", "S&P 500"]
    assert all("Nasdaq Composite" in row or "S&P 500" in row for row in result["data"])
    chart = {"chart_type": "line", "title": "t", "series": result["series"], "data": result["data"]}
    assert validate_chart(chart)["valid"]
