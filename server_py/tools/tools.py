"""Direct port of server/src/tools/tools.js -- keep the two in sync.

Defines the 10 typed, read-only data tools plus render_chart as tool-calling
schemas (Bedrock Converse / OpenAI / Anthropic function-calling all accept
this same JSON Schema shape for a tool's input), the handler each data tool
name dispatches to, and the two entry points the orchestrator uses:
is_data_tool() (to tell a data fetch apart from the final render_chart call)
and run_tool() (execute a tool call by name and return its JSON result).
"""

from ..data.entities import DOMAINS, END_DATE, START_DATE
from ..data.market_data_api import fetch_daily_bars
from ..data.market_tickers import MARKET_DATA_START_DATE, MARKET_TICKERS
from .market_data_query import resample_multi
from .query_engine import ToolInputError, pivot_by_entity, run_grouped_time_series

DATE_PROPS = {
    "start_date": {
        "type": "string",
        "description": f"Inclusive start date, YYYY-MM-DD. Data available from {START_DATE}.",
    },
    "end_date": {
        "type": "string",
        "description": f"Inclusive end date, YYYY-MM-DD. Data available through {END_DATE}.",
    },
    "granularity": {
        "type": "string",
        "enum": ["day", "week", "month"],
        "description": "Time bucket size. Use week/month for ranges longer than ~90 days to keep series readable.",
    },
}


def _time_series_result(
    *,
    table,
    entity_col,
    entity_allowed,
    entities=None,
    extra_filters=None,
    value_col,
    aggregate="SUM",
    args,
    fallback_series_name=None,
) -> dict:
    result = run_grouped_time_series(
        table=table,
        entity_col=entity_col,
        entity_allowed=entity_allowed,
        entities=entities,
        extra_filters=extra_filters,
        value_col=value_col,
        aggregate=aggregate,
        start_date=args.get("start_date"),
        end_date=args.get("end_date"),
        granularity=args.get("granularity") or "day",
        group_by_entity=args.get("group_by") != "total",
    )
    rows = result["rows"]
    pivoted = pivot_by_entity(rows, fallback_series_name)
    output = {
        "row_count": len(rows),
        "point_count": len(pivoted["data"]),
        "series": pivoted["series"],
        "data": pivoted["data"],
    }
    if result.get("warning"):
        output["data_quality_warning"] = result["warning"]
    return output


