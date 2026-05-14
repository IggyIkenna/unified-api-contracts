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
    }
)


def venue_has_no_expected_defi_coverage(venue: str) -> bool:
    """Return True if data-status should NOT expect any DeFi instruments
    coverage for this venue — either deprecated subgraph or not yet onboarded.
    """
    upper = venue.upper()
    return upper in EMPTY_OR_DEPRECATED_DEFI_VENUES or upper in DEFI_INSTRUMENTS_NOT_YET_COLLECTED


__all__ = [
    "DEFI_INSTRUMENTS_NOT_YET_COLLECTED",
    "EMPTY_OR_DEPRECATED_DEFI_VENUES",
    "venue_has_no_expected_defi_coverage",
]
