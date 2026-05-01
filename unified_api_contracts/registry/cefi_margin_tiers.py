"""CeFi venue margin tiers — MMR / IMR per venue per tier.

Per audit P2.1a (workspace audit 2026-05-01). Mirrors the shape of
:mod:`unified_api_contracts.registry.defi_reserve_params` (Aave reserve
params) so consumers (UTL ``margin_and_liquidation`` engine, risk-and-exposure
service) can call ``get_margin_tier(venue, asset, notional_usd)`` without
service-local lookups.

CeFi venues use a tiered margin schedule: position notional in USD determines
which tier applies. Higher tier = higher MMR (maintenance margin requirement)
and lower max leverage. These values track venue documentation and are
periodically revalidated against venue API ``getLeverageBracket`` endpoints.
Last revalidated: 2026-05-01.

Sources:
- Binance: https://www.binance.com/en/futures/trading-rules/perpetual/leverage-margin
- Bybit: https://www.bybit.com/en/help-center/article/Risk-Limit
- OKX: https://www.okx.com/help-center/usdt-margined-perpetual-swaps-tiered-rates

The values are conservative defaults — risk-and-exposure-service may override
per-client based on the venue's actual returned tier in real-time queries.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Final


@dataclass(frozen=True)
class MarginTier:
    """One tier in a venue's margin schedule for a single asset."""

    tier: int
    max_notional_usd: Decimal
    """Position notional ceiling for this tier (in USD)."""
    max_leverage: int
    initial_margin_rate: Decimal
    """IMR — fraction of notional required to open."""
    maintenance_margin_rate: Decimal
    """MMR — fraction of notional below which liquidation triggers."""


@dataclass(frozen=True)
class VenueMarginSchedule:
    """Margin tier schedule for a single (venue, asset) pair."""

    venue: str
    asset: str  # base asset symbol, e.g. 'BTC', 'ETH'
    tiers: tuple[MarginTier, ...]


def _tier(n: int, max_notional: str, max_lev: int, imr: str, mmr: str) -> MarginTier:
    """Helper for compact tier construction."""
    return MarginTier(
        tier=n,
        max_notional_usd=Decimal(max_notional),
        max_leverage=max_lev,
        initial_margin_rate=Decimal(imr),
        maintenance_margin_rate=Decimal(mmr),
    )


# ── Binance USDT-M perpetuals ───────────────────────────────────────────────

_BINANCE_BTC = VenueMarginSchedule(
    venue="binance",
    asset="BTC",
    tiers=(
        _tier(1, "50000", 125, "0.008", "0.004"),
        _tier(2, "250000", 100, "0.01", "0.005"),
        _tier(3, "1000000", 50, "0.02", "0.01"),
        _tier(4, "5000000", 20, "0.05", "0.025"),
        _tier(5, "20000000", 10, "0.10", "0.05"),
        _tier(6, "50000000", 5, "0.20", "0.10"),
        _tier(7, "100000000", 4, "0.25", "0.125"),
        _tier(8, "200000000", 3, "0.333", "0.15"),
        _tier(9, "500000000", 2, "0.50", "0.25"),
        _tier(10, "1000000000", 1, "1.00", "0.50"),
    ),
)

_BINANCE_ETH = VenueMarginSchedule(
    venue="binance",
    asset="ETH",
    tiers=(
        _tier(1, "50000", 100, "0.01", "0.005"),
        _tier(2, "250000", 75, "0.0133", "0.0065"),
        _tier(3, "1000000", 50, "0.02", "0.01"),
        _tier(4, "5000000", 20, "0.05", "0.025"),
        _tier(5, "20000000", 10, "0.10", "0.05"),
        _tier(6, "50000000", 5, "0.20", "0.10"),
        _tier(7, "100000000", 4, "0.25", "0.125"),
        _tier(8, "200000000", 3, "0.333", "0.15"),
        _tier(9, "500000000", 2, "0.50", "0.25"),
        _tier(10, "1000000000", 1, "1.00", "0.50"),
    ),
)


