"""Polymarket CLOB API: markets, tokens, order book, trades, orders, fills, market results, errors.

Polymarket runs on Polygon. Ref: https://docs.polymarket.com/

Three-API architecture:
- Gamma API (gamma-api.polymarket.com): events, markets, tags — metadata, no auth
- CLOB API (clob.polymarket.com): order book, orders, trades — trading, L2 HMAC auth
- Subgraph (Goldsky): on-chain history, OI, PNL
"""

from pydantic import BaseModel, Field

from unified_api_contracts.shared import ErrorAction

# ---------------------------------------------------------------------------
# PolymarketIdentifiers — critical for joining Gamma, CLOB, Subgraph
# ---------------------------------------------------------------------------


class PolymarketIdentifiers(BaseModel):
    """Identifiers for joining Polymarket data across Gamma, CLOB, and Subgraph.

    Join pattern:
      Gamma market.condition_id == Subgraph condition.id
      Gamma market.clob_token_ids[0] == CLOB token_id (YES)
      Gamma market.clob_token_ids[1] == CLOB token_id (NO)
    """

    condition_id: str | None = Field(None, alias="conditionId")
    question_id: str | None = Field(None, alias="questionId")
    market_id: str | None = Field(None, alias="marketId")
    slug: str | None = None
    clob_token_ids: list[str] | None = Field(None, alias="clobTokenIds")
    market_maker_address: str | None = Field(None, alias="marketMakerAddress")


class PolymarketToken(BaseModel):
    """Outcome token in a Polymarket market."""

    token_id: str | None = Field(None, alias="tokenId")
    outcome: str | None = None
    price: float | None = None


class PolymarketMarket(BaseModel):
    """Polymarket prediction market."""

    condition_id: str | None = Field(None, alias="conditionId")
    question: str | None = None
    end_date_iso: str | None = Field(None, alias="endDateIso")
    market_slug: str | None = Field(None, alias="marketSlug")
    tokens: list[PolymarketToken] | None = None
    volume: float | None = None
    liquidity: float | None = None
    active: bool | None = None
    closed: bool | None = None


class PolymarketOrderBook(BaseModel):
    """Order book for a Polymarket market/token."""

    market: str | None = None
    asset_id: str | None = Field(None, alias="assetId")
    bids: list[list[float]] | None = None
    asks: list[list[float]] | None = None


class PolymarketTrade(BaseModel):
    """Trade on Polymarket CLOB."""

    id: str | None = None
    market: str | None = None
    asset_id: str | None = Field(None, alias="assetId")
    price: float | None = None
    size: float | None = None
    side: str | None = None
    timestamp: int | None = None
    maker: str | None = None
    taker: str | None = None


class PolymarketOrder(BaseModel):
    """Order on Polymarket CLOB (legacy fields)."""

    id: str | None = None
    market: str | None = None
    asset_id: str | None = Field(None, alias="assetId")
    side: str | None = None
    price: float | None = None
    size: float | None = None
    status: str | None = None
    owner: str | None = None
    timestamp: int | None = None
    expiration: int | None = None


class PolymarketCLOBOrder(BaseModel):
    """CLOB order schema for GET /orders, GET /orders/{order_id}, POST /order.

    Aligns with CLOB API /order and /book endpoints. Full order lifecycle fields.
    """

    order_id: str | None = Field(None, alias="orderId")
    asset_id: str | None = Field(None, alias="assetId")
    side: str | None = None  # BUY | SELL
    price: str | None = None
    size_matched: str | None = Field(None, alias="sizeMatched")
    size_remaining: str | None = Field(None, alias="sizeRemaining")
    status: str | None = None  # LIVE | MATCHED | CANCELED | DELAYED
    type: str | None = None  # GTC | FOK | GTD
    maker_address: str | None = Field(None, alias="makerAddress")
    outcome: str | None = None  # Yes | No
    market: str | None = None
    owner: str | None = None
    expiration: int | None = None
    created_at: str | None = Field(None, alias="createdAt")
    outcome_index: int | None = Field(None, alias="outcomeIndex")
    associate_trades: list[str] | None = Field(None, alias="associateTrades")


