"""CeFi instrument universe — curated base assets for CeFi venue filtering.

SSOT for which crypto assets the instruments-service tracks across CeFi venues.
URDI Tardis/direct adapters filter to only return instruments where the base
asset is in this set. Keeps scope manageable (~20 top coins by market cap)
while covering all asset classes the system needs.

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
# fmt: on
