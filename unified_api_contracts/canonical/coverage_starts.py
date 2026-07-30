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
# ``BINANCE``, ``DERIBIT``, ``COINBASE-SPOT`` — same casing as the
# canonical/partition_paths build_*_partition_path output.

CEFI_SOURCE_COVERAGE_START: dict[str, date] = {
    # 8 values below corrected 2026-07-27 (coverage_floor_registries_no_
    # cross_propagation_2026_07_17.md [DATA] P1) — the prior dates were
    # unverified VENUE-LAUNCH-DATE guesses (per this module's own "derived
    # from venue launch dates" docstring caveat); probed live against
    # market-data-tick-cefi-prd-{project}'s availability index
    # (`read_availability_index(bucket).groupby("venue")["date"].min()` on
    # capture_status="captured" rows) — every value below is the measured
    # min(date) across that venue's registry-2 (venue_mapping.py) suffixed
    # keys, each independently confirmed to be a CLEAN boundary (zero rows
    # of ANY capture_status before the measured date, so it is a genuine
    # first-attempt, not an unbackfilled gap masquerading as a floor).
    "BITFINEX": date(2020, 1, 1),
    "KRAKEN": date(2020, 1, 1),
    "COINBASE-SPOT": date(2020, 1, 1),
    # DERIBIT: measured min is 2019-05-08 (real, substantial `trades` rows —
    # thousands to hundreds of thousands of instrument_count per day — not a
    # placeholder), earlier than book_snapshot_5/derivative_ticker's clean
    # 2020-01-01 floor. The 2019-05..2019-12 window is sparse (not every
    # calendar day has a row), suggesting a partial historical backfill —
    # real lower bound confirmed, but more pre-2020 history may exist
    # unbackfilled. Flagged as a follow-up in the same issue doc, not blocking
    # this floor correction (a partial-coverage lower bound is still a real,
    # truthful floor — never treat "some data below the old floor" as reason
    # to keep the floor artificially late).
    "DERIBIT": date(2019, 5, 8),
    "OKX": date(2020, 1, 1),
    "BINANCE": date(2020, 1, 1),
    "BYBIT": date(2021, 1, 1),
    # HYPERLIQUID: NOT set to the measured captured-min (2024-01-01) —
    # venue_mapping.py's 2023-04-15 is vendor-verified (Hyperliquid
    # book_snapshot_5 S3 archive start, cross-checked against a documented
    # 2026-05-05 incident investigation into the discovery-API's narrower
    # window). The 2023-04-15..2023-12-31 gap has ZERO manifest rows of any
    # capture_status (never attempted, not confirmed-empty) — a real,
    # unbackfilled window, not evidence the floor should move later. Matching
    # registry 2's verified value here (not the naive manifest probe) is the
    # correct fix; the backfill gap itself is a separate, already-documented
    # data-completeness finding.
    "HYPERLIQUID": date(2023, 4, 15),
    # Bitget native USDT-M perp launched 2019-07-10 but Tardis only carries
    # bitget-futures from 2024-11-08. `availableSince` probe confirmed
    # 2026-05-07 against `https://api.tardis.dev/v1/exchanges/bitget-futures`
    # (910 perpetuals, all gated by exchange-wide 2024-11-08T00:00:00Z floor).
    # Pre-cutoff dates → EXPECTED_PRE_SOURCE_COVERAGE_START.
    "BITGET": date(2024, 11, 8),
    # Prediction-platform PERPETUAL FUTURES — CFTC-regulated crypto perps with
    # funding. Coverage start = venue launch date (no pre-launch data exists).
    # Distinct from POLYMARKET/KALSHI prediction YES/NO markets (in
    # PREDICTION_SOURCE_COVERAGE_START). Treated as cefi for bucket/path logic.
    # SSOT: plans/active/prediction_venue_perps_and_live_clob_depth_2026_06_20.md
    "KALSHI-PERP": date(2026, 5, 29),  # Kalshi CFTC crypto perp launch
    "POLYMARKET-PERP": date(2026, 4, 21),  # Polymarket perp beta launch
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


# Per-(venue, data_type) DeFi collection-start floor (data-driven, 2026-06-22).
# DISTINCT from DEFI_SOURCE_COVERAGE_START above (venue-level): the
# ``expected_coverage()`` availability oracle reads coverage_start PER DATA_TYPE
# (``get_source_coverage_start_for_data_type``) — venue launch alone does not
# clip a data_type we only STARTED COLLECTING later. Each value is the MEASURED
# earliest ``capture_status='captured'`` date for that exact (venue, data_type)
# pair, read from the prod defi ``_index/availability_index.parquet`` on
# 2026-06-22 (925,820 captured rows). The data exists on-chain back to protocol
# launch, but our subgraph/RPC adapter only began materialising this data_type
# on the date below → dates before it are honestly EXPECTED_PRE_SOURCE_COVERAGE_START,
# not DIVERGENT_EMPTY. This closed the chain-blind-fix residual divergent tail
# (the operator's #1 Slack alert): the per-chain venue-launch fix
# (UAC@c8f4bbd7, 85,900→22,140) cleared pre-launch over-expectation; this clears
# the pre-COLLECTION-start over-expectation.
#
# **PER-PAIR + DATA-DRIVEN, never a flat default** (operator HARD POINT): each
# entry is its own measured floor; a pair absent here returns None (= no clip,
# the oracle still expects data). The flat value is the EARLIEST across all
# chains the pair was captured on (conservative — clips only dates before ANY
# chain had it), matching the flat (venue, data_type) grain of the divergence
# oracle (which itself carries no chain axis). When a backfill extends a pair's
# history backwards, LOWER its value here (or delete it) — never raise it to
# mask a real gap. SSOT: data_pipeline_hardening_self_monitoring_2026_06_22.md
# Phase 3.
DEFI_DATA_TYPE_COVERAGE_START: dict[str, dict[str, date]] = {
    "AAVE_V3": {
        "lending_indices": date(2022, 3, 12),
        "risk_params": date(2024, 5, 2),
    },
    "AERODROME_V3": {
        "dex_pool_state": date(2024, 5, 1),
        "dex_pool_swaps": date(2024, 7, 1),
    },
    "ALCHEMY": {"gas_fees": date(2020, 1, 1)},
    "BALANCER": {
        "dex_pool_state": date(2021, 5, 1),
        "dex_pool_swaps": date(2021, 5, 1),
    },
    "CAMELOT_V3": {"dex_pool_state": date(2023, 6, 14)},
    "COMPOUND_V3": {"lending_indices": date(2022, 8, 13)},
    "CURVE": {
        "dex_pool_state": date(2021, 1, 1),
        "dex_pool_swaps": date(2021, 1, 1),
    },
    "PANCAKESWAP_V3": {
        "dex_pool_state": date(2023, 4, 1),
        "dex_pool_swaps": date(2024, 1, 1),
    },
    # ── LST venues IS-wired 2026-07-18 (MTDS@8746708c lst_rates acquisition) ──
    # No MEASURED manifest floor yet (freshly acquired), so the honest floor is the
    # protocol's ETHEREUM on-chain genesis — an lst_rates exchange-rate row cannot
    # exist before the protocol launched. Same chain_env.PROTOCOL_LAUNCH_DATES
    # ETHEREUM genesis used for their venue-launch clip in venue_launch_dates.py
    # (kept consistent). Sibling of STADER/STAKEWISE/SWELL below (also LST lst_rates
    # floors == their ETH genesis). LOWER these when a backfill measures an earlier
    # captured date — never raise to mask a real gap.
    "BEEFY": {"lst_rates": date(2021, 12, 1)},  # Beefy ETH vaults genesis (chain_env ETHEREUM)
    "IDLE": {"lst_rates": date(2019, 8, 13)},  # Idle Finance ETH mainnet launch
    "KELPDAO": {"lst_rates": date(2023, 11, 9)},  # KelpDAO rsETH mainnet
    "PENDLE": {"lst_rates": date(2021, 6, 15)},  # Pendle V1 mainnet
    "RENZO": {"lst_rates": date(2024, 4, 29)},  # Renzo ezETH mainnet
    "STADER": {"lst_rates": date(2023, 7, 10)},
    "STAKEWISE": {"lst_rates": date(2023, 11, 28)},
    "SUSHISWAP": {
        "dex_pool_state": date(2021, 8, 31),
        "dex_pool_swaps": date(2021, 8, 31),
    },
    "SUSHISWAP_V3": {"dex_pool_swaps": date(2024, 1, 1)},
    "SWELL": {"lst_rates": date(2023, 4, 17)},
    "UNISWAP_V3": {"dex_pool_swaps": date(2021, 5, 4)},
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
    # Verified 2026-07-25 against live manifest (market-data-tick-tradfi
    # availability_index.parquet): earliest CME capture_status=captured row
    # is 2020-01-01; every pre-2020 date is empty_confirmed/expected_unattempted
    # (EXPECTED_INSTRUMENT_NOT_LISTED), not real data. Matches
    # registry/venue_mapping.py's CME=2020-01-01 (also "earliest manifest
    # data", no TODO) — the two registries now agree for CME, closing the
    # coverage_floor_registries_no_cross_propagation_2026_07_17.md P2 item.
    "CME": date(2020, 1, 1),
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
    # order-book trading history that can be backtested. The pre-CLOB window is
    # entirely BELOW this floor, so the floor alone already clips it.
    "POLYMARKET": date(2022, 11, 21),
    "KALSHI": date(2021, 7, 19),
    "MANIFOLD": date(2022, 1, 1),
}


# NOTE — ``PREDICTION_KNOWN_COVERAGE_GAPS`` was DELETED 2026-07-17.
# It declared a bounded range (POLYMARKET pre-CLOB 2020-06-12 → 2022-11-20) and its
# comment claimed data-status dropped it from the denominator and the orchestrator
# pre-skipped it. Neither was true: it was never exported in ``__all__`` and had ZERO
# importers workspace-wide — dead code asserting an effect it did not have. It was also
# redundant: its range ended exactly one day below the POLYMARKET floor above, so the
# floor already clipped every day it named. It was, in miniature, the failure mode that
# motivated the evidenced registry: a bounded exclusion typed in without provenance,
# without a consumer, and without anything that could ever prove it wrong.
#
# Bounded out-of-bounds ranges now live in ONE cross-asset, evidence-gated, falsifiable
# SSOT: ``unified_api_contracts.canonical.coverage_exclusions.COVERAGE_EXCLUSIONS``.


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
    "DEFI_DATA_TYPE_COVERAGE_START",
    "DEFI_SOURCE_COVERAGE_START",
    "PREDICTION_SOURCE_COVERAGE_START",
    "SPORTS_SOURCE_COVERAGE_START",
    "TRADFI_SOURCE_COVERAGE_START",
    "TRADFI_TICKER_COVERAGE_START",
    "coverage_start",
]
