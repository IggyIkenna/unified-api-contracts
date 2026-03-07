"""Pydantic schemas for Databento API responses. Full surface: historical, symbology, metadata."""

__api_version__ = "v0"  # matches provider_api_versions.yaml

from pydantic import BaseModel, Field

from unified_api_contracts import ErrorAction


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


class DatabentoTbbo(BaseModel):
    """Time and Sales BBO (trade-based best bid/offer).

    One row per trade with BBO immediately before that trade. In trade space
    (unlike MBP-1 which is in book-update space). action is always T (Trade).
    Ref: https://databento.com/docs/schemas-and-data-formats/tbbo
    """

    ts_recv: int = Field(..., description="Capture-server received timestamp (nanoseconds)")
    ts_event: int = Field(..., description="Matching-engine received timestamp (nanoseconds)")
    rtype: int = Field(..., description="Record type sentinel (always 1 for TBBO)")
    publisher_id: int = Field(..., description="Databento publisher ID")
    instrument_id: int = Field(..., description="Numeric instrument ID")
    action: str = Field(..., description="Event action (always T=Trade)")
    side: str = Field(..., description="Initiating side: A=Ask, B=Bid, N=None")
    depth: int = Field(..., description="Book level of the update")
    price: int = Field(..., description="Order price (fixed-point, divide by 1e9)")
    size: int = Field(..., description="Order quantity")
    flags: int | None = Field(None, description="Bit field for event end, data quality")
    ts_in_delta: int | None = Field(None, description="Matching-engine send time (ns before ts_recv)")
    sequence: int | None = Field(None, description="Venue message sequence number")
    bid_px_00: int = Field(..., description="Top-level bid price (fixed-point)")
    ask_px_00: int = Field(..., description="Top-level ask price (fixed-point)")
    bid_sz_00: int = Field(..., description="Top-level bid size")
    ask_sz_00: int = Field(..., description="Top-level ask size")
    bid_ct_00: int | None = Field(None, description="Top-level bid order count")
    ask_ct_00: int | None = Field(None, description="Top-level ask order count")


class DatabentoMbo(BaseModel):
    """Market by order (order-level book). Each record = one order event.

    Ref: https://databento.com/docs/schemas-and-data-formats/mbo
    """

    ts_recv: int = Field(..., description="Receive timestamp in nanoseconds")
    ts_event: int = Field(..., description="Event timestamp in nanoseconds")
    rtype: int = Field(..., description="Record type (MBO)")
    publisher_id: int = Field(..., description="Publisher/venue ID")
    instrument_id: int = Field(..., description="Databento instrument ID")
    order_id: int = Field(..., description="Order ID")
    price: int = Field(..., description="Order price (fixed-point, divide by 1e9)")
    size: int = Field(..., description="Order size")
    flags: int | None = Field(None, description="Event flags (LAST, SNAPSHOT)")
    channel_id: int | None = Field(None, description="Channel ID")
    action: str = Field(..., description="A=Add, C=Cancel, M=Modify, R=Clear, T=Trade, F=Fill, N=None")
    side: str = Field(..., description="A=Ask, B=Bid, N=None")
    ts_in_delta: int | None = Field(None, description="Timestamp delta in nanoseconds")
    sequence: int | None = Field(None, description="Message sequence number")


class DatabentoBbo1s(BaseModel):
    """Best bid and offer, 1-second interval. OHLCV-style BBO.

    Ref: https://databento.com/docs/schemas-and-data-formats/bbo
    """

    ts_recv: int = Field(..., description="End of interval (nanoseconds)")
    ts_event: int = Field(..., description="Last trade timestamp (nanoseconds)")
    rtype: int = Field(..., description="Record type")
    publisher_id: int = Field(..., description="Publisher ID")
    instrument_id: int = Field(..., description="Instrument ID")
    action: str = Field(..., description="Event action")
    side: str = Field(..., description="A=Ask, B=Bid, N=None")
    price: int = Field(..., description="Last trade price (fixed-point)")
    size: int = Field(..., description="Last trade size")
    flags: int | None = Field(None, description="Event/quality flags")
    ts_in_delta: int | None = Field(None, description="Timestamp delta")
    sequence: int | None = Field(None, description="Sequence number")
    bid_px_00: int = Field(..., description="Top bid price (fixed-point)")
    ask_px_00: int = Field(..., description="Top ask price (fixed-point)")
    bid_sz_00: int = Field(..., description="Top bid size")
    ask_sz_00: int = Field(..., description="Top ask size")
    bid_ct_00: int | None = Field(None, description="Top bid order count")
    ask_ct_00: int | None = Field(None, description="Top ask order count")


