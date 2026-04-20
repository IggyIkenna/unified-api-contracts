"""Unit tests for :class:`SignalPayload` + :class:`PayloadDepth`."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from unified_api_contracts.signal_broadcast import (
    PayloadDepth,
    SignalPayload,
)


class TestPayloadDepth:
    def test_members(self) -> None:
        assert {d.value for d in PayloadDepth} == {"MINIMAL", "STANDARD", "RICH"}


def _base_kwargs() -> dict[str, object]:
    return {
        "slot_label": "stat-arb-pairs-fixed-cefi-spot-btc-eth",
        "signal_version": "v0.1.0",
        "directional_intent": "LONG",
        "target_exposure": 1000.0,
        "timeframe": "1m",
        "emitted_at": datetime(2026, 4, 20, 12, 0, 0, tzinfo=UTC),
    }


class TestSignalPayload:
    def test_minimal_valid(self) -> None:
        payload = SignalPayload(**_base_kwargs())  # type: ignore[arg-type]
        assert payload.depth is PayloadDepth.MINIMAL
        assert payload.confidence is None
        assert payload.expected_horizon_seconds is None

    def test_standard_payload(self) -> None:
        kwargs = _base_kwargs()
        kwargs.update(
            depth=PayloadDepth.STANDARD,
            confidence=0.75,
            expected_horizon_seconds=300,
            stop_loss_bps=50,
            take_profit_bps=120,
        )
        payload = SignalPayload(**kwargs)  # type: ignore[arg-type]
        assert payload.depth is PayloadDepth.STANDARD
        assert payload.confidence == 0.75

    def test_rich_payload_bounded_feature_snapshot(self) -> None:
        kwargs = _base_kwargs()
        kwargs.update(
            depth=PayloadDepth.RICH,
            confidence=0.9,
            expected_horizon_seconds=600,
            rationale_tags=("model-v2", "regime-lo-vol"),
            feature_snapshot={f"f_{i}": float(i) for i in range(32)},
        )
        payload = SignalPayload(**kwargs)  # type: ignore[arg-type]
        assert len(payload.feature_snapshot) == 32

    def test_rich_payload_exceeds_feature_snapshot_cap(self) -> None:
        kwargs = _base_kwargs()
        kwargs.update(
            depth=PayloadDepth.RICH,
            feature_snapshot={f"f_{i}": float(i) for i in range(33)},
        )
        with pytest.raises(ValidationError):
            SignalPayload(**kwargs)  # type: ignore[arg-type]

    def test_confidence_out_of_range(self) -> None:
        kwargs = _base_kwargs()
        kwargs["confidence"] = 1.2
        with pytest.raises(ValidationError):
            SignalPayload(**kwargs)  # type: ignore[arg-type]

    def test_direction_literal_enforced(self) -> None:
        kwargs = _base_kwargs()
        kwargs["directional_intent"] = "UP"  # not a valid literal
        with pytest.raises(ValidationError):
            SignalPayload(**kwargs)  # type: ignore[arg-type]

    def test_roundtrip_json(self) -> None:
        payload = SignalPayload(**_base_kwargs())  # type: ignore[arg-type]
        serialised = payload.model_dump(mode="json")
        rebuilt = SignalPayload.model_validate(serialised)
        assert rebuilt == payload

    def test_json_roundtrip_preserves_fields_for_hmac(self) -> None:
        """The HMAC-signing helper takes ``model_dump(mode='json')``
        output — every payload field must survive unchanged so the
        signature verifies on the counterparty side."""

        payload = SignalPayload(**_base_kwargs())  # type: ignore[arg-type]
        dumped = payload.model_dump(mode="json")
        assert dumped["slot_label"] == "stat-arb-pairs-fixed-cefi-spot-btc-eth"
        assert dumped["directional_intent"] == "LONG"
        assert dumped["target_exposure"] == 1000.0
        assert dumped["timeframe"] == "1m"
        assert "signature" not in dumped  # envelope helper adds this
        assert "signed_at" not in dumped
