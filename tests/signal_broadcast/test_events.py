"""Unit tests for :class:`StrategySignalEmittedExternal` +
:class:`StrategySignalAcknowledged`."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from unified_api_contracts.signal_broadcast import (
    AckSource,
    SignalPayload,
    StrategySignalAcknowledged,
    StrategySignalEmittedExternal,
)


def _payload() -> SignalPayload:
    return SignalPayload(
        slot_label="slot-a",
        signal_version="v0.1.0",
        directional_intent="LONG",
        target_exposure=100.0,
        timeframe="1m",
        emitted_at=datetime(2026, 4, 20, tzinfo=UTC),
    )


class TestAckSource:
    def test_members(self) -> None:
        assert {s.value for s in AckSource} == {
            "WEBHOOK_RESPONSE",
            "REST_PULL_ACK",
            "OUT_OF_BAND",
        }


class TestStrategySignalEmittedExternal:
    def test_valid(self) -> None:
        key = uuid4()
        evt = StrategySignalEmittedExternal(
            slot_label="slot-a",
            counterparty_id="cp-1",
            payload=_payload(),
            signature="a" * 64,
            idempotency_key=key,
            emitted_at=datetime(2026, 4, 20, tzinfo=UTC),
        )
        assert evt.idempotency_key == key
        assert evt.signature

    def test_roundtrip(self) -> None:
        evt = StrategySignalEmittedExternal(
            slot_label="slot-a",
            counterparty_id="cp-1",
            payload=_payload(),
            signature="sig",
            idempotency_key=uuid4(),
            emitted_at=datetime(2026, 4, 20, tzinfo=UTC),
        )
        rebuilt = StrategySignalEmittedExternal.model_validate(evt.model_dump(mode="json"))
        assert rebuilt == evt

    def test_empty_signature_rejected(self) -> None:
        with pytest.raises(ValidationError):
            StrategySignalEmittedExternal(
                slot_label="slot-a",
                counterparty_id="cp-1",
                payload=_payload(),
                signature="",
                idempotency_key=uuid4(),
                emitted_at=datetime(2026, 4, 20, tzinfo=UTC),
            )

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            StrategySignalEmittedExternal(
                slot_label="slot-a",
                counterparty_id="cp-1",
                payload=_payload(),
                signature="sig",
                idempotency_key=uuid4(),
                emitted_at=datetime(2026, 4, 20, tzinfo=UTC),
                unknown="x",  # type: ignore[call-arg]
            )


class TestStrategySignalAcknowledged:
    def test_valid(self) -> None:
        evt = StrategySignalAcknowledged(
            slot_label="slot-a",
            counterparty_id="cp-1",
            idempotency_key=uuid4(),
            acked_at=datetime(2026, 4, 20, tzinfo=UTC),
            ack_source=AckSource.WEBHOOK_RESPONSE,
        )
        assert evt.ack_source is AckSource.WEBHOOK_RESPONSE

    def test_roundtrip(self) -> None:
        evt = StrategySignalAcknowledged(
            slot_label="slot-a",
            counterparty_id="cp-1",
            idempotency_key=uuid4(),
            acked_at=datetime(2026, 4, 20, tzinfo=UTC),
            ack_source=AckSource.REST_PULL_ACK,
        )
        rebuilt = StrategySignalAcknowledged.model_validate(evt.model_dump(mode="json"))
        assert rebuilt == evt

    def test_invalid_ack_source(self) -> None:
        with pytest.raises(ValidationError):
            StrategySignalAcknowledged(
                slot_label="slot-a",
                counterparty_id="cp-1",
                idempotency_key=uuid4(),
                acked_at=datetime(2026, 4, 20, tzinfo=UTC),
                ack_source="UNKNOWN",  # type: ignore[arg-type]
            )
