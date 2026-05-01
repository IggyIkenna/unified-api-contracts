"""Instrument-side volatility-derived leverage caps — UAC SSOT.

Sibling of :mod:`unified_api_contracts.internal.risk` ``LIQUIDATION_PARAMS_REGISTRY``.
That table answers *"given a venue/protocol, what HF/MMR thresholds trigger
liquidation?"*. This module answers the orthogonal question:

    *"given an instrument, how much leverage is safe before a single adverse
    move puts us at the liquidation threshold?"*

The leg-controller clamp at runtime is ``min(venue.max_leverage, instrument.max_safe_leverage)``;
this file owns the second term.

Formula
-------
``max_safe_leverage = (1 - safety_buffer) / max_move_pct``

A 25% expected adverse move with a 50% buffer leaves us at
``(1 - 0.5) / 0.25 = 2.0x`` — a 25% move at 2x burns 50% of equity, the buffer.
Lowering the buffer permits more aggressive leverage at the cost of a thinner
margin between adverse-move PnL and liquidation.

Source semantics
----------------
``MaxUnderlyingMove.source`` records how the entry was derived:

- ``realised_30d`` — empirical 95th-percentile 30-day return from
  features-cefi/onchain ``vol_realised_30d`` feature.
- ``garch_forecast`` — GARCH(1,1) one-month-ahead 95% one-sided shock estimate.
- ``manual_override`` — operator-set value (for new tokens with insufficient
  history, or to override a noisy estimate).

The seed table below is heuristic-realistic: 95%-confidence one-sided 30-day
adverse move calibrated against historical crypto + tradfi behaviour. These
should be overwritten by the seed script
(``unified-api-contracts/scripts/seed_instrument_volatility_registry.py``) once
the features pipelines are wired up.

Lookup
------
The registry is keyed on **base-asset symbol** (e.g. ``"BTC"``, ``"AVAX"``)
not full :class:`InstrumentKey`. Volatility is an underlying-asset property,
not a venue-specific one — a BTC perp on Binance and a BTC perp on Hyperliquid
share the same underlying-move profile, so they share the same cap.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Final

from pydantic import BaseModel, ConfigDict, Field


class VolatilitySource(StrEnum):
    """How a :class:`MaxUnderlyingMove` entry was derived."""

    REALISED_30D = "realised_30d"
    GARCH_FORECAST = "garch_forecast"
    MANUAL_OVERRIDE = "manual_override"


class MaxUnderlyingMove(BaseModel):
    """Per-asset adverse-move estimate used to cap leverage.

    Attributes
    ----------
    asset_symbol : str
        Base-asset symbol, uppercase (``"BTC"``, ``"ETH"``, ``"AVAX"`` ...).
    horizon_days : int
        Window over which ``max_move_pct`` is calibrated. The leg-controller
        rebalance cadence should be at most this horizon, otherwise the cap
        is calibrated to a longer window than the position is held and the
        derived leverage is conservative-but-stale.
    max_move_pct : Decimal
        Expected adverse one-sided move, as a fraction of underlying price.
        ``Decimal("0.25")`` means a 25% adverse move is the planning case.
    confidence : Decimal
        Confidence level of the move estimate (one-sided). ``0.95`` is the
        default — covers all but the most extreme tails.
    source : VolatilitySource
        Provenance of the value (see :class:`VolatilitySource`).
    derived_at : datetime
        When this entry was computed. Drives reseed cadence — anything older
        than 30 days should be re-derived.
    """

    model_config = ConfigDict(frozen=True)

    asset_symbol: str
    horizon_days: int = Field(gt=0)
    max_move_pct: Decimal = Field(gt=Decimal("0"), le=Decimal("1"))
    confidence: Decimal = Field(gt=Decimal("0"), lt=Decimal("1"))
    source: VolatilitySource
    derived_at: datetime


_SEED_DERIVED_AT: Final[datetime] = datetime(2026, 5, 1, 0, 0, 0)


def _seed(symbol: str, move_pct: str) -> MaxUnderlyingMove:
    return MaxUnderlyingMove(
        asset_symbol=symbol,
        horizon_days=30,
        max_move_pct=Decimal(move_pct),
        confidence=Decimal("0.95"),
        source=VolatilitySource.MANUAL_OVERRIDE,
        derived_at=_SEED_DERIVED_AT,
    )


INSTRUMENT_VOLATILITY_REGISTRY: Final[dict[str, MaxUnderlyingMove]] = {
    # Majors
    "BTC": _seed("BTC", "0.25"),
    "ETH": _seed("ETH", "0.30"),
    "SOL": _seed("SOL", "0.40"),
    "BNB": _seed("BNB", "0.25"),
    # Large-cap alts
    "AVAX": _seed("AVAX", "0.45"),
    "LINK": _seed("LINK", "0.40"),
    "DOT": _seed("DOT", "0.40"),
    "ATOM": _seed("ATOM", "0.45"),
    "NEAR": _seed("NEAR", "0.50"),
    "ADA": _seed("ADA", "0.35"),
    "XRP": _seed("XRP", "0.30"),
    "MATIC": _seed("MATIC", "0.45"),
    "LTC": _seed("LTC", "0.30"),
    "TRX": _seed("TRX", "0.25"),
    "DOGE": _seed("DOGE", "0.50"),
    # New / high-vol
    "SUI": _seed("SUI", "0.50"),
    "APT": _seed("APT", "0.45"),
    "SEI": _seed("SEI", "0.55"),
    "ARB": _seed("ARB", "0.45"),
    "OP": _seed("OP", "0.45"),
    # ETH-side LSTs (track ETH closely; small protocol-specific premium/discount)
    "STETH": _seed("STETH", "0.30"),
    "WEETH": _seed("WEETH", "0.30"),
    "RETH": _seed("RETH", "0.30"),
    "CBETH": _seed("CBETH", "0.30"),
    "ANKRETH": _seed("ANKRETH", "0.35"),
    "ETHX": _seed("ETHX", "0.35"),
    "SFRXETH": _seed("SFRXETH", "0.30"),
    "PUFETH": _seed("PUFETH", "0.30"),
    # SOL-side LSTs
    "JITOSOL": _seed("JITOSOL", "0.40"),
    "MSOL": _seed("MSOL", "0.40"),
    # Stables (de-peg / break-the-buck risk)
    "USDC": _seed("USDC", "0.02"),
    "USDT": _seed("USDT", "0.02"),
    "DAI": _seed("DAI", "0.02"),
    "FRAX": _seed("FRAX", "0.03"),
    "SUSDE": _seed("SUSDE", "0.05"),
    # DeFi governance / utility
    "UNI": _seed("UNI", "0.45"),
    "AAVE": _seed("AAVE", "0.40"),
    "COMP": _seed("COMP", "0.45"),
    "CRV": _seed("CRV", "0.50"),
}


_DEFAULT_SAFETY_BUFFER: Final[Decimal] = Decimal("0.5")


def derive_max_safe_leverage(
    asset_symbol: str,
    safety_buffer: Decimal = _DEFAULT_SAFETY_BUFFER,
) -> Decimal | None:
    """Return the volatility-derived leverage cap for ``asset_symbol``.

    Returns ``None`` when the asset is not in the registry — the controller
    interprets this as *"no instrument-side cap is known; use the venue cap
    only"* and emits a WARNING event so missing entries surface in operations.

    Parameters
    ----------
    asset_symbol : str
        Base-asset symbol, case-insensitive. Matched after upper-casing.
    safety_buffer : Decimal, optional
        Fraction of equity to leave between worst-case adverse move and
        liquidation. ``Decimal("0.5")`` (default) leaves 50% headroom.
        Must be in ``[0, 1)``. ``0.0`` = no buffer (liquidation at exactly
        the expected adverse move); ``1.0`` would yield zero leverage and
        is rejected as a configuration error.

    Returns
    -------
    Decimal | None
        Maximum safe leverage as a positive Decimal. ``None`` when the
        asset has no registry entry.

    Raises
    ------
    ValueError
        ``safety_buffer`` outside ``[0, 1)``.
    """
    if safety_buffer < Decimal("0") or safety_buffer >= Decimal("1"):
        raise ValueError(f"safety_buffer must be in [0, 1), got {safety_buffer}")
    entry = INSTRUMENT_VOLATILITY_REGISTRY.get(asset_symbol.upper())
    if entry is None:
        return None
    return (Decimal("1") - safety_buffer) / entry.max_move_pct


__all__ = [
    "INSTRUMENT_VOLATILITY_REGISTRY",
    "MaxUnderlyingMove",
    "VolatilitySource",
    "derive_max_safe_leverage",
]
