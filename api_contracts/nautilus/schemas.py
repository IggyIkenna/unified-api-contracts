"""NautilusTrader-like Pydantic schemas for execution-services testing.

These schemas mirror NautilusTrader model types (Order, Position, Instrument, Fill, Account)
to enable testing without the full nautilus-trader dependency in api-contracts.

Reference: https://github.com/nautechsystems/nautilus_trader
Docs: https://nautilustrader.io/docs/latest/
"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


# --- Order ---
class Order(BaseModel):
    """Order schema mirroring NautilusTrader Order for testing."""

    order_id: str = Field(..., description="Unique order identifier")
    instrument_id: str = Field(..., description="Instrument ID (e.g., BTCUSDT-PERP.BINANCE)")
    side: str = Field(..., description="BUY or SELL")
    quantity: Decimal = Field(..., ge=0, description="Order quantity")
    price: Decimal | None = Field(None, description="Limit price (None for market orders)")
    status: str = Field(
        ...,
        description="PENDING, SUBMITTED, ACCEPTED, FILLED, CANCELLED, REJECTED, EXPIRED",
    )
    timestamp: datetime = Field(..., description="Order creation timestamp")
    client_order_id: str | None = Field(None, description="Client-assigned order ID")
    order_type: str = Field(default="MARKET", description="MARKET, LIMIT, STOP_MARKET, etc.")
    filled_qty: Decimal = Field(default=Decimal("0"), ge=0, description="Filled quantity")
    avg_px: Decimal | None = Field(None, description="Average fill price")
    venue_order_id: str | None = Field(None, description="Exchange-assigned order ID")
    account_id: str | None = Field(None, description="Account ID")
    strategy_id: str | None = Field(None, description="Strategy ID")


# --- Position ---
class Position(BaseModel):
    """Position schema mirroring NautilusTrader Position for testing."""

    position_id: str = Field(..., description="Unique position identifier")
    instrument_id: str = Field(..., description="Instrument ID")
    side: str = Field(..., description="LONG, SHORT, or FLAT")
    quantity: Decimal = Field(..., ge=0, description="Absolute position size")
    signed_qty: Decimal = Field(..., description="Signed quantity (+ for LONG, - for SHORT)")
    entry_price: Decimal = Field(..., ge=0, description="Average entry price")
    unrealized_pnl: Decimal = Field(default=Decimal("0"), description="Unrealized PnL")
    realized_pnl: Decimal = Field(default=Decimal("0"), description="Realized PnL")
    timestamp: datetime = Field(..., description="Position timestamp")
    account_id: str | None = Field(None, description="Account ID")
    strategy_id: str | None = Field(None, description="Strategy ID")
    venue: str | None = Field(None, description="Trading venue")
    is_open: bool = Field(default=True, description="Whether position is open")
    ts_opened_ns: int = Field(default=0, description="Open timestamp (nanoseconds)")
    ts_closed_ns: int = Field(default=0, description="Close timestamp (nanoseconds)")


# --- Instrument ---
class Instrument(BaseModel):
    """Instrument schema mirroring NautilusTrader Instrument for testing."""

    instrument_id: str = Field(..., description="Unique instrument ID (SYMBOL.VENUE)")
    symbol: str = Field(..., description="Ticker symbol")
    venue: str = Field(..., description="Trading venue")
    asset_class: str = Field(default="CRYPTO", description="CRYPTO, EQUITY, FX, FUTURES, etc.")
    tick_size: Decimal = Field(..., gt=0, description="Minimum price increment")
    lot_size: Decimal = Field(..., gt=0, description="Minimum quantity increment")
    price_precision: int = Field(default=8, ge=0, description="Price decimal precision")
    size_precision: int = Field(default=8, ge=0, description="Size decimal precision")
    base_currency: str | None = Field(None, description="Base currency (e.g., BTC)")
    quote_currency: str | None = Field(None, description="Quote currency (e.g., USDT)")
    is_inverse: bool = Field(default=False, description="Whether instrument is inverse")
    multiplier: Decimal = Field(default=Decimal("1"), description="Contract multiplier")


# --- Fill (OrderFilled / Trade) ---
class Fill(BaseModel):
    """Fill schema mirroring NautilusTrader OrderFilled/Trade for testing."""

    fill_id: str = Field(..., description="Unique fill/trade identifier")
    order_id: str = Field(..., description="Order ID this fill belongs to")
    instrument_id: str = Field(..., description="Instrument ID")
    quantity: Decimal = Field(..., gt=0, description="Fill quantity")
    price: Decimal = Field(..., ge=0, description="Fill price")
    timestamp: datetime = Field(..., description="Fill timestamp")
    side: str = Field(..., description="BUY or SELL")
    commission: Decimal = Field(default=Decimal("0"), ge=0, description="Commission amount")
    commission_currency: str | None = Field(None, description="Commission currency")
    venue_trade_id: str | None = Field(None, description="Exchange trade ID")
    position_id: str | None = Field(None, description="Position ID (for hedging OMS)")


# --- Account ---
class Account(BaseModel):
    """Account schema mirroring NautilusTrader Account for testing."""

    account_id: str = Field(..., description="Unique account identifier")
    balance: Decimal = Field(..., ge=0, description="Account balance")
    equity: Decimal = Field(..., ge=0, description="Account equity")
    margin: Decimal = Field(default=Decimal("0"), ge=0, description="Used margin")
    free_margin: Decimal = Field(default=Decimal("0"), ge=0, description="Free margin")
    currency: str = Field(default="USDT", description="Account currency")
    timestamp: datetime = Field(..., description="Account snapshot timestamp")
    venue: str | None = Field(None, description="Trading venue")
    is_margin_account: bool = Field(default=False, description="Whether margin is enabled")