TOOL_DEFINITIONS = [
    {
        "name": "query_stablecoin_supply",
        "description": (
            "Time series of stablecoin circulating supply (USD) by issuer and/or chain. Issuers: "
            + ", ".join(DOMAINS["stablecoins"]["entities"])
            + ". Chains: "
            + ", ".join(DOMAINS["stablecoins"]["chains"])
            + "."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "issuers": {
                    "type": "array",
                    "items": {"type": "string", "enum": DOMAINS["stablecoins"]["entities"]},
                    "description": "Filter to these issuers. Omit for all.",
                },
                "chains": {
                    "type": "array",
                    "items": {"type": "string", "enum": DOMAINS["stablecoins"]["chains"]},
                    "description": "Filter to these chains. Omit for all.",
                },
                "group_by": {"type": "string", "enum": ["issuer", "total"], "description": "Split series by issuer, or return a single combined total."},
                **DATE_PROPS,
            },
        },
    },
    {
        "name": "query_defi_tvl",
        "description": (
            "Time series of DeFi protocol Total Value Locked (USD). Protocols: "
            + ", ".join(DOMAINS["defi_tvl"]["entities"])
            + ". Chains: "
            + ", ".join(DOMAINS["defi_tvl"]["chains"])
            + "."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "protocols": {"type": "array", "items": {"type": "string", "enum": DOMAINS["defi_tvl"]["entities"]}},
                "chains": {"type": "array", "items": {"type": "string", "enum": DOMAINS["defi_tvl"]["chains"]}},
                "group_by": {"type": "string", "enum": ["protocol", "total"]},
                **DATE_PROPS,
            },
        },
    },
    {
        "name": "query_perpetuals",
        "description": (
            "Time series of perpetual futures open interest or trading volume (USD) by exchange. Exchanges: "
            + ", ".join(DOMAINS["perpetuals"]["entities"])
            + "."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "exchanges": {"type": "array", "items": {"type": "string", "enum": DOMAINS["perpetuals"]["entities"]}},
                "metric": {"type": "string", "enum": ["open_interest", "volume"], "description": "Which measure to return."},
                "group_by": {"type": "string", "enum": ["exchange", "total"]},
                **DATE_PROPS,
            },
            "required": ["metric"],
        },
    },
    {
        "name": "query_prediction_markets",
        "description": (
            "Time series of prediction market trading volume (USD) by platform and/or category. Platforms: "
            + ", ".join(DOMAINS["prediction_markets"]["entities"])
            + ". Categories: "
            + ", ".join(DOMAINS["prediction_markets"]["categories"])
            + "."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "platforms": {"type": "array", "items": {"type": "string", "enum": DOMAINS["prediction_markets"]["entities"]}},
                "categories": {"type": "array", "items": {"type": "string", "enum": DOMAINS["prediction_markets"]["categories"]}},
                "group_by": {"type": "string", "enum": ["platform", "category", "total"]},
                **DATE_PROPS,
            },
        },
    },
    {
        "name": "query_rwa",
        "description": (
            "Time series of tokenized real-world asset (RWA) value (USD) by issuer. Issuers: "
            + ", ".join(DOMAINS["rwa"]["entities"])
            + ". Asset types: "
            + ", ".join(DOMAINS["rwa"]["asset_types"])
            + "."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "issuers": {"type": "array", "items": {"type": "string", "enum": DOMAINS["rwa"]["entities"]}},
                "asset_types": {"type": "array", "items": {"type": "string", "enum": DOMAINS["rwa"]["asset_types"]}},
                "group_by": {"type": "string", "enum": ["issuer", "asset_type", "total"]},
                **DATE_PROPS,
            },
        },
    },
    {
        "name": "query_protocol_revenue",
        "description": (
            "Time series of blockchain protocol revenue or fees (USD). Protocols: "
            + ", ".join(DOMAINS["protocol_revenue"]["entities"])
            + "."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "protocols": {"type": "array", "items": {"type": "string", "enum": DOMAINS["protocol_revenue"]["entities"]}},
                "metric": {"type": "string", "enum": ["revenue", "fees"]},
                "group_by": {"type": "string", "enum": ["protocol", "total"]},
                **DATE_PROPS,
            },
            "required": ["metric"],
        },
    },
    {
        "name": "query_chain_activity",
        "description": (
            "Time series of daily active addresses or transaction counts by chain. Chains: "
            + ", ".join(DOMAINS["chain_activity"]["entities"])
            + "."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "chains": {"type": "array", "items": {"type": "string", "enum": DOMAINS["chain_activity"]["entities"]}},
                "metric": {"type": "string", "enum": ["active_addresses", "transactions"]},
                "group_by": {"type": "string", "enum": ["chain", "total"]},
                **DATE_PROPS,
            },
            "required": ["metric"],
        },
    },
    {
        "name": "query_staking",
        "description": (
            "Time series of staked ETH or staking APR by provider. Providers: "
            + ", ".join(DOMAINS["staking"]["entities"])
            + "."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "providers": {"type": "array", "items": {"type": "string", "enum": DOMAINS["staking"]["entities"]}},
                "metric": {"type": "string", "enum": ["staked_eth", "apr_pct"]},
                "group_by": {"type": "string", "enum": ["provider", "total"]},
                **DATE_PROPS,
            },
            "required": ["metric"],
        },
    },
    {
        "name": "query_nft_volume",
        "description": (
            "Time series of NFT marketplace trading volume (USD) or sales count. Marketplaces: "
            + ", ".join(DOMAINS["nft"]["entities"])
            + "."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "marketplaces": {"type": "array", "items": {"type": "string", "enum": DOMAINS["nft"]["entities"]}},
                "metric": {"type": "string", "enum": ["volume", "sales_count"]},
                "group_by": {"type": "string", "enum": ["marketplace", "total"]},
                **DATE_PROPS,
            },
            "required": ["metric"],
        },
    },
    {
        "name": "query_x402_agentic_payments",
        "description": (
            "Time series of x402 agentic payment volume (USD) or transaction count — machine-to-machine payments "
            "made by AI agents. Facilitators: "
            + ", ".join(DOMAINS["x402_agentic_payments"]["entities"])
            + ". Agent networks: "
            + ", ".join(DOMAINS["x402_agentic_payments"]["agent_networks"])
            + "."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "facilitators": {"type": "array", "items": {"type": "string", "enum": DOMAINS["x402_agentic_payments"]["entities"]}},
                "agent_networks": {"type": "array", "items": {"type": "string", "enum": DOMAINS["x402_agentic_payments"]["agent_networks"]}},
                "metric": {"type": "string", "enum": ["volume", "tx_count"]},
                "group_by": {"type": "string", "enum": ["facilitator", "agent_network", "total"]},
                **DATE_PROPS,
            },
            "required": ["metric"],
        },
    },
    {
        "name": "query_market_data",
        "description": (
            "Time series of traditional market index/equity price data, via a separate market-data API "
            "integration -- NOT one of the on-chain domains above. Available tickers: "
            + ", ".join(MARKET_TICKERS.keys())
            + f". Data available from {MARKET_DATA_START_DATE} to {END_DATE}. Pass more than one entry in "
            "`tickers` to compare them on one chart -- one series per ticker, aligned by period, same as "
            "requesting multiple entities from any other tool. Use metric='level' for a price trend (pairs "
            "with chart_type 'line'/'area' for one ticker, 'line' to compare several). Use metric='return_pct' "
            "for period-over-period percent change -- e.g. \"weekly/monthly/quarterly performance\" or "
            "\"return\" -- which pairs with chart_type 'bar' for one ticker, 'line' to compare several; pick "
            "granularity to match the period the user asked about."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "tickers": {
                    "type": "array",
                    "items": {"type": "string", "enum": list(MARKET_TICKERS.keys())},
                    "description": "One or more ticker display names. Pass more than one to compare them on the same chart.",
                },
                "metric": {
                    "type": "string",
                    "enum": ["level", "return_pct"],
                    "description": "'level' for the raw price series; 'return_pct' for percent change vs. the prior period.",
                },
                "start_date": {"type": "string", "description": f"Inclusive start date, YYYY-MM-DD. Data available from {MARKET_DATA_START_DATE}."},
                "end_date": {"type": "string", "description": f"Inclusive end date, YYYY-MM-DD. Data available through {END_DATE}."},
                "granularity": {
                    "type": "string",
                    "enum": ["day", "week", "month", "quarter"],
                    "description": "Time bucket size. 'quarter' is only meaningful here, not on the on-chain tools.",
                },
            },
            "required": ["tickers"],
        },
    },
    {
        "name": "render_chart",
        "description": (
            "Render the final chart for the user. Call this once you have the data you need. type='line'/'area' for "
            "trend over time, 'bar' for magnitude comparison, 'stacked_bar' for part-to-whole over time, 'stat' for a "
            "single current value (a KPI, not a trend), 'small_multiples' for many entities' trend shapes at once, "
            "'scatter' for comparing two numeric metrics across entities (correlation, risk/return) -- add a `z` "
            "value per point to render it as a bubble chart sized by a third metric. 'treemap' for a market-share/"
            "composition SNAPSHOT sized by one metric -- 'who dominates this category right now' -- use 'stacked_bar' "
            "instead when the user wants to see composition change over time. "
            "`series` lists the entity keys in the order they should be colored (max 8, fold extras into 'Other') "
            "for every chart_type except 'scatter' (point-group names instead, usually just one) and 'treemap' "
            "(exactly one entry -- the metric each box is sized by; put entity names in `data`'s `x` field instead, "
            "like 'bar'). "
            "`data` is an array of rows shaped { x: <date or category label>, <series key>: <number>, ... } for every "
            "chart_type except 'scatter', ascending by x -- 'stat' and 'small_multiples' use this same shape too, "
            "they just render it differently. 'scatter' rows are shaped { label: <entity name>, x: <number>, "
            "y: <number>, z: <number, optional, bubble size>, group: <one of `series`, optional if `series` has one "
            "entry> } instead -- x/y are two different metrics for the same entity, not a date and a value, so build "
            "them yourself from prior tool results rather than passing one straight through."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "chart_type": {"type": "string", "enum": ["line", "area", "bar", "stacked_bar", "stat", "small_multiples", "scatter", "treemap"]},
                "title": {"type": "string"},
                "subtitle": {"type": "string", "description": "One short sentence of context (units, date range)."},
                "y_unit": {"type": "string", "enum": ["usd", "count", "percent"], "description": "How to format axis ticks and tooltip values (the y-axis metric, for 'scatter')."},
                "x_unit": {"type": "string", "enum": ["usd", "count", "percent"], "description": "'scatter' only: how to format the x-axis metric."},
                "x_axis_label": {"type": "string", "description": "'scatter' only: name of the x-axis metric, e.g. 'TVL (USD)'."},
                "y_axis_label": {"type": "string", "description": "'scatter' only: name of the y-axis metric."},
                "z_axis_label": {"type": "string", "description": "'scatter' only: name of the bubble-size metric, if any point has a `z` value."},
                "series": {"type": "array", "items": {"type": "string"}, "maxItems": 8},
                "data": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Rows shaped { x, <series key>: number, ... }, ascending by x -- or, for 'scatter', { label, x, y, z?, group? }.",
                },
                "insight": {"type": "string", "description": "One or two sentence takeaway a sharp analyst would say about this chart."},
            },
            "required": ["chart_type", "title", "series", "data"],
        },
    },
    {
        "name": "render_diagram",
        "description": (
            "Render a CONCEPTUAL/STRUCTURAL diagram -- how something works, or how entities relate -- as opposed "
            "to render_chart, which visualizes quantitative data. Use this for 'explain how X works' or 'show "
            "the flow of Y' questions, never for a metric over time or across entities (that's always "
            "render_chart). Only diagram_type 'flowchart' is available right now: nodes laid out top-to-bottom "
            "by dependency order, connected by directional edges. You supply structure only (node ids, labels, "
            "which node points to which) -- never coordinates or raw SVG; the backend lays it out deterministically."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "diagram_type": {"type": "string", "enum": ["flowchart"]},
                "title": {"type": "string"},
                "nodes": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string", "description": "Short, unique identifier referenced by edges -- not shown to the user."},
                            "label": {"type": "string", "description": "Text shown in the box. Keep it short (under ~30 characters) so it fits."},
                        },
                        "required": ["id", "label"],
                    },
                    "description": "Up to 12 nodes.",
                },
                "edges": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "from": {"type": "string", "description": "A node id."},
                            "to": {"type": "string", "description": "A node id."},
                            "label": {"type": "string", "description": "Optional short label on the connector, e.g. 'settles via'."},
                        },
                        "required": ["from", "to"],
                    },
                },
            },
            "required": ["diagram_type", "title", "nodes"],
        },
    },
]


