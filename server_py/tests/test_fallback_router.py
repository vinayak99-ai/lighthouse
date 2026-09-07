from ..chat.fallback_router import route_offline
from ..tools.chart_validator import validate_chart


def _assert_valid_chart(result):
    """Regression guard, mirroring fallbackRouter.test.js: whatever chart
    shape/type this deterministic router picks must always pass the same
    validator a real model's render_chart call is checked against."""
    assert result["chart"] is not None
    validity = validate_chart(result["chart"])
    assert validity["valid"], validity["issues"]


def test_routes_stablecoin_question_to_stablecoin_tool():
    result = route_offline("Chart USDT vs USDC supply over the last 90 days")
    assert set(result["chart"]["series"]) == {"USDT", "USDC"}
    _assert_valid_chart(result)


def test_unmatched_question_returns_no_chart():
    result = route_offline("What's the weather like today?")
    assert result["chart"] is None
    assert "couldn't map" in result["reply"]


def test_ambiguous_entity_name_prefers_domain_with_most_keyword_matches():
    """'Lido' is both a defi_tvl keyword and a staking entity -- a question
    clearly about staking must route to staking, not defi_tvl, just because
    defi_tvl's ROUTES entry comes first."""
    result = route_offline("How much ETH is staked with Lido and Rocket Pool?")
    assert set(result["chart"]["series"]).issubset({"Lido", "Rocket Pool"})
    _assert_valid_chart(result)


def test_shared_entity_names_use_keyword_match_not_first_route():
    """'Solana' and 'Base' appear in both chain_activity and
    protocol_revenue's entity lists -- the keyword phrase must decide."""
    result = route_offline("Active addresses on Solana vs Base this year")
    _assert_valid_chart(result)
    assert result["chart"]["y_unit"] == "count"


def test_current_value_question_renders_stat_tile():
    result = route_offline("What is the current staked ETH for Coinbase?")
    assert result["chart"]["chart_type"] == "stat"
    _assert_valid_chart(result)


def test_trend_question_does_not_render_stat_tile():
    result = route_offline("Show the staked ETH trend for Coinbase since January")
    assert result["chart"]["chart_type"] != "stat"
    _assert_valid_chart(result)


def test_share_breakdown_question_renders_stacked_bar():
    result = route_offline("Show DeFi TVL breakdown by protocol over the last 6 months")
    assert result["chart"]["chart_type"] == "stacked_bar"
    _assert_valid_chart(result)


def test_many_series_falls_back_to_small_multiples():
    result = route_offline("Compare TVL across all DeFi protocols over the last 90 days")
    if len(result["chart"]["series"]) > 4:
        assert result["chart"]["chart_type"] == "small_multiples"
    _assert_valid_chart(result)
