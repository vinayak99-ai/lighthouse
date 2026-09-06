import test from "node:test";
import assert from "node:assert/strict";
import { seedAll } from "../data/seed.js";
import { routeOffline } from "./fallbackRouter.js";

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
