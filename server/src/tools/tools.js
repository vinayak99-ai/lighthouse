import { DOMAINS, START_DATE, END_DATE } from "../data/entities.js";
import { runGroupedTimeSeries, pivotByEntity, ToolInputError } from "./queryEngine.js";

const dateProps = {
  start_date: { type: "string", description: `Inclusive start date, YYYY-MM-DD. Data available from ${START_DATE}.` },
  end_date: { type: "string", description: `Inclusive end date, YYYY-MM-DD. Data available through ${END_DATE}.` },
  granularity: { type: "string", enum: ["day", "week", "month"], description: "Time bucket size. Use week/month for ranges longer than ~90 days to keep series readable." },
};

async function timeSeriesResult({ table, entityCol, entityAllowed, entities, extraFilters, valueCol, aggregate, args, fallbackSeriesName }) {
  const { rows } = await runGroupedTimeSeries({
    table,
    entityCol,
    entityAllowed,
    entities,
    extraFilters,
    valueCol,
    aggregate,
    startDate: args.start_date,
    endDate: args.end_date,
    granularity: args.granularity || "day",
    groupByEntity: args.group_by !== "total",
  });
  const { data, series } = pivotByEntity(rows, { fallbackSeriesName });
  return { row_count: rows.length, point_count: data.length, series, data };
}

