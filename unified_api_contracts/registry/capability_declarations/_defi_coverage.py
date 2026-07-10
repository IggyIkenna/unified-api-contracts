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
        "TRADER_JOE_V2-AVALANCHE",  # 0 instruments as of 2026-04-29 (DF-17; underscore-canonical 2026-06-01)
        "UNISWAP_V3-POLYGON",  # subgraph returns 0 instruments as of 2026-04-29 (migration finding)
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
        "AAVEV2",  # superseded by AAVE_V2
        "AAVEV3",  # superseded by AAVE_V3
        "CAMELOTV3",  # superseded by CAMELOT_V3
        "COMPOUNDV3",  # superseded by COMPOUND_V3
        "MORPHO_VAULTS",  # underscore legacy form (pre-2026-05-06 manifest) → canonical MORPHOVAULTS
        "PANCAKESWAPV3",  # superseded by PANCAKESWAP_V3
        "SUSHISWAPV3",  # superseded by SUSHISWAP_V3
        "VELODROMEV2",  # superseded by VELODROME_V2
        "TRADER_JOEV2",  # superseded by TRADER_JOE_V2 (DF-17 underscore-canonical 2026-06-01)
        "TRADERJOEV2",  # fully-glued legacy form, superseded by TRADER_JOE_V2
        "YEARNV3",  # superseded by YEARN_V3
        "AERODROMEV3",  # superseded by AERODROME_V3 (Base chain Velodrome fork)
    }
)

# Venues that have a subgraph (and may receive future coverage) but have not been
# collected by instruments-service yet. data-status should not flag historical
# days as missing until the venue's first parquet write.
#
# SPARK-ETHEREUM removed 2026-07-10 (defi_turbo_api_hides_real_captured_data_2026_07_07.md):
# this entry was stale — it claimed "instruments-service has never written historical
# parquets for this venue" as of 2026-04-29, but a live GCS manifest read on
# 2026-07-07/2026-07-10 found 7,405 real captured lending_indices rows,
# 2023-03-07 -> 2026-06-21 (current). venue_has_no_expected_defi_coverage() short-
# circuited every mtds_expected_dates_cached() call for this venue to an empty
# frozenset, so the MTDS honest-coverage override always computed
# expected_shards=0 -> the turbo API left SPARK-ETHEREUM off the UAC-annotated
# response path entirely, masking the real captured data instead of reporting it.
DEFI_INSTRUMENTS_NOT_YET_COLLECTED: frozenset[str] = frozenset(
    {
        "VELODROME_V2-OPTIMISM",  # subgraph: 881 instruments; bucket: 0 parquets as of 2026-04-29
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
