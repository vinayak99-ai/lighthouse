// Reference lists of entities for each stubbed data domain.
// Shared by the seed generator (data realism) and the tool layer (arg validation).

export const DOMAINS = {
  stablecoins: {
    table: "stablecoin_supply",
    entityCol: "issuer",
    entities: ["USDT", "USDC", "DAI", "FDUSD", "PYUSD", "USDe"],
    chains: ["Ethereum", "Tron", "Solana", "Base", "Arbitrum"],
  },
  defi_tvl: {
    table: "defi_tvl",
    entityCol: "protocol",
    entities: ["Aave", "Lido", "EigenLayer", "Uniswap", "MakerDAO", "Curve"],
    chains: ["Ethereum", "Arbitrum", "Base", "Solana", "Optimism"],
  },
  perpetuals: {
    table: "perp_markets",
    entityCol: "exchange",
    entities: ["Hyperliquid", "dYdX", "GMX", "Binance Futures", "Bybit"],
  },
  prediction_markets: {
    table: "prediction_markets",
    entityCol: "platform",
    entities: ["Polymarket", "Kalshi", "Manifold"],
    categories: ["Politics", "Crypto", "Sports", "Economics", "Culture"],
  },
  rwa: {
    table: "rwa_value",
    entityCol: "issuer",
    entities: ["BlackRock BUIDL", "Ondo Finance", "Franklin Templeton", "Superstate", "Hashnote"],
    assetTypes: ["Treasuries", "Private Credit", "Commodities", "Money Market"],
  },
  protocol_revenue: {
    table: "protocol_revenue",
    entityCol: "protocol",
    entities: ["Ethereum", "Solana", "Tron", "Base", "Arbitrum"],
    chains: ["Ethereum", "Solana", "Tron", "Base", "Arbitrum"],
  },
  chain_activity: {
    table: "chain_activity",
    entityCol: "chain",
    entities: ["Ethereum", "Solana", "Base", "Arbitrum", "Bitcoin"],
  },
  staking: {
    table: "staking",
    entityCol: "provider",
    entities: ["Lido", "Coinbase", "Rocket Pool", "EigenLayer", "Binance"],
  },
  nft: {
    table: "nft_volume",
    entityCol: "marketplace",
    entities: ["Blur", "OpenSea", "Magic Eden"],
  },
  x402_agentic_payments: {
    table: "x402_payments",
    entityCol: "facilitator",
    entities: ["Coinbase", "Circle", "Skyfire"],
    agentNetworks: ["Autonomous Trading", "AI Shopping Agents", "Data & API Access", "Agent-to-Agent Settlement"],
  },
};

export const START_DATE = "2026-01-01";
export const END_DATE = "2026-08-22";
