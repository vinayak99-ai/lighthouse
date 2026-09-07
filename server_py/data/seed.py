"""Generates deterministic stub blockchain data and loads it into SQLite.

Not real chain data -- shaped to look plausible (trend + weekly seasonality
+ noise) so charts built on top of it have something realistic to show.
Same algorithm shape as server/src/data/seed.js (random walk with drift,
weekly dip, a soft floor, seeded per-entity), but uses Python's own
random.Random(seed_string) rather than porting the JS mulberry32 PRNG
bit-for-bit -- these are two independent servers with their own stub
datasets; "deterministic per entity" is the property that matters, not
byte-identical output between the Node and Python versions.
"""

import random
from datetime import date, timedelta

from .db import ensure_schema, get_db
from .entities import DOMAINS, END_DATE, START_DATE


def _date_range(start: str, end: str) -> list[str]:
    start_d = date.fromisoformat(start)
    end_d = date.fromisoformat(end)
    dates = []
    cur = start_d
    while cur <= end_d:
        dates.append(cur.isoformat())
        cur += timedelta(days=1)
    return dates


DATES = _date_range(START_DATE, END_DATE)


def series(entity_key: str, base: float, drift_pct: float, vol_pct: float, weekend_dip_pct: float = 0) -> list[dict]:
    """Random walk with drift, weekly seasonality, and a floor at 15% of base."""
    rng = random.Random(entity_key)
    out = []
    value = base
    for d in DATES:
        day_of_week = date.fromisoformat(d).weekday()  # Monday=0 .. Sunday=6
        is_weekend = day_of_week >= 5  # Saturday, Sunday
        drift = 1 + drift_pct / 100 / 30 + (rng.random() - 0.48) * (vol_pct / 100)
        value = max(value * drift, base * 0.15)
        seasonal = (1 - weekend_dip_pct / 100) if is_weekend else 1
        out.append({"date": d, "value": value * seasonal})
    return out


def _replace_rows(table: str, columns: list[str], rows: list[dict]) -> None:
    """Clear + insert as ONE atomic transaction -- same reasoning as
    seed.js's insertRows: a concurrent seedAll() call from another process
    sharing this SQLite file must not be able to interleave its own DELETE
    between this call's DELETE and INSERT (which would double the table).
    """
    conn = get_db()
    placeholders = ", ".join("?" for _ in columns)
    with conn:  # sqlite3's context manager wraps this in one transaction
        conn.execute(f"DELETE FROM {table}")
        conn.executemany(
            f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})",
            [tuple(row[c] for c in columns) for row in rows],
        )


def _seed_stablecoins():
    bases = {"USDT": 118_000_000_000, "USDC": 34_000_000_000, "DAI": 5_300_000_000, "FDUSD": 3_200_000_000, "PYUSD": 900_000_000, "USDe": 5_800_000_000}
    drift = {"USDT": 0.9, "USDC": 1.6, "DAI": -0.2, "FDUSD": 0.3, "PYUSD": 2.4, "USDe": 3.1}
    chain_weight = {"Ethereum": 0.55, "Tron": 0.3, "Solana": 0.08, "Base": 0.04, "Arbitrum": 0.03}
    rows = []
    for issuer in DOMAINS["stablecoins"]["entities"]:
        for chain in DOMAINS["stablecoins"]["chains"]:
            for point in series(f"stable:{issuer}:{chain}", bases[issuer] * chain_weight[chain], drift[issuer], 1.1):
                rows.append({"date": point["date"], "issuer": issuer, "chain": chain, "supply_usd": round(point["value"])})
    _replace_rows("stablecoin_supply", ["date", "issuer", "chain", "supply_usd"], rows)


def _seed_defi_tvl():
    bases = {"Aave": 18_000_000_000, "Lido": 24_000_000_000, "EigenLayer": 11_000_000_000, "Uniswap": 5_200_000_000, "MakerDAO": 6_800_000_000, "Curve": 2_100_000_000}
    drift = {"Aave": 1.2, "Lido": 0.6, "EigenLayer": 2.8, "Uniswap": 0.8, "MakerDAO": -0.3, "Curve": 0.4}
    chain_weight = {"Ethereum": 0.62, "Arbitrum": 0.15, "Base": 0.12, "Solana": 0.07, "Optimism": 0.04}
    rows = []
    for protocol in DOMAINS["defi_tvl"]["entities"]:
        for chain in DOMAINS["defi_tvl"]["chains"]:
            for point in series(f"tvl:{protocol}:{chain}", bases[protocol] * chain_weight[chain], drift[protocol], 1.8):
                rows.append({"date": point["date"], "protocol": protocol, "chain": chain, "tvl_usd": round(point["value"])})
    _replace_rows("defi_tvl", ["date", "protocol", "chain", "tvl_usd"], rows)


