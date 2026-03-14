"""Soccer Football Info source schemas — public re-exports."""

from unified_api_contracts.external.soccer_football_info.schemas import (
    SFILeague,
    SFIMatch,
    SFIMatchDominance,
    SFIMatchProgressiveOdds,
    SFIMatchProgressiveStats,
    SFITeam,
    SFLeagueRaw,
    SFMatchDominanceRaw,
    SFMatchEventRaw,
    SFMatchProgressiveOddsRaw,
    SFMatchProgressiveStatsRaw,
    SFMatchRaw,
    SFTeamRaw,
)

__all__ = [
    # Clean normalised schemas
    "SFILeague",
    "SFIMatch",
    "SFIMatchDominance",
    "SFIMatchProgressiveOdds",
    "SFIMatchProgressiveStats",
    "SFITeam",
    # Raw source schemas (legacy SF* table mirrors)
    "SFLeagueRaw",
    "SFMatchDominanceRaw",
    "SFMatchEventRaw",
    "SFMatchProgressiveOddsRaw",
    "SFMatchProgressiveStatsRaw",
    "SFMatchRaw",
    "SFTeamRaw",
]
