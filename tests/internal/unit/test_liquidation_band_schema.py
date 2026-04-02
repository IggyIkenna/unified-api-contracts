"""Tests for LiquidationBandEntry and LiquidationBandPredictionSnapshot schemas."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from unified_api_contracts.internal.features import (
    LiquidationBandEntry,
    LiquidationBandPredictionSnapshot,
)


def _make_band(
    tier: int = 10, prob: float = 0.4, long_price: float = 45000.0, short_price: float = 55000.0
) -> LiquidationBandEntry:
    return LiquidationBandEntry(
        leverage_tier=tier,
        long_liq_price=Decimal(str(long_price)),
        short_liq_price=Decimal(str(short_price)),
        probability=prob,
        estimated_long_usd=Decimal(str(prob * 300_000)),
        estimated_short_usd=Decimal(str(prob * 200_000)),
        maintenance_margin_rate=0.005,
    )


def _make_snapshot() -> LiquidationBandPredictionSnapshot:
    return LiquidationBandPredictionSnapshot(
        instrument_key="BINANCE:PERPETUAL:BTCUSDT",
        venue="BINANCE",
        timestamp=datetime(2025, 6, 15, 12, 0, 0, tzinfo=UTC),
        current_price=Decimal("50000.00"),
        bands=[
            _make_band(5, 0.1, 40000.0, 60000.0),
            _make_band(10, 0.4, 45000.0, 55000.0),
            _make_band(25, 0.25, 48000.0, 52000.0),
            _make_band(50, 0.15, 49000.0, 51000.0),
            _make_band(100, 0.1, 49500.0, 50500.0),
        ],
        model_version="v0.1.0",
        calibration_date="2025-06-14",
        total_oi_usd=Decimal("5000000"),
    )


class TestLiquidationBandEntry:
    def test_valid_construction(self) -> None:
        band = _make_band()
        assert band.leverage_tier == 10
        assert band.probability == 0.4

    def test_negative_leverage_raises(self) -> None:
        with pytest.raises(ValueError, match="positive"):
            _make_band(tier=-1)

    def test_zero_leverage_raises(self) -> None:
        with pytest.raises(ValueError, match="positive"):
            _make_band(tier=0)

    def test_probability_bounds(self) -> None:
        _make_band(prob=0.0)
        _make_band(prob=1.0)
        with pytest.raises(ValueError):
            _make_band(prob=-0.1)
        with pytest.raises(ValueError):
            _make_band(prob=1.1)


class TestLiquidationBandPredictionSnapshot:
    def test_serialization_roundtrip(self) -> None:
        snapshot = _make_snapshot()
        data = snapshot.model_dump()
        restored = LiquidationBandPredictionSnapshot.model_validate(data)
        assert restored.instrument_key == snapshot.instrument_key
        assert len(restored.bands) == 5
        assert restored.bands[1].leverage_tier == 10
        assert restored.model_version == "v0.1.0"

    def test_json_roundtrip(self) -> None:
        snapshot = _make_snapshot()
        json_str = snapshot.model_dump_json()
        restored = LiquidationBandPredictionSnapshot.model_validate_json(json_str)
        assert restored.current_price == Decimal("50000.00")
        assert len(restored.bands) == 5

    def test_to_canonical_clusters(self) -> None:
        snapshot = _make_snapshot()
        clusters = snapshot.to_canonical_clusters()
        assert len(clusters) == 10
        for c in clusters:
            assert c["source"] == "internal_prediction"
            assert c["instrument_key"] == "BINANCE:PERPETUAL:BTCUSDT"
            assert c["venue"] == "BINANCE"

        long_clusters = [c for c in clusters if c["long_liq_usd"] != Decimal("0")]
        short_clusters = [c for c in clusters if c["short_liq_usd"] != Decimal("0")]
        assert len(long_clusters) == 5
        assert len(short_clusters) == 5

    def test_canonical_cluster_leverage_assumption(self) -> None:
        snapshot = _make_snapshot()
        clusters = snapshot.to_canonical_clusters()
        first_pair = clusters[:2]
        assert first_pair[0]["leverage_assumption"] == Decimal("5")
        assert first_pair[1]["leverage_assumption"] == Decimal("5")

    def test_empty_bands(self) -> None:
        snapshot = LiquidationBandPredictionSnapshot(
            instrument_key="TEST:PERP:BTCUSD",
            venue="TEST",
            timestamp=datetime(2025, 1, 1, tzinfo=UTC),
            current_price=Decimal("40000"),
            bands=[],
            model_version="v0",
            calibration_date="2025-01-01",
        )
        clusters = snapshot.to_canonical_clusters()
        assert clusters == []
