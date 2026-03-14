"""Cross-venue prediction market arbitrage signal schemas.

Two primary arb patterns:
1. Neg-risk bucket arb (Polymarket-specific): Multiple mutually-exclusive outcome
   markets on the same underlying share a neg_risk_market_id. If sum(YES ask prices)
   < 1.0, buying all YES outcomes guarantees profit on resolution. Lock-up period
   is until market expiry.

   Example (gold June futures ranges):
     "Gold above $3200?"     ask = 0.31
     "Gold $3000-$3200?"     ask = 0.29
     "Gold $2800-$3000?"     ask = 0.22
     "Gold $2600-$2800?"     ask = 0.08
     "Gold below $2600?"     ask = 0.04
     ─────────────────────────────────
     Sum of asks             = 0.94  ← buy all YES, guaranteed 6¢ per $1 at resolution

2. Cross-venue same-event arb (Kalshi vs Polymarket vs sports books): The same event
   trades on multiple venues at different implied probabilities. Buy YES on the cheaper
   venue, sell NO (or buy NO) on the more expensive venue.
"""

from __future__ import annotations

__api_version__ = "v2"  # matches provider_api_versions.yaml

from decimal import Decimal
from typing import Literal

from pydantic import AwareDatetime, BaseModel

# ---------------------------------------------------------------------------
# 3.1 Direct Same-Market Arb (Kalshi vs Polymarket)
# ---------------------------------------------------------------------------


class CrossVenueLink(BaseModel):
    """Direct link between semantically equivalent markets on two venues.

    Both venues may list markets on identical events (Fed rate, CPI, BTC price).
    Price discrepancy = arb opportunity.
    """

    venue_a: Literal["kalshi", "polymarket", "manifold", "metaculus"]
    market_id_a: str
    venue_b: str
    market_id_b: str
    link_type: Literal["identical", "equivalent", "related", "correlated"]
    basis_bps: Decimal  # Current price difference in basis points
    verified_by: str  # "manual" | "nlp_similarity" | "structured_match"
    created_at: AwareDatetime


# ---------------------------------------------------------------------------
# 3.2 Probability-Bucket Arb (The Gold Pattern)
# ---------------------------------------------------------------------------


class BucketMarket(BaseModel):
    """Single bucket market in a probability-bucket arb group.

    Multiple binary markets on the same underlying cover non-overlapping,
    exhaustive ranges. If sum(yes_ask) < 1.0, buy all YES = guaranteed profit.
    """

    market_id: str
    lower_bound: Decimal | None = None  # None = negative infinity
    upper_bound: Decimal | None = None  # None = positive infinity
    include_lower: bool = True
    include_upper: bool = True
    yes_bid: Decimal
    yes_ask: Decimal
    no_bid: Decimal | None = None
    no_ask: Decimal | None = None


class ProbabilityBucket(BaseModel):
    """Group of bucket markets on same underlying with exhaustive ranges.

    Example: Gold June 30 price prediction markets — 5 buckets covering
    full distribution. If sum(asks) < 1.0, arb exists.
    """

    group_id: str
    underlying: str  # e.g. "GOLD_JUNE_2025"
    expiry: str  # ISO 8601 date or datetime
    venue: str
    buckets: list[BucketMarket]


# ---------------------------------------------------------------------------
# 3.3 Sports Book Cross-Venue Arb
# ---------------------------------------------------------------------------


class SportsbookLink(BaseModel):
    """Polymarket vs traditional sports book price comparison.

    Polymarket often mispriced vs books due to UMA resolution delay,
    no vig on individual markets, and liquidity provider discount.
    """

    polymarket_market_id: str
    sportsbook: str  # "pinnacle", "draftkings", "betfair"
    sportsbook_event_id: str
    sportsbook_market_type: str  # "moneyline", "spread", "total"
    sportsbook_implied_prob: Decimal
    polymarket_yes_mid: Decimal
    discrepancy_bps: Decimal
    captured_at: AwareDatetime


# ---------------------------------------------------------------------------
# Neg-Risk Bucket Arb (Polymarket-specific)
# ---------------------------------------------------------------------------


class NegRiskBucket(BaseModel):
    """Single bucket in a neg-risk multi-outcome market."""

    label: str  # e.g. "Gold above $3200"
    range_description: str | None = None  # e.g. "> $3200"
    token_id: str | None = None  # Polymarket CLOB token ID for YES outcome
    condition_id: str | None = None
    yes_ask: Decimal | None = None  # Current ask price (implied probability, 0-1)
    yes_bid: Decimal | None = None
    liquidity_usd: Decimal | None = None


