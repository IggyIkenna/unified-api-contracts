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
        "TRADERJOEV2-AVALANCHE",  # subgraph returns 0 instruments as of 2026-04-29
        "UNISWAPV3-POLYGON",  # subgraph returns 0 instruments as of 2026-04-29 (migration finding)
        # Spark uses its own schema (no `reserves` field) — aave_v3 adapter
        # is incompatible. Needs a dedicated spark adapter to backfill.
        "SPARK-ETHEREUM",
        "GMX-AVALANCHE",  # 0 historical parquets / minimal subgraph data (1 instrument) as of 2026-04-29
    }
)

# Venues that have a subgraph (and may receive future coverage) but have not been
# collected by instruments-service yet. data-status should not flag historical
# days as missing until the venue's first parquet write.
DEFI_INSTRUMENTS_NOT_YET_COLLECTED: frozenset[str] = frozenset(
    {
        "VELODROMEV2-OPTIMISM",  # subgraph: 881 instruments; bucket: 0 parquets as of 2026-04-29
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