def _seed_perpetuals():
    bases = {
        "Hyperliquid": {"oi": 3_800_000_000, "vol": 6_200_000_000},
        "dYdX": {"oi": 420_000_000, "vol": 780_000_000},
        "GMX": {"oi": 310_000_000, "vol": 540_000_000},
        "Binance Futures": {"oi": 18_000_000_000, "vol": 42_000_000_000},
        "Bybit": {"oi": 9_200_000_000, "vol": 21_000_000_000},
    }
    drift = {"Hyperliquid": 4.2, "dYdX": -0.8, "GMX": 0.5, "Binance Futures": 0.6, "Bybit": 0.9}
    rows = []
    for exchange in DOMAINS["perpetuals"]["entities"]:
        oi_series = series(f"perp-oi:{exchange}", bases[exchange]["oi"], drift[exchange], 2.5)
        vol_series = series(f"perp-vol:{exchange}", bases[exchange]["vol"], drift[exchange] * 0.6, 6, weekend_dip_pct=22)
        for oi_pt, vol_pt in zip(oi_series, vol_series):
            rows.append({"date": oi_pt["date"], "exchange": exchange, "open_interest_usd": round(oi_pt["value"]), "volume_usd": round(vol_pt["value"])})
    _replace_rows("perp_markets", ["date", "exchange", "open_interest_usd", "volume_usd"], rows)


def _seed_prediction_markets():
    bases = {"Polymarket": 42_000_000, "Kalshi": 21_000_000, "Manifold": 900_000}
    drift = {"Polymarket": 1.8, "Kalshi": 3.4, "Manifold": 0.4}
    cat_weight = {"Politics": 0.32, "Crypto": 0.24, "Sports": 0.28, "Economics": 0.1, "Culture": 0.06}
    rows = []
    for platform in DOMAINS["prediction_markets"]["entities"]:
        for category in DOMAINS["prediction_markets"]["categories"]:
            for point in series(f"pm:{platform}:{category}", bases[platform] * cat_weight[category], drift[platform], 9, weekend_dip_pct=12):
                rows.append({"date": point["date"], "platform": platform, "category": category, "volume_usd": round(point["value"])})
    _replace_rows("prediction_markets", ["date", "platform", "category", "volume_usd"], rows)


def _seed_rwa():
    bases = {"BlackRock BUIDL": 2_400_000_000, "Ondo Finance": 1_400_000_000, "Franklin Templeton": 780_000_000, "Superstate": 420_000_000, "Hashnote": 1_300_000_000}
    drift = {"BlackRock BUIDL": 3.6, "Ondo Finance": 4.1, "Franklin Templeton": 2.2, "Superstate": 3.8, "Hashnote": 1.6}
    type_for = {"BlackRock BUIDL": "Treasuries", "Ondo Finance": "Treasuries", "Franklin Templeton": "Money Market", "Superstate": "Treasuries", "Hashnote": "Private Credit"}
    rows = []
    for issuer in DOMAINS["rwa"]["entities"]:
        for point in series(f"rwa:{issuer}", bases[issuer], drift[issuer], 1.4):
            rows.append({"date": point["date"], "asset_type": type_for[issuer], "issuer": issuer, "value_usd": round(point["value"])})
    _replace_rows("rwa_value", ["date", "asset_type", "issuer", "value_usd"], rows)


def _seed_protocol_revenue():
    bases = {"Ethereum": 2_800_000, "Solana": 1_900_000, "Tron": 2_100_000, "Base": 780_000, "Arbitrum": 340_000}
    drift = {"Ethereum": -0.4, "Solana": 2.6, "Tron": 0.3, "Base": 3.2, "Arbitrum": 0.8}
    rows = []
    for protocol in DOMAINS["protocol_revenue"]["entities"]:
        for point in series(f"rev-fees:{protocol}", bases[protocol], drift[protocol], 5, weekend_dip_pct=15):
            rows.append({
                "date": point["date"],
                "protocol": protocol,
                "chain": protocol,
                "revenue_usd": round(point["value"] * 0.62),
                "fees_usd": round(point["value"]),
            })
    _replace_rows("protocol_revenue", ["date", "protocol", "chain", "revenue_usd", "fees_usd"], rows)


def _seed_chain_activity():
    bases = {
        "Ethereum": {"addr": 420_000, "tx": 1_150_000},
        "Solana": {"addr": 1_450_000, "tx": 42_000_000},
        "Base": {"addr": 680_000, "tx": 8_200_000},
        "Arbitrum": {"addr": 310_000, "tx": 2_600_000},
        "Bitcoin": {"addr": 940_000, "tx": 480_000},
    }
    drift = {"Ethereum": 0.2, "Solana": 1.9, "Base": 2.8, "Arbitrum": 0.6, "Bitcoin": -0.1}
    rows = []
    for chain in DOMAINS["chain_activity"]["entities"]:
        addr_series = series(f"addr:{chain}", bases[chain]["addr"], drift[chain], 2.2, weekend_dip_pct=8)
        tx_series = series(f"tx:{chain}", bases[chain]["tx"], drift[chain] * 1.1, 3, weekend_dip_pct=10)
        for addr_pt, tx_pt in zip(addr_series, tx_series):
            rows.append({"date": addr_pt["date"], "chain": chain, "active_addresses": round(addr_pt["value"]), "transactions": round(tx_pt["value"])})
    _replace_rows("chain_activity", ["date", "chain", "active_addresses", "transactions"], rows)


