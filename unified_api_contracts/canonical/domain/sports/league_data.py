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
# EVIDENCE RULE (operator ruling 2026-07-15, "amend floors to reality"): every
# floor below is the earliest date at which a REAL object is held — parquet that
# PARSES, carries >= 1 row, and is HISTORICALLY COHERENT with its date partition.
# Object EXISTENCE is not evidence: the corpus contains a large artifact class of
# present-day reference data replicated under historical partitions (e.g.
# `day=2014-01-01/.../entity=standings` carrying `season=2026`, `update=2026-06-12`),
# which is why each floor cites a probed row count + a coherence witness.
# Re-probe with the entity/day walk before moving any floor.
# SPORTS DATA FLOOR = 2020-06-06 (operator ruling 2026-07-21, CANONICAL). Odds tick data
# starts 2020-06-06 (measured: ZERO odds before it); without odds nothing downstream is
# legitimately computable, so 2020-06-06 is the floor for ALL sports sources/coverage/
# expectations. This SUPERSEDES the per-source evidence floors (understat 2014, the
# 2026-07-15 footystats/transfermarkt/open_meteo->2018 amendment, api_football 2018,
# sfi 2019) — those describe where a source's raw data begins, but pre-floor sports data
# is out-of-scope and is being wiped. Do NOT lower any sports floor below 2020-06-06.
SOURCE_COVERAGE_START: dict[str, date] = {
    # Measured 2026-07-15 (legacy + prd object probe, all trees, years 2014-2021):
    # no api_football object of ANY entity exists before 2018-01-01, and the
    # 2018-01-01 objects are real + coherent (fixtures 64 rows; fixture_events
    # ENG_CHAMPIONSHIP 20 rows, available_at=2018-01-01T17:00). The 2014/2017
    # `teams`/`standings` objects in the prd bucket are the artifact class above
    # (season=2026) and are NOT evidence. Earlier probes had already shown the
    # subscription returns empty for seasons 2015-2017 (35,889 all-empty_confirmed
    # across 76 MVP leagues — subscription floor, not a backfill bug). CONFIRMED
    # CORRECT — unchanged.
    "api_football": date(2020, 6, 6),
    # LOWERED 2019-01-01 → 2018-01-01 (2026-07-15). Real+coherent at 2018-01-01:
    # footystats_matches ENG_LEAGUE_ONE 12 rows (genuine New Year's Day League One
    # card: AFC Wimbledon v Southend, Bristol Rovers v Portsmouth, …); footystats_odds
    # + footystats_predictions ENG_LEAGUE_ONE 12 rows each with kickoff_utc=
    # 2018-01-01T15:00 and available_at=2017-12-29T15:00 — exactly the documented
    # kickoff-minus-72h pre-match snapshot semantics. No footystats object exists
    # before 2018-01-01.
    "footystats": date(2020, 6, 6),
    # Earliest real understat object is 2014-08-08 (prd, LIGUE_1 understat_xg,
    # season=2014, Reims v PSG, home_xg=1.36787 — the real 2014/15 Ligue 1 opener),
    # i.e. the archive starts mid-2014 with the season. This floor already sits
    # BELOW the earliest real object, so it clips nothing real — left as-is
    # (no evidence would justify lowering it further).
    "understat": date(2020, 6, 6),
    # LOWERED 2019-01-01 → 2018-01-01 (2026-07-15). Real+coherent at 2018-01-01:
    # entity=player_values/season=2017/player_values.parquet, 456 rows, season=2017
    # (historically coherent for a 2018-01-01 partition). NOTE: transfermarkt's real
    # payload is the `season=YYYY`-partitioned shape; the bare `player_values.parquet`
    # is the artifact class (the 2019-01-01 one carries season=2026), so the floor is
    # evidenced by the season-partitioned objects only.
    "transfermarkt": date(2020, 6, 6),
    # Earliest real SFI object is 2020-01-01 (progressive_stats, 8,125 rows,
    # available_at spread across 2020-01-01T15:00+ in 30s steps). No SFI object
    # exists in 2018 or 2019 at all. This source-wide floor already sits BELOW the
    # earliest real object — left as-is; the operative floor is the
    # SFI_PROGRESSIVE_STATS override below, which measures EXACTLY correct.
    "soccer_football_info": date(2020, 6, 6),
    # LOWERED 2019-03-02 → 2018-01-01 (2026-07-15). Real+coherent at 2018-01-01:
    # entity=weather/weather.parquet, 26 rows, date=2018-01-01, every `actual_*`
    # observation column populated 26/26 (actual_ko_temp, actual_1h_*, actual_2h_*,
    # actual_total_precip_mm, …) — matching the 2020-06-06 reference object's 22/22.
    # The null `forecast_t24h_*` columns are EXPECTED for a historical backfill
    # (actuals are retrievable; archived forecasts are not) and do not make the
    # object a placeholder.
    "open_meteo": date(2020, 6, 6),
    # odds-api raw ticks → MDPS bucketed odds (consumed by FSS odds_features).
    # odds-api itself provides historical from 2020-06; our MTDS+MDPS hooked
    # in at 2020-06-06 per market-data-tick-sports/processed/by_date probe.
    "odds_api": date(2020, 6, 6),
    "mdps_odds_horizon_bucket": date(2020, 6, 6),
}