class PolymarketFill(BaseModel):
    """Fill (execution) on Polymarket."""

    id: str | None = None
    order_id: str | None = Field(None, alias="orderId")
    market: str | None = None
    asset_id: str | None = Field(None, alias="assetId")
    price: float | None = None
    size: float | None = None
    side: str | None = None
    timestamp: int | None = None
    fee: float | None = None


class PolymarketMarketResult(BaseModel):
    """Market resolution result on Polymarket."""

    condition_id: str | None = Field(None, alias="conditionId")
    resolution: str | None = None
    winning_outcome: str | None = Field(None, alias="winningOutcome")
    resolution_time: str | None = Field(None, alias="resolutionTime")


class PolymarketError(BaseModel):
    """Polymarket API error response."""

    error: str | None = None
    message: str | None = None
    code: int | None = None

    @classmethod
    def classify(cls, code: int | None = None, error: str | None = None) -> ErrorAction:
        """Map Polymarket error to retry action."""
        if code == 429 or (error and "rate" in (error or "").lower()):
            return ErrorAction.RETRY_WITH_BACKOFF
        if code is not None and code >= 500:
            return ErrorAction.RETRY_WITH_BACKOFF
        if code == 401 or (error and "unauthorized" in (error or "").lower()):
            return ErrorAction.FAIL_HARD
        return ErrorAction.FAIL_HARD


# ---------------------------------------------------------------------------
# Gamma API schemas (market metadata, events, tags, resolution)
# ---------------------------------------------------------------------------


class PolymarketResolutionSource(BaseModel):
    """Resolution source for a Polymarket market.

    Identifies who/what resolves the market (e.g. Reuters, AP, official body).
    """

    name: str | None = None
    url: str | None = None
    description: str | None = None


class PolymarketGammaTag(BaseModel):
    """Tag from Polymarket Gamma API.

    Endpoint: GET gamma-api.polymarket.com/tags

    Note: Polymarket tagging is not structured — tags are free-text and inconsistently
    applied, especially for CYOM (create-your-own-market) markets. Many markets have
    zero tags. Fall back to question text matching when tags are absent.
    """

    id: str | None = None
    slug: str | None = None  # e.g. "crypto", "fed-rate", "nba", "soccer"
    label: str | None = None  # Human-readable name
    description: str | None = None
    force_show_count: bool | None = None
    # Gamma API fields (from live /tags response)
    published_at: str | None = Field(None, alias="publishedAt")
    created_at: str | None = Field(None, alias="createdAt")
    updated_at: str | None = Field(None, alias="updatedAt")
    force_show: bool | None = Field(None, alias="forceShow")
    force_hide: bool | None = Field(None, alias="forceHide")
    is_carousel: bool | None = Field(None, alias="isCarousel")
    requires_translation: bool | None = Field(None, alias="requiresTranslation")


