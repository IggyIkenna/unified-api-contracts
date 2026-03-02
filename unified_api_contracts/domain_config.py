"""
Domain Configuration Protocols

Protocol definitions for domain configuration objects used across unified-trading-services.
Eliminates type errors from optional unified-config-interface dependency.
"""

from typing import Protocol


class DomainConfigProtocol(Protocol):
    """Protocol for domain-specific configuration objects."""

    # Core GCP configuration
    gcp_project_id: str
    gcs_bucket: str
    bigquery_dataset: str

    # AWS configuration (optional)
    aws_region: str | None
    s3_bucket: str | None

    # Generic config dict for extensibility
    config: dict[str, object]

    # Optional attributes from unified-config-interface
    data_type: str | None
    exchange: str | None
    environment: str | None


class DataTypeConfigProtocol(Protocol):
    """Protocol for data type configuration."""

    gcp_project_id: str
    gcs_bucket: str
    bigquery_dataset: str
    config: dict[str, object]

    # Data type specific
    data_type: str
    retention_days: int
    compression_enabled: bool


class ExchangeInstrumentConfigProtocol(Protocol):
    """Protocol for exchange instrument configuration."""

    gcp_project_id: str
    gcs_bucket: str
    bigquery_dataset: str
    config: dict[str, object]

    # Exchange specific
    exchange: str
    instrument_type: str
    market_hours: dict[str, str]
    timezone: str


class MLConfigProtocol(Protocol):
    """Protocol for ML pipeline configuration."""

    gcp_project_id: str
    gcs_bucket: str
    bigquery_dataset: str
    vertex_ai_project: str | None

    # ML specific
    model_registry_bucket: str
    feature_store_dataset: str
    training_pipeline_config: dict[str, object]
    config: dict[str, object]
