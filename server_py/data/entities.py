"""Reference lists of entities for each stubbed data domain.

Shared by the seed generator (data realism) and the tool layer (arg
validation). Direct port of server/src/data/entities.js -- keep the two in
sync if you change one.
"""

DOMAINS = {
    "stablecoins": {
        "table": "stablecoin_supply",
        "entity_col": "issuer",
        "entities": ["USDT", "USDC", "DAI", "FDUSD", "PYUSD", "USDe"],
        "chains": ["Ethereum", "Tron", "Solana", "Base", "Arbitrum"],
    },
    "defi_tvl": {
        "table": "defi_tvl",
        "entity_col": "protocol",
        "entities": ["Aave", "Lido", "EigenLayer", "Uniswap", "MakerDAO", "Curve"],
        "chains": ["Ethereum", "Arbitrum", "Base", "Solana", "Optimism"],
    },
    "perpetuals": {
        "table": "perp_markets",
        "entity_col": "exchange",
        "entities": ["Hyperliquid", "dYdX", "GMX", "Binance Futures", "Bybit"],
    },
    "prediction_markets": {
        "table": "prediction_markets",
        "entity_col": "platform",
        "entities": ["Polymarket", "Kalshi", "Manifold"],
        "categories": ["Politics", "Crypto", "Sports", "Economics", "Culture"],
    },
    "rwa": {
        "table": "rwa_value",
        "entity_col": "issuer",
        "entities": ["BlackRock BUIDL", "Ondo Finance", "Franklin Templeton", "Superstate", "Hashnote"],
        "asset_types": ["Treasuries", "Private Credit", "Commodities", "Money Market"],
    },
    "protocol_revenue": {
        "table": "protocol_revenue",
        "entity_col": "protocol",
        "entities": ["Ethereum", "Solana", "Tron", "Base", "Arbitrum"],
        "chains": ["Ethereum", "Solana", "Tron", "Base", "Arbitrum"],
    },
    "chain_activity": {
        "table": "chain_activity",
        "entity_col": "chain",
        "entities": ["Ethereum", "Solana", "Base", "Arbitrum", "Bitcoin"],
    },
    "staking": {
        "table": "staking",
        "entity_col": "provider",
        "entities": ["Lido", "Coinbase", "Rocket Pool", "EigenLayer", "Binance"],
    },
    "nft": {
        "table": "nft_volume",
        "entity_col": "marketplace",
        "entities": ["Blur", "OpenSea", "Magic Eden"],
    },
    "x402_agentic_payments": {
        "table": "x402_payments",
        "entity_col": "facilitator",
        "entities": ["Coinbase", "Circle", "Skyfire"],
        "agent_networks": ["Autonomous Trading", "AI Shopping Agents", "Data & API Access", "Agent-to-Agent Settlement"],
    },
}

START_DATE = "2026-01-01"
END_DATE = "2026-08-22"