# Per-(source, data_type) override when a specific entity from a source has
# a LATER coverage start than the source-wide value. An entry equal to (or below)
# the source-wide value is meaningless — delete it and let the source-wide floor
# apply. Probed live 2026-04-30: SFI's source-wide coverage is 2019-01-01
# (leagues, day-list endpoint), but /matches/view/progressive/ returns empty for
# every match before 2020-01-01, so SFI_PROGRESSIVE_STATS gets its own later floor
# here. RE-CONFIRMED by object probe 2026-07-15: earliest real progressive_stats
# object is EXACTLY 2020-01-01 (8,125 rows) — this override measures correct.
#
# REMOVED 2026-07-15 (operator ruling "amend floors to reality") — the four
# api_football per-fixture overrides (FIXTURE_EVENTS / FIXTURE_LINEUPS /
# FIXTURE_STATS / PLAYER_STATS), each previously pinned at 2020-06-06. Their
# justification asserted that "our backfill never captured 2018-2020 dates due to
# pre-flight skips", and then clipped coverage to the odds_api cutoff on that basis.
# That premise was FALSE: an object probe of the legacy + prd buckets on 2026-07-15
# found REAL, historically-coherent per-fixture data at 2018-01-01 —
#   fixture_events   ENG_CHAMPIONSHIP  20 rows (available_at=2018-01-01T17:00)
#   fixture_lineups  (roll-up)         32 rows
#   fixture_stats    ENG_CHAMPIONSHIP   4 rows
#   player_stats     ENG_CHAMPIONSHIP  28 rows
# ~22.3k such objects exist for 2018-2020. Since the measured earliest real date
# for all four equals the api_football source-wide floor (2018-01-01), the
# overrides are redundant AND contradict this dict's own "later than source-wide"
# contract — so they are deleted rather than restated. Consequence, accepted by the
# operator: honest-coverage denominators widen and coverage % drops. That is the
# honest number. (The old floor also conflated "no odds downstream" with "no data
# upstream" — a downstream trading constraint is not an upstream coverage fact.)
DATA_TYPE_COVERAGE_START: dict[tuple[str, str], date] = {
    ("soccer_football_info", "SFI_PROGRESSIVE_STATS"): date(2020, 6, 6),
    # SFI_LEAGUES retired 2026-05-05 — was a static provider-catalog mapping,
    # now lives in UAC SOCCER_FOOTBALL_INFO_IDS rather than as captured GCS data.
}


