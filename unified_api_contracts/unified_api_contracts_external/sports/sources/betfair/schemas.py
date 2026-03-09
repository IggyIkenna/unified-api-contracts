"""Betfair Exchange source schemas — markets, runners, prices, orders."""

from __future__ import annotations

__api_version__ = "2.1"  # matches provider_api_versions.yaml

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict


class BetfairMarketStatus(StrEnum):
    """Betfair market lifecycle status."""

    INACTIVE = "INACTIVE"
    OPEN = "OPEN"
    SUSPENDED = "SUSPENDED"
    CLOSED = "CLOSED"


class BetfairPrice(BaseModel):
    """A single price/size entry in the Betfair order book."""

    model_config = ConfigDict(frozen=True)

    price: Decimal
    size: Decimal

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        """Construct from raw API response."""
        return cls.model_validate(data)


class BetfairRunner(BaseModel):
    """A runner (selection) within a Betfair market."""

    model_config = ConfigDict(frozen=True)

    selection_id: int
    runner_name: str
    handicap: Decimal | None = None
    status: str | None = None
    last_price_traded: Decimal | None = None
    total_matched: Decimal | None = None
    back_prices: list[BetfairPrice] = []
    lay_prices: list[BetfairPrice] = []

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        """Construct from raw API response."""
        return cls.model_validate(data)


class BetfairMarket(BaseModel):
    """A Betfair Exchange market."""

    model_config = ConfigDict(frozen=True)

    market_id: str
    market_name: str
    event_id: str | None = None
    event_name: str | None = None
    competition_id: str | None = None
    market_start_time: datetime | None = None
    status: BetfairMarketStatus | None = None
    total_matched: Decimal | None = None
    runners: list[BetfairRunner] = []

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        """Construct from raw API response."""
        return cls.model_validate(data)


class BetfairOrder(BaseModel):
    """A Betfair Exchange bet/order."""

    model_config = ConfigDict(frozen=True)

    bet_id: str
    market_id: str
    selection_id: int
    side: str
    price: Decimal
    size: Decimal
    size_matched: Decimal | None = None
    size_remaining: Decimal | None = None
    status: str
    placed_date: datetime | None = None

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        """Construct from raw API response."""
        return cls.model_validate(data)


class BetfairExchangeOdds(BaseModel):
    """Betfair Exchange best-available odds for a runner."""

    model_config = ConfigDict(frozen=True)

    market_id: str
    selection_id: int
    runner_name: str
    best_back_price: Decimal | None = None
    best_back_size: Decimal | None = None
    best_lay_price: Decimal | None = None
    best_lay_size: Decimal | None = None
    last_traded_price: Decimal | None = None
    total_matched: Decimal | None = None
    timestamp_utc: datetime

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        """Construct from raw API response."""
        return cls.model_validate(data)
