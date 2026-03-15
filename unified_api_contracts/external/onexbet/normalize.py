"""1xBet venue-specific normalizers.

Re-exports all normalize_onexbet_* functions from normalize_utils/ modules
into a single venue-local module.
"""

from __future__ import annotations

from datetime import UTC, datetime

from unified_api_contracts.canonical.domain import CanonicalBetMarket

from .schemas import OneXBetMarket

# ---------------------------------------------------------------------------
# Sports / prediction normalizers
# ---------------------------------------------------------------------------


def normalize_onexbet_market(raw: OneXBetMarket, venue: str = "onexbet") -> CanonicalBetMarket:
    """Convert OneXBetMarket to CanonicalBetMarket.

    OneXBetMarket has a name and a list of outcomes (selections); no distinct market ID is
    provided by the API, so the name is used as market_id.
    """
    return CanonicalBetMarket(
        venue=venue,
        market_id=raw.name or "",
        event_id=raw.name or "",
        market_name=raw.name or "",
        event_name=raw.name or "",
        sport=None,
        competition=None,
        status=None,
        in_play=None,
        timestamp=datetime.now(UTC),
        close_time=None,
    )


__all__ = [
    "normalize_onexbet_market",
]
