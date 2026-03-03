"""Cross-provider mapping schemas for teams, fixtures, and players."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class TeamMapping(BaseModel):
    """Maps a team identity across all data providers."""

    model_config = ConfigDict(frozen=True)

    canonical_team_id: str
    display_name: str
    api_football_id: int | None = None
    footystats_id: str | None = None
    understat_name: str | None = None
    soccer_football_id: int | None = None
    betfair_id: str | None = None
    pinnacle_id: int | None = None
    odds_api_key: str | None = None
    aliases: frozenset[str] = frozenset()


class FixtureMapping(BaseModel):
    """Maps a fixture identity across all data providers."""

    model_config = ConfigDict(frozen=True)

    canonical_fixture_id: str
    api_football_fixture_id: int | None = None
    footystats_match_id: str | None = None
    understat_match_id: int | None = None
    date: str
    home_team_id: str
    away_team_id: str


class PlayerMapping(BaseModel):
    """Maps a player identity across all data providers."""

    model_config = ConfigDict(frozen=True)

    canonical_player_id: str
    display_name: str
    api_football_player_id: int | None = None
    footystats_player_id: str | None = None
    understat_player_id: int | None = None
    soccer_football_player_id: int | None = None
