"""Odds API v4 market key <-> OddsType mapping."""

from __future__ import annotations

from ...canonical.domain.sports.odds import OddsType

ODDS_API_MARKET_KEYS: dict[OddsType, str] = {
    OddsType.H2H: "h2h",
    OddsType.OVER_UNDER: "totals",
    OddsType.ASIAN_HANDICAP: "spreads",
    OddsType.BOTH_TEAMS_SCORE: "btts",
    OddsType.CORRECT_SCORE: "correct_score",
    OddsType.OUTRIGHT: "outrights",
    OddsType.DRAW_NO_BET: "draw_no_bet",
    OddsType.DOUBLE_CHANCE: "double_chance",
    OddsType.PLAYER_PROPS: "player_pass_tds",
}

ALL_SOCCER_MARKETS = ",".join(
    [
        "h2h",
        "spreads",
        "totals",
        "btts",
        "draw_no_bet",
        "double_chance",
    ]
)
DEFAULT_MARKETS = "h2h,spreads,totals"

__all__ = ["ALL_SOCCER_MARKETS", "DEFAULT_MARKETS", "ODDS_API_MARKET_KEYS"]
