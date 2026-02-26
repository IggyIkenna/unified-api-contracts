"""
Cloud SDK Type Protocols

Protocol definitions for AWS (boto3) and GCP cloud SDK clients.
These provide proper typing without requiring the actual SDKs to be installed.

Used by: unified-cloud-services for type hints on dynamically created clients.
"""

from api_contracts.cloud_sdks.aws import S3ClientProtocol, SecretsManagerClientProtocol
from api_contracts.cloud_sdks.gcp import (
    BigQueryClientProtocol,
    SecretManagerServiceClientProtocol,
    StorageClientProtocol,
)

__all__ = [
    "BigQueryClientProtocol",
    "S3ClientProtocol",
    "SecretManagerServiceClientProtocol",
    "SecretsManagerClientProtocol",
    "StorageClientProtocol",
]