class NegRiskArbSignal(BaseModel):
    """Probability bucket arbitrage: sum(YES asks) < 1.0 across mutually-exclusive outcomes.

    Detectable pattern: find Polymarket neg_risk_market_id groups where all buckets
    cover the real line (ranges are exhaustive and mutually exclusive), then check if
    sum(ask) < 1.0. Profit is locked up until market resolution.

    To detect: query Gamma API for markets with same neg_risk_market_id, verify ranges
    cover full distribution, compute sum(best_ask for each YES token).
    """

    neg_risk_market_id: str
    underlying: str  # e.g. "GOLD_JUN2025", "BTC_DEC2025"
    event_description: str | None = None  # e.g. "Gold price on June 30, 2025"
    expiry: str  # ISO 8601 date or datetime
    venue: str = "polymarket"
    buckets: list[NegRiskBucket]
    sum_of_asks: Decimal  # Sum of all YES ask prices; < 1.0 = arb exists
    yes_ask_sum: Decimal | None = None  # Alias for sum_of_asks; (1.0 - yes_ask_sum) * 10000 = arb_bps
    no_bid_sum: Decimal | None = None  # Sum of NO bid prices; = 1 - yes_ask_sum at fair value
    arb_bps: Decimal | None = None  # (1.0 - yes_ask_sum) * 10000
    bucket_markets: list[str] | None = None  # condition_ids or market IDs in the group
    capital_required_usdc: Decimal | None = None  # Capital needed to buy all buckets
    expected_profit_usdc: Decimal | None = None  # Expected profit at resolution
    implied_profit_pct: Decimal  # (1.0 - sum_of_asks) * 100
    estimated_capital_usd: Decimal | None = None  # Capital needed; prefer capital_required_usdc
    requires_lock_up_days: int | None = None  # Days until market resolution
    is_exhaustive: bool | None = None  # Whether ranges provably cover the full distribution
    detected_at: str | None = None  # ISO 8601 timestamp when signal was detected


class CrossVenueArbLeg(BaseModel):
    """Single leg of a cross-venue arbitrage."""

    venue: str  # "kalshi", "polymarket", "pinnacle", "betfair"
    side: str  # "yes_buy", "no_buy", "back", "lay"
    price: Decimal  # Ask price (probability) for the action
    market_ticker: str | None = None  # Kalshi ticker
    condition_id: str | None = None  # Polymarket condition_id
    event_id: str | None = None  # Sports book event ID
    liquidity_usd: Decimal | None = None


class CrossVenueArbSignal(BaseModel):
    """Arbitrage opportunity: same event trading at different probabilities across venues.

    Example: Fed raises 25bps in November
      Kalshi   YES ask = 0.62  (buy YES here)
      Polymarket NO ask = 0.34  (buy NO here = implied prob of YES = 0.66)
      Net cost = 0.62 + 0.34 = 0.96 → guaranteed $1 payout → 4% profit

    Example: NBA Finals arb (Polymarket vs Pinnacle):
      Polymarket Lakers YES ask = 0.45
      Pinnacle Lakers moneyline implied prob = 0.40
      → Polymarket overpriced vs Pinnacle; buy NO on Polymarket, back on Pinnacle
    """

    event_description: str
    underlying_category: str | None = None  # "fed_rate", "sports_nba", "crypto_btc", "politics_us"
    expiry: str | None = None
    legs: list[CrossVenueArbLeg]
    total_cost: Decimal  # Sum of leg costs; < 1.0 = guaranteed profit
    implied_profit_pct: Decimal  # (1.0 - total_cost) * 100
    requires_lock_up_days: int | None = None
    detected_at: str | None = None
    notes: str | None = None  # e.g. "Lock-up ~60 days for June gold futures resolution"


class PredictionMarketUniverse(BaseModel):
    """Metadata describing a prediction market across venues.

    Used to group the same real-world event across Kalshi, Polymarket, and sports books
    so arb detection can find matching markets programmatically.
    """

    event_description: str
    category: str  # "economics", "finance", "sports", "politics"
    sub_category: str | None = None  # "fed_rate", "cpi", "nba_finals", "us_election"
    underlying: str | None = None  # "BTC", "GOLD", "SPX", "FED_FUNDS_RATE"
    expiry: str | None = None
    kalshi_event_ticker: str | None = None
    kalshi_market_tickers: list[str] | None = None
    polymarket_condition_ids: list[str] | None = None
    polymarket_neg_risk_market_id: str | None = None
    betfair_event_id: str | None = None
    pinnacle_event_id: str | None = None
    notes: str | None = None  # e.g. "Kalshi markets daily; Polymarket has monthly buckets"
