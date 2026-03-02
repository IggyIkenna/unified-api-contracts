
from pydantic import BaseModel


class BinanceExchangeinfo(BaseModel):
    """Binance exchange_info response."""

    timezone: str | None = None
    serverTime: int  # timestamp | None = None
    rateLimits: list[object] | None = None
    exchangeFilters: list[object] | None = None
    symbols: list[object] | None = None

