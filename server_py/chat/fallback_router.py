"""Direct port of server/src/chat/fallbackRouter.js -- keep the two in sync.

Deterministic, keyword-based router used only when no LLM client is
configured, so the app is fully demoable without a live model. It picks
one of the same 10 backend tools a real model would pick, runs it, and
shapes the result into a render_chart-style spec using the same rules the
system prompt gives the model. Configure a real LLM provider (see
chat/orchestrator.py) and the orchestrator takes over transparently -- the
HTTP contract is identical either way.
"""

from __future__ import annotations

import re
from datetime import date, timedelta

from ..data.entities import DOMAINS, END_DATE, START_DATE
from ..tools.tools import run_tool

ROUTES = [
    {
        "tool": "query_stablecoin_supply",
        "keywords": ["stablecoin", "usdt", "usdc", "dai", "fdusd", "pyusd", "usde", "tether", "circle supply"],
        "entity_field": "issuers",
        "entity_list": DOMAINS["stablecoins"]["entities"],
        "default_args": {"group_by": "issuer"},
        "unit": "usd",
        "label": "stablecoin supply",
    },
    {
        "tool": "query_defi_tvl",
        "keywords": ["tvl", "total value locked", "defi", "aave", "lido", "eigenlayer", "uniswap", "makerdao", "maker", "curve"],
        "entity_field": "protocols",
        "entity_list": DOMAINS["defi_tvl"]["entities"],
        "default_args": {"group_by": "protocol"},
        "unit": "usd",
        "label": "DeFi TVL",
    },
    {
        "tool": "query_perpetuals",
        "keywords": ["perp", "perpetual", "open interest", "hyperliquid", "dydx", "gmx", "bybit", "futures"],
        "entity_field": "exchanges",
        "entity_list": DOMAINS["perpetuals"]["entities"],
        "default_args": {"group_by": "exchange", "metric": "volume"},
        "metric_keywords": {"open_interest": ["open interest", "oi"], "volume": ["volume", "trading"]},
        "unit": "usd",
        "label": "perpetuals",
    },
    {
        "tool": "query_prediction_markets",
        "keywords": ["prediction market", "polymarket", "kalshi", "manifold"],
        "entity_field": "platforms",
        "entity_list": DOMAINS["prediction_markets"]["entities"],
        "default_args": {"group_by": "platform"},
        "unit": "usd",
        "label": "prediction market volume",
    },
    {
        "tool": "query_rwa",
        "keywords": ["rwa", "real world asset", "tokenized treasur", "blackrock", "ondo", "franklin templeton", "superstate", "hashnote"],
        "entity_field": "issuers",
        "entity_list": DOMAINS["rwa"]["entities"],
        "default_args": {"group_by": "issuer"},
        "unit": "usd",
        "label": "tokenized RWA value",
    },
    {
        "tool": "query_protocol_revenue",
        "keywords": ["revenue", "protocol fees", "protocol revenue"],
        "entity_field": "protocols",
        "entity_list": DOMAINS["protocol_revenue"]["entities"],
        "default_args": {"group_by": "protocol", "metric": "revenue"},
        "metric_keywords": {"revenue": ["revenue"], "fees": ["fees", "fee"]},
        "unit": "usd",
        "label": "protocol revenue",
    },
    {
        "tool": "query_chain_activity",
        "keywords": ["active address", "chain activity", "onchain activity", "on-chain activity"],
        "entity_field": "chains",
        "entity_list": DOMAINS["chain_activity"]["entities"],
        "default_args": {"group_by": "chain", "metric": "active_addresses"},
        "metric_keywords": {"active_addresses": ["active address", "wallet"], "transactions": ["transaction", "tx count", "txn"]},
        "unit": "count",
        "label": "chain activity",
    },
    {
        "tool": "query_staking",
        "keywords": ["staking", "staked eth", "apr", "rocket pool"],
        "entity_field": "providers",
        "entity_list": DOMAINS["staking"]["entities"],
        "default_args": {"group_by": "provider", "metric": "staked_eth"},
        "metric_keywords": {"apr_pct": ["apr", "yield"], "staked_eth": ["staked eth", "staking"]},
        "unit": "count",
        "label": "staking",
    },
    {
        "tool": "query_nft_volume",
        "keywords": ["nft", "blur", "opensea", "magic eden"],
        "entity_field": "marketplaces",
        "entity_list": DOMAINS["nft"]["entities"],
        "default_args": {"group_by": "marketplace", "metric": "volume"},
        "metric_keywords": {"volume": ["volume"], "sales_count": ["sales", "sale count"]},
        "unit": "usd",
        "label": "NFT volume",
    },
    {
        "tool": "query_x402_agentic_payments",
        "keywords": ["x402", "agentic payment", "agent payment", "ai agent payment", "agent-to-agent"],
        "entity_field": "facilitators",
        "entity_list": DOMAINS["x402_agentic_payments"]["entities"],
        "default_args": {"group_by": "facilitator", "metric": "volume"},
        "metric_keywords": {"volume": ["volume"], "tx_count": ["transaction", "tx count"]},
        "unit": "usd",
        "label": "x402 agentic payments",
    },
]


def _count_keyword_matches(text: str, keywords: list[str]) -> int:
    return sum(1 for kw in keywords if kw in text)


def _extract_entities(text: str, entity_list: list[str]) -> list[str]:
    return [e for e in entity_list if e.lower() in text]


