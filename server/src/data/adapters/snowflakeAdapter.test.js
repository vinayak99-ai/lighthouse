import test from "node:test";
import assert from "node:assert/strict";
import { assertSelectOnly, UnsafeQueryError, __testables } from "./snowflakeAdapter.js";

test("a plain SELECT passes the safety guard", () => {
  assert.doesNotThrow(() => assertSelectOnly("SELECT * FROM stablecoin_supply WHERE date >= ?"));
});

test("a WITH ... SELECT (our own two-stage aggregation queries) passes", () => {
  assert.doesNotThrow(() => assertSelectOnly("WITH daily AS (SELECT date, value FROM t) SELECT * FROM daily"));
});

test("multiple statements chained with a semicolon are rejected", () => {
  assert.throws(() => assertSelectOnly("SELECT 1; DROP TABLE t;"), UnsafeQueryError);
});

test("a single trailing semicolon is fine", () => {
  assert.doesNotThrow(() => assertSelectOnly("SELECT 1;"));
});

for (const bad of ["INSERT INTO t VALUES (1)", "UPDATE t SET x = 1", "DELETE FROM t", "DROP TABLE t", "CREATE TABLE t (x INT)", "ALTER SESSION SET X=1", "GRANT SELECT ON t TO ROLE r", "TRUNCATE TABLE t"]) {
  test(`rejects a write/DDL statement: ${bad.split(" ")[0]}`, () => {
    assert.throws(() => assertSelectOnly(bad), UnsafeQueryError);
  });
}

test("a statement that isn't SELECT or WITH at all is rejected", () => {
  assert.throws(() => assertSelectOnly("SHOW TABLES"), UnsafeQueryError);
});

test("executeWithTimeout resolves normally when the query completes in time", async () => {
  const fakeConnection = {
    execute({ complete }) {
      setTimeout(() => complete(null, {}, [{ x: 1 }]), 5);
      return { cancel: () => {} };
    },
  };
  const rows = await __testables.executeWithTimeout(fakeConnection, "SELECT 1", [], 200);
  assert.deepEqual(rows, [{ x: 1 }]);
});

test("executeWithTimeout cancels the statement and rejects when the query hangs past the timeout", async () => {
  let cancelCalled = false;
  const fakeConnection = {
    execute() {
      // Never calls `complete` -- simulates a hung/long-running query.
      return {
        cancel(cb) {
          cancelCalled = true;
          cb();
        },
      };
    },
  };

  await assert.rejects(
    () => __testables.executeWithTimeout(fakeConnection, "SELECT 1", [], 20),
    /exceeded the 0\.02s application-level timeout/
  );
  assert.equal(cancelCalled, true, "the hung statement should have been explicitly cancelled");
});

test("executeWithTimeout ignores a late completion after it already timed out", async () => {
  const fakeConnection = {
    execute({ complete }) {
      // Completes AFTER the timeout has already fired and rejected.
      setTimeout(() => complete(null, {}, [{ x: 1 }]), 50);
      return { cancel: (cb) => cb() };
    },
  };

  await assert.rejects(() => __testables.executeWithTimeout(fakeConnection, "SELECT 1", [], 10));
  // Give the late `complete` a chance to fire and confirm it doesn't throw
  // an unhandled rejection or resolve a promise nobody awaits anymore.
  await new Promise((r) => setTimeout(r, 60));
});

test("getConnection retries after a failed attempt instead of caching the failure forever", async () => {
  // Regression test for a real bug found by testing against an unreachable
  // account: a rejected connection used to stay cached, so every future
  // query would fail immediately even after the network issue cleared.
  __testables.resetConnectionCache();
  let attempts = 0;
  const flakyConnect = () => {
    attempts++;
    if (attempts === 1) return Promise.reject(new Error("network unreachable"));
    return Promise.resolve({ fake: true });
  };

  await assert.rejects(() => __testables.getConnection(flakyConnect), /network unreachable/);
  const connection = await __testables.getConnection(flakyConnect);

  assert.deepEqual(connection, { fake: true });
  assert.equal(attempts, 2, "the second call should have retried instead of reusing the cached failure");
  __testables.resetConnectionCache();
});

test("getConnection caches a successful connection across calls", async () => {
  __testables.resetConnectionCache();
  let attempts = 0;
  const connectOnce = () => {
    attempts++;
    return Promise.resolve({ fake: true });
  };

  await __testables.getConnection(connectOnce);
  await __testables.getConnection(connectOnce);

  assert.equal(attempts, 1, "a successful connection should be reused, not re-established per query");
  __testables.resetConnectionCache();
});
