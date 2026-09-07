"""SQLite connection + schema. Direct port of server/src/data/db.js."""

import sqlite3
from pathlib import Path
from threading import Lock

DB_PATH = Path(__file__).parent / "lighthouse.sqlite"

_conn: sqlite3.Connection | None = None
_lock = Lock()

SCHEMA = """
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
"""


def get_db() -> sqlite3.Connection:
    """A single shared connection, like the Node version's getDb() singleton.

    check_same_thread=False because FastAPI's request handlers can run this
    on different threads (uvicorn's default sync-route threadpool); we're
    doing short-lived reads, not concurrent writes, so this is safe.
    """
    global _conn
    with _lock:
        if _conn is None:
            _conn = sqlite3.connect(DB_PATH, check_same_thread=False)
            _conn.row_factory = sqlite3.Row
            _conn.execute("PRAGMA journal_mode = WAL")
            # Same reasoning as db.js: this file is shared by multiple
            # processes in dev (the server, the seed script, tests) --
            # without a busy timeout a concurrent writer gets SQLITE_BUSY
            # immediately instead of waiting its turn.
            _conn.execute("PRAGMA busy_timeout = 5000")
        return _conn


def ensure_schema(conn: sqlite3.Connection | None = None) -> sqlite3.Connection:
    conn = conn or get_db()
    conn.executescript(SCHEMA)
    return conn
