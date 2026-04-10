"""Trade history and coin breakdown schemas for client reporting.

Covers individual trade records, per-coin P&L aggregation,
and portfolio allocation snapshots.
"""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum

from pydantic import AwareDatetime, BaseModel, Field


class TradeType(StrEnum):
    """Classification of how a trade was executed."""

    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    LIQUIDATION = "LIQUIDATION"
    FUNDING = "FUNDING"
    TRANSFER = "TRANSFER"


class TradeSide(StrEnum):
    """Trade direction."""

    BUY = "BUY"
    SELL = "SELL"


class TradeRecord(BaseModel, frozen=True):
    """Single trade/fill record from an exchange.

    Represents one execution event. Multiple TradeRecords may share
    the same order_id when a single order is filled in parts.
    """

    trade_id: str = Field(description="Exchange-assigned trade ID")
    client_id: str = Field(description="Client identifier")
    venue: str = Field(description="Exchange venue (e.g. 'binance', 'okx')")
    symbol: str = Field(description="Trading pair (e.g. 'BTC-USDT')")
    side: TradeSide = Field(description="Trade direction")
    quantity: Decimal = Field(description="Filled quantity in base currency")
    price: Decimal = Field(description="Execution price in quote currency")
    fee: Decimal = Field(description="Fee charged by exchange")
    fee_currency: str = Field(description="Currency of the fee (e.g. 'USDT', 'BNB')")
    realized_pnl: Decimal = Field(
        default=Decimal("0"),
        description="Realized P&L from this trade (for closing trades)",
    )
    timestamp: AwareDatetime = Field(description="Execution timestamp (UTC)")
    order_id: str = Field(default="", description="Parent order ID")
    trade_type: TradeType = Field(default=TradeType.MARKET, description="How the trade was executed")
    notional_usd: Decimal = Field(
        default=Decimal("0"),
        description="Notional value in USD at time of execution",
    )


class TransferRecord(BaseModel, frozen=True):
    """Deposit or withdrawal record from an exchange.

    Used to detect balance changes that are NOT from trading
    (critical for accurate NAV and P&L calculations).
    """

    transfer_id: str = Field(description="Exchange-assigned transfer ID")
    client_id: str = Field(description="Client identifier")
    venue: str = Field(description="Exchange venue")
    direction: str = Field(description="'deposit' or 'withdrawal'")
    currency: str = Field(description="Asset transferred (e.g. 'USDT', 'BTC')")
    amount: Decimal = Field(description="Transfer amount")
    fee: Decimal = Field(default=Decimal("0"), description="Transfer fee")
    status: str = Field(description="Transfer status (e.g. 'ok', 'pending', 'canceled')")
    timestamp: AwareDatetime = Field(description="Transfer timestamp (UTC)")
    tx_hash: str = Field(default="", description="Blockchain transaction hash (if on-chain)")
    address: str = Field(default="", description="Destination/source address")
    network: str = Field(default="", description="Network used (e.g. 'ETH', 'TRC20')")


class CoinPnLBreakdown(BaseModel, frozen=True):
    """Per-coin P&L aggregation for portfolio breakdown.

    Groups all trades for a specific symbol and computes aggregate
    realized/unrealized P&L and allocation percentage.
    """

    symbol: str = Field(description="Asset symbol (e.g. 'BTC', 'ETH')")
    quantity: Decimal = Field(description="Current holding quantity")
    avg_entry_price: Decimal = Field(description="Volume-weighted average entry price")
    current_price: Decimal = Field(description="Current mark price in USD")
    cost_basis_usd: Decimal = Field(description="Total cost basis in USD")
    market_value_usd: Decimal = Field(description="Current market value in USD")
    realized_pnl: Decimal = Field(description="Total realized P&L in USD")
    unrealized_pnl: Decimal = Field(description="Current unrealized P&L in USD")
    total_pnl: Decimal = Field(description="realized + unrealized P&L in USD")
    allocation_pct: Decimal = Field(description="Percentage of total portfolio value")
    trade_count: int = Field(description="Number of trades for this coin")
    first_trade_at: AwareDatetime | None = Field(default=None, description="Timestamp of first trade")
    last_trade_at: AwareDatetime | None = Field(default=None, description="Timestamp of most recent trade")


class PortfolioAllocation(BaseModel, frozen=True):
    """Complete portfolio allocation snapshot.

    Aggregates per-coin breakdowns into a portfolio-level view
    with total equity and timestamp.
    """

    client_id: str = Field(description="Client identifier")
    total_equity_usd: Decimal = Field(description="Total portfolio equity in USD")
    allocations: list[CoinPnLBreakdown] = Field(
        default_factory=list,
        description="Per-coin breakdown sorted by allocation_pct descending",
    )
    snapshot_timestamp: AwareDatetime = Field(description="When this snapshot was taken")
    venue: str = Field(default="", description="Venue filter (empty = all venues)")
