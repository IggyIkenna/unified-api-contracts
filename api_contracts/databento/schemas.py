"""Pydantic schemas for Databento API responses. Full surface: historical, symbology, metadata."""

from pydantic import BaseModel, Field

from api_contracts.shared import ErrorAction


class DatabentoOhlcvBar(BaseModel):
    """OHLCV bar (1m or 1s). Prices/volumes as raw int; divide price by 1e9 for float."""

    ts_event: int = Field(..., description="Bar close timestamp in nanoseconds since epoch (UTC)")
    rtype: int = Field(..., description="Record type (32=OHLCV-1M, 17=OHLCV-1S)")
    publisher_id: int = Field(..., description="Publisher/venue ID")
    instrument_id: int = Field(..., description="Databento internal instrument ID")
    open: int = Field(..., description="Opening price (fixed-point, divide by 1e9)")
    high: int = Field(..., description="High price (fixed-point)")
    low: int = Field(..., description="Low price (fixed-point)")
    close: int = Field(..., description="Closing price (fixed-point)")
    volume: int = Field(..., description="Total volume")


class DatabentoTrade(BaseModel):
    """Single trade record."""

    ts_event: int = Field(..., description="Trade timestamp in nanoseconds since epoch (UTC)")
    rtype: int = Field(..., description="Record type identifier")
    publisher_id: int = Field(..., description="Publisher/venue ID")
    instrument_id: int = Field(..., description="Databento internal instrument ID")
    action: str = Field(..., description="Trade action (e.g. T=trade)")
    side: str = Field(..., description="Aggressor side (A=ask/sell, B=bid/buy)")
    price: int = Field(..., description="Trade price (fixed-point, divide by 1e9)")
    size: int = Field(..., description="Trade size/quantity")
    sequence: int | None = Field(None, description="Exchange sequence number")


class DatabentoMbp1(BaseModel):
    """Market by price (best bid/ask)."""

    ts_event: int = Field(..., description="Quote timestamp in nanoseconds")
    rtype: int = Field(..., description="Record type identifier")
    publisher_id: int = Field(..., description="Publisher/venue ID")
    instrument_id: int = Field(..., description="Databento internal instrument ID")
    bid_px_00: int = Field(..., description="Best bid price (fixed-point)")
    ask_px_00: int = Field(..., description="Best ask price (fixed-point)")
    bid_sz_00: int = Field(..., description="Best bid size")
    ask_sz_00: int = Field(..., description="Best ask size")
    bid_ct_00: int | None = Field(None, description="Bid order count")
    ask_ct_00: int | None = Field(None, description="Ask order count")


class DatabentoDefinition(BaseModel):
    """Instrument definition."""

    ts_recv: int = Field(..., description="Definition receive timestamp in nanoseconds")
    publisher_id: int = Field(..., description="Publisher/venue ID")
    instrument_id: int = Field(..., description="Databento internal instrument ID")
    raw_symbol: str = Field(..., description="Raw exchange symbol")
    security_update_action: str = Field(..., description="A=add, M=modify, D=delete")
    instrument_class: str = Field(..., description="F=future, O=option, S=stock, etc.")
    min_lot_size_round_lot: int | None = None
    strike_price: int | None = None
    underlying: str | None = None
    expiration: int | None = None
    currency: str | None = None
    unit_of_measure: str | None = None
    unit_of_measure_qty: int | None = None
    min_price_increment: int | None = None


class DatabentoSymbol(BaseModel):
    """Symbol/metadata from Databento symbology or metadata API."""

    raw_symbol: str = Field(..., description="Raw exchange symbol")
    instrument_id: int | None = Field(None, description="Databento instrument ID")
    instrument_class: str | None = None
    description: str | None = None


# Price divisor for fixed-point conversion (1e9)
DATABENTO_PRICE_DIVISOR = 1_000_000_000


class DatabentoError(BaseModel):
    """Databento API error.

    Error hierarchy:
    - BentoError (base)
    - BentoHttpError (4xx/5xx HTTP)
    - BentoClientError (client validation, 4xx)
    - BentoServerError (server errors, 5xx)
    """

    error_type: str  # BentoHttpError, BentoClientError, BentoServerError
    status_code: int | None = None
    message: str | None = None

    @classmethod
    def classify(cls, error_type: str, status_code: int | None = None) -> ErrorAction:
        """Map Databento error type to retry action.

        Ref: https://databento.com/docs/api-reference-live/errors
        """
        if error_type == "BentoServerError":
            return ErrorAction.RETRY_WITH_BACKOFF
        if status_code is not None and status_code >= 500:
            return ErrorAction.RETRY_WITH_BACKOFF
        return ErrorAction.FAIL_HARD  # BentoClientError = fix the request