export const TOOL_DEFINITIONS = [
  {
    name: "query_stablecoin_supply",
    description:
      "Time series of stablecoin circulating supply (USD) by issuer and/or chain. Issuers: " +
      DOMAINS.stablecoins.entities.join(", ") + ". Chains: " + DOMAINS.stablecoins.chains.join(", ") + ".",
    input_schema: {
      type: "object",
      properties: {
        issuers: { type: "array", items: { type: "string", enum: DOMAINS.stablecoins.entities }, description: "Filter to these issuers. Omit for all." },
        chains: { type: "array", items: { type: "string", enum: DOMAINS.stablecoins.chains }, description: "Filter to these chains. Omit for all." },
        group_by: { type: "string", enum: ["issuer", "total"], description: "Split series by issuer, or return a single combined total." },
        ...dateProps,
      },
    },
  },
  {
    name: "query_defi_tvl",
    description:
      "Time series of DeFi protocol Total Value Locked (USD). Protocols: " + DOMAINS.defi_tvl.entities.join(", ") +
      ". Chains: " + DOMAINS.defi_tvl.chains.join(", ") + ".",
    input_schema: {
      type: "object",
      properties: {
        protocols: { type: "array", items: { type: "string", enum: DOMAINS.defi_tvl.entities } },
        chains: { type: "array", items: { type: "string", enum: DOMAINS.defi_tvl.chains } },
        group_by: { type: "string", enum: ["protocol", "total"] },
        ...dateProps,
      },
    },
  },
  {
    name: "query_perpetuals",
    description: "Time series of perpetual futures open interest or trading volume (USD) by exchange. Exchanges: " + DOMAINS.perpetuals.entities.join(", ") + ".",
    input_schema: {
      type: "object",
      properties: {
        exchanges: { type: "array", items: { type: "string", enum: DOMAINS.perpetuals.entities } },
        metric: { type: "string", enum: ["open_interest", "volume"], description: "Which measure to return." },
        group_by: { type: "string", enum: ["exchange", "total"] },
        ...dateProps,
      },
      required: ["metric"],
    },
  },
  {
    name: "query_prediction_markets",
    description:
      "Time series of prediction market trading volume (USD) by platform and/or category. Platforms: " +
      DOMAINS.prediction_markets.entities.join(", ") + ". Categories: " + DOMAINS.prediction_markets.categories.join(", ") + ".",
    input_schema: {
      type: "object",
      properties: {
        platforms: { type: "array", items: { type: "string", enum: DOMAINS.prediction_markets.entities } },
        categories: { type: "array", items: { type: "string", enum: DOMAINS.prediction_markets.categories } },
        group_by: { type: "string", enum: ["platform", "category", "total"] },
        ...dateProps,
      },
    },
  },
  {
    name: "query_rwa",
    description:
      "Time series of tokenized real-world asset (RWA) value (USD) by issuer. Issuers: " + DOMAINS.rwa.entities.join(", ") +
      ". Asset types: " + DOMAINS.rwa.assetTypes.join(", ") + ".",
    input_schema: {
      type: "object",
      properties: {
        issuers: { type: "array", items: { type: "string", enum: DOMAINS.rwa.entities } },
        asset_types: { type: "array", items: { type: "string", enum: DOMAINS.rwa.assetTypes } },
        group_by: { type: "string", enum: ["issuer", "asset_type", "total"] },
        ...dateProps,
      },
    },
  },
  {
    name: "query_protocol_revenue",
    description: "Time series of blockchain protocol revenue or fees (USD). Protocols: " + DOMAINS.protocol_revenue.entities.join(", ") + ".",
    input_schema: {
      type: "object",
      properties: {
        protocols: { type: "array", items: { type: "string", enum: DOMAINS.protocol_revenue.entities } },
        metric: { type: "string", enum: ["revenue", "fees"] },
        group_by: { type: "string", enum: ["protocol", "total"] },
        ...dateProps,
      },
      required: ["metric"],
    },
  },
  {
    name: "query_chain_activity",
    description: "Time series of daily active addresses or transaction counts by chain. Chains: " + DOMAINS.chain_activity.entities.join(", ") + ".",
    input_schema: {
      type: "object",
      properties: {
        chains: { type: "array", items: { type: "string", enum: DOMAINS.chain_activity.entities } },
        metric: { type: "string", enum: ["active_addresses", "transactions"] },
        group_by: { type: "string", enum: ["chain", "total"] },
        ...dateProps,
      },
      required: ["metric"],
    },
  },
  {
    name: "query_staking",
    description: "Time series of staked ETH or staking APR by provider. Providers: " + DOMAINS.staking.entities.join(", ") + ".",
    input_schema: {
      type: "object",
      properties: {
        providers: { type: "array", items: { type: "string", enum: DOMAINS.staking.entities } },
        metric: { type: "string", enum: ["staked_eth", "apr_pct"] },
        group_by: { type: "string", enum: ["provider", "total"] },
        ...dateProps,
      },
      required: ["metric"],
    },
  },
  {
    name: "query_nft_volume",
    description: "Time series of NFT marketplace trading volume (USD) or sales count. Marketplaces: " + DOMAINS.nft.entities.join(", ") + ".",
    input_schema: {
      type: "object",
      properties: {
        marketplaces: { type: "array", items: { type: "string", enum: DOMAINS.nft.entities } },
        metric: { type: "string", enum: ["volume", "sales_count"] },
        group_by: { type: "string", enum: ["marketplace", "total"] },
        ...dateProps,
      },
      required: ["metric"],
    },
  },
  {
    name: "query_x402_agentic_payments",
    description:
      "Time series of x402 agentic payment volume (USD) or transaction count — machine-to-machine payments made by AI agents. Facilitators: " +
      DOMAINS.x402_agentic_payments.entities.join(", ") + ". Agent networks: " + DOMAINS.x402_agentic_payments.agentNetworks.join(", ") + ".",
    input_schema: {
      type: "object",
      properties: {
        facilitators: { type: "array", items: { type: "string", enum: DOMAINS.x402_agentic_payments.entities } },
        agent_networks: { type: "array", items: { type: "string", enum: DOMAINS.x402_agentic_payments.agentNetworks } },
        metric: { type: "string", enum: ["volume", "tx_count"] },
        group_by: { type: "string", enum: ["facilitator", "agent_network", "total"] },
        ...dateProps,
      },
      required: ["metric"],
    },
  },
  {
    name: "render_chart",
    description:
      "Render the final chart for the user. Call this once you have the data you need. type='line'/'area' for trend over time, " +
      "'bar' for magnitude comparison, 'stacked_bar' for part-to-whole over time, 'stat' for a single current value (a KPI, not " +
      "a trend), 'small_multiples' for many entities' trend shapes at once, 'scatter' for comparing two numeric metrics across " +
      "entities (correlation, risk/return) -- add a `z` value per point to render it as a bubble chart sized by a third metric. " +
      "`series` lists the entity keys in the order they should be colored (max 8, fold extras into 'Other') for every " +
      "chart_type except 'scatter', where it instead lists the point-group names (usually just one). `data` is an array of " +
      "rows shaped { x: <date or category label>, <series key>: <number>, ... } for every chart_type except 'scatter', " +
      "ascending by x -- 'stat' and 'small_multiples' use this same shape too, they just render it differently. 'scatter' " +
      "rows are shaped { label: <entity name>, x: <number>, y: <number>, z: <number, optional, bubble size>, " +
      "group: <one of `series`, optional if `series` has one entry> } instead -- x/y are two different metrics for the same " +
      "entity, not a date and a value, so build them yourself from prior tool results rather than passing one straight through.",
    input_schema: {
      type: "object",
      properties: {
        chart_type: { type: "string", enum: ["line", "area", "bar", "stacked_bar", "stat", "small_multiples", "scatter"] },
        title: { type: "string" },
        subtitle: { type: "string", description: "One short sentence of context (units, date range)." },
        y_unit: { type: "string", enum: ["usd", "count", "percent"], description: "How to format axis ticks and tooltip values (the y-axis metric, for 'scatter')." },
        x_unit: { type: "string", enum: ["usd", "count", "percent"], description: "'scatter' only: how to format the x-axis metric." },
        x_axis_label: { type: "string", description: "'scatter' only: name of the x-axis metric, e.g. 'TVL (USD)'." },
        y_axis_label: { type: "string", description: "'scatter' only: name of the y-axis metric." },
        z_axis_label: { type: "string", description: "'scatter' only: name of the bubble-size metric, if any point has a `z` value." },
        series: { type: "array", items: { type: "string" }, maxItems: 8 },
        data: {
          type: "array",
          items: { type: "object" },
          description: "Rows shaped { x, <series key>: number, ... }, ascending by x -- or, for 'scatter', { label, x, y, z?, group? }.",
        },
        insight: { type: "string", description: "One or two sentence takeaway a sharp analyst would say about this chart." },
      },
      required: ["chart_type", "title", "series", "data"],
    },
  },
];

