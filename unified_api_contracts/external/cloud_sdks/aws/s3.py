from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class S3CreateBucketRequest(BaseModel):
    """Request schema for s3.create_bucket()."""

    Bucket: str
    ACL: str | None = None
    CreateBucketConfiguration: dict[str, str] | None = None


class S3CreateBucketResponse(BaseModel):
    """Response from s3.create_bucket()."""

    Location: str | None = None


class S3ListObjectsV2Request(BaseModel):
    """Request schema for s3.list_objects_v2()."""

    Bucket: str
    Prefix: str | None = None
    Delimiter: str | None = None
    MaxKeys: int | None = 1000
    ContinuationToken: str | None = None
    StartAfter: str | None = None
    FetchOwner: bool | None = None


class S3ObjectOwner(BaseModel):
    """S3 object owner."""

    DisplayName: str | None = None
    ID: str | None = None


class S3ObjectSummary(BaseModel):
    """S3 object summary from list_objects_v2 Contents."""

    Key: str | None = None
    LastModified: datetime | None = None
    ETag: str | None = None
    Size: int | None = None
    StorageClass: str | None = None
    Owner: S3ObjectOwner | None = None


class S3ListObjectsV2Response(BaseModel):
    """Response from s3.list_objects_v2()."""

    IsTruncated: bool | None = None
    Contents: list[S3ObjectSummary] | None = None
    Name: str | None = None
    Prefix: str | None = None
    MaxKeys: int | None = None
    KeyCount: int | None = None
    NextContinuationToken: str | None = None
    ContinuationToken: str | None = None
    CommonPrefixes: list[dict[str, str]] | None = None


class S3PutObjectRequest(BaseModel):
    """Request schema for s3.put_object()."""

    Bucket: str
    Key: str
    Body: bytes | None = None
    ContentType: str | None = None
    ContentLength: int | None = None
    Metadata: dict[str, str] | None = None
    StorageClass: str | None = None


class S3PutObjectResponse(BaseModel):
    """Response from s3.put_object()."""

    ETag: str | None = None
    VersionId: str | None = None


class S3GetObjectRequest(BaseModel):
    """Request schema for s3.get_object()."""

    Bucket: str
    Key: str
    Range: str | None = None
    VersionId: str | None = None


class S3GetObjectResponse(BaseModel):
    """Response from s3.get_object(). Body is stream; metadata only here."""

    Body: object | None = None
    ContentLength: int | None = None
    ContentType: str | None = None
    ETag: str | None = None
    LastModified: datetime | None = None
    Metadata: dict[str, str] | None = None
