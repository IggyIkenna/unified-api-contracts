"""Tests for UsageMeterRow usage-metering row schema.

Stage 3E G2 § 3. Every metered unit of work lands as one row in
GCS ``odum-<env>-usage-metering/``. Schema stays pinned so dev,
staging, and prod writers + BigQuery aggregators stay in lockstep.

SSOT: codex/14-playbooks/infra-spec/stage-3e-g2-env-split.md § 3.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from unified_api_contracts.internal.architecture_v2 import UsageMeterRow


def _minimal_row(**overrides: object) -> UsageMeterRow:
    base: dict[str, object] = {
        "timestamp_utc": "2026-05-01T12:34:56Z",
        "org_id": "alpha-capital",
        "caller_audience": "trading_platform_subscriber",
        "meter_kind": "api_call",
        "unit_count": 1,
        "source_service": "execution-service",
        "env": "staging",
    }
    base.update(overrides)
    return UsageMeterRow(**base)  # pyright: ignore[reportArgumentType]


def test_usage_row_minimal_happy_path() -> None:
    row = _minimal_row()
    assert row.org_id == "alpha-capital"
    assert row.unit_count == 1
    assert row.env == "staging"
    assert row.dims == {}


def test_usage_row_accepts_none_org_for_internal_traffic() -> None:
    row = _minimal_row(org_id=None, caller_audience="admin")
    assert row.org_id is None
    assert row.caller_audience == "admin"


def test_usage_row_rejects_bad_env() -> None:
    with pytest.raises(ValidationError):
        _minimal_row(env="qa")


def test_usage_row_rejects_bad_meter_kind() -> None:
    with pytest.raises(ValidationError):
        _minimal_row(meter_kind="funny_business")


def test_usage_row_rejects_extra_fields() -> None:
    """``extra='forbid'`` keeps GCS/BigQuery schema pinned."""

    with pytest.raises(ValidationError):
        UsageMeterRow(  # pyright: ignore[reportCallIssue]
            timestamp_utc="2026-05-01T12:00:00Z",
            org_id="alpha",
            caller_audience="im_client",
            meter_kind="data_pull",
            unit_count=3,
            source_service="mtds",
            env="prod",
            rogue_field="nope",  # pyright: ignore[reportCallIssue]
        )


def test_usage_row_carries_dims() -> None:
    row = _minimal_row(
        meter_kind="execution_fill",
        source_service="execution-service",
        dims={"venue": "binance", "category": "CEFI", "instrument_type": "spot"},
    )
    assert row.dims["venue"] == "binance"
    assert row.dims["category"] == "CEFI"


def test_usage_row_is_frozen() -> None:
    row = _minimal_row()
    with pytest.raises(ValidationError):
        row.unit_count = 999  # pyright: ignore[reportAttributeAccessIssue]


def test_usage_row_rejects_bad_audience() -> None:
    with pytest.raises(ValidationError):
        _minimal_row(caller_audience="superuser")
