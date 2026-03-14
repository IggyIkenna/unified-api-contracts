"""
AWS SDK (boto3) Type Protocols

Protocol definitions for boto3 clients used in unified-trading-library.
Based on actual boto3 API surface area from aws_clients.py usage.
"""

from __future__ import annotations

import io
from collections.abc import Callable, Iterator
from typing import Protocol

# boto3 S3 transfer types (per boto3.s3.transfer docs):
# - Callback: callable(bytes_transferred: int) -> None
# - Config: boto3.s3.transfer.TransferConfig (use object to avoid boto3 dep)
# - Fileobj: file-like object opened in binary mode (io.BufferedIOBase)
S3TransferCallback = Callable[[int], None]
S3TransferConfig = object  # boto3.s3.transfer.TransferConfig
S3Fileobj = io.BufferedIOBase


class PaginatorProtocol(Protocol):
    """boto3 Paginator protocol."""

    def paginate(self, **kwargs: object) -> Iterator[dict[str, object]]: ...


class S3ClientProtocol(Protocol):
    """
    Protocol for boto3 S3 client.

    Defines only the methods actually used in unified-trading-library/core/aws_clients.py.
    Prevents ~500+ unknown type errors from boto3's dynamic client.
    """

    def upload_file(
        self,
        Filename: str,
        Bucket: str,
        Key: str,
        ExtraArgs: dict[str, str | int | bool | bytes | None] | None = None,
        Callback: S3TransferCallback | None = None,
        Config: S3TransferConfig | None = None,
    ) -> None:
        """Upload a file to S3."""
        ...

    def upload_fileobj(
        self,
        Fileobj: S3Fileobj,
        Bucket: str,
        Key: str,
        ExtraArgs: dict[str, str | int | bool | bytes | None] | None = None,
        Callback: S3TransferCallback | None = None,
        Config: S3TransferConfig | None = None,
    ) -> None:
        """Upload a file-like object to S3."""
        ...

    def download_file(
        self,
        Bucket: str,
        Key: str,
        Filename: str,
        ExtraArgs: dict[str, str | int | bool | bytes | None] | None = None,
        Callback: S3TransferCallback | None = None,
        Config: S3TransferConfig | None = None,
    ) -> None:
        """Download a file from S3."""
        ...

    def download_fileobj(
        self,
        Bucket: str,
        Key: str,
        Fileobj: S3Fileobj,
        ExtraArgs: dict[str, str | int | bool | bytes | None] | None = None,
        Callback: S3TransferCallback | None = None,
        Config: S3TransferConfig | None = None,
    ) -> None:
        """Download an S3 object to a file-like object."""
        ...

    def get_object(
        self,
        Bucket: str,
        Key: str,
        Range: str | None = None,
        **kwargs: object,
    ) -> dict[str, object]:
        """Retrieve an object from S3."""
        ...

    def get_paginator(self, operation_name: str) -> PaginatorProtocol:
        """Create a paginator for an operation."""
        ...

    def head_object(
        self,
        Bucket: str,
        Key: str,
        **kwargs: object,
    ) -> dict[str, object]:
        """Retrieve metadata from an object without returning the object itself."""
        ...

    def delete_object(
        self,
        Bucket: str,
        Key: str,
        **kwargs: object,
    ) -> dict[str, object]:
        """Delete an object from S3."""
        ...

    def delete_objects(
        self,
        Bucket: str,
        Delete: dict[str, object],
        **kwargs: object,
    ) -> dict[str, object]:
        """Delete multiple objects from S3."""
        ...

    def copy_object(
        self,
        CopySource: dict[str, str],
        Bucket: str,
        Key: str,
        **kwargs: object,
    ) -> dict[str, object]:
        """Copy an object from one S3 location to another."""
        ...


class SecretsManagerClientProtocol(Protocol):
    """
    Protocol for boto3 Secrets Manager client.

    Placeholder - methods TBD based on actual usage in unified-trading-library.
    """

    def get_secret_value(
        self,
        SecretId: str,
        **kwargs: object,
    ) -> dict[str, object]:
        """Retrieve the value of a secret."""
        ...

    def create_secret(
        self,
        Name: str,
        SecretString: str | None = None,
        SecretBinary: bytes | None = None,
        **kwargs: object,
    ) -> dict[str, object]:
        """Create a new secret."""
        ...

    def list_secrets(
        self,
        **kwargs: object,
    ) -> dict[str, object]:
        """List secrets."""
        ...
