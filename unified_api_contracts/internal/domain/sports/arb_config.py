"""Sports arbitrage strategy configuration and venue balance schemas.

ArbitrageStrategyConfig: controls arb detection, sizing, and venue allocation.
VenueBalance: per-bookmaker/exchange capital tracking.
VenueAllocationWeights: rolling-window venue allocation (written to GCS daily).

These schemas are consumed by:
  - strategy-service: ArbitrageStrategy reads config + weights
  - position-balance-monitor-service: tracks VenueBalance per venue
  - execution-service: checks available balance before placing bets
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ArbitrageStrategyConfig(BaseModel):
    """Configuration for sports arbitrage strategy.

    Stored in strategy-service config. Window and sizing params are
    tunable without code changes.
    """

    # Screening
    min_expected_net_arb_pct: float = Field(
        default=0.3,
        description="Minimum expected net arb % after commission to place bet",
    )
    max_odds: float = Field(
        default=50.0,
        description="Reject individual legs with odds above this (likely stale/erroneous)",
    )

    # Sizing
    bet_size_pct_of_venue_balance: float = Field(
        default=25.0,
        description="Max % of venue available balance per arb leg. 25% = reserve for ~4 concurrent bets.",
    )
    max_total_exposure_pct: float = Field(
        default=80.0,
        description="Max % of total bankroll deployed at any time across all venues.",
    )

    # Venue allocation
    venue_allocation_window_days: int = Field(
        default=7,
        description="Rolling window (days) for adaptive venue allocation. "
        "Weights computed from arb frequency in this window. "
        "Use 3 for testing with limited data, 7-30 for production.",
    )
    exchange_allocation_discount: float = Field(
        default=0.6,
        description="Exchanges accumulate capital from arb wins, so allocate less. "
        "0.6 = 60% of proportional weight. Bookmakers get 1.4x (they drain).",
    )

    # Commission
    exchange_commission_rate: float = Field(
        default=0.02,
        description="Exchange commission on net winnings (Betfair = 2%).",
    )

    # Transfer constraints
    allow_intraday_transfers: bool = Field(
        default=False,
        description="Whether capital can move between venues within the same day. "
        "False = realistic (transfers take hours/days).",
    )

    # Markets
    enable_3way_arb: bool = Field(default=True, description="Enable h2h 3-way arb detection")
    enable_back_lay_arb: bool = Field(default=True, description="Enable back-lay arb (exchange lay vs bookmaker back)")
    enable_totals_arb: bool = Field(default=True, description="Enable Over/Under arb detection")
    enable_spreads_arb: bool = Field(default=False, description="Enable Asian handicap arb (less liquid)")

    # Backtest / execution simulation
    simulate_execution_lag: bool = Field(
        default=False,
        description="If True, detect arb at snapshot T but execute at T+1 prices. "
        "Both bookmakers must have fresh bm_time at T+1. Backtest toggle.",
    )
    track_missed_opportunities: bool = Field(
        default=True,
        description="Track which venue was the bottleneck when an arb is skipped due to capital.",
    )
    execution_order: str = Field(
        default="exchange_first",
        description="Which leg to place first: 'exchange_first' (recommended — exchanges lag, "
        "capture generous price before correction) or 'bookmaker_first'.",
    )


class VenueBalance(BaseModel):
    """Per-venue capital state. Tracked by position-balance-monitor-service.

    Written to GCS daily:
      position-store-sports-{project}/venue_balances/day={date}/balances.parquet
    """

    venue: str = Field(description="Bookmaker or exchange key (e.g., betfair_ex_uk, pinnacle)")
    is_exchange: bool = Field(default=False, description="True for exchanges (Betfair, Matchbook, etc.)")
    balance: float = Field(default=0.0, description="Current total balance at this venue")
    available: float = Field(default=0.0, description="Balance minus locked (available for new bets)")
    locked: float = Field(default=0.0, description="Capital locked in unsettled bets")
    total_deposited: float = Field(default=0.0, description="Cumulative deposits to this venue")
    total_withdrawn: float = Field(default=0.0, description="Cumulative withdrawals from this venue")
    total_won: float = Field(default=0.0, description="Cumulative net winnings at this venue")
    total_lost: float = Field(default=0.0, description="Cumulative losses at this venue")
    total_fees: float = Field(default=0.0, description="Cumulative commission/fees paid at this venue")
    bets_placed: int = Field(default=0, description="Total bets placed at this venue")
    bets_settled: int = Field(default=0, description="Total bets settled at this venue")


class VenueAllocationWeights(BaseModel):
    """Rolling-window venue allocation weights. Written to GCS daily by strategy-service.

    GCS path:
      strategy-store-sports-{project}/venue_allocation/day={date}/weights.parquet

    Read at start of each trading day to redistribute capital.
    Computed from arb frequency in the last N days (no lookahead).
    """

    venue: str = Field(description="Venue key")
    weight: float = Field(description="Proportional weight [0, 1]. All weights sum to 1.")
    raw_frequency: int = Field(default=0, description="Arb leg appearances in rolling window")
    capital_flow_direction: str = Field(
        default="neutral",
        description="'accumulates' (exchange) or 'drains' (bookmaker) or 'neutral'",
    )
    adjusted_weight: float = Field(
        default=0.0,
        description="Weight after flow adjustment (exchanges discounted, bookmakers boosted)",
    )


class VenueLedgerEntry(BaseModel):
    """Per-venue capital ledger entry. Separates transfers from trading P&L.

    Used by position-balance-monitor-service VenueBalanceTracker.get_ledger()
    to provide a clear breakdown of where capital came from / went.
    """

    venue: str = Field(description="Bookmaker or exchange key")
    initial_deposit: float = Field(default=0.0, description="First deposit to this venue")
    transfers_in: float = Field(default=0.0, description="Capital transferred in from other venues")
    transfers_out: float = Field(default=0.0, description="Capital transferred out to other venues")
    trading_pnl: float = Field(default=0.0, description="Net P&L from settled bets (won - lost - fees)")
    balance: float = Field(default=0.0, description="Current total balance (should equal initial + in - out + pnl)")


# Exchange venue registry — venues that charge commission on net winnings
EXCHANGE_VENUES: frozenset[str] = frozenset(
    {
        "betfair_ex_uk",
        "betfair_ex_eu",
        "betfair_ex_au",
        "matchbook",
    }
)

# Per-exchange commission rates (default 2%)
EXCHANGE_COMMISSION_RATES: dict[str, float] = {
    "betfair_ex_uk": 0.02,
    "betfair_ex_eu": 0.02,
    "betfair_ex_au": 0.02,
    "matchbook": 0.015,  # 1.5%
}

# Bookmaker operator groups — same company, different regional skins.
# Arbs between venues in the same group are not real (same operator).
# Strategy must ensure arb legs come from DIFFERENT groups.
VENUE_OPERATOR_GROUPS: dict[str, str] = {
    "betfair_ex_uk": "BETFAIR",
    "betfair_ex_eu": "BETFAIR",
    "betfair_ex_au": "BETFAIR",
    "betfair_sb_uk": "BETFAIR_SB",
    "unibet": "UNIBET",
    "unibet_uk": "UNIBET",
    "unibet_fr": "UNIBET",
    "unibet_nl": "UNIBET",
    "unibet_se": "UNIBET",
    "leovegas": "LEOVEGAS",
    "leovegas_se": "LEOVEGAS",
    "ladbrokes_uk": "LADBROKES",
    "ladbrokes_au": "LADBROKES",
    "williamhill": "WILLIAMHILL",
    "williamhill_us": "WILLIAMHILL",
    "winamax_fr": "WINAMAX",
    "winamax_de": "WINAMAX",
}


def get_operator(venue: str) -> str:
    """Get the operator group for a venue. Ungrouped venues are their own operator."""
    return VENUE_OPERATOR_GROUPS.get(venue, venue)


def arb_legs_are_independent(venues: list[str]) -> bool:
    """Check that all arb legs come from different operators.

    Returns False if two legs are from the same group
    (e.g., betfair_ex_uk and betfair_ex_eu are both BETFAIR).
    """
    operators = [get_operator(v) for v in venues]
    return len(operators) == len(set(operators))
