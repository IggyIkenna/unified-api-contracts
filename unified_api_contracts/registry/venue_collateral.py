"""Venue collateral acceptance matrix — which tokens each venue accepts as margin."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Final, Literal

VenueKind = Literal["PERP_CEX", "PERP_DEX", "LENDING", "STAKING"]
"""How callers should think about this venue's collateral usage.

- ``PERP_CEX`` / ``PERP_DEX``: collateral funds a perpetual short / long.
- ``LENDING``: collateral underwrites a borrow (Aave, Compound, etc.).
- ``STAKING``: collateral is the principal being staked.

Used by callers like ``CARRY_STAKED_BASIS`` to filter to perp-margining venues
when deciding the leg sequence — see
``unified-trading-pm/plans/active/carry_staked_basis_structure_axis_2026_05_04.plan.md``.
"""

_PERP_VENUE_KINDS: Final[frozenset[str]] = frozenset({"PERP_CEX", "PERP_DEX"})


@dataclass(frozen=True)
class CollateralAcceptance:
    """A single venue-token collateral acceptance entry."""

    venue: str
    token: str
    accepted: bool
    haircut_pct: Decimal | None
    margin_type: str
    notes: str
    venue_kind: VenueKind


VENUE_COLLATERAL_MATRIX: list[CollateralAcceptance] = [
    # HyperLiquid — USDC only
    CollateralAcceptance("HYPERLIQUID", "USDC", True, Decimal("0"), "CROSS", "Only accepted margin", "PERP_CEX"),
    CollateralAcceptance("HYPERLIQUID", "ETH", False, None, "", "Not accepted", "PERP_CEX"),
    CollateralAcceptance("HYPERLIQUID", "weETH", False, None, "", "Not accepted", "PERP_CEX"),
    CollateralAcceptance("HYPERLIQUID", "WETH", False, None, "", "Not accepted", "PERP_CEX"),
    # Aster
    CollateralAcceptance("ASTER", "USDC", True, Decimal("0"), "CROSS", "Primary margin", "PERP_CEX"),
    CollateralAcceptance("ASTER", "USDT", True, Decimal("0.01"), "CROSS", "Slight haircut", "PERP_CEX"),
    # Aave V3 (referencing defi_reserve_params.py LTV values)
    CollateralAcceptance("AAVEV3-ETHEREUM", "WETH", True, Decimal("0.175"), "ISOLATED", "LTV 82.5%", "LENDING"),
    CollateralAcceptance("AAVEV3-ETHEREUM", "weETH", True, Decimal("0.275"), "ISOLATED", "LTV 72.5%", "LENDING"),
    CollateralAcceptance("AAVEV3-ETHEREUM", "wstETH", True, Decimal("0.205"), "ISOLATED", "LTV 79.5%", "LENDING"),
    CollateralAcceptance("AAVEV3-ETHEREUM", "USDT", True, Decimal("0.23"), "ISOLATED", "LTV 77%", "LENDING"),
    CollateralAcceptance("AAVEV3-ETHEREUM", "USDC", True, Decimal("0.23"), "ISOLATED", "LTV 77%", "LENDING"),
    CollateralAcceptance("AAVEV3-ETHEREUM", "WBTC", True, Decimal("0.27"), "ISOLATED", "LTV 73%", "LENDING"),
    # Binance
    CollateralAcceptance("BINANCE", "USDT", True, Decimal("0"), "CROSS", "Linear futures", "PERP_CEX"),
    CollateralAcceptance("BINANCE", "BTC", True, Decimal("0.05"), "CROSS", "Coin-margined", "PERP_CEX"),
    CollateralAcceptance("BINANCE", "ETH", True, Decimal("0.05"), "CROSS", "Coin-margined", "PERP_CEX"),
    # OKX
    CollateralAcceptance("OKX", "USDT", True, Decimal("0"), "CROSS", "Linear", "PERP_CEX"),
    CollateralAcceptance("OKX", "BTC", True, Decimal("0.05"), "CROSS", "Coin-margined", "PERP_CEX"),
    CollateralAcceptance("OKX", "ETH", True, Decimal("0.05"), "CROSS", "Coin-margined", "PERP_CEX"),
    # Bybit
    CollateralAcceptance("BYBIT", "USDT", True, Decimal("0"), "CROSS", "Linear", "PERP_CEX"),
    CollateralAcceptance("BYBIT", "BTC", True, Decimal("0.05"), "CROSS", "Coin-margined", "PERP_CEX"),
    # Deribit
    CollateralAcceptance("DERIBIT", "BTC", True, Decimal("0"), "PORTFOLIO", "Portfolio margin", "PERP_CEX"),
    CollateralAcceptance("DERIBIT", "ETH", True, Decimal("0"), "PORTFOLIO", "Portfolio margin", "PERP_CEX"),
    CollateralAcceptance("DERIBIT", "USDC", True, Decimal("0.02"), "PORTFOLIO", "Slight haircut", "PERP_CEX"),
    # Lido / Etherfi staking venues — included so callers can discover the
    # staking principal asset (ETH) without needing a separate registry.
    # ``accepted=True`` for the native asset only; the staking contract is
    # not a perp-margining venue. ROCKETPOOL / JITO / MARINADE / DRIFT
    # rows are deferred until those venues are registered in
    # ``venue_constants.py`` — see plan
    # ``carry_staked_basis_structure_axis_2026_05_04`` Phase 1a-followup.
    CollateralAcceptance("LIDO", "ETH", True, Decimal("0"), "STAKE", "Native staking", "STAKING"),
    CollateralAcceptance("ETHERFI", "ETH", True, Decimal("0"), "STAKE", "Native staking", "STAKING"),
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


def accepted_perp_collateral(venue: str) -> list[str]:
    """Get list of accepted collateral tokens at a perp-margining venue.

    Filters to ``venue_kind in {PERP_CEX, PERP_DEX}``. Used by carry/basis
    strategies that need to know which assets a perp short can post as margin
    — distinct from lending-protocol or staking-protocol acceptance.
    Returns ``[]`` if the venue is not perp-kind or has no accepted rows.
    """
    return [
        e.token
        for e in VENUE_COLLATERAL_MATRIX
        if e.venue == venue and e.accepted and e.venue_kind in _PERP_VENUE_KINDS
    ]
