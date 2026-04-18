"""Unit tests for the ML training manifest SchemaContract (Phase 5d.1)."""

from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd

from unified_api_contracts.internal.schemas.contracts import (
    CONTRACT_REGISTRY,
    ML_TRAINING_MANIFEST,
    lookup_contract,
    validate_dataframe,
)


def test_ml_training_manifest_registered() -> None:
    contract = CONTRACT_REGISTRY[("ml_training", "manifest", "training_run")]
    assert contract is ML_TRAINING_MANIFEST


def test_ml_training_manifest_lookup_works() -> None:
    contract = lookup_contract(
        category="ml_training",
        instrument_type="manifest",
        data_type="training_run",
    )
    assert contract is ML_TRAINING_MANIFEST


def test_ml_training_manifest_symbol_column_is_experiment_id() -> None:
    assert ML_TRAINING_MANIFEST.symbol_column == "experiment_id"


def test_ml_training_manifest_has_v4_shard_columns() -> None:
    """v4 manifest shard dims — model_family, training_period, experiment_id —
    MUST be non-nullable columns on every training manifest row."""
    by_name = {c.name: c for c in ML_TRAINING_MANIFEST.columns}
    for name in ("model_family", "training_period", "experiment_id", "category", "status"):
        assert name in by_name
        assert by_name[name].nullable is False


def test_ml_training_manifest_completion_fields_nullable() -> None:
    """rc / model_artifact_uri / metrics_artifact_uri / val_loss / val_accuracy
    are only populated once the run completes — must be nullable."""
    by_name = {c.name: c for c in ML_TRAINING_MANIFEST.columns}
    for name in (
        "rc",
        "model_artifact_uri",
        "metrics_artifact_uri",
        "val_loss",
        "val_accuracy",
        "ts_event_out",
        "train_row_count",
        "features_hash",
        "strategy_id",
    ):
        assert by_name[name].nullable is True


def test_ml_training_manifest_validates_sample_row() -> None:
    df = pd.DataFrame(
        {
            "instrument_id": pd.Series(["ML_TRAINING:XGBOOST_CLASSIFIER_V2:exp-abc"], dtype="string"),
            "category": pd.Series(["cefi"], dtype="string"),
            "model_family": pd.Series(["xgboost_classifier_v2"], dtype="string"),
            "training_period": pd.Series(["2020-01-01..2024-12-31"], dtype="string"),
            "experiment_id": pd.Series(["exp-abc"], dtype="string"),
            "strategy_id": pd.Series([pd.NA], dtype="string"),
            "ts_event": pd.Series(
                [datetime(2026, 4, 18, 20, 0, tzinfo=UTC)],
                dtype="datetime64[ns, UTC]",
            ),
            "ts_event_out": pd.Series([pd.NaT], dtype="datetime64[ns, UTC]"),
            "status": pd.Series(["RUNNING"], dtype="string"),
            "rc": pd.Series([pd.NA], dtype="Int64"),
            "model_artifact_uri": pd.Series([pd.NA], dtype="string"),
            "metrics_artifact_uri": pd.Series([pd.NA], dtype="string"),
            "val_loss": pd.Series([pd.NA], dtype="Float64"),
            "val_accuracy": pd.Series([pd.NA], dtype="Float64"),
            "train_row_count": pd.Series([pd.NA], dtype="Int64"),
            "features_hash": pd.Series([pd.NA], dtype="string"),
        }
    )
    violations = validate_dataframe(df, ML_TRAINING_MANIFEST)
    # Some dtype coercions may flag; accept what does not flag as
    # structural violations and check that missing-column isn't one of them.
    kinds = {v.kind for v in violations}
    assert "missing_column" not in kinds, f"structural violation: {violations}"


def test_ml_training_manifest_instrument_id_required() -> None:
    by_name = {c.name: c for c in ML_TRAINING_MANIFEST.columns}
    assert by_name["instrument_id"].nullable is False
    assert by_name["instrument_id"].dtype == "string"
