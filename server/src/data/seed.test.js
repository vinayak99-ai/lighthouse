import test from "node:test";
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { getDb } from "./db.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SEED_SCRIPT = path.join(__dirname, "seed.js");

const EXPECTED_COUNTS = {
  stablecoin_supply: 7020,
  defi_tvl: 7020,
  perp_markets: 1170,
  prediction_markets: 3510,
  rwa_value: 1170,
  protocol_revenue: 1170,
  chain_activity: 1170,
  staking: 1170,
  nft_volume: 702,
  x402_payments: 2808,
};

function runSeedInChildProcess() {
  return new Promise((resolve, reject) => {
    const child = spawn(process.execPath, [SEED_SCRIPT], { stdio: "ignore" });
    child.on("exit", (code) => (code === 0 ? resolve() : reject(new Error(`seed.js exited with code ${code}`))));
    child.on("error", reject);
  });
}

test("two OS processes seeding at once never double a table", { timeout: 30000 }, async () => {
  // Sanity check motivated by a real production bug: a dev server's
  // boot-time auto-seed raced a separate `npm run seed`/test-run process
  // against the same on-disk file, and because clearTable() and insertRows()
  // were two separate autocommit statements, the second process's DELETE
  // landed between the first's DELETE and INSERT -- both inserts survived,
  // silently doubling stablecoin_supply to 14,040 rows in the live dev
  // database (caught by a suspiciously-exact 2x value while spot-checking
  // charts, not by a test). The real guarantee against that race is
  // insertRows()'s DELETE+INSERT now being one SQLite transaction, which is
  // correct by construction (SQLite serializes concurrent writers to the
  // same file) regardless of timing. This test's two concurrently-spawned
  // processes are a best-effort attempt to also exercise that race
  // end-to-end; the microsecond-scale window between the two statements
  // means this doesn't reliably reproduce the failure on demand (it did not
  // fail when checked against the pre-fix code either) -- keep it as a
  // baseline correctness check on concurrent seeding, not as proof the
  // race is covered.
  await Promise.all([runSeedInChildProcess(), runSeedInChildProcess()]);

  for (const [table, expected] of Object.entries(EXPECTED_COUNTS)) {
    const { c } = getDb().prepare(`SELECT COUNT(*) c FROM ${table}`).get();
    assert.equal(c, expected, `${table} should have exactly ${expected} rows after a concurrent reseed, got ${c}`);
  }
});