def _parse_date_range(text: str) -> dict:
    m = re.search(r"last (\d+)\s*days?", text)
    if m:
        return {"days": int(m.group(1))}
    if re.search(r"last week", text):
        return {"days": 7}
    if re.search(r"last month", text):
        return {"days": 30}
    if re.search(r"last quarter|last 90", text):
        return {"days": 90}
    if re.search(r"year to date|ytd|this year|all time|since inception|since january", text):
        return {"since_start": True}
    return {"days": 90}


def _add_days(date_str: str, delta: int) -> str:
    return (date.fromisoformat(date_str) + timedelta(days=delta)).isoformat()


def _format_value(v: float, unit: str) -> str:
    if unit == "percent":
        return f"{v:.2f}%"
    if unit == "count":
        return f"{v / 1e6:.2f}M" if v >= 1e6 else f"{v:,.0f}"
    if v >= 1e9:
        return f"${v / 1e9:.2f}B"
    if v >= 1e6:
        return f"${v / 1e6:.2f}M"
    return f"${v:,.0f}"


def _build_insight(series: list[str], data: list[dict], unit: str) -> str:
    if not data:
        return "No data points matched this query."
    first, last = data[0], data[-1]
    top_series = series[0]
    top_last = float("-inf")
    for s in series:
        v = last.get(s) or 0
        if v > top_last:
            top_last = v
            top_series = s
    first_val = first.get(top_series) or 0
    pct = ((last[top_series] - first_val) / first_val * 100) if first_val else 0.0
    direction = "up" if pct >= 0 else "down"
    return f"{top_series} leads at {_format_value(top_last, unit)}, {direction} {abs(pct):.1f}% over the period."


def route_offline(user_text: str) -> dict:
    text = user_text.lower()
    # Keyword matches are domain-specific and take priority over entity-name
    # matches alone -- e.g. "Solana" and "Base" are valid entities in both
    # chain_activity and protocol_revenue, so a phrase like "active addresses
    # on Solana vs Base" must not fall to whichever of those two happens to
    # sit first in ROUTES just because its entity list also contains them.
    # Among keyword matches, the route with the MOST matching keywords wins,
    # not just the first one found in list order -- an entity name that
    # doubles as another domain's keyword (e.g. "Lido" is a defi_tvl keyword
    # AND a staking entity) must not out-rank a question that's clearly about
    # staking ("staked eth", "rocket pool") just because it comes first.
    keyword_counts = [
        {"route": r, "count": _count_keyword_matches(text, r["keywords"])} for r in ROUTES
    ]
    keyword_counts = [m for m in keyword_counts if m["count"] > 0]
    best_keyword_match = max(keyword_counts, key=lambda m: m["count"], default=None)
    route = best_keyword_match["route"] if best_keyword_match else next(
        (r for r in ROUTES if _extract_entities(text, r["entity_list"])), None
    )

    if route is None:
        return {
            "reply": (
                "I couldn't map that to a data domain I have stubbed. Try asking about stablecoins, DeFi TVL, "
                "perpetuals, prediction markets, RWA, protocol revenue, chain activity, staking, NFT volume, or "
                "x402 agentic payments."
            ),
            "chart": None,
        }

    args = dict(route["default_args"])
    entities = _extract_entities(text, route["entity_list"])
    if entities:
        args[route["entity_field"]] = entities

    metric_keywords = route.get("metric_keywords")
    if metric_keywords:
        for metric, kws in metric_keywords.items():
            if any(kw in text for kw in kws):
                args["metric"] = metric
                break

    date_range = _parse_date_range(text)
    since_start = date_range.get("since_start", False)
    days = date_range.get("days")
    args["start_date"] = START_DATE if since_start else _add_days(END_DATE, -(days - 1))
    args["end_date"] = END_DATE
    span = 9999 if since_start else days
    wants_share = bool(re.search(r"share|breakdown|composition|percent of total", text))
    # Stacked bars read as a barcode past ~16 categories, so bucket much
    # coarser than a line/area chart would for the same date range.
    if wants_share:
        args["granularity"] = "month" if span > 100 else "week" if span > 14 else "day"
    else:
        args["granularity"] = "month" if span > 270 else "week" if span > 120 else "day"

    result = run_tool(route["tool"], args)
    # "current supply of X" wants a KPI tile, not a trend chart -- but only
    # when the phrasing is actually asking for a snapshot, not a history
    # ("current trend" / "since January" still means "show me the chart").
    wants_stat = bool(
        re.search(r"\b(current|latest|today|right now|what is|what's|how much is)\b", text)
    ) and not bool(re.search(r"\b(trend|over time|chart|history|since|compare|vs\.?|versus)\b", text))
    if wants_share and len(result["series"]) > 1:
        chart_type = "stacked_bar"
    elif wants_stat:
        chart_type = "stat"
    elif len(result["series"]) > 4:
        chart_type = "small_multiples"  # too many overlapping lines to read as one chart -- facet instead
    else:
        chart_type = "line"

    entity_note = ", ".join(entities) if entities else "all tracked entities"
    label = route["label"]
    title = f"{label[0].upper()}{label[1:]}" + (f" — {', '.join(entities)}" if entities else "")
    chart = {
        "chart_type": chart_type,
        "title": title,
        "subtitle": f"{entity_note} · {args['start_date']} to {args['end_date']}",
        "y_unit": route["unit"],
        "series": result["series"],
        "data": result["data"],
        "insight": _build_insight(result["series"], result["data"], route["unit"]),
    }

    return {"reply": chart["insight"], "chart": chart}
