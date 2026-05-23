"""FootyStats venue-specific normalizers.

FootyStatsMatch, FootyStatsOdds -> CanonicalBetMarket, CanonicalOdds, CanonicalFixture.
Uses _d, _to_decimal, _ts_ms_to_datetime from normalize_utils._helpers.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from unified_api_contracts.canonical.domain import CanonicalBetMarket, CanonicalOdds
from unified_api_contracts.canonical.domain.sports import (
    CanonicalFixture,
    CanonicalLeague,
    CanonicalTeam,
    build_fixture_id,
    build_league_id,
    build_team_id,
)
from unified_api_contracts.normalize_utils._helpers import to_decimal as _to_decimal
from unified_api_contracts.normalize_utils._helpers import unix_sec_to_utc as _ts_sec

from .schemas import FootyStatsMatch, FootyStatsOdds, FTMatchRaw


def normalize_footystats_match(raw: FootyStatsMatch, venue: str = "footystats") -> CanonicalFixture:
    """Convert FootyStatsMatch to CanonicalFixture with human-readable canonical IDs."""
    kickoff_utc = _ts_sec(raw.date_unix) if raw.date_unix > 0 else datetime.now(UTC)

    home_name = raw.home_name or ""
    away_name = raw.away_name or ""
    home_team = CanonicalTeam(
        team_id=build_team_id(home_name),
        name=home_name,
        short_name=None,
        country=None,
        founded=None,
        logo_url=None,
        venue=None,
    )
    away_team = CanonicalTeam(
        team_id=build_team_id(away_name),
        name=away_name,
        short_name=None,
        country=None,
        founded=None,
        logo_url=None,
        venue=None,
    )

    league = CanonicalLeague(
        league_id=build_league_id("", str(raw.competition_id or "")),
        name="",
        country="",
        league_type=None,
        logo_url=None,
    )

    date_str = kickoff_utc.strftime("%Y%m%d")
    fixture_id = (
        build_fixture_id(
            league.league_id,
            home_team.team_id,
            away_team.team_id,
            date_str,
        )
        if home_team.team_id and away_team.team_id
        else str(raw.match_id or "")
    )

    return CanonicalFixture(
        fixture_id=fixture_id,
        home_team=home_team,
        away_team=away_team,
        league=league,
        kickoff_utc=kickoff_utc,
        venue=None,
        referee=None,
        season=raw.season or "",
        match_week=raw.game_week,
        source=venue,
        status=raw.status,
        home_goals=raw.home_goals,
        away_goals=raw.away_goals,
        home_goals_halftime=raw.home_goals_halftime,
        away_goals_halftime=raw.away_goals_halftime,
        home_xg=raw.home_xg,
        away_xg=raw.away_xg,
        home_shots_on_target=raw.home_shots_on_target,
        away_shots_on_target=raw.away_shots_on_target,
        home_total_shots=raw.home_shots,
        away_total_shots=raw.away_shots,
        home_possession=raw.home_possession,
        away_possession=raw.away_possession,
        home_corners=raw.home_corners,
        away_corners=raw.away_corners,
        home_fouls=raw.home_fouls,
        away_fouls=raw.away_fouls,
        home_yellow_cards=raw.home_yellow_cards,
        away_yellow_cards=raw.away_yellow_cards,
        home_red_cards=raw.home_red_cards,
        away_red_cards=raw.away_red_cards,
        home_shots_blocked=None,
        away_shots_blocked=None,
        home_offsides=raw.home_offsides,
        away_offsides=raw.away_offsides,
        home_passes_total=None,
        away_passes_total=None,
        home_passes_accuracy=None,
        away_passes_accuracy=None,
    )


def normalize_footystats_match_to_market(raw: FootyStatsMatch, venue: str = "footystats") -> CanonicalBetMarket:
    """Convert FootyStatsMatch to CanonicalBetMarket."""
    now = datetime.now(UTC)
    close_time: datetime | None = None
    if raw.date_unix > 0:
        close_time = _ts_sec(raw.date_unix)

    event_name = f"{raw.home_name or ''} vs {raw.away_name or ''}"

    return CanonicalBetMarket(
        venue=venue,
        market_id=str(raw.match_id or ""),
        event_id=str(raw.match_id or ""),
        market_name=event_name,
        event_name=event_name,
        sport=None,
        competition=None,
        status=raw.status,
        in_play=None,
        timestamp=now,
        close_time=close_time,
    )


def normalize_footystats_odds(
    raw: FootyStatsOdds,
    event_name: str = "",
    venue: str = "footystats",
) -> CanonicalOdds:
    """Convert ``FootyStatsOdds`` to ``CanonicalOdds``.

    **What this is**: real published bookmaker odds for a match-market-selection.
    FootyStats aggregates published prices from named bookmakers and exposes them as
    decimal odds — these are MARKET DATA (what the book offered).

    **NOT to be confused with** ``normalize_footystats_predictions`` (below) which
    extracts FootyStats-PROPRIETARY pre-match forecasts (potentials, xG prematch,
    PPG) — those are MODEL OUTPUT, not market odds, even though their values look
    odds-like (probabilities, decimal coefficients). Per C.3 audit 2026-05-07
    (`session_2026_05_07_data_status_audit_findings.md`): the deployment-ui
    data-status panel renders both data_types side-by-side; the disambiguation
    is critical so consumers know whether they're reading book quotes
    (this fn → ``data_type=ODDS``) or FootyStats's own forecasts
    (``normalize_footystats_predictions`` → ``data_type=PREDICTIONS``).

    Sister fn ``normalize_footystats_odds_snapshot`` (below) is the pre-match-
    snapshot variant captured by ``get_fixture_odds_snapshot()``; same source,
    flat-row shape covering 68 markets, written to ``entity=footystats_odds``
    in instruments-service. ``available_at = kickoff - 72h`` (FootyStats
    publishes opening odds ~3 days before kickoff).
    """
    match_id = str(raw.match_id or "")
    dec = _to_decimal(raw.odds_value)
    if dec is None or dec <= 0:
        dec = Decimal("2.0")
    selection_id = f"{match_id}:{raw.market_type or ''}:{raw.market_option or ''}".replace(" ", "_")
    return CanonicalOdds(
        venue=venue,
        event_id=match_id,
        market_id=f"{match_id}:{raw.market_type or ''}",
        selection_id=selection_id,
        selection_name=raw.market_option or "",
        decimal_odds=dec,
        timestamp=datetime.now(UTC),
        is_back=True,
        available_size=None,
        event_name=event_name,
        sport=None,
        competition=None,
    )


def normalize_footystats_predictions(raw: FootyStatsMatch, venue: str = "footystats") -> dict[str, object]:
    """Extract FootyStats PROPRIETARY pre-match forecast fields.

    Returns a flat dict suitable for a DataFrame row. These fields are
    FootyStats's own MODEL OUTPUT — NOT bookmaker odds. They represent
    FootyStats's forecast of match outcomes:

    - **Potentials** (``btts_potential``, ``o05_potential`` … ``o45_potential``,
      ``corners_potential``, ``cards_potential``, ``offsides_potential``,
      ``avg_potential``): FootyStats's proprietary likelihood scores
      (NOT bookmaker odds). Higher = more likely per FootyStats's model.
    - **Pre-match xG** (``xg_prematch_home``/``away``/``total``):
      FootyStats's pre-game expected-goals model.
    - **PPG** (``pre_match_home_ppg``/``away_ppg``/``home_overall_ppg``/
      ``away_overall_ppg``): FootyStats's points-per-game projections.

    **NOT to be confused with** ``normalize_footystats_odds``
    (above) and ``normalize_footystats_odds_snapshot`` (below) which return
    REAL BOOKMAKER ODDS aggregated by FootyStats from named books. Per C.3
    audit 2026-05-07 (`session_2026_05_07_data_status_audit_findings.md`):
    the deployment-ui data-status panel renders both data_types side-by-side;
    the disambiguation is critical so consumers know whether they're reading
    FootyStats's own forecasts (this fn → ``data_type=PREDICTIONS``,
    ``entity=footystats_predictions``) or book quotes (the odds normalizers
    → ``data_type=ODDS``, ``entity=footystats_odds``).

    Both data_types share the same source (FootyStats) and similar
    `available_at` (kickoff - 72h, since FootyStats publishes both
    opening odds and prematch predictions on the same ~3-day-out cadence)
    but they ARE NOT the same data and SHOULD NOT be merged in features.
    """
    kickoff_utc = _ts_sec(raw.date_unix) if raw.date_unix > 0 else datetime.now(UTC)
    home_name = raw.home_name or ""
    away_name = raw.away_name or ""

    date_str = kickoff_utc.strftime("%Y%m%d")
    home_id = build_team_id(home_name)
    away_id = build_team_id(away_name)
    league_id = build_league_id("", str(raw.competition_id or ""))
    fixture_id = (
        build_fixture_id(league_id, home_id, away_id, date_str) if home_id and away_id else str(raw.match_id or "")
    )

    return {
        "fixture_id": fixture_id,
        "source": venue,
        "kickoff_utc": kickoff_utc.isoformat(),
        "home_team": home_name,
        "away_team": away_name,
        # Potentials (full set)
        "btts_potential": raw.btts_potential,
        "btts_fhg_potential": raw.btts_fhg_potential,
        "btts_2hg_potential": raw.btts_2hg_potential,
        "o05_potential": raw.o05_potential,
        "o15_potential": raw.o15_potential,
        "o25_potential": raw.o25_potential,
        "o35_potential": raw.o35_potential,
        "o45_potential": raw.o45_potential,
        "u05_potential": raw.u05_potential,
        "u15_potential": raw.u15_potential,
        "u25_potential": raw.u25_potential,
        "u35_potential": raw.u35_potential,
        "u45_potential": raw.u45_potential,
        "o05HT_potential": raw.o05HT_potential,
        "o15HT_potential": raw.o15HT_potential,
        "o05_2H_potential": raw.o05_2H_potential,
        "o15_2H_potential": raw.o15_2H_potential,
        "corners_o85_potential": raw.corners_o85_potential,
        "corners_o95_potential": raw.corners_o95_potential,
        "corners_o105_potential": raw.corners_o105_potential,
        "corners_potential": raw.corners_potential,
        "cards_potential": raw.cards_potential,
        "offsides_potential": raw.offsides_potential,
        "avg_potential": raw.avg_potential,
        # Pre-match xG
        "xg_prematch_home": raw.xg_prematch_home,
        "xg_prematch_away": raw.xg_prematch_away,
        "xg_prematch_total": raw.xg_prematch_total,
        # PPG
        "pre_match_home_ppg": raw.pre_match_home_ppg,
        "pre_match_away_ppg": raw.pre_match_away_ppg,
        "pre_match_home_overall_ppg": raw.pre_match_team_a_overall_ppg,
        "pre_match_away_overall_ppg": raw.pre_match_team_b_overall_ppg,
    }


def normalize_footystats_odds_snapshot(
    raw: FootyStatsMatch | FTMatchRaw,
    venue: str = "footystats",
) -> dict[str, object]:
    """Extract all odds fields from a FootyStats match as a flat dict.

    See ``normalize_footystats_odds`` docstring for the bookmaker-odds vs
    FootyStats-predictions distinction (per C.3 audit 2026-05-07): this
    fn returns REAL book quotes (same class of data as ``normalize_footystats_odds``),
    just in flat-row dict shape across 68 markets for the pre-match snapshot
    used by ``data_type=ODDS`` / ``entity=footystats_odds`` in
    instruments-service. NOT FootyStats's proprietary forecasts (those live
    in ``normalize_footystats_predictions`` / ``data_type=PREDICTIONS``).

    Accepts either ``FootyStatsMatch`` or ``FTMatchRaw``. Uses ``getattr``
    for fields that may not exist on the normalized model.

    Returns a row suitable for a DataFrame written to ``entity=footystats_odds``.
    """
    kickoff_utc = _ts_sec(raw.date_unix) if raw.date_unix is not None and raw.date_unix > 0 else datetime.now(UTC)
    home_name = raw.home_name or ""
    away_name = raw.away_name or ""

    date_str = kickoff_utc.strftime("%Y%m%d")
    home_id = build_team_id(home_name)
    away_id = build_team_id(away_name)
    league_id = build_league_id("", str(raw.competition_id or ""))
    _match_id = getattr(raw, "ft_match_id", None) or getattr(raw, "match_id", "")
    fixture_id = build_fixture_id(league_id, home_id, away_id, date_str) if home_id and away_id else str(_match_id)

    return {
        "fixture_id": fixture_id,
        "canonical_fixture_id": fixture_id,
        "source": venue,
        "kickoff_utc": kickoff_utc.isoformat(),
        "home_team": home_name,
        "away_team": away_name,
        # Full-time 1X2
        "odds_ft_1": raw.odds_ft_1,
        "odds_ft_x": raw.odds_ft_x,
        "odds_ft_2": raw.odds_ft_2,
        # Full-time over/under (all lines)
        "odds_ft_over05": raw.odds_ft_over05,
        "odds_ft_over15": raw.odds_ft_over15,
        "odds_ft_over25": raw.odds_ft_over25,
        "odds_ft_over35": raw.odds_ft_over35,
        "odds_ft_over45": raw.odds_ft_over45,
        "odds_ft_under05": raw.odds_ft_under05,
        "odds_ft_under15": raw.odds_ft_under15,
        "odds_ft_under25": raw.odds_ft_under25,
        "odds_ft_under35": raw.odds_ft_under35,
        "odds_ft_under45": raw.odds_ft_under45,
        # BTTS
        "odds_btts_yes": raw.odds_btts_yes,
        "odds_btts_no": raw.odds_btts_no,
        "odds_btts_1st_half_yes": raw.odds_btts_1st_half_yes,
        "odds_btts_1st_half_no": raw.odds_btts_1st_half_no,
        "odds_btts_2nd_half_yes": raw.odds_btts_2nd_half_yes,
        "odds_btts_2nd_half_no": raw.odds_btts_2nd_half_no,
        # Double chance + DNB
        "odds_doublechance_1x": raw.odds_doublechance_1x,
        "odds_doublechance_12": raw.odds_doublechance_12,
        "odds_doublechance_x2": raw.odds_doublechance_x2,
        "odds_dnb_1": raw.odds_dnb_1,
        "odds_dnb_2": raw.odds_dnb_2,
        # 1st half
        "odds_1st_half_result_1": raw.odds_1st_half_result_1,
        "odds_1st_half_result_x": raw.odds_1st_half_result_x,
        "odds_1st_half_result_2": raw.odds_1st_half_result_2,
        "odds_1st_half_over05": raw.odds_1st_half_over05,
        "odds_1st_half_over15": raw.odds_1st_half_over15,
        "odds_1st_half_over25": raw.odds_1st_half_over25,
        "odds_1st_half_over35": raw.odds_1st_half_over35,
        "odds_1st_half_under05": raw.odds_1st_half_under05,
        "odds_1st_half_under15": raw.odds_1st_half_under15,
        "odds_1st_half_under25": raw.odds_1st_half_under25,
        "odds_1st_half_under35": raw.odds_1st_half_under35,
        # 2nd half
        "odds_2nd_half_result_1": raw.odds_2nd_half_result_1,
        "odds_2nd_half_result_x": raw.odds_2nd_half_result_x,
        "odds_2nd_half_result_2": raw.odds_2nd_half_result_2,
        "odds_2nd_half_over05": raw.odds_2nd_half_over05,
        "odds_2nd_half_over15": raw.odds_2nd_half_over15,
        "odds_2nd_half_over25": raw.odds_2nd_half_over25,
        "odds_2nd_half_over35": raw.odds_2nd_half_over35,
        "odds_2nd_half_under05": raw.odds_2nd_half_under05,
        "odds_2nd_half_under15": raw.odds_2nd_half_under15,
        "odds_2nd_half_under25": raw.odds_2nd_half_under25,
        "odds_2nd_half_under35": raw.odds_2nd_half_under35,
        # Corners
        "odds_corners_1": raw.odds_corners_1,
        "odds_corners_2": raw.odds_corners_2,
        "odds_corners_x": raw.odds_corners_x,
        "odds_corners_over_75": raw.odds_corners_over_75,
        "odds_corners_over_85": raw.odds_corners_over_85,
        "odds_corners_over_95": raw.odds_corners_over_95,
        "odds_corners_over_105": raw.odds_corners_over_105,
        "odds_corners_over_115": raw.odds_corners_over_115,
        "odds_corners_under_75": raw.odds_corners_under_75,
        "odds_corners_under_85": raw.odds_corners_under_85,
        "odds_corners_under_95": raw.odds_corners_under_95,
        "odds_corners_under_105": raw.odds_corners_under_105,
        "odds_corners_under_115": raw.odds_corners_under_115,
        # Clean sheet
        "odds_team_a_cs_yes": raw.odds_team_a_cs_yes,
        "odds_team_a_cs_no": raw.odds_team_a_cs_no,
        "odds_team_b_cs_yes": raw.odds_team_b_cs_yes,
        "odds_team_b_cs_no": raw.odds_team_b_cs_no,
        # Specials
        "odds_team_to_score_first_1": raw.odds_team_to_score_first_1,
        "odds_team_to_score_first_2": raw.odds_team_to_score_first_2,
        "odds_team_to_score_first_x": raw.odds_team_to_score_first_x,
        "odds_win_to_nil_1": raw.odds_win_to_nil_1,
        "odds_win_to_nil_2": raw.odds_win_to_nil_2,
    }


__all__ = [
    "normalize_footystats_match",
    "normalize_footystats_match_to_market",
    "normalize_footystats_odds",
    "normalize_footystats_odds_snapshot",
    "normalize_footystats_predictions",
]
