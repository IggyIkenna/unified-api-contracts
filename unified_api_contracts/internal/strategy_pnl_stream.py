"""Strategy PnL stream contract — emitted by strategy-service archetypes.

Consumed by trading-agent-service allocator. Off-by-default until post-cutover
production allocator logic ships.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class StrategyPnlStreamEvent(BaseModel):
    """Per-archetype PnL stream event emitted at each strategy tick.

    Emitted by carry_staked_basis and arbitrage_price_dispersion archetypes
    (May-23 scope). All other archetypes add emission post-cutover.
    """

    archetype_id: str = Field(description="Canonical archetype name, e.g. 'carry_staked_basis'")
    mode: Literal["live", "paper", "backtest_continuation"] = Field(description="Operational mode of the strategy run")
    pnl_realized: Decimal = Field(description="Cumulative realized PnL in reporting currency")
    pnl_unrealized: Decimal = Field(description="Current unrealized PnL in reporting currency")
    equity: Decimal = Field(description="Current equity value in reporting currency")
    n_trades: int = Field(description="Number of completed trades in the session")
    sharpe_window_n: Decimal | None = Field(
        default=None,
        description="Rolling Sharpe ratio over window N; None if window not yet filled",
    )
    drawdown_window_n: Decimal | None = Field(
        default=None,
        description="Rolling max drawdown over window N; None if window not yet filled",
    )
    timestamp: datetime = Field(description="UTC tz-aware timestamp of this PnL snapshot")
    available_at: datetime = Field(description="Write-time UTC timestamp per per-row available_at rule")
