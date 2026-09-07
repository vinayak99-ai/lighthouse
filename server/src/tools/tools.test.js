import test from "node:test";
import assert from "node:assert/strict";
import { seedAll } from "../data/seed.js";
import { getDb } from "../data/db.js";
import { runTool, isDataTool, ToolInputError } from "./tools.js";
import { TOOL_DEFINITIONS } from "./tools.js";

test.before(() => {
  seedAll();
});

test("exposes exactly 10 data tools plus render_chart", () => {
  const names = TOOL_DEFINITIONS.map((t) => t.name);
  assert.equal(names.filter(isDataTool).length, 10);
  assert.ok(names.includes("render_chart"));
});

test("query_stablecoin_supply groups by issuer over full range", async () => {
  const result = await runTool("query_stablecoin_supply", { issuers: ["USDT", "USDC"], group_by: "issuer" });
  assert.deepEqual(result.series.sort(), ["USDC", "USDT"]);
  assert.ok(result.data.length > 200);
  assert.ok(result.data[0].USDT > 0);
});

test("query_stablecoin_supply total collapses to one series", async () => {
  const result = await runTool("query_stablecoin_supply", { group_by: "total" });
  assert.equal(result.series.length, 1);
});

test("date range filters narrow the result", async () => {
  const result = await runTool("query_defi_tvl", { protocols: ["Aave"], group_by: "issuer" === "issuer" ? "protocol" : "protocol", start_date: "2026-06-01", end_date: "2026-06-30" });
  assert.ok(result.data.every((d) => d.x >= "2026-06-01" && d.x <= "2026-06-30"));
});

test("week granularity buckets down the point count", async () => {
  const daily = await runTool("query_chain_activity", { chains: ["Solana"], metric: "transactions", group_by: "chain" });
  const weekly = await runTool("query_chain_activity", { chains: ["Solana"], metric: "transactions", group_by: "chain", granularity: "week" });
  assert.ok(weekly.data.length < daily.data.length);
});

test("unknown entity is rejected with a helpful error", async () => {
  await assert.rejects(() => runTool("query_perpetuals", { exchanges: ["NotAnExchange"], metric: "volume" }), ToolInputError);
});

test("metric switch changes which column is aggregated", async () => {
  const oi = await runTool("query_perpetuals", { exchanges: ["Hyperliquid"], metric: "open_interest", group_by: "total" });
  const vol = await runTool("query_perpetuals", { exchanges: ["Hyperliquid"], metric: "volume", group_by: "total" });
  assert.notEqual(oi.data[0]["Open interest"], vol.data[0].Volume);
});

test("x402 agentic payments groups by agent network", async () => {
  const result = await runTool("query_x402_agentic_payments", { metric: "volume", group_by: "agent_network" });
  assert.ok(result.series.includes("AI Shopping Agents"));
});

test("issuer total sums across the hidden chain dimension, not just one chain", async () => {
  // Sanity check against raw SQL: total USDT supply on one day is the sum
  // across every chain, not an average across the 5 chain rows.
  const raw = getDb().prepare("SELECT SUM(supply_usd) v FROM stablecoin_supply WHERE issuer = 'USDT' AND date = '2026-08-22'").get();
  const result = await runTool("query_stablecoin_supply", { issuers: ["USDT"], group_by: "issuer", start_date: "2026-08-22", end_date: "2026-08-22" });
  assert.equal(result.data[0].USDT, raw.v);
});

test("stock metrics are averaged, not summed, when bucketed weekly", async () => {
  const daily = await runTool("query_rwa", { issuers: ["BlackRock BUIDL"], group_by: "issuer", start_date: "2026-06-01", end_date: "2026-06-07" });
  const weekly = await runTool("query_rwa", {
    issuers: ["BlackRock BUIDL"],
    group_by: "issuer",
    start_date: "2026-06-01",
    end_date: "2026-06-07",
    granularity: "week",
  });
  const dailyAvg = daily.data.reduce((sum, d) => sum + d["BlackRock BUIDL"], 0) / daily.data.length;
  assert.equal(weekly.data.length, 1);
  // A naive SUM over 7 days would be ~7x the average; AVG should land close to it instead.
  assert.ok(Math.abs(weekly.data[0]["BlackRock BUIDL"] - dailyAvg) / dailyAvg < 0.05);
});

test("flow metrics still sum across a weekly bucket", async () => {
  const daily = await runTool("query_protocol_revenue", { protocols: ["Solana"], metric: "revenue", start_date: "2026-06-01", end_date: "2026-06-07" });
  const weekly = await runTool("query_protocol_revenue", {
    protocols: ["Solana"],
    metric: "revenue",
    start_date: "2026-06-01",
    end_date: "2026-06-07",
    granularity: "week",
  });
  const dailySum = daily.data.reduce((sum, d) => sum + d.Solana, 0);
  assert.equal(weekly.data.length, 1);
  assert.ok(Math.abs(weekly.data[0].Solana - dailySum) / dailySum < 0.01);
});
