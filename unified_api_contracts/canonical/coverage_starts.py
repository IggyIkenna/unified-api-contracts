"""SSOT for source-coverage start dates across all asset groups.

The catalogue generator uses these dates to compute the *expected* date
denominator per (asset_group, venue) tuple — without clipping, the
coverage % would falsely show "missing" days for the period before a venue
had ANY data (e.g. Hyperliquid before its 2023-06-29 launch). Sports already
has its SSOT in
:mod:`unified_api_contracts.canonical.domain.sports.league_data` — kept
there because it's tied to per-source league rosters; re-exported through
this module for parity.

Update when:
  * A new venue is onboarded.
  * An existing venue extends history backwards (e.g. paid-tier upgrade
    unlocks earlier data).
  * A backfill VM verifies the actual earliest-captured date in production
    and the seeded value is wrong.

Seed values were derived from venue launch dates and (where verified)
manifest min(date) probes. Anything marked ``# TODO verify`` is best-effort
and should be confirmed against
``read_availability_index({bucket}).date.min()`` on the prod manifest.
"""

from __future__ import annotations

from datetime import date

from unified_api_contracts.canonical.domain.sports.league_data import (
    SOURCE_COVERAGE_START as _SPORTS_SOURCE_COVERAGE_START,
)
from unified_api_contracts.canonical.gcs_paths import AssetGroup

# ---------------------------------------------------------------------------
# CeFi
# ---------------------------------------------------------------------------
# Keys are venue tokens (uppercase) matching the GCS partition value, e.g.
# ``BINANCE``, ``DERIBIT``, ``COINBASE`` — same casing as the
# canonical/partition_paths build_*_partition_path output.

CEFI_SOURCE_COVERAGE_START: dict[str, date] = {
    "BITFINEX": date(2013, 4, 30),
    "KRAKEN": date(2013, 9, 10),
    "COINBASE": date(2014, 12, 8),
    "DERIBIT": date(2016, 6, 13),
    "OKX": date(2017, 5, 31),
    "BINANCE": date(2017, 8, 17),
    "BYBIT": date(2018, 11, 21),
    "HYPERLIQUID": date(2023, 6, 29),
    # Tardis multi-venue feed — earliest cross-venue tick coverage.
    "TARDIS": date(2017, 6, 1),  # TODO verify
}


# ---------------------------------------------------------------------------
# DeFi
# ---------------------------------------------------------------------------
# DeFi venues = protocols. Coverage start is the earlier of the protocol
# deployment date and our adapter's earliest indexed block. Where the
# adapter relies on subgraphs / indexers with shorter retention, the
# effective start is later than the on-chain deployment.

DEFI_SOURCE_COVERAGE_START: dict[str, date] = {
    "CURVE": date(2020, 1, 19),
    "UNISWAP_V2": date(2020, 5, 4),
    "AAVE_V2": date(2020, 12, 1),
    "UNISWAP_V3": date(2021, 5, 5),
    "BALANCER": date(2021, 5, 13),
    "AAVE_V3": date(2022, 3, 16),
    "LIDO": date(2020, 12, 19),
    "ETHENA": date(2024, 2, 19),
    "ETHERFI": date(2023, 11, 1),  # TODO verify
    "UNISWAP_V4": date(2025, 1, 31),  # TODO verify
}


# ---------------------------------------------------------------------------
# TradFi
# ---------------------------------------------------------------------------
# TradFi venues = data sources. FRED has very deep history (DGS series go
# back to 1962). OPRA options chain goes to 2003 via Databento. Tardis
# institutional feed is more recent.

TRADFI_SOURCE_COVERAGE_START: dict[str, date] = {
    "FRED": date(1962, 1, 2),
    "OPRA": date(2003, 1, 13),
    "DATABENTO": date(2003, 1, 13),
    "TARDIS": date(2017, 6, 1),  # TODO verify
    "CME": date(2010, 1, 1),  # TODO verify
}


# ---------------------------------------------------------------------------
# Prediction
# ---------------------------------------------------------------------------
# Prediction venues = market venues. Coverage start = venue inception.

PREDICTION_SOURCE_COVERAGE_START: dict[str, date] = {
    "POLYMARKET": date(2020, 6, 12),
    "KALSHI": date(2021, 7, 19),
    "MANIFOLD": date(2022, 1, 1),
}


# ---------------------------------------------------------------------------
# Sports — re-exported from the existing sports SSOT for parity
# ---------------------------------------------------------------------------
# Sports keys are source-name tokens (e.g. ``api_football`` / ``odds_api``)
# rather than uppercase venue tokens. Kept lowercase to match the existing
# canonical/domain/sports/league_data.py SSOT.

SPORTS_SOURCE_COVERAGE_START: dict[str, date] = dict(_SPORTS_SOURCE_COVERAGE_START)


# ---------------------------------------------------------------------------
# Cross-asset lookup
# ---------------------------------------------------------------------------

_REGISTRY_BY_ASSET_GROUP: dict[AssetGroup, dict[str, date]] = {
    AssetGroup.CEFI: CEFI_SOURCE_COVERAGE_START,
    AssetGroup.DEFI: DEFI_SOURCE_COVERAGE_START,
    AssetGroup.TRADFI: TRADFI_SOURCE_COVERAGE_START,
    AssetGroup.PREDICTION: PREDICTION_SOURCE_COVERAGE_START,
    AssetGroup.SPORTS: SPORTS_SOURCE_COVERAGE_START,
}


def coverage_start(
    asset_group: AssetGroup | str,
    source_key: str,
) -> date | None:
    """Return the earliest date a source has data for, or ``None`` if unknown.

    Caller treats ``None`` as "no clip" — the expected denominator runs from
    the start of the query window instead of being clipped.

    Args:
        asset_group: Asset group enum or lowercase string token.
        source_key: Venue/source token. Casing follows the per-asset-group
            dict convention (CeFi/DeFi/TradFi/Prediction = uppercase venue;
            sports = lowercase source name).
    """
    ag = AssetGroup(asset_group) if not isinstance(asset_group, AssetGroup) else asset_group
    registry = _REGISTRY_BY_ASSET_GROUP.get(ag)
    if registry is None:
        return None
    return registry.get(source_key)


__all__ = [
    "CEFI_SOURCE_COVERAGE_START",
    "DEFI_SOURCE_COVERAGE_START",
    "PREDICTION_SOURCE_COVERAGE_START",
    "SPORTS_SOURCE_COVERAGE_START",
    "TRADFI_SOURCE_COVERAGE_START",
    "coverage_start",
]
