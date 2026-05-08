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
    # close of an hour / day. HOURLY → ~24 markets/day; DAILY → 1 market/day.
    BTC_UP_DOWN_HOURLY = "BTC_UP_DOWN_HOURLY"
    BTC_UP_DOWN_DAILY = "BTC_UP_DOWN_DAILY"
    ETH_UP_DOWN_HOURLY = "ETH_UP_DOWN_HOURLY"
    ETH_UP_DOWN_DAILY = "ETH_UP_DOWN_DAILY"
    SPX_UP_DOWN_DAILY = "SPX_UP_DOWN_DAILY"

    # Macro events with FOMC / CPI cadence.
    FED_RATE_DECISION_PER_FOMC = "FED_RATE_DECISION_PER_FOMC"
    CPI_PRINT_PER_MONTH = "CPI_PRINT_PER_MONTH"

    # Election markets with explicit year (no floating; historical readback
    # must remain unambiguous per Phase 0 audit recommendation).
    ELECTION_PRESIDENT_2028 = "ELECTION_PRESIDENT_2028"

    # Single-fire entertainment markets — populated as needed when real
    # consumers surface them via the override dicts.
    OSCARS_BEST_PICTURE = "OSCARS_BEST_PICTURE"

    # Catch-all bucket for low-confidence classifier output. Manifest rows
    # under ``OTHER`` are not blocked from capture but flagged in audits.
    OTHER = "OTHER"


_Cadence = Literal["hourly", "daily", "weekly", "monthly", "irregular", "single"]
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
