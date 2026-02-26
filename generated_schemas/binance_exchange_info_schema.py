from typing import Any

from pydantic import BaseModel


class BinanceExchangeinfo(BaseModel):
    """Binance exchange_info response."""

    timezone: str | None = None
    serverTime: int  # timestamp | None = None
    rateLimits: list[Any] | None = None
    exchangeFilters: list[Any] | None = None
    symbols: list[Any] | None = None