# ── Bybit USDT perpetuals ───────────────────────────────────────────────────

_BYBIT_BTC = VenueMarginSchedule(
    venue="bybit",
    asset="BTC",
    tiers=(
        _tier(1, "2000000", 100, "0.01", "0.005"),
        _tier(2, "5000000", 50, "0.02", "0.01"),
        _tier(3, "20000000", 20, "0.05", "0.025"),
        _tier(4, "50000000", 10, "0.10", "0.05"),
        _tier(5, "100000000", 5, "0.20", "0.10"),
        _tier(6, "200000000", 2, "0.50", "0.25"),
    ),
)

_BYBIT_ETH = VenueMarginSchedule(
    venue="bybit",
    asset="ETH",
    tiers=(
        _tier(1, "1000000", 50, "0.02", "0.01"),
        _tier(2, "5000000", 25, "0.04", "0.02"),
        _tier(3, "20000000", 10, "0.10", "0.05"),
        _tier(4, "50000000", 5, "0.20", "0.10"),
        _tier(5, "100000000", 2, "0.50", "0.25"),
    ),
)


# ── OKX USDT perpetuals ─────────────────────────────────────────────────────

_OKX_BTC = VenueMarginSchedule(
    venue="okx",
    asset="BTC",
    tiers=(
        _tier(1, "100000", 100, "0.01", "0.005"),
        _tier(2, "1000000", 50, "0.02", "0.01"),
        _tier(3, "5000000", 25, "0.04", "0.02"),
        _tier(4, "20000000", 10, "0.10", "0.05"),
        _tier(5, "100000000", 5, "0.20", "0.10"),
        _tier(6, "500000000", 2, "0.50", "0.25"),
    ),
)

_OKX_ETH = VenueMarginSchedule(
    venue="okx",
    asset="ETH",
    tiers=(
        _tier(1, "100000", 75, "0.0133", "0.0065"),
        _tier(2, "500000", 50, "0.02", "0.01"),
        _tier(3, "5000000", 25, "0.04", "0.02"),
        _tier(4, "20000000", 10, "0.10", "0.05"),
        _tier(5, "100000000", 5, "0.20", "0.10"),
        _tier(6, "500000000", 2, "0.50", "0.25"),
    ),
)


# ── Master registry ─────────────────────────────────────────────────────────

CEFI_MARGIN_TIERS: Final[dict[tuple[str, str], VenueMarginSchedule]] = {
    ("binance", "BTC"): _BINANCE_BTC,
    ("binance", "ETH"): _BINANCE_ETH,
    ("bybit", "BTC"): _BYBIT_BTC,
    ("bybit", "ETH"): _BYBIT_ETH,
    ("okx", "BTC"): _OKX_BTC,
    ("okx", "ETH"): _OKX_ETH,
}


def get_margin_schedule(venue: str, asset: str) -> VenueMarginSchedule | None:
    """Lookup the full tier schedule for a (venue, asset) pair."""
    return CEFI_MARGIN_TIERS.get((venue.lower(), asset.upper()))


def get_margin_tier(venue: str, asset: str, notional_usd: Decimal) -> MarginTier | None:
    """Resolve which tier applies to a position of a given notional.

    Returns the smallest tier whose ``max_notional_usd`` accommodates the
    position, or ``None`` if no tier exists for the (venue, asset) pair.
    """
    schedule = get_margin_schedule(venue, asset)
    if schedule is None:
        return None
    for tier in schedule.tiers:
        if notional_usd <= tier.max_notional_usd:
            return tier
    return schedule.tiers[-1] if schedule.tiers else None


def maintenance_margin_for(venue: str, asset: str, notional_usd: Decimal) -> Decimal | None:
    """Convenience: MMR for a position of a given notional, or ``None``."""
    tier = get_margin_tier(venue, asset, notional_usd)
    return tier.maintenance_margin_rate if tier is not None else None
