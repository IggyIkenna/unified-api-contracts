"""Understat source schemas — public API surface."""

from unified_api_contracts.external.understat.schemas import (
    UnderstatMatch,
    UnderstatPlayerSeason,
    UnderstatShot,
    UnderstatTeamHistory,
    UnderstatXGData,
    USMatchRaw,
    USMatchRosterRaw,
    USMatchShotRaw,
    USPlayerMatchRaw,
    USPlayerRaw,
    USPlayerSeasonRaw,
    USPlayerShotRaw,
    USTeamHistoryRaw,
    USTeamRaw,
)

__all__ = [
    # Raw US* schemas (originally in sports-betting-services-previous)
    "USMatchRaw",
    "USMatchRosterRaw",
    "USMatchShotRaw",
    "USPlayerMatchRaw",
    "USPlayerRaw",
    "USPlayerSeasonRaw",
    "USPlayerShotRaw",
    "USTeamHistoryRaw",
    "USTeamRaw",
    # Normalised Understat schemas
    "UnderstatMatch",
    "UnderstatPlayerSeason",
    "UnderstatShot",
    "UnderstatTeamHistory",
    "UnderstatXGData",
]
