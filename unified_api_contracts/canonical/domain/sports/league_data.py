"""League data - the canonical LEAGUE_REGISTRY dict and query helpers.

Assembles all Prediction, Features, Reference, and Non-football leagues into a
single ``LEAGUE_REGISTRY`` dict keyed by canonical league_id string.

Also exposes convenience lookup functions used throughout the system.

Data is split across:
- ``league_data_prediction.py`` - top-tier domestic football leagues
- ``league_data_other.py``      - Features, Reference, and Non-football leagues

Source: Ported from instruments-service/instruments_service/sports/ into UAC so
all downstream consumers (features-sports-service, instruments-service, USRI)
share a single SSOT.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date, timedelta

from unified_api_contracts.canonical.crosscutting.config_versioning import (
    ConfigDescriptor,
    compute_config_content_hash,
)

from .league_data_other import FEATURES_LEAGUES as FEATURES_LEAGUES
from .league_data_other import NON_FOOTBALL_LEAGUES as NON_FOOTBALL_LEAGUES
from .league_data_other import REFERENCE_LEAGUES as REFERENCE_LEAGUES
from .league_data_prediction import PREDICTION_LEAGUES as PREDICTION_LEAGUES
from .league_registry import SEASON_BY_COUNTRY, LeagueDefinition

# ---------------------------------------------------------------------------
# LEAGUE_REGISTRY - single source of truth for all leagues
# ---------------------------------------------------------------------------

LEAGUE_REGISTRY: dict[str, LeagueDefinition] = {
    **PREDICTION_LEAGUES,
    **FEATURES_LEAGUES,
    **REFERENCE_LEAGUES,
    **NON_FOOTBALL_LEAGUES,
}

# ---------------------------------------------------------------------------
# Reverse lookup - API-Football ID -> league_id
# ---------------------------------------------------------------------------

_API_FOOTBALL_ID_TO_LEAGUE: dict[int, str] = {
    league.api_football_id: league.league_id
    for league in LEAGUE_REGISTRY.values()
    if league.api_football_id is not None
}


# ---------------------------------------------------------------------------
# Per-source data coverage start dates
# ---------------------------------------------------------------------------
# The data-status reader's expected denominator is "league plays per UAC
# fixture calendar", but a source can't deliver data for a date before the
# source itself launched / our capture pipeline hooked it up. Without this
# clip, dates pre-source-start show as ``missing`` shards forever, which is
# wrong: the source NEVER had data for those days, by design.
#
# Each entry is the earliest date for which the source produces SOME parquet
# for SOME league. Days before the start date are excluded from
# ``expected_dates_for_league`` for sources that read this registry.
#
# SSOT for data-status coverage clipping. Update when adding a new provider
# or when an existing provider extends backfill (e.g. footystats Pro tier
# unlocks earlier history).
SOURCE_COVERAGE_START: dict[str, date] = {
    "api_football": date(2015, 1, 1),
    "footystats": date(2019, 1, 1),
    "understat": date(2014, 1, 1),
    "transfermarkt": date(2019, 1, 1),
    "soccer_football_info": date(2019, 1, 1),
    "open_meteo": date(2019, 3, 2),
    # odds-api raw ticks → MDPS bucketed odds (consumed by FSS odds_features).
    # odds-api itself provides historical from 2020-06; our MTDS+MDPS hooked
    # in at 2020-06-06 per market-data-tick-sports/processed/by_date probe.
    "odds_api": date(2020, 6, 6),
    "mdps_odds_horizon_bucket": date(2020, 6, 6),
}


# Per-(source, data_type) override when a specific entity from a source has
# a later coverage start than the source-wide value. Probed live 2026-04-30:
# SFI's source-wide coverage is 2019-01-01 (leagues, day-list endpoint), but
# /matches/view/progressive/ returns empty for every match before 2020-01-01,
# so SFI_PROGRESSIVE_STATS gets its own later floor here.
#
# api_football per-fixture endpoints (events/lineups/statistics/players) all
# nominally have data going back to 2017-10 per live probes (2026-05-01),
# but our backfill never captured 2018-2020 dates due to pre-flight skips
# that mark dates as "done" once any league has a row. Re-fetching is
# expensive (paid API quota) and operationally we only need data ≥ 2020-06
# to match the odds_api downstream cutoff — strategies built on these
# features can't trade on dates without odds anyway. So we declare
# 2020-06-06 as the effective coverage start (matches odds_api) and stop
# counting pre-cutoff dates as missing.
DATA_TYPE_COVERAGE_START: dict[tuple[str, str], date] = {
    ("soccer_football_info", "SFI_PROGRESSIVE_STATS"): date(2020, 1, 1),
    # SFI_LEAGUES retired 2026-05-05 — was a static provider-catalog mapping,
    # now lives in UAC SOCCER_FOOTBALL_INFO_IDS rather than as captured GCS data.
    ("api_football", "FIXTURE_EVENTS"): date(2020, 6, 6),
    ("api_football", "FIXTURE_LINEUPS"): date(2020, 6, 6),
    ("api_football", "FIXTURE_STATS"): date(2020, 6, 6),
    ("api_football", "PLAYER_STATS"): date(2020, 6, 6),
}


# Date-range gaps that we KNOW are missing and should NOT count as "missing"
# in the data-status denominator. Format: list of (start, end) inclusive
# `YYYY-MM-DD` tuples per (source, data_type).
#
# Add to this registry as we discover gaps live (e.g. provider outages,
# leagues paused). Sparse-but-not-empty windows (like SFI_PROGRESSIVE_STATS
# 2020-2021, where some matches return data and most don't) are NOT a good
# fit — those still count as expected, just under-captured.
#
# Design decision — sports off-seasons (D2 Phase 2, Decision 1, 2026-05-21):
# Per-league off-season windows are handled SEPARATELY by
# ``get_league_fixture_calendar()`` + ``SEASON_BY_COUNTRY`` (fixture-calendar
# level), NOT via KNOWN_COVERAGE_GAPS. The oracle ``expected_coverage()`` in
# ``registry/expected_coverage.py`` does not include a per-league off-season
# gate because the oracle signature is per-(asset_group, source, data_type)
# without a league_id axis. Per-league oracle integration is Decision 3
# (deferred — requires IS instrument-catalogue access).
#
# This dict is ONLY for SOURCE-LEVEL gaps: complete provider outages or
# protocol-level blackout periods where the source produced NO data at all
# for a date range. Population happens as such gaps are discovered from
# data audits or provider communications.
KNOWN_COVERAGE_GAPS: dict[tuple[str, str], list[tuple[str, str]]] = {}


# Sports manifest data_type → source-key mapping (SSOT).
#
# The manifest stores rows keyed by ``data_type`` (e.g. ``MATCHES``, ``XG``,
# ``PREDICTIONS``) but the coverage windows above are keyed by
# ``source_key`` (e.g. ``footystats``, ``understat``).  This mapping is the
# bridge — used by the manifest-purge tooling and the orchestrator's
# pre-flight to decide whether a (date, data_type) shard is even possible.
#
# Mirrors the orchestrator's ``_enrichment_entity_venues`` list at
# ``instruments-service/instruments_service/engine/orchestrator.py:1113``
# but UAC-side so other repos can import it without a circular dep.
SPORTS_DATA_TYPE_TO_SOURCE: dict[str, str] = {
    # FootyStats — match aggregates + footystats' own in-house prediction model.
    # NOTE: ODDS was removed 2026-06-25 (#6 coherent unit) — bookmaker odds are
    # MARKET-TICK-DATA owned by MTDS/odds-api (ODDS_SNAPSHOT/ODDS_MOVEMENT/ARBITRAGE).
    # TEAMS/STANDINGS moved to api_football 2026-06-25 (canonical-form alignment):
    #   footystats writes ONLY footystats_matches/odds/predictions to disk — it does
    #   NOT write teams/standings. Those are written by the api_football handler under
    #   pipeline_mode=batch_api_football/entity={teams,standings}. This map was the
    #   stale outlier vs the canonical SOURCE_PRIORITY[("sports","TEAMS"|"STANDINGS")]
    #   = ["api_football"] (the writer already raised MissingSourceError on footystats),
    #   which produced ~137k mis-sourced/phantom manifest rows. Aligned to the SSOT.
    "MATCHES": "footystats",
    "PREDICTIONS": "footystats",
    # Understat — xG model + per-shot xG
    "XG": "understat",
    "XG_SHOTS": "understat",
    # API-Football — fixtures + per-fixture detail + reference (teams / standings)
    "FIXTURES": "api_football",
    "INJURIES": "api_football",
    "FIXTURE_STATS": "api_football",
    "FIXTURE_EVENTS": "api_football",
    "FIXTURE_LINEUPS": "api_football",
    "PLAYER_STATS": "api_football",
    "TEAMS": "api_football",
    "STANDINGS": "api_football",
    # Transfermarkt — player values.
    # TRANSFERMARKT_LEAGUES retired 2026-05-05 (was static catalog mapping;
    # lives in UAC TRANSFERMARKT_IDS as provider-id config rather than captured data).
    # TRANSFERMARKT_VALUES retired 2026-05-15 (stale alias — PLAYER_VALUES is canonical).
    "PLAYER_VALUES": "transfermarkt",
    # SoccerFootball.info.
    # SFI_LEAGUES retired 2026-05-05 (same reason — UAC SOCCER_FOOTBALL_INFO_IDS).
    # SFI_STANDINGS retired 2026-05-05 — SFI has no standings endpoint.
    "SFI_PROGRESSIVE_STATS": "soccer_football_info",
    # OpenMeteo — historical weather
    "WEATHER": "open_meteo",
    # MDPS odds horizon bucket — derived from odds-api
    "ODDS_HORIZON_BUCKET": "mdps_odds_horizon_bucket",
}


def get_source_for_data_type(data_type: str) -> str | None:
    """Return the source-key for a sports manifest ``data_type``, or
    ``None`` if unknown (caller should treat as no-clip)."""
    return SPORTS_DATA_TYPE_TO_SOURCE.get(data_type)


def is_pre_launch_date(data_type: str, iso_date: str) -> bool:
    """True if ``iso_date`` is before the source/data_type's coverage start.

    Used to identify illegitimate manifest rows that claim
    ``capture_status=captured`` for dates the source never covered.  A
    pre-launch row should not exist — the writer skipped the
    ``clip_dates_to_source_coverage`` clip and recorded a sentinel for
    a date the source had no data on.

    Returns ``False`` if the data_type is unknown or has no coverage
    window — defensively means "we can't prove it's pre-launch".
    """
    source = SPORTS_DATA_TYPE_TO_SOURCE.get(data_type)
    if source is None:
        return False
    coverage_start = get_source_coverage_start(source, data_type)
    if coverage_start is None:
        return False
    return iso_date < coverage_start.isoformat()


def get_source_coverage_start(
    source_key: str,
    data_type: str | None = None,
) -> date | None:
    """Return the earliest date this source has data for (UAC SSOT).

    When ``data_type`` is supplied AND a per-(source, data_type) override
    exists in ``DATA_TYPE_COVERAGE_START``, returns that — otherwise falls
    back to the source-wide value. Returns ``None`` for unknown sources —
    caller should treat as no clip.

    Used by deployment-api ``_sports_expected_dates_for_league`` to drop
    pre-launch dates from the expected denominator so the data-status UI
    doesn't paint them as missing.
    """
    if data_type is not None:
        override = DATA_TYPE_COVERAGE_START.get((source_key, data_type))
        if override is not None:
            return override
    return SOURCE_COVERAGE_START.get(source_key)


def get_known_coverage_gaps(
    source_key: str,
    data_type: str,
) -> list[tuple[str, str]]:
    """Return list of (start, end) ISO-date gap windows that should be
    excluded from the expected denominator for this (source, data_type)."""
    return KNOWN_COVERAGE_GAPS.get((source_key, data_type), [])


def is_in_known_gap(
    source_key: str,
    data_type: str,
    iso_date: str,
) -> bool:
    """True if the given ``YYYY-MM-DD`` date falls inside a registered
    known-gap window for this (source, data_type)."""
    return any(start <= iso_date <= end for start, end in KNOWN_COVERAGE_GAPS.get((source_key, data_type), []))


def clip_dates_to_source_coverage(
    source_key: str,
    start: str,
    end: str,
    data_type: str | None = None,
) -> tuple[str, str]:
    """Clip a date range so it doesn't extend before the source's launch.

    Both inputs/outputs are ``YYYY-MM-DD`` strings. If the source is unknown
    the input range is returned unchanged.

    When ``data_type`` is supplied, applies the per-(source, data_type)
    override from ``DATA_TYPE_COVERAGE_START`` if one exists — otherwise
    falls back to the source-wide ``SOURCE_COVERAGE_START``.

    Empty-range signal: when the entire query window is BEFORE the source's
    coverage start, returns ``(end, "")`` where ``start > end`` — callers
    should detect ``end == ""`` (or ``start > end``) as "no expected dates".
    Returning a single-day window inside the pre-source range would be wrong
    because the source had no data on that day either.
    """
    coverage_start = get_source_coverage_start(source_key, data_type)
    if coverage_start is None:
        return start, end
    coverage_iso = coverage_start.isoformat()
    if start >= coverage_iso:
        return start, end
    if end < coverage_iso:
        # Entire range pre-source → signal empty via inverted bounds.
        return coverage_iso, ""
    return coverage_iso, end


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------


def get_league(league_id: str) -> LeagueDefinition | None:
    """Look up a league by its canonical identifier (case-insensitive)."""
    return LEAGUE_REGISTRY.get(league_id.upper())


def get_league_by_api_football_id(api_football_id: int) -> LeagueDefinition | None:
    """Look up a league by its API-Football numeric ID."""
    lid = _API_FOOTBALL_ID_TO_LEAGUE.get(api_football_id)
    if lid is None:
        return None
    return LEAGUE_REGISTRY.get(lid)


def get_leagues_for_sport(sport: str) -> list[LeagueDefinition]:
    """Return all leagues for a given sport type (case-insensitive)."""
    sport_upper = sport.upper()
    return [league for league in LEAGUE_REGISTRY.values() if league.sport == sport_upper]


def get_leagues_by_classification(classification: str) -> list[LeagueDefinition]:
    """Return all leagues matching a classification label."""
    cls_lower = classification.lower()
    return [league for league in LEAGUE_REGISTRY.values() if league.classification.lower() == cls_lower]


def get_leagues_by_country(country: str) -> list[LeagueDefinition]:
    """Return all leagues for a given ISO country code (case-insensitive)."""
    country_upper = country.upper()
    return [league for league in LEAGUE_REGISTRY.values() if league.country == country_upper]


def get_prediction_leagues() -> list[LeagueDefinition]:
    """Return all Prediction-tier leagues (suitable for model-based betting)."""
    return get_leagues_by_classification("Prediction")


def get_live_stats_api_football_ids() -> frozenset[int]:
    """Return API Football league IDs that support live in-play statistics.

    API Football provides live stats (possession, shots, corners, fouls) for
    top-tier football leagues (Tier 0 cups/continental + Tier 1 national top
    divisions). Lower tiers only get score + events (goals/cards/subs).

    Used by instruments-service live poller to decide which fixtures get the
    extra ``/fixtures/statistics`` call vs just score + events.
    """
    return frozenset(
        league.api_football_id
        for league in LEAGUE_REGISTRY.values()
        if league.api_football_id is not None and league.sport == "FOOTBALL" and league.tier <= 1
    )


def get_all_prediction_league_ids() -> list[str]:
    """Return canonical league_id strings for all Prediction-tier leagues.

    Used by data-status to iterate leagues and show 0% for newly added ones.
    """
    return [league.league_id for league in get_prediction_leagues()]


def _is_in_season(d: date, season_start: int, season_end: int) -> bool:
    """Check if a date falls within a season defined by start/end months.

    Handles wrap-around seasons (e.g. Aug-May crosses year boundary).
    """
    month = d.month
    if season_start <= season_end:
        # Calendar-year season (e.g. Feb-Nov)
        return season_start <= month <= season_end
    # Wrap-around season (e.g. Aug-May)
    return month >= season_start or month <= season_end


def get_league_fixture_calendar(
    league_id: str,
    start: str,
    end: str,
) -> list[str]:
    """Return expected fixture dates for a league within a date range.

    Uses the league's country → ``SEASON_BY_COUNTRY`` season months to
    determine which dates fall within the active season. Off-season dates are
    excluded. Only returns dates that are NOT in the off-season gap.

    Args:
        league_id: Canonical league identifier (e.g. ``EPL``, ``BUN``).
        start: Start date (``YYYY-MM-DD`` inclusive).
        end: End date (``YYYY-MM-DD`` inclusive).

    Returns:
        Sorted list of date strings (``YYYY-MM-DD``) within the league's
        active season. Empty list if the league is not found or the entire
        range is off-season.
    """
    league = get_league(league_id)
    if league is None:
        return []

    season_months = SEASON_BY_COUNTRY.get(league.country, league.season_months)
    season_start, season_end = season_months

    start_date = date.fromisoformat(start)
    end_date = date.fromisoformat(end)

    result: list[str] = []
    current = start_date
    while current <= end_date:
        if _is_in_season(current, season_start, season_end):
            result.append(current.isoformat())
        current += timedelta(days=1)

    return result


# ---------------------------------------------------------------------------
# Expected team-count seed per league per season
# ---------------------------------------------------------------------------

# Drift-check denominator used by Transfermarkt + API-Football adapters to
# detect silent partial fetches (e.g. EPL returning 17 teams instead of 20).
#
# Keys are canonical ``league_id`` strings; values are ``{season_year:
# expected_team_count}``. Most top-tier football leagues have stable rosters
# across decades; MLS expansion is the headline exception. Seed values here
# are slow-moving — see ``get_expected_team_count_for_league`` for the
# lookup contract.
#
# SSOT: ``codex/02-data/sports-scheduling-and-sharding.md`` §2.7.
LEAGUE_EXPECTED_TEAM_COUNTS: dict[str, dict[int, int]] = {
    # England
    "EPL": dict.fromkeys(range(2020, 2027), 20),
    "ENG_CHAMPIONSHIP": dict.fromkeys(range(2020, 2027), 24),
    "ENG_LEAGUE_ONE": dict.fromkeys(range(2020, 2027), 24),
    "ENG_LEAGUE_TWO": dict.fromkeys(range(2020, 2027), 24),
    # Spain
    "LA_LIGA": dict.fromkeys(range(2020, 2027), 20),
    "SEGUNDA_DIVISION": dict.fromkeys(range(2020, 2027), 22),
    # Germany
    "BUNDESLIGA": dict.fromkeys(range(2020, 2027), 18),
    "BUNDESLIGA_2": dict.fromkeys(range(2020, 2027), 18),
    "LIGA_3": dict.fromkeys(range(2020, 2027), 20),
    # Italy
    "SERIE_A": dict.fromkeys(range(2020, 2027), 20),
    "SERIE_B": dict.fromkeys(range(2020, 2027), 20),
    # France
    "LIGUE_1": {2020: 20, 2021: 20, 2022: 20, 2023: 18, 2024: 18, 2025: 18, 2026: 18},
    "LIGUE_2": dict.fromkeys(range(2020, 2027), 20),
    # Netherlands / Portugal / Belgium
    "EREDIVISIE": dict.fromkeys(range(2020, 2027), 18),
    "PRIMEIRA_LIGA": dict.fromkeys(range(2020, 2027), 18),
    "JUPILER_PRO": dict.fromkeys(range(2020, 2027), 18),
    # Turkey / Greece / Scotland / Austria / Switzerland
    "SUPER_LIG": dict.fromkeys(range(2020, 2024), 20) | dict.fromkeys(range(2024, 2027), 19),
    "GREEK_SUPER_LEAGUE": dict.fromkeys(range(2020, 2027), 14),
    "SCOTTISH_PREMIERSHIP": dict.fromkeys(range(2020, 2027), 12),
    "AUSTRIAN_BUNDESLIGA": dict.fromkeys(range(2020, 2027), 12),
    "SWISS_SUPER_LEAGUE": dict.fromkeys(range(2020, 2023), 10) | dict.fromkeys(range(2023, 2027), 12),
    # Nordics / Poland
    "DANISH_SUPERLIGA": dict.fromkeys(range(2020, 2027), 12),
    "ELITESERIEN": dict.fromkeys(range(2020, 2027), 16),
    "ALLSVENSKAN": dict.fromkeys(range(2020, 2027), 16),
    "EKSTRAKLASA": dict.fromkeys(range(2020, 2027), 18),
    # Americas
    "ARGENTINA_PRIMERA": dict.fromkeys(range(2020, 2027), 28),
    "BRASILEIRAO": dict.fromkeys(range(2020, 2027), 20),
    "CHILE_PRIMERA": dict.fromkeys(range(2020, 2027), 16),
    "MLS": {2020: 26, 2021: 27, 2022: 28, 2023: 29, 2024: 29, 2025: 30, 2026: 30},
    "LIGA_MX": dict.fromkeys(range(2020, 2027), 18),
    # Asia-Pacific
    "J1_LEAGUE": dict.fromkeys(range(2020, 2027), 18),
    "K_LEAGUE_1": dict.fromkeys(range(2020, 2027), 12),
    "A_LEAGUE": dict.fromkeys(range(2020, 2024), 12) | dict.fromkeys(range(2024, 2027), 13),
}


def get_expected_team_count_for_league(league_id: str, season: int) -> int | None:
    """Return expected team count for a league in a given season, or ``None``.

    Lookup order:
      1. The league's own ``LeagueDefinition.expected_team_count_per_season``
         (per-instance override for test fixtures / future inline migration).
      2. The module-level seed dict ``LEAGUE_EXPECTED_TEAM_COUNTS`` (primary
         SSOT for production adapters).

    ``None`` signals "unknown" and MUST be interpreted by callers as
    "skip the drift check silently" — never as zero.

    Args:
        league_id: Canonical league identifier (case-insensitive).
        season: Season year (e.g. ``2024`` for the 2024-25 EPL season).

    Returns:
        Expected team count, or ``None`` when the league / season is not seeded.
    """
    lid = league_id.upper()
    league = LEAGUE_REGISTRY.get(lid)
    if league is not None and league.expected_team_count_per_season is not None:
        override = league.expected_team_count_per_season.get(season)
        if override is not None:
            return override
    seeded = LEAGUE_EXPECTED_TEAM_COUNTS.get(lid)
    if seeded is None:
        return None
    return seeded.get(season)


def get_expected_leagues_for_source(
    source_key: str,
    classifications: Iterable[str] | None = None,
) -> list[LeagueDefinition]:
    """Return leagues expected to produce data for a given source.

    Canonical denominator for deployment-api data-status coverage %. For a
    given source (``api_football``, ``footystats``, ``odds_api``,
    ``open_meteo``, ``soccer_football_info``, ``transfermarkt``,
    ``understat``), returns the list of leagues whose ``data_sources``
    frozenset contains ``source_key``. Optionally restrict by league
    classification (``Prediction`` / ``Features`` / ``Reference`` /
    ``Other``).

    SSOT: ``codex/02-data/sports-data-source-coverage-matrix.md``.

    Args:
        source_key: Data-source identifier as stored in
            ``LeagueDefinition.data_sources`` (e.g. ``"api_football"``).
        classifications: Optional iterable of classification strings.
            ``None`` means all classifications.

    Returns:
        List of ``LeagueDefinition`` entries matching the filter.
        Empty list if the source key is unknown or no leagues match.
    """
    allowed = {c.lower() for c in classifications} if classifications is not None else None
    return [
        league
        for league in LEAGUE_REGISTRY.values()
        if source_key in league.data_sources and (allowed is None or league.classification.lower() in allowed)
    ]


# ---------------------------------------------------------------------------
# Config versioning — monotonic version + deterministic content hash for the
# sports-leagues config. PER-CONFIG (independent of MVP_SCOPE / prediction-
# markets), surfaced in data-status so a coverage delta attributes to a
# leagues-scope change (e.g. an added/removed league) vs a data change.
# Metadata only — never a GCS partition key. SSOT:
# ``plans/active/mvp_scope_catalogue_tagging_2026_06_08.md`` § Config versioning.
# ---------------------------------------------------------------------------

SPORTS_LEAGUES_CONFIG_VERSION: int = 1
"""Monotonic version of :data:`LEAGUE_REGISTRY`. Bump on any content change."""


def _compute_sports_leagues_content_hash() -> str:
    """SHA-256 (16-hex prefix) of the canonical LEAGUE_REGISTRY content."""
    return compute_config_content_hash(
        SPORTS_LEAGUES_CONFIG_VERSION,
        [(league_id, LEAGUE_REGISTRY[league_id]) for league_id in sorted(LEAGUE_REGISTRY)],
    )


SPORTS_LEAGUES_CONFIG_HASH: str = _compute_sports_leagues_content_hash()
"""Content hash of :data:`LEAGUE_REGISTRY` — flips IFF the league set/defs change."""


def sports_leagues_config_descriptor() -> ConfigDescriptor:
    """Return the sports-leagues ``(version, content-hash)`` descriptor."""
    return ConfigDescriptor(SPORTS_LEAGUES_CONFIG_VERSION, SPORTS_LEAGUES_CONFIG_HASH)


__all__ = [
    "DATA_TYPE_COVERAGE_START",
    "FEATURES_LEAGUES",
    "KNOWN_COVERAGE_GAPS",
    "LEAGUE_EXPECTED_TEAM_COUNTS",
    "LEAGUE_REGISTRY",
    "NON_FOOTBALL_LEAGUES",
    "PREDICTION_LEAGUES",
    "REFERENCE_LEAGUES",
    "SOURCE_COVERAGE_START",
    "SPORTS_LEAGUES_CONFIG_HASH",
    "SPORTS_LEAGUES_CONFIG_VERSION",
    "clip_dates_to_source_coverage",
    "get_all_prediction_league_ids",
    "get_expected_leagues_for_source",
    "get_expected_team_count_for_league",
    "get_known_coverage_gaps",
    "get_league",
    "get_league_by_api_football_id",
    "get_league_fixture_calendar",
    "get_leagues_by_classification",
    "get_leagues_by_country",
    "get_leagues_for_sport",
    "get_live_stats_api_football_ids",
    "get_prediction_leagues",
    "get_source_coverage_start",
    "is_in_known_gap",
    "sports_leagues_config_descriptor",
]