class DatabentoBbo1m(BaseModel):
    """Best bid and offer, 1-minute interval. Same structure as BBO-1s."""

    ts_recv: int = Field(..., description="End of interval (nanoseconds)")
    ts_event: int = Field(..., description="Last trade timestamp (nanoseconds)")
    rtype: int = Field(..., description="Record type")
    publisher_id: int = Field(..., description="Publisher ID")
    instrument_id: int = Field(..., description="Instrument ID")
    action: str = Field(..., description="Event action")
    side: str = Field(..., description="A=Ask, B=Bid, N=None")
    price: int = Field(..., description="Last trade price (fixed-point)")
    size: int = Field(..., description="Last trade size")
    flags: int | None = Field(None, description="Event/quality flags")
    ts_in_delta: int | None = Field(None, description="Timestamp delta")
    sequence: int | None = Field(None, description="Sequence number")
    bid_px_00: int = Field(..., description="Top bid price (fixed-point)")
    ask_px_00: int = Field(..., description="Top ask price (fixed-point)")
    bid_sz_00: int = Field(..., description="Top bid size")
    ask_sz_00: int = Field(..., description="Top ask size")
    bid_ct_00: int | None = Field(None, description="Top bid order count")
    ask_ct_00: int | None = Field(None, description="Top ask order count")


class DatabentoCmbp1(BaseModel):
    """Consolidated market by price, 1 level (multi-venue best bid/ask).

    Ref: https://databento.com/docs/schemas-and-data-formats/cmbp
    """

    ts_recv: int = Field(..., description="Receive timestamp (nanoseconds)")
    ts_event: int = Field(..., description="Event timestamp (nanoseconds)")
    rtype: int = Field(..., description="Record type (177 for CMBP-1)")
    publisher_id: int = Field(..., description="Publisher ID")
    instrument_id: int = Field(..., description="Instrument ID")
    action: str = Field(..., description="A, C, M, R, T")
    side: str = Field(..., description="A=Ask, B=Bid, N=None")
    price: int = Field(..., description="Order price (fixed-point)")
    size: int = Field(..., description="Order quantity")
    flags: int | None = Field(None, description="Event/quality flags")
    ts_in_delta: int | None = Field(None, description="Timestamp delta")
    bid_px_00: int = Field(..., description="Top bid price (fixed-point)")
    ask_px_00: int = Field(..., description="Top ask price (fixed-point)")
    bid_sz_00: int = Field(..., description="Top bid size")
    ask_sz_00: int = Field(..., description="Top ask size")
    bid_pb_00: int | None = Field(None, description="Publisher ID for best bid")
    ask_pb_00: int | None = Field(None, description="Publisher ID for best ask")


class DatabentoStatus(BaseModel):
    """Trading status message (halt, resume, etc.).

    Ref: https://databento.com/docs/schemas-and-data-formats/status
    """

    ts_recv: int = Field(..., description="Receive timestamp (nanoseconds)")
    ts_event: int = Field(..., description="Event timestamp (nanoseconds)")
    rtype: int = Field(..., description="Record type (18 for Status)")
    publisher_id: int = Field(..., description="Publisher ID")
    instrument_id: int = Field(..., description="Instrument ID")
    action: int = Field(..., description="Status change type")
    reason: int = Field(..., description="Reason for status change")
    trading_event: int = Field(..., description="Trading event code")
    is_trading: str = Field(..., description="Y/N/~")
    is_quoting: str = Field(..., description="Y/N/~")
    is_short_sell_restricted: str | None = Field(None, description="Y/N/~")


