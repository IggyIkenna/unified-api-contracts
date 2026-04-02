"""Sports-specific risk and exposure types.

SportsBetPosition and SportsExposure define the risk schemas for sports
betting positions. Consumed by risk-and-exposure-service and pnl-attribution-service.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field


class BetSide(StrEnum):
    """Side of a sports bet."""

    BACK = "back"
    LAY = "lay"


class SportsBetPosition(BaseModel):
    """A single sports bet position for risk tracking."""

    bet_id: str
    venue_key: str
    fixture_id: str
    market_type: str
    selection: str
    side: BetSide
    stake: Decimal
    odds: Decimal
    potential_profit: Decimal = Field(default=Decimal("0"))
    liability: Decimal = Field(default=Decimal("0"))
    status: str = "open"


class SportsExposure(BaseModel):
    """Aggregate sports exposure summary."""

    total_backed_stake: Decimal = Field(default=Decimal("0"))
    total_laid_stake: Decimal = Field(default=Decimal("0"))
    net_exposure: Decimal = Field(default=Decimal("0"))
    max_loss: Decimal = Field(default=Decimal("0"))
    max_profit: Decimal = Field(default=Decimal("0"))


class SportsBetPnL(BaseModel):
    """PnL attribution for a settled sports bet."""

    bet_id: str
    venue_key: str
    fixture_id: str
    market_type: str
    selection: str
    side: str
    stake: Decimal
    odds_at_placement: Decimal
    closing_odds: Decimal | None = None
    closing_line_source: str = "pinnacle"
    settlement_status: str | None = None
    payout: Decimal = Field(default=Decimal("0"))
    profit_loss: Decimal = Field(default=Decimal("0"))
    clv_edge_pct: Decimal | None = None
    strategy_id: str | None = None
    model_version: str | None = None
    placed_at: datetime | None = None
    settled_at: datetime | None = None


__all__ = [
    "BetSide",
    "SportsBetPnL",
    "SportsBetPosition",
    "SportsExposure",
]
