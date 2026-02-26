"""
GCP SDK Type Protocols

Protocol definitions for Google Cloud SDK clients used in unified-cloud-services.
Based on actual GCP API surface area from gcp_clients.py and cloud_auth_factory.py usage.
"""

import io
from collections.abc import Iterator
from datetime import datetime
from typing import Protocol

# google-cloud-storage Blob.upload_from_file/download_to_file: file_obj is a
# file handle opened in binary mode (per GCS docs)
GCSFileobj = io.BufferedIOBase


class BucketProtocol(Protocol):
    """google.cloud.storage.Bucket protocol."""

    name: str

    def blob(self, blob_name: str) -> "BlobProtocol": ...
    def list_blobs(
        self, prefix: str | None = None, delimiter: str | None = None, **kwargs: object
    ) -> Iterator["BlobProtocol"]: ...
    def get_blob(self, blob_name: str) -> "BlobProtocol | None": ...
    def delete_blob(self, blob_name: str) -> None: ...
    def exists(self) -> bool: ...
    def create(self, location: str | None = None, **kwargs: object) -> None: ...
    def copy_blob(
        self,
        source_blob: "BlobProtocol",
        destination_bucket: "BucketProtocol",
        new_name: str,
        **kwargs: object,
    ) -> "BlobProtocol": ...


class BlobProtocol(Protocol):
    """google.cloud.storage.Blob protocol."""

    name: str
    size: int | None
    content_type: str | None
    etag: str | None
    updated: datetime | None
    public_url: str | None

    def upload_from_filename(self, filename: str, content_type: str | None = None, **kwargs: object) -> None: ...
    def upload_from_file(self, file_obj: GCSFileobj, content_type: str | None = None, **kwargs: object) -> None: ...
    def upload_from_string(self, data: str | bytes, content_type: str | None = None, **kwargs: object) -> None: ...
    def download_to_filename(self, filename: str, **kwargs: object) -> None: ...
    def download_to_file(self, file_obj: GCSFileobj, **kwargs: object) -> None: ...
    def download_as_bytes(self, **kwargs: object) -> bytes: ...
    def download_as_text(self, **kwargs: object) -> str: ...
    def exists(self) -> bool: ...
    def reload(self) -> None: ...
    def delete(self) -> None: ...
    def copy_to(self, destination: "BlobProtocol", **kwargs: object) -> "BlobProtocol": ...


class StorageClientProtocol(Protocol):
    """
    Protocol for google.cloud.storage.Client.

    Defines methods used in unified-cloud-services/core/gcp_clients.py.
    """

    project: str | None

    def bucket(self, bucket_name: str) -> BucketProtocol: ...
    def list_buckets(self, max_results: int | None = None, **kwargs: object) -> Iterator[BucketProtocol]: ...
    def get_bucket(self, bucket_name: str) -> BucketProtocol: ...
    def create_bucket(self, bucket_name: str, **kwargs: object) -> BucketProtocol: ...


class QueryJobProtocol(Protocol):
    """google.cloud.bigquery.QueryJob protocol."""

    def result(self, timeout: float | None = None, **kwargs: object) -> object: ...


class BigQueryClientProtocol(Protocol):
    """
    Protocol for google.cloud.bigquery.Client.

    Defines methods used in unified-cloud-services/core/gcp_clients.py.
    """

    project: str | None

    def query(self, query: str, **kwargs: object) -> QueryJobProtocol: ...
    def get_table(self, table_ref: str | object, **kwargs: object) -> object: ...
    def list_tables(self, dataset_ref: str | object, **kwargs: object) -> Iterator[object]: ...
    def load_table_from_dataframe(self, dataframe: object, destination: str | object, **kwargs: object) -> object: ...


class SecretProtocol(Protocol):
    """google.cloud.secretmanager.Secret protocol."""

    name: str


class SecretManagerServiceClientProtocol(Protocol):
    """
    Protocol for google.cloud.secretmanager.SecretManagerServiceClient.

    Defines methods used in unified-cloud-services/core/secret_manager.py.
    """

    def list_secrets(
        self,
        request: dict[str, object] | None = None,
        parent: str | None = None,
        timeout: float | None = None,
        **kwargs: object,
    ) -> Iterator[SecretProtocol]: ...

    def access_secret_version(
        self,
        request: dict[str, object] | None = None,
        name: str | None = None,
        **kwargs: object,
    ) -> object: ...

    def create_secret(
        self,
        request: dict[str, object] | None = None,
        parent: str | None = None,
        secret_id: str | None = None,
        secret: object | None = None,
        **kwargs: object,
    ) -> object: ...