class DatabentoImbalance(BaseModel):
    """Auction imbalance (opening/closing auction).

    Ref: https://databento.com/docs/schemas-and-data-formats/imbalance
    """

    ts_recv: int = Field(..., description="Receive timestamp (nanoseconds)")
    ts_event: int = Field(..., description="Event timestamp (nanoseconds)")
    rtype: int = Field(..., description="Record type (20 for Imbalance)")
    publisher_id: int = Field(..., description="Publisher ID")
    instrument_id: int = Field(..., description="Instrument ID")
    ref_price: int = Field(..., description="Reference price (fixed-point)")
    auction_time: int = Field(..., description="Auction timestamp (nanoseconds)")
    cont_book_clr_price: int | None = Field(None, description="Hypothetical clearing price (cross+continuous)")
    auct_interest_clr_price: int | None = Field(None, description="Hypothetical clearing price (cross only)")
    ssr_filling_price: int | None = Field(None, description="SSR filling price")
    ind_match_price: int | None = Field(None, description="Indication match price")
    upper_collar: int | None = Field(None, description="Upper auction collar")
    lower_collar: int | None = Field(None, description="Lower auction collar")
    paired_qty: int | None = Field(None, description="Paired quantity at ref_price")
    total_imbalance_qty: int | None = Field(None, description="Unpaired quantity")
    market_imbalance_qty: int | None = Field(None, description="Market order imbalance")
    unpaired_qty: int | None = Field(None, description="Unpaired shares (Closing Auction)")
    auction_type: str | None = Field(None, description="Auction type code")
    side: str | None = Field(None, description="A=Ask, B=Bid, N=None")
    auction_status: int | None = Field(None, description="Auction status")
    freeze_status: int | None = Field(None, description="Freeze status")
    num_extensions: int | None = Field(None, description="Halt extension count")
    unpaired_side: str | None = Field(None, description="Side of unpaired_qty")
    significant_imbalance: str | None = Field(None, description="Significant imbalance flag")


class DatabentoStatistics(BaseModel):
    """Statistics record (VWAP, high, low, etc.).

    Ref: https://databento.com/docs/schemas-and-data-formats/statistics
    """

    ts_recv: int = Field(..., description="Receive timestamp (nanoseconds)")
    ts_event: int = Field(..., description="Event timestamp (nanoseconds)")
    rtype: int = Field(..., description="Record type (24 for Statistics)")
    publisher_id: int = Field(..., description="Publisher ID")
    instrument_id: int = Field(..., description="Instrument ID")
    ts_ref: int = Field(..., description="Reference timestamp (nanoseconds)")
    price: int = Field(..., description="Price stat (fixed-point)")
    quantity: int = Field(..., description="Non-price stat (INT64_MAX if unused)")
    sequence: int | None = Field(None, description="Sequence number")
    ts_in_delta: int | None = Field(None, description="Timestamp delta")
    stat_type: int = Field(..., description="Stat type")
    channel_id: int | None = Field(None, description="Channel ID")
    update_action: int | None = Field(None, description="1=Add, 2=Delete")
    stat_flags: int | None = Field(None, description="Stat flags")


class DatabentoSystemMsg(BaseModel):
    """System/gateway message (DBN v1: 64 chars; v2+: 303 chars)."""

    msg: str = Field(..., description="Gateway message")
    code: int | None = Field(None, description="System message type (DBN v2+)")


class DatabentoErrorMsg(BaseModel):
    """Error message from feed (DBN v1: 64 chars; v2+: 302 chars).

    Error codes: 1=AuthFailed, 2=ApiKeyDeactivated, 3=ConnectionLimitExceeded,
    4=SymbolResolutionFailed, 5=InvalidSubscription, 6=InternalError
    """

    err: str = Field(..., description="Error message")
    code: int | None = Field(None, description="Error code 1-6 (DBN v2+)")
    is_last: int | None = Field(None, description="Last in series of errors (DBN v2+)")


