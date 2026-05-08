"""Tests for the `code: AlertCode | None` field on AlertEvent / AlertMessage / DefiAlert envelopes.

Added 2026-05-08 as part of the Option A producer-migration unblock for Phase 3 of
`alerting_service_live_rules_2026_05_07.md`. Operator decision: extend the three envelope models
with an optional `code: AlertCode` field rather than (B) backdoor-stamping in `details` dict or
(C) deprecating legacy enums in this cycle. Issue doc:
`unified-trading-pm/plans/active/issues/alerting_phase3_envelope_schema_gap_2026_05_08.md`.

Coverage matrix: 3 envelopes x {accepts AlertCode, accepts None, rejects raw string,
rejects unknown enum value} = 12 cases.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from unified_api_contracts import AlertCode, DefiAlertType
from unified_api_contracts.internal import AlertEvent, AlertMessage, DefiAlert
from unified_api_contracts.internal.risk import AlertType

# ---------------------------------------------------------------------------
# AlertEvent
# ---------------------------------------------------------------------------


def _alert_event_kwargs() -> dict[str, object]:
    return {
        "alert_id": "alert-001",
        "rule_id": "rule-balance-drift",
        "triggered_at": datetime(2026, 5, 8, 12, 0, tzinfo=UTC),
        "severity": "CRITICAL",
        "message": "Balance drift detected",
        "metric_value": 1.23,
        "threshold": 1.0,
    }


def test_alert_event_accepts_alert_code() -> None:
    event = AlertEvent(**_alert_event_kwargs(), code=AlertCode.BALANCE_DRIFT)
    assert event.code is AlertCode.BALANCE_DRIFT


def test_alert_event_accepts_none() -> None:
    event = AlertEvent(**_alert_event_kwargs())
    assert event.code is None
    event_explicit_none = AlertEvent(**_alert_event_kwargs(), code=None)
    assert event_explicit_none.code is None


def test_alert_event_rejects_unknown_string() -> None:
    with pytest.raises(ValidationError):
        AlertEvent(**_alert_event_kwargs(), code="NOT_A_REAL_ALERT_CODE")  # type: ignore[arg-type]


def test_alert_event_accepts_alert_code_value_string() -> None:
    """StrEnum coerces a valid `.value` string back to the enum — Pydantic v2 default."""

    event = AlertEvent(**_alert_event_kwargs(), code=AlertCode.BALANCE_DRIFT.value)  # type: ignore[arg-type]
    assert event.code is AlertCode.BALANCE_DRIFT


# ---------------------------------------------------------------------------
# AlertMessage
# ---------------------------------------------------------------------------


def _alert_message_kwargs() -> dict[str, object]:
    return {
        "alert_type": AlertType.MARGIN_WARNING,
        "client_id": "client-1",
        "metric": "leverage",
        "current_value": Decimal("3.5"),
        "threshold": Decimal("3.0"),
        "timestamp": datetime(2026, 5, 8, 12, 0, tzinfo=UTC),
    }


def test_alert_message_accepts_alert_code() -> None:
    msg = AlertMessage(**_alert_message_kwargs(), code=AlertCode.MARGIN_THRESHOLD_BREACH)
    assert msg.code is AlertCode.MARGIN_THRESHOLD_BREACH


def test_alert_message_accepts_none() -> None:
    msg = AlertMessage(**_alert_message_kwargs())
    assert msg.code is None
    msg_explicit_none = AlertMessage(**_alert_message_kwargs(), code=None)
    assert msg_explicit_none.code is None


def test_alert_message_rejects_unknown_string() -> None:
    with pytest.raises(ValidationError):
        AlertMessage(**_alert_message_kwargs(), code="NOT_A_REAL_ALERT_CODE")  # type: ignore[arg-type]


def test_alert_message_legacy_alert_type_still_required() -> None:
    """`code` is additive — `alert_type` field is still required per Option A."""

    kwargs = _alert_message_kwargs()
    del kwargs["alert_type"]
    with pytest.raises(ValidationError):
        AlertMessage(**kwargs, code=AlertCode.BALANCE_DRIFT)


# ---------------------------------------------------------------------------
# DefiAlert
# ---------------------------------------------------------------------------


def _defi_alert_kwargs() -> dict[str, object]:
    return {
        "alert_type": DefiAlertType.HEALTH_FACTOR_CRITICAL,
        "message": "Aave health factor critical",
    }


def test_defi_alert_accepts_alert_code() -> None:
    alert = DefiAlert(**_defi_alert_kwargs(), code=AlertCode.DEFI_HEALTH_FACTOR_CRITICAL)
    assert alert.code is AlertCode.DEFI_HEALTH_FACTOR_CRITICAL


def test_defi_alert_accepts_none() -> None:
    alert = DefiAlert(**_defi_alert_kwargs())
    assert alert.code is None
    alert_explicit_none = DefiAlert(**_defi_alert_kwargs(), code=None)
    assert alert_explicit_none.code is None


def test_defi_alert_rejects_unknown_string() -> None:
    with pytest.raises(ValidationError):
        DefiAlert(**_defi_alert_kwargs(), code="NOT_A_REAL_ALERT_CODE")  # type: ignore[arg-type]


def test_defi_alert_legacy_alert_type_still_required() -> None:
    """`code` is additive — `alert_type` field is still required per Option A."""

    kwargs = _defi_alert_kwargs()
    del kwargs["alert_type"]
    with pytest.raises(ValidationError):
        DefiAlert(**kwargs, code=AlertCode.DEFI_HEALTH_FACTOR_CRITICAL)


# ---------------------------------------------------------------------------
# Round-trip serialization sanity check
# ---------------------------------------------------------------------------


def test_alert_event_code_round_trips_through_model_dump() -> None:
    """AlertEvent envelope -> dict -> AlertEvent preserves the code value."""

    original = AlertEvent(**_alert_event_kwargs(), code=AlertCode.BALANCE_DRIFT)
    payload = original.model_dump()
    assert payload["code"] == AlertCode.BALANCE_DRIFT.value
    rehydrated = AlertEvent.model_validate(payload)
    assert rehydrated.code is AlertCode.BALANCE_DRIFT


def test_defi_alert_code_round_trips_through_model_dump() -> None:
    original = DefiAlert(**_defi_alert_kwargs(), code=AlertCode.DEFI_HEALTH_FACTOR_CRITICAL)
    payload = original.model_dump()
    assert payload["code"] == AlertCode.DEFI_HEALTH_FACTOR_CRITICAL.value
    rehydrated = DefiAlert.model_validate(payload)
    assert rehydrated.code is AlertCode.DEFI_HEALTH_FACTOR_CRITICAL