def _query_stablecoin_supply(args: dict) -> dict:
    return _time_series_result(
        table="stablecoin_supply",
        entity_col="issuer",
        entity_allowed=DOMAINS["stablecoins"]["entities"],
        entities=args.get("issuers"),
        extra_filters=[{"col": "chain", "allowed": DOMAINS["stablecoins"]["chains"], "values": args.get("chains")}],
        value_col="supply_usd",
        aggregate="AVG",  # supply is a stock (point-in-time level) -- summing across bucketed days would inflate it
        args=args,
        fallback_series_name="Total supply",
    )


def _query_defi_tvl(args: dict) -> dict:
    return _time_series_result(
        table="defi_tvl",
        entity_col="protocol",
        entity_allowed=DOMAINS["defi_tvl"]["entities"],
        entities=args.get("protocols"),
        extra_filters=[{"col": "chain", "allowed": DOMAINS["defi_tvl"]["chains"], "values": args.get("chains")}],
        value_col="tvl_usd",
        aggregate="AVG",  # TVL is a stock, not a flow -- average the bucket, don't sum it
        args=args,
        fallback_series_name="Total TVL",
    )


def _query_perpetuals(args: dict) -> dict:
    metric = args.get("metric")
    return _time_series_result(
        table="perp_markets",
        entity_col="exchange",
        entity_allowed=DOMAINS["perpetuals"]["entities"],
        entities=args.get("exchanges"),
        value_col="open_interest_usd" if metric == "open_interest" else "volume_usd",
        aggregate="AVG" if metric == "open_interest" else "SUM",  # open interest is a stock; volume is a flow
        args=args,
        fallback_series_name="Open interest" if metric == "open_interest" else "Volume",
    )


