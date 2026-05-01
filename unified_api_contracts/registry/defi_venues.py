"""DeFi venue canonical-form registry — extracted from ``venue_mapping.py``.

Two artefacts for the DeFi side of the registry:

- ``ALL_DEFI_VENUES``: canonical ``PROTOCOL-CHAIN`` identifiers for every DeFi
  (protocol, chain) combination ingested by MTDS sub-dim buckets. Sourced from
  live enumeration across the ``market-data-tick-{gas-fees, lending-indices,
  dex-swaps, dex-pools, oracle-prices, lst-rates, liquidations, evm-defi,
  solana-defi, perp-funding}-<project>`` buckets on 2026-04-20.
- ``LEGACY_DEFI_VENUE_ALIASES``: mapping from the raw single-token forms that
  pre-2026-04 manifests carry (``AAVE_V3`` / ``UNISWAP_V2`` / ``CURVE`` /
  ``LIDO`` / ...) to their canonical ``PROTOCOL-CHAIN`` form. Used by
  ``normalize_defi_venue`` in ``VenueMapping``.

Kept as a separate module so ``venue_mapping.py`` stays under the 900-line
QG ceiling as the DeFi multi-chain coverage grows.

SSOT: ``codex/02-data/mtds-data-source-coverage-matrix.md``.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Canonical PROTOCOL-CHAIN venues
# ---------------------------------------------------------------------------
# Naming convention: protocol versioning is collapsed (AAVEV3, not AAVE_V3;
# COMPOUNDV3, not COMPOUND_V3; PANCAKESWAPV3) to match
# ``VENUE_DATA_TYPE_CAPABILITIES`` keys. Raw manifest values with underscores
# (``AAVE_V3`` + ``chain=POLYGON``, ``COMPOUND_V3`` + ``chain=SCROLL``,
# ``PANCAKESWAP_V3`` + ``chain=BSC``) resolve to these canonical names via
# ``VenueMapping.normalize_defi_venue``.

ALL_DEFI_VENUES: list[str] = [
    # ── Ethereum ──
    "UNISWAPV2-ETHEREUM",
    "UNISWAPV3-ETHEREUM",
    "UNISWAPV4-ETHEREUM",
    "CURVE-ETHEREUM",
    "BALANCER-ETHEREUM",
    "AAVEV3-ETHEREUM",
    "COMPOUNDV3-ETHEREUM",
    "MORPHO-ETHEREUM",
    "FLUID-ETHEREUM",
    "SPARK-ETHEREUM",
    "LIDO-ETHEREUM",
    "ETHERFI-ETHEREUM",
    "ETHENA-ETHEREUM",
    "SUSHISWAPV3-ETHEREUM",
    "PANCAKESWAPV3-ETHEREUM",
    # ── Arbitrum ──
    "UNISWAPV3-ARBITRUM",
    "AAVEV3-ARBITRUM",
    "COMPOUNDV3-ARBITRUM",
    "BALANCER-ARBITRUM",
    "SUSHISWAP-ARBITRUM",
    "PANCAKESWAPV3-ARBITRUM",
    "CAMELOTV3-ARBITRUM",
    "GMX-ARBITRUM",
    # ── Base ──
    "UNISWAPV3-BASE",
    "AAVEV3-BASE",
    "COMPOUNDV3-BASE",
    "BALANCER-BASE",
    "MORPHO-BASE",
    "SUSHISWAPV3-BASE",
    "PANCAKESWAPV3-BASE",
    "AERODROMEV3-BASE",
    # ── Optimism ──
    "UNISWAPV3-OPTIMISM",
    "AAVEV3-OPTIMISM",
    "COMPOUNDV3-OPTIMISM",
    "BALANCER-OPTIMISM",
    "CURVE-OPTIMISM",
    "VELODROMEV2-OPTIMISM",
    # ── Polygon ──
    "UNISWAPV3-POLYGON",
    "AAVEV3-POLYGON",
    "BALANCER-POLYGON",
    "COMPOUNDV3-POLYGON",
    # ── Avalanche ──
    "AAVEV3-AVALANCHE",
    "BALANCER-AVALANCHE",
    "CURVE-AVALANCHE",
    "GMX-AVALANCHE",
    "SUSHISWAPV3-AVALANCHE",
    "TRADER_JOEV2-AVALANCHE",
    # ── BSC ──
    "AAVEV3-BSC",
    "PANCAKESWAPV3-BSC",
    # ── Linea / Scroll / zkSync ──
    "AAVEV3-LINEA",
    "AAVEV3-SCROLL",
    "COMPOUNDV3-SCROLL",
    "AAVEV3-ZKSYNC",
    "PANCAKESWAPV3-ZKSYNC",
    # ── Solana ──
    "KAMINO-SOLANA",
    "MARINADE-SOLANA",
    "ORCA-SOLANA",
    "RAYDIUM-SOLANA",
]


# ---------------------------------------------------------------------------
# Legacy → canonical aliases
# ---------------------------------------------------------------------------
# Chain-less legacy names default to ETHEREUM canonical. Callers that pass
# the chain kwarg via ``VenueMapping.normalize_defi_venue(raw, chain)`` get
# the non-Ethereum canonical (``AAVEV3-ARBITRUM`` etc) synthesised by
# replacing the ``-ETHEREUM`` suffix.

LEGACY_DEFI_VENUE_ALIASES: dict[str, str] = {
    # DEX swap protocols
    "UNISWAP_V2": "UNISWAPV2-ETHEREUM",
    "UNISWAP_V3": "UNISWAPV3-ETHEREUM",
    "UNISWAP_V4": "UNISWAPV4-ETHEREUM",
    "UNISWAPV2": "UNISWAPV2-ETHEREUM",
    "UNISWAPV3": "UNISWAPV3-ETHEREUM",
    "UNISWAPV4": "UNISWAPV4-ETHEREUM",
    "CURVE": "CURVE-ETHEREUM",
    "BALANCER": "BALANCER-ETHEREUM",
    "SUSHISWAP": "SUSHISWAP-ETHEREUM",
    "SUSHISWAP_V3": "SUSHISWAPV3-ETHEREUM",
    "SUSHISWAPV3": "SUSHISWAPV3-ETHEREUM",
    "PANCAKESWAP_V3": "PANCAKESWAPV3-ETHEREUM",
    "PANCAKESWAPV3": "PANCAKESWAPV3-ETHEREUM",
    "CAMELOT_V3": "CAMELOTV3-ARBITRUM",
    "CAMELOTV3": "CAMELOTV3-ARBITRUM",
    "AERODROME_V3": "AERODROMEV3-BASE",
    "AERODROMEV3": "AERODROMEV3-BASE",
    "VELODROME_V2": "VELODROMEV2-OPTIMISM",
    "VELODROMEV2": "VELODROMEV2-OPTIMISM",
    "TRADER_JOE_V2": "TRADER_JOEV2-AVALANCHE",
    "TRADER_JOEV2": "TRADER_JOEV2-AVALANCHE",
    # Lending
    "AAVE_V3": "AAVEV3-ETHEREUM",
    "AAVEV3": "AAVEV3-ETHEREUM",
    "COMPOUND_V3": "COMPOUNDV3-ETHEREUM",
    "COMPOUNDV3": "COMPOUNDV3-ETHEREUM",
    "MORPHO": "MORPHO-ETHEREUM",
    "FLUID": "FLUID-ETHEREUM",
    "SPARK": "SPARK-ETHEREUM",
    # Perpetual DEXes
    "GMX": "GMX-ARBITRUM",
    # LST / yield
    "LIDO": "LIDO-ETHEREUM",
    "ETHERFI": "ETHERFI-ETHEREUM",
    "ETHENA": "ETHENA-ETHEREUM",
    # Solana
    "KAMINO": "KAMINO-SOLANA",
    "MARINADE": "MARINADE-SOLANA",
    "ORCA": "ORCA-SOLANA",
    "RAYDIUM": "RAYDIUM-SOLANA",
}


# Curated subset of DeFi venues that MTDS actively backfills. Used as
# ``VENUES_BY_ASSET_GROUP['defi']`` in ``market_data_categories.py``.
# Extracted here to keep that module under the 900-line QG ceiling as the
# DeFi multi-chain coverage grows.
MTDS_DEFI_VENUES: list[str] = [
    # --- DEX protocols (swaps + liquidity) ---
    "UNISWAPV2-ETHEREUM",
    "UNISWAPV3-ETHEREUM",
    "UNISWAPV3-ARBITRUM",
    "UNISWAPV3-BASE",
    "UNISWAPV3-OPTIMISM",
    "UNISWAPV3-POLYGON",
    "UNISWAPV4-ETHEREUM",
    "CURVE-ETHEREUM",
    "CURVE-AVALANCHE",
    "CURVE-OPTIMISM",
    "BALANCER-ETHEREUM",
    "BALANCER-ARBITRUM",
    "BALANCER-AVALANCHE",
    "BALANCER-BASE",
    "BALANCER-OPTIMISM",
    "BALANCER-POLYGON",
    # --- Lending protocols ---
    "AAVEV3-ETHEREUM",
    "AAVEV3-ARBITRUM",
    "AAVEV3-AVALANCHE",
    "AAVEV3-BASE",
    "AAVEV3-BSC",
    "AAVEV3-LINEA",
    "AAVEV3-OPTIMISM",
    "AAVEV3-POLYGON",
    "COMPOUNDV3-ETHEREUM",
    "COMPOUNDV3-ARBITRUM",
    "COMPOUNDV3-BASE",
    "COMPOUNDV3-OPTIMISM",
    "COMPOUNDV3-POLYGON",
    "MORPHO-ETHEREUM",
    "MORPHO-ARBITRUM",
    "MORPHO-BASE",
    "MORPHO-OPTIMISM",
    "MORPHO-POLYGON",
    "FLUID-ETHEREUM",
    "FLUID-ARBITRUM",
    "EULER_V2-ETHEREUM",
    "EULER_V2-ARBITRUM",
    "RADIANT-ETHEREUM",
    "RADIANT-ARBITRUM",
    "RADIANT-BSC",
    "VENUS-BSC",
    "VENUS-ETHEREUM",
    "BENQI-AVALANCHE",
    # --- LST/Yield protocols ---
    "LIDO-ETHEREUM",
    "ETHERFI-ETHEREUM",
    "ETHENA-ETHEREUM",
    "JITO-SOLANA",
]


__all__ = ["ALL_DEFI_VENUES", "LEGACY_DEFI_VENUE_ALIASES", "MTDS_DEFI_VENUES"]
