import test from "node:test";
import assert from "node:assert/strict";
import { toPositionalBinds } from "./sqlBinding.js";

test("converts named placeholders to positional ? in order of appearance", () => {
  const { sql, binds } = toPositionalBinds("SELECT * FROM t WHERE date >= @startDate AND date <= @endDate", {
    startDate: "2026-01-01",
    endDate: "2026-02-01",
  });
  assert.equal(sql, "SELECT * FROM t WHERE date >= ? AND date <= ?");
  assert.deepEqual(binds, ["2026-01-01", "2026-02-01"]);
});

test("repeats a placeholder's value each time it appears", () => {
  const { sql, binds } = toPositionalBinds("SELECT @x, @x", { x: 5 });
  assert.equal(sql, "SELECT ?, ?");
  assert.deepEqual(binds, [5, 5]);
});

test("throws on a placeholder with no matching param", () => {
  assert.throws(() => toPositionalBinds("SELECT @missing", {}), /Missing bind parameter/);
});

test("leaves SQL with no placeholders untouched", () => {
  const { sql, binds } = toPositionalBinds("SELECT 1", {});
  assert.equal(sql, "SELECT 1");
  assert.deepEqual(binds, []);
});
