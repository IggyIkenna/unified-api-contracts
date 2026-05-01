"""Tests for unified_api_contracts.internal.instrument_volatility."""

from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from unified_api_contracts.internal import (
    INSTRUMENT_VOLATILITY_REGISTRY,
    MaxUnderlyingMove,
    VolatilitySource,
    derive_max_safe_leverage,
)


def test_registry_has_minimum_seed_coverage() -> None:
    """Plan §Phase-1.2 calls for ≥30 seeded instruments at registry boot."""
    assert len(INSTRUMENT_VOLATILITY_REGISTRY) >= 30


def test_registry_keys_are_uppercase() -> None:
    for key in INSTRUMENT_VOLATILITY_REGISTRY:
        assert key == key.upper(), f"registry key {key!r} is not uppercase"


def test_registry_covers_majors_lsts_stables() -> None:
    """Spot-check the three coverage groups the controller will hit most."""
    majors = {"BTC", "ETH", "SOL", "BNB"}
    lsts = {"STETH", "WEETH", "RETH", "ANKRETH", "ETHX"}
    stables = {"USDC", "USDT", "DAI"}
    assert majors.issubset(INSTRUMENT_VOLATILITY_REGISTRY.keys())
    assert lsts.issubset(INSTRUMENT_VOLATILITY_REGISTRY.keys())
    assert stables.issubset(INSTRUMENT_VOLATILITY_REGISTRY.keys())


def test_max_underlying_move_is_frozen() -> None:
    entry = INSTRUMENT_VOLATILITY_REGISTRY["BTC"]
    with pytest.raises(ValidationError):
        entry.max_move_pct = Decimal("0.99")  # type: ignore[misc]


def test_max_move_pct_must_be_in_unit_range() -> None:
    """Entries must respect ``0 < max_move_pct ≤ 1`` Pydantic constraint."""
    from datetime import datetime

    with pytest.raises(ValidationError):
        MaxUnderlyingMove(
            asset_symbol="X",
            horizon_days=30,
            max_move_pct=Decimal("0"),
            confidence=Decimal("0.95"),
            source=VolatilitySource.MANUAL_OVERRIDE,
            derived_at=datetime(2026, 5, 1),
        )
    with pytest.raises(ValidationError):
        MaxUnderlyingMove(
            asset_symbol="X",
            horizon_days=30,
            max_move_pct=Decimal("1.5"),
            confidence=Decimal("0.95"),
            source=VolatilitySource.MANUAL_OVERRIDE,
            derived_at=datetime(2026, 5, 1),
        )


def test_horizon_days_must_be_positive() -> None:
    from datetime import datetime

    with pytest.raises(ValidationError):
        MaxUnderlyingMove(
            asset_symbol="X",
            horizon_days=0,
            max_move_pct=Decimal("0.25"),
            confidence=Decimal("0.95"),
            source=VolatilitySource.MANUAL_OVERRIDE,
            derived_at=datetime(2026, 5, 1),
        )


def test_derive_btc_default_buffer() -> None:
    """BTC max_move=0.25 with default buffer 0.5 → 2.0x."""
    cap = derive_max_safe_leverage("BTC")
    assert cap == Decimal("2.0")


def test_derive_avax_default_buffer() -> None:
    """AVAX max_move=0.45 with default buffer 0.5 → ~1.111x."""
    cap = derive_max_safe_leverage("AVAX")
    assert cap is not None
    assert Decimal("1.10") < cap < Decimal("1.12")


def test_derive_usdc_tight_cap() -> None:
    """USDC max_move=0.02 with default buffer 0.5 → 25x — depeg headroom only."""
    cap = derive_max_safe_leverage("USDC")
    assert cap == Decimal("25")


def test_derive_case_insensitive_lookup() -> None:
    upper = derive_max_safe_leverage("BTC")
    lower = derive_max_safe_leverage("btc")
    mixed = derive_max_safe_leverage("Btc")
    assert upper == lower == mixed


def test_derive_unknown_symbol_returns_none() -> None:
    """Missing entry → None (controller falls back to venue cap with WARNING)."""
    assert derive_max_safe_leverage("DOES_NOT_EXIST") is None


def test_derive_zero_buffer() -> None:
    """buffer=0 → leverage = 1 / max_move (no headroom; liquidation at adverse move)."""
    cap = derive_max_safe_leverage("BTC", safety_buffer=Decimal("0"))
    assert cap == Decimal("4.0")


def test_derive_high_buffer() -> None:
    """buffer=0.9 → leverage = 0.1 / 0.25 = 0.4x for BTC."""
    cap = derive_max_safe_leverage("BTC", safety_buffer=Decimal("0.9"))
    assert cap == Decimal("0.4")


def test_derive_buffer_must_be_under_one() -> None:
    with pytest.raises(ValueError, match="safety_buffer"):
        derive_max_safe_leverage("BTC", safety_buffer=Decimal("1"))
    with pytest.raises(ValueError, match="safety_buffer"):
        derive_max_safe_leverage("BTC", safety_buffer=Decimal("1.1"))


def test_derive_buffer_must_be_non_negative() -> None:
    with pytest.raises(ValueError, match="safety_buffer"):
        derive_max_safe_leverage("BTC", safety_buffer=Decimal("-0.1"))


def test_volatility_source_enum_values() -> None:
    """Source enum is the SSOT for entry provenance."""
    assert VolatilitySource.REALISED_30D.value == "realised_30d"
    assert VolatilitySource.GARCH_FORECAST.value == "garch_forecast"
    assert VolatilitySource.MANUAL_OVERRIDE.value == "manual_override"


def test_stable_caps_are_high() -> None:
    """Stables have very tight max_move and therefore very high leverage caps —
    sanity check that the depeg-only assumption produces ≥10x for USDC/USDT/DAI."""
    for sym in ("USDC", "USDT", "DAI"):
        cap = derive_max_safe_leverage(sym)
        assert cap is not None and cap >= Decimal("10")


def test_high_vol_alts_yield_low_caps() -> None:
    """High-vol alts (≥0.50 max move) yield caps ≤1x at default buffer —
    controller should reduce position or skip these instruments under leverage."""
    for sym in ("DOGE", "SUI", "SEI", "CRV"):
        cap = derive_max_safe_leverage(sym)
        assert cap is not None and cap <= Decimal("1")
