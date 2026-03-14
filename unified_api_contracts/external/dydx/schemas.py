"""dYdX v4 REST/WebSocket API schemas.

dYdX v4 is a fully on-chain perpetuals DEX (Cosmos L1 + Ethereum bridging).
REST base: https://indexer.dydx.trade/v4/
WS: wss://indexer.dydx.trade/v4/ws
"""

from __future__ import annotations

__api_version__ = "v4"  # matches provider_api_versions.yaml


from pydantic import BaseModel


class DydxTrade(BaseModel):
    """dYdX v4 public trade (REST: GET /v4/trades/perpetualMarket/{ticker}, WS: v4_trades).

    side: BUY or SELL.
    type: LIMIT, MARKET, STOP_LIMIT, TAKE_PROFIT, STOP_MARKET, TAKE_PROFIT_MARKET.
    """

    id: str | None = None
    side: str | None = None  # BUY, SELL
    size: str | None = None
    price: str | None = None
    type: str | None = None  # LIMIT, MARKET, etc.
    createdAt: str | None = None  # ISO 8601
    createdAtHeight: str | None = None


class DydxOrderBook(BaseModel):
    """dYdX v4 order book (REST: GET /v4/orderbooks/perpetualMarket/{ticker}, WS: v4_orderbook).

    bids/asks: [[price, size], ...] strings.
    """

    bids: list[list[str]] = []
    asks: list[list[str]] = []


class DydxOrder(BaseModel):
    """dYdX v4 private order (REST: GET /v4/orders/{orderId}, WS: v4_orders channel).

    status: OPEN, FILLED, CANCELED, BEST_EFFORT_OPENED, BEST_EFFORT_CANCELED, UNTRIGGERED.
    type: LIMIT, MARKET, STOP_LIMIT, TAKE_PROFIT, STOP_MARKET, TAKE_PROFIT_MARKET.
    side: BUY or SELL.
    timeInForce: GTT, FOK, IOC, UNSPECIFIED.
    """

    id: str | None = None
    clientId: str | None = None
    market: str | None = None
    side: str | None = None  # BUY, SELL
    price: str | None = None
    remainingSize: str | None = None
    size: str | None = None
    totalFilled: str | None = None
    reducedQuantums: str | None = None
    createdAt: str | None = None  # ISO 8601
    unfillableAt: str | None = None
    expiresAt: str | None = None
    type: str | None = None
    status: str | None = None  # OPEN, FILLED, CANCELED, etc.
    timeInForce: str | None = None  # GTT, FOK, IOC
    postOnly: bool | None = None
    reduceOnly: bool | None = None
    goodTilBlock: int | None = None
    goodTilBlockTime: str | None = None
    clientMetadata: str | None = None
    triggerPrice: str | None = None
    subaccountNumber: int | None = None


class DydxFill(BaseModel):
    """dYdX v4 private fill (REST: GET /v4/fills, WS: v4_fills channel).

    side: BUY or SELL.
    liquidity: TAKER or MAKER.
    type: LIMIT, LIQUIDATED, LIQUIDATION, DELEVERAGED, OFFSETTING, etc.
    """

    id: str | None = None
    side: str | None = None  # BUY, SELL
    liquidity: str | None = None  # TAKER, MAKER
    type: str | None = None
    market: str | None = None
    orderId: str | None = None
    price: str | None = None
    size: str | None = None
    createdAt: str | None = None  # ISO 8601
    createdAtHeight: str | None = None
    subaccountNumber: int | None = None
    clientMetadata: str | None = None
    fee: str | None = None


class DydxPerpetualMarket(BaseModel):
    """dYdX v4 perpetual market metadata (REST: GET /v4/perpetualMarkets)."""

    market: str | None = None  # ticker e.g. BTC-USD
    status: str | None = None
    baseAsset: str | None = None
    quoteAsset: str | None = None
    stepSize: str | None = None
    tickSize: str | None = None
    indexPrice: str | None = None
    oraclePrice: str | None = None
    priceChange24H: str | None = None
    volume24H: str | None = None
    trades24H: int | None = None
    nextFundingRate: str | None = None
    nextFundingAt: str | None = None
    minOrderSize: str | None = None
    type: str | None = None  # PERPETUAL
    initialMarginFraction: str | None = None
    maintenanceMarginFraction: str | None = None
    openInterest: str | None = None


__all__ = [
    "DydxFill",
    "DydxOrder",
    "DydxOrderBook",
    "DydxPerpetualMarket",
    "DydxTrade",
]
