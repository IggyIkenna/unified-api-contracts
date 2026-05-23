"""Per-chain DEX router addresses — SSOT for execution-service swap legs.

Fixes the silent-Ethereum-only bug surfaced by defi_recursive_borrow Family 1 design
2026-05-12: ``UniswapConnector.swap_exact_input`` was hardcoding mainnet SwapRouter02
``0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45``, which only resolves on Ethereum.
Family 1 + 2 cells on Base + Arbitrum + Optimism need per-chain dispatch.

Plan:
``unified-trading-pm/plans/active/defi_recursive_borrow_archetypes_2026_05_10.md``
Family 1 design § "Cross-plan annotations queued".

Provenance: addresses sourced from Uniswap V3 deployments docs:
- Ethereum mainnet: SwapRouter02 ``0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45``
- Base mainnet: SwapRouter02 ``0x2626664c2603336E57B271c5C0b26F421741e481``
- Arbitrum One: SwapRouter02 ``0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45`` (same as mainnet)
- Optimism: SwapRouter02 ``0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45`` (same as mainnet)
- Polygon: SwapRouter02 ``0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45`` (same as mainnet)
"""

from __future__ import annotations

from typing import Final

# Uniswap V3 SwapRouter02 addresses, keyed by chain name (uppercase).
# SwapRouter02 is the canonical multi-hop router for Uniswap V3 across all
# supported chains. Used by execution-service ``UniswapConnector.swap_exact_input``
# for cross-asset swap legs in Family 1 + Family 2 recursive-borrow archetypes.
#
# NOTE: addresses are checksummed EIP-55 form; consumers must respect the
# checksum case when constructing tx calldata to avoid downstream Web3 strict-mode
# validation errors.
UNISWAP_SWAP_ROUTER_BY_CHAIN: Final[dict[str, str]] = {
    "ETHEREUM": "0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45",
    "BASE": "0x2626664c2603336E57B271c5C0b26F421741e481",
    "ARBITRUM": "0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45",
    "OPTIMISM": "0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45",
    "POLYGON": "0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45",
}


# Uniswap V3 Factory addresses (added for completeness; consumers needing pool
# lookup via factory.getPool() use this).
UNISWAP_V3_FACTORY_BY_CHAIN: Final[dict[str, str]] = {
    "ETHEREUM": "0x1F98431c8aD98523631AE4a59f267346ea31F984",
    "BASE": "0x33128a8fC17869897dcE68Ed026d694621f6FDfD",
    "ARBITRUM": "0x1F98431c8aD98523631AE4a59f267346ea31F984",
    "OPTIMISM": "0x1F98431c8aD98523631AE4a59f267346ea31F984",
    "POLYGON": "0x1F98431c8aD98523631AE4a59f267346ea31F984",
}


def get_uniswap_swap_router(chain: str) -> str | None:
    """Return the Uniswap V3 SwapRouter02 address for a chain.

    Args:
        chain: Chain name (case-insensitive; canonicalised internally).

    Returns:
        EIP-55 checksummed address or None if chain not supported.
    """
    return UNISWAP_SWAP_ROUTER_BY_CHAIN.get(chain.upper())


def get_uniswap_v3_factory(chain: str) -> str | None:
    """Return the Uniswap V3 Factory address for a chain.

    Args:
        chain: Chain name (case-insensitive; canonicalised internally).

    Returns:
        EIP-55 checksummed address or None if chain not supported.
    """
    return UNISWAP_V3_FACTORY_BY_CHAIN.get(chain.upper())


# Uniswap V3 QuoterV2 addresses, keyed by chain name (uppercase).
# QuoterV2 is the on-chain quote contract for Uniswap V3 (replaces the original
# Quoter). Used by execution-service UniswapConnector for off-chain quote lookups.
# Only chains confirmed from deployment docs are populated; consumers must handle
# None (chain not yet verified).
UNISWAP_QUOTER_V2_BY_CHAIN: Final[dict[str, str]] = {
    "ETHEREUM": "0x61fFE014bA17989E743c5F6cB21bF9697530B21e",
}


def get_uniswap_quoter_v2(chain: str) -> str | None:
    """Return the Uniswap V3 QuoterV2 address for a chain.

    Args:
        chain: Chain name (case-insensitive; canonicalised internally).

    Returns:
        EIP-55 checksummed address or None if chain not supported.
    """
    return UNISWAP_QUOTER_V2_BY_CHAIN.get(chain.upper())


__all__ = [
    "UNISWAP_QUOTER_V2_BY_CHAIN",
    "UNISWAP_SWAP_ROUTER_BY_CHAIN",
    "UNISWAP_V3_FACTORY_BY_CHAIN",
    "get_uniswap_quoter_v2",
    "get_uniswap_swap_router",
    "get_uniswap_v3_factory",
]