def _query_prediction_markets(args: dict) -> dict:
    group_by_category = args.get("group_by") == "category"
    return _time_series_result(
        table="prediction_markets",
        entity_col="category" if group_by_category else "platform",
        entity_allowed=DOMAINS["prediction_markets"]["categories"] if group_by_category else DOMAINS["prediction_markets"]["entities"],
        entities=args.get("categories") if group_by_category else args.get("platforms"),
        extra_filters=(
            [{"col": "platform", "allowed": DOMAINS["prediction_markets"]["entities"], "values": args.get("platforms")}]
            if group_by_category
            else [{"col": "category", "allowed": DOMAINS["prediction_markets"]["categories"], "values": args.get("categories")}]
        ),
        value_col="volume_usd",
        args=args,
        fallback_series_name="Total volume",
    )


def _query_rwa(args: dict) -> dict:
    group_by_asset_type = args.get("group_by") == "asset_type"
    return _time_series_result(
        table="rwa_value",
        entity_col="asset_type" if group_by_asset_type else "issuer",
        entity_allowed=DOMAINS["rwa"]["asset_types"] if group_by_asset_type else DOMAINS["rwa"]["entities"],
        entities=args.get("asset_types") if group_by_asset_type else args.get("issuers"),
        extra_filters=(
            [{"col": "issuer", "allowed": DOMAINS["rwa"]["entities"], "values": args.get("issuers")}]
            if group_by_asset_type
            else [{"col": "asset_type", "allowed": DOMAINS["rwa"]["asset_types"], "values": args.get("asset_types")}]
        ),
        value_col="value_usd",
        aggregate="AVG",  # tokenized value is a stock -- average the bucket, don't sum it
        args=args,
        fallback_series_name="Total value",
    )


