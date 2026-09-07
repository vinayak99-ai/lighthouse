"""Direct port of server/src/starters.js -- keep the two in sync.

Starter grid shown on the empty chat screen -- one card per backend tool.
"""

STARTER_DOMAINS = [
    {"key": "stablecoins", "label": "Stablecoins", "icon": "\U0001F4B5", "example": "Chart USDT vs USDC supply over the last 90 days"},
    {"key": "defi_tvl", "label": "DeFi TVL", "icon": "\U0001F3DB️", "example": "Show TVL for Aave, Lido and EigenLayer this year"},
    {"key": "perpetuals", "label": "Perpetuals", "icon": "\U0001F4C8", "example": "Compare open interest across Hyperliquid, dYdX and GMX"},
    {"key": "prediction_markets", "label": "Prediction markets", "icon": "\U0001F3AF", "example": "Prediction market volume by platform, last 30 days"},
    {"key": "rwa", "label": "RWA", "icon": "\U0001F3E6", "example": "Tokenized RWA value by issuer since January"},
    {"key": "protocol_revenue", "label": "Protocol revenue", "icon": "\U0001F4B0", "example": "Ethereum vs Solana protocol revenue, last quarter"},
    {"key": "chain_activity", "label": "Chain activity", "icon": "\U0001F30D", "example": "Active addresses on Solana vs Base this year"},
    {"key": "staking", "label": "Staking", "icon": "\U0001F512", "example": "Staked ETH by provider over the last 6 months"},
    {"key": "nft", "label": "NFT volume", "icon": "\U0001F5BC️", "example": "Blur vs OpenSea volume, last 30 days"},
    {
        "key": "x402_agentic_payments",
        "label": "x402 Agentic Payments",
        "icon": "\U0001F916",
        "example": "x402 agentic payment volume by agent network",
        "hot": True,
    },
]
