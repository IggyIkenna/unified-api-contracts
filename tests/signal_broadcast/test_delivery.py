"""Unit tests for transport configs + :class:`DeliveryAttempt`."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from unified_api_contracts.signal_broadcast import (
    DeliveryAttempt,
    DeliveryStatus,
    RestPullDeliveryConfig,
    WebhookDeliveryConfig,
)


class TestDeliveryStatus:
    def test_members(self) -> None:
        assert DeliveryStatus.PENDING == "PENDING"
        assert DeliveryStatus.SENT == "SENT"
        assert DeliveryStatus.ACKED == "ACKED"
        assert DeliveryStatus.FAILED == "FAILED"

    def test_enum_completeness(self) -> None:
        assert {s.value for s in DeliveryStatus} == {"PENDING", "SENT", "ACKED", "FAILED"}


class TestWebhookDeliveryConfig:
    def test_defaults(self) -> None:
        cfg = WebhookDeliveryConfig(endpoint="https://cp.invalid/hook")
        assert cfg.transport == "webhook"
        assert cfg.max_retries == 3
        assert cfg.retry_backoff_base_seconds > 0.0
        assert cfg.timeout_seconds > 0.0

    def test_rejects_negative_retries(self) -> None:
        with pytest.raises(ValidationError):
            WebhookDeliveryConfig(endpoint="https://cp.invalid/hook", max_retries=-1)

    def test_roundtrip(self) -> None:
        cfg = WebhookDeliveryConfig(
            endpoint="https://cp.invalid/hook",
            max_retries=5,
            retry_backoff_base_seconds=0.5,
            timeout_seconds=10.0,
        )
        rebuilt = WebhookDeliveryConfig.model_validate(cfg.model_dump(mode="json"))
        assert rebuilt == cfg


class TestRestPullDeliveryConfig:
    def test_defaults(self) -> None:
        cfg = RestPullDeliveryConfig(pull_endpoint_path="/signal/pending")
        assert cfg.transport == "rest_pull"
        assert cfg.poll_interval_seconds > 0.0
        assert cfg.retention_hours > 0

    def test_rejects_zero_poll_interval(self) -> None:
        with pytest.raises(ValidationError):
            RestPullDeliveryConfig(
                pull_endpoint_path="/signal/pending",
                poll_interval_seconds=0.0,
            )


class TestDeliveryAttempt:
    def test_pending_minimal(self) -> None:
        key = uuid4()
        started = datetime(2026, 4, 20, 0, 0, tzinfo=UTC)
        attempt = DeliveryAttempt(
            idempotency_key=key,
            attempt_number=1,
            status=DeliveryStatus.PENDING,
            started_at=started,
        )
        assert attempt.completed_at is None
        assert attempt.http_status_code is None
        assert attempt.error_reason is None

    def test_attempt_number_must_be_positive(self) -> None:
        with pytest.raises(ValidationError):
            DeliveryAttempt(
                idempotency_key=uuid4(),
                attempt_number=0,
                status=DeliveryStatus.PENDING,
                started_at=datetime(2026, 4, 20, tzinfo=UTC),
            )

    def test_roundtrip_via_json(self) -> None:
        key = uuid4()
        started = datetime(2026, 4, 20, 0, 0, tzinfo=UTC)
        completed = datetime(2026, 4, 20, 0, 0, 1, tzinfo=UTC)
        attempt = DeliveryAttempt(
            idempotency_key=key,
            attempt_number=2,
            status=DeliveryStatus.ACKED,
            started_at=started,
            completed_at=completed,
            http_status_code=200,
        )
        rebuilt = DeliveryAttempt.model_validate(attempt.model_dump(mode="json"))
        assert rebuilt == attempt
