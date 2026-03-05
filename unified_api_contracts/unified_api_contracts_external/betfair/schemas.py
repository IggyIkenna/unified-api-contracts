"""Betfair Exchange API: streaming (auth, subscriptions, market data, order updates) and REST response schemas.

Streaming: https://docs.developer.betfair.com/display/1smk3cen4v3lu3yomq5qye0ni/Exchange+Stream+API
REST: https://docs.developer.betfair.com/display/1smk3cen4v3lu3yomq5qye0ni/Betting+API
"""

from pydantic import BaseModel, Field

from unified_api_contracts.shared import ErrorAction


class BetfairPriceSize(BaseModel):
    """Price and size at a level (shared by streaming and REST)."""

    price: float | None = None
    size: float | None = None


# ---------------------------------------------------------------------------
# REST: listMarketCatalogue (MarketCatalogue)
# ---------------------------------------------------------------------------


class BetfairEventType(BaseModel):
    """Event type (e.g. Soccer, Tennis)."""

    id: str | None = None
    name: str | None = None


class BetfairCompetition(BaseModel):
    """Competition within an event type."""

    id: str | None = None
    name: str | None = None


class BetfairEvent(BaseModel):
    """Event (match/race) within a competition."""

    id: str | None = None
    name: str | None = None
    country_code: str | None = Field(None, alias="countryCode")
    timezone: str | None = None
    open_date: str | None = Field(None, alias="openDate")


class BetfairRunnerCatalog(BaseModel):
    """Runner (selection) in market catalogue."""

    selection_id: int | None = Field(None, alias="selectionId")
    runner_name: str | None = Field(None, alias="runnerName")
    handicap: float | None = None
    sort_priority: int | None = Field(None, alias="sortPriority")
    metadata: dict[str, object] | None = None


class BetfairMarketCatalogue(BaseModel):
    """Market catalogue item from listMarketCatalogue response.

    Ref: Betting Type Definitions - MarketCatalogue
    """

    market_id: str | None = Field(None, alias="marketId")
    market_name: str | None = Field(None, alias="marketName")
    market_start_time: str | None = Field(None, alias="marketStartTime")
    total_matched: float | None = Field(None, alias="totalMatched")
    runners: list[BetfairRunnerCatalog] | None = None
    event_type: BetfairEventType | None = Field(None, alias="eventType")
    competition: BetfairCompetition | None = None
    event: BetfairEvent | None = None


# ---------------------------------------------------------------------------
# REST: placeOrders (PlaceExecutionReport)
# ---------------------------------------------------------------------------


class BetfairPlaceInstructionReport(BaseModel):
    """Report for a single place instruction."""

    status: str | None = None
    bet_id: str | None = Field(None, alias="betId")
    placed_date: str | None = Field(None, alias="placedDate")
    average_price_matched: float | None = Field(None, alias="averagePriceMatched")
    size_matched: float | None = Field(None, alias="sizeMatched")
    order_status: str | None = Field(None, alias="orderStatus")
    error_code: str | None = Field(None, alias="errorCode")
    instruction: dict[str, object] | None = None


class BetfairPlaceOrdersResponse(BaseModel):
    """placeOrders response (PlaceExecutionReport)."""

    status: str | None = None
    market_id: str | None = Field(None, alias="marketId")
    error_code: str | None = Field(None, alias="errorCode")
    instruction_reports: list[BetfairPlaceInstructionReport] | None = Field(None, alias="instructionReports")


# ---------------------------------------------------------------------------
# REST: listCurrentOrders (CurrentOrderSummaryReport)
# ---------------------------------------------------------------------------


class BetfairCurrentOrderSummary(BaseModel):
    """Current order summary from listCurrentOrders."""

    bet_id: str | None = Field(None, alias="betId")
    market_id: str | None = Field(None, alias="marketId")
    selection_id: int | None = Field(None, alias="selectionId")
    handicap: float | None = None
    price_size: BetfairPriceSize | None = Field(None, alias="priceSize")
    bsp_liability: float | None = Field(None, alias="bspLiability")
    side: str | None = None
    status: str | None = None
    persistence_type: str | None = Field(None, alias="persistenceType")
    order_type: str | None = Field(None, alias="orderType")
    placed_date: str | None = Field(None, alias="placedDate")
    average_price_matched: float | None = Field(None, alias="averagePriceMatched")
    size_matched: float | None = Field(None, alias="sizeMatched")
    size_remaining: float | None = Field(None, alias="sizeRemaining")
    size_lapsed: float | None = Field(None, alias="sizeLapsed")
    size_cancelled: float | None = Field(None, alias="sizeCancelled")
    size_voided: float | None = Field(None, alias="sizeVoided")
    regulator_code: str | None = Field(None, alias="regulatorCode")