class DatabentoMbp10(BaseModel):
    """10-level market by price (L2 order book).

    Includes every trade and depth change with size and order count at each level.
    Ref: https://databento.com/docs/schemas-and-data-formats/mbp-10
    """

    ts_recv: int = Field(..., description="Capture-server received timestamp (nanoseconds)")
    ts_event: int = Field(..., description="Matching-engine received timestamp (nanoseconds)")
    rtype: int = Field(..., description="Record type sentinel")
    publisher_id: int = Field(..., description="Publisher ID")
    instrument_id: int = Field(..., description="Instrument ID")
    action: str = Field(..., description="Event action: A=Add, C=Cancel, M=Modify, R=Clear, T=Trade")
    side: str = Field(..., description="Initiating side: A, B, N")
    depth: int = Field(..., description="Book level of the update")
    price: int = Field(..., description="Order price (fixed-point)")
    size: int = Field(..., description="Order quantity")
    flags: int | None = Field(None, description="Bit field")
    ts_in_delta: int | None = Field(None, description="Timestamp delta")
    sequence: int | None = Field(None, description="Sequence number")
    # Level 0 (required for snapshot)
    bid_px_00: int = Field(..., description="Bid price level 0")
    ask_px_00: int = Field(..., description="Ask price level 0")
    bid_sz_00: int = Field(..., description="Bid size level 0")
    ask_sz_00: int = Field(..., description="Ask size level 0")
    bid_ct_00: int | None = Field(None, description="Bid order count level 0")
    ask_ct_00: int | None = Field(None, description="Ask order count level 0")
    # Levels 1-9 (optional for incremental updates)
    bid_px_01: int | None = None
    ask_px_01: int | None = None
    bid_sz_01: int | None = None
    ask_sz_01: int | None = None
    bid_ct_01: int | None = None
    ask_ct_01: int | None = None
    bid_px_02: int | None = None
    ask_px_02: int | None = None
    bid_sz_02: int | None = None
    ask_sz_02: int | None = None
    bid_ct_02: int | None = None
    ask_ct_02: int | None = None
    bid_px_03: int | None = None
    ask_px_03: int | None = None
    bid_sz_03: int | None = None
    ask_sz_03: int | None = None
    bid_ct_03: int | None = None
    ask_ct_03: int | None = None
    bid_px_04: int | None = None
    ask_px_04: int | None = None
    bid_sz_04: int | None = None
    ask_sz_04: int | None = None
    bid_ct_04: int | None = None
    ask_ct_04: int | None = None
    bid_px_05: int | None = None
    ask_px_05: int | None = None
    bid_sz_05: int | None = None
    ask_sz_05: int | None = None
    bid_ct_05: int | None = None
    ask_ct_05: int | None = None
    bid_px_06: int | None = None
    ask_px_06: int | None = None
    bid_sz_06: int | None = None
    ask_sz_06: int | None = None
    bid_ct_06: int | None = None
    ask_ct_06: int | None = None
    bid_px_07: int | None = None
    ask_px_07: int | None = None
    bid_sz_07: int | None = None
    ask_sz_07: int | None = None
    bid_ct_07: int | None = None
    ask_ct_07: int | None = None
    bid_px_08: int | None = None
    ask_px_08: int | None = None
    bid_sz_08: int | None = None
    ask_sz_08: int | None = None
    bid_ct_08: int | None = None
    ask_ct_08: int | None = None
    bid_px_09: int | None = None
    ask_px_09: int | None = None
    bid_sz_09: int | None = None
    ask_sz_09: int | None = None
    bid_ct_09: int | None = None
    ask_ct_09: int | None = None


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


class DatabentoOptionQuote(BaseModel):
    """Option quote (OPRA equity options: SPY, QQQ, etc.).

    Ref: https://databento.com/docs/schemas-and-data-formats/mbp-1
    """

    ts_recv: int = Field(..., description="Receive timestamp (nanoseconds)")
    ts_event: int = Field(..., description="Event timestamp (nanoseconds)")
    rtype: int = Field(..., description="Record type identifier")
    publisher_id: int = Field(..., description="Publisher ID (OPRA)")
    instrument_id: int = Field(..., description="Databento instrument ID")
    underlying: str = Field(..., description="Underlying symbol (SPY, QQQ)")
    strike_price: int = Field(..., description="Strike price (fixed-point, divide by 1e9)")
    expiration: int = Field(..., description="Expiration timestamp (nanoseconds)")
    option_type: str = Field(..., description="C=call, P=put")
    bid_px_00: int = Field(..., description="Best bid price (fixed-point)")
    ask_px_00: int = Field(..., description="Best ask price (fixed-point)")
    bid_sz_00: int = Field(..., description="Best bid size (contracts)")
    ask_sz_00: int = Field(..., description="Best ask size (contracts)")
    bid_ct_00: int | None = Field(None, description="Bid order count")
    ask_ct_00: int | None = Field(None, description="Ask order count")
    implied_volatility: int | None = Field(None, description="Implied volatility (fixed-point, divide by 1e9)")
    delta: int | None = Field(None, description="Delta (fixed-point, divide by 1e9)")
    gamma: int | None = Field(None, description="Gamma (fixed-point, divide by 1e9)")
    theta: int | None = Field(None, description="Theta (fixed-point, divide by 1e9)")
    vega: int | None = Field(None, description="Vega (fixed-point, divide by 1e9)")


