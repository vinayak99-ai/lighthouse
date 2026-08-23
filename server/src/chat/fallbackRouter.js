// Deterministic, keyword-based router used only when ANTHROPIC_API_KEY is not
// configured, so the app is fully demoable without a live model. It picks one
// of the same 10 backend tools a real model would pick, runs it, and shapes
// the result into a render_chart-style spec using the same rules the system
// prompt gives the model. Swap in a real ANTHROPIC_API_KEY and the orchestrator
// takes over transparently -- the frontend contract is identical either way.

import { DOMAINS, START_DATE, END_DATE } from "../data/entities.js";
import { runTool } from "../tools/tools.js";

const ROUTES = [
  {
    tool: "query_stablecoin_supply",
    keywords: ["stablecoin", "usdt", "usdc", "dai", "fdusd", "pyusd", "usde", "tether", "circle supply"],
    entityField: "issuers",
    entityList: DOMAINS.stablecoins.entities,
    defaultArgs: { group_by: "issuer" },
    unit: "usd",
    label: "stablecoin supply",
  },
  {
    tool: "query_defi_tvl",
    keywords: ["tvl", "total value locked", "defi", "aave", "lido", "eigenlayer", "uniswap", "makerdao", "maker", "curve"],
    entityField: "protocols",
    entityList: DOMAINS.defi_tvl.entities,
    defaultArgs: { group_by: "protocol" },
    unit: "usd",
    label: "DeFi TVL",
  },
  {
    tool: "query_perpetuals",
    keywords: ["perp", "perpetual", "open interest", "hyperliquid", "dydx", "gmx", "bybit", "futures"],
    entityField: "exchanges",
    entityList: DOMAINS.perpetuals.entities,
    defaultArgs: { group_by: "exchange", metric: "volume" },
    metricKeywords: { open_interest: ["open interest", "oi"], volume: ["volume", "trading"] },
    unit: "usd",
    label: "perpetuals",
  },
  {
    tool: "query_prediction_markets",
    keywords: ["prediction market", "polymarket", "kalshi", "manifold"],
    entityField: "platforms",
    entityList: DOMAINS.prediction_markets.entities,
    defaultArgs: { group_by: "platform" },
    unit: "usd",
    label: "prediction market volume",
  },
  {
    tool: "query_rwa",
    keywords: ["rwa", "real world asset", "tokenized treasur", "blackrock", "ondo", "franklin templeton", "superstate", "hashnote"],
    entityField: "issuers",
    entityList: DOMAINS.rwa.entities,
    defaultArgs: { group_by: "issuer" },
    unit: "usd",
    label: "tokenized RWA value",
  },
  {
    tool: "query_protocol_revenue",
    keywords: ["revenue", "protocol fees", "protocol revenue"],
    entityField: "protocols",
    entityList: DOMAINS.protocol_revenue.entities,
    defaultArgs: { group_by: "protocol", metric: "revenue" },
    metricKeywords: { revenue: ["revenue"], fees: ["fees", "fee"] },
    unit: "usd",
    label: "protocol revenue",
  },
  {
    tool: "query_chain_activity",
    keywords: ["active address", "chain activity", "onchain activity", "on-chain activity"],
    entityField: "chains",
    entityList: DOMAINS.chain_activity.entities,
    defaultArgs: { group_by: "chain", metric: "active_addresses" },
    metricKeywords: { active_addresses: ["active address", "wallet"], transactions: ["transaction", "tx count", "txn"] },
    unit: "count",
    label: "chain activity",
  },
  {
    tool: "query_staking",
    keywords: ["staking", "staked eth", "apr", "rocket pool"],
    entityField: "providers",
    entityList: DOMAINS.staking.entities,
    defaultArgs: { group_by: "provider", metric: "staked_eth" },
    metricKeywords: { apr_pct: ["apr", "yield"], staked_eth: ["staked eth", "staking"] },
    unit: "count",
    label: "staking",
  },
  {
    tool: "query_nft_volume",
    keywords: ["nft", "blur", "opensea", "magic eden"],
    entityField: "marketplaces",
    entityList: DOMAINS.nft.entities,
    defaultArgs: { group_by: "marketplace", metric: "volume" },
    metricKeywords: { volume: ["volume"], sales_count: ["sales", "sale count"] },
    unit: "usd",
    label: "NFT volume",
  },
  {
    tool: "query_x402_agentic_payments",
    keywords: ["x402", "agentic payment", "agent payment", "ai agent payment", "agent-to-agent"],
    entityField: "facilitators",
    entityList: DOMAINS.x402_agentic_payments.entities,
    defaultArgs: { group_by: "facilitator", metric: "volume" },
    metricKeywords: { volume: ["volume"], tx_count: ["transaction", "tx count"] },
    unit: "usd",
    label: "x402 agentic payments",
  },
];

