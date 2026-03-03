"""OddsJam API source schemas — real-time odds and arb detection.

OddsJam provides real-time odds via REST/WebSocket API with built-in
arb/value detection. These schemas model the raw API responses before
normalisation to CanonicalOdds.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Self

from pydantic import BaseModel, ConfigDict

_RawDict = dict[str, str | int | float | bool | None]


class OddsJamOdds(BaseModel):
    """A single odds entry from an OddsJam market response."""

    model_config = ConfigDict(frozen=True)

    sportsbook: str
    odds: Decimal
    is_main: bool = True
    last_updated: datetime | None = None

    @classmethod
    def from_raw(cls, data: _RawDict) -> Self:
        """Construct from raw API response."""
        return cls.model_validate(data)


class OddsJamMarket(BaseModel):
    """A market from an OddsJam game response."""

    model_config = ConfigDict(frozen=True)

    market_name: str  # "moneyline", "spread", "total", "btts"
    bet_name: str  # "home", "away", "draw", "over", "under"
    line: Decimal | None = None
    odds_list: list[OddsJamOdds]

    @classmethod
    def from_raw(cls, data: _RawDict) -> Self:
        """Construct from raw API response."""
        return cls.model_validate(data)


class OddsJamGame(BaseModel):
    """Full game response from OddsJam with odds across sportsbooks."""

    model_config = ConfigDict(frozen=True)

    game_id: str
    sport: str
    league: str
    home_team: str
    away_team: str
    start_date: datetime
    is_live: bool = False
    markets: list[OddsJamMarket]

    @classmethod
    def from_raw(cls, data: _RawDict) -> Self:
        """Construct from raw API response."""
        return cls.model_validate(data)
