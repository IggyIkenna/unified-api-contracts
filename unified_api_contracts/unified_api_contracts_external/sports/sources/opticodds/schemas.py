"""OpticOdds API source schemas — real-time odds streaming.

OpticOdds provides low-latency odds streaming via WebSocket and REST API.
These schemas model the raw API responses before normalisation to CanonicalOdds.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Self

from pydantic import BaseModel, ConfigDict

_RawDict = dict[str, str | int | float | bool | None]


class OpticOddsMarket(BaseModel):
    """A single market from an OpticOdds sportsbook response."""

    model_config = ConfigDict(frozen=True)

    market_id: str
    market_type: str  # "moneyline", "spread", "total", "btts"
    home_odds: Decimal | None = None
    draw_odds: Decimal | None = None
    away_odds: Decimal | None = None
    over_odds: Decimal | None = None
    under_odds: Decimal | None = None
    line: Decimal | None = None
    is_live: bool = False
    last_updated: datetime | None = None

    @classmethod
    def from_raw(cls, data: _RawDict) -> Self:
        """Construct from raw API response."""
        return cls.model_validate(data)


class OpticOddsSportsbook(BaseModel):
    """A sportsbook entry from an OpticOdds fixture response."""

    model_config = ConfigDict(frozen=True)

    sportsbook_id: str
    sportsbook_name: str
    markets: list[OpticOddsMarket]

    @classmethod
    def from_raw(cls, data: _RawDict) -> Self:
        """Construct from raw API response."""
        return cls.model_validate(data)


class OpticOddsFixture(BaseModel):
    """Full fixture response from OpticOdds with odds from multiple sportsbooks."""

    model_config = ConfigDict(frozen=True)

    fixture_id: str
    sport: str
    league: str
    home_team: str
    away_team: str
    start_time: datetime
    is_live: bool = False
    sportsbooks: list[OpticOddsSportsbook]

    @classmethod
    def from_raw(cls, data: _RawDict) -> Self:
        """Construct from raw API response."""
        return cls.model_validate(data)
