import test from "node:test";
import assert from "node:assert/strict";
import { seedAll } from "../data/seed.js";
import { routeOffline } from "./fallbackRouter.js";
import { validateChart } from "../tools/chartValidator.js";

test.before(() => {
  seedAll();
});

test("a domain keyword wins over an entity name shared with another domain", () => {
  // "Solana" and "Base" are valid entities in both chain_activity and
  // protocol_revenue -- the "active addresses" keyword must decide this,
  // not entity-list order.
  const { chart } = routeOffline("Active addresses on Solana vs Base this year");
  assert.match(chart.title, /chain activity/i);
  assert.deepEqual(chart.series.sort(), ["Base", "Solana"]);
});

test("protocol revenue keyword still routes correctly for the same shared entities", () => {
  const { chart } = routeOffline("Solana vs Base protocol revenue this quarter");
  assert.match(chart.title, /protocol revenue/i);
});

test("unmapped question returns no chart", () => {
  const { chart, reply } = routeOffline("What's the weather like today?");
  assert.equal(chart, null);
  assert.match(reply, /couldn't map/i);
});

test("a snapshot question renders a stat tile, not a trend chart", () => {
  const { chart } = routeOffline("What's the current TVL of Aave?");
  assert.equal(chart.chart_type, "stat");
  assert.deepEqual(chart.series, ["Aave"]);
});

test("'current' with trend language still renders a chart, not a stat tile", () => {
  const { chart } = routeOffline("Show the current TVL trend for Aave over time");
  assert.notEqual(chart.chart_type, "stat");
});

test("more than 4 entities in one line chart renders as small multiples instead", () => {
  // No specific issuer named -> all 6 stablecoin issuers -> too many for one overlay plot.
  const { chart } = routeOffline("Chart stablecoin supply this year");
  assert.equal(chart.chart_type, "small_multiples");
  assert.ok(chart.series.length > 4);
});

test("a few named entities still render as a plain line chart", () => {
  const { chart } = routeOffline("Chart USDT vs USDC supply over the last 90 days");
  assert.equal(chart.chart_type, "line");
});

test("the route with the most keyword matches wins, not the first one in array order", () => {
  // "Lido" is a defi_tvl keyword AND a staking entity -- "staked eth" and
  // "rocket pool" (2 staking-keyword matches) must beat defi_tvl's 1 match.
  const { chart } = routeOffline("What is the current staked eth for Lido, Coinbase and Rocket Pool?");
  assert.match(chart.title, /staking/i);
  assert.deepEqual(chart.series.sort(), ["Coinbase", "Lido", "Rocket Pool"]);
});

// The offline router's heuristics (granularity bumping, small_multiples
// auto-switch, stat detection) were hand-tuned against chartValidator.js's
// rules separately from the live-model retry loop in the providers. This
// sweep is the regression guard that keeps them in sync: every chart the
// router can produce, across every domain and phrasing style, must pass the
// same check the live path enforces.
const REPRESENTATIVE_QUERIES = [
  "Chart USDT vs USDC supply over the last 90 days",
  "Chart stablecoin supply this year",
  "Show TVL for Aave, Lido and EigenLayer this year",
  "DeFi TVL breakdown by protocol",
  "Compare open interest across Hyperliquid, dYdX and GMX",
  "Prediction market volume by platform, last 30 days",
  "Tokenized RWA value share by issuer breakdown",
  "Ethereum vs Solana protocol revenue, last quarter",
  "Active addresses on Solana vs Base this year",
  "Staked ETH by provider over the last 6 months",
  "Blur vs OpenSea volume, last 30 days",
  "x402 agentic payment volume by agent network",
  "What's the current TVL of Aave?",
  "What is the current staked eth for Lido, Coinbase and Rocket Pool?",
];

test("every chart the offline router can produce passes the shared validator", () => {
  for (const query of REPRESENTATIVE_QUERIES) {
    const { chart } = routeOffline(query);
    assert.ok(chart, `expected a chart for: "${query}"`);
    const { valid, issues } = validateChart(chart);
    assert.ok(valid, `"${query}" produced an invalid chart: ${issues.join("; ")}`);
  }
});
