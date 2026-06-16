"""``CanonicalQuestionGroup`` enum + per-group metadata SSOT.

Predictions plan
``predictions_canonical_question_group_polymarket_migration_2026_05_06.md``
Phase 1A.

Recurring canonical groups (``BTC_UP_DOWN_HOURLY``, ``BTC_UP_DOWN_DAILY``,
``SPX_UP_DOWN_DAILY``, ``ELECTION_PRESIDENT_2028``, etc.) cycle through
multiple raw market_ids over time — HOURLY = 24/day, DAILY = 1/day,
ELECTION = 1 over months/years. The shard atom for prediction tick
parquets is ``(asset_group=prediction, venue, data_type, canonical_question_group, day)``;
multiple market_ids on the same canonical_group/day bundle into one
parquet (analogous to options-chain bundling).

Naming convention (Phase 0 audit recommendation, Option A):

* Cadenced range-bracket markets: ``{UNDERLYING}_UP_DOWN_{CADENCE}``
  (e.g. ``BTC_UP_DOWN_HOURLY``).
* Event markets with explicit year: ``{UNDERLYING}_{EVENT}_{YYYY}``
  (e.g. ``ELECTION_PRESIDENT_2028``).
* Event markets per-cycle: ``{UNDERLYING}_{EVENT}_PER_{CYCLE}``
  (e.g. ``FED_RATE_DECISION_PER_FOMC``).
* Single-fire markets: ``{UNDERLYING}_{EVENT}`` (e.g. ``OSCARS_BEST_PICTURE``).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from enum import StrEnum
from typing import Final, Literal


class CanonicalQuestionGroup(StrEnum):
    """Closed set of canonical-question-group identifiers for prediction markets.

    Adding a new group = adding it here AND seeding the metadata entry in
    :data:`CANONICAL_GROUP_METADATA` AND populating
    :data:`unified_api_contracts.canonical.crosscutting.honest_coverage.PREDICTION_GROUPS`.
    No half-measures: the writer guard at
    ``unified_trading_library.manifest_writer.ManifestWriter.record_captured``
    fires the moment a bundled prediction shard names a new group with no
    cluster registry seeded.
    """

    # Cadenced range-bracket markets — BTC / ETH / SPX up-or-down at the
    # close of a 1m/5m/15m interval / hour / day.
    # INTRADAY is a fallback for unknown-interval intraday slugs.
    # HOURLY → ~24/day; DAILY → 1/day; 5MIN → 288/day; 15MIN → 96/day.
    BTC_UP_DOWN_5MIN = "BTC_UP_DOWN_5MIN"
    BTC_UP_DOWN_15MIN = "BTC_UP_DOWN_15MIN"
    BTC_UP_DOWN_INTRADAY = "BTC_UP_DOWN_INTRADAY"  # fallback for unknown-interval intraday
    BTC_UP_DOWN_HOURLY = "BTC_UP_DOWN_HOURLY"
    BTC_UP_DOWN_DAILY = "BTC_UP_DOWN_DAILY"
    ETH_UP_DOWN_5MIN = "ETH_UP_DOWN_5MIN"
    ETH_UP_DOWN_15MIN = "ETH_UP_DOWN_15MIN"
    ETH_UP_DOWN_INTRADAY = "ETH_UP_DOWN_INTRADAY"  # fallback for unknown-interval intraday
    ETH_UP_DOWN_HOURLY = "ETH_UP_DOWN_HOURLY"
    ETH_UP_DOWN_DAILY = "ETH_UP_DOWN_DAILY"
    SPX_UP_DOWN_DAILY = "SPX_UP_DOWN_DAILY"

    # CME event-contract linked groups — added Phase 5 (predictions_master).
    # Each maps 1:1 to a CME EC* root via cme_polymarket_link.py.
    NDX_UP_DOWN_DAILY = "NDX_UP_DOWN_DAILY"  # ECNQ (E-mini NDX 100)
    RUT_UP_DOWN_DAILY = "RUT_UP_DOWN_DAILY"  # ECRTY (E-mini Russell 2000)
    DJIA_UP_DOWN_DAILY = "DJIA_UP_DOWN_DAILY"  # ECYM (E-mini Dow Jones)
    GOLD_UP_DOWN_DAILY = "GOLD_UP_DOWN_DAILY"  # ECGC (Gold)
    CRUDE_OIL_UP_DOWN_DAILY = "CRUDE_OIL_UP_DOWN_DAILY"  # ECCL (Crude WTI)
    NATGAS_UP_DOWN_DAILY = "NATGAS_UP_DOWN_DAILY"  # ECNG (Natural Gas)
    EUR_UP_DOWN_DAILY = "EUR_UP_DOWN_DAILY"  # EC6E (Euro FX)

    # Alt-coin daily up-or-down groups — mirror BTC/ETH (decision 338,
    # 2026-06-16). The taxonomy already tags these underlyings; only DAILY is
    # added (data-grounded: the observed alt-coin price markets are
    # range_bracket/monthly → DAILY-fallback). Intraday/hourly cadences are NOT
    # pre-built — add per-coin if/when those products list.
    SOL_UP_DOWN_DAILY = "SOL_UP_DOWN_DAILY"
    XRP_UP_DOWN_DAILY = "XRP_UP_DOWN_DAILY"
    DOGE_UP_DOWN_DAILY = "DOGE_UP_DOWN_DAILY"
    BNB_UP_DOWN_DAILY = "BNB_UP_DOWN_DAILY"
    ADA_UP_DOWN_DAILY = "ADA_UP_DOWN_DAILY"
    AVAX_UP_DOWN_DAILY = "AVAX_UP_DOWN_DAILY"
    LINK_UP_DOWN_DAILY = "LINK_UP_DOWN_DAILY"
    LTC_UP_DOWN_DAILY = "LTC_UP_DOWN_DAILY"
    SUI_UP_DOWN_DAILY = "SUI_UP_DOWN_DAILY"
    HYPE_UP_DOWN_DAILY = "HYPE_UP_DOWN_DAILY"

    # Macro events with FOMC / CPI cadence.
    FED_RATE_DECISION_PER_FOMC = "FED_RATE_DECISION_PER_FOMC"
    CPI_PRINT_PER_MONTH = "CPI_PRINT_PER_MONTH"

    # Macro economic-release groups — recurring prints the taxonomy already
    # tags (decision 338, 2026-06-16). Event-keyed (the resolution_period is
    # release-driven, not clock-driven). Extends the FED/CPI pair.
    UNEMPLOYMENT_RATE_PER_MONTH = "UNEMPLOYMENT_RATE_PER_MONTH"
    NONFARM_PAYROLLS_PER_MONTH = "NONFARM_PAYROLLS_PER_MONTH"
    GDP_PRINT_PER_QUARTER = "GDP_PRINT_PER_QUARTER"
    PPI_PRINT_PER_MONTH = "PPI_PRINT_PER_MONTH"
    PCE_PRINT_PER_MONTH = "PCE_PRINT_PER_MONTH"
    TREASURY_YIELD_PER_PRINT = "TREASURY_YIELD_PER_PRINT"
    CRYPTO_FEAR_GREED_INDEX = "CRYPTO_FEAR_GREED_INDEX"

    # Weather — daily highest-temperature markets (London / NYC factories;
    # decision 338, 2026-06-16). Both range_bracket ("between N-Nf") and binary
    # ("Nf or higher") route here.
    WEATHER_TEMP_DAILY = "WEATHER_TEMP_DAILY"

    # Election markets with explicit year (no floating; historical readback
    # must remain unambiguous per Phase 0 audit recommendation).
    ELECTION_PRESIDENT_2028 = "ELECTION_PRESIDENT_2028"

    # Single-fire entertainment markets — populated as needed when real
    # consumers surface them via the override dicts.
    OSCARS_BEST_PICTURE = "OSCARS_BEST_PICTURE"

    # === decision 338 pass 2 (2026-06-16) — granular split per operator ===
    # Crypto PRICE-RANGE ("between $X-$Y" / multistrike / above-below) — split
    # OUT of {COIN}_UP_DOWN (which is direction-only). Retrofits BTC/ETH.
    BTC_PRICE_RANGE_DAILY = "BTC_PRICE_RANGE_DAILY"
    ETH_PRICE_RANGE_DAILY = "ETH_PRICE_RANGE_DAILY"
    SOL_PRICE_RANGE_DAILY = "SOL_PRICE_RANGE_DAILY"
    XRP_PRICE_RANGE_DAILY = "XRP_PRICE_RANGE_DAILY"
    DOGE_PRICE_RANGE_DAILY = "DOGE_PRICE_RANGE_DAILY"
    BNB_PRICE_RANGE_DAILY = "BNB_PRICE_RANGE_DAILY"
    ADA_PRICE_RANGE_DAILY = "ADA_PRICE_RANGE_DAILY"
    AVAX_PRICE_RANGE_DAILY = "AVAX_PRICE_RANGE_DAILY"
    LINK_PRICE_RANGE_DAILY = "LINK_PRICE_RANGE_DAILY"
    LTC_PRICE_RANGE_DAILY = "LTC_PRICE_RANGE_DAILY"
    SUI_PRICE_RANGE_DAILY = "SUI_PRICE_RANGE_DAILY"
    HYPE_PRICE_RANGE_DAILY = "HYPE_PRICE_RANGE_DAILY"

    # Political-figure split (approval / statements / executive-order).
    TRUMP_APPROVAL_RATING = "TRUMP_APPROVAL_RATING"
    TRUMP_STATEMENTS = "TRUMP_STATEMENTS"
    TRUMP_EXEC_ORDER = "TRUMP_EXEC_ORDER"
    # Tech-personality (Elon) recurring factories.
    ELON_TWEET_COUNT = "ELON_TWEET_COUNT"
    ELON_STATEMENTS = "ELON_STATEMENTS"
    ELON_NET_WORTH = "ELON_NET_WORTH"

    # Geopolitics conflict-by-date — two high-volume pairs + a long-tail catch.
    GEO_ISRAEL_IRAN = "GEO_ISRAEL_IRAN"
    GEO_RUSSIA_UKRAINE = "GEO_RUSSIA_UKRAINE"
    GEO_OTHER_BY_DATE = "GEO_OTHER_BY_DATE"

    # Culture — box-office opening weekend.
    BOX_OFFICE_OPENING_WEEKEND = "BOX_OFFICE_OPENING_WEEKEND"

    # Commodity price-LEVEL ("gold above $X by DATE") — distinct from the
    # CME-linked daily-direction {COMMODITY}_UP_DOWN_DAILY groups.
    GOLD_PRICE_LEVEL = "GOLD_PRICE_LEVEL"
    SILVER_PRICE_LEVEL = "SILVER_PRICE_LEVEL"
    CRUDE_OIL_PRICE_LEVEL = "CRUDE_OIL_PRICE_LEVEL"

    # === decision 338 pass 2 sports (per operator: league x market-type;
    # fixture = the recurring instance/market_id within the group) ===
    # US team sports — MATCH (moneyline) / SPREAD / TOTAL (+ MLB NRFI).
    SPORTS_MLB_MATCH = "SPORTS_MLB_MATCH"
    SPORTS_MLB_SPREAD = "SPORTS_MLB_SPREAD"
    SPORTS_MLB_TOTAL = "SPORTS_MLB_TOTAL"
    SPORTS_MLB_NRFI = "SPORTS_MLB_NRFI"
    SPORTS_NFL_MATCH = "SPORTS_NFL_MATCH"
    SPORTS_NFL_SPREAD = "SPORTS_NFL_SPREAD"
    SPORTS_NFL_TOTAL = "SPORTS_NFL_TOTAL"
    SPORTS_NBA_MATCH = "SPORTS_NBA_MATCH"
    SPORTS_NBA_SPREAD = "SPORTS_NBA_SPREAD"
    SPORTS_NBA_TOTAL = "SPORTS_NBA_TOTAL"
    SPORTS_NHL_MATCH = "SPORTS_NHL_MATCH"
    SPORTS_NHL_SPREAD = "SPORTS_NHL_SPREAD"
    SPORTS_NHL_TOTAL = "SPORTS_NHL_TOTAL"
    # Football — MATCH (3-way: home/draw/away) / TOTAL.
    SPORTS_EPL_MATCH = "SPORTS_EPL_MATCH"
    SPORTS_EPL_TOTAL = "SPORTS_EPL_TOTAL"
    SPORTS_UEFA_MATCH = "SPORTS_UEFA_MATCH"
    SPORTS_UEFA_TOTAL = "SPORTS_UEFA_TOTAL"
    SPORTS_CHAMPIONS_LEAGUE_MATCH = "SPORTS_CHAMPIONS_LEAGUE_MATCH"
    SPORTS_LA_LIGA_MATCH = "SPORTS_LA_LIGA_MATCH"
    SPORTS_SERIE_A_MATCH = "SPORTS_SERIE_A_MATCH"
    SPORTS_BUNDESLIGA_MATCH = "SPORTS_BUNDESLIGA_MATCH"
    SPORTS_WORLD_CUP_MATCH = "SPORTS_WORLD_CUP_MATCH"
    # F1 — GP winner / constructor / generic-season (MATCH).
    SPORTS_F1_MATCH = "SPORTS_F1_MATCH"
    SPORTS_F1_GP_WINNER = "SPORTS_F1_GP_WINNER"
    SPORTS_F1_CONSTRUCTOR = "SPORTS_F1_CONSTRUCTOR"
    # Individual / combat sports — MATCH (tournament/bout winner).
    SPORTS_TENNIS_MATCH = "SPORTS_TENNIS_MATCH"
    SPORTS_GOLF_MATCH = "SPORTS_GOLF_MATCH"
    SPORTS_UFC_MATCH = "SPORTS_UFC_MATCH"
    SPORTS_BOXING_MATCH = "SPORTS_BOXING_MATCH"
    SPORTS_OLYMPICS_MATCH = "SPORTS_OLYMPICS_MATCH"

    # Explicit small residual for genuinely-uncategorised (category=MISC)
    # novelty markets, so OTHER stops being a silent ~80% catch-all.
    MISC_NOVELTY = "MISC_NOVELTY"

    # Catch-all bucket for low-confidence classifier output. Manifest rows
    # under ``OTHER`` are not blocked from capture but flagged in audits.
    OTHER = "OTHER"


_Cadence = Literal["1min", "5min", "15min", "intraday", "hourly", "daily", "weekly", "monthly", "irregular", "single"]
_ResolutionBasis = Literal["price_threshold", "binary_outcome", "multi_outcome"]


@dataclass(frozen=True)
class CanonicalGroupMetadata:
    """Per-canonical_question_group metadata used by the cluster gate +
    coverage denominator.

    * ``cadence`` drives ``expected_market_ids_per_day`` defaults — HOURLY
      → 24, DAILY → 1, etc. ``irregular`` covers macro events that don't
      tick on a clock (Fed decisions, CPI prints, election cycles).
    * ``expected_market_ids_per_day`` is the registry-side claim for the
      cluster gate; per-day overrides for irregular cadences live in
      :func:`expected_market_ids_for_canonical_group`
      (in :mod:`.lifecycle`) which consults the live lifecycle table.
    * ``resolution_basis`` informs feature engineering — price-threshold
      groups carry an underlying spot ref; binary / multi-outcome groups
      consume the YES/NO / candidate prices directly.
    * ``settlement_lag`` is the typical ``settlement_time - resolution_time``
      gap; UMA-undisputed Polymarket = ~2h, disputed = 48-72h. Used as a
      fallback when ``settlement_time`` is unavailable from the source.
    """

    group: CanonicalQuestionGroup
    cadence: _Cadence
    expected_market_ids_per_day: int
    resolution_basis: _ResolutionBasis
    settlement_lag: timedelta


_HOUR = timedelta(hours=1)
_DAY = timedelta(hours=24)
_WEEK = timedelta(weeks=1)


CANONICAL_GROUP_METADATA: Final[dict[CanonicalQuestionGroup, CanonicalGroupMetadata]] = {
    CanonicalQuestionGroup.BTC_UP_DOWN_5MIN: CanonicalGroupMetadata(
        group=CanonicalQuestionGroup.BTC_UP_DOWN_5MIN,
        cadence="5min",
        expected_market_ids_per_day=288,
        resolution_basis="price_threshold",
        settlement_lag=2 * _HOUR,
    ),
    CanonicalQuestionGroup.BTC_UP_DOWN_15MIN: CanonicalGroupMetadata(
        group=CanonicalQuestionGroup.BTC_UP_DOWN_15MIN,
        cadence="15min",
        expected_market_ids_per_day=96,
        resolution_basis="price_threshold",
        settlement_lag=2 * _HOUR,
    ),
    CanonicalQuestionGroup.BTC_UP_DOWN_INTRADAY: CanonicalGroupMetadata(
        group=CanonicalQuestionGroup.BTC_UP_DOWN_INTRADAY,
        cadence="intraday",
        expected_market_ids_per_day=288,  # fallback for unknown-interval; lifecycle table overrides
        resolution_basis="price_threshold",
        settlement_lag=2 * _HOUR,
    ),
    CanonicalQuestionGroup.BTC_UP_DOWN_HOURLY: CanonicalGroupMetadata(
        group=CanonicalQuestionGroup.BTC_UP_DOWN_HOURLY,
        cadence="hourly",
        expected_market_ids_per_day=24,
        resolution_basis="price_threshold",
        settlement_lag=2 * _HOUR,
    ),
    CanonicalQuestionGroup.BTC_UP_DOWN_DAILY: CanonicalGroupMetadata(
        group=CanonicalQuestionGroup.BTC_UP_DOWN_DAILY,
        cadence="daily",
        expected_market_ids_per_day=1,
        resolution_basis="price_threshold",
        settlement_lag=2 * _HOUR,
    ),
    CanonicalQuestionGroup.ETH_UP_DOWN_5MIN: CanonicalGroupMetadata(
        group=CanonicalQuestionGroup.ETH_UP_DOWN_5MIN,
        cadence="5min",
        expected_market_ids_per_day=288,
        resolution_basis="price_threshold",
        settlement_lag=2 * _HOUR,
    ),
    CanonicalQuestionGroup.ETH_UP_DOWN_15MIN: CanonicalGroupMetadata(
        group=CanonicalQuestionGroup.ETH_UP_DOWN_15MIN,
        cadence="15min",
        expected_market_ids_per_day=96,
        resolution_basis="price_threshold",
        settlement_lag=2 * _HOUR,
    ),
    CanonicalQuestionGroup.ETH_UP_DOWN_INTRADAY: CanonicalGroupMetadata(
        group=CanonicalQuestionGroup.ETH_UP_DOWN_INTRADAY,
        cadence="intraday",
        expected_market_ids_per_day=288,  # fallback for unknown-interval; lifecycle table overrides
        resolution_basis="price_threshold",
        settlement_lag=2 * _HOUR,
    ),
    CanonicalQuestionGroup.ETH_UP_DOWN_HOURLY: CanonicalGroupMetadata(
        group=CanonicalQuestionGroup.ETH_UP_DOWN_HOURLY,
        cadence="hourly",
        expected_market_ids_per_day=24,
        resolution_basis="price_threshold",
        settlement_lag=2 * _HOUR,
    ),
    CanonicalQuestionGroup.ETH_UP_DOWN_DAILY: CanonicalGroupMetadata(
        group=CanonicalQuestionGroup.ETH_UP_DOWN_DAILY,
        cadence="daily",
        expected_market_ids_per_day=1,
        resolution_basis="price_threshold",
        settlement_lag=2 * _HOUR,
    ),
    CanonicalQuestionGroup.SPX_UP_DOWN_DAILY: CanonicalGroupMetadata(
        group=CanonicalQuestionGroup.SPX_UP_DOWN_DAILY,
        cadence="daily",
        expected_market_ids_per_day=1,
        resolution_basis="price_threshold",
        settlement_lag=2 * _HOUR,
    ),
    CanonicalQuestionGroup.NDX_UP_DOWN_DAILY: CanonicalGroupMetadata(
        group=CanonicalQuestionGroup.NDX_UP_DOWN_DAILY,
        cadence="daily",
        expected_market_ids_per_day=1,
        resolution_basis="price_threshold",
        settlement_lag=2 * _HOUR,
    ),
    CanonicalQuestionGroup.RUT_UP_DOWN_DAILY: CanonicalGroupMetadata(
        group=CanonicalQuestionGroup.RUT_UP_DOWN_DAILY,
        cadence="daily",
        expected_market_ids_per_day=1,
        resolution_basis="price_threshold",
        settlement_lag=2 * _HOUR,
    ),
    CanonicalQuestionGroup.DJIA_UP_DOWN_DAILY: CanonicalGroupMetadata(
        group=CanonicalQuestionGroup.DJIA_UP_DOWN_DAILY,
        cadence="daily",
        expected_market_ids_per_day=1,
        resolution_basis="price_threshold",
        settlement_lag=2 * _HOUR,
    ),
    CanonicalQuestionGroup.GOLD_UP_DOWN_DAILY: CanonicalGroupMetadata(
        group=CanonicalQuestionGroup.GOLD_UP_DOWN_DAILY,
        cadence="daily",
        expected_market_ids_per_day=1,
        resolution_basis="price_threshold",
        settlement_lag=2 * _HOUR,
    ),
    CanonicalQuestionGroup.CRUDE_OIL_UP_DOWN_DAILY: CanonicalGroupMetadata(
        group=CanonicalQuestionGroup.CRUDE_OIL_UP_DOWN_DAILY,
        cadence="daily",
        expected_market_ids_per_day=1,
        resolution_basis="price_threshold",
        settlement_lag=2 * _HOUR,
    ),
    CanonicalQuestionGroup.NATGAS_UP_DOWN_DAILY: CanonicalGroupMetadata(
        group=CanonicalQuestionGroup.NATGAS_UP_DOWN_DAILY,
        cadence="daily",
        expected_market_ids_per_day=1,
        resolution_basis="price_threshold",
        settlement_lag=2 * _HOUR,
    ),
    CanonicalQuestionGroup.EUR_UP_DOWN_DAILY: CanonicalGroupMetadata(
        group=CanonicalQuestionGroup.EUR_UP_DOWN_DAILY,
        cadence="daily",
        expected_market_ids_per_day=1,
        resolution_basis="price_threshold",
        settlement_lag=2 * _HOUR,
    ),
    CanonicalQuestionGroup.FED_RATE_DECISION_PER_FOMC: CanonicalGroupMetadata(
        group=CanonicalQuestionGroup.FED_RATE_DECISION_PER_FOMC,
        cadence="irregular",
        # 8 FOMC meetings per year ≈ 1 active market on a meeting-week,
        # 0 otherwise. Cluster gate consults the live lifecycle table.
        expected_market_ids_per_day=1,
        resolution_basis="multi_outcome",
        settlement_lag=24 * _HOUR,
    ),
    CanonicalQuestionGroup.CPI_PRINT_PER_MONTH: CanonicalGroupMetadata(
        group=CanonicalQuestionGroup.CPI_PRINT_PER_MONTH,
        cadence="monthly",
        expected_market_ids_per_day=1,
        resolution_basis="multi_outcome",
        settlement_lag=24 * _HOUR,
    ),
    CanonicalQuestionGroup.ELECTION_PRESIDENT_2028: CanonicalGroupMetadata(
        group=CanonicalQuestionGroup.ELECTION_PRESIDENT_2028,
        cadence="single",
        expected_market_ids_per_day=1,
        resolution_basis="multi_outcome",
        settlement_lag=72 * _HOUR,
    ),
    CanonicalQuestionGroup.OSCARS_BEST_PICTURE: CanonicalGroupMetadata(
        group=CanonicalQuestionGroup.OSCARS_BEST_PICTURE,
        cadence="single",
        expected_market_ids_per_day=1,
        resolution_basis="multi_outcome",
        settlement_lag=24 * _HOUR,
    ),
    # Alt-coin daily up-or-down — mirror BTC/ETH DAILY (decision 338). Floors
    # set conservatively at 500 (alts thinner than BTC/ETH on Polymarket).
    **{
        group: CanonicalGroupMetadata(
            group=group,
            cadence="daily",
            expected_market_ids_per_day=1,
            resolution_basis="price_threshold",
            settlement_lag=2 * _HOUR,
        )
        for group in (
            CanonicalQuestionGroup.SOL_UP_DOWN_DAILY,
            CanonicalQuestionGroup.XRP_UP_DOWN_DAILY,
            CanonicalQuestionGroup.DOGE_UP_DOWN_DAILY,
            CanonicalQuestionGroup.BNB_UP_DOWN_DAILY,
            CanonicalQuestionGroup.ADA_UP_DOWN_DAILY,
            CanonicalQuestionGroup.AVAX_UP_DOWN_DAILY,
            CanonicalQuestionGroup.LINK_UP_DOWN_DAILY,
            CanonicalQuestionGroup.LTC_UP_DOWN_DAILY,
            CanonicalQuestionGroup.SUI_UP_DOWN_DAILY,
            CanonicalQuestionGroup.HYPE_UP_DOWN_DAILY,
        )
    },
    # Macro economic-release groups (decision 338).
    CanonicalQuestionGroup.UNEMPLOYMENT_RATE_PER_MONTH: CanonicalGroupMetadata(
        group=CanonicalQuestionGroup.UNEMPLOYMENT_RATE_PER_MONTH,
        cadence="monthly",
        expected_market_ids_per_day=1,
        resolution_basis="binary_outcome",
        settlement_lag=24 * _HOUR,
    ),
    CanonicalQuestionGroup.NONFARM_PAYROLLS_PER_MONTH: CanonicalGroupMetadata(
        group=CanonicalQuestionGroup.NONFARM_PAYROLLS_PER_MONTH,
        cadence="monthly",
        expected_market_ids_per_day=1,
        resolution_basis="binary_outcome",
        settlement_lag=24 * _HOUR,
    ),
    CanonicalQuestionGroup.GDP_PRINT_PER_QUARTER: CanonicalGroupMetadata(
        group=CanonicalQuestionGroup.GDP_PRINT_PER_QUARTER,
        cadence="irregular",  # quarterly; no "quarterly" literal in _Cadence
        expected_market_ids_per_day=1,
        resolution_basis="binary_outcome",
        settlement_lag=24 * _HOUR,
    ),
    CanonicalQuestionGroup.PPI_PRINT_PER_MONTH: CanonicalGroupMetadata(
        group=CanonicalQuestionGroup.PPI_PRINT_PER_MONTH,
        cadence="monthly",
        expected_market_ids_per_day=1,
        resolution_basis="binary_outcome",
        settlement_lag=24 * _HOUR,
    ),
    CanonicalQuestionGroup.PCE_PRINT_PER_MONTH: CanonicalGroupMetadata(
        group=CanonicalQuestionGroup.PCE_PRINT_PER_MONTH,
        cadence="monthly",
        expected_market_ids_per_day=1,
        resolution_basis="binary_outcome",
        settlement_lag=24 * _HOUR,
    ),
    CanonicalQuestionGroup.TREASURY_YIELD_PER_PRINT: CanonicalGroupMetadata(
        group=CanonicalQuestionGroup.TREASURY_YIELD_PER_PRINT,
        cadence="weekly",
        expected_market_ids_per_day=1,
        resolution_basis="price_threshold",
        settlement_lag=24 * _HOUR,
    ),
    CanonicalQuestionGroup.CRYPTO_FEAR_GREED_INDEX: CanonicalGroupMetadata(
        group=CanonicalQuestionGroup.CRYPTO_FEAR_GREED_INDEX,
        cadence="daily",
        expected_market_ids_per_day=1,
        resolution_basis="price_threshold",
        settlement_lag=24 * _HOUR,
    ),
    # Weather daily highest-temperature (decision 338).
    CanonicalQuestionGroup.WEATHER_TEMP_DAILY: CanonicalGroupMetadata(
        group=CanonicalQuestionGroup.WEATHER_TEMP_DAILY,
        cadence="daily",
        expected_market_ids_per_day=1,
        resolution_basis="price_threshold",
        settlement_lag=24 * _HOUR,
    ),
    # === decision 338 pass 2 metadata ===
    # Crypto PRICE-RANGE — daily price-level markets (mirror the UP_DOWN daily).
    **{
        group: CanonicalGroupMetadata(
            group=group,
            cadence="daily",
            expected_market_ids_per_day=1,
            resolution_basis="price_threshold",
            settlement_lag=2 * _HOUR,
        )
        for group in (
            CanonicalQuestionGroup.BTC_PRICE_RANGE_DAILY,
            CanonicalQuestionGroup.ETH_PRICE_RANGE_DAILY,
            CanonicalQuestionGroup.SOL_PRICE_RANGE_DAILY,
            CanonicalQuestionGroup.XRP_PRICE_RANGE_DAILY,
            CanonicalQuestionGroup.DOGE_PRICE_RANGE_DAILY,
            CanonicalQuestionGroup.BNB_PRICE_RANGE_DAILY,
            CanonicalQuestionGroup.ADA_PRICE_RANGE_DAILY,
            CanonicalQuestionGroup.AVAX_PRICE_RANGE_DAILY,
            CanonicalQuestionGroup.LINK_PRICE_RANGE_DAILY,
            CanonicalQuestionGroup.LTC_PRICE_RANGE_DAILY,
            CanonicalQuestionGroup.SUI_PRICE_RANGE_DAILY,
            CanonicalQuestionGroup.HYPE_PRICE_RANGE_DAILY,
        )
    },
    CanonicalQuestionGroup.TRUMP_APPROVAL_RATING: CanonicalGroupMetadata(
        group=CanonicalQuestionGroup.TRUMP_APPROVAL_RATING,
        cadence="daily",
        expected_market_ids_per_day=1,
        resolution_basis="price_threshold",
        settlement_lag=24 * _HOUR,
    ),
    CanonicalQuestionGroup.TRUMP_STATEMENTS: CanonicalGroupMetadata(
        group=CanonicalQuestionGroup.TRUMP_STATEMENTS,
        cadence="irregular",
        expected_market_ids_per_day=1,
        resolution_basis="binary_outcome",
        settlement_lag=24 * _HOUR,
    ),
    CanonicalQuestionGroup.TRUMP_EXEC_ORDER: CanonicalGroupMetadata(
        group=CanonicalQuestionGroup.TRUMP_EXEC_ORDER,
        cadence="irregular",
        expected_market_ids_per_day=1,
        resolution_basis="binary_outcome",
        settlement_lag=24 * _HOUR,
    ),
    CanonicalQuestionGroup.ELON_TWEET_COUNT: CanonicalGroupMetadata(
        group=CanonicalQuestionGroup.ELON_TWEET_COUNT,
        cadence="weekly",
        expected_market_ids_per_day=1,
        resolution_basis="price_threshold",
        settlement_lag=24 * _HOUR,
    ),
    CanonicalQuestionGroup.ELON_STATEMENTS: CanonicalGroupMetadata(
        group=CanonicalQuestionGroup.ELON_STATEMENTS,
        cadence="irregular",
        expected_market_ids_per_day=1,
        resolution_basis="binary_outcome",
        settlement_lag=24 * _HOUR,
    ),
    CanonicalQuestionGroup.ELON_NET_WORTH: CanonicalGroupMetadata(
        group=CanonicalQuestionGroup.ELON_NET_WORTH,
        cadence="irregular",
        expected_market_ids_per_day=1,
        resolution_basis="price_threshold",
        settlement_lag=24 * _HOUR,
    ),
    **{
        group: CanonicalGroupMetadata(
            group=group,
            cadence="irregular",
            expected_market_ids_per_day=1,
            resolution_basis="binary_outcome",
            settlement_lag=24 * _HOUR,
        )
        for group in (
            CanonicalQuestionGroup.GEO_ISRAEL_IRAN,
            CanonicalQuestionGroup.GEO_RUSSIA_UKRAINE,
            CanonicalQuestionGroup.GEO_OTHER_BY_DATE,
        )
    },
    CanonicalQuestionGroup.BOX_OFFICE_OPENING_WEEKEND: CanonicalGroupMetadata(
        group=CanonicalQuestionGroup.BOX_OFFICE_OPENING_WEEKEND,
        cadence="irregular",
        expected_market_ids_per_day=1,
        resolution_basis="price_threshold",
        settlement_lag=24 * _HOUR,
    ),
    **{
        group: CanonicalGroupMetadata(
            group=group,
            cadence="irregular",
            expected_market_ids_per_day=1,
            resolution_basis="price_threshold",
            settlement_lag=24 * _HOUR,
        )
        for group in (
            CanonicalQuestionGroup.GOLD_PRICE_LEVEL,
            CanonicalQuestionGroup.SILVER_PRICE_LEVEL,
            CanonicalQuestionGroup.CRUDE_OIL_PRICE_LEVEL,
        )
    },
    # === decision 338 pass 2 sports metadata (event/fixture-driven) ===
    # MATCH / GP_WINNER / CONSTRUCTOR → multi_outcome (winner-of-field / 3-way).
    **{
        group: CanonicalGroupMetadata(
            group=group,
            cadence="irregular",
            expected_market_ids_per_day=1,
            resolution_basis="multi_outcome",
            settlement_lag=24 * _HOUR,
        )
        for group in (
            CanonicalQuestionGroup.SPORTS_MLB_MATCH,
            CanonicalQuestionGroup.SPORTS_NFL_MATCH,
            CanonicalQuestionGroup.SPORTS_NBA_MATCH,
            CanonicalQuestionGroup.SPORTS_NHL_MATCH,
            CanonicalQuestionGroup.SPORTS_EPL_MATCH,
            CanonicalQuestionGroup.SPORTS_UEFA_MATCH,
            CanonicalQuestionGroup.SPORTS_CHAMPIONS_LEAGUE_MATCH,
            CanonicalQuestionGroup.SPORTS_LA_LIGA_MATCH,
            CanonicalQuestionGroup.SPORTS_SERIE_A_MATCH,
            CanonicalQuestionGroup.SPORTS_BUNDESLIGA_MATCH,
            CanonicalQuestionGroup.SPORTS_WORLD_CUP_MATCH,
            CanonicalQuestionGroup.SPORTS_F1_MATCH,
            CanonicalQuestionGroup.SPORTS_F1_GP_WINNER,
            CanonicalQuestionGroup.SPORTS_F1_CONSTRUCTOR,
            CanonicalQuestionGroup.SPORTS_TENNIS_MATCH,
            CanonicalQuestionGroup.SPORTS_GOLF_MATCH,
            CanonicalQuestionGroup.SPORTS_UFC_MATCH,
            CanonicalQuestionGroup.SPORTS_BOXING_MATCH,
            CanonicalQuestionGroup.SPORTS_OLYMPICS_MATCH,
        )
    },
    # SPREAD / TOTAL / NRFI → binary_outcome (cover / over-under / yes-no).
    **{
        group: CanonicalGroupMetadata(
            group=group,
            cadence="irregular",
            expected_market_ids_per_day=1,
            resolution_basis="binary_outcome",
            settlement_lag=24 * _HOUR,
        )
        for group in (
            CanonicalQuestionGroup.SPORTS_MLB_SPREAD,
            CanonicalQuestionGroup.SPORTS_MLB_TOTAL,
            CanonicalQuestionGroup.SPORTS_MLB_NRFI,
            CanonicalQuestionGroup.SPORTS_NFL_SPREAD,
            CanonicalQuestionGroup.SPORTS_NFL_TOTAL,
            CanonicalQuestionGroup.SPORTS_NBA_SPREAD,
            CanonicalQuestionGroup.SPORTS_NBA_TOTAL,
            CanonicalQuestionGroup.SPORTS_NHL_SPREAD,
            CanonicalQuestionGroup.SPORTS_NHL_TOTAL,
            CanonicalQuestionGroup.SPORTS_EPL_TOTAL,
            CanonicalQuestionGroup.SPORTS_UEFA_TOTAL,
        )
    },
    CanonicalQuestionGroup.MISC_NOVELTY: CanonicalGroupMetadata(
        group=CanonicalQuestionGroup.MISC_NOVELTY,
        cadence="irregular",
        expected_market_ids_per_day=0,
        resolution_basis="binary_outcome",
        settlement_lag=24 * _HOUR,
    ),
    CanonicalQuestionGroup.OTHER: CanonicalGroupMetadata(
        group=CanonicalQuestionGroup.OTHER,
        cadence="irregular",
        expected_market_ids_per_day=0,
        resolution_basis="binary_outcome",
        settlement_lag=24 * _HOUR,
    ),
}


__all__ = [
    "CANONICAL_GROUP_METADATA",
    "CanonicalGroupMetadata",
    "CanonicalQuestionGroup",
]
