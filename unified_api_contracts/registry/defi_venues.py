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
    "MORPHOVAULTS-ETHEREUM",
    "YEARNV3-ETHEREUM",
    "FRAX-ETHEREUM",
    "MAKER-ETHEREUM",
    # ── LST / staking-yield protocols on Ethereum (added 2026-05-07 per
    #    DEFI-panel audit — these were live in the lst-rates bucket but
    #    not declared, causing duplicate "no chevron" rendering in the
    #    deployment-ui DEFI panel). All are actively backfilled by MTDS
    #    via the lst-rates sub-bucket.
    "ANKR-ETHEREUM",
    "ROCKETPOOL-ETHEREUM",
    "STADER-ETHEREUM",
    "STAKEWISE-ETHEREUM",
    "SWELL-ETHEREUM",
    "PUFFER-ETHEREUM",
    "MANTLE-ETHEREUM",
    # ── Gas-fee oracle (operates as a DeFi-context gas price source via
    #    the gas-fees sub-bucket; declared so the data-status panel
    #    renders it as an expected DeFi venue).
    "ALCHEMY-ETHEREUM",
    "EIGENLAYER-ETHEREUM",
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
    # PANCAKESWAPV3-ZKSYNC dropped 2026-05-06 — low-quality + low-volume data,
    # never produced useful captures. The 446 manifest rows that existed were
    # purged via `migrate_defi_legacy_venue_chain.py`. Do NOT re-add without
    # validating data quality + non-trivial liquidity on the chain.
    # ── Solana ──
    "KAMINO-SOLANA",
    "MARINADE-SOLANA",
    "ORCA-SOLANA",
    "RAYDIUM-SOLANA",
    # Solana LST/staking-yield (added 2026-05-07 — MTDS backfilled; data-
    # status was treating them as un-declared). JITO already in
    # MTDS_DEFI_VENUES below; this adds it to the full DeFi registry too.
    "JITO-SOLANA",
    "MARGINFI-SOLANA",
    "SOLEND-SOLANA",
    "DRIFT-SOLANA",
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
    # Vaults / yield-bearing
    "MORPHO_VAULTS": "MORPHOVAULTS-ETHEREUM",
    "MORPHOVAULTS": "MORPHOVAULTS-ETHEREUM",
    "YEARN_V3": "YEARNV3-ETHEREUM",
    "YEARNV3": "YEARNV3-ETHEREUM",
    "FRAX": "FRAX-ETHEREUM",
    "MAKER": "MAKER-ETHEREUM",
    # Solana
    "KAMINO": "KAMINO-SOLANA",
    "MARINADE": "MARINADE-SOLANA",
    "ORCA": "ORCA-SOLANA",
    "RAYDIUM": "RAYDIUM-SOLANA",
    "JITO": "JITO-SOLANA",
    "MARGINFI": "MARGINFI-SOLANA",
    "SOLEND": "SOLEND-SOLANA",
    "DRIFT": "DRIFT-SOLANA",
    # LST / staking-yield protocols on Ethereum (added 2026-05-07 — DEFI
    # panel audit). Bare-name aliases needed because the manifest carries
    # them as ``venue=ANKR chain=ETHEREUM`` etc.; the
    # ``VenueMapping.normalize_defi_venue`` lookup only matches
    # ``raw_venue in all_defi_venues`` for fully-canonical strings, so
    # bare names need an explicit alias to resolve.
    "ANKR": "ANKR-ETHEREUM",
    "ROCKETPOOL": "ROCKETPOOL-ETHEREUM",
    "STADER": "STADER-ETHEREUM",
    "STAKEWISE": "STAKEWISE-ETHEREUM",
    "SWELL": "SWELL-ETHEREUM",
    "PUFFER": "PUFFER-ETHEREUM",
    "MANTLE": "MANTLE-ETHEREUM",
    # Gas-fee + restaking oracles
    "ALCHEMY": "ALCHEMY-ETHEREUM",
    "EIGENLAYER": "EIGENLAYER-ETHEREUM",
}


# ---------------------------------------------------------------------------
# DeFi venue phase — distinguishes actively-backfilled venues ("live") from
# UAC-declared roadmap entries ("pipeline"). The deployment-ui DEFI panel
# uses this to render only "live" venues in the live-coverage section AND
# surface "pipeline" venues in a separate roadmap section so operators see
# what's queued without polluting the active honest-coverage view. Added
# 2026-05-07 per DEFI panel audit.
#
# - "live": MTDS backfill is shipping data; manifest has rows; UI shows
#   in the main DEFI panel with chevron + dates.
# - "pipeline": UAC declares the venue (chain expansion roadmap, not yet
#   plumbed in MTDS); manifest has zero rows; UI shows in a "roadmap"
#   section so the operator can see what's coming.
#
# Every entry in ``ALL_DEFI_VENUES`` must appear here. The
# ``DEFI_VENUE_PHASE`` test (test_defi_venue_phase_coverage) asserts the
# 1:1 invariant.
# ---------------------------------------------------------------------------


