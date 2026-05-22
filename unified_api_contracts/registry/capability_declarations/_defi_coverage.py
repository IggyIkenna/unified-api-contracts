"""DeFi venue expected-coverage metadata.

Some venues in `SUBGRAPH_IDS` either have empty/retired subgraphs or
haven't been onboarded into instruments-service yet — historical parquets
don't exist. Without explicit metadata, data-status flags every day as
"missing" for these venues. This module is the SSOT.

Discovered 2026-04-29 during instruments-service-metadata-refactor migration.
"""

from __future__ import annotations

EMPTY_OR_DEPRECATED_DEFI_VENUES: frozenset[str] = frozenset(
    {
        "TRADER_JOEV2-AVALANCHE",  # 0 instruments as of 2026-04-29 (DF-17 migration 2026-05-13)
        "UNISWAPV3-POLYGON",  # subgraph returns 0 instruments as of 2026-04-29 (migration finding)
        "GMX-AVALANCHE",  # 0 historical parquets / minimal subgraph data (1 instrument) as of 2026-04-29
    }
)

# Era-2 ghost venue names (capabilities-era handlers, no underscore) that have been
# superseded by canonical underscore names. These should never appear in the manifest
# or data-status UI. Consolidator drops them at merge time; data-status service
# filters them at read time. Audit: defi_coverage_capability_alignment_2026_05_22.md
DEPRECATED_DEFI_GHOST_VENUE_NAMES: frozenset[str] = frozenset(
    {
        "UNISWAPV3",  # superseded by UNISWAP_V3
        "UNISWAPV2",  # superseded by UNISWAP_V2
        "UNISWAPV4",  # superseded by UNISWAP_V4
        "AAVEV2",  # superseded by AAVE_V2 (canonical) or dropped
        "AAVEV3",  # superseded by AAVE_V3
        "CAMELOTV3",  # superseded by CAMELOT_V3
        "COMPOUNDV3",  # superseded by COMPOUND_V3
        "MORPHOVAULTS",  # superseded by MORPHO_VAULTS
        "PANCAKESWAPV3",  # superseded by PANCAKESWAP_V3
        "SUSHISWAPV3",  # superseded by SUSHISWAP_V3
        "VELODROMEV2",  # superseded by VELODROME_V2
        "YEARNV3",  # superseded by YEARN_V3
        "AERODROMEV3",  # superseded by AERODROME_V3 (Base chain Velodrome fork)
    }
)

# Venues that have a subgraph (and may receive future coverage) but have not been
# collected by instruments-service yet. data-status should not flag historical
# days as missing until the venue's first parquet write.
DEFI_INSTRUMENTS_NOT_YET_COLLECTED: frozenset[str] = frozenset(
    {
        "VELODROMEV2-OPTIMISM",  # subgraph: 881 instruments; bucket: 0 parquets as of 2026-04-29
        # Spark adapter shipped 2026-04-29 (separate from aave_v3); subgraph
        # returns 17 markets but instruments-service has never written
        # historical parquets for this venue — until first scheduled run lands
        # on bucket, data-status should NOT flag historical days as missing.
        "SPARK-ETHEREUM",
        # SANCTUM: instruments-service adapter not yet created (Phase 2 of
        # solana_lst_native_staking_adapters_2026_05_14.md). Remove when
        # Phase 2 ships + first backfill completes.
        "SANCTUM-SOLANA",
        # SOLBLAZE: execution-service connector exists but instruments-service
        # reference data adapter + MTDS wiring not yet done (Phase 3 of plan).
        # Remove when Phase 3 ships + first backfill completes.
        "SOLBLAZE-SOLANA",
    }
)


def venue_has_no_expected_defi_coverage(venue: str) -> bool:
    """Return True if data-status should NOT expect any DeFi instruments
    coverage for this venue — either deprecated subgraph or not yet onboarded.
    """
    upper = venue.upper()
    return (
        upper in EMPTY_OR_DEPRECATED_DEFI_VENUES
        or upper in DEFI_INSTRUMENTS_NOT_YET_COLLECTED
        or upper in DEPRECATED_DEFI_GHOST_VENUE_NAMES
    )


__all__ = [
    "DEFI_INSTRUMENTS_NOT_YET_COLLECTED",
    "DEPRECATED_DEFI_GHOST_VENUE_NAMES",
    "EMPTY_OR_DEPRECATED_DEFI_VENUES",
    "venue_has_no_expected_defi_coverage",
]
