"""Internal ML schemas — model metadata, inference requests/responses, training jobs."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class TargetType(StrEnum):
    DIRECTION = "direction"
    RETURN = "return"
    VOLATILITY = "volatility"
    REGIME = "regime"
    SPREAD = "spread"
    SIGNAL = "signal"


class ModelType(StrEnum):
    LIGHTGBM = "lightgbm"
    XGBOOST = "xgboost"
    RANDOM_FOREST = "random_forest"
    NEURAL_NET = "neural_net"
    LINEAR = "linear"
    ENSEMBLE = "ensemble"


class TrainingPeriod(BaseModel):
    start: str = Field(description="ISO date string YYYY-MM-DD")
    end: str = Field(description="ISO date string YYYY-MM-DD")


class ModelVariantConfig(BaseModel):
    """Config for a single model variant in the training grid (ModelVariantConfig)."""

    instrument_id: str
    timeframe: str
    lookback_window: int
    target_type: TargetType
    std_dev_threshold: float
    breakout_threshold: float


class ModelMetadata(BaseModel):
    """Full metadata record stored in GCS after a training run (ModelMetadata.to_dict())."""

    model_id: str
    model_version: str
    instrument_id: str
    symbol: str
    category: str
    timeframe: str
    lookback_window: int
    target_type: TargetType
    std_dev_threshold: float
    breakout_threshold: float
    model_type: ModelType
    feature_count: int
    feature_names: str = Field(description="comma-separated feature names")
    hyperparameters: str = Field(description="JSON-serialised dict")
    performance_metrics: str = Field(description="JSON-serialised dict")
    training_timestamp: str = Field(description="ISO 8601 UTC")
    training_duration_seconds: float
    training_period_start: str | None = None
    training_period_end: str | None = None


class MLConfigDict(BaseModel):
    """Full config dict for a model (MLConfigDict TypedDict converted to model)."""

    model_id: str
    model_version: str
    category: str
    asset: str
    target_type: TargetType
    model_type: ModelType
    timeframe: str
    features_config: dict[str, str | int | float | bool | list[str] | None]
    hyperparameters: dict[str, str | int | float | bool | None]
    training_period: TrainingPeriod
    training_cutoff_date: str
    performance_metrics: dict[str, float]
    feature_names: list[str]
    lookback_window: int
    description: str = ""
    grid_metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class InferenceRequest(BaseModel):
    """Request sent to ml-inference-service for a single prediction."""

    request_id: str
    model_id: str
    instrument_id: str
    timestamp: datetime
    features: dict[str, float | int | bool | None]
    timeframe: str = "1h"


class InferenceResult(BaseModel):
    """Prediction output from ml-inference-service."""

    request_id: str
    model_id: str
    instrument_id: str
    timestamp: datetime
    prediction: float
    confidence: float | None = None
    target_type: TargetType
    feature_importance: dict[str, float] | None = None
    latency_ms: float | None = None
    model_version: str | None = None


class TrainingJobRequest(BaseModel):
    """Request to kick off a training run in ml-training-service."""

    job_id: str
    job_config: MLConfigDict
    training_data_path: str
    output_path: str
    triggered_by: str = "scheduled"
    triggered_at: datetime | None = None
    priority: int = 5


class TrainingJobResult(BaseModel):
    """Outcome of a training job."""

    job_id: str
    model_id: str
    model_version: str
    status: str
    started_at: datetime
    completed_at: datetime | None = None
    model_path: str | None = None
    metadata: ModelMetadata | None = None
    error: str | None = None
