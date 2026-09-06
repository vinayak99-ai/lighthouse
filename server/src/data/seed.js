// Generates deterministic stub blockchain data and loads it into SQLite.
// Not real chain data -- shaped to look plausible (trend + weekly seasonality + noise)
// so charts built on top of it have something realistic to show.

import { getDb, ensureSchema } from "./db.js";
import { DOMAINS, START_DATE, END_DATE } from "./entities.js";

function mulberry32(seed) {
  let a = seed;
  return function () {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function hashSeed(str) {
  let h = 0;
  for (let i = 0; i < str.length; i++) {
    h = (Math.imul(h, 31) + str.charCodeAt(i)) | 0;
  }
  return h;
}

function dateRange(start, end) {
  const dates = [];
  const cur = new Date(start + "T00:00:00Z");
  const stop = new Date(end + "T00:00:00Z");
  while (cur <= stop) {
    dates.push(cur.toISOString().slice(0, 10));
    cur.setUTCDate(cur.getUTCDate() + 1);
  }
  return dates;
}

const DATES = dateRange(START_DATE, END_DATE);

// Random walk with drift, weekly seasonality and a soft floor, seeded per-entity.
function series(entityKey, { base, driftPct, volPct, weekendDipPct = 0 }) {
  const rng = mulberry32(hashSeed(entityKey));
  const out = [];
  let value = base;
  DATES.forEach((date, i) => {
    const dayOfWeek = new Date(date + "T00:00:00Z").getUTCDay();
    const isWeekend = dayOfWeek === 0 || dayOfWeek === 6;
    const drift = 1 + driftPct / 100 / 30 + (rng() - 0.48) * (volPct / 100);
    value = Math.max(value * drift, base * 0.15);
    const seasonal = isWeekend ? 1 - weekendDipPct / 100 : 1;
    out.push({ date, value: value * seasonal });
  });
  return out;
}

// Clear + insert as ONE atomic transaction. Two separate autocommit
// statements (DELETE, then INSERT) left a window where a second, concurrent
// seedAll() call -- e.g. a dev server's boot-time auto-seed racing a test
// run's seedAll() against the same on-disk file -- could sneak its own
// DELETE in between this call's DELETE and INSERT, so both inserts survived
// and doubled the table. Wrapping both statements in one transaction makes
// SQLite serialize concurrent callers instead of interleaving them.
function insertRows(db, table, columns, rows) {
  const placeholders = columns.map(() => "?").join(", ");
  const stmt = db.prepare(`INSERT INTO ${table} (${columns.join(", ")}) VALUES (${placeholders})`);
  const replace = db.transaction((rows) => {
    db.prepare(`DELETE FROM ${table}`).run();
    for (const row of rows) stmt.run(...columns.map((c) => row[c]));
  });
  replace(rows);
}


function seedStablecoins(db) {
  const bases = { USDT: 118000000000, USDC: 34000000000, DAI: 5300000000, FDUSD: 3200000000, PYUSD: 900000000, USDe: 5800000000 };
  const drift = { USDT: 0.9, USDC: 1.6, DAI: -0.2, FDUSD: 0.3, PYUSD: 2.4, USDe: 3.1 };
  const rows = [];
  for (const issuer of DOMAINS.stablecoins.entities) {
    for (const chain of DOMAINS.stablecoins.chains) {
      const chainWeight = { Ethereum: 0.55, Tron: 0.3, Solana: 0.08, Base: 0.04, Arbitrum: 0.03 }[chain];
      const s = series(`stable:${issuer}:${chain}`, { base: bases[issuer] * chainWeight, driftPct: drift[issuer], volPct: 1.1 });
      s.forEach(({ date, value }) => rows.push({ date, issuer, chain, supply_usd: Math.round(value) }));
    }
  }
  insertRows(db, "stablecoin_supply", ["date", "issuer", "chain", "supply_usd"], rows);
}

function seedDefiTvl(db) {
  const bases = { Aave: 18000000000, Lido: 24000000000, EigenLayer: 11000000000, Uniswap: 5200000000, MakerDAO: 6800000000, Curve: 2100000000 };
  const drift = { Aave: 1.2, Lido: 0.6, EigenLayer: 2.8, Uniswap: 0.8, MakerDAO: -0.3, Curve: 0.4 };
  const chainWeights = { Ethereum: 0.62, Arbitrum: 0.15, Base: 0.12, Solana: 0.07, Optimism: 0.04 };
  const rows = [];
  for (const protocol of DOMAINS.defi_tvl.entities) {
    for (const chain of DOMAINS.defi_tvl.chains) {
      const s = series(`tvl:${protocol}:${chain}`, { base: bases[protocol] * chainWeights[chain], driftPct: drift[protocol], volPct: 1.8 });
      s.forEach(({ date, value }) => rows.push({ date, protocol, chain, tvl_usd: Math.round(value) }));
    }
  }
  insertRows(db, "defi_tvl", ["date", "protocol", "chain", "tvl_usd"], rows);
}

function seedPerpetuals(db) {
  const bases = {
    Hyperliquid: { oi: 3800000000, vol: 6200000000 },
    dYdX: { oi: 420000000, vol: 780000000 },
    GMX: { oi: 310000000, vol: 540000000 },
    "Binance Futures": { oi: 18000000000, vol: 42000000000 },
    Bybit: { oi: 9200000000, vol: 21000000000 },
  };
  const drift = { Hyperliquid: 4.2, dYdX: -0.8, GMX: 0.5, "Binance Futures": 0.6, Bybit: 0.9 };
  const rows = [];
  for (const exchange of DOMAINS.perpetuals.entities) {
    const oiSeries = series(`perp-oi:${exchange}`, { base: bases[exchange].oi, driftPct: drift[exchange], volPct: 2.5 });
    const volSeries = series(`perp-vol:${exchange}`, { base: bases[exchange].vol, driftPct: drift[exchange] * 0.6, volPct: 6, weekendDipPct: 22 });
    for (let i = 0; i < oiSeries.length; i++) {
      rows.push({ date: oiSeries[i].date, exchange, open_interest_usd: Math.round(oiSeries[i].value), volume_usd: Math.round(volSeries[i].value) });
    }
  }
  insertRows(db, "perp_markets", ["date", "exchange", "open_interest_usd", "volume_usd"], rows);
}

function seedPredictionMarkets(db) {
  const bases = { Polymarket: 42000000, Kalshi: 21000000, Manifold: 900000 };
  const drift = { Polymarket: 1.8, Kalshi: 3.4, Manifold: 0.4 };
  const catWeights = { Politics: 0.32, Crypto: 0.24, Sports: 0.28, Economics: 0.1, Culture: 0.06 };
  const rows = [];
  for (const platform of DOMAINS.prediction_markets.entities) {
    for (const category of DOMAINS.prediction_markets.categories) {
      const s = series(`pm:${platform}:${category}`, {
        base: bases[platform] * catWeights[category],
        driftPct: drift[platform],
        volPct: 9,
        weekendDipPct: 12,
      });
      s.forEach(({ date, value }) => rows.push({ date, platform, category, volume_usd: Math.round(value) }));
    }
  }
  insertRows(db, "prediction_markets", ["date", "platform", "category", "volume_usd"], rows);
}

function seedRwa(db) {
  const bases = { "BlackRock BUIDL": 2400000000, "Ondo Finance": 1400000000, "Franklin Templeton": 780000000, Superstate: 420000000, Hashnote: 1300000000 };
  const drift = { "BlackRock BUIDL": 3.6, "Ondo Finance": 4.1, "Franklin Templeton": 2.2, Superstate: 3.8, Hashnote: 1.6 };
  const typeFor = { "BlackRock BUIDL": "Treasuries", "Ondo Finance": "Treasuries", "Franklin Templeton": "Money Market", Superstate: "Treasuries", Hashnote: "Private Credit" };
  const rows = [];
  for (const issuer of DOMAINS.rwa.entities) {
    const s = series(`rwa:${issuer}`, { base: bases[issuer], driftPct: drift[issuer], volPct: 1.4 });
    s.forEach(({ date, value }) => rows.push({ date, asset_type: typeFor[issuer], issuer, value_usd: Math.round(value) }));
  }
  insertRows(db, "rwa_value", ["date", "asset_type", "issuer", "value_usd"], rows);
}

function seedProtocolRevenue(db) {
  const bases = { Ethereum: 2800000, Solana: 1900000, Tron: 2100000, Base: 780000, Arbitrum: 340000 };
  const drift = { Ethereum: -0.4, Solana: 2.6, Tron: 0.3, Base: 3.2, Arbitrum: 0.8 };
  const rows = [];
  for (const protocol of DOMAINS.protocol_revenue.entities) {
    const feesSeries = series(`rev-fees:${protocol}`, { base: bases[protocol], driftPct: drift[protocol], volPct: 5, weekendDipPct: 15 });
    feesSeries.forEach(({ date, value }) => {
      rows.push({ date, protocol, chain: protocol, revenue_usd: Math.round(value * 0.62), fees_usd: Math.round(value) });
    });
  }
  insertRows(db, "protocol_revenue", ["date", "protocol", "chain", "revenue_usd", "fees_usd"], rows);
}

function seedChainActivity(db) {
  const bases = {
    Ethereum: { addr: 420000, tx: 1150000 },
    Solana: { addr: 1450000, tx: 42000000 },
    Base: { addr: 680000, tx: 8200000 },
    Arbitrum: { addr: 310000, tx: 2600000 },
    Bitcoin: { addr: 940000, tx: 480000 },
  };
  const drift = { Ethereum: 0.2, Solana: 1.9, Base: 2.8, Arbitrum: 0.6, Bitcoin: -0.1 };
  const rows = [];
  for (const chain of DOMAINS.chain_activity.entities) {
    const addrSeries = series(`addr:${chain}`, { base: bases[chain].addr, driftPct: drift[chain], volPct: 2.2, weekendDipPct: 8 });
    const txSeries = series(`tx:${chain}`, { base: bases[chain].tx, driftPct: drift[chain] * 1.1, volPct: 3, weekendDipPct: 10 });
    for (let i = 0; i < addrSeries.length; i++) {
      rows.push({ date: addrSeries[i].date, chain, active_addresses: Math.round(addrSeries[i].value), transactions: Math.round(txSeries[i].value) });
    }
  }
  insertRows(db, "chain_activity", ["date", "chain", "active_addresses", "transactions"], rows);
}

function seedStaking(db) {
  const bases = {
    Lido: { staked: 9800000, apr: 3.1 },
    Coinbase: { staked: 3900000, apr: 2.7 },
    "Rocket Pool": { staked: 1100000, apr: 3.3 },
    EigenLayer: { staked: 5200000, apr: 4.6 },
    Binance: { staked: 2600000, apr: 2.9 },
  };
  const drift = { Lido: 0.4, Coinbase: 0.6, "Rocket Pool": 0.3, EigenLayer: 2.9, Binance: 0.5 };
  const rows = [];
  for (const provider of DOMAINS.staking.entities) {
    const stakedSeries = series(`stake:${provider}`, { base: bases[provider].staked, driftPct: drift[provider], volPct: 0.6 });
    const rng = mulberry32(hashSeed(`apr:${provider}`));
    stakedSeries.forEach(({ date, value }, i) => {
      const apr = bases[provider].apr + Math.sin(i / 21) * 0.25 + (rng() - 0.5) * 0.15;
      rows.push({ date, provider, staked_eth: Math.round(value), apr_pct: Math.round(apr * 100) / 100 });
    });
  }
  insertRows(db, "staking", ["date", "provider", "staked_eth", "apr_pct"], rows);
}

function seedNftVolume(db) {
  const bases = { Blur: 32000000, OpenSea: 18000000, "Magic Eden": 9000000 };
  const drift = { Blur: -1.8, OpenSea: -0.6, "Magic Eden": 2.4 };
  const rows = [];
  for (const marketplace of DOMAINS.nft.entities) {
    const volSeries = series(`nft-vol:${marketplace}`, { base: bases[marketplace], driftPct: drift[marketplace], volPct: 8, weekendDipPct: 5 });
    const salesSeries = series(`nft-sales:${marketplace}`, { base: bases[marketplace] / 900, driftPct: drift[marketplace] * 0.8, volPct: 7 });
    for (let i = 0; i < volSeries.length; i++) {
      rows.push({ date: volSeries[i].date, marketplace, volume_usd: Math.round(volSeries[i].value), sales_count: Math.round(salesSeries[i].value) });
    }
  }
  insertRows(db, "nft_volume", ["date", "marketplace", "volume_usd", "sales_count"], rows);
}

function seedX402Payments(db) {
  const bases = { Coinbase: 4200000, Circle: 2600000, Skyfire: 780000 };
  const drift = { Coinbase: 9.5, Circle: 8.2, Skyfire: 12.5 };
  const netWeights = { "Autonomous Trading": 0.3, "AI Shopping Agents": 0.28, "Data & API Access": 0.24, "Agent-to-Agent Settlement": 0.18 };
  const rows = [];
  for (const facilitator of DOMAINS.x402_agentic_payments.entities) {
    for (const agentNetwork of DOMAINS.x402_agentic_payments.agentNetworks) {
      const volSeries = series(`x402-vol:${facilitator}:${agentNetwork}`, {
        base: bases[facilitator] * netWeights[agentNetwork],
        driftPct: drift[facilitator],
        volPct: 6,
      });
      const txSeries = series(`x402-tx:${facilitator}:${agentNetwork}`, {
        base: (bases[facilitator] * netWeights[agentNetwork]) / 18,
        driftPct: drift[facilitator] * 0.9,
        volPct: 6,
      });
      for (let i = 0; i < volSeries.length; i++) {
        rows.push({
          date: volSeries[i].date,
          facilitator,
          agent_network: agentNetwork,
          volume_usd: Math.round(volSeries[i].value),
          tx_count: Math.round(txSeries[i].value),
        });
      }
    }
  }
  insertRows(db, "x402_payments", ["date", "facilitator", "agent_network", "volume_usd", "tx_count"], rows);
}

export function seedAll() {
  const db = ensureSchema(getDb());
  seedStablecoins(db);
  seedDefiTvl(db);
  seedPerpetuals(db);
  seedPredictionMarkets(db);
  seedRwa(db);
  seedProtocolRevenue(db);
  seedChainActivity(db);
  seedStaking(db);
  seedNftVolume(db);
  seedX402Payments(db);
  return db;
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const db = seedAll();
  const counts = [
    "stablecoin_supply",
    "defi_tvl",
    "perp_markets",
    "prediction_markets",
    "rwa_value",
    "protocol_revenue",
    "chain_activity",
    "staking",
    "nft_volume",
    "x402_payments",
  ].map((t) => `${t}: ${db.prepare(`SELECT COUNT(*) c FROM ${t}`).get().c} rows`);
  console.log("Seeded stub blockchain dataset:\n" + counts.join("\n"));
}
