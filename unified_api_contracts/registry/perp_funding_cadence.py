"""Per-venue perp funding-rate cadence + annualisation math.

Different perp venues charge funding at different intervals:

* CeFi 8h cadence (3 fundings/day): Binance, Bybit, OKX, Aster (perp-CCXT)
* CeFi 4h cadence (6 fundings/day): Kraken Pro derivatives
* CeFi 1h cadence (24 fundings/day): Deribit
* DeFi 1h cadence (24 fundings/day): Hyperliquid, GMX, Pacifica, Lighter
* DeFi 5min cadence (288 fundings/day): Drift (Solana)

Reading raw funding_rate from MTDS adapters and feeding it directly into
strategy features as an annualised rate without venue-aware scaling produces
~10× under-estimates for the hourly+sub-hourly venues. This module is the
single source of truth for the conversion. Strategy + features-service +
risk-and-exposure all consume from here.

Single-place rule (Bucket-name SSOT cousin): never inline a `* 3 * 365`
constant — call ``annualise_funding_rate_bps(rate, venue)``.

Adding a new venue: pick the cadence in seconds from the venue's funding
schedule docs (Binance: every 8h on UTC clock; Hyperliquid: every hour;
Deribit: every hour but settled every 15min of accrual — see Deribit Funding
docs for the formula). Then add a row + a unit test.

Refs:
* plans/active/phase5_features_streaming_carry_staked_basis_mvp_2026_05_19.md
  Phase A
* features-service/features_service/cefi/calculators/perp_funding_rates.py
* features-service/features_service/onchain/calculators/perp_funding_rates_defi.py
"""

from __future__ import annotations

from decimal import Decimal
from typing import Final

# ── Per-venue funding cadence in seconds ─────────────────────────────────────
# Single SSOT — update here, not in any consumer.
FUNDING_CADENCE_SECONDS: Final[dict[str, int]] = {
    # CeFi — 8h cadence (3/day)
    "binance": 8 * 3600,
    "bybit": 8 * 3600,
    "okx": 8 * 3600,
    "aster": 8 * 3600,
    "bitget": 8 * 3600,
    "bitfinex": 8 * 3600,
    # CeFi — 4h cadence (6/day)
    "kraken": 4 * 3600,
    # CeFi — 1h cadence (24/day)
    "deribit": 1 * 3600,
    # DeFi — 1h cadence (24/day)
    "hyperliquid": 1 * 3600,
    "gmx": 1 * 3600,
    "pacifica": 1 * 3600,
    "lighter": 1 * 3600,
    # DeFi — sub-hourly (Drift settles every block; we approximate at 5min)
    "drift": 5 * 60,
}

SECONDS_PER_YEAR: Final[int] = 365 * 24 * 3600

# Convenience: 10000 bps = 100% → multiplier from rate-fraction to bps
_BPS_PER_RATE: Final[Decimal] = Decimal("10000")


def fundings_per_year(venue: str) -> Decimal:
    """Number of funding accruals per year for ``venue``.

    Raises ``KeyError`` if the venue isn't in the registry — caller should
    have validated venue against ``FUNDING_CADENCE_SECONDS.keys()`` already.
    """
    cadence = FUNDING_CADENCE_SECONDS[venue.lower()]
    # Decimal arithmetic to avoid float drift on the high cadences (Drift =
    # 105120 fundings/year would float-round otherwise).
    return Decimal(SECONDS_PER_YEAR) / Decimal(cadence)


def annualise_funding_rate_bps(rate: Decimal, venue: str) -> Decimal:
    """Convert a raw per-funding-cycle rate fraction into annualised APY bps.

    ``rate`` is the raw funding_rate from the venue's API as a Decimal
    fraction (e.g. 0.0001 = 1bp per cycle = 0.01%). Output is the linearly
    annualised APY in basis points.

    Linear (not compounded) is used because (a) funding is rebated, not
    reinvested — there's no auto-compounding inside the venue; (b) strategy
    comparisons are easier in linear bps; (c) cycle rates are tiny so
    linear ≈ compounded to 1bp anyway.

    Example: Binance 0.01% per 8h → 0.0001 × 3 × 365 × 10000 = 109,500 bps =
    1095% APY (deliberately huge to highlight units in tests; real funding
    is typically 0.001% - 0.01% per cycle = ~11% - 110% APY).
    """
    return rate * fundings_per_year(venue) * _BPS_PER_RATE


def is_supported_venue(venue: str) -> bool:
    """``True`` if ``venue`` has a registered funding cadence."""
    return venue.lower() in FUNDING_CADENCE_SECONDS


__all__ = [
    "FUNDING_CADENCE_SECONDS",
    "SECONDS_PER_YEAR",
    "annualise_funding_rate_bps",
    "fundings_per_year",
    "is_supported_venue",
]
