"""Tests for `manual_audit_paths` path SSOT."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from unified_api_contracts.internal.execution import ManualAuditCategory
from unified_api_contracts.internal.manual_audit_paths import (
    BUCKET_KIND_MANUAL_AUDIT,
    OBJECT_KEY_TEMPLATE,
    manual_audit_date_prefix,
    manual_audit_object_key,
)


def _now() -> datetime:
    return datetime(2026, 5, 12, 10, 30, 0, tzinfo=UTC)


def test_bucket_kind_is_canonical_string() -> None:
    """The bucket-name SSOT lookup key is a stable string constant."""
    assert BUCKET_KIND_MANUAL_AUDIT == "manual-audit"


def test_object_key_template_shape() -> None:
    """Template includes all 4 partition axes: date / category / audit_id."""
    assert "{date}" in OBJECT_KEY_TEMPLATE
    assert "{action_category}" in OBJECT_KEY_TEMPLATE
    assert "{audit_id}" in OBJECT_KEY_TEMPLATE
    assert OBJECT_KEY_TEMPLATE.endswith(".jsonl")


def test_manual_audit_object_key_manual_trade() -> None:
    """A MANUAL_TRADE audit row keys under manual_trade/."""
    key = manual_audit_object_key(
        audit_id="aud-defi-100",
        action_category=ManualAuditCategory.MANUAL_TRADE,
        persisted_at=_now(),
    )
    assert key == "manual_audit/2026-05-12/manual_trade/aud-defi-100.jsonl"


def test_manual_audit_object_key_ml_training() -> None:
    """An ML_TRAINING_CONTROL audit row keys under ml_training_control/."""
    key = manual_audit_object_key(
        audit_id="aud-ml-200",
        action_category=ManualAuditCategory.ML_TRAINING_CONTROL,
        persisted_at=_now(),
    )
    assert key == "manual_audit/2026-05-12/ml_training_control/aud-ml-200.jsonl"


def test_manual_audit_object_key_empty_audit_id_rejected() -> None:
    """Empty audit_id is rejected."""
    with pytest.raises(ValueError, match="non-empty"):
        manual_audit_object_key(
            audit_id="",
            action_category=ManualAuditCategory.MANUAL_TRADE,
            persisted_at=_now(),
        )


def test_manual_audit_object_key_path_separators_rejected() -> None:
    """audit_id containing path separators rejected (prevents escape)."""
    with pytest.raises(ValueError, match="path separators"):
        manual_audit_object_key(
            audit_id="aud/100",
            action_category=ManualAuditCategory.MANUAL_TRADE,
            persisted_at=_now(),
        )


def test_manual_audit_date_prefix() -> None:
    """Date prefix for batch listing under a (category, date) tuple."""
    prefix = manual_audit_date_prefix(ManualAuditCategory.MANUAL_TRADE, date(2026, 5, 12))
    assert prefix == "manual_audit/2026-05-12/manual_trade/"
    # Same date, different category.
    ml_prefix = manual_audit_date_prefix(ManualAuditCategory.ML_TRAINING_CONTROL, date(2026, 5, 12))
    assert ml_prefix == "manual_audit/2026-05-12/ml_training_control/"


def test_date_partition_uses_utc_date() -> None:
    """Date partition is the UTC date of persisted_at."""
    # 2026-05-12 23:59 UTC → partition is 2026-05-12.
    late_utc = datetime(2026, 5, 12, 23, 59, 0, tzinfo=UTC)
    key = manual_audit_object_key(
        audit_id="aud-late",
        action_category=ManualAuditCategory.MANUAL_TRADE,
        persisted_at=late_utc,
    )
    assert "manual_audit/2026-05-12/" in key
