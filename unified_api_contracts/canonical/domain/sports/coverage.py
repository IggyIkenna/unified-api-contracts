"""Sports odds bookmaker × market coverage enumeration.

Provides LeagueTier, BookmakerKey and EXPECTED_BOOKMAKER_MARKET_SETS for the
NaN-fill step in the instruments-service sports orchestrator.  Markets are
empirical baselines derived from a 2-week FootyStats sample (2026-06).
"""
from __future__ import annotations

from enum import StrEnum

from .odds import OddsType


class LeagueTier(StrEnum):
    TIER_1_DOMESTIC = "tier_1_domestic"
    TIER_2_DOMESTIC = "tier_2_domestic"
    TIER_1_INTERNATIONAL = "tier_1_international"
    TIER_2_INTERNATIONAL = "tier_2_international"
    OTHER = "other"


BookmakerKey = str

# fmt: off
EXPECTED_BOOKMAKER_MARKET_SETS: dict[LeagueTier, dict[BookmakerKey, list[OddsType]]] = {
    LeagueTier.TIER_1_DOMESTIC: {
        "footystats": [
            OddsType.H2H,
            OddsType.OVER_UNDER,
            OddsType.BOTH_TEAMS_SCORE,
            OddsType.HALF_TIME_RESULT,
            OddsType.FIRST_HALF_OVER_UNDER,
            OddsType.CORNERS,
            OddsType.DOUBLE_CHANCE,
            OddsType.DRAW_NO_BET,
        ],
    },
    LeagueTier.TIER_2_DOMESTIC: {
        "footystats": [
            OddsType.H2H,
            OddsType.OVER_UNDER,
            OddsType.BOTH_TEAMS_SCORE,
        ],
    },
    LeagueTier.TIER_1_INTERNATIONAL: {
        "footystats": [
            OddsType.H2H,
            OddsType.OVER_UNDER,
            OddsType.BOTH_TEAMS_SCORE,
            OddsType.HALF_TIME_RESULT,
            OddsType.FIRST_HALF_OVER_UNDER,
            OddsType.DOUBLE_CHANCE,
        ],
    },
    LeagueTier.TIER_2_INTERNATIONAL: {
        "footystats": [
            OddsType.H2H,
            OddsType.OVER_UNDER,
        ],
    },
    LeagueTier.OTHER: {
        "footystats": [
            OddsType.H2H,
        ],
    },
}
# fmt: on

# Countries where a league is classified as international rather than domestic.
_INTERNATIONAL_COUNTRIES: frozenset[str] = frozenset(
    {
        "",
        "WORLD",
        "EUROPE",
        "SOUTH AMERICA",
        "AFRICA",
        "ASIA",
        "NORTH AMERICA",
        "OCEANIA",
    }
)


def get_league_tier(tier_int: int, country: str | None = None) -> LeagueTier:
    """Map a LeagueDefinition tier integer + optional country to a LeagueTier.

    Args:
        tier_int: Integer tier from ``LeagueDefinition.tier`` (1 = top-flight).
        country: Country name from ``LeagueDefinition.country`` (None → treated
            as international).

    Returns:
        The corresponding ``LeagueTier`` value.
    """
    _is_intl = (country or "").upper().strip() in _INTERNATIONAL_COUNTRIES
    if tier_int == 1:
        return LeagueTier.TIER_1_INTERNATIONAL if _is_intl else LeagueTier.TIER_1_DOMESTIC
    if tier_int == 2:
        return LeagueTier.TIER_2_INTERNATIONAL if _is_intl else LeagueTier.TIER_2_DOMESTIC
    return LeagueTier.OTHER