# Design decision — sports off-seasons (D2 Phase 2, Decision 1, 2026-05-21):
# Per-league off-season windows are handled SEPARATELY by
# ``get_league_fixture_calendar()`` + ``SEASON_BY_COUNTRY`` (fixture-calendar
# level). The oracle ``expected_coverage()`` in ``registry/expected_coverage.py``
# does not include a per-league off-season gate because the oracle signature is
# per-(asset_group, source, data_type) without a league_id axis. Per-league
# oracle integration is Decision 3 (deferred — requires IS instrument-catalogue
# access).
#
# Bounded, SOURCE-LEVEL gaps (complete provider outages or protocol-level
# blackout periods where the source produced NO data at all for a date range)
# are declared in the evidence-gated, falsifiable SSOT instead:
#   ``unified_api_contracts.canonical.coverage_exclusions.COVERAGE_EXCLUSIONS``
# — mandatory typed reason + machine-checkable evidence + re-runnable probe + verified_at/by
# (enforced at construction), cross-asset, and continuously falsified by
# ``scripts/check_coverage_exclusions.py``. The oracle gate for it is cross-asset and fires
# for sports too, so there is no source-level-gap registry at this layer.
#
# The unevidenced ``KNOWN_COVERAGE_GAPS`` dict + its ``get_known_coverage_gaps`` /
# ``is_in_known_gap`` accessors were DELETED 2026-07-17 (frozen empty since 2026-07-17,
# deleted once MTDS' sports manifest-rebuild classifiers were migrated off them) — see
# ``codex/02-data/honest-coverage-model.md`` § Bounded coverage exclusions.


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
    # FootyStats — match aggregates + footystats' own in-house prediction model
    # + aggregated pre-match bookmaker odds snapshot.
    #
    # ODDS note (operator decision 2026-06-27, #6 REVERSED): footystats ODDS are a
    # PRE-MATCH SNAPSHOT (68 markets at kickoff-72h, all named books aggregated) — a
    # PREDICTIVE/reference signal captured by IS, NOT raw intra-day bookmaker ticks.
    # RAW bookmaker tick data (ODDS_SNAPSHOT/ODDS_MOVEMENT/ARBITRAGE) lives in MTDS
    # via odds-api. The two coexist: MTDS=tick market data, IS=footystats snapshot.
    # See codex/02-data/sports-data-source-coverage-matrix.md §2.2 for the full
    # PREDICTIONS vs ODDS disambiguation.
    # TEAMS/STANDINGS moved to api_football 2026-06-25 (canonical-form alignment):
    #   footystats writes ONLY footystats_matches/odds/predictions to disk — it does
    #   NOT write teams/standings. Those are written by the api_football handler under
    #   pipeline_mode=batch_api_football/entity={teams,standings}. This map was the
    #   stale outlier vs the canonical SOURCE_PRIORITY[("sports","teams"|"standings")]
    #   = ["api_football"] (the writer already raised MissingSourceError on footystats),
    #   which produced ~137k mis-sourced/phantom manifest rows. Aligned to the SSOT.
    # Keys are LOWERCASE per 2026-08-08 operator ruling (sports taxonomy canonicalisation
    # P1). IS writer still stamps UPPERCASE until P2 re-stamps; get_source_for_data_type()
    # normalises callers via .lower() so existing uppercase callers keep working.
    "matches": "footystats",
    "odds": "footystats",
    "predictions": "footystats",
    # Understat — xG model + per-shot xG
    "xg": "understat",
    "xg_shots": "understat",
    # API-Football — fixtures + per-fixture detail + reference (teams / standings)
    "fixtures": "api_football",
    # fixtures_schedule/fixtures_outcomes are the schedule/outcome split of the same
    # api_football fixtures feed (writer cutover 2026-07-14, fixture_lifecycle.py) —
    # missing here meant is_pre_launch_date() silently returned False for them,
    # letting ~83,541 pre-2020-06-06 objects misclassify as real orphans instead of
    # the pre-launch-floor violations they are (found 2026-07-22, orphan-sweep audit).
    "fixtures_schedule": "api_football",
    "fixtures_outcomes": "api_football",
    "injuries": "api_football",
    "fixture_stats": "api_football",
    "fixture_events": "api_football",
    "fixture_lineups": "api_football",
    "player_stats": "api_football",
    "teams": "api_football",
    "standings": "api_football",
    # Transfermarkt — player values.
    # TRANSFERMARKT_LEAGUES retired 2026-05-05 (was static catalog mapping;
    # lives in UAC TRANSFERMARKT_IDS as provider-id config rather than captured data).
    # TRANSFERMARKT_VALUES retired 2026-05-15 (stale alias — player_values is canonical).
    "player_values": "transfermarkt",
    # SoccerFootball.info.
    # SFI_LEAGUES retired 2026-05-05 (same reason — UAC SOCCER_FOOTBALL_INFO_IDS).
    # SFI_STANDINGS retired 2026-05-05 — SFI has no standings endpoint.
    "sfi_progressive_stats": "soccer_football_info",
    # OpenMeteo — historical weather
    "weather": "open_meteo",
    # MDPS odds horizon bucket — derived from odds-api
    "odds_horizon_bucket": "mdps_odds_horizon_bucket",
}


