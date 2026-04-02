"""Venue collateral acceptance matrix — which tokens each venue accepts as margin."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class CollateralAcceptance:
    """A single venue-token collateral acceptance entry."""

    venue: str
    token: str
    accepted: bool
    haircut_pct: Decimal | None
    margin_type: str
    notes: str


VENUE_COLLATERAL_MATRIX: list[CollateralAcceptance] = [
    # HyperLiquid — USDC only
    CollateralAcceptance("HYPERLIQUID", "USDC", True, Decimal("0"), "CROSS", "Only accepted margin"),
    CollateralAcceptance("HYPERLIQUID", "ETH", False, None, "", "Not accepted"),
    CollateralAcceptance("HYPERLIQUID", "weETH", False, None, "", "Not accepted"),
    CollateralAcceptance("HYPERLIQUID", "WETH", False, None, "", "Not accepted"),
    # Aster
    CollateralAcceptance("ASTER", "USDC", True, Decimal("0"), "CROSS", "Primary margin"),
    CollateralAcceptance("ASTER", "USDT", True, Decimal("0.01"), "CROSS", "Slight haircut"),
    # Aave V3 (referencing defi_reserve_params.py LTV values)
    CollateralAcceptance("AAVEV3-ETHEREUM", "WETH", True, Decimal("0.175"), "ISOLATED", "LTV 82.5%"),
    CollateralAcceptance("AAVEV3-ETHEREUM", "weETH", True, Decimal("0.275"), "ISOLATED", "LTV 72.5%"),
    CollateralAcceptance("AAVEV3-ETHEREUM", "wstETH", True, Decimal("0.205"), "ISOLATED", "LTV 79.5%"),
    CollateralAcceptance("AAVEV3-ETHEREUM", "USDT", True, Decimal("0.23"), "ISOLATED", "LTV 77%"),
    CollateralAcceptance("AAVEV3-ETHEREUM", "USDC", True, Decimal("0.23"), "ISOLATED", "LTV 77%"),
    CollateralAcceptance("AAVEV3-ETHEREUM", "WBTC", True, Decimal("0.27"), "ISOLATED", "LTV 73%"),
    # Binance
    CollateralAcceptance("BINANCE", "USDT", True, Decimal("0"), "CROSS", "Linear futures"),
    CollateralAcceptance("BINANCE", "BTC", True, Decimal("0.05"), "CROSS", "Coin-margined"),
    CollateralAcceptance("BINANCE", "ETH", True, Decimal("0.05"), "CROSS", "Coin-margined"),
    # OKX
    CollateralAcceptance("OKX", "USDT", True, Decimal("0"), "CROSS", "Linear"),
    CollateralAcceptance("OKX", "BTC", True, Decimal("0.05"), "CROSS", "Coin-margined"),
    CollateralAcceptance("OKX", "ETH", True, Decimal("0.05"), "CROSS", "Coin-margined"),
    # Bybit
    CollateralAcceptance("BYBIT", "USDT", True, Decimal("0"), "CROSS", "Linear"),
    CollateralAcceptance("BYBIT", "BTC", True, Decimal("0.05"), "CROSS", "Coin-margined"),
    # Deribit
    CollateralAcceptance("DERIBIT", "BTC", True, Decimal("0"), "PORTFOLIO", "Portfolio margin"),
    CollateralAcceptance("DERIBIT", "ETH", True, Decimal("0"), "PORTFOLIO", "Portfolio margin"),
    CollateralAcceptance("DERIBIT", "USDC", True, Decimal("0.02"), "PORTFOLIO", "Slight haircut"),
]


def venue_accepts_collateral(venue: str, token: str) -> bool:
    """Check if a venue accepts a given token as collateral."""
    for entry in VENUE_COLLATERAL_MATRIX:
        if entry.venue == venue and entry.token == token:
            return entry.accepted
    return False


def get_collateral_haircut(venue: str, token: str) -> Decimal | None:
    """Get the haircut percentage for a token at a venue, or None if not accepted."""
    for entry in VENUE_COLLATERAL_MATRIX:
        if entry.venue == venue and entry.token == token and entry.accepted:
            return entry.haircut_pct
    return None


def get_accepted_collateral(venue: str) -> list[str]:
    """Get list of accepted collateral tokens for a venue."""
    return [e.token for e in VENUE_COLLATERAL_MATRIX if e.venue == venue and e.accepted]
