"""Unit tests for orphan UIC schemas — instantiate each to verify they work.

Per orphan-contracts-utilization.plan.md Phase 1: Add unit tests for all UIC schemas.
Orphans: InferenceRequest (has test), InferenceResult, DeltaOneFeatureRecord,
FeatureSnapshotRequest, OptionsIvRecord, FuturesTermStructureRecord,
CircuitBreakerEventMessage, HealthAlertMessage.
"""

from __future__ import annotations

from datetime import UTC, datetime

from unified_api_contracts.internal.features import (
    DeltaOneFeatureRecord,
    FeatureSnapshotRequest,
    FuturesTermStructureRecord,
    OptionsIvRecord,
)
from unified_api_contracts.internal.ml import InferenceRequest, InferenceResult
from unified_api_contracts.internal.pubsub import (
    CircuitBreakerEventMessage,
    HealthAlertMessage,
)


class TestOrphanMlSchemas:
    """Tests for ml.py orphan schemas."""

    def test_inference_request_instantiate(self) -> None:
        """InferenceRequest can be instantiated with minimal fields."""
        req = InferenceRequest(instrument_id="i1")
        assert req.instrument_id == "i1"
        assert req.request_id == ""
        assert req.timeframe == "1h"

    def test_inference_result_instantiate(self) -> None:
        """InferenceResult can be instantiated."""
        ts = datetime.now(UTC)
        res = InferenceResult(
            request_id="r1",
            model_id="m1",
            instrument_id="i1",
            timestamp=ts,
            prediction=0.75,
        )
        assert res.request_id == "r1"
        assert res.prediction == 0.75
        assert res.confidence is None


class TestOrphanFeatureSchemas:
    """Tests for features.py orphan schemas."""

    def test_delta_one_feature_record_instantiate(self) -> None:
        """DeltaOneFeatureRecord can be instantiated."""
        ts = datetime.now(UTC)
        rec = DeltaOneFeatureRecord(
            timestamp=ts,
            timestamp_out=ts,
            instrument_id="BTC-USDT",
        )
        assert rec.instrument_id == "BTC-USDT"
        assert rec.rsi_14 is None

    def test_feature_snapshot_request_instantiate(self) -> None:
        """FeatureSnapshotRequest can be instantiated."""
        ts = datetime.now(UTC)
        req = FeatureSnapshotRequest(
            instrument_id="i1",
            timestamp=ts,
            swing_lookback_window=100,
        )
        assert req.instrument_id == "i1"
        assert req.swing_lookback_window == 100
        assert req.feature_groups == []

    def test_options_iv_record_instantiate(self) -> None:
        """OptionsIvRecord can be instantiated."""
        ts = datetime.now(UTC)
        rec = OptionsIvRecord(
            timestamp=ts,
            timestamp_out=ts,
            venue="deribit",
            underlying_symbol="BTC",
        )
        assert rec.venue == "deribit"
        assert rec.atm_iv is None

    def test_futures_term_structure_record_instantiate(self) -> None:
        """FuturesTermStructureRecord can be instantiated."""
        ts = datetime.now(UTC)
        rec = FuturesTermStructureRecord(
            timestamp=ts,
            timestamp_out=ts,
            venue="binance",
            underlying_symbol="BTC",
            spot_price=50000.0,
        )
        assert rec.spot_price == 50000.0
        assert rec.basis is None


class TestOrphanPubsubSchemas:
    """Tests for pubsub.py orphan schemas."""

    def test_circuit_breaker_event_message_instantiate(self) -> None:
        """CircuitBreakerEventMessage can be instantiated."""
        msg = CircuitBreakerEventMessage(
            name="venue-binance",
            previous_state="closed",
            new_state="open",
            timestamp=datetime.now(UTC).isoformat(),
        )
        assert msg.name == "venue-binance"
        assert msg.new_state == "open"
        assert msg.failure_count == 0

    def test_health_alert_message_instantiate(self) -> None:
        """HealthAlertMessage can be instantiated."""
        msg = HealthAlertMessage(
            service_name="ml-inference-service",
            status="degraded",
            timestamp=datetime.now(UTC).isoformat(),
        )
        assert msg.service_name == "ml-inference-service"
        assert msg.status == "degraded"
        assert msg.previous_status is None
