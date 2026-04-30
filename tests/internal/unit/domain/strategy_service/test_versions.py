"""Plan D — StrategyVersion invariants + facade exports + maturity floor."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from unified_api_contracts.internal.domain.strategy_service.lifecycle import (
    StrategyMaturityPhase,
)
from unified_api_contracts.strategy import (
    ApprovalRecord,
    ConfigDiff,
    StrategyVersion,
    VersionStatus,
    minimum_approval_maturity,
)


def _now() -> datetime:
    return datetime(2026, 4, 25, 12, 0, 0, tzinfo=UTC)


def test_minimum_approval_maturity_is_backtest_1yr() -> None:
    assert minimum_approval_maturity() is StrategyMaturityPhase.BACKTEST_1YR


def test_genesis_version_must_have_no_config_diff() -> None:
    diff = ConfigDiff(base_version_id="v_other", changed_fields=(), unchanged_fingerprint="")
    with pytest.raises(ValueError, match="Genesis version"):
        StrategyVersion(
            version_id="v_genesis",
            parent_instance_id="inst_alpha",
            maturity_phase=StrategyMaturityPhase.LIVE_STABLE,
            status=VersionStatus.ROLLED_OUT,
            authored_by="system_seed",
            created_at=_now(),
            parent_version_id=None,
            config_diff=diff,
            rolled_out_at=_now(),
        )


def test_genesis_rolled_out_ok() -> None:
    v = StrategyVersion(
        version_id="v_genesis",
        parent_instance_id="inst_alpha",
        maturity_phase=StrategyMaturityPhase.LIVE_STABLE,
        status=VersionStatus.ROLLED_OUT,
        authored_by="system_seed",
        created_at=_now(),
        rolled_out_at=_now(),
    )
    assert v.parent_version_id is None
    assert v.config_diff is None
    assert v.status is VersionStatus.ROLLED_OUT


def test_approved_requires_approval_record() -> None:
    with pytest.raises(ValueError, match="approval=None"):
        StrategyVersion(
            version_id="v_draft",
            parent_instance_id="inst_alpha",
            maturity_phase=StrategyMaturityPhase.BACKTEST_1YR,
            status=VersionStatus.APPROVED,
            authored_by="client_a",
            created_at=_now(),
            parent_version_id="v_genesis",
            config_diff=ConfigDiff(base_version_id="v_genesis"),
        )


def test_approved_requires_backtest_1yr_floor() -> None:
    approval = ApprovalRecord(
        approved_by="admin_x",
        approved_at=_now(),
        backtest_maturity=StrategyMaturityPhase.BACKTEST_MINIMAL,
        backtest_series_ref="gs://x/y/backtest.parquet",
    )
    with pytest.raises(ValueError, match="below the BACKTEST_1YR floor"):
        StrategyVersion(
            version_id="v_draft",
            parent_instance_id="inst_alpha",
            maturity_phase=StrategyMaturityPhase.BACKTEST_MINIMAL,
            status=VersionStatus.APPROVED,
            authored_by="client_a",
            created_at=_now(),
            parent_version_id="v_genesis",
            config_diff=ConfigDiff(base_version_id="v_genesis"),
            approval=approval,
        )


def test_approved_at_floor_ok() -> None:
    approval = ApprovalRecord(
        approved_by="admin_x",
        approved_at=_now(),
        backtest_maturity=StrategyMaturityPhase.BACKTEST_1YR,
        backtest_series_ref="gs://x/y/backtest.parquet",
    )
    v = StrategyVersion(
        version_id="v_draft",
        parent_instance_id="inst_alpha",
        maturity_phase=StrategyMaturityPhase.BACKTEST_1YR,
        status=VersionStatus.APPROVED,
        authored_by="client_a",
        created_at=_now(),
        parent_version_id="v_genesis",
        config_diff=ConfigDiff(base_version_id="v_genesis"),
        approval=approval,
    )
    assert v.status is VersionStatus.APPROVED


def test_approved_above_floor_ok() -> None:
    approval = ApprovalRecord(
        approved_by="admin_x",
        approved_at=_now(),
        backtest_maturity=StrategyMaturityPhase.PAPER_STABLE,
        backtest_series_ref="gs://x/y/backtest.parquet",
    )
    v = StrategyVersion(
        version_id="v_draft",
        parent_instance_id="inst_alpha",
        maturity_phase=StrategyMaturityPhase.PAPER_STABLE,
        status=VersionStatus.APPROVED,
        authored_by="client_a",
        created_at=_now(),
        parent_version_id="v_genesis",
        config_diff=ConfigDiff(base_version_id="v_genesis"),
        approval=approval,
    )
    assert v.status is VersionStatus.APPROVED


def test_rolled_out_requires_rolled_out_at() -> None:
    with pytest.raises(ValueError, match="rolled_out_at=None"):
        StrategyVersion(
            version_id="v_draft",
            parent_instance_id="inst_alpha",
            maturity_phase=StrategyMaturityPhase.LIVE_STABLE,
            status=VersionStatus.ROLLED_OUT,
            authored_by="client_a",
            created_at=_now(),
            parent_version_id="v_genesis",
            config_diff=ConfigDiff(base_version_id="v_genesis"),
        )


def test_draft_does_not_require_approval() -> None:
    v = StrategyVersion(
        version_id="v_draft",
        parent_instance_id="inst_alpha",
        maturity_phase=StrategyMaturityPhase.SMOKE,
        status=VersionStatus.DRAFT,
        authored_by="client_a",
        created_at=_now(),
        parent_version_id="v_genesis",
        config_diff=ConfigDiff(base_version_id="v_genesis"),
    )
    assert v.approval is None


def test_pending_approval_does_not_require_approval() -> None:
    v = StrategyVersion(
        version_id="v_draft",
        parent_instance_id="inst_alpha",
        maturity_phase=StrategyMaturityPhase.BACKTEST_1YR,
        status=VersionStatus.PENDING_APPROVAL,
        authored_by="client_a",
        created_at=_now(),
        parent_version_id="v_genesis",
        config_diff=ConfigDiff(base_version_id="v_genesis"),
    )
    assert v.status is VersionStatus.PENDING_APPROVAL


def test_rejected_status_allowed_without_approval() -> None:
    v = StrategyVersion(
        version_id="v_draft",
        parent_instance_id="inst_alpha",
        maturity_phase=StrategyMaturityPhase.SMOKE,
        status=VersionStatus.REJECTED,
        authored_by="client_a",
        created_at=_now(),
        parent_version_id="v_genesis",
        config_diff=ConfigDiff(base_version_id="v_genesis"),
    )
    assert v.status is VersionStatus.REJECTED


def test_config_diff_changed_fields_tuple() -> None:
    diff = ConfigDiff(
        base_version_id="v_genesis",
        changed_fields=(("entry_threshold_bps", "5", "8"),),
        unchanged_fingerprint="abc123",
    )
    assert diff.changed_fields[0] == ("entry_threshold_bps", "5", "8")


def test_supersedes_round_trip() -> None:
    approval = ApprovalRecord(
        approved_by="admin_x",
        approved_at=_now(),
        backtest_maturity=StrategyMaturityPhase.BACKTEST_1YR,
        backtest_series_ref="gs://x/y.parquet",
    )
    v = StrategyVersion(
        version_id="v_new",
        parent_instance_id="inst_alpha",
        maturity_phase=StrategyMaturityPhase.LIVE_STABLE,
        status=VersionStatus.ROLLED_OUT,
        authored_by="client_a",
        created_at=_now(),
        parent_version_id="v_genesis",
        config_diff=ConfigDiff(base_version_id="v_genesis"),
        approval=approval,
        rolled_out_at=_now(),
        supersedes_version_id="v_prior",
    )
    assert v.supersedes_version_id == "v_prior"
