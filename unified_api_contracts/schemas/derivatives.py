"""Derivatives market data schemas: futures, options, funding rates, liquidations.

DEPRECATION NOTICE
------------------
``FundingRate`` and ``Liquidation`` @dataclasses in this module are **deprecated**.

- ``FundingRate`` → use :class:`unified_api_contracts.unified_normalised_contracts.domain.CanonicalFundingRate`
  (Pydantic BaseModel, normalized, produced by UAC normalizers).
  Note: ``next_funding_time`` was renamed to ``next_funding_timestamp`` in the canonical schema.
- ``Liquidation`` → use :class:`unified_api_contracts.unified_normalised_contracts.domain.CanonicalLiquidation`
  (Pydantic BaseModel, normalized, produced by UAC liquidation normalizers).

These raw @dataclasses are not produced by any normalizer and have divergent field names
from the canonical layer. They will be removed in a future release.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field


@dataclass
class FundingRate:
    """DEPRECATED: Use CanonicalFundingRate from unified_normalised_contracts.domain instead.

    This raw @dataclass has divergent field names (next_funding_time vs
    next_funding_timestamp in canonical) and is not produced by any normalizer.
    """

    venue: str
    symbol: str
    rate: Decimal
    timestamp: datetime
    next_funding_time: datetime | None = None
    predicted_rate: Decimal | None = None

    def __post_init__(self) -> None:
        _msg = (
            "FundingRate @dataclass is deprecated. "
            "Use CanonicalFundingRate from unified_normalised_contracts.domain instead."
        )
        warnings.warn(_msg, DeprecationWarning, stacklevel=2)


@dataclass
class Liquidation:
    """DEPRECATED: Use CanonicalLiquidation from unified_normalised_contracts.domain instead.

    This raw @dataclass has divergent field names and is not produced by any normalizer.
    """

    venue: str
    symbol: str
    side: str  # "buy" | "sell"
    quantity: Decimal
    price: Decimal
    timestamp: datetime
    order_type: str = "market"

    def __post_init__(self) -> None:
        _msg = (
            "Liquidation @dataclass is deprecated. "
            "Use CanonicalLiquidation from unified_normalised_contracts.domain instead."
        )
        warnings.warn(_msg, DeprecationWarning, stacklevel=2)


@dataclass
class SettlementPrice:
    venue: str
    symbol: str
    price: Decimal
    settlement_time: datetime
    contract_type: str = "perpetual"  # "perpetual" | "quarterly" | "monthly"


@dataclass
class OptionsChain:
    venue: str
    underlying: str
    expiry: datetime
    strikes: list[Decimal] = field(default_factory=list)
    calls: dict[str, OptionContract] = field(default_factory=dict)
    puts: dict[str, OptionContract] = field(default_factory=dict)
    timestamp: datetime | None = None


@dataclass
class OptionContract:
    strike: Decimal
    option_type: str  # "call" | "put"
    bid: Decimal | None
    ask: Decimal | None
    last: Decimal | None
    volume: Decimal | None
    open_interest: Decimal | None
    implied_volatility: Decimal | None
    greeks: OptionGreeks | None = None


@dataclass
class OptionGreeks:
    delta: Decimal | None = None
    gamma: Decimal | None = None
    theta: Decimal | None = None
    vega: Decimal | None = None
    rho: Decimal | None = None
    vanna: Decimal | None = None  # dDelta/dIV — delta sensitivity to implied vol moves
    volga: Decimal | None = None  # dVega/dIV — vega sensitivity to implied vol (vol-of-vol risk)


# =============================================================================
# Pydantic models (API contracts for institutional derivatives)
# =============================================================================


class PositionRisk(BaseModel):
    """Position risk metrics."""

    liquidationPrice: Decimal | None = Field(None, description="Liquidation price")
    bankruptcyPrice: Decimal | None = Field(None, description="Bankruptcy price")
    maintenanceMarginRate: Decimal | None = Field(None, description="Maintenance margin rate")
    initialMarginRate: Decimal | None = Field(None, description="Initial margin rate")
    marginRatio: Decimal | None = Field(None, description="Current margin ratio")
    adlRank: int | None = Field(None, description="Auto-deleveraging rank")
    riskTier: int | None = Field(None, description="Risk tier")


class InsuranceFundState(BaseModel):
    """Insurance fund state snapshot."""

    asset: str = Field(..., description="Asset symbol")
    amount: Decimal = Field(..., description="Fund amount")
    timestamp: datetime = Field(..., description="Snapshot timestamp")


class LongShortRatio(BaseModel):
    """Long/short ratio aggregate."""

    longShortRatio: Decimal = Field(..., description="Ratio of long to short")
    longAccount: Decimal = Field(..., description="Long account proportion")
    shortAccount: Decimal = Field(..., description="Short account proportion")


class OpenInterestHistory(BaseModel):
    """Open interest history point."""

    symbol: str = Field(..., description="Instrument symbol")
    timestamp: datetime = Field(..., description="Snapshot timestamp")
    openInterest: Decimal = Field(..., description="Open interest value")


class FundingRateHistory(BaseModel):
    """Funding rate history point."""

    fundingTime: datetime = Field(..., description="Funding timestamp")
    rate: Decimal = Field(..., description="Funding rate")
    markPrice: Decimal | None = Field(None, description="Mark price at funding")
    indexPrice: Decimal | None = Field(None, description="Index price at funding")


class SettlementEvent(BaseModel):
    """Settlement event record."""

    instrument: str = Field(..., description="Instrument symbol")
    settlementPrice: Decimal = Field(..., description="Settlement price")
    deliveryTime: datetime = Field(..., description="Delivery/settlement time")
    cashFlow: Decimal | None = Field(None, description="Cash flow amount")
    fee: Decimal | None = Field(None, description="Settlement fee")


# --- Options volatility surface ---


class VolSmilePoint(BaseModel):
    """Single point on volatility smile (strike vs IV)."""

    strike: Decimal = Field(..., description="Strike price")
    impliedVol: Decimal = Field(..., description="Implied volatility")


class VolSurfaceSlice(BaseModel):
    """Volatility smile at a single expiry."""

    expiry: datetime = Field(..., description="Expiry timestamp")
    points: list[VolSmilePoint] = Field(default_factory=list, description="Strike/IV points")


class VolTermStructure(BaseModel):
    """Volatility term structure (expiry vs ATM IV)."""

    expiry: datetime = Field(..., description="Expiry timestamp")
    atmVol: Decimal = Field(..., description="At-the-money implied volatility")


class VolSurface(BaseModel):
    """Full volatility surface (smile + term structure)."""

    symbol: str = Field(..., description="Underlying symbol")
    timestamp: datetime = Field(..., description="Snapshot timestamp")
    slices: list[VolSurfaceSlice] = Field(default_factory=list, description="Smile slices per expiry")
    termStructure: list[VolTermStructure] = Field(default_factory=list, description="Term structure")


# ---------------------------------------------------------------------------
# Multi-leg combo instrument schemas (cross-venue canonical)
# ---------------------------------------------------------------------------


class ComboStrategyType(StrEnum):
    """Named options/futures spread strategy types."""

    CALENDAR_SPREAD = "calendar_spread"  # same underlying, different expiries
    RISK_REVERSAL = "risk_reversal"  # buy call + sell put (same expiry)
    STRADDLE = "straddle"  # buy call + buy put (same strike/expiry)
    STRANGLE = "strangle"  # buy OTM call + buy OTM put
    BUTTERFLY = "butterfly"  # 3-leg: buy 1 + sell 2 + buy 1
    CONDOR = "condor"  # 4-leg: bull spread + bear spread
    BULL_CALL_SPREAD = "bull_call_spread"  # buy lower strike call + sell higher
    BEAR_PUT_SPREAD = "bear_put_spread"  # buy higher strike put + sell lower
    EFP = "efp"  # Exchange for Physical (IBKR): futures vs basket
    CUSTOM = "custom"  # arbitrary legs (e.g. Deribit block trade)


class ComboLeg(BaseModel):
    """Single leg of a multi-leg instrument (venue-agnostic).

    Maps to: DeribitComboLeg, IBKRComboLeg, OKXRfqLeg
    """

    instrument_id: str  # Venue-specific instrument identifier
    direction: str  # "buy" | "sell"
    ratio: int = 1  # Quantity multiplier (1 for equal-weighted legs)
    venue: str | None = None  # For cross-venue combos


class MultiLegInstrument(BaseModel):
    """Normalized multi-leg/combo instrument (cross-venue canonical).

    Maps to venue-specific types:
    - Deribit: DeribitComboInstrument (kind=future_combo/option_combo)
    - IBKR: IBKRComboContract (secType=BAG)
    - OKX: OKXRfqCreateRequest (multi-leg via RFQ system)
    - Binance: No native combo; use separate legs
    """

    combo_id: str | None = None  # Venue-assigned combo identifier
    venue: str  # Primary venue
    strategy_type: ComboStrategyType | None = None
    underlying: str | None = None  # e.g. "BTC", "ETH", "SPX"
    legs: list[ComboLeg]
    block_trade_only: bool = False  # True = OTC/institutional block trade required
    description: str | None = None  # Human-readable e.g. "BTC JUN/SEP calendar spread"
    timestamp: datetime | None = None  # When this combo was created/observed


class ComboQuote(BaseModel):
    """Unified combo price + net greeks (cross-venue).

    Net price = sum of (leg_price x direction_sign x ratio).
    Net greeks = sum of per-leg greeks weighted by direction and ratio.
    """

    combo_id: str
    venue: str
    net_price: Decimal | None = None  # Net debit (positive) or credit (negative)
    bid: Decimal | None = None  # Best bid for the combo as a unit
    ask: Decimal | None = None  # Best ask for the combo as a unit
    net_delta: Decimal | None = None  # Net portfolio delta
    net_gamma: Decimal | None = None
    net_vega: Decimal | None = None
    net_theta: Decimal | None = None
    timestamp: datetime | None = None
