"""Risk type taxonomy — all risk dimensions across strategy types.

External venues provide data for many of these (Deribit: delta/gamma/vega/theta,
exchanges: funding rates). Schema lives in UAC because external sources report on
these dimensions. Internal computation uses the same enum.
"""

from __future__ import annotations

from enum import StrEnum


class RiskType(StrEnum):
    """Comprehensive risk dimension taxonomy."""

    # First order — direct price/rate sensitivities
    DELTA = "delta"
    VEGA = "vega"
    THETA = "theta"
    RHO = "rho"
    FUNDING = "funding"
    BASIS = "basis"
    CARRY = "carry"
    FX = "fx"
    LIQUIDITY = "liquidity"
    # Second order — higher-order sensitivities
    GAMMA = "gamma"
    VOLGA = "volga"
    VANNA = "vanna"
    SLIDE = "slide"
    # Structural — portfolio/position structure risks
    DURATION = "duration"
    CONVEXITY = "convexity"
    SPREAD = "spread"
    CONCENTRATION = "concentration"
    # Operational — infrastructure risks
    VENUE_PROTOCOL = "venue_protocol"
    CORRELATION = "correlation"
    # Domain-specific
    EDGE_DECAY = "edge_decay"
    MARKET_SUSPENSION = "market_suspension"
    PROTOCOL_RISK = "protocol_risk"
    IMPERMANENT_LOSS = "impermanent_loss"
    # DeFi-specific
    ORACLE_DEPEG = "oracle_depeg"
    STABLECOIN_DEPEG = "stablecoin_depeg"
    BORROW_RATE_SPREAD = "borrow_rate_spread"
    WITHDRAWAL_DELAY = "withdrawal_delay"
    EMERGENCY_CLOSE_COST = "emergency_close_cost"
    REBALANCE_COST = "rebalance_cost"
    # Share class / currency
    BASE_CURRENCY_DRIFT = "base_currency_drift"
    MARGIN_CURRENCY_MISMATCH = "margin_currency_mismatch"


class RiskCategory(StrEnum):
    """Groups RiskTypes for UI display."""

    FIRST_ORDER = "first_order"
    SECOND_ORDER = "second_order"
    STRUCTURAL = "structural"
    OPERATIONAL = "operational"
    DOMAIN_SPECIFIC = "domain_specific"


RISK_TYPE_CATEGORIES: dict[RiskCategory, list[RiskType]] = {
    RiskCategory.FIRST_ORDER: [
        RiskType.DELTA,
        RiskType.VEGA,
        RiskType.THETA,
        RiskType.RHO,
        RiskType.FUNDING,
        RiskType.BASIS,
        RiskType.CARRY,
        RiskType.FX,
        RiskType.LIQUIDITY,
    ],
    RiskCategory.SECOND_ORDER: [
        RiskType.GAMMA,
        RiskType.VOLGA,
        RiskType.VANNA,
        RiskType.SLIDE,
    ],
    RiskCategory.STRUCTURAL: [
        RiskType.DURATION,
        RiskType.CONVEXITY,
        RiskType.SPREAD,
        RiskType.CONCENTRATION,
    ],
    RiskCategory.OPERATIONAL: [
        RiskType.VENUE_PROTOCOL,
        RiskType.CORRELATION,
    ],
    RiskCategory.DOMAIN_SPECIFIC: [
        RiskType.EDGE_DECAY,
        RiskType.MARKET_SUSPENSION,
        RiskType.PROTOCOL_RISK,
        RiskType.IMPERMANENT_LOSS,
        RiskType.ORACLE_DEPEG,
        RiskType.STABLECOIN_DEPEG,
        RiskType.BORROW_RATE_SPREAD,
        RiskType.WITHDRAWAL_DELAY,
        RiskType.EMERGENCY_CLOSE_COST,
        RiskType.REBALANCE_COST,
        RiskType.BASE_CURRENCY_DRIFT,
        RiskType.MARGIN_CURRENCY_MISMATCH,
    ],
}
