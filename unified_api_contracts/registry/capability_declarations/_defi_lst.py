"""LST / LRT genesis dates + venue-to-token mapping.

SSOT for liquid-staking-token launch dates on the chains the lst-rates
collector covers. Used by:

* MTDS lst-rates collector — short-circuits eth_calls before genesis
  instead of issuing reverts.
* deployment-api data-status — clamps expected-coverage start so the UI
  doesn't flag pre-launch dates as "missing".

Dates are sourced from project docs / Etherscan ``getContractCreation``
and represent the first day a noon-UTC rate query can succeed.
"""

from __future__ import annotations

# Per-token mainnet genesis (Ethereum for ETH-family, Solana for SOL-family).
LST_TOKEN_GENESIS: dict[str, str] = {
    # ETH-family — Ethereum mainnet
    "stETH": "2020-12-19",  # Lido genesis
    "wstETH": "2022-02-19",  # wstETH wrapper
    "rETH": "2021-11-08",  # Rocket Pool atlas
    "cbETH": "2022-08-26",  # Coinbase Wrapped Staked ETH
    "sUSDe": "2024-01-22",  # Ethena staked USDe
    "sDAI": "2023-08-07",  # MakerDAO sDAI / DSR vault
    "mETH": "2023-10-06",  # Mantle LSP launch
    "swETH": "2023-04-17",  # Swell mainnet
    "ETHx": "2023-07-10",  # Stader ETHx mainnet
    "osETH": "2023-11-28",  # StakeWise V3 launch
    "ankrETH": "2020-12-30",  # Ankr Eth2 staking (legacy aETHc renamed ankrETH)
    "weETH": "2024-01-29",  # EtherFi weETH wrapper
    # Puffer Vault V2 deployed 2024-01-31 but had zero shares at noon UTC that
    # day -> convertToAssets(1e18) returned empty bytes; first non-empty read
    # is 2024-02-01 (rate = 1.00000000).
    "pufETH": "2024-02-01",
    # SOL-family — Solana mainnet
    "mSOL": "2021-08-02",  # Marinade Finance launch
    "jitoSOL": "2022-11-01",  # Jito stake pool launch
}


# Inverse of LST_TOKEN_GENESIS — venue/protocol -> tokens. The MTDS handler
# bundles all tokens for a protocol into one parquet, so a venue is "expected"
# once its earliest token has launched. Keys are uppercase to match how MTDS
# lst-rates writes the venue partition.
LST_VENUE_TO_TOKENS: dict[str, tuple[str, ...]] = {
    "LIDO": ("stETH", "wstETH"),
    "ROCKETPOOL": ("rETH",),
    "COINBASE": ("cbETH",),
    "ETHENA": ("sUSDe",),
    "MAKER": ("sDAI",),
    "MANTLE": ("mETH",),
    "SWELL": ("swETH",),
    "STADER": ("ETHx",),
    "STAKEWISE": ("osETH",),
    "ANKR": ("ankrETH",),
    "ETHERFI": ("weETH",),
    "PUFFER": ("pufETH",),
    "MARINADE": ("mSOL",),
    "JITO": ("jitoSOL",),
}


def get_lst_token_genesis(token: str) -> str | None:
    """Return the YYYY-MM-DD genesis date for an LST token, or None if unknown.

    Used by MTDS lst-rates collectors to skip pre-genesis dates instead of
    issuing eth_calls / REST calls that will revert or fail.
    """
    return LST_TOKEN_GENESIS.get(token)


def get_lst_venue_genesis(venue: str) -> str | None:
    """Return the earliest LST_TOKEN_GENESIS among tokens emitted under
    this venue, or None if the venue is not a known LST protocol.

    Used in data-status / coverage builders to clamp the expected-coverage
    start so pre-genesis dates don't get flagged as missing.
    """
    tokens = LST_VENUE_TO_TOKENS.get(venue.upper())
    if not tokens:
        return None
    candidates = [LST_TOKEN_GENESIS[t] for t in tokens if t in LST_TOKEN_GENESIS]
    return min(candidates) if candidates else None


__all__ = [
    "LST_TOKEN_GENESIS",
    "LST_VENUE_TO_TOKENS",
    "get_lst_token_genesis",
    "get_lst_venue_genesis",
]
