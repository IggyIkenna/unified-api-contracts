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

# Per-ticker listing-date overrides for tradfi instruments whose source-wide
# venue coverage (NYSE/NASDAQ/ARCA → Databento equities ~2003) is much earlier
# than the instrument's actual listing. Without these, data-status checks
# would flag pre-listing weekdays as `missing` since they're inside the venue's
# coverage window. Only the ETFs we currently backfill are listed — extend as
# new tickers are added to the universe. Futures roll forward continuously
# so they don't need per-ticker overrides; the venue-level CME / DATABENTO
# clip suffices.
TRADFI_TICKER_COVERAGE_START: dict[str, date] = {
    # US BTC spot ETFs — launched 2024-01-11 (SEC-approval cohort).
    "IBIT": date(2024, 1, 11),
    "FBTC": date(2024, 1, 11),
    "ARKB": date(2024, 1, 11),
    "GBTC": date(2024, 1, 11),  # uplisted from OTC same day
    # US ETH spot ETFs — launched 2024-07-23.
    "ETHA": date(2024, 7, 23),
    "FETH": date(2024, 7, 23),
    "ETHE": date(2024, 7, 23),  # uplisted from OTC same day
    # Older crypto ETFs (futures-based + OTC, predate 2024 cohort).
    "BITO": date(2021, 10, 19),
}


# ---------------------------------------------------------------------------
# Prediction
# ---------------------------------------------------------------------------
# Prediction venues = market venues. Coverage start = venue inception.

PREDICTION_SOURCE_COVERAGE_START: dict[str, date] = {
    # Polymarket: CLOB (central-limit order book) launched 2022-11-21, which is
    # the canonical "tradeable history" cutoff. The platform itself launched
    # 2020-06-12 on Matic with AMM-style markets, but pre-CLOB data has no
    # order-book trading history that can be backtested. The pre-CLOB window
    # is captured in PREDICTION_KNOWN_COVERAGE_GAPS so data-status drops
    # those days from the denominator instead of flagging them missing.
    "POLYMARKET": date(2022, 11, 21),
    "KALSHI": date(2021, 7, 19),
    "MANIFOLD": date(2022, 1, 1),
}


# Known provider-side gaps within the source-coverage window. data-status drops
# these from the denominator (don't count as missing) and the orchestrator
# pre-skips them so VMs don't waste rate-limit on known-empty windows.
# Keys: (source_token_uppercase, "*" for all data_types or specific data_type)
# Values: list of (start_date, end_date) inclusive ranges.
PREDICTION_KNOWN_COVERAGE_GAPS: dict[tuple[str, str], list[tuple[date, date]]] = {
    # Polymarket pre-CLOB AMM era — markets existed but no order-book trades.
    ("POLYMARKET", "*"): [(date(2020, 6, 12), date(2022, 11, 20))],
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
    ticker: str | None = None,
) -> date | None:
    """Return the earliest date a source has data for, or ``None`` if unknown.

    Caller treats ``None`` as "no clip" — the expected denominator runs from
    the start of the query window instead of being clipped.

    Args:
        asset_group: Asset group enum or lowercase string token.
        source_key: Venue/source token. Casing follows the per-asset-group
            dict convention (CeFi/DeFi/TradFi/Prediction = uppercase venue;
            sports = lowercase source name).
        ticker: Optional per-instrument override. For TradFi ETFs whose
            listing date is materially later than the source-wide venue
            coverage (e.g. IBIT listed 2024-01-11 but NASDAQ data goes
            back to 2003), pass the ticker symbol to apply the per-ticker
            clip. Falls back to the source-wide value if the ticker has
            no override.
    """
    ag = AssetGroup(asset_group) if not isinstance(asset_group, AssetGroup) else asset_group
    if ag == AssetGroup.TRADFI and ticker:
        ticker_clip = TRADFI_TICKER_COVERAGE_START.get(ticker.upper())
        if ticker_clip is not None:
            return ticker_clip
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
    "TRADFI_TICKER_COVERAGE_START",
    "coverage_start",
]
