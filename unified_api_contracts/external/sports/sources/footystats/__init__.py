"""FootyStats source schemas — canonical and raw API response models."""

from unified_api_contracts.external.sports.sources.footystats.schemas import (
    FootyStatsBTTS,
    FootyStatsLeague,
    FootyStatsMatch,
    FootyStatsOdds,
    FootyStatsOverUnder,
    FootyStatsPlayer,
    FootyStatsReferee,
    FootyStatsTeam,
    FTLeagueStatsRaw,
    FTLineupEventRaw,
    FTLineupRaw,
    FTMatchRaw,
    FTOddsRaw,
    FTPlayerRaw,
    FTRefereeRaw,
    FTTeamRaw,
    FTWeatherRaw,
)

__all__ = [
    # Raw API response schemas
    "FTLeagueStatsRaw",
    "FTLineupEventRaw",
    "FTLineupRaw",
    "FTMatchRaw",
    "FTOddsRaw",
    "FTPlayerRaw",
    "FTRefereeRaw",
    "FTTeamRaw",
    "FTWeatherRaw",
    # Canonical schemas
    "FootyStatsBTTS",
    "FootyStatsLeague",
    "FootyStatsMatch",
    "FootyStatsOdds",
    "FootyStatsOverUnder",
    "FootyStatsPlayer",
    "FootyStatsReferee",
    "FootyStatsTeam",
]
