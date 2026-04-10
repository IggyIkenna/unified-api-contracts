"""Balance snapshot schemas for client reporting.

Covers hourly balance snapshots (for equity curve data) and
daily balance summaries (for daily P&L reports and CSV exports).
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import AwareDatetime, BaseModel, Field

from .nav_snapshot import AssetBalanceSummary


class SnapshotSource(BaseModel, frozen=True):
    """Source metadata for a balance snapshot."""

    source_type: str = Field(
        default="API_LIVE",
        description="How this snapshot was obtained: API_LIVE, MANUAL, HISTORICAL_BACKFILL",
    )
    venue: str = Field(description="Exchange venue (e.g. 'binance', 'okx')")
    account_type: str = Field(
        default="spot",
        description="Account type: spot, futures, margin, unified",
    )


class PositionSnapshot(BaseModel, frozen=True):
    """Single open position at snapshot time."""

    symbol: str = Field(description="Trading pair (e.g. 'BTC-USDT')")
    side: str = Field(description="Position side: 'long' or 'short'")
    quantity: Decimal = Field(description="Position size in base currency")
    entry_price: Decimal = Field(description="Average entry price")
    mark_price: Decimal = Field(description="Current mark/market price")
    unrealized_pnl: Decimal = Field(description="Unrealized P&L in USD")
    leverage: Decimal = Field(default=Decimal("1"), description="Leverage multiplier")
    liquidation_price: Decimal | None = Field(default=None, description="Estimated liquidation price")
    notional_usd: Decimal = Field(default=Decimal("0"), description="Notional value in USD")
    margin_used: Decimal = Field(default=Decimal("0"), description="Margin/collateral used in USD")


class HourlyBalanceSnapshot(BaseModel, frozen=True):
    """Hourly balance snapshot for a client account.

    Collected every hour by the snapshot collector job.
    Stored in GCS Parquet and optionally Firestore for real-time queries.
    """

    client_id: str = Field(description="Client identifier")
    timestamp: AwareDatetime = Field(description="Snapshot timestamp (UTC)")
    total_equity_usd: Decimal = Field(description="Total account equity in USD")
    free_balance_usd: Decimal = Field(description="Available balance in USD")
    locked_balance_usd: Decimal = Field(
        default=Decimal("0"),
        description="Balance locked in orders/collateral in USD",
    )
    unrealized_pnl_usd: Decimal = Field(
        default=Decimal("0"),
        description="Total unrealized P&L across all positions in USD",
    )
    margin_used_usd: Decimal = Field(
        default=Decimal("0"),
        description="Total margin/collateral in use in USD",
    )
    asset_balances: list[AssetBalanceSummary] = Field(
        default_factory=list,
        description="Per-asset balance breakdown",
    )
    positions: list[PositionSnapshot] = Field(
        default_factory=list,
        description="Open positions at snapshot time",
    )
    source: SnapshotSource = Field(description="How this snapshot was obtained")


class DailyBalanceSummary(BaseModel, frozen=True):
    """Daily balance summary aggregating hourly snapshots.

    Computed from hourly snapshots for a given calendar day.
    Used for daily P&L CSV exports and performance charts.
    """

    client_id: str = Field(description="Client identifier")
    date: str = Field(description="Calendar date (YYYY-MM-DD)")
    opening_equity: Decimal = Field(description="Equity at first snapshot of the day")
    closing_equity: Decimal = Field(description="Equity at last snapshot of the day")
    high_equity: Decimal = Field(description="Highest equity during the day")
    low_equity: Decimal = Field(description="Lowest equity during the day")
    daily_return_pct: Decimal = Field(description="Daily return as decimal ((close - open) / open)")
    daily_pnl_usd: Decimal = Field(description="Daily P&L in USD (close - open - net_transfers)")
    net_deposits: Decimal = Field(
        default=Decimal("0"),
        description="Net deposits during the day (deposits - withdrawals)",
    )
    net_withdrawals: Decimal = Field(
        default=Decimal("0"),
        description="Net withdrawals during the day",
    )
    realized_pnl: Decimal = Field(
        default=Decimal("0"),
        description="Realized P&L from closed trades during the day",
    )
    unrealized_pnl_change: Decimal = Field(
        default=Decimal("0"),
        description="Change in unrealized P&L during the day",
    )
    trade_count: int = Field(default=0, description="Number of trades during the day")
    total_volume_usd: Decimal = Field(
        default=Decimal("0"),
        description="Total traded volume in USD during the day",
    )
    total_fees_usd: Decimal = Field(
        default=Decimal("0"),
        description="Total fees paid in USD during the day",
    )
    venue: str = Field(default="", description="Venue (empty = aggregated across venues)")