const HANDLERS = {
  query_stablecoin_supply: (args) =>
    timeSeriesResult({
      table: "stablecoin_supply",
      entityCol: "issuer",
      entityAllowed: DOMAINS.stablecoins.entities,
      entities: args.issuers,
      extraFilters: [{ col: "chain", allowed: DOMAINS.stablecoins.chains, values: args.chains }],
      valueCol: "supply_usd",
      aggregate: "AVG", // supply is a stock (point-in-time level) -- summing across bucketed days would inflate it
      args,
      fallbackSeriesName: "Total supply",
    }),
  query_defi_tvl: (args) =>
    timeSeriesResult({
      table: "defi_tvl",
      entityCol: "protocol",
      entityAllowed: DOMAINS.defi_tvl.entities,
      entities: args.protocols,
      extraFilters: [{ col: "chain", allowed: DOMAINS.defi_tvl.chains, values: args.chains }],
      valueCol: "tvl_usd",
      aggregate: "AVG", // TVL is a stock, not a flow -- average the bucket, don't sum it
      args,
      fallbackSeriesName: "Total TVL",
    }),
  query_perpetuals: (args) =>
    timeSeriesResult({
      table: "perp_markets",
      entityCol: "exchange",
      entityAllowed: DOMAINS.perpetuals.entities,
      entities: args.exchanges,
      valueCol: args.metric === "open_interest" ? "open_interest_usd" : "volume_usd",
      aggregate: args.metric === "open_interest" ? "AVG" : "SUM", // open interest is a stock; volume is a flow
      args,
      fallbackSeriesName: args.metric === "open_interest" ? "Open interest" : "Volume",
    }),
  query_prediction_markets: (args) =>
    timeSeriesResult({
      table: "prediction_markets",
      entityCol: args.group_by === "category" ? "category" : "platform",
      entityAllowed: args.group_by === "category" ? DOMAINS.prediction_markets.categories : DOMAINS.prediction_markets.entities,
      entities: args.group_by === "category" ? args.categories : args.platforms,
      extraFilters:
        args.group_by === "category"
          ? [{ col: "platform", allowed: DOMAINS.prediction_markets.entities, values: args.platforms }]
          : [{ col: "category", allowed: DOMAINS.prediction_markets.categories, values: args.categories }],
      valueCol: "volume_usd",
      args,
      fallbackSeriesName: "Total volume",
    }),
  query_rwa: (args) =>
    timeSeriesResult({
      table: "rwa_value",
      entityCol: args.group_by === "asset_type" ? "asset_type" : "issuer",
      entityAllowed: args.group_by === "asset_type" ? DOMAINS.rwa.assetTypes : DOMAINS.rwa.entities,
      entities: args.group_by === "asset_type" ? args.asset_types : args.issuers,
      extraFilters:
        args.group_by === "asset_type"
          ? [{ col: "issuer", allowed: DOMAINS.rwa.entities, values: args.issuers }]
          : [{ col: "asset_type", allowed: DOMAINS.rwa.assetTypes, values: args.asset_types }],
      valueCol: "value_usd",
      aggregate: "AVG", // tokenized value is a stock -- average the bucket, don't sum it
      args,
      fallbackSeriesName: "Total value",
    }),
  query_protocol_revenue: (args) =>
    timeSeriesResult({
      table: "protocol_revenue",
      entityCol: "protocol",
      entityAllowed: DOMAINS.protocol_revenue.entities,
      entities: args.protocols,
      valueCol: args.metric === "revenue" ? "revenue_usd" : "fees_usd",
      args,
      fallbackSeriesName: args.metric === "revenue" ? "Revenue" : "Fees",
    }),
  query_chain_activity: (args) =>
    timeSeriesResult({
      table: "chain_activity",
      entityCol: "chain",
      entityAllowed: DOMAINS.chain_activity.entities,
      entities: args.chains,
      valueCol: args.metric === "active_addresses" ? "active_addresses" : "transactions",
      // active addresses is a daily headcount (stock-like, summing double-counts repeat users);
      // transactions is a genuine flow, safe to sum across a bucket.
      aggregate: args.metric === "active_addresses" ? "AVG" : "SUM",
      args,
      fallbackSeriesName: args.metric === "active_addresses" ? "Active addresses" : "Transactions",
    }),
  query_staking: (args) =>
    timeSeriesResult({
      table: "staking",
      entityCol: "provider",
      entityAllowed: DOMAINS.staking.entities,
      entities: args.providers,
      valueCol: args.metric === "apr_pct" ? "apr_pct" : "staked_eth",
      aggregate: "AVG", // both staked ETH and APR are stocks/rates -- never summed across a bucket
      args,
      fallbackSeriesName: args.metric === "apr_pct" ? "APR" : "Staked ETH",
    }),
  query_nft_volume: (args) =>
    timeSeriesResult({
      table: "nft_volume",
      entityCol: "marketplace",
      entityAllowed: DOMAINS.nft.entities,
      entities: args.marketplaces,
      valueCol: args.metric === "sales_count" ? "sales_count" : "volume_usd",
      args,
      fallbackSeriesName: args.metric === "sales_count" ? "Sales" : "Volume",
    }),
  query_x402_agentic_payments: (args) =>
    timeSeriesResult({
      table: "x402_payments",
      entityCol: args.group_by === "agent_network" ? "agent_network" : "facilitator",
      entityAllowed: args.group_by === "agent_network" ? DOMAINS.x402_agentic_payments.agentNetworks : DOMAINS.x402_agentic_payments.entities,
      entities: args.group_by === "agent_network" ? args.agent_networks : args.facilitators,
      extraFilters:
        args.group_by === "agent_network"
          ? [{ col: "facilitator", allowed: DOMAINS.x402_agentic_payments.entities, values: args.facilitators }]
          : [{ col: "agent_network", allowed: DOMAINS.x402_agentic_payments.agentNetworks, values: args.agent_networks }],
      valueCol: args.metric === "tx_count" ? "tx_count" : "volume_usd",
      args,
      fallbackSeriesName: args.metric === "tx_count" ? "Transactions" : "Volume",
    }),
};

export function isDataTool(name) {
  return name !== "render_chart" && Object.prototype.hasOwnProperty.call(HANDLERS, name);
}

export async function runTool(name, args) {
  const handler = HANDLERS[name];
  if (!handler) throw new ToolInputError(`Unknown tool: ${name}`);
  return handler(args || {});
}

export { ToolInputError };
