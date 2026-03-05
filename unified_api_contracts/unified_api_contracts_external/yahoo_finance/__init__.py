"""Yahoo Finance API contracts (TradFi market data adapter)."""

from pydantic import BaseModel


class YahooOptionContract(BaseModel):
    """Yahoo Finance options contract (yfinance Ticker.option_chain).

    Fields map directly to the DataFrame columns returned by
    ``Ticker.option_chain(date).calls`` / ``.puts``.
    """

    contractSymbol: str  # e.g. AAPL240621C00150000
    strike: float
    currency: str | None = None  # USD
    lastPrice: float | None = None
    change: float | None = None
    percentChange: float | None = None
    volume: float | None = None
    openInterest: float | None = None
    bid: float | None = None
    ask: float | None = None
    contractSize: str | None = None  # REGULAR
    expiration: int | None = None  # Unix ms
    lastTradeDate: int | None = None  # Unix ms
    impliedVolatility: float | None = None
    inTheMoney: bool | None = None
    option_type: str | None = None  # call or put (injected by caller)
    underlying: str | None = None  # underlying ticker (injected by caller)


class YahooOhlcv(BaseModel):
    """Yahoo Finance OHLCV bar (yfinance Ticker.history).

    Timestamp is the bar open time represented as Unix ms.
    ``Date`` is the pandas DatetimeIndex converted to Unix ms by the caller.
    """

    timestamp_ms: int  # Unix ms (converted from pandas Timestamp)
    symbol: str  # ticker e.g. AAPL
    Open: float
    High: float
    Low: float
    Close: float
    Volume: float
    Dividends: float | None = None
    Stock_Splits: float | None = None
