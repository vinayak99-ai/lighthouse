import pytest

from ..data.entities import DOMAINS
from ..tools.query_engine import ToolInputError, pivot_by_entity, run_grouped_time_series


def test_grouped_time_series_by_entity_two_stage_aggregation():
    """Regression guard for the aggregation bug found while spot-checking
    sample charts: a table can carry a hidden dimension (issuer,chain) --
    rows sharing the same (date, issuer) must be SUMmed first, and only
    then averaged/summed across the days inside one bucket."""
    result = run_grouped_time_series(
        table="stablecoin_supply",
        entity_col="issuer",
        entity_allowed=DOMAINS["stablecoins"]["entities"],
        entities=["USDT"],
        value_col="supply_usd",
        aggregate="AVG",
        start_date="2026-08-01",
        end_date="2026-08-07",
        granularity="day",
    )
    assert len(result["rows"]) == 7
    for row in result["rows"]:
        assert row["entity"] == "USDT"
        # A single issuer's total across all its chains should be well above
        # any single chain's contribution -- catches an accidental single-chain
        # regression as much as an accidental cross-issuer summation.
        assert row["value"] > 1_000_000_000


def test_grouped_time_series_total_has_no_entity_dimension():
    result = run_grouped_time_series(
        table="stablecoin_supply",
        entity_col="issuer",
        entity_allowed=DOMAINS["stablecoins"]["entities"],
        value_col="supply_usd",
        aggregate="AVG",
        start_date="2026-08-01",
        end_date="2026-08-07",
        group_by_entity=False,
    )
    assert len(result["rows"]) == 7
    assert all("entity" not in row or row["entity"] is None for row in result["rows"])


def test_unknown_entity_raises_tool_input_error():
    with pytest.raises(ToolInputError):
        run_grouped_time_series(
            table="stablecoin_supply",
            entity_col="issuer",
            entity_allowed=DOMAINS["stablecoins"]["entities"],
            entities=["NOTACOIN"],
            value_col="supply_usd",
        )


def test_unknown_extra_filter_value_raises_tool_input_error():
    with pytest.raises(ToolInputError):
        run_grouped_time_series(
            table="stablecoin_supply",
            entity_col="issuer",
            entity_allowed=DOMAINS["stablecoins"]["entities"],
            value_col="supply_usd",
            extra_filters=[{"col": "chain", "allowed": DOMAINS["stablecoins"]["chains"], "values": ["Nowhere"]}],
        )


def test_pivot_by_entity_reshapes_rows():
    rows = [
        {"bucket": "2026-08-01", "entity": "USDT", "value": 10},
        {"bucket": "2026-08-01", "entity": "USDC", "value": 20},
        {"bucket": "2026-08-02", "entity": "USDT", "value": 11},
    ]
    pivoted = pivot_by_entity(rows)
    assert pivoted["series"] == ["USDT", "USDC"]
    assert pivoted["data"] == [
        {"x": "2026-08-01", "USDT": 10, "USDC": 20},
        {"x": "2026-08-02", "USDT": 11},
    ]


def test_pivot_by_entity_uses_fallback_name_when_no_entity_dimension():
    rows = [{"bucket": "2026-08-01", "value": 42}]
    pivoted = pivot_by_entity(rows, "Total supply")
    assert pivoted["series"] == ["Total supply"]
    assert pivoted["data"] == [{"x": "2026-08-01", "Total supply": 42}]


class _FakeAdapter:
    """Stands in for a real data-source adapter (SQLite or Snowflake) so
    the result-sanity wiring (data/result_sanity.py, invoked from inside
    run_grouped_time_series) can be exercised without depending on what
    the seeded stub data happens to contain."""

    def __init__(self, rows):
        self._rows = rows

    def bucket_expr(self, granularity):
        return "date"

    def run_query(self, sql, params):
        return self._rows


def _patched_source(monkeypatch, rows):
    monkeypatch.setattr("server_py.tools.query_engine.get_data_source", lambda: _FakeAdapter(rows))


def test_result_sanity_warning_surfaces_through_run_grouped_time_series(monkeypatch):
    _patched_source(monkeypatch, [{"bucket": "2026-08-01", "value": 1.0}])  # stale vs. end_date below
    result = run_grouped_time_series(
        table="stablecoin_supply",
        entity_col="issuer",
        entity_allowed=DOMAINS["stablecoins"]["entities"],
        value_col="supply_usd",
        end_date="2026-08-22",
    )
    assert result["warning"] is not None
    assert "days before the requested end date" in result["warning"]


def test_healthy_result_has_no_warning_through_run_grouped_time_series(monkeypatch):
    _patched_source(monkeypatch, [{"bucket": "2026-08-21", "value": 1.0}, {"bucket": "2026-08-22", "value": 2.0}])
    result = run_grouped_time_series(
        table="stablecoin_supply",
        entity_col="issuer",
        entity_allowed=DOMAINS["stablecoins"]["entities"],
        value_col="supply_usd",
        end_date="2026-08-22",
    )
    assert result["warning"] is None


def test_runaway_row_count_raises_tool_input_error(monkeypatch):
    from ..data.result_sanity import ROW_COUNT_LIMIT

    _patched_source(monkeypatch, [{"bucket": "2026-08-22", "value": 1.0}] * (ROW_COUNT_LIMIT + 1))
    with pytest.raises(ToolInputError, match="row safety cap"):
        run_grouped_time_series(
            table="stablecoin_supply",
            entity_col="issuer",
            entity_allowed=DOMAINS["stablecoins"]["entities"],
            value_col="supply_usd",
            end_date="2026-08-22",
        )
