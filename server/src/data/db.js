import path from "node:path";
import { fileURLToPath } from "node:url";
import Database from "better-sqlite3";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
export const DB_PATH = path.join(__dirname, "lighthouse.sqlite");

let _db = null;

export function getDb() {
  if (_db) return _db;
  _db = new Database(DB_PATH);
  _db.pragma("journal_mode = WAL");
  // This file is shared by multiple OS processes in dev (the server, `npm run
  // seed`, and test runs) -- without a busy timeout, a writer that finds the
  // file locked throws SQLITE_BUSY immediately instead of waiting its turn.
  _db.pragma("busy_timeout = 5000");
  return _db;
}

export const SCHEMA = `
CREATE TABLE IF NOT EXISTS stablecoin_supply (
  date TEXT NOT NULL,
  issuer TEXT NOT NULL,
  chain TEXT NOT NULL,
  supply_usd REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_stablecoin_supply_date ON stablecoin_supply(date);

CREATE TABLE IF NOT EXISTS defi_tvl (
  date TEXT NOT NULL,
  protocol TEXT NOT NULL,
  chain TEXT NOT NULL,
  tvl_usd REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_defi_tvl_date ON defi_tvl(date);

CREATE TABLE IF NOT EXISTS perp_markets (
  date TEXT NOT NULL,
  exchange TEXT NOT NULL,
  open_interest_usd REAL NOT NULL,
  volume_usd REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_perp_markets_date ON perp_markets(date);

CREATE TABLE IF NOT EXISTS prediction_markets (
  date TEXT NOT NULL,
  platform TEXT NOT NULL,
  category TEXT NOT NULL,
  volume_usd REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_prediction_markets_date ON prediction_markets(date);

CREATE TABLE IF NOT EXISTS rwa_value (
  date TEXT NOT NULL,
  asset_type TEXT NOT NULL,
  issuer TEXT NOT NULL,
  value_usd REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_rwa_value_date ON rwa_value(date);

CREATE TABLE IF NOT EXISTS protocol_revenue (
  date TEXT NOT NULL,
  protocol TEXT NOT NULL,
  chain TEXT NOT NULL,
  revenue_usd REAL NOT NULL,
  fees_usd REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_protocol_revenue_date ON protocol_revenue(date);

CREATE TABLE IF NOT EXISTS chain_activity (
  date TEXT NOT NULL,
  chain TEXT NOT NULL,
  active_addresses INTEGER NOT NULL,
  transactions INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_chain_activity_date ON chain_activity(date);

CREATE TABLE IF NOT EXISTS staking (
  date TEXT NOT NULL,
  provider TEXT NOT NULL,
  staked_eth REAL NOT NULL,
  apr_pct REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_staking_date ON staking(date);

CREATE TABLE IF NOT EXISTS nft_volume (
  date TEXT NOT NULL,
  marketplace TEXT NOT NULL,
  volume_usd REAL NOT NULL,
  sales_count INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_nft_volume_date ON nft_volume(date);

CREATE TABLE IF NOT EXISTS x402_payments (
  date TEXT NOT NULL,
  facilitator TEXT NOT NULL,
  agent_network TEXT NOT NULL,
  volume_usd REAL NOT NULL,
  tx_count INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_x402_payments_date ON x402_payments(date);
`;

export function ensureSchema(db = getDb()) {
  db.exec(SCHEMA);
  return db;
}
