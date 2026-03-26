"""DeFi major asset symbols — SSOT for instrument relevance filtering.

Used by URDI DEX adapters to filter pools at query time (only return pools
where both base AND quote are in this set for DEXes, or base for lending).

This is the canonical default. instruments-service config_reloaders can
override via cloud ConfigStore (hot-reloadable), but URDI adapters use this
as the built-in filter so they never return irrelevant instruments.

Mirrors UCI InstrumentDomainConfig.defi_major_assets default — kept in sync
manually. If you add an asset here, add it to UCI too.
"""

from __future__ import annotations

# fmt: off
DEFI_MAJOR_ASSET_SYMBOLS: frozenset[str] = frozenset({
    # ETH and liquid staking/restaking derivatives
    "ETH", "WETH", "STETH", "WSTETH", "CBETH", "RETH", "WEETH", "EETH",
    "SFRXETH", "FRXETH", "OETH", "OSETH", "SWETH", "ETHX", "METH",
    "EZETH", "RSETH", "PUFETH", "ANKRETH",
    # BTC and wrapped variants
    "BTC", "WBTC", "TBTC", "CBBTC", "LBTC",
    # Major stablecoins
    "USDT", "USDC", "DAI", "FRAX", "USDE", "SUSDE", "GHO", "CRVUSD",
    "LUSD", "PYUSD", "EURC", "SUSD", "TUSD", "USDP",
    # Major DeFi governance / Aave collateral
    "AAVE", "LINK", "UNI", "MKR", "CRV", "SNX", "BAL", "LDO", "RPL",
    "COMP", "YFI", "SUSHI", "1INCH", "FXS",
    # Other liquid assets on Aave
    "SOL", "MATIC", "WMATIC",
})
# fmt: on

# DEX keyword detection — venues containing these are treated as DEX pools
# where BOTH base and quote must be in the whitelist
DEX_VENUE_KEYWORDS: frozenset[str] = frozenset({"UNISWAP", "BALANCER", "CURVE"})
