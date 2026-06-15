"""Canonical greeks-snapshot + implied-vol-surface schemas (single-canonical).

These are the ONE wire/manifest shape that every source — Deribit live, Tardis
historical-crypto, Massive TradFi — maps to, and the SHAPE that greeks-service
emits. Per the workspace "Live = batch / Batch = Live" rule an engine reading
``greeks_snapshot`` / ``implied_vol_surface`` MUST NOT be able to tell live from
batch: same fields, same units (IV annualised fractional; greeks per the BS
convention), ``available_at`` stamped per-row at write-time, no live-only field
set, no read-time derivation.

Single-canonical convergence with greeks-service@0299b03:

* ``CanonicalIVSurfacePoint`` mirrors ``greeks_service.kernels.iv_surface.SurfacePoint``
  field-for-field (instrument_key / strike / expiry / right / moneyness /
  tenor_years / implied_vol / iv_source) and ``CanonicalImpliedVolSurface``
  mirrors ``IVSurface`` (underlying / underlying_mark / as_of / points). The
  greeks-service dataclasses are SCHEMA_PROVENANCE_EXEMPT *in-memory computation
  containers* (pure-function kernel I/O); this module is the *wire-format domain
  contract* that the assembled surface is serialised to for the manifest + the
  engine feature feed. One shape, two representations — never a divergent set.
* ``CanonicalGreeksSnapshot`` carries the per-leg greeks computed in-house by
  ``greeks_service.kernels.black_scholes`` (delta/gamma/vega/theta/rho +
  the IV used), keyed by ``instrument_key`` — the per-leg companion to the
  surface. ``iv_source`` records whether the IV was the venue-published
  ``mark_iv`` or fitted from a mark price (honest provenance; never invented).

Units: ``implied_vol`` annualised fractional (0.62 = 62%); ``moneyness`` =
strike / underlying_mark; ``tenor_years`` = (expiry minus as_of) in years. All
datetimes are UTC-aware.

SSOT: codex/04-architecture/greeks-service-overview.md § "Greeks snapshot + IV
surface canonical schema".
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import AwareDatetime, Field

from .._base import CanonicalBase


class CanonicalGreeksSnapshot(CanonicalBase):
    """Per-leg option greeks snapshot — the ``greeks_snapshot`` data_type row.

    One row per option instrument at one snapshot time. Greeks are computed
    in-house (Black-Scholes) from the option chain + underlying mark; ``iv_used``
    is the IV that produced them and ``iv_source`` records its provenance
    (``"mark_iv"`` = venue-published, ``"fitted"`` = solved from a mark price).
    Identical shape regardless of which source (Deribit / Tardis / Massive) fed
    the chain — batch == live.
    """

    instrument_key: str = Field(description="Canonical instrument key for the option leg")
    venue: str
    underlying: str
    as_of: AwareDatetime = Field(description="Snapshot time (UTC)")
    expiry: AwareDatetime = Field(description="Option expiry (UTC)")
    strike: Decimal
    right: str = Field(description='"CALL" or "PUT"')
    underlying_mark: Decimal = Field(description="Underlying index/mark price at snapshot")
    iv_used: Decimal = Field(description="Annualised fractional IV the greeks were computed at")
    iv_source: str = Field(description='"mark_iv" (venue) or "fitted" (BS solver)')
    delta: Decimal
    gamma: Decimal
    vega: Decimal
    theta: Decimal
    rho: Decimal | None = None
    schema_version: str = "1.0"


class CanonicalIVSurfacePoint(CanonicalBase):
    """One (strike x expiry) node on the IV surface.

    Mirrors ``greeks_service.kernels.iv_surface.SurfacePoint`` field-for-field --
    the single-canonical convergence point (one shape both produce).
    """

    instrument_key: str
    strike: Decimal
    expiry: AwareDatetime
    right: str = Field(description='"CALL" or "PUT"')
    moneyness: Decimal = Field(description="strike / underlying_mark")
    tenor_years: Decimal = Field(description="(expiry - as_of) in years")
    implied_vol: Decimal = Field(description="Annualised, fractional")
    iv_source: str = Field(description='"mark_iv" or "fitted"')


class CanonicalImpliedVolSurface(CanonicalBase):
    """Assembled IV surface for one underlying at one snapshot — ``implied_vol_surface``.

    Mirrors ``greeks_service.kernels.iv_surface.IVSurface`` (flattened to the
    canonical ``points`` list; the by_expiry / by_strike indices are a read-time
    convenience the consumer rebuilds, never persisted divergently). An empty
    ``points`` list = honest absence (no leg had a usable IV) — never a synthetic
    node.
    """

    underlying: str
    venue: str
    underlying_mark: Decimal
    as_of: AwareDatetime = Field(description="Snapshot time (UTC)")
    points: list[CanonicalIVSurfacePoint] = Field(default_factory=list)
    schema_version: str = "1.0"


__all__ = [
    "CanonicalGreeksSnapshot",
    "CanonicalIVSurfacePoint",
    "CanonicalImpliedVolSurface",
]
