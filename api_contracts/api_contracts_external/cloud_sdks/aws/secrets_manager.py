from __future__ import annotations

from pydantic import BaseModel


class SecretsManagerSecret(BaseModel):
    """Secrets Manager secret metadata. sm.list_secrets() / sm.describe_secret()"""

    ARN: str | None = None
    Name: str | None = None
    Description: str | None = None
    KmsKeyId: str | None = None
    RotationEnabled: bool | None = None
    RotationLambdaARN: str | None = None
    LastRotatedDate: str | None = None
    LastChangedDate: str | None = None
    LastAccessedDate: str | None = None
    DeletedDate: str | None = None
    Tags: list[dict[str, object]] | None = None
    SecretVersionsToStages: dict[str, list[str]] | None = None


class SecretsManagerGetSecretValueRequest(BaseModel):
    """Request to get secret value. sm.get_secret_value()"""

    SecretId: str | None = None
    VersionId: str | None = None
    VersionStage: str | None = None


class SecretsManagerGetSecretValueResponse(BaseModel):
    """Secret value response. Equivalent of GCP SecretAccessResponse."""

    ARN: str | None = None
    Name: str | None = None
    VersionId: str | None = None
    SecretBinary: bytes | None = None
    SecretString: str | None = None
    VersionStages: list[str] | None = None
    CreatedDate: str | None = None


class SecretsManagerCreateSecretRequest(BaseModel):
    """Create a new secret. sm.create_secret()"""

    Name: str | None = None
    Description: str | None = None
    KmsKeyId: str | None = None
    SecretString: str | None = None
    SecretBinary: bytes | None = None
    Tags: list[dict[str, object]] | None = None
    AddReplicaRegions: list[dict[str, object]] | None = None