def get_source_for_data_type(data_type: str) -> str | None:
    """Return the source-key for a sports manifest ``data_type``, or
    ``None`` if unknown (caller should treat as no-clip).

    Normalises ``data_type`` to lowercase before lookup so existing callers
    that pass uppercase tokens (IS writer, backfill scripts) keep working
    across the P1→P2 transition (IS writer still stamps UPPERCASE until P2
    re-stamps the manifest; keys are canonical lowercase from P1 onwards).
    """
    return SPORTS_DATA_TYPE_TO_SOURCE.get(data_type.lower())


# ---------------------------------------------------------------------------
# Structural (league x source) honest-absence gaps (operator 2026-06-27 #6)
# ---------------------------------------------------------------------------
# Some (league x source) combinations are STRUCTURALLY UNAVAILABLE — the source
# simply does not carry that league, at ANY date. This is distinct from
# ``SOURCE_COVERAGE_START`` (a date floor): a structural gap is "the source
# NEVER has this league". Encoding it
# means:
#   1. the honest-coverage SSOT treats the (league x source) cell as
#      EXPECTED-ABSENT (it is NOT counted as missing in any denominator), and
#   2. the IS sports producers / download-attempts SKIP it entirely — no
#      attempt → no fail → no ``attempted_failed`` noise.
#
# Operator-confirmed structural gaps (2026-06-27 #6):
#   * A_LEAGUE          x footystats   — footystats does not carry the A-League.
#   * GREEK_SUPER_LEAGUE x transfermarkt — transfermarkt has no market-values
#                                          coverage for the Greek Super League.
#   * understat carries ONLY the "big-5" leagues (EPL / LA_LIGA / BUNDESLIGA /
#     SERIE_A / LIGUE_1). The other 89 football leagues x understat are NOT
#     carried — encoded as an understat ALLOW-LIST (its complement is structural
#     absence) so we never attempt understat XG for a non-big-5 league.
#
# Two encodings, both consulted by :func:`is_sports_structural_gap`:
#   * SPORTS_STRUCTURAL_GAPS — explicit (source → {league_ids it does NOT carry}).
#   * SPORTS_SOURCE_LEAGUE_ALLOWLIST — (source → {ONLY these leagues carried});
#     any league NOT in the allow-list is a structural gap for that source.
SPORTS_STRUCTURAL_GAPS: dict[str, frozenset[str]] = {
    "footystats": frozenset({"A_LEAGUE"}),
    "transfermarkt": frozenset({"GREEK_SUPER_LEAGUE"}),
}

#: understat carries ONLY the big-5 European leagues — every other league is a
#: structural gap for understat (operator 2026-06-27 #6). Keyed by source.
SPORTS_SOURCE_LEAGUE_ALLOWLIST: dict[str, frozenset[str]] = {
    "understat": frozenset({"EPL", "LA_LIGA", "BUNDESLIGA", "SERIE_A", "LIGUE_1"}),
}


def is_sports_structural_gap(source_key: str, league_id: str) -> bool:
    """Return ``True`` iff ``(source_key, league_id)`` is a STRUCTURAL gap.

    A structural gap means the source NEVER carries that league (at any date),
    so the cell is expected-absent for honest coverage AND the IS sports
    producers MUST skip it (no attempt → no ``attempted_failed`` noise). This is
    the SSOT both the coverage denominator and the IS sports adapters consult.

    Two rules (OR-combined):
      1. ``league_id`` is in the source's explicit gap set
         (:data:`SPORTS_STRUCTURAL_GAPS`).
      2. the source has an ALLOW-LIST (:data:`SPORTS_SOURCE_LEAGUE_ALLOWLIST`)
         AND ``league_id`` is NOT in it (understat big-5-only).

    Args:
        source_key: source identifier (``footystats`` / ``understat`` /
            ``transfermarkt`` / …) — the ``SPORTS_DATA_TYPE_TO_SOURCE`` value.
        league_id: canonical league id (case-insensitive).

    Returns:
        ``True`` when the (source, league) combo is structurally unavailable.
    """
    lid = league_id.upper()
    if lid in SPORTS_STRUCTURAL_GAPS.get(source_key, frozenset()):
        return True
    allow = SPORTS_SOURCE_LEAGUE_ALLOWLIST.get(source_key)
    return allow is not None and lid not in allow


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


