"""Internal configuration schemas — ConfigStore records, change notifications, active pointers."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ConfigStoreMetadata(BaseModel):
    """Embedded _metadata key inside every persisted config YAML."""

    timestamp: datetime
    schema_version: str
    deployer: str | None = None
    git_commit: str | None = None
    environment: str | None = None


class ConfigStoreRecord(BaseModel):
    """A versioned config snapshot stored in GCS/S3.

    Path: ```{service}/schema-v{semver}/config-v{timestamp}.yaml```
    """

    service_name: str
    schema_version: str
    config_values: dict[str, str | int | float | bool | list[str] | None]
    metadata: ConfigStoreMetadata


class ConfigStoreActivePointer(BaseModel):
    """Content of the ```{service}/active.yaml``` file pointing to the live config version."""

    config_path: str
    timestamp: datetime
    schema_version: str | None = None
    deployer: str | None = None


class ConfigChangeNotification(BaseModel):
    """Payload emitted as a CONFIG_CHANGED lifecycle event's details dict."""

    config_file: str
    changed_by: str
    change_type: str = "update"
    authorized: bool = True
    git_commit_sha: str | None = None
    fields_changed: list[str] = Field(default_factory=list)
    previous_schema_version: str | None = None
    new_schema_version: str | None = None
    environment: str | None = None


class ConfigValidationResult(BaseModel):
    """Result of validating a config against its schema."""

    valid: bool
    service_name: str
    schema_version: str
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    timestamp: datetime | None = None


class ConfigValidationResponse(BaseModel):
    """HTTP response from the /config/validate endpoint."""

    valid: bool
    errors: list[str] = Field(default_factory=list)
