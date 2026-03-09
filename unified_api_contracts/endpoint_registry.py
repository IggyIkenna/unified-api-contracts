"""Endpoint registry with access mode and version metadata for all venues.

EndpointSpec enables consumers to understand:
- Whether an endpoint is streaming vs polling vs batch file download
- Whether historical data is available, live-only, or both
- API version, deprecation dates, and migration notes

This is complementary to ENDPOINT_SCHEMA_MAP (which maps to schema classes) and
venue_manifest.py (which describes per-venue capability coverage).

ENDPOINT_REGISTRY data lives in _endpoint_registry_data.py (SRP size split).
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel


class AccessMode(StrEnum):
    """How data is accessed from this endpoint."""

    REST_POLLING = "rest_polling"
    STREAMING_WEBSOCKET = "streaming_websocket"
    STREAMING_SSE = "streaming_sse"
    BATCH_FILE = "batch_file"  # e.g. Tardis full-day zstd files, Barchart CSV dumps
    GRAPHQL = "graphql"  # The Graph subgraph queries
    ON_CHAIN = "on_chain"  # Direct smart contract calls / eth_call


class DataAvailability(StrEnum):
    """Temporal data availability of this endpoint."""

    HISTORICAL_ONLY = "historical_only"
    LIVE_ONLY = "live_only"
    BOTH = "both"


class ResponseFormat(StrEnum):
    """Serialization format of the response body."""

    JSON = "json"  # application/json — standard REST responses
    NDJSON = "ndjson"  # newline-delimited JSON — streaming, large datasets
    CSV = "csv"  # text/csv — Barchart, Soccer-Football-Info, some TradFi exports
    CSV_GZIP = "csv_gzip"  # gzip-compressed CSV — Tardis historical files
    CSV_ZST = "csv_zst"  # zstd-compressed CSV — some Tardis datasets
    DBN = "dbn"  # Databento Binary Notation — Databento batch/live (decoded via dbn library)
    DBN_ZST = "dbn_zst"  # zstd-compressed DBN — Databento batch file downloads
    PARQUET = "parquet"  # Apache Parquet — Polymarket historical datasets
    PROTOBUF = "protobuf"  # Protocol Buffers — some Google APIs, gRPC
    BINARY = "binary"  # Raw binary (venue-specific encoding)
    SSE = "sse"  # Server-Sent Events — some REST streaming endpoints
    GRPC = "grpc"  # gRPC binary — some Google Cloud SDK calls
    HTML = "html"  # text/html — scraping targets (Transfermarkt)
    TEXT = "text"  # plain text


class CassetteStatus(StrEnum):
    """VCR cassette recording status for this endpoint.

    RECORDED       — cassette YAML exists in the venue's mocks/ directory; replay works offline.
    AUTH_BLOCKED   — endpoint requires an API key / session token stored in Secret Manager;
                     cassette cannot be recorded in CI until the key is provisioned.
                     Secret Manager key name documented in ``notes``.
    NOT_APPLICABLE — endpoint cannot be cassette-recorded: WebSocket streams, binary batch
                     downloads (DBN, Parquet, CSV-GZ), or on-chain eth_call RPC calls.
    PENDING        — public endpoint where a cassette has not been recorded yet but could be.
    """

    RECORDED = "recorded"
    AUTH_BLOCKED = "auth_blocked"
    NOT_APPLICABLE = "not_applicable"
    PENDING = "pending"


class EndpointSpec(BaseModel):
    """Metadata for a single API endpoint, with versioning and access tagging.

    Used to document the endpoint universe per venue so consumers know:
    - Which schema class parses the response
    - Whether they need a streaming client or REST client
    - Whether to use this endpoint for backtesting (historical) or live trading
    - Any version or deprecation constraints

    Example::

        EndpointSpec(
            venue="kalshi",
            endpoint_path="/trade-api/v2/markets/{ticker}",
            http_method="GET",
            schema_class="KalshiMarket",
            access_mode=AccessMode.REST_POLLING,
            data_availability=DataAvailability.BOTH,
            version="v2",
            notes="Integer cent fields deprecated March 5 2026; use yes_bid_dollars",
            cassette_status=CassetteStatus.RECORDED,
        )
    """

    venue: str
    endpoint_path: str
    http_method: str | None = None  # GET, POST, DELETE, WS
    schema_class: str  # Name of the Pydantic class that parses this response
    access_mode: AccessMode
    data_availability: DataAvailability
    version: str | None = None  # API version string (e.g. "v2", "v5")
    deprecated_date: str | None = None  # ISO 8601 date endpoint retires
    available_from_date: str | None = None  # ISO 8601 when endpoint went live
    notes: str | None = None  # Migration notes, schema version quirks, etc.
    requires_auth: bool = True
    rate_limit_per_second: int | None = None
    response_format: ResponseFormat = ResponseFormat.JSON
    """Serialization format of the response. Determines how to decode the response body."""
    content_type_header: str | None = None
    """Expected Content-Type header value (e.g. 'application/json', 'text/csv', 'application/octet-stream')"""
    is_paginated: bool = False
    """Whether this endpoint returns paginated results requiring cursor/offset iteration."""
    pagination_style: str | None = None
    """Pagination mechanism: 'cursor', 'offset_limit', 'page_number', 'link_header', 'next_page_token'"""
    max_lookback_days: int | None = None
    """Maximum historical lookback in days (None = unlimited). Important for free tier constraints."""
    cassette_status: CassetteStatus = CassetteStatus.PENDING
    """VCR cassette recording status. Set to RECORDED once the mocks/ YAML is committed."""


# ENDPOINT_REGISTRY data lives in _endpoint_registry_data.py (SRP file-size split).
# Re-exported here so consumers always import from endpoint_registry, never the private data file.
from ._endpoint_registry_data import ENDPOINT_REGISTRY as ENDPOINT_REGISTRY  # noqa: E402

__all__ = [
    "ENDPOINT_REGISTRY",
    "AccessMode",
    "CassetteStatus",
    "DataAvailability",
    "EndpointSpec",
    "ResponseFormat",
]
