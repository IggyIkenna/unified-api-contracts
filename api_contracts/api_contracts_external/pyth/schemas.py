"""Pydantic schemas for Pyth Network WebSocket price feeds.

Ref: https://docs.pyth.network/price-feeds/core/publish-data/pyth-client-websocket-api
100+ assets across DeFi/TradFi/CeFi. JSON-RPC 2.0 over WebSocket.
"""

from pydantic import BaseModel, Field

from api_contracts.shared import ErrorAction


class PythPriceFeed(BaseModel):
    """Price feed from Pyth WS: id, price, conf, expo, publish_time, ema_price.

    actual_price = price * 10^expo; same for conf.
    """

    id: str | None = None  # feed/price account ID
    price: int | None = None  # mantissa (fixed-point)
    conf: int | None = None  # confidence/uncertainty
    expo: int | None = None  # exponent: actual = mantissa * 10^expo
    publish_time: int | None = Field(None, alias="publishTime")  # microseconds
    ema_price: int | None = Field(None, alias="emaPrice")  # exponential moving average
    ema_confidence: int | None = Field(None, alias="emaConfidence")
    status: str | None = None  # trading | unknown

    model_config = {"populate_by_name": True}


class PythProductAttr(BaseModel):
    """Product metadata from get_product_list / get_product."""

    symbol: str | None = None
    asset_type: str | None = Field(None, alias="assetType")
    quote_currency: str | None = Field(None, alias="quoteCurrency")
    description: str | None = None
    tenor: str | None = None

    model_config = {"populate_by_name": True}


class PythProduct(BaseModel):
    """Product from Pyth get_product / get_all_products."""

    account: str | None = None
    attr_dict: PythProductAttr | dict | None = Field(None, alias="attrDict")
    price_accounts: list[dict] | None = Field(None, alias="priceAccounts")

    model_config = {"populate_by_name": True}


class PythWsNotification(BaseModel):
    """WebSocket notification (e.g. notify_price_sched)."""

    jsonrpc: str = "2.0"
    method: str | None = None
    params: dict | None = None


class PythWsResponse(BaseModel):
    """JSON-RPC 2.0 response from Pyth WebSocket."""

    jsonrpc: str = "2.0"
    id: int | str | None = None
    result: dict | list | None = None
    error: dict | None = None


class PythError(BaseModel):
    """Pyth API/WebSocket error."""

    code: int | None = None
    message: str | None = None

    @classmethod
    def classify(cls, code: int | None = None) -> ErrorAction:
        """Map Pyth error to retry action."""
        if code in (-32603, -32602):  # Internal error, Invalid params
            return ErrorAction.RETRY_WITH_BACKOFF
        if code == -32600:  # Invalid request
            return ErrorAction.FAIL_HARD
        return ErrorAction.FAIL_HARD
