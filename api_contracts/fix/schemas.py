"""FIX protocol message schemas — FIX 4.2 / 4.4 / 5.0.

Covers order management (NewOrderSingle, ExecutionReport, Cancel),
market data (MarketDataRequest, Snapshot, IncrementalRefresh),
and admin messages (Logon, Logout, Heartbeat).

Venues: IBKR (FIX 4.2 TWS), Databento market data (FIX 4.4), institutional CeFi.
Tags referenced in docstrings use FIX standard notation (e.g. Tag 35 = MsgType).
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field


class FixVersion(StrEnum):
    FIX42 = "FIX.4.2"
    FIX44 = "FIX.4.4"
    FIX50 = "FIX.5.0"
    FIXT11 = "FIXT.1.1"


class FixMsgType(StrEnum):
    """Tag 35 values."""

    HEARTBEAT = "0"
    LOGON = "A"
    LOGOUT = "5"
    RESEND_REQUEST = "2"
    REJECT = "3"
    SEQUENCE_RESET = "4"
    # Order management
    NEW_ORDER_SINGLE = "D"
    ORDER_CANCEL_REQUEST = "F"
    ORDER_CANCEL_REPLACE = "G"
    EXECUTION_REPORT = "8"
    ORDER_CANCEL_REJECT = "9"
    # Market data
    MARKET_DATA_REQUEST = "V"
    MARKET_DATA_SNAPSHOT = "W"
    MARKET_DATA_INCREMENTAL_REFRESH = "X"
    MARKET_DATA_REQUEST_REJECT = "Y"
    # Business-level reject
    BUSINESS_MESSAGE_REJECT = "j"
    # Pre-trade
    QUOTE_REQUEST = "R"
    QUOTE = "S"
    QUOTE_CANCEL = "Z"


class FixSide(StrEnum):
    BUY = "1"
    SELL = "2"
    BUY_MINUS = "3"
    SELL_PLUS = "4"
    SELL_SHORT = "5"
    SELL_SHORT_EXEMPT = "6"


class FixOrdType(StrEnum):
    MARKET = "1"
    LIMIT = "2"
    STOP = "3"
    STOP_LIMIT = "4"
    MARKET_ON_CLOSE = "5"
    LIMIT_ON_CLOSE = "B"
    PEGGED = "P"


class FixTimeInForce(StrEnum):
    DAY = "0"
    GTC = "1"
    AT_OPEN = "2"
    IOC = "3"
    FOK = "4"
    GTD = "6"
    AT_CLOSE = "7"


class FixOrdStatus(StrEnum):
    NEW = "0"
    PARTIALLY_FILLED = "1"
    FILLED = "2"
    DONE_FOR_DAY = "3"
    CANCELLED = "4"
    REPLACED = "5"
    PENDING_CANCEL = "6"
    STOPPED = "7"
    REJECTED = "8"
    SUSPENDED = "9"
    PENDING_NEW = "A"
    CALCULATED = "B"
    EXPIRED = "C"
    ACCEPTED_FOR_BIDDING = "D"
    PENDING_REPLACE = "E"


class FixExecType(StrEnum):
    NEW = "0"
    PARTIAL_FILL = "1"
    FILL = "2"
    DONE_FOR_DAY = "3"
    CANCELLED = "4"
    REPLACED = "5"
    PENDING_CANCEL = "6"
    STOPPED = "7"
    REJECTED = "8"
    SUSPENDED = "9"
    PENDING_NEW = "A"
    CALCULATED = "B"
    EXPIRED = "C"
    RESTATED = "D"
    PENDING_REPLACE = "E"
    TRADE = "F"
    TRADE_CORRECT = "G"
    TRADE_CANCEL = "H"
    ORDER_STATUS = "I"


class FixHeader(BaseModel):
    """Standard FIX message header (Tags 8, 9, 35, 34, 49, 56, 52)."""

    begin_string: FixVersion = Field(description="Tag 8: FIX version")
    body_length: int | None = Field(default=None, description="Tag 9: length of body in bytes")
    msg_type: FixMsgType = Field(description="Tag 35: message type")
    msg_seq_num: int = Field(description="Tag 34: sequence number")
    sender_comp_id: str = Field(description="Tag 49: sending firm ID")
    target_comp_id: str = Field(description="Tag 56: target firm ID")
    sending_time: datetime = Field(description="Tag 52: UTC send time")
    on_behalf_of_comp_id: str | None = Field(default=None, description="Tag 115")
    deliver_to_comp_id: str | None = Field(default=None, description="Tag 128")


class FixTrailer(BaseModel):
    """Standard FIX message trailer (Tag 10 checksum)."""

    check_sum: str = Field(description="Tag 10: 3-digit checksum string")


class FixSessionConfig(BaseModel):
    """Connection config for a FIX session."""

    begin_string: FixVersion
    sender_comp_id: str
    target_comp_id: str
    host: str
    port: int
    heartbeat_interval_seconds: int = 30
    reconnect_interval_seconds: int = 10
    log_on_password: str | None = None
    reset_on_logon: bool = True
    reset_on_logout: bool = False
    reset_on_disconnect: bool = False


# ---------------------------------------------------------------------------
# Admin messages
# ---------------------------------------------------------------------------


class FixLogon(BaseModel):
    """Tag 35=A — session logon."""

    header: FixHeader
    encrypt_method: int = Field(default=0, description="Tag 98: 0=none")
    heartbt_int: int = Field(default=30, description="Tag 108: heartbeat interval seconds")
    reset_seq_num_flag: bool = Field(default=False, description="Tag 141")
    username: str | None = Field(default=None, description="Tag 553")
    password: str | None = Field(default=None, description="Tag 554")
    trailer: FixTrailer | None = None


class FixLogout(BaseModel):
    """Tag 35=5 — session logout."""

    header: FixHeader
    text: str | None = Field(default=None, description="Tag 58: free text reason")
    trailer: FixTrailer | None = None


class FixHeartbeat(BaseModel):
    """Tag 35=0 — heartbeat / test request response."""

    header: FixHeader
    test_req_id: str | None = Field(default=None, description="Tag 112: echoed from TestRequest")
    trailer: FixTrailer | None = None


class FixReject(BaseModel):
    """Tag 35=3 — session-level reject."""

    header: FixHeader
    ref_seq_num: int = Field(description="Tag 45: rejected message sequence number")
    ref_msg_type: str | None = Field(default=None, description="Tag 372: rejected MsgType")
    session_reject_reason: int | None = Field(default=None, description="Tag 373")
    text: str | None = Field(default=None, description="Tag 58")
    trailer: FixTrailer | None = None


# ---------------------------------------------------------------------------
# Order management messages
# ---------------------------------------------------------------------------


class FixNewOrderSingle(BaseModel):
    """Tag 35=D — submit a new order."""

    header: FixHeader
    cl_ord_id: str = Field(description="Tag 11: client order ID (unique per session)")
    symbol: str = Field(description="Tag 55: instrument symbol")
    security_id: str | None = Field(default=None, description="Tag 48: exchange-native ID")
    security_id_source: str | None = Field(default=None, description="Tag 22: e.g. 8=ISIN")
    security_type: str | None = Field(default=None, description="Tag 167: CS/FUT/OPT/FX/MLEG")
    maturity_month_year: str | None = Field(default=None, description="Tag 200: YYYYMM")
    maturity_date: str | None = Field(default=None, description="Tag 541: YYYYMMDD")
    put_or_call: str | None = Field(default=None, description="Tag 201: 0=put 1=call")
    strike_price: Decimal | None = Field(default=None, description="Tag 202")
    side: FixSide = Field(description="Tag 54")
    transact_time: datetime = Field(description="Tag 60: UTC")
    order_qty: Decimal = Field(description="Tag 38: shares/contracts")
    ord_type: FixOrdType = Field(description="Tag 40")
    price: Decimal | None = Field(default=None, description="Tag 44: limit price")
    stop_px: Decimal | None = Field(default=None, description="Tag 99: stop price")
    time_in_force: FixTimeInForce = Field(default=FixTimeInForce.DAY, description="Tag 59")
    expire_time: datetime | None = Field(default=None, description="Tag 126: GTD expiry")
    account: str | None = Field(default=None, description="Tag 1: account code")
    on_behalf_of_comp_id: str | None = Field(default=None, description="Tag 115")
    ex_destination: str | None = Field(default=None, description="Tag 100: routing venue MIC")
    currency: str | None = Field(default=None, description="Tag 15: ISO 4217")
    min_qty: Decimal | None = Field(default=None, description="Tag 110")
    max_floor: Decimal | None = Field(default=None, description="Tag 111: iceberg peak size")
    text: str | None = Field(default=None, description="Tag 58: free text")
    trailer: FixTrailer | None = None


class FixExecutionReport(BaseModel):
    """Tag 35=8 — execution report (ack, fill, cancel confirm, reject)."""

    header: FixHeader
    order_id: str = Field(description="Tag 37: exchange-assigned order ID")
    cl_ord_id: str = Field(description="Tag 11: client order ID")
    orig_cl_ord_id: str | None = Field(default=None, description="Tag 41: previous cl_ord_id")
    exec_id: str = Field(description="Tag 17: unique execution ID")
    exec_type: FixExecType = Field(description="Tag 150")
    ord_status: FixOrdStatus = Field(description="Tag 39")
    symbol: str = Field(description="Tag 55")
    side: FixSide = Field(description="Tag 54")
    order_qty: Decimal = Field(description="Tag 38")
    last_qty: Decimal | None = Field(default=None, description="Tag 32: qty of this fill")
    last_px: Decimal | None = Field(default=None, description="Tag 31: price of this fill")
    leaves_qty: Decimal = Field(description="Tag 151: open quantity remaining")
    cum_qty: Decimal = Field(description="Tag 14: total filled quantity")
    avg_px: Decimal = Field(description="Tag 6: average fill price")
    transact_time: datetime = Field(description="Tag 60: UTC")
    account: str | None = Field(default=None, description="Tag 1")
    text: str | None = Field(default=None, description="Tag 58: reject reason or notes")
    ord_rej_reason: int | None = Field(default=None, description="Tag 103")
    exec_restatement_reason: int | None = Field(default=None, description="Tag 378")
    trailer: FixTrailer | None = None


class FixOrderCancelRequest(BaseModel):
    """Tag 35=F — cancel an open order."""

    header: FixHeader
    orig_cl_ord_id: str = Field(description="Tag 41: cl_ord_id of order to cancel")
    cl_ord_id: str = Field(description="Tag 11: new unique ID for this cancel request")
    order_id: str | None = Field(default=None, description="Tag 37: exchange order ID")
    symbol: str = Field(description="Tag 55")
    side: FixSide = Field(description="Tag 54")
    transact_time: datetime = Field(description="Tag 60")
    order_qty: Decimal | None = Field(default=None, description="Tag 38")
    text: str | None = Field(default=None, description="Tag 58")
    trailer: FixTrailer | None = None


class FixOrderCancelReject(BaseModel):
    """Tag 35=9 — cancel request rejected by exchange."""

    header: FixHeader
    order_id: str = Field(description="Tag 37")
    cl_ord_id: str = Field(description="Tag 11")
    orig_cl_ord_id: str = Field(description="Tag 41")
    ord_status: FixOrdStatus = Field(description="Tag 39: current status")
    cxl_rej_reason: int | None = Field(default=None, description="Tag 102")
    cxl_rej_response_to: str = Field(
        default="1",
        description="Tag 434: 1=OrderCancelRequest 2=OrderCancelReplaceRequest",
    )
    text: str | None = Field(default=None, description="Tag 58")
    trailer: FixTrailer | None = None


# ---------------------------------------------------------------------------
# Market data messages (FIX 4.4+)
# ---------------------------------------------------------------------------


class FixMdEntryType(StrEnum):
    BID = "0"
    OFFER = "1"
    TRADE = "2"
    INDEX_VALUE = "3"
    OPENING_PRICE = "4"
    CLOSING_PRICE = "5"
    SETTLEMENT_PRICE = "6"
    HIGH_PRICE = "7"
    LOW_PRICE = "8"
    TRADE_VOLUME = "B"
    OPEN_INTEREST = "C"


class FixMarketDataRequest(BaseModel):
    """Tag 35=V — subscribe to or unsubscribe from market data."""

    header: FixHeader
    md_req_id: str = Field(description="Tag 262: client-assigned request ID")
    subscription_request_type: str = Field(description="Tag 263: 0=snapshot 1=subscribe 2=unsubscribe")
    market_depth: int = Field(default=0, description="Tag 264: 0=full book 1=top of book")
    md_update_type: str | None = Field(default=None, description="Tag 265: 0=full 1=incremental")
    no_md_entry_types: list[FixMdEntryType] = Field(default_factory=list, description="Tag 267 group: types requested")
    symbols: list[str] = Field(default_factory=list, description="Tag 55 group: instruments")
    trailer: FixTrailer | None = None


class FixMdEntry(BaseModel):
    """Single market data entry in snapshot or incremental refresh."""

    md_entry_type: FixMdEntryType = Field(description="Tag 269")
    md_entry_px: Decimal | None = Field(default=None, description="Tag 270: price")
    md_entry_size: Decimal | None = Field(default=None, description="Tag 271: quantity")
    md_update_action: str | None = Field(
        default=None, description="Tag 279: 0=new 1=change 2=delete (incremental only)"
    )
    symbol: str | None = Field(default=None, description="Tag 55")
    md_entry_date: str | None = Field(default=None, description="Tag 272: YYYYMMDD")
    md_entry_time: str | None = Field(default=None, description="Tag 273: HH:MM:SS.sss")


class FixMarketDataSnapshot(BaseModel):
    """Tag 35=W — full market data snapshot."""

    header: FixHeader
    md_req_id: str = Field(description="Tag 262")
    symbol: str = Field(description="Tag 55")
    no_md_entries: list[FixMdEntry] = Field(default_factory=list, description="Tag 268 group")
    trailer: FixTrailer | None = None


class FixMarketDataIncrementalRefresh(BaseModel):
    """Tag 35=X — incremental market data update."""

    header: FixHeader
    md_req_id: str | None = Field(default=None, description="Tag 262")
    no_md_entries: list[FixMdEntry] = Field(default_factory=list, description="Tag 268 group")
    trailer: FixTrailer | None = None