def _seed_staking():
    import math

    bases = {
        "Lido": {"staked": 9_800_000, "apr": 3.1},
        "Coinbase": {"staked": 3_900_000, "apr": 2.7},
        "Rocket Pool": {"staked": 1_100_000, "apr": 3.3},
        "EigenLayer": {"staked": 5_200_000, "apr": 4.6},
        "Binance": {"staked": 2_600_000, "apr": 2.9},
    }
    drift = {"Lido": 0.4, "Coinbase": 0.6, "Rocket Pool": 0.3, "EigenLayer": 2.9, "Binance": 0.5}
    rows = []
    for provider in DOMAINS["staking"]["entities"]:
        staked_series = series(f"stake:{provider}", bases[provider]["staked"], drift[provider], 0.6)
        rng = random.Random(f"apr:{provider}")
        for i, point in enumerate(staked_series):
            apr = bases[provider]["apr"] + math.sin(i / 21) * 0.25 + (rng.random() - 0.5) * 0.15
            rows.append({"date": point["date"], "provider": provider, "staked_eth": round(point["value"]), "apr_pct": round(apr, 2)})
    _replace_rows("staking", ["date", "provider", "staked_eth", "apr_pct"], rows)


def _seed_nft_volume():
    bases = {"Blur": 32_000_000, "OpenSea": 18_000_000, "Magic Eden": 9_000_000}
    drift = {"Blur": -1.8, "OpenSea": -0.6, "Magic Eden": 2.4}
    rows = []
    for marketplace in DOMAINS["nft"]["entities"]:
        vol_series = series(f"nft-vol:{marketplace}", bases[marketplace], drift[marketplace], 8, weekend_dip_pct=5)
        sales_series = series(f"nft-sales:{marketplace}", bases[marketplace] / 900, drift[marketplace] * 0.8, 7)
        for vol_pt, sales_pt in zip(vol_series, sales_series):
            rows.append({"date": vol_pt["date"], "marketplace": marketplace, "volume_usd": round(vol_pt["value"]), "sales_count": round(sales_pt["value"])})
    _replace_rows("nft_volume", ["date", "marketplace", "volume_usd", "sales_count"], rows)


def _seed_x402_payments():
    bases = {"Coinbase": 4_200_000, "Circle": 2_600_000, "Skyfire": 780_000}
    drift = {"Coinbase": 9.5, "Circle": 8.2, "Skyfire": 12.5}
    net_weight = {"Autonomous Trading": 0.3, "AI Shopping Agents": 0.28, "Data & API Access": 0.24, "Agent-to-Agent Settlement": 0.18}
    rows = []
    for facilitator in DOMAINS["x402_agentic_payments"]["entities"]:
        for agent_network in DOMAINS["x402_agentic_payments"]["agent_networks"]:
            vol_series = series(f"x402-vol:{facilitator}:{agent_network}", bases[facilitator] * net_weight[agent_network], drift[facilitator], 6)
            tx_series = series(f"x402-tx:{facilitator}:{agent_network}", (bases[facilitator] * net_weight[agent_network]) / 18, drift[facilitator] * 0.9, 6)
            for vol_pt, tx_pt in zip(vol_series, tx_series):
                rows.append({
                    "date": vol_pt["date"],
                    "facilitator": facilitator,
                    "agent_network": agent_network,
                    "volume_usd": round(vol_pt["value"]),
                    "tx_count": round(tx_pt["value"]),
                })
    _replace_rows("x402_payments", ["date", "facilitator", "agent_network", "volume_usd", "tx_count"], rows)


def seed_all():
    ensure_schema(get_db())
    _seed_stablecoins()
    _seed_defi_tvl()
    _seed_perpetuals()
    _seed_prediction_markets()
    _seed_rwa()
    _seed_protocol_revenue()
    _seed_chain_activity()
    _seed_staking()
    _seed_nft_volume()
    _seed_x402_payments()
    return get_db()


if __name__ == "__main__":
    db = seed_all()
    tables = [
        "stablecoin_supply", "defi_tvl", "perp_markets", "prediction_markets", "rwa_value",
        "protocol_revenue", "chain_activity", "staking", "nft_volume", "x402_payments",
    ]
    print("Seeded stub blockchain dataset:")
    for t in tables:
        count = db.execute(f"SELECT COUNT(*) c FROM {t}").fetchone()["c"]
        print(f"{t}: {count} rows")