function matchKeyword(text, list) {
  return list.some((kw) => text.includes(kw));
}

function extractEntities(text, entityList) {
  return entityList.filter((e) => text.includes(e.toLowerCase()));
}

function parseDateRange(text) {
  const m = text.match(/last (\d+)\s*days?/);
  if (m) return { days: Number(m[1]) };
  if (/last week/.test(text)) return { days: 7 };
  if (/last month/.test(text)) return { days: 30 };
  if (/last quarter|last 90/.test(text)) return { days: 90 };
  if (/year to date|ytd|this year|all time|since inception|since january/.test(text)) return { sinceStart: true };
  return { days: 90 };
}

function addDays(dateStr, delta) {
  const d = new Date(dateStr + "T00:00:00Z");
  d.setUTCDate(d.getUTCDate() + delta);
  return d.toISOString().slice(0, 10);
}

function formatValue(v, unit) {
  if (unit === "percent") return `${v.toFixed(2)}%`;
  if (unit === "count") return v >= 1e6 ? `${(v / 1e6).toFixed(2)}M` : v.toLocaleString();
  if (v >= 1e9) return `$${(v / 1e9).toFixed(2)}B`;
  if (v >= 1e6) return `$${(v / 1e6).toFixed(2)}M`;
  return `$${v.toLocaleString()}`;
}

function buildInsight(series, data, unit) {
  if (data.length === 0) return "No data points matched this query.";
  const first = data[0];
  const last = data[data.length - 1];
  let topSeries = series[0];
  let topLast = -Infinity;
  for (const s of series) {
    const v = last[s] ?? 0;
    if (v > topLast) {
      topLast = v;
      topSeries = s;
    }
  }
  const firstVal = first[topSeries] ?? 0;
  const pct = firstVal ? (((last[topSeries] - firstVal) / firstVal) * 100).toFixed(1) : "0.0";
  const direction = Number(pct) >= 0 ? "up" : "down";
  return `${topSeries} leads at ${formatValue(topLast, unit)}, ${direction} ${Math.abs(pct)}% over the period.`;
}

export function routeOffline(userText) {
  const text = userText.toLowerCase();
  // Keyword matches are domain-specific and take priority. Entity names alone
  // are ambiguous -- e.g. "Solana" and "Base" are valid entities in both
  // chain_activity and protocol_revenue, so a phrase like "active addresses
  // on Solana vs Base" must not fall to whichever of those two happens to
  // sit first in ROUTES just because its entity list also contains them.
  const route =
    ROUTES.find((r) => matchKeyword(text, r.keywords)) || ROUTES.find((r) => extractEntities(text, r.entityList).length > 0);

  if (!route) {
    return {
      reply:
        "I couldn't map that to a data domain I have stubbed. Try asking about stablecoins, DeFi TVL, perpetuals, " +
        "prediction markets, RWA, protocol revenue, chain activity, staking, NFT volume, or x402 agentic payments.",
      chart: null,
    };
  }

  const args = { ...route.defaultArgs };
  const entities = extractEntities(text, route.entityList);
  if (entities.length > 0) args[route.entityField] = entities;

  if (route.metricKeywords) {
    for (const [metric, kws] of Object.entries(route.metricKeywords)) {
      if (kws.some((kw) => text.includes(kw))) {
        args.metric = metric;
        break;
      }
    }
  }

  const { days, sinceStart } = parseDateRange(text);
  args.start_date = sinceStart ? START_DATE : addDays(END_DATE, -(days - 1));
  args.end_date = END_DATE;
  const span = sinceStart ? 9999 : days;
  const wantsShare = /share|breakdown|composition|percent of total/.test(text);
  // Stacked bars read as a barcode past ~16 categories, so bucket much
  // coarser than a line/area chart would for the same date range.
  args.granularity = wantsShare
    ? span > 100
      ? "month"
      : span > 14
      ? "week"
      : "day"
    : span > 270
    ? "month"
    : span > 120
    ? "week"
    : "day";

  const result = runTool(route.tool, args);
  const chartType = wantsShare && result.series.length > 1 ? "stacked_bar" : "line";

  const entityNote = entities.length > 0 ? entities.join(", ") : "all tracked entities";
  const chart = {
    chart_type: chartType,
    title: `${route.label[0].toUpperCase()}${route.label.slice(1)}${entities.length ? ` — ${entities.join(", ")}` : ""}`,
    subtitle: `${entityNote} · ${args.start_date} to ${args.end_date}`,
    y_unit: route.unit,
    series: result.series,
    data: result.data,
    insight: buildInsight(result.series, result.data, route.unit),
  };

  return { reply: chart.insight, chart };
}