class PolymarketGammaMarket(BaseModel):
    """Full market metadata from Polymarket Gamma API.

    Endpoint: GET gamma-api.polymarket.com/markets
    Query params: ?limit=100&offset=0&active=true&closed=false&tag_slug=crypto

    This is the primary metadata source. CLOB API has trading data but minimal metadata.
    No auth required. Aligns with /markets, /markets/{id}, /markets/slug/{slug}.
    """

    id: str | None = None
    condition_id: str | None = Field(None, alias="conditionId")
    question_id: str | None = Field(None, alias="questionId")
    question: str | None = None
    description: str | None = None
    market_slug: str | None = Field(None, alias="marketSlug")
    outcomes: list[str] | None = None  # e.g. ["Yes", "No"] or ["$0-$100", "$100-$200", ...]
    outcome_prices: list[str] | None = Field(None, alias="outcomePrices")  # string decimals
    clob_token_ids: list[str] | None = Field(None, alias="clobTokenIds")
    market_maker_address: str | None = Field(None, alias="marketMakerAddress")
    best_bid: str | None = Field(None, alias="bestBid")
    best_ask: str | None = Field(None, alias="bestAsk")
    last_trade_price: str | None = Field(None, alias="lastTradePrice")
    spread: str | None = None
    volume_num: float | None = Field(None, alias="volumeNum")
    volume_24hr: float | None = Field(None, alias="volume24hr")
    liquidity_num: float | None = Field(None, alias="liquidityNum")
    # Tags (inconsistently applied; use question text as fallback)
    tags: list[PolymarketGammaTag] | None = None
    # Neg-risk / bucket arb fields
    neg_risk: bool | None = Field(None, alias="negRisk")  # True = part of bucket set
    neg_risk_market_id: str | None = Field(None, alias="negRiskMarketId")
    # Market type
    market_type: str | None = Field(None, alias="marketType")  # binary, categorical, scalar
    # Dates
    start_date: str | None = Field(None, alias="startDate")
    end_date_iso: str | None = Field(None, alias="endDateIso")
    # Status
    active: bool | None = None
    closed: bool | None = None
    archived: bool | None = None
    accepting_orders: bool | None = Field(None, alias="acceptingOrders")
    accepting_order_timestamp: str | None = Field(None, alias="acceptingOrderTimestamp")
    # CLOB info
    minimum_order_size: float | None = Field(None, alias="minimumOrderSize")
    minimum_tick_size: float | None = Field(None, alias="minimumTickSize")
    # Resolution
    resolution_source: str | None = Field(None, alias="resolutionSource")  # URL or name
    resolution_rules: str | None = Field(None, alias="resolutionRules")  # plain text
    uma_resolution_status: str | None = Field(None, alias="umaResolutionStatus")  # proposed|disputed|settled
    winner: str | None = None  # winning outcome after resolution
    # Icon / metadata
    icon: str | None = None
    image: str | None = None
    # Rewards
    rewards: dict[str, object] | None = None


class PolymarketGammaSeries(BaseModel):
    """Series metadata from Polymarket Gamma API (event grouping).

    Events can belong to a series (e.g. NBA daily markets). Nested in Event.series.
    """

    id: str | None = None
    ticker: str | None = None
    slug: str | None = None
    title: str | None = None
    series_type: str | None = Field(None, alias="seriesType")
    recurrence: str | None = None
    image: str | None = None
    icon: str | None = None
    active: bool | None = None
    closed: bool | None = None
    archived: bool | None = None
    new: bool | None = None
    featured: bool | None = None
    restricted: bool | None = None
    published_at: str | None = Field(None, alias="publishedAt")
    created_at: str | None = Field(None, alias="createdAt")
    updated_at: str | None = Field(None, alias="updatedAt")
    created_by: str | None = Field(None, alias="createdBy")
    updated_by: str | None = Field(None, alias="updatedBy")
    comments_enabled: bool | None = Field(None, alias="commentsEnabled")
    competitive: str | None = None
    volume_24hr: float | None = Field(None, alias="volume24hr")
    start_date: str | None = Field(None, alias="startDate")
    comment_count: int | None = Field(None, alias="commentCount")
    requires_translation: bool | None = Field(None, alias="requiresTranslation")