class BetfairListCurrentOrdersResponse(BaseModel):
    """listCurrentOrders response (CurrentOrderSummaryReport)."""

    current_orders: list[BetfairCurrentOrderSummary] | None = Field(None, alias="currentOrders")
    more_available: bool | None = Field(None, alias="moreAvailable")


# ---------------------------------------------------------------------------
# Streaming API (existing)
# ---------------------------------------------------------------------------


class BetfairAuthRequest(BaseModel):
    """Betfair authentication request (cert login or app key)."""

    username: str | None = None
    password: str | None = None
    app_key: str | None = Field(None, alias="appKey")


class BetfairAuthResponse(BaseModel):
    """Betfair authentication response with session token."""

    session_token: str | None = Field(None, alias="sessionToken")
    status: str | None = None
    token: str | None = None


class BetfairMarketSubscription(BaseModel):
    """Market subscription request for Betfair Stream API."""

    market_ids: list[str] | None = Field(None, alias="marketIds")
    market_filter: dict[str, object] | None = Field(None, alias="marketFilter")
    market_data_filter: dict[str, object] | None = Field(None, alias="marketDataFilter")
    conflate_ms: int | None = Field(None, alias="conflateMs")


class BetfairOrderSubscription(BaseModel):
    """Order subscription request for Betfair Stream API."""

    order_filter: dict[str, object] | None = Field(None, alias="orderFilter")
    order_data_filter: dict[str, object] | None = Field(None, alias="orderDataFilter")


class BetfairRunner(BaseModel):
    """Runner (selection) in a market."""

    selection_id: int | None = Field(None, alias="selectionId")
    handicap: float | None = None
    status: str | None = None
    adjustment_factor: float | None = Field(None, alias="adjustmentFactor")
    last_price_traded: float | None = Field(None, alias="lastPriceTraded")
    total_matched: float | None = Field(None, alias="totalMatched")
    removal_date: str | None = Field(None, alias="removalDate")
    ex: dict[str, list[dict[str, float]]] | None = None  # availableToBack, availableToLay, tradedVolume
    sp: dict[str, list[dict[str, float]]] | None = None  # starting price


class BetfairMarketBook(BaseModel):
    """Market book snapshot (order book for a market)."""

    market_id: str | None = Field(None, alias="marketId")
    is_market_data_delayed: bool | None = Field(None, alias="isMarketDataDelayed")
    status: str | None = None
    bet_delay: int | None = Field(None, alias="betDelay")
    bsp_reconciled: bool | None = Field(None, alias="bspReconciled")
    complete: bool | None = None
    in_play: bool | None = Field(None, alias="inPlay")
    number_of_winners: int | None = Field(None, alias="numberOfWinners")
    runners: list[BetfairRunner] | None = None
    runners_vacant: bool | None = Field(None, alias="runnersVacant")


class BetfairRunnerChange(BaseModel):
    """Runner change in a market delta."""

    id: int | None = None
    atb: list[BetfairPriceSize] | None = None
    atl: list[BetfairPriceSize] | None = None
    trd: list[BetfairPriceSize] | None = None
    sp: dict[str, object] | None = None
    hc: float | None = None
    uo: bool | None = None


class BetfairMarketChangeMessage(BaseModel):
    """Market change message (mcm) from Betfair Stream API."""

    op: str | None = None
    id: int | None = None
    clk: str | None = None
    pt: int | None = None
    ct: str | None = None
    initial_clk: str | None = Field(None, alias="initialClk")
    conflate_ms: int | None = Field(None, alias="conflateMs")
    heartbeat_ms: int | None = Field(None, alias="heartbeatMs")
    mc: list[dict[str, object]] | None = None  # market changes


class BetfairOrderUpdate(BaseModel):
    """Order update from Betfair Stream API."""

    op: str | None = None
    id: int | None = None
    clk: str | None = None
    pt: int | None = None
    ct: str | None = None
    initial_clk: str | None = Field(None, alias="initialClk")
    conflate_ms: int | None = Field(None, alias="conflateMs")
    heartbeat_ms: int | None = Field(None, alias="heartbeatMs")
    oc: list[dict[str, object]] | None = None  # order changes


class BetfairError(BaseModel):
    """Betfair API error response."""

    error: str | None = None
    error_code: str | None = Field(None, alias="errorCode")
    request_id: str | None = Field(None, alias="requestId")

    @classmethod
    def classify(cls, error_code: str | None = None, error: str | None = None) -> ErrorAction:
        """Map Betfair error to retry action."""
        if error_code == "INVALID_SESSION_INFORMATION" or (error and "session" in (error or "").lower()):
            return ErrorAction.RECONNECT
        if error_code == "TOO_MANY_REQUESTS" or (error and "rate" in (error or "").lower()):
            return ErrorAction.RETRY_WITH_BACKOFF
        if error_code == "INVALID_APP_KEY" or (error and "unauthorized" in (error or "").lower()):
            return ErrorAction.FAIL_HARD
        return ErrorAction.FAIL_HARD
