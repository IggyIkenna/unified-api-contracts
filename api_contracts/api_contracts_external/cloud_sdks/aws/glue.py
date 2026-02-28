from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class GlueCreateTableRequest(BaseModel):
    """Request schema for glue.create_table()."""

    DatabaseName: str
    TableInput: dict[str, object]


class GlueCreateTableResponse(BaseModel):
    """Response from glue.create_table(). No response body."""

    model_config = {"extra": "allow"}


class GlueGetTableRequest(BaseModel):
    """Request for glue.get_table()."""

    DatabaseName: str
    Name: str
    CatalogId: str | None = None


class GlueTable(BaseModel):
    """Glue table from get_table/get_tables."""

    Name: str | None = None
    DatabaseName: str | None = None
    Description: str | None = None
    StorageDescriptor: dict[str, object] | None = None
    PartitionKeys: list[dict[str, object]] | None = None
    CreateTime: datetime | None = None
    UpdateTime: datetime | None = None


class GlueGetTableResponse(BaseModel):
    """Response from glue.get_table()."""

    Table: GlueTable | None = None


class GlueGetTablesRequest(BaseModel):
    """Request for glue.get_tables()."""

    DatabaseName: str
    CatalogId: str | None = None
    Expression: str | None = None
    NextToken: str | None = None
    MaxResults: int | None = None


class GlueGetTablesResponse(BaseModel):
    """Response from glue.get_tables()."""

    TableList: list[GlueTable] | None = None
    NextToken: str | None = None


class GlueGetDatabaseRequest(BaseModel):
    """Request for glue.get_database()."""

    Name: str
    CatalogId: str | None = None


class GlueDatabase(BaseModel):
    """Glue database from get_database."""

    Name: str | None = None
    Description: str | None = None
    LocationUri: str | None = None
    CreateTime: datetime | None = None


class GlueGetDatabaseResponse(BaseModel):
    """Response from glue.get_database()."""

    Database: GlueDatabase | None = None
