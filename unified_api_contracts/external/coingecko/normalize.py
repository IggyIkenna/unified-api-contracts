"""CoinGecko normalizers — all normalize_coingecko_* functions.

Extracted from normalize_utils/instruments.py.

Covers global market data (macro-level aggregate pseudo-instrument).
"""

from __future__ import annotations

from datetime import UTC, datetime

from ...canonical.domain import CanonicalInstrument
from .schemas import (
    GlobalMarketData,
    GlobalMarketResponse,
)

# ---------------------------------------------------------------------------
# CoinGecko — global market data
# ---------------------------------------------------------------------------


def normalize_coingecko_global_market(
    raw: GlobalMarketData,
    venue: str = "coingecko",
) -> CanonicalInstrument:
    """Normalize CoinGecko GlobalMarketData to CanonicalInstrument.

    GlobalMarketData is a macro-level aggregate (not a single instrument),
    mapped to a pseudo-instrument representing the global crypto market cap.
    """
    ik = f"{venue.upper()}:INDEX:GLOBAL"
    total_mcap_usd = raw.total_market_cap.get("usd") if raw.total_market_cap else None
    return CanonicalInstrument(
        instrument_key=ik,
        venue=venue,
        symbol="GLOBAL",
        timestamp=datetime.now(UTC),
        tick_size=None,
        min_size=None,
        contract_size=total_mcap_usd,  # repurpose for total market cap
        base_asset=None,
        quote_asset="USD",
        settle_asset=None,
    )


def normalize_coingecko_global_market_response(
    raw: GlobalMarketResponse,
    venue: str = "coingecko",
) -> CanonicalInstrument:
    """Normalize CoinGecko GlobalMarketResponse (wrapper) to CanonicalInstrument."""
    return normalize_coingecko_global_market(raw.data, venue=venue)


__all__ = [
    "normalize_coingecko_global_market",
    "normalize_coingecko_global_market_response",
]