def get_mvp_football_league_ids() -> frozenset[str]:
    """Canonical MVP/prediction-scope football league_ids (``in_mvp_scope=True``).

    SSOT for "which leagues are in the MVP football universe" — the scope any
    per-fixture enrichment or strategy/features consumer must use, as distinct
    from the much wider could-exist FIXTURES denominator
    (``get_expected_leagues_for_source``, 383 leagues post curated-universe
    expansion). The curated-universe expansion
    (plans/active/sports_satellite_ao_dispatch_batch2_2026_07_24.md) added
    wider-reference football entries (continental cups, majors) explicitly
    tagged ``in_mvp_scope=False`` so they widen FIXTURES coverage without
    widening MVP/prediction scope (operator 2026-07-24 Directive B).

    ``unified_api_contracts.canonical.crosscutting._mvp_scope_rules._mvp_football_league_ids()``
    delegates here — this is the single implementation, not a mirror.
    """
    return frozenset(
        league.league_id for league in LEAGUE_REGISTRY.values() if league.sport == "FOOTBALL" and league.in_mvp_scope
    )


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
    "LA_LIGA_2": dict.fromkeys(range(2020, 2027), 22),
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
    frozenset contains ``source_key`` AND that are not a structural gap for
    that source per :func:`is_sports_structural_gap` (the explicit
    ``SPORTS_STRUCTURAL_GAPS``/``SPORTS_SOURCE_LEAGUE_ALLOWLIST`` SSOT). The
    two checks currently agree for every registry entry (``data_sources`` is
    hand-curated to already exclude known gaps) — this is defense-in-depth so
    a future ``data_sources`` edit can't silently diverge from the explicit
    gap/allowlist SSOT and reintroduce an ad-hoc-vs-declared mismatch.
    Optionally restrict by league classification (``Prediction`` /
    ``Features`` / ``Reference`` / ``Other``).

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
        if source_key in league.data_sources
        and not is_sports_structural_gap(source_key, league.league_id)
        and (allowed is None or league.classification.lower() in allowed)
    ]


# ---------------------------------------------------------------------------
# Config versioning — monotonic version + deterministic content hash for the
# sports-leagues config. PER-CONFIG (independent of MVP_SCOPE / prediction-
# markets), surfaced in data-status so a coverage delta attributes to a
# leagues-scope change (e.g. an added/removed league) vs a data change.
# Metadata only — never a GCS partition key. SSOT:
# ``plans/active/mvp_scope_catalogue_tagging_2026_06_08.md`` § Config versioning.
# ---------------------------------------------------------------------------

SPORTS_LEAGUES_CONFIG_VERSION: int = 3
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
    "LEAGUE_EXPECTED_TEAM_COUNTS",
    "LEAGUE_REGISTRY",
    "NON_FOOTBALL_LEAGUES",
    "PREDICTION_LEAGUES",
    "REFERENCE_LEAGUES",
    "SOURCE_COVERAGE_START",
    "SPORTS_LEAGUES_CONFIG_HASH",
    "SPORTS_LEAGUES_CONFIG_VERSION",
    "SPORTS_SOURCE_LEAGUE_ALLOWLIST",
    "SPORTS_STRUCTURAL_GAPS",
    "clip_dates_to_source_coverage",
    "get_all_prediction_league_ids",
    "get_expected_leagues_for_source",
    "get_expected_team_count_for_league",
    "get_league",
    "get_league_by_api_football_id",
    "get_league_fixture_calendar",
    "get_leagues_by_classification",
    "get_leagues_by_country",
    "get_leagues_for_sport",
    "get_live_stats_api_football_ids",
    "get_mvp_football_league_ids",
    "get_prediction_leagues",
    "get_source_coverage_start",
    "is_sports_structural_gap",
    "sports_leagues_config_descriptor",
]
