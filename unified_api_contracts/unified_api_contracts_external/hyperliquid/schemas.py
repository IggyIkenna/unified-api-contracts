"""Hyperliquid HTTP + S3/stats: market data, order/position, errors, WebSocket."""

from pydantic import BaseModel, Field

from unified_api_contracts.shared import ErrorAction


# --- Nested types for user state ---
class HyperliquidAssetPosition(BaseModel):
    """Single asset position in user state."""

    coin: str | None = None
    cumFunding: dict[str, str] | None = None
    entryPx: str | None = None
    leverage: dict[str, object] | None = None
    liquidationPx: str | None = None
    marginUsed: str | None = None
    maxLeverage: int | None = None
    positionValue: str | None = None
    returnOnEquity: str | None = None
    szi: str | None = None
    unrealizedPnl: str | None = None


class HyperliquidAssetPositionEntry(BaseModel):
    """Asset position wrapper (position + type)."""

    position: HyperliquidAssetPosition | None = None
    type: str | None = None


class HyperliquidMarginSummary(BaseModel):
    """Margin summary (account value, margin used, etc.)."""

    accountValue: str | None = None
    totalMarginUsed: str | None = None
    totalNtlPos: str | None = None
    totalRawUsd: str | None = None


class HyperliquidUserState(BaseModel):
    """User clearinghouse state (equity, margin, withdrawable, assetPositions).

    POST /info type='clearinghouseState'
    """

    assetPositions: list[HyperliquidAssetPositionEntry] | None = None
    crossMaintenanceMarginUsed: str | None = None
    crossMarginSummary: HyperliquidMarginSummary | None = None
    marginSummary: HyperliquidMarginSummary | None = None
    time: int | None = None
    withdrawable: str | None = None


class HyperliquidL2Level(BaseModel):
    """Single level in L2 book."""

    px: str | None = None
    sz: str | None = None
    n: int | None = None


class HyperliquidL2Book(BaseModel):
    """L2 order book snapshot. POST /info type='l2Book'."""

    coin: str | None = None
    time: int | None = None
    levels: list[list[HyperliquidL2Level]] | None = None  # [bids, asks]


class HyperliquidFundingHistoryEntry(BaseModel):
    """Funding history entry. POST /info type='userFunding' or 'fundingHistory'."""

    coin: str | None = None
    fundingRate: str | None = None
    premium: str | None = None
    time: int | None = None
    delta: dict[str, object] | None = None
    hash: str | None = None
    szi: str | None = None
    usdc: str | None = None


class HyperliquidFill(BaseModel):
    """Fill/trade (fees, closedPnl). POST /info type='userFills'."""

    closedPnl: str | None = None
    coin: str | None = None
    crossed: bool | None = None
    dir: str | None = None
    fee: str | None = None
    feeToken: str | None = None
    builderFee: str | None = None
    hash: str | None = None
    oid: int | None = None
    px: str | None = None
    side: str | None = None
    startPosition: str | None = None
    sz: str | None = None
    time: int | None = None
    tid: int | None = None


class HyperliquidOpenOrder(BaseModel):
    """Open order. POST /info type='openOrders' or 'frontendOpenOrders'."""

    coin: str | None = None
    limitPx: str | None = None
    oid: int | None = None
    side: str | None = None
    sz: str | None = None
    timestamp: int | None = None
    isPositionTpsl: bool | None = None
    isTrigger: bool | None = None
    orderType: str | None = None
    origSz: str | None = None
    reduceOnly: bool | None = None
    triggerCondition: str | None = None
    triggerPx: str | None = None


class HyperliquidCandle(BaseModel):
    """OHLCV candle. POST /info type='candleSnapshot'."""

    T: int | None = None  # close time
    c: str | None = None  # close
    h: str | None = None  # high
    i: str | None = None  # interval
    low: str | None = Field(None, alias="l")  # low (l in API)
    n: int | None = None  # num trades
    o: str | None = None  # open
    s: str | None = None  # symbol
    t: int | None = None  # start time
    v: str | None = None  # volume


class HyperliquidVaultDetails(BaseModel):
    """Vault details. POST /info type='vaultDetails'."""

    name: str | None = None
    vaultAddress: str | None = None
    leader: str | None = None
    description: str | None = None
    portfolio: list[tuple[str, dict[str, object]]] | None = None
    apr: float | None = None
    followerState: dict[str, object] | None = None
    leaderFraction: float | None = None
    leaderCommission: float | None = None
    followers: list[dict[str, object]] | None = None
    maxDistributable: float | None = None
    maxWithdrawable: float | None = None
    isClosed: bool | None = None
    relationship: dict[str, object] | None = None
    allowDeposits: bool | None = None
    alwaysCloseOnWithdraw: bool | None = None


class HyperliquidLiquidation(BaseModel):
    """Liquidation event (WebSocket or fills)."""

    lid: int | None = None
    liquidator: str | None = None
    liquidated_user: str | None = None
    liquidated_ntl_pos: str | None = None
    liquidated_account_value: str | None = None
    liquidatedUser: str | None = None
    markPx: float | None = None
    method: str | None = None  # "market" | "backstop"


