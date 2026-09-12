import pytest

from ..tools.tools import HANDLERS, TOOL_DEFINITIONS, ToolInputError, is_data_tool, run_tool


def test_tool_definitions_cover_all_handlers_plus_render_only_tools():
    names = {d["name"] for d in TOOL_DEFINITIONS}
    assert names == set(HANDLERS) | {"render_chart", "render_diagram"}


def test_is_data_tool():
    assert is_data_tool("query_stablecoin_supply") is True
    assert is_data_tool("render_chart") is False
    assert is_data_tool("render_diagram") is False
    assert is_data_tool("not_a_real_tool") is False


def test_run_tool_unknown_name_raises():
    with pytest.raises(ToolInputError):
        run_tool("not_a_real_tool", {})


@pytest.mark.parametrize(
    "name,args",
    [
        ("query_stablecoin_supply", {"group_by": "total", "start_date": "2026-08-01", "end_date": "2026-08-07"}),
        ("query_defi_tvl", {"group_by": "total", "start_date": "2026-08-01", "end_date": "2026-08-07"}),
        ("query_perpetuals", {"metric": "volume", "start_date": "2026-08-01", "end_date": "2026-08-07"}),
        ("query_prediction_markets", {"group_by": "total", "start_date": "2026-08-01", "end_date": "2026-08-07"}),
        ("query_rwa", {"group_by": "total", "start_date": "2026-08-01", "end_date": "2026-08-07"}),
        ("query_protocol_revenue", {"metric": "revenue", "start_date": "2026-08-01", "end_date": "2026-08-07"}),
        ("query_chain_activity", {"metric": "transactions", "start_date": "2026-08-01", "end_date": "2026-08-07"}),
        ("query_staking", {"metric": "staked_eth", "start_date": "2026-08-01", "end_date": "2026-08-07"}),
        ("query_nft_volume", {"metric": "volume", "start_date": "2026-08-01", "end_date": "2026-08-07"}),
        ("query_x402_agentic_payments", {"metric": "volume", "start_date": "2026-08-01", "end_date": "2026-08-07"}),
    ],
)
def test_every_data_tool_returns_shape(name, args):
    result = run_tool(name, args)
    assert result["row_count"] > 0
    assert result["point_count"] > 0
    assert isinstance(result["series"], list) and result["series"]
    assert isinstance(result["data"], list) and result["data"]
    assert all("x" in row for row in result["data"])


def test_query_prediction_markets_group_by_category():
    result = run_tool(
        "query_prediction_markets",
        {"group_by": "category", "start_date": "2026-08-01", "end_date": "2026-08-07"},
    )
    from ..data.entities import DOMAINS

    assert set(result["series"]).issubset(set(DOMAINS["prediction_markets"]["categories"]))


def test_run_tool_defaults_missing_args_to_empty_dict():
    result = run_tool("query_stablecoin_supply", None)
    assert result["row_count"] > 0
