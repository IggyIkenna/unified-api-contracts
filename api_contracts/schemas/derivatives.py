"""Derivatives market data schemas: futures, options, funding rates, liquidations."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal


@dataclass
class FundingRate:
    venue: str
    symbol: str
    rate: Decimal
    timestamp: datetime
    next_funding_time: datetime | None = None
    predicted_rate: Decimal | None = None


@dataclass
class Liquidation:
    venue: str
    symbol: str
    side: str  # "buy" | "sell"
    quantity: Decimal
    price: Decimal
    timestamp: datetime
    order_type: str = "market"


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