class DatabentoCMEOptionQuote(BaseModel):
    """CME commodity option quote (GC, NG, CL, etc.).

    Ref: https://databento.com/docs/schemas-and-data-formats/mbp-1
    """

    ts_recv: int = Field(..., description="Receive timestamp (nanoseconds)")
    ts_event: int = Field(..., description="Event timestamp (nanoseconds)")
    rtype: int = Field(..., description="Record type identifier")
    publisher_id: int = Field(..., description="Publisher ID (CME)")
    instrument_id: int = Field(..., description="Databento instrument ID")
    underlying: str = Field(..., description="Underlying symbol (GC, NG, CL)")
    strike_price: int = Field(..., description="Strike price (fixed-point, divide by 1e9)")
    expiration: int = Field(..., description="Expiration timestamp (nanoseconds)")
    option_type: str = Field(..., description="C=call, P=put")
    bid_px_00: int = Field(..., description="Best bid price (fixed-point)")
    ask_px_00: int = Field(..., description="Best ask price (fixed-point)")
    bid_sz_00: int = Field(..., description="Best bid size (contracts)")
    ask_sz_00: int = Field(..., description="Best ask size (contracts)")
    bid_ct_00: int | None = Field(None, description="Bid order count")
    ask_ct_00: int | None = Field(None, description="Ask order count")
    implied_volatility: int | None = Field(None, description="Implied volatility (fixed-point, divide by 1e9)")
    delta: int | None = Field(None, description="Delta (fixed-point, divide by 1e9)")
    gamma: int | None = Field(None, description="Gamma (fixed-point, divide by 1e9)")
    theta: int | None = Field(None, description="Theta (fixed-point, divide by 1e9)")
    vega: int | None = Field(None, description="Vega (fixed-point, divide by 1e9)")
    contract_size: int | None = Field(None, description="Contract size/multiplier")
    unit_of_measure: str | None = Field(None, description="Unit of measure (oz, MMBtu)")


class DatabentoReferenceInstrument(BaseModel):
    """Instrument definition from Databento REST reference endpoint.

    Returned by GET https://hist.databento.com/v0/reference/instruments?dataset=...
    This is a JSON REST response, distinct from DatabentoDefinition which is the
    DBN binary format record.
    """

    instrument_id: int = Field(..., description="Databento internal instrument ID")
    raw_symbol: str = Field(..., description="Raw exchange symbol e.g. ESZ4")
    instrument_class: str = Field(
        ..., description="B=bond, C=crypto, E=equity, F=future, N=fund/ETF, O=option, S=FX spot, T=spread, X=index"
    )
    dataset: str | None = Field(None, description="Dataset the instrument belongs to e.g. GLBX.MDP3")
    currency: str | None = Field(None, description="Settlement/quote currency e.g. USD")
    expiration: str | None = Field(None, description="Expiry as ISO datetime string e.g. 2024-12-20T00:00:00Z")
    strike_price: float | None = Field(None, description="Strike price for options")
    option_type: str | None = Field(None, description="C=call or P=put for options")
    underlying: str | None = Field(None, description="Underlying symbol for derivatives")
    min_price_increment: float | None = Field(None, description="Minimum tick size")
    min_lot_size_round_lot: float | None = Field(None, description="Minimum round-lot size")


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
