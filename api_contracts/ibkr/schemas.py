"""Pydantic schemas for TWS/ib_insync. Full surface: market data, order, position, account, errors, callbacks."""

from decimal import Decimal
from typing import Any

from pydantic import BaseModel


# --- Market data (bars, ticker, order book) ---
class IBKRBar(BaseModel):
    """Historical bar from reqHistoricalData / reqBarChartData."""

    date: str | None = None
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float | None = None
    volume: float | None = None
    barCount: int | None = None
    average: float | None = None


class IBKRTicker(BaseModel):
    """Live ticker (bid, ask, last, etc.)."""

    bid: float | None = None
    ask: float | None = None
    last: float | None = None
    bidSize: float | None = None
    askSize: float | None = None
    lastSize: float | None = None
    volume: float | None = None
    high: float | None = None
    low: float | None = None
    open: float | None = None
    close: float | None = None


# --- Order ---
class IBKROrder(BaseModel):
    """Order submission / status. Align with ib_insync order attributes."""

    orderId: int | None = None
    clientId: int | None = None
    permId: int | None = None
    action: str | None = None  # BUY, SELL
    orderType: str | None = None  # MKT, LMT, etc.
    totalQuantity: float | None = None
    lmtPrice: float | None = None
    auxPrice: float | None = None
    status: str | None = None  # PendingSubmit, Submitted, Filled, Cancelled, etc.
    filledQuantity: float | None = None
    avgFillPrice: float | None = None
    info: dict[str, Any] | None = None


# --- Position ---
class IBKRPosition(BaseModel):
    """Position from reqPositions / position update."""

    account: str | None = None
    contract: dict | None = None  # conId, symbol, secType, exchange, etc.
    position: float | None = None
    avgCost: float | None = None
    marketPrice: float | None = None
    marketValue: float | None = None
    unrealizedPNL: float | None = None
    realizedPNL: float | None = None
    info: dict[str, Any] | None = None


# --- Account summary / balance ---
class IBKRAccountValue(BaseModel):
    """Single account value (NetLiquidation, TotalCashValue, etc.)."""

    tag: str | None = None
    value: str | None = None
    currency: str | None = None
    account: str | None = None


class IBKRPortfolioItem(BaseModel):
    """Portfolio item (holding)."""

    account: str | None = None
    contract: dict | None = None
    position: float | None = None
    marketPrice: float | None = None
    marketValue: float | None = None
    avgCost: float | None = None
    unrealizedPNL: float | None = None
    realizedPNL: float | None = None


# --- PnL ---
class IBKRPnL(BaseModel):
    """Daily PnL (reqPnL)."""

    dailyPnL: float | None = None
    unrealizedPnL: float | None = None


# --- Error / status ---
class IBKRError(BaseModel):
    """TWS error message."""

    reqId: int | None = None
    errorCode: int | None = None
    errorString: str | None = None
    advancedOrderRejectJson: str | None = None


class IBKRContractDetails(BaseModel):
    """IBKR contract details (TWS API: reqContractDetails).

    Note: IBKR uses TWS API (not REST). These schemas represent the
    normalized response for reference data purposes.
    """

    conid: int | None = None  # contract ID
    symbol: str | None = None
    secType: str | None = None  # STK, OPT, FUT, CASH, CFD
    lastTradeDateOrContractMonth: str | None = None
    strike: Decimal | float | None = None
    right: str | None = None  # C=call, P=put
    multiplier: str | None = None  # contract multiplier
    exchange: str | None = None
    currency: str | None = None
    localSymbol: str | None = None
    tradingClass: str | None = None
    minTick: Decimal | float | None = None
    longName: str | None = None
    industry: str | None = None
    category: str | None = None
    subcategory: str | None = None
    timeZoneId: str | None = None
    underConid: int | None = None  # underlying contract id
    evRule: str | None = None


class IBKRCorporateAction(BaseModel):
    """IBKR corporate action event (from IBKR statement/flex query)."""

    conid: int | None = None
    symbol: str
    description: str | None = None
    reportDate: str | None = None  # YYYY-MM-DD
    currency: str | None = None
    type: str | None = None  # Dividends, Splits, Mergers, BonusRights
    amount: Decimal | None = None
    actionDescription: str | None = None
