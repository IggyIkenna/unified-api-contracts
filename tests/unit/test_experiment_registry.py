"""Unit tests for the Phase BB.1 experiment registry SSOT."""

from __future__ import annotations

from unified_api_contracts import ExperimentKind as RootKind
from unified_api_contracts import ExperimentRunSpec as RootSpec
from unified_api_contracts import ExperimentStatus as RootStatus
from unified_api_contracts.canonical.crosscutting.experiment_registry import (
    ExperimentKind,
    ExperimentRunSpec,
    ExperimentStatus,
)

# ---------------------------------------------------------------------------
# Root import surface
# ---------------------------------------------------------------------------


def test_root_import_surface() -> None:
    assert RootKind is ExperimentKind
    assert RootSpec is ExperimentRunSpec
    assert RootStatus is ExperimentStatus


# ---------------------------------------------------------------------------
# ExperimentKind
# ---------------------------------------------------------------------------


def test_experiment_kind_values() -> None:
    assert ExperimentKind.ML_TRAINING == "ML_TRAINING"
    assert ExperimentKind.STRATEGY_BACKTEST == "STRATEGY_BACKTEST"
    assert ExperimentKind.EXECUTION_BACKTEST == "EXECUTION_BACKTEST"


def test_experiment_kind_is_str() -> None:
    for kind in ExperimentKind:
        assert isinstance(kind, str)


def test_experiment_kind_closed_set() -> None:
    assert set(ExperimentKind) == {
        ExperimentKind.ML_TRAINING,
        ExperimentKind.STRATEGY_BACKTEST,
        ExperimentKind.EXECUTION_BACKTEST,
    }


# ---------------------------------------------------------------------------
# ExperimentStatus
# ---------------------------------------------------------------------------


def test_experiment_status_values() -> None:
    assert ExperimentStatus.RUNNING == "running"
    assert ExperimentStatus.COMPLETED == "completed"
    assert ExperimentStatus.FAILED == "failed"
    assert ExperimentStatus.CANCELLED == "cancelled"


def test_experiment_status_closed_set() -> None:
    assert set(ExperimentStatus) == {
        ExperimentStatus.RUNNING,
        ExperimentStatus.COMPLETED,
        ExperimentStatus.FAILED,
        ExperimentStatus.CANCELLED,
    }


# ---------------------------------------------------------------------------
# ExperimentRunSpec
# ---------------------------------------------------------------------------

_SAMPLE_RUN_ID = "01967c5d-0000-7000-8000-000000000001"


def _make_spec(**overrides: object) -> ExperimentRunSpec:
    defaults: dict[str, object] = {
        "run_id": _SAMPLE_RUN_ID,
        "kind": ExperimentKind.STRATEGY_BACKTEST,
        "owner": "ikenna",
        "asset_group": "defi",
        "started_at": "2026-05-19T10:00:00+00:00",
        "hyperparams": {"lookback_days": 30, "leverage": 1.5},
        "expected_steps": 100,
        "status": ExperimentStatus.RUNNING,
    }
    defaults.update(overrides)
    return ExperimentRunSpec(**defaults)  # type: ignore[arg-type]


def test_spec_is_frozen() -> None:
    spec = _make_spec()
    try:
        spec.owner = "other"  # type: ignore[misc]
        raise AssertionError("Should have raised FrozenInstanceError")
    except Exception as exc:
        assert "frozen" in str(exc).lower() or "cannot assign" in str(exc).lower()


def test_spec_defaults() -> None:
    spec = _make_spec()
    assert spec.result_blob_uri is None
    assert spec.error_message is None
    assert spec.owning_plan == "deployment_ui_lifecycle_tabs_2026_05_08"


def test_spec_gcs_prefix() -> None:
    spec = _make_spec()
    assert spec.gcs_prefix == f"by_kind={ExperimentKind.STRATEGY_BACKTEST}/run_id={_SAMPLE_RUN_ID}"


def test_spec_manifest_blob_path() -> None:
    spec = _make_spec()
    assert (
        spec.manifest_blob_path == f"by_kind={ExperimentKind.STRATEGY_BACKTEST}/run_id={_SAMPLE_RUN_ID}/manifest.json"
    )


def test_spec_metrics_blob_path() -> None:
    spec = _make_spec()
    assert spec.metrics_blob_path == f"by_kind={ExperimentKind.STRATEGY_BACKTEST}/run_id={_SAMPLE_RUN_ID}/metrics.jsonl"


def test_spec_result_blob_uri_completed() -> None:
    spec = _make_spec(
        status=ExperimentStatus.COMPLETED,
        result_blob_uri="gs://pid-experiments/by_kind=STRATEGY_BACKTEST/run_id=01967c5d-0000-7000-8000-000000000001/result.parquet",
    )
    assert spec.result_blob_uri is not None
    assert "result.parquet" in spec.result_blob_uri


def test_spec_error_message_failed() -> None:
    spec = _make_spec(
        status=ExperimentStatus.FAILED,
        error_message="OOM on epoch 42",
    )
    assert spec.error_message == "OOM on epoch 42"


def test_spec_all_kinds_produce_gcs_prefix() -> None:
    for kind in ExperimentKind:
        spec = _make_spec(kind=kind)
        assert f"by_kind={kind}" in spec.gcs_prefix
        assert f"run_id={_SAMPLE_RUN_ID}" in spec.gcs_prefix


def test_spec_hyperparams_dict() -> None:
    spec = _make_spec(hyperparams={"alpha": 0.01, "beta": 0.99, "dry_run": True})
    assert spec.hyperparams["alpha"] == 0.01
    assert spec.hyperparams["dry_run"] is True
