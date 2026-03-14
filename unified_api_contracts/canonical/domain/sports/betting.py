"""Betting schemas — orders, executions, signals."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict

from .odds import OddsType


class BetStatus(StrEnum):
    """Lifecycle status of a bet."""

    PENDING = "pending"
    PLACED = "placed"
    PARTIALLY_MATCHED = "partially_matched"
    MATCHED = "matched"
    SETTLED_WIN = "settled_win"
    SETTLED_LOSS = "settled_loss"
    SETTLED_VOID = "settled_void"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class SignalSource(StrEnum):
    """Origin of a betting signal."""

    ARBITRAGE = "arbitrage"
    ML_MODEL = "ml_model"


class BettingSignal(BaseModel):
    """A signal recommending a bet, from ML model or arbitrage detector."""

    model_config = ConfigDict(frozen=True)

    signal_id: str
    fixture_id: str
    market: OddsType
    selection: str
    confidence: Decimal
    expected_value: Decimal
    source: SignalSource
    model_version: str | None = None
    created_at_utc: datetime

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        """Construct from a flat dictionary."""
        return cls.model_validate(data)


class BetOrder(BaseModel):
    """A bet order to be placed at a bookmaker or exchange."""

    model_config = ConfigDict(frozen=True)

    order_id: str
    fixture_id: str
    bookmaker_key: str
    market: OddsType
    selection: str
    requested_odds: Decimal
    stake: Decimal
    max_acceptable_odds: Decimal
    strategy_source: SignalSource
    signal_id: str | None = None
    opportunity_id: str | None = None
    created_at_utc: datetime

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        """Construct from a flat dictionary."""
        return cls.model_validate(data)


class BetExecution(BaseModel):
    """Result of a bet placement attempt."""

    model_config = ConfigDict(frozen=True)

    execution_id: str
    order_id: str
    bet_id: str | None = None
    status: BetStatus
    filled_odds: Decimal | None = None
    filled_stake: Decimal | None = None
    bookmaker_ref: str | None = None
    error_message: str | None = None
    executed_at_utc: datetime

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        """Construct from a flat dictionary."""
        return cls.model_validate(data)