def _query_protocol_revenue(args: dict) -> dict:
    metric = args.get("metric")
    return _time_series_result(
        table="protocol_revenue",
        entity_col="protocol",
        entity_allowed=DOMAINS["protocol_revenue"]["entities"],
        entities=args.get("protocols"),
        value_col="revenue_usd" if metric == "revenue" else "fees_usd",
        args=args,
        fallback_series_name="Revenue" if metric == "revenue" else "Fees",
    )


def _query_chain_activity(args: dict) -> dict:
    metric = args.get("metric")
    return _time_series_result(
        table="chain_activity",
        entity_col="chain",
        entity_allowed=DOMAINS["chain_activity"]["entities"],
        entities=args.get("chains"),
        value_col="active_addresses" if metric == "active_addresses" else "transactions",
        # active addresses is a daily headcount (stock-like, summing double-counts repeat users);
        # transactions is a genuine flow, safe to sum across a bucket.
        aggregate="AVG" if metric == "active_addresses" else "SUM",
        args=args,
        fallback_series_name="Active addresses" if metric == "active_addresses" else "Transactions",
    )


def _query_staking(args: dict) -> dict:
    metric = args.get("metric")
    return _time_series_result(
        table="staking",
        entity_col="provider",
        entity_allowed=DOMAINS["staking"]["entities"],
        entities=args.get("providers"),
        value_col="apr_pct" if metric == "apr_pct" else "staked_eth",
        aggregate="AVG",  # both staked ETH and APR are stocks/rates -- never summed across a bucket
        args=args,
        fallback_series_name="APR" if metric == "apr_pct" else "Staked ETH",
    )


