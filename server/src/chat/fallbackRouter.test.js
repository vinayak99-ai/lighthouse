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