class HyperliquidSpotTokenInfo(BaseModel):
    """Spot token metadata from spotMeta."""

    name: str | None = None
    szDecimals: int | None = None
    weiDecimals: int | None = None
    index: int | None = None
    tokenId: str | None = None
    isCanonical: bool | None = None
    evmContract: str | None = None
    fullName: str | None = None


class HyperliquidSpotPairInfo(BaseModel):
    """Spot pair metadata from spotMeta universe."""

    name: str | None = None
    tokens: list[int] | None = None
    index: int | None = None
    isCanonical: bool | None = None


class HyperliquidSpotMeta(BaseModel):
    """Spot market metadata. POST /info type='spotMeta'."""

    tokens: list[HyperliquidSpotTokenInfo] | None = None
    universe: list[HyperliquidSpotPairInfo] | None = None


class HyperliquidSpotAssetInfo(BaseModel):
    """Spot balance/asset info (from subAccounts spotState)."""

    coin: str | None = None
    token: int | None = None
    total: str | None = None
    hold: str | None = None
    entryNtl: str | None = None


class HyperliquidUserFees(BaseModel):
    """User fee schedule. POST /info type='userFees'."""

    dailyUserVlm: list[dict[str, object]] | None = None
    feeSchedule: dict[str, object] | None = None
    userCrossRate: str | None = None
    userAddRate: str | None = None
    userSpotCrossRate: str | None = None
    userSpotAddRate: str | None = None
    activeReferralDiscount: str | None = None
    trial: dict[str, object] | None = None
    feeTrialReward: str | None = None
    nextTrialAvailableTimestamp: int | None = None
    stakingLink: dict[str, object] | None = None
    activeStakingDiscount: dict[str, object] | None = None


class HyperliquidSubAccount(BaseModel):
    """Sub-account. POST /info type='subAccounts'."""

    name: str | None = None
    subAccountUser: str | None = None
    master: str | None = None
    clearinghouseState: HyperliquidUserState | None = None
    spotState: dict[str, object] | None = None


class HyperliquidAssetInfo(BaseModel):
    """Hyperliquid asset/perpetual metadata (REST POST /info, type='meta').

    Response is a list of asset objects inside universe[].
    """

    name: str  # e.g. BTC, ETH
    szDecimals: int | None = None  # decimal places for size
    maxLeverage: int | None = None
    onlyIsolated: bool | None = None


class HyperliquidMeta(BaseModel):
    """Hyperliquid exchange meta (POST /info, type='meta')."""

    universe: list[HyperliquidAssetInfo] | None = None


class HyperliquidTicker(BaseModel):
    """Ticker / mid / mark from HTTP API."""

    coin: str | None = None
    markPx: str | None = None
    midPx: str | None = None
    prevDayPx: str | None = None
    dayNtlVlm: str | None = None
    funding: str | None = None
    openInterest: str | None = None
    info: dict[str, object] | None = None


class HyperliquidOrder(BaseModel):
    """Order (REST or WebSocket)."""

    coin: str | None = None
    side: str | None = None
    limitPx: str | None = None
    sz: str | None = None
    orderType: dict[str, object] | None = None
    oid: int | None = None
    timestamp: int | None = None
    status: str | None = None
    info: dict[str, object] | None = None


class HyperliquidPosition(BaseModel):
    """Position from user state / fills."""

    coin: str | None = None
    entryPx: str | None = None
    positionValue: str | None = None
    unrealizedPnl: str | None = None
    szi: str | None = None  # size (signed)
    leverage: dict[str, object] | None = None
    info: dict[str, object] | None = None


class HyperliquidError(BaseModel):
    """Hyperliquid API error."""

    response: dict[str, object] | None = None
    message: str | None = None

    @classmethod
    def classify(cls, http_status: int | None = None, message: str | None = None) -> ErrorAction:
        """Map Hyperliquid error to retry action.

        Hyperliquid uses HTTP status codes primarily; no structured error codes.
        """
        if http_status is not None and http_status >= 500:
            return ErrorAction.RETRY_WITH_BACKOFF
        return ErrorAction.FAIL_HARD


# --- S3 / stats bucket (e.g. daily stats) ---
class HyperliquidStatsRow(BaseModel):
    """Single row from stats bucket (e.g. daily volume)."""

    coin: str | None = None
    volume: str | float | None = None
    openInterest: str | float | None = None
    info: dict[str, object] | None = None


class HyperliquidWebSocketSubscribe(BaseModel):
    """Hyperliquid WebSocket subscription request.

    WS: wss://api.hyperliquid.xyz/ws
    Auth: Ethereum wallet address (user field in private subscriptions)
    """

    method: str  # "subscribe" or "unsubscribe"
    subscription: dict[str, object]  # {"type": "trades", "coin": "BTC"} or {"type": "orderUpdates", "user": "0x..."}


class HyperliquidWebSocketPost(BaseModel):
    """Hyperliquid WebSocket POST request (for sending orders via WS)."""

    method: str = "post"
    id: int  # request tracking id
    request: dict[str, object]  # {"type": "order", ...} — same format as REST /exchange POST body


class HyperliquidWebSocketClose(BaseModel):
    """Hyperliquid WebSocket close frame (RFC 6455).

    Codes: 1000=normal, 1006=abnormal, 1008=policy.
    """

    code: int
    reason: str | None = None
