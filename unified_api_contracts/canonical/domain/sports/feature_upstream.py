"""Honest-coverage SSOT for features-sports-service calculators (Phase 1).

Every features-sports-service calculator depends on a specific set of upstream
data entities. This module declares the dependency graph as the single source
of truth, so both the features compute logic AND deployment-api data-status
calc can answer the same question: "for (source, entity, league, date), is
this shard expected to have a manifest row?"

Three states honest-coverage distinguishes:
  1. **NaN-expected** — upstream legitimately doesn't cover this combo
     (e.g. understat XG for MLS). Feature is NaN-by-design; ``captured`` in
     the data-status UI.
  2. **NaN-empty-confirmed** — upstream is in-coverage but returned empty
     (e.g. league had no fixture that week). ``empty_confirmed`` status.
  3. **Skipped (genuine gap)** — upstream ``attempted_failed`` or no
     manifest row, AND in-coverage. Compute is skipped + manifest marked
     ``attempted_failed`` with reason ``upstream_missing``.

The ``in_coverage`` helper here returns True iff the (source, data_type,
league, date) is *expected* to have data — i.e. case 2 or 3 territory.
False = case 1 (NaN-by-design is fine).

Plan: features_sports_honest_coverage_2026_05_05.plan.md
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date as date_type
from datetime import datetime

from .league_data import (
    clip_dates_to_source_coverage,
    is_in_known_gap,
    is_pre_launch_date,
)
from .provider_league_ids import get_entity_league_coverage


@dataclass(frozen=True)
class UpstreamReq:
    """A single upstream dependency for a features-sports calculator.

    Args:
        source: Source key — matches ``SPORTS_DATA_TYPE_TO_SOURCE`` values
            (``api_football`` / ``footystats`` / ``understat`` / ``transfermarkt``
            / ``soccer_football_info`` / ``open_meteo`` / ``odds_api`` /
            ``mdps_odds_horizon_bucket``). Special token ``"derived"`` for
            inputs that come from another calculator's output (Stage D).
        data_type: UAC canonical data_type (``FIXTURES``, ``XG``,
            ``PLAYER_VALUES``, ``ODDS_HORIZON_BUCKET``, etc.). For
            ``source="derived"``, this is the upstream calculator's name
            (e.g. ``"team_xg"``).
        required: If True, missing upstream → skip the shard with
            ``upstream_missing`` reason. If False, missing → NaN that column
            but compute the rest (used for optional fallbacks like
            transfermarkt PLAYER_VALUES enriching a primary api_football
            feature).
        notes: Optional human-readable note about why this requirement
            exists (e.g. "fallback to base xG model when understat is
            out-of-coverage").
    """

    source: str
    data_type: str
    required: bool = True
    notes: str = ""


# Per-calculator upstream requirements. Keyed by calculator name as it
# appears in ``features_sports_service.exporters.derived_features_exporter``
# dispatcher. Inventory derived from Phase 0 audit (1,142 features across
# 34 calculators) — see plan Phase 0 corrected output for the full map.
#
# Stage tag in the comments mirrors the plan's stage breakdown:
#   A = single-source (Phase 4 backfill)
#   C = cross-source join (Phase 6)
#   D = enriched / derived (Phase 7)
FEATURE_UPSTREAM_REQUIREMENTS: dict[str, list[UpstreamReq]] = {
    # ------------------------------------------------------------------
    # Stage A — single-source calculators
    # ------------------------------------------------------------------
    "team_form": [
        UpstreamReq(source="api_football", data_type="FIXTURES"),
    ],
    "team_goals": [
        UpstreamReq(source="api_football", data_type="FIXTURES"),
    ],
    "season_context": [
        UpstreamReq(source="api_football", data_type="FIXTURES"),
        UpstreamReq(source="api_football", data_type="STANDINGS"),
    ],
    "goal_timing": [
        UpstreamReq(source="api_football", data_type="FIXTURE_EVENTS"),
    ],
    "ht_features": [
        UpstreamReq(source="footystats", data_type="MATCHES"),
    ],
    "manager_calculator": [
        UpstreamReq(source="api_football", data_type="FIXTURES"),
        UpstreamReq(source="api_football", data_type="TEAMS", required=False),
    ],
    "formation_calculator": [
        UpstreamReq(source="api_football", data_type="FIXTURE_LINEUPS"),
        UpstreamReq(source="api_football", data_type="FIXTURES"),
    ],
    "injury_impact_calculator": [
        UpstreamReq(source="api_football", data_type="INJURIES"),
    ],
    "travel_calculator": [
        UpstreamReq(source="api_football", data_type="FIXTURES"),
        UpstreamReq(source="api_football", data_type="VENUES", required=False),
    ],
    "european_fatigue_calculator": [
        UpstreamReq(source="api_football", data_type="FIXTURES"),
    ],
    "elo_calculator": [
        UpstreamReq(source="api_football", data_type="FIXTURES"),
    ],
    "h2h_calculator": [
        UpstreamReq(source="api_football", data_type="FIXTURES"),
    ],
    "advanced_stats_calculator": [
        UpstreamReq(source="api_football", data_type="FIXTURE_STATS"),
        UpstreamReq(source="api_football", data_type="FIXTURES"),
    ],
    "venue_context": [
        UpstreamReq(source="api_football", data_type="FIXTURES"),
        UpstreamReq(source="api_football", data_type="VENUES", required=False),
    ],
    "league_calculator": [
        UpstreamReq(source="api_football", data_type="FIXTURES"),
        UpstreamReq(source="api_football", data_type="STANDINGS"),
    ],
    "referee_features": [
        UpstreamReq(source="api_football", data_type="FIXTURES"),
    ],
    "squad_value_calculator": [
        UpstreamReq(source="transfermarkt", data_type="PLAYER_VALUES"),
        UpstreamReq(source="transfermarkt", data_type="TRANSFER_RECORDS", required=False),
    ],
    "weather_calculator": [
        UpstreamReq(source="open_meteo", data_type="WEATHER"),
        UpstreamReq(source="api_football", data_type="FIXTURES"),
    ],
    "sfi_progressive": [
        UpstreamReq(source="soccer_football_info", data_type="SFI_PROGRESSIVE_STATS"),
    ],
    "footystats_predictions": [
        UpstreamReq(source="footystats", data_type="PREDICTIONS"),
    ],
    # ------------------------------------------------------------------
    # Stage C — cross-source join calculators
    # ------------------------------------------------------------------
    "team_xg": [
        UpstreamReq(source="understat", data_type="XG"),
        UpstreamReq(source="api_football", data_type="FIXTURES"),
    ],
    "halftime_calculator": [
        UpstreamReq(source="footystats", data_type="MATCHES"),
        UpstreamReq(source="api_football", data_type="FIXTURE_STATS"),
    ],
    "transfer_window_calculator": [
        UpstreamReq(source="transfermarkt", data_type="PLAYER_VALUES"),
        UpstreamReq(source="transfermarkt", data_type="TRANSFER_RECORDS", required=False),
        UpstreamReq(source="api_football", data_type="FIXTURE_LINEUPS", required=False),
    ],
    "player_lineup_calculator": [
        UpstreamReq(source="api_football", data_type="FIXTURE_LINEUPS"),
        UpstreamReq(source="transfermarkt", data_type="PLAYER_VALUES", required=False),
    ],
    "bench_sub_calculator": [
        UpstreamReq(source="api_football", data_type="FIXTURE_EVENTS"),
        UpstreamReq(source="api_football", data_type="FIXTURE_LINEUPS"),
    ],
    "odds_calculator": [
        UpstreamReq(source="footystats", data_type="ODDS"),
        UpstreamReq(
            source="mdps_odds_horizon_bucket",
            data_type="ODDS_HORIZON_BUCKET",
            required=False,
            notes="MDPS post-processed bucketed odds; complements footystats raw odds",
        ),
    ],
    "multisource_xg": [
        UpstreamReq(source="understat", data_type="XG"),
        UpstreamReq(source="footystats", data_type="MATCHES"),
        UpstreamReq(source="derived", data_type="team_xg", required=False),
    ],
    "xg_decomposition": [
        UpstreamReq(source="api_football", data_type="FIXTURE_STATS"),
        UpstreamReq(source="understat", data_type="XG"),
    ],
    # ------------------------------------------------------------------
    # Stage D — enriched / derived calculators
    # ------------------------------------------------------------------
    "team_derived": [
        UpstreamReq(source="derived", data_type="team_form"),
        UpstreamReq(source="derived", data_type="team_goals"),
    ],
    "relative_context": [
        UpstreamReq(source="api_football", data_type="FIXTURES"),
        UpstreamReq(source="api_football", data_type="STANDINGS"),
        UpstreamReq(source="derived", data_type="team_form", required=False),
    ],
    "meta_features": [
        UpstreamReq(source="derived", data_type="team_form"),
        UpstreamReq(source="derived", data_type="team_xg", required=False),
    ],
    "ml_predictions": [
        UpstreamReq(source="derived", data_type="team_form"),
        UpstreamReq(source="derived", data_type="team_xg", required=False),
        UpstreamReq(source="derived", data_type="odds_calculator", required=False),
    ],
    "replacement_model": [
        UpstreamReq(source="transfermarkt", data_type="PLAYER_VALUES"),
    ],
    "bucketed_features": [
        UpstreamReq(
            source="derived",
            data_type="team_form",
            notes="bucketed_features expands other calculators' outputs at runtime",
        ),
    ],
    "poisson_xg_calculator": [
        UpstreamReq(source="derived", data_type="team_xg"),
    ],
}


@dataclass(frozen=True)
class CoverageResult:
    """Result of an :func:`in_coverage` check with the reason for the verdict."""

    in_coverage: bool
    reason: str = field(default="")


def in_coverage(
    source: str,
    data_type: str,
    league_id: str,
    iso_date: str,
) -> bool:
    """Return True iff the (source, data_type, league, date) is *expected*
    to have a manifest row.

    Composes existing UAC coverage helpers:
      1. ``is_pre_launch_date(data_type, iso_date)`` — date floor check
      2. ``is_in_known_gap(source, data_type, iso_date)`` — provider-outage
         windows
      3. ``get_entity_league_coverage(data_type)`` — league filter

    Returns True if the combination is **in coverage** — i.e. we expect
    upstream to have data, so a missing manifest row is a real gap. Returns
    False if the combination is **out of coverage** — upstream legitimately
    doesn't serve this combo, so NaN-by-design is the right outcome.

    The ``source`` arg is currently used only for known-gap lookup;
    data_type → source mapping is via ``SPORTS_DATA_TYPE_TO_SOURCE``. The
    arg is kept explicit on the signature so callers can pass it directly
    when they already know the source (avoids round-tripping through the
    dict).

    Args:
        source: Source key (``api_football`` / ``footystats`` / ``understat``
            / ``transfermarkt`` / ``soccer_football_info`` / ``open_meteo`` /
            ``odds_api`` / ``mdps_odds_horizon_bucket``). Use ``"derived"``
            for in-pipeline feature dependencies — those always return True
            (no upstream coverage check applies; the dependent calculator
            is responsible for in-coverage propagation).
        data_type: UAC canonical data_type. Empty string returns True
            (no clip-able data_type → assume in-coverage).
        league_id: Canonical UAC league_id (``EPL``, ``LA_LIGA``, etc.).
            Empty string disables the league check.
        iso_date: ``YYYY-MM-DD`` date string.

    Returns:
        True if expected to have data; False if out-of-coverage (NaN
        legitimate).
    """
    # Derived features have no upstream coverage check; the dependent
    # calculator's coverage propagates instead.
    if source == "derived":
        return True

    # 1. Pre-launch date: source had no data on iso_date.
    if data_type and is_pre_launch_date(data_type, iso_date):
        return False

    # 2. Known gap window: provider outage / paused league for this
    #    (source, data_type) over a documented date range.
    if is_in_known_gap(source, data_type, iso_date):
        return False

    # 3. League coverage: this entity may only serve certain leagues
    #    (e.g. understat = 6 European leagues). league_id="" disables
    #    the check (used when the calculator doesn't shard by league).
    if league_id and data_type:
        league_set = get_entity_league_coverage(data_type)
        if league_set is not None and league_id not in league_set:
            return False

    return True


def _coerce_iso_date(value: object) -> str:
    """Best-effort coerce date / datetime / str to YYYY-MM-DD."""
    if isinstance(value, str):
        return value
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date_type):
        return value.isoformat()
    return str(value)


def in_coverage_dt(
    source: str,
    data_type: str,
    league_id: str,
    when: date_type | datetime | str,
) -> bool:
    """``in_coverage`` accepting date / datetime / str."""
    return in_coverage(source, data_type, league_id, _coerce_iso_date(when))


# Re-exported from .league_data for convenience — callers building upstream
# coverage windows often want both the per-source clip and the in_coverage
# check in the same import.
__all__ = [
    "FEATURE_UPSTREAM_REQUIREMENTS",
    "CoverageResult",
    "UpstreamReq",
    "clip_dates_to_source_coverage",
    "in_coverage",
    "in_coverage_dt",
]
