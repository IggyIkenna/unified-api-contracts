"""
GCP BigQuery: Pydantic request/response schemas.

Client: google.cloud.bigquery.Client (sync)
Sync: Client is sync. Use asyncio.to_thread() for async.
Async: No native async client; wrap query(), create_table() in executor.
"""

from pydantic import BaseModel, Field

# --- Query request ---


class QueryRequest(BaseModel):
    """Request for Client.query() / query_and_wait()."""

    query: str = Field(..., description="SQL query string")
    job_config: dict[str, object] | None = Field(
        None,
        description="QueryJobConfig (destination, dry_run, etc.)",
    )
    location: str | None = Field(None, description="Job location")
    project: str | None = Field(None, description="Project ID")


# --- Table create ---


class TableCreateRequest(BaseModel):
    """Request for Client.create_table()."""

    table: dict[str, object] = Field(
        ...,
        description="Table resource (tableReference, schema, etc.)",
    )
    exists_ok: bool = Field(False, description="Ignore already-exists errors")


# --- External table (Hive partitioning) ---


class HivePartitioningOptions(BaseModel):
    """Hive-style partitioning for external tables."""

    mode: str | None = Field(None, description="AUTO, CUSTOM, or STRINGS")
    source_uri_prefix: str | None = Field(
        None,
        description="Common URI prefix (required for CUSTOM)",
    )
    require_partition_filter: bool = Field(
        False,
        description="Require partition filter in queries",
    )


class ExternalTableConfig(BaseModel):
    """External table definition with Hive partitioning."""

    source_format: str = Field(..., description="PARQUET, CSV, JSON, AVRO, ORC")
    source_uris: list[str] = Field(..., description="GCS URIs (gs://bucket/path/*)")
    hive_partitioning_options: HivePartitioningOptions | None = Field(
        None,
        description="Hive partitioning config",
    )
    autodetect: bool = Field(True, description="Auto-detect schema")


class ExternalTableCreateRequest(BaseModel):
    """Request for creating external table with ExternalConfig."""

    table_reference: dict[str, str] = Field(
        ...,
        description="projectId, datasetId, tableId",
    )
    external_config: ExternalTableConfig = Field(
        ...,
        description="External data config",
    )


# --- Response schemas ---


class QueryJobResult(BaseModel):
    """Query job result (simplified)."""

    job_id: str | None = None
    total_rows: int | None = None
    table_schema: list[dict[str, object]] | None = Field(
        None,
        description="Result table schema (alias: schema in BQ API)",
    )


class TableInfo(BaseModel):
    """Table metadata (simplified)."""

    table_id: str | None = None
    dataset_id: str | None = None
    project: str | None = None
    num_rows: int | None = None
    num_bytes: int | None = None


# --- Quota ---


class BqQuotaUsage(BaseModel):
    """BigQuery quota usage for monitoring."""

    project_id: str = Field(..., description="Project ID")
    datasets_count: int = Field(0, description="Number of datasets")
    tables_count: int = Field(0, description="Number of tables")
    query_bytes_processed: int = Field(0, description="Bytes processed by queries")
