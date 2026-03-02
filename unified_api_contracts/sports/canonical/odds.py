"""Canonical odds schemas — market types, bookmaker odds, implied probabilities."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict

from unified_api_contracts.sports.canonical.bookmaker import BookmakerInfo


class OddsType(StrEnum):
    """Supported betting market types."""

    H2H = "h2h"
    OVER_UNDER = "over_under"
    ASIAN_HANDICAP = "asian_handicap"
    BOTH_TEAMS_SCORE = "both_teams_score"
    CORRECT_SCORE = "correct_score"
    OUTRIGHT = "outright"


class OutcomeType(StrEnum):
    """Possible bet outcomes."""

    HOME = "home"
    DRAW = "draw"
    AWAY = "away"
    OVER = "over"
    UNDER = "under"
    YES = "yes"
    NO = "no"


class MarketStatus(StrEnum):
    """Status of an odds market."""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    CLOSED = "closed"
    SETTLED = "settled"


class CanonicalBookmakerMarket(BaseModel):
    """Single bookmaker's offering for a specific market."""

    model_config = ConfigDict(frozen=True)

    bookmaker_key: str
    market: OddsType
    outcomes: dict[str, Decimal]
    margin: Decimal | None = None
    last_updated_utc: datetime | None = None

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        """Construct from a flat dictionary."""
        return cls.model_validate(data)


class CanonicalOdds(BaseModel):
    """Normalised odds for a fixture from a single bookmaker."""

    model_config = ConfigDict(frozen=True)

    fixture_id: str
    bookmaker_key: str
    bookmaker: BookmakerInfo | None = None
    market: OddsType
    home_odds: Decimal | None = None
    draw_odds: Decimal | None = None
    away_odds: Decimal | None = None
    over_line: Decimal | None = None
    over_odds: Decimal | None = None
    under_odds: Decimal | None = None
    handicap_line: Decimal | None = None
    handicap_home_odds: Decimal | None = None
    handicap_away_odds: Decimal | None = None
    implied_home_prob: Decimal | None = None
    implied_draw_prob: Decimal | None = None
    implied_away_prob: Decimal | None = None
    margin: Decimal | None = None
    timestamp_utc: datetime
    source: str

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        """Construct from a flat dictionary."""
        return cls.model_validate(data)