def _query_nft_volume(args: dict) -> dict:
    metric = args.get("metric")
    return _time_series_result(
        table="nft_volume",
        entity_col="marketplace",
        entity_allowed=DOMAINS["nft"]["entities"],
        entities=args.get("marketplaces"),
        value_col="sales_count" if metric == "sales_count" else "volume_usd",
        args=args,
        fallback_series_name="Sales" if metric == "sales_count" else "Volume",
    )


def _query_x402_agentic_payments(args: dict) -> dict:
    group_by_agent_network = args.get("group_by") == "agent_network"
    metric = args.get("metric")
    return _time_series_result(
        table="x402_payments",
        entity_col="agent_network" if group_by_agent_network else "facilitator",
        entity_allowed=DOMAINS["x402_agentic_payments"]["agent_networks"] if group_by_agent_network else DOMAINS["x402_agentic_payments"]["entities"],
        entities=args.get("agent_networks") if group_by_agent_network else args.get("facilitators"),
        extra_filters=(
            [{"col": "facilitator", "allowed": DOMAINS["x402_agentic_payments"]["entities"], "values": args.get("facilitators")}]
            if group_by_agent_network
            else [{"col": "agent_network", "allowed": DOMAINS["x402_agentic_payments"]["agent_networks"], "values": args.get("agent_networks")}]
        ),
        value_col="tx_count" if metric == "tx_count" else "volume_usd",
        args=args,
        fallback_series_name="Transactions" if metric == "tx_count" else "Volume",
    )


def _query_market_data(args: dict) -> dict:
    ticker_names = args.get("tickers") or []
    if not ticker_names:
        raise ToolInputError(f"`tickers` must include at least one of: {', '.join(MARKET_TICKERS.keys())}")
    unknown = [t for t in ticker_names if t not in MARKET_TICKERS]
    if unknown:
        raise ToolInputError(f"Unknown ticker(s): {', '.join(unknown)}. Valid values: {', '.join(MARKET_TICKERS.keys())}")

    metric = args.get("metric", "level")
    granularity = args.get("granularity") or ("month" if metric == "return_pct" else "day")

    bars_by_ticker = {}
    total_rows = 0
    for name in ticker_names:
        bars = fetch_daily_bars(MARKET_TICKERS[name]["code"], args.get("start_date"), args.get("end_date"))
        if not bars:
            raise ToolInputError(f"No market data for {name} in that date range.")
        bars_by_ticker[name] = bars
        total_rows += len(bars)

    result = resample_multi(bars_by_ticker, granularity=granularity, metric=metric)
    return {
        "row_count": total_rows,
        "point_count": len(result["data"]),
        "series": result["series"],
        "data": result["data"],
    }


HANDLERS = {
    "query_stablecoin_supply": _query_stablecoin_supply,
    "query_defi_tvl": _query_defi_tvl,
    "query_perpetuals": _query_perpetuals,
    "query_prediction_markets": _query_prediction_markets,
    "query_rwa": _query_rwa,
    "query_protocol_revenue": _query_protocol_revenue,
    "query_chain_activity": _query_chain_activity,
    "query_staking": _query_staking,
    "query_nft_volume": _query_nft_volume,
    "query_x402_agentic_payments": _query_x402_agentic_payments,
    "query_market_data": _query_market_data,
}


def is_data_tool(name: str) -> bool:
    return name != "render_chart" and name in HANDLERS


def run_tool(name: str, args: dict | None) -> dict:
    handler = HANDLERS.get(name)
    if not handler:
        raise ToolInputError(f"Unknown tool: {name}")
    return handler(args or {})
