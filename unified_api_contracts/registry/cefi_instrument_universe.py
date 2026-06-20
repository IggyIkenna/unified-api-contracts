"""CeFi instrument universe — curated base assets for CeFi venue filtering.

SSOT for which crypto assets the instruments-service tracks across CeFi venues.
Tardis/direct adapters filter to only return instruments where the base
asset is in this set. Curated set (~45 assets — top market-cap coins plus
operator-requested coverage incl. EigenLayer dust) covering the asset classes
the system needs while keeping scope manageable.

Includes FTT and LUNA (delisted) to test the system's handling of delistings —
they will appear with ``is_active=False`` and ``available_to`` set.
"""

from __future__ import annotations

# fmt: off

# Top coins by market cap + 2 delisted assets for delisting testing.
# Quote assets (USDT, USDC, USD, BTC, ETH) are not filtered — any quote is fine
# as long as the base is in this set.
CEFI_BASE_ASSET_UNIVERSE: frozenset[str] = frozenset({
    # --- Top 20 by market cap ---
    "BTC",      # Bitcoin
    "ETH",      # Ethereum
    "BNB",      # BNB Chain
    "SOL",      # Solana
    "XRP",      # Ripple
    "ADA",      # Cardano
    "DOGE",     # Dogecoin
    "AVAX",     # Avalanche
    "DOT",      # Polkadot
    "LINK",     # Chainlink
    "TRX",      # Tron
    "MATIC",    # Polygon
    "SHIB",     # Shiba Inu
    "LTC",      # Litecoin
    "UNI",      # Uniswap
    "ATOM",     # Cosmos
    "NEAR",     # NEAR Protocol
    "APT",      # Aptos
    "ARB",      # Arbitrum
    "OP",       # Optimism
    "HYPE",     # Hyperliquid
    "PEPE",     # Pepe
    # --- Added 2026-06-16 (operator: full requested CeFi coverage + EigenLayer rewards dust) ---
    "EIGEN",    # EigenLayer (rewards dust tracking)
    "AAVE",     # Aave
    "ALGO",     # Algorand
    "AXS",      # Axie Infinity
    "CHZ",      # Chiliz
    "COMP",     # Compound
    "DASH",     # Dash
    "ENJ",      # Enjin
    "EOS",      # EOS
    "FIL",      # Filecoin
    "GALA",     # Gala
    "ICP",      # Internet Computer
    "MANA",     # Decentraland
    "SAND",     # The Sandbox
    "THETA",    # Theta Network
    "XLM",      # Stellar
    "ZEC",      # Zcash
    # --- Stablecoins (as base in stablecoin pairs like USDT/USD) ---
    "USDT",     # Tether
    "USDC",     # USD Coin
    "DAI",      # MakerDAO DAI
    # --- Delisted / collapsed — for delisting testing ---
    "FTT",      # FTX Token — delisted Nov 2022 (exchange collapse)
    "LUNA",     # Terra Luna — delisted May 2022 (death spiral)
})

# Quote assets we accept. Only USD and major stablecoins — no cross pairs.
CEFI_ACCEPTED_QUOTE_ASSETS: frozenset[str] = frozenset({
    "USDT", "USDC", "USD",
})

# Options are only tracked for these underlyings. Everything else (SOL, USDC,
# BNB options on Deribit etc.) is filtered out to keep data volume manageable.
CEFI_OPTIONS_UNDERLYINGS: frozenset[str] = frozenset({
    "BTC",
    "ETH",
})

# Equity base assets for crypto-venue single-stock perps + tokenized stocks.
# These are the UNDERLYING real-equity tickers (as used by Databento DBEQ.BASIC),
# NOT the full crypto-venue symbol (e.g. META not METAUSDT). Each entry here
# indicates a family of crypto-venue instruments (e.g. Binance METAUSDT,
# OKX META-USDT-SWAP, Bybit METAUSDT) that track the real equity.
# Pre-IPO / no-real-twin symbols (SPACEX, etc.) are tracked separately in the
# crypto_equity_link module (STANDALONE_EQUITY_PERP_SYMBOLS).
# Operator-seeded 2026-06-20: OKX 17 US equity perps + Binance/Bybit reps.
CEFI_EQUITY_PERP_BASE_UNIVERSE: frozenset[str] = frozenset({
    # --- US equities (OKX 17-perp universe + Binance/Bybit verified coverage) ---
    "AAPL",     # Apple
    "TSLA",     # Tesla
    "AMZN",     # Amazon
    "MSFT",     # Microsoft
    "GOOGL",    # Alphabet (Google)
    "META",     # Meta Platforms (Facebook)
    "NVDA",     # NVIDIA
    "NFLX",     # Netflix
    "AMD",      # AMD
    "INTC",     # Intel
    "BABA",     # Alibaba
    "COIN",     # Coinbase
    "MSTR",     # MicroStrategy
    "PLTR",     # Palantir
    "GME",      # GameStop
    "AMC",      # AMC Entertainment
    "MARA",     # Marathon Digital
    # --- Korean equities (OKX confirmed) ---
    "005930",   # Samsung Electronics (KRX code)
    "000660",   # SK Hynix (KRX code)
    "005380",   # Hyundai Motor (KRX code)
})
# fmt: on
