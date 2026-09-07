import test from "node:test";
import assert from "node:assert/strict";
import { validateChart } from "./chartValidator.js";

function baseChart(overrides = {}) {
  return {
    chart_type: "line",
    title: "Test chart",
    series: ["A", "B"],
    data: [
      { x: "2026-01-01", A: 1, B: 2 },
      { x: "2026-01-02", A: 2, B: 3 },
    ],
    ...overrides,
  };
}

test("a well-formed line chart passes", () => {
  const { valid, issues } = validateChart(baseChart());
  assert.equal(valid, true);
  assert.deepEqual(issues, []);
});

test("empty series is rejected", () => {
  const { valid, issues } = validateChart(baseChart({ series: [] }));
  assert.equal(valid, false);
  assert.match(issues[0], /empty/i);
});

test("empty data is rejected", () => {
  const { valid, issues } = validateChart(baseChart({ data: [] }));
  assert.equal(valid, false);
  assert.match(issues[0], /empty/i);
});

test("more than 8 series is rejected", () => {
  const series = Array.from({ length: 9 }, (_, i) => `S${i}`);
  const data = [Object.fromEntries([["x", "2026-01-01"], ...series.map((s) => [s, 1])])];
  const { valid, issues } = validateChart(baseChart({ series, data }));
  assert.equal(valid, false);
  assert.match(issues.join(" "), /8-series cap/);
});

test("area chart with more than one series is rejected", () => {
  const { valid, issues } = validateChart(baseChart({ chart_type: "area" }));
  assert.equal(valid, false);
  assert.match(issues.join(" "), /muddy band/);
});

test("area chart with exactly one series is fine", () => {
  const { valid } = validateChart(
    baseChart({ chart_type: "area", series: ["A"], data: [{ x: "2026-01-01", A: 1 }] })
  );
  assert.equal(valid, true);
});

test("stacked_bar with too many bars is rejected", () => {
  const data = Array.from({ length: 20 }, (_, i) => ({ x: `2026-01-${i + 1}`, A: 1, B: 2 }));
  const { valid, issues } = validateChart(baseChart({ chart_type: "stacked_bar", data }));
  assert.equal(valid, false);
  assert.match(issues.join(" "), /barcode/);
});

test("stacked_bar within the bar limit is fine", () => {
  const data = Array.from({ length: 10 }, (_, i) => ({ x: `2026-01-${i + 1}`, A: 1, B: 2 }));
  const { valid } = validateChart(baseChart({ chart_type: "stacked_bar", data }));
  assert.equal(valid, true);
});

test("a line chart with too many overlapping series is rejected", () => {
  const series = ["A", "B", "C", "D", "E", "F", "G"];
  const data = [Object.fromEntries([["x", "2026-01-01"], ...series.map((s) => [s, 1])])];
  const { valid, issues } = validateChart(baseChart({ series, data }));
  assert.equal(valid, false);
  assert.match(issues.join(" "), /small_multiples/);
});

test("small_multiples is exempt from the line overlay series limit", () => {
  const series = ["A", "B", "C", "D", "E", "F", "G"];
  const data = [Object.fromEntries([["x", "2026-01-01"], ...series.map((s) => [s, 1])])];
  const { valid } = validateChart(baseChart({ chart_type: "small_multiples", series, data }));
  assert.equal(valid, true);
});

test("a series that never has a value anywhere is flagged", () => {
  const { valid, issues } = validateChart(
    baseChart({
      series: ["A", "B", "Ghost"],
      data: [
        { x: "2026-01-01", A: 1, B: 2 },
        { x: "2026-01-02", A: 2, B: 3 },
      ],
    })
  );
  assert.equal(valid, false);
  assert.match(issues.join(" "), /Ghost/);
});

function scatterChart(overrides = {}) {
  return {
    chart_type: "scatter",
    title: "Test scatter",
    series: ["value"],
    data: [{ label: "Aave", x: 1, y: 2, group: "value" }],
    ...overrides,
  };
}

test("a well-formed ungrouped scatter chart passes", () => {
  const { valid, issues } = validateChart(scatterChart());
  assert.equal(valid, true);
  assert.deepEqual(issues, []);
});

test("scatter group is optional when series has a single entry", () => {
  const { valid } = validateChart(scatterChart({ data: [{ label: "Aave", x: 1, y: 2 }] }));
  assert.equal(valid, true);
});

test("a bubble chart (z + multiple groups) passes", () => {
  const { valid } = validateChart(
    scatterChart({
      series: ["L1", "L2"],
      data: [
        { label: "Ethereum", x: 100, y: 2.5, z: 4e11, group: "L1" },
        { label: "Arbitrum", x: 20, y: -1.2, z: 3e9, group: "L2" },
      ],
    })
  );
  assert.equal(valid, true);
});

test("a scatter point missing x or y is rejected", () => {
  const { valid, issues } = validateChart(scatterChart({ data: [{ label: "Aave", y: 2 }] }));
  assert.equal(valid, false);
  assert.match(issues.join(" "), /numeric `x`/);
});

test("a scatter point missing a label is rejected", () => {
  const { valid } = validateChart(scatterChart({ data: [{ x: 1, y: 2 }] }));
  assert.equal(valid, false);
});

test("a scatter point group not in series is rejected", () => {
  const { valid, issues } = validateChart(scatterChart({ data: [{ label: "Aave", x: 1, y: 2, group: "nope" }] }));
  assert.equal(valid, false);
  assert.match(issues.join(" "), /nope/);
});

test("scatter over the point limit is rejected", () => {
  const data = Array.from({ length: 201 }, (_, i) => ({ label: `e${i}`, x: i, y: i, group: "value" }));
  const { valid, issues } = validateChart(scatterChart({ data }));
  assert.equal(valid, false);
  assert.match(issues.join(" "), /200-point/);
});

test("scatter still enforces the max-series cap", () => {
  const series = Array.from({ length: 9 }, (_, i) => `S${i}`);
  const { valid, issues } = validateChart(
    scatterChart({ series, data: [{ label: "e", x: 1, y: 1, group: series[0] }] })
  );
  assert.equal(valid, false);
  assert.match(issues.join(" "), /8-series cap/);
});
