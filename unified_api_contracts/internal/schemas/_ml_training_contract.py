"""ML training manifest SchemaContract — Phase 5d.1.

Plan: ``data_pipeline_completion_2026_04_18`` §Phase 5d.1. Registers the
canonical training-manifest SchemaContract so every ml-training-service run
writes one row per experiment with the v4 shard dimensions populated
(``model_family``, ``training_period``, ``strategy_id``, ``experiment_id``,
plus the upstream data ``asset_group``). Rows land at:

    gs://ml-models-{asset_group}-*/manifests/training/by_date/day={YYYY-MM-DD}/
        model_family={family}/training_period={span}/experiment_id={uuid}/
        manifest.parquet

The 3-tuple registry key is ``(ml_training, manifest, training_run)`` — we
introduced the ``ml_training`` asset_group literal for meta-contracts that
aren't themselves market-data shards. The ``asset_group`` **column** on each
row records the upstream data plane (cefi / tradfi / defi / sports /
prediction) so the training manifest UI can filter by business domain.

Per-row columns:

    instrument_id       — canonical model artifact id
                          (e.g. ``ML_TRAINING:<family>:<exp_id>``)
    asset_group         — upstream data plane (cefi / tradfi / …)
    model_family        — e.g. xgboost_classifier_v2, lightgbm_regressor
    training_period     — ISO date span (e.g. 2020-01-01..2024-12-31)
    experiment_id       — UUID of this run
    strategy_id         — downstream consumer strategy (nullable;
                          some training runs target multiple strategies)
    ts_event            — run start timestamp (UTC)
    ts_event_out        — run completion timestamp (UTC; nullable until done)
    status              — QUEUED / RUNNING / COMPLETED / FAILED
    rc                  — exit code (nullable until complete)
    model_artifact_uri  — gs:// URI of trained model; nullable until done
    metrics_artifact_uri — gs:// URI of metrics.parquet; nullable until done
    val_loss            — validation loss (nullable)
    val_accuracy        — validation accuracy / AUC (nullable)
    train_row_count     — rows fed into training (nullable)
    features_hash       — content-hash of features parquet consumed (stability)

Do NOT import this module directly; use
``unified_api_contracts.internal.schemas.contracts``.
"""

from __future__ import annotations

from unified_api_contracts.internal.schemas.contracts import (
    CONTRACT_REGISTRY,
    INSTRUMENT_ID_COL,
    TS_EVENT_COL,
    ColumnSpec,
    SchemaContract,
)

ML_TRAINING_MANIFEST = SchemaContract(
    asset_group="ml_training",
    instrument_type="manifest",
    data_type="training_run",
    columns=[
        INSTRUMENT_ID_COL,
        ColumnSpec(
            name="asset_group",
            dtype="string",
            nullable=False,
            description="Upstream data plane (cefi/tradfi/defi/sports/prediction).",
        ),
        ColumnSpec(
            name="model_family",
            dtype="string",
            nullable=False,
            description="v4 shard dim — e.g. xgboost_classifier_v2, lightgbm_regressor.",
        ),
        ColumnSpec(
            name="training_period",
            dtype="string",
            nullable=False,
            description="ISO date span (YYYY-MM-DD..YYYY-MM-DD) — v4 shard dim.",
        ),
        ColumnSpec(
            name="experiment_id",
            dtype="string",
            nullable=False,
            description="UUID of this training run — unique across all runs.",
        ),
        ColumnSpec(
            name="strategy_id",
            dtype="string",
            nullable=True,
            description="Downstream strategy consumer; nullable for multi-consumer trainings.",
        ),
        TS_EVENT_COL,
        ColumnSpec(
            name="ts_event_out",
            dtype="datetime64[ns, UTC]",
            nullable=True,
            description="Run completion timestamp — nullable while status != COMPLETED/FAILED.",
        ),
        ColumnSpec(
            name="status",
            dtype="string",
            nullable=False,
            description="QUEUED / RUNNING / COMPLETED / FAILED.",
        ),
        ColumnSpec(
            name="rc",
            dtype="int64",
            nullable=True,
            description="Exit code — nullable until run completes.",
        ),
        ColumnSpec(
            name="model_artifact_uri",
            dtype="string",
            nullable=True,
            description="gs:// URI of the trained model artifact; null until COMPLETED.",
        ),
        ColumnSpec(
            name="metrics_artifact_uri",
            dtype="string",
            nullable=True,
            description="gs:// URI of metrics.parquet; null until COMPLETED.",
        ),
        ColumnSpec(
            name="val_loss",
            dtype="float64",
            nullable=True,
        ),
        ColumnSpec(
            name="val_accuracy",
            dtype="float64",
            nullable=True,
        ),
        ColumnSpec(
            name="train_row_count",
            dtype="int64",
            nullable=True,
        ),
        ColumnSpec(
            name="features_hash",
            dtype="string",
            nullable=True,
            description="Content-hash of upstream features parquet; pins training input for replay symmetry.",
        ),
    ],
    symbol_column="experiment_id",
    required_row_count_min=1,
)


CONTRACT_REGISTRY[("ml_training", "manifest", "training_run")] = ML_TRAINING_MANIFEST


__all__ = ["ML_TRAINING_MANIFEST"]