DEFI_VENUE_PHASE: dict[str, str] = {
    # ── Live (Ethereum DEX / lending) ──
    "UNISWAPV2-ETHEREUM": "live",
    "UNISWAPV3-ETHEREUM": "live",
    "UNISWAPV4-ETHEREUM": "live",
    "CURVE-ETHEREUM": "live",
    "BALANCER-ETHEREUM": "live",
    "AAVEV3-ETHEREUM": "live",
    "COMPOUNDV3-ETHEREUM": "live",
    "MORPHO-ETHEREUM": "live",
    "FLUID-ETHEREUM": "live",
    "SPARK-ETHEREUM": "live",
    "SUSHISWAPV3-ETHEREUM": "live",
    "PANCAKESWAPV3-ETHEREUM": "live",
    "MORPHOVAULTS-ETHEREUM": "live",
    "YEARNV3-ETHEREUM": "live",
    "FRAX-ETHEREUM": "live",
    "MAKER-ETHEREUM": "live",
    # ── Live (Ethereum LST / staking-yield) ──
    "LIDO-ETHEREUM": "live",
    "ETHERFI-ETHEREUM": "live",
    "ETHENA-ETHEREUM": "live",
    "ANKR-ETHEREUM": "live",
    "ROCKETPOOL-ETHEREUM": "live",
    "STADER-ETHEREUM": "live",
    "STAKEWISE-ETHEREUM": "live",
    "SWELL-ETHEREUM": "live",
    "PUFFER-ETHEREUM": "live",
    "MANTLE-ETHEREUM": "live",
    # ── Live (Ethereum gas / restaking oracles) ──
    "ALCHEMY-ETHEREUM": "live",
    "EIGENLAYER-ETHEREUM": "live",
    # ── Pipeline (Arbitrum) — UAC-declared, MTDS backfill not yet shipping ──
    "UNISWAPV3-ARBITRUM": "pipeline",
    "AAVEV3-ARBITRUM": "pipeline",
    "COMPOUNDV3-ARBITRUM": "pipeline",
    "BALANCER-ARBITRUM": "pipeline",
    "SUSHISWAP-ARBITRUM": "pipeline",
    "PANCAKESWAPV3-ARBITRUM": "pipeline",
    "CAMELOTV3-ARBITRUM": "pipeline",
    "GMX-ARBITRUM": "pipeline",
    # ── Pipeline (Base) ──
    "UNISWAPV3-BASE": "pipeline",
    "AAVEV3-BASE": "pipeline",
    "COMPOUNDV3-BASE": "pipeline",
    "BALANCER-BASE": "pipeline",
    "MORPHO-BASE": "pipeline",
    "SUSHISWAPV3-BASE": "pipeline",
    "PANCAKESWAPV3-BASE": "pipeline",
    "AERODROMEV3-BASE": "pipeline",
    # ── Pipeline (Optimism) ──
    "UNISWAPV3-OPTIMISM": "pipeline",
    "AAVEV3-OPTIMISM": "pipeline",
    "COMPOUNDV3-OPTIMISM": "pipeline",
    "BALANCER-OPTIMISM": "pipeline",
    "CURVE-OPTIMISM": "pipeline",
    "VELODROMEV2-OPTIMISM": "pipeline",
    # ── Pipeline (Polygon) ──
    "UNISWAPV3-POLYGON": "pipeline",
    "AAVEV3-POLYGON": "pipeline",
    "BALANCER-POLYGON": "pipeline",
    "COMPOUNDV3-POLYGON": "pipeline",
    # ── Pipeline (Avalanche) ──
    "AAVEV3-AVALANCHE": "pipeline",
    "BALANCER-AVALANCHE": "pipeline",
    "CURVE-AVALANCHE": "pipeline",
    "GMX-AVALANCHE": "pipeline",
    "SUSHISWAPV3-AVALANCHE": "pipeline",
    "TRADER_JOEV2-AVALANCHE": "pipeline",
    # ── Pipeline (BSC) ──
    "AAVEV3-BSC": "pipeline",
    "PANCAKESWAPV3-BSC": "pipeline",
    # ── Pipeline (Linea / Scroll / zkSync) ──
    "AAVEV3-LINEA": "pipeline",
    "AAVEV3-SCROLL": "pipeline",
    "COMPOUNDV3-SCROLL": "pipeline",
    "AAVEV3-ZKSYNC": "pipeline",
    # ── Live (Solana — JITO, MARINADE, ORCA, RAYDIUM, KAMINO actively
    #    backfilled per memory.project_carry_tracer_session_2026_05_06) ──
    "KAMINO-SOLANA": "live",
    "MARINADE-SOLANA": "live",
    "ORCA-SOLANA": "live",
    "RAYDIUM-SOLANA": "live",
    "JITO-SOLANA": "live",
    "MARGINFI-SOLANA": "live",
    "SOLEND-SOLANA": "live",
    "DRIFT-SOLANA": "live",
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


__all__ = [
    "ALL_DEFI_VENUES",
    "DEFI_VENUE_PHASE",
    "LEGACY_DEFI_VENUE_ALIASES",
    "MTDS_DEFI_VENUES",
]
