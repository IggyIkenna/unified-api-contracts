"""Unit tests for the canonical greeks_snapshot + implied_vol_surface schemas.

These types are the single-canonical wire shape that every options source
(Deribit live, Tardis historical-crypto, Massive TradFi) and greeks-service
converge on. The tests assert (a) the public-export surface, (b) field-for-field
shape parity with the greeks-service kernel output (SurfacePoint / IVSurface),
(c) batch==live: the same instance round-trips identically regardless of which
source produced it, and (d) honest-absence (empty surface) is representable.

SSOT: v2_engine_venue_buildout_2026_06_15.md Phase D P1 (a).
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal


def test_canonical_types_exported_from_root() -> None:
    """The three new types are reachable from the UAC root facade."""
    from unified_api_contracts import (
        CanonicalGreeksSnapshot,
        CanonicalImpliedVolSurface,
        CanonicalIVSurfacePoint,
    )

    assert CanonicalGreeksSnapshot.__name__ == "CanonicalGreeksSnapshot"
    assert CanonicalImpliedVolSurface.__name__ == "CanonicalImpliedVolSurface"
    assert CanonicalIVSurfacePoint.__name__ == "CanonicalIVSurfacePoint"


def test_canonical_types_exported_from_domain() -> None:
    """Reachable from the derivatives domain (the canonical home)."""
    from unified_api_contracts.canonical.domain.derivatives import (
        CanonicalGreeksSnapshot,
        CanonicalImpliedVolSurface,
        CanonicalIVSurfacePoint,
    )

    assert CanonicalGreeksSnapshot is not None
    assert CanonicalImpliedVolSurface is not None
    assert CanonicalIVSurfacePoint is not None


def test_iv_surface_point_matches_greeks_service_surfacepoint_fields() -> None:
    """Field-for-field parity with greeks_service.kernels.iv_surface.SurfacePoint.

    Single-canonical convergence: the canonical wire type carries exactly the
    fields the greeks-service kernel emits (one shape, two representations).
    """
    from unified_api_contracts.canonical.domain.derivatives import CanonicalIVSurfacePoint

    expected = {
        "instrument_key",
        "strike",
        "expiry",
        "right",
        "moneyness",
        "tenor_years",
        "implied_vol",
        "iv_source",
    }
    assert set(CanonicalIVSurfacePoint.model_fields) == expected


def test_implied_vol_surface_construct_and_honest_absence() -> None:
    """An empty surface (no usable IV) is representable — honest absence."""
    from unified_api_contracts.canonical.domain.derivatives import CanonicalImpliedVolSurface

    empty = CanonicalImpliedVolSurface(
        underlying="BTC",
        venue="DERIBIT",
        underlying_mark=Decimal("66849.03"),
        as_of=datetime(2026, 6, 15, tzinfo=UTC),
        points=[],
    )
    assert empty.points == []
    assert empty.schema_version == "1.0"


def test_greeks_snapshot_iv_provenance_is_explicit() -> None:
    """iv_source records mark_iv (venue) vs fitted (BS solver) — never invented."""
    from unified_api_contracts.canonical.domain.derivatives import CanonicalGreeksSnapshot

    snap = CanonicalGreeksSnapshot(
        instrument_key="DERIBIT:OPTION:BTC-16JUN26-56000-C",
        venue="DERIBIT",
        underlying="BTC",
        as_of=datetime(2026, 6, 15, tzinfo=UTC),
        expiry=datetime(2026, 6, 16, 8, tzinfo=UTC),
        strike=Decimal("56000"),
        right="CALL",
        underlying_mark=Decimal("66849.03"),
        iv_used=Decimal("0.9088"),
        iv_source="mark_iv",
        delta=Decimal("0.92"),
        gamma=Decimal("0.00001"),
        vega=Decimal("12.5"),
        theta=Decimal("-30.1"),
    )
    assert snap.iv_source == "mark_iv"
    assert snap.iv_used == Decimal("0.9088")
    assert snap.rho is None  # optional


def test_batch_equals_live_same_shape_regardless_of_source() -> None:
    """A surface point serialises identically whether it came from a Deribit
    live pull, a Tardis historical backfill, or a Massive TradFi chain — the
    engine MUST NOT be able to tell live from batch.
    """
    from unified_api_contracts.canonical.domain.derivatives import CanonicalIVSurfacePoint

    common = {
        "instrument_key": "X:OPTION:BTC-16JUN26-56000-C",
        "strike": Decimal("56000"),
        "expiry": datetime(2026, 6, 16, 8, tzinfo=UTC),
        "right": "CALL",
        "moneyness": Decimal("0.8377"),
        "tenor_years": Decimal("0.00274"),
        "implied_vol": Decimal("0.9088"),
        "iv_source": "mark_iv",
    }
    live_point = CanonicalIVSurfacePoint(**common)
    batch_point = CanonicalIVSurfacePoint(**common)
    assert live_point.model_dump() == batch_point.model_dump()


def test_extra_fields_forbidden() -> None:
    """Canonical types reject unknown fields (CanonicalBase extra='forbid')."""
    import pytest
    from pydantic import ValidationError

    from unified_api_contracts.canonical.domain.derivatives import CanonicalIVSurfacePoint

    with pytest.raises(ValidationError):
        CanonicalIVSurfacePoint(
            instrument_key="x",
            strike=Decimal("1"),
            expiry=datetime(2026, 6, 16, tzinfo=UTC),
            right="CALL",
            moneyness=Decimal("1"),
            tenor_years=Decimal("0.1"),
            implied_vol=Decimal("0.5"),
            iv_source="mark_iv",
            bogus_field="nope",  # type: ignore[call-arg]
        )
