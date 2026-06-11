"""Prediction hand-written ``SchemaSpec`` column tuples (CF-18 CITADEL —
carry ALL source columns; operator ratification 2026-06-11 decision #2).

Derived from ACTUAL prod parquet footers (CF-18 sampling over
``orphan_sweep_prediction.parquet``, 2026-06-11):

- ``trades`` — the polymarket CLOB trade rows under the current
  ``asset_group=`` shape. Source carries BOTH legacy camelCase
  (``conditionId`` / ``outcomeIndex`` / ``transactionHash``) and the
  canonical snake_case twins — the camelCase names are declared as
  ``source_aliases`` (the migrator rename map), never as duplicate canonical
  columns.
- ``prediction_trades`` — the legacy ``category=`` polymarket data-api trade
  corpus (per-condition files, ``_migrated_`` suffix epoch) carrying the
  trader-profile payload (``proxyWallet`` / ``pseudonym`` / ``bio`` /
  ``profileImage`` …) the CLOB shape does not.
"""

from __future__ import annotations

from unified_api_contracts.registry._schema_spec_types import ColumnSpec

PREDICTION_TRADES_COLUMNS: tuple[ColumnSpec, ...] = (
    ColumnSpec("instrument_id", "string"),
    ColumnSpec("venue", "string"),
    ColumnSpec("condition_id", "string", source_aliases=("conditionId",)),
    ColumnSpec("outcome", "string"),
    ColumnSpec("outcome_index", "int64", nullable=True, source_aliases=("outcomeIndex",)),
    ColumnSpec("price", "float64", description="Implied probability 0-1"),
    ColumnSpec("size", "float64"),
    ColumnSpec("amount", "float64", nullable=True, description="Trade notional (price x size)"),
    ColumnSpec("side", "string"),
    ColumnSpec("trade_id", "string"),
    ColumnSpec("transaction_hash", "string", nullable=True, source_aliases=("transactionHash",)),
    ColumnSpec("asset", "string", nullable=True, description="Polymarket asset/token id"),
    ColumnSpec("symbol", "string", nullable=True),
    ColumnSpec("underlying", "string", nullable=True),
    ColumnSpec("market_type", "string", nullable=True),
    ColumnSpec("resolution_period", "string", nullable=True),
    ColumnSpec("timestamp", "timestamp[us, UTC]", nullable=True, description="Source trade timestamp"),
    ColumnSpec("captured_at", "timestamp[us, UTC]"),
    ColumnSpec(
        "source",
        "string",
        nullable=True,
        source_aliases=("data_source",),
        description="Row-level provenance (legacy data_source)",
    ),
)

PREDICTION_PREDICTION_TRADES_COLUMNS: tuple[ColumnSpec, ...] = (
    ColumnSpec("condition_id", "string", source_aliases=("conditionId",)),
    ColumnSpec("outcome", "string"),
    ColumnSpec("outcome_index", "int64", nullable=True, source_aliases=("outcomeIndex",)),
    ColumnSpec("price", "float64", description="Implied probability 0-1"),
    ColumnSpec("size", "float64"),
    ColumnSpec("side", "string"),
    ColumnSpec("transaction_hash", "string", nullable=True, source_aliases=("transactionHash",)),
    ColumnSpec("timestamp", "timestamp[us, UTC]", description="Source trade timestamp"),
    ColumnSpec("asset", "string", nullable=True, description="Polymarket asset/token id"),
    ColumnSpec("symbol", "string", nullable=True),
    ColumnSpec("underlying", "string", nullable=True),
    ColumnSpec("title", "string", nullable=True, description="Market title"),
    ColumnSpec("slug", "string", nullable=True),
    ColumnSpec("event_slug", "string", nullable=True, source_aliases=("eventSlug",)),
    ColumnSpec("icon", "string", nullable=True),
    # Trader-profile payload (polymarket data-api)
    ColumnSpec("proxy_wallet", "string", nullable=True, source_aliases=("proxyWallet",)),
    ColumnSpec("name", "string", nullable=True),
    ColumnSpec("pseudonym", "string", nullable=True),
    ColumnSpec("bio", "string", nullable=True),
    ColumnSpec("profile_image", "string", nullable=True, source_aliases=("profileImage",)),
    ColumnSpec("profile_image_optimized", "string", nullable=True, source_aliases=("profileImageOptimized",)),
)

__all__ = [
    "PREDICTION_PREDICTION_TRADES_COLUMNS",
    "PREDICTION_TRADES_COLUMNS",
]
