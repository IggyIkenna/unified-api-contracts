"""Season-structure registry — external truth for fixture-completeness oracle.

Per (league_id, season_year), encodes:
  - n_teams / format / expected_fixtures: the denominator for "did we capture
    every game?" (depth_coverage Tier-B per codex §2.1).
  - expected_breaks: known calendar gaps that are NOT capture gaps.
  - promotion_relegation_extra_fixtures: playoff fixtures added on top of the
    regular-season count.

This is the sports analogue of the cefi futures expiry-schedule oracle —
encode external listing/structure truth, versioned by effective season, so
any historical day is honestly scored.

Design:
  - ``FixtureFormat`` names the scheduling model; ``expected_fixtures`` is
    always explicit (never computed lazily) so callers do a single dict
    lookup without branching on format.
  - For ``DOUBLE_ROUND_ROBIN`` leagues ``expected_fixtures = n_teams *
    (n_teams - 1)`` and is stored pre-computed for clarity.
  - For ``MULTI_PHASE`` / ``SPLIT`` / ``CONFERENCE`` / ``APERTURA_CLAUSURA``
    leagues the value is derived from the known league rule for that season
    and stored directly.
  - Breaks are stored as (month_start, month_end, name) so the validator can
    suppress unexplained calendar gaps inside these windows.

SSOT for fixture-completeness oracle.  Add new entries when leagues change
format or the universe expands.  See
``instruments_service.sports.fixture_completeness`` for the validator that
reads this registry.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import NamedTuple


class FixtureFormat(StrEnum):
    """High-level scheduling model for a league season."""

    DOUBLE_ROUND_ROBIN = "double_round_robin"
    """Each team plays every other team home AND away (the default)."""

    SPLIT = "split"
    """Double (or triple) round-robin followed by a split-phase where teams
    are divided into groups (top-half / bottom-half) for additional fixtures.
    Scottish Premiership (triple RR + 5-round split) is the canonical example."""

    MULTI_PHASE = "multi_phase"
    """Regular season followed by championship/playoff groups with reset or
    carry-over points.  Belgian Pro League, Austrian Bundesliga, Greek Super
    League, Danish Superliga post-2020."""

    CONFERENCE = "conference"
    """Teams organised into conferences; inter-conference games are a subset.
    MLS Eastern/Western Conference model."""

    APERTURA_CLAUSURA = "apertura_clausura"
    """Season split into two short tournaments (Apertura / Clausura).
    Liga MX and Argentine Primera División."""


class SeasonBreak(NamedTuple):
    """A calendar window where no fixtures are expected.

    ``month_start`` / ``month_end`` are 1-indexed (January = 1).  For a break
    that crosses the calendar year (e.g. Dec-Jan) ``month_end < month_start``.
    """

    name: str
    month_start: int
    month_end: int


@dataclass(frozen=True)
class SeasonStructure:
    """Complete structural description of one league-season.

    Attributes:
        league_id: Canonical league identifier (e.g. ``"EPL"``).
        season_year: The calendar year in which the season STARTS.  For
            cross-year seasons (e.g. EPL Aug 2025 - May 2026) this is 2025.
        n_teams: Number of teams competing in the regular season.
        format: Scheduling model (see ``FixtureFormat``).
        expected_fixtures: Total regular-season fixtures.  For
            ``DOUBLE_ROUND_ROBIN`` this equals ``n_teams * (n_teams - 1)``.
            For other formats it is the known season total (regular phase
            only; playoff extras are in ``promotion_relegation_extra``).
        expected_breaks: Known calendar gaps inside the season window where
            zero fixture dates are expected (winter break, international
            breaks, mid-season splits).  An unexplained gap outside these
            windows is flagged as a capture gap.
        promotion_relegation_extra: Additional playoff fixtures beyond the
            regular-season count (e.g. Championship play-offs = 3 per
            finalist pair, ENG_CHAMPIONSHIP = 3 extra matches).
    """

    league_id: str
    season_year: int
    n_teams: int
    format: FixtureFormat
    expected_fixtures: int
    expected_breaks: list[SeasonBreak] = field(default_factory=list)
    promotion_relegation_extra: int = 0


# ---------------------------------------------------------------------------
# Common break definitions (reused across leagues)
# ---------------------------------------------------------------------------

_INTL_BREAKS: list[SeasonBreak] = [
    SeasonBreak("international_break_sept", 9, 9),
    SeasonBreak("international_break_oct", 10, 10),
    SeasonBreak("international_break_nov", 11, 11),
    SeasonBreak("international_break_mar", 3, 3),
    SeasonBreak("international_break_jun", 6, 6),
]
_WINTER_BREAK_DEC_JAN = SeasonBreak("winter_break", 12, 1)
_WINTER_BREAK_DEC_FEB = SeasonBreak("winter_break", 12, 2)
_WINTER_BREAK_NOV_MAR = SeasonBreak("winter_break", 11, 3)  # Nordic/Australasian


def _drr(league_id: str, season_year: int, n_teams: int,
         extra_breaks: list[SeasonBreak] | None = None,
         promo_extra: int = 0) -> SeasonStructure:
    """Shorthand for a standard double-round-robin league-season."""
    breaks = [*_INTL_BREAKS, *(extra_breaks or [])]
    return SeasonStructure(
        league_id=league_id,
        season_year=season_year,
        n_teams=n_teams,
        format=FixtureFormat.DOUBLE_ROUND_ROBIN,
        expected_fixtures=n_teams * (n_teams - 1),
        expected_breaks=breaks,
        promotion_relegation_extra=promo_extra,
    )


# ---------------------------------------------------------------------------
# SEASON_STRUCTURE_REGISTRY
# keyed by league_id → list of SeasonStructure (one per season_year)
# Seasons 2019-2026 for the 33 MVP prediction leagues.
# ---------------------------------------------------------------------------

def _europe_western(reg: dict[str, list[SeasonStructure]]) -> None:
    """Populate England, Scotland, Spain, Germany, Italy, France."""
    for lid, n in [("EPL", 20), ("ENG_CHAMPIONSHIP", 24),
                   ("ENG_LEAGUE_ONE", 24), ("ENG_LEAGUE_TWO", 24)]:
        promo_extra = 5 if lid != "EPL" else 0  # EFL play-offs
        reg[lid] = [_drr(lid, y, n, promo_extra=promo_extra) for y in range(2019, 2027)]

    # Scottish Premiership: 12 teams, triple-RR then top/bottom split = 228 fixtures.
    reg["SCOTTISH_PREMIERSHIP"] = [
        SeasonStructure("SCOTTISH_PREMIERSHIP", y, 12, FixtureFormat.SPLIT, 228,
                        [*_INTL_BREAKS, _WINTER_BREAK_DEC_JAN], 2)
        for y in range(2019, 2027)
    ]

    reg["LA_LIGA"] = [_drr("LA_LIGA", y, 20) for y in range(2019, 2027)]
    reg["SEGUNDA_DIVISION"] = [_drr("SEGUNDA_DIVISION", y, 22) for y in range(2019, 2027)]

    _de_breaks = [_WINTER_BREAK_DEC_JAN]
    reg["BUNDESLIGA"] = [_drr("BUNDESLIGA", y, 18, extra_breaks=_de_breaks) for y in range(2019, 2027)]
    reg["BUNDESLIGA_2"] = [_drr("BUNDESLIGA_2", y, 18, extra_breaks=_de_breaks) for y in range(2019, 2027)]
    reg["LIGA_3"] = [_drr("LIGA_3", y, 20, extra_breaks=_de_breaks) for y in range(2019, 2027)]

    reg["SERIE_A"] = [_drr("SERIE_A", y, 20) for y in range(2019, 2027)]
    reg["SERIE_B"] = [_drr("SERIE_B", y, 20) for y in range(2019, 2027)]

    # Ligue 1: 20 teams until 2022-23, 18 teams from 2023-24.
    reg["LIGUE_1"] = [_drr("LIGUE_1", y, 20 if y < 2023 else 18) for y in range(2019, 2027)]
    reg["LIGUE_2"] = [_drr("LIGUE_2", y, 20) for y in range(2019, 2027)]


def _europe_other(reg: dict[str, list[SeasonStructure]]) -> None:
    """Populate Netherlands, Portugal, Belgium, Turkey, Greece, Austria, Switzerland."""
    _nl_breaks = [_WINTER_BREAK_DEC_JAN]
    reg["EREDIVISIE"] = [_drr("EREDIVISIE", y, 18, extra_breaks=_nl_breaks) for y in range(2019, 2027)]
    reg["PRIMEIRA_LIGA"] = [_drr("PRIMEIRA_LIGA", y, 18) for y in range(2019, 2027)]

    # Jupiler Pro League: 18 teams, DRR (306) + top-6 championship playoff (15) = 321.
    reg["JUPILER_PRO"] = [
        SeasonStructure("JUPILER_PRO", y, 18, FixtureFormat.MULTI_PHASE, 321,
                        [*_INTL_BREAKS, _WINTER_BREAK_DEC_JAN], 6)
        for y in range(2019, 2027)
    ]

    # Super Lig: 20 teams pre-2024, 19 from 2024 onwards.
    reg["SUPER_LIG"] = [
        _drr("SUPER_LIG", y, 20 if y < 2024 else 19, extra_breaks=[_WINTER_BREAK_DEC_JAN])
        for y in range(2019, 2027)
    ]

    # Greek Super League: 14 teams, DRR regular (182) + multi-phase playoffs.
    reg["GREEK_SUPER_LEAGUE"] = [
        SeasonStructure("GREEK_SUPER_LEAGUE", y, 14, FixtureFormat.MULTI_PHASE, 182,
                        [*_INTL_BREAKS], 43)
        for y in range(2019, 2027)
    ]

    # Austrian Bundesliga: 12 teams, DRR (132) + top/bottom playoff groups = 162.
    reg["AUSTRIAN_BUNDESLIGA"] = [
        SeasonStructure("AUSTRIAN_BUNDESLIGA", y, 12, FixtureFormat.MULTI_PHASE, 162,
                        [*_INTL_BREAKS, _WINTER_BREAK_DEC_FEB], 4)
        for y in range(2019, 2027)
    ]

    # Swiss Super League: 10 teams (pre-2023) / 12 teams (2023+), MULTI_PHASE.
    def _swiss(y: int) -> SeasonStructure:
        n, expected = (10, 110) if y < 2023 else (12, 162)
        return SeasonStructure("SWISS_SUPER_LEAGUE", y, n,
                               FixtureFormat.MULTI_PHASE, expected,
                               [*_INTL_BREAKS, _WINTER_BREAK_DEC_JAN])
    reg["SWISS_SUPER_LEAGUE"] = [_swiss(y) for y in range(2019, 2027)]

    # Nordic leagues: spring-autumn calendar, long winter off-season.
    _nordic_breaks = [_WINTER_BREAK_NOV_MAR]
    reg["DANISH_SUPERLIGA"] = [_drr("DANISH_SUPERLIGA", y, 14, extra_breaks=_nordic_breaks)
                               for y in range(2019, 2027)]
    reg["ELITESERIEN"] = [_drr("ELITESERIEN", y, 16, extra_breaks=_nordic_breaks)
                          for y in range(2019, 2027)]
    reg["ALLSVENSKAN"] = [_drr("ALLSVENSKAN", y, 16, extra_breaks=_nordic_breaks)
                          for y in range(2019, 2027)]
    reg["EKSTRAKLASA"] = [_drr("EKSTRAKLASA", y, 18, extra_breaks=[_WINTER_BREAK_DEC_FEB])
                          for y in range(2019, 2027)]


def _americas(reg: dict[str, list[SeasonStructure]]) -> None:
    """Populate MLS, Brasileirao, Argentina, Chile, Liga MX."""
    # MLS: CONFERENCE format; fixture count varies by team count and season.
    _mls_n = {2019: 26, 2020: 26, 2021: 27, 2022: 28, 2023: 29,
              2024: 29, 2025: 30, 2026: 30}
    _mls_fx = {2019: 374, 2020: 217, 2021: 406, 2022: 476,
               2023: 493, 2024: 493, 2025: 510, 2026: 510}
    reg["MLS"] = [
        SeasonStructure("MLS", y, _mls_n.get(y, 30), FixtureFormat.CONFERENCE,
                        _mls_fx.get(y, _mls_n.get(y, 30) * 34 // 2),
                        [*_INTL_BREAKS], 13)
        for y in range(2019, 2027)
    ]

    reg["BRASILEIRAO"] = [_drr("BRASILEIRAO", y, 20) for y in range(2019, 2027)]

    # Argentina: Apertura/Clausura, 28 teams, two single round-robins per year.
    reg["ARGENTINA_PRIMERA"] = [
        SeasonStructure("ARGENTINA_PRIMERA", y, 28, FixtureFormat.APERTURA_CLAUSURA,
                        28 * 27, [*_INTL_BREAKS], 4)
        for y in range(2019, 2027)
    ]

    # Chile: Apertura/Clausura, 16 teams.
    reg["CHILE_PRIMERA"] = [
        SeasonStructure("CHILE_PRIMERA", y, 16, FixtureFormat.APERTURA_CLAUSURA,
                        16 * 15, [*_INTL_BREAKS])
        for y in range(2019, 2027)
    ]

    # Liga MX: Apertura/Clausura, 18 teams, 306 regular + 8 Liguilla.
    reg["LIGA_MX"] = [
        SeasonStructure("LIGA_MX", y, 18, FixtureFormat.APERTURA_CLAUSURA,
                        306, [*_INTL_BREAKS], 8)
        for y in range(2019, 2027)
    ]


def _asia_pacific(reg: dict[str, list[SeasonStructure]]) -> None:
    """Populate J1 League, K-League 1, A-League."""
    reg["J1_LEAGUE"] = [_drr("J1_LEAGUE", y, 18, extra_breaks=[_INTL_BREAKS[3]])
                        for y in range(2019, 2027)]

    # K-League 1: 12 teams, triple-RR (198) + Finals Round (15) = 213.
    reg["K_LEAGUE_1"] = [
        SeasonStructure("K_LEAGUE_1", y, 12, FixtureFormat.SPLIT, 213,
                        [*_INTL_BREAKS, _WINTER_BREAK_DEC_JAN])
        for y in range(2019, 2027)
    ]

    # A-League: spring-autumn (Oct-May), 12 teams pre-2024, 13 from 2024.
    def _a_league(y: int) -> SeasonStructure:
        n = 12 if y < 2024 else 13
        return SeasonStructure("A_LEAGUE", y, n, FixtureFormat.DOUBLE_ROUND_ROBIN,
                               n * (n - 1), [_WINTER_BREAK_NOV_MAR], 5)
    reg["A_LEAGUE"] = [_a_league(y) for y in range(2019, 2027)]


def _build_registry() -> dict[str, list[SeasonStructure]]:
    reg: dict[str, list[SeasonStructure]] = {}
    _europe_western(reg)
    _europe_other(reg)
    _americas(reg)
    _asia_pacific(reg)
    return reg


SEASON_STRUCTURE_REGISTRY: dict[str, list[SeasonStructure]] = _build_registry()

# Fast lookup index: (league_id, season_year) → SeasonStructure
_INDEX: dict[tuple[str, int], SeasonStructure] = {
    (s.league_id, s.season_year): s
    for seasons in SEASON_STRUCTURE_REGISTRY.values()
    for s in seasons
}


# ---------------------------------------------------------------------------
# Public accessors
# ---------------------------------------------------------------------------


def get_season_structure(league_id: str, season_year: int) -> SeasonStructure | None:
    """Return the SeasonStructure for ``league_id`` in ``season_year``, or
    ``None`` if not yet registered."""
    return _INDEX.get((league_id.upper(), season_year))


def get_expected_fixture_count(league_id: str, season_year: int) -> int | None:
    """Return the total expected regular-season fixture count, or ``None``."""
    s = get_season_structure(league_id, season_year)
    return s.expected_fixtures if s is not None else None


def get_all_league_ids() -> list[str]:
    """Return all league IDs that have a registered season structure."""
    return sorted(SEASON_STRUCTURE_REGISTRY.keys())


__all__ = [
    "SEASON_STRUCTURE_REGISTRY",
    "FixtureFormat",
    "SeasonBreak",
    "SeasonStructure",
    "get_all_league_ids",
    "get_expected_fixture_count",
    "get_season_structure",
]