class PolymarketGammaEvent(BaseModel):
    """Event grouping markets from Polymarket Gamma API.

    Endpoint: GET gamma-api.polymarket.com/events
    An event contains one or more markets, typically all related to the same
    real-world occurrence. Questions, outcomes, volumes, resolution metadata.

    Aligns with /events, /events/{id}, /events/slug/{slug} endpoints.
    """

    id: str | None = None
    ticker: str | None = None
    slug: str | None = None
    title: str | None = None
    description: str | None = None
    category: str | None = None  # Crypto, Sports, Politics, Economics, etc.
    sub_category: str | None = Field(None, alias="subCategory")
    resolution_source: str | None = Field(None, alias="resolutionSource")
    start_date: str | None = Field(None, alias="startDate")
    creation_date: str | None = Field(None, alias="creationDate")
    end_date: str | None = Field(None, alias="endDate")
    active: bool | None = None
    closed: bool | None = None
    archived: bool | None = None
    restricted: bool | None = None
    new: bool | None = None
    featured: bool | None = None
    tags: list[PolymarketGammaTag] | None = None
    markets: list[PolymarketGammaMarket] | None = None
    series: list[PolymarketGammaSeries] | None = None
    volume: float | None = None
    liquidity: float | None = None
    open_interest: float | None = Field(None, alias="openInterest")
    sort_by: str | None = Field(None, alias="sortBy")
    published_at: str | None = None
    created_at: str | None = Field(None, alias="createdAt")
    updated_at: str | None = Field(None, alias="updatedAt")
    competitive: int | float | None = None
    volume_24hr: float | None = Field(None, alias="volume24hr")
    volume_1wk: float | None = Field(None, alias="volume1wk")
    volume_1mo: float | None = Field(None, alias="volume1mo")
    volume_1yr: float | None = Field(None, alias="volume1yr")
    liquidity_amm: float | None = Field(None, alias="liquidityAmm")
    liquidity_clob: float | None = Field(None, alias="liquidityClob")
    comment_count: int | None = Field(None, alias="commentCount")
    cyom: bool | None = None
    closed_time: str | None = Field(None, alias="closedTime")
    show_all_outcomes: bool | None = Field(None, alias="showAllOutcomes")
    show_market_images: bool | None = Field(None, alias="showMarketImages")
    enable_neg_risk: bool | None = Field(None, alias="enableNegRisk")
    series_slug: str | None = Field(None, alias="seriesSlug")
    neg_risk_augmented: bool | None = Field(None, alias="negRiskAugmented")
    neg_risk: bool | None = Field(None, alias="negRisk")
    neg_risk_market_id: str | None = Field(None, alias="negRiskMarketId")
    icon: str | None = None
    image: str | None = None


# Type aliases for Gamma API schemas (task naming / documentation)
PolymarketEvent = PolymarketGammaEvent
PolymarketTag = PolymarketGammaTag


class PolymarketNegRiskEvent(BaseModel):
    """Neg-risk multi-outcome event: mutually-exclusive bucket markets.

    All markets share neg_risk_market_id. Exactly one resolves YES.
    Sum of best_bid across markets ≈ 1.0 in efficient market.
    Bucket arb: when sum(YES ask prices) < 1.0, buy all YES = guaranteed profit.
    """

    neg_risk_market_id: str | None = Field(None, alias="negRiskMarketId")
    markets: list[PolymarketGammaMarket] | None = None


class PolymarketResolution(BaseModel):
    """Resolution metadata for Polymarket markets (UMA oracle).

    UMA flow: market closes → proposer submits outcome → 2h dispute window →
    undisputed: auto-settle; disputed: DVM vote (48-72h delay).
    """

    resolution_source: str | None = Field(None, alias="resolutionSource")
    uma_resolution_status: str | None = Field(None, alias="umaResolutionStatus")  # proposed|disputed|settled
    question_id: str | None = Field(None, alias="questionId")
    winner: str | None = None


# ---------------------------------------------------------------------------
# Neg-risk multi-outcome market (bucket arb opportunity)
# ---------------------------------------------------------------------------


class NegRiskOutcome(BaseModel):
    """Single outcome bucket in a neg-risk multi-outcome market."""

    label: str  # e.g. "Gold above $3200", "Gold $3000-$3200"
    token_id: str | None = None  # CLOB token ID for YES outcome
    condition_id: str | None = None
    price: float | None = None  # Current YES ask price (implied probability)
    liquidity: float | None = None


class PolymarketNegRiskMarket(BaseModel):
    """Mutually-exclusive multi-outcome market (neg-risk structure).

    All outcomes share neg_risk_market_id. Exactly one outcome resolves YES;
    all others resolve NO. Sum of all YES prices ≈ 1.0 in efficient market.

    Bucket arb: When sum(YES ask prices) < 1.0, buying all YES outcomes is
    risk-free (guarantees $1 payout per $sum_of_asks spent). Lock-up until expiry.

    To find arb: group Gamma markets by neg_risk_market_id, fetch CLOB ask prices
    for each YES token, compute sum(asks). If sum < 1.0 → signal.
    """

    neg_risk_market_id: str
    question_stem: str | None = None  # The common question (e.g. "Where will gold be on June 30?")
    underlying: str | None = None  # e.g. "GOLD", "BTC", "SPX"
    expiry: str | None = None
    outcomes: list[NegRiskOutcome]
    sum_yes_prices: float | None = None  # Computed: sum of outcome prices
    active: bool | None = None
    resolved: bool | None = None
    winning_outcome: str | None = None  # label of resolved outcome


