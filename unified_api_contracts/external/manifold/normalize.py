"""Manifold Markets venue-specific normalizers.

Re-exports all normalize_manifold_* functions from normalize_utils/ modules
into a single venue-local module.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from unified_api_contracts.canonical.crosscutting.errors import (
    CanonicalError,
    ErrorAction,
)
from unified_api_contracts.canonical.domain import (
    CanonicalBetMarket,
    CanonicalOdds,
    CanonicalTrade,
)
from unified_api_contracts.normalize_utils.errors._utils import from_http_status

from .schemas import ManifoldMarket, ManifoldTrade

# ---------------------------------------------------------------------------
# Sports / prediction normalizers
# ---------------------------------------------------------------------------


def normalize_manifold_market(raw: ManifoldMarket, venue: str = "manifold") -> CanonicalBetMarket:
    """Convert ManifoldMarket to CanonicalBetMarket."""
    now = datetime.now(UTC)
    close_time: datetime | None = None
    if raw.close_time is not None:
        try:
            close_time = datetime.fromtimestamp(raw.close_time / 1000.0, tz=UTC)
        except (ValueError, TypeError, OSError):
            close_time = None
    status: str | None = None
    if raw.resolution is not None:
        status = "closed"
    return CanonicalBetMarket(
        venue=venue,
        market_id=raw.id or "",
        event_id=raw.id or "",
        market_name=raw.question or "",
        event_name=raw.question or "",
        sport=None,
        competition=None,
        status=status,
        in_play=False,
        timestamp=now,
        close_time=close_time,
    )


def normalize_manifold_odds(raw: ManifoldMarket, venue: str = "manifold") -> CanonicalOdds:
    """Convert ManifoldMarket to CanonicalOdds.

    probability is 0.0-1.0, converted to decimal odds: decimal = 1 / probability.
    """
    now = datetime.now(UTC)
    prob = float(raw.probability or 0.5)
    # Clamp probability to avoid division by zero or absurd odds
    prob = max(0.01, min(0.99, prob))
    decimal_odds = Decimal(str(round(1.0 / prob, 6)))
    return CanonicalOdds(
        venue=venue,
        event_id=raw.id or "",
        market_id=raw.id or "",
        selection_id=f"{raw.id or ''}-yes",
        selection_name="Yes",
        decimal_odds=decimal_odds,
        timestamp=now,
        is_back=True,
        available_size=None,
        event_name=raw.question or "",
        sport=None,
        competition=None,
    )


# ---------------------------------------------------------------------------
# Trades
# ---------------------------------------------------------------------------


def normalize_manifold_trade(
    raw: ManifoldTrade,
    venue: str = "manifold",
    symbol: str = "",
) -> CanonicalTrade:
    """Convert ManifoldTrade to CanonicalTrade.

    Manifold prediction market: price is probability (0-1), amount is mana wagered.
    """
    sym = symbol or raw.contract_id or "UNKNOWN"
    return CanonicalTrade(
        venue=venue,
        symbol=sym,
        trade_id=raw.id or "",
        timestamp=datetime.now(UTC),
        price=Decimal(str(raw.price or 0)),
        quantity=Decimal(str(raw.amount or 0)),
        side="buy",  # Manifold doesn't have directional sides
        buyer_maker=None,
        venue_trade_id=raw.id,
    )


# ---------------------------------------------------------------------------
# Error
# ---------------------------------------------------------------------------


def normalize_manifold_error(
    error_code: str | int,
    message: str = "",
    venue: str = "manifold",
) -> CanonicalError:
    """Map a Manifold Markets HTTP status to a CanonicalError subclass."""
    code = str(error_code)
    try:
        status = int(code)
        return from_http_status(status, message, venue)
    except ValueError:
        return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


__all__ = [
    "normalize_manifold_error",
    "normalize_manifold_market",
    "normalize_manifold_odds",
    "normalize_manifold_trade",
]
