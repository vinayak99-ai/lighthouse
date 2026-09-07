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