# ---------------------------------------------------------------------------
# AMM-era schemas (pre-November 2022)
# Pre-CLOB Polymarket used an AMM model. No price series exist.
# Only on-chain split/merge events (capital flow proxies) are available.
# Source: Polymarket Activity subgraph (Goldsky GraphQL)
# ---------------------------------------------------------------------------


class PolymarketSplit(BaseModel):
    """AMM-era split event: user deposits USDC and receives YES+NO tokens.

    Equivalent to 'bet placed' in pre-CLOB era.
    Source: The Graph / Goldsky subgraph entity 'splits'
    Available: June 2021 - November 2022 (AMM era only)
    """

    id: str | None = None
    timestamp: int | None = None  # Unix timestamp
    condition_id: str | None = Field(None, alias="conditionId")
    amount: str | None = None  # USDC amount (18 decimals, divide by 1e6 for human)
    position_id: str | None = Field(None, alias="positionId")
    user: str | None = None  # Wallet address


class PolymarketMerge(BaseModel):
    """AMM-era merge event: user redeems YES+NO tokens back for USDC.

    Equivalent to 'position closed' in pre-CLOB era.
    Source: The Graph / Goldsky subgraph entity 'merges'
    """

    id: str | None = None
    timestamp: int | None = None
    condition_id: str | None = Field(None, alias="conditionId")
    amount: str | None = None  # USDC amount
    position_id: str | None = Field(None, alias="positionId")
    user: str | None = None


# ---------------------------------------------------------------------------
# CLOB authentication schemas
# ---------------------------------------------------------------------------


class PolymarketL1AuthParams(BaseModel):
    """L1 authentication parameters for Polymarket CLOB API.

    L1 auth is one-time: sign an EIP-712 message with your wallet private key
    to derive reusable CLOB API credentials. Only needed once per session.

    Endpoint: POST clob.polymarket.com/auth/derive-api-key
    """

    wallet_address: str  # Ethereum wallet address (checksum)
    signature: str  # EIP-712 signature of the auth message
    nonce: str | None = None
    timestamp: str | None = None  # Unix timestamp of signature


class PolymarketL2Headers(BaseModel):
    """L2 HMAC-SHA256 authentication headers for Polymarket CLOB trading requests.

    Required on all authenticated CLOB endpoints (order placement, fills, positions).
    Generated per-request from the CLOB API key derived via L1 auth.

    Headers sent:
      POLY_ADDRESS: wallet address
      POLY_SIGNATURE: HMAC-SHA256 of request body
      POLY_TIMESTAMP: Unix timestamp
      POLY_NONCE: random nonce
    """

    poly_address: str = Field(..., alias="POLY_ADDRESS")
    poly_signature: str = Field(..., alias="POLY_SIGNATURE")
    poly_timestamp: str = Field(..., alias="POLY_TIMESTAMP")
    poly_nonce: str = Field(..., alias="POLY_NONCE")


# ---------------------------------------------------------------------------
# Price history (CLOB era only)
# ---------------------------------------------------------------------------


class PolymarketPricePoint(BaseModel):
    """Single price data point from CLOB history.

    Price is a probability (0.0-1.0) representing the implied probability
    that the YES outcome will resolve.
    token1 = YES outcome, token2 = NO outcome (nonusdc_side field in trade data).
    """

    t: int | None = None  # Unix timestamp (seconds)
    p: float | None = None  # Price / implied probability (0.0-1.0)


class PolymarketPriceHistory(BaseModel):
    """Price history for a single outcome token.

    Endpoint: GET clob.polymarket.com/prices-history?market={token_id}&interval=max&fidelity=60
    Available: November 21, 2022 (CLOB launch) onwards.
    No auth required for public price history.

    To get both YES and NO probabilities: query both token IDs for the market.
    YES + NO prices should sum to ≈1.0 at any given timestamp.
    """

    token_id: str | None = None
    history: list[PolymarketPricePoint] | None = None
