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

The legacy ``prediction_trades`` schema (the ``category=`` polymarket data-api
trade corpus carrying the trader-profile payload) was retired 2026-07-19: the
prod manifest migration folded every ``prediction_trades`` row into canonical
``trades`` (0 captured cells lost), so no ``prediction_trades`` shard remains to
validate.
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

__all__ = [
    "PREDICTION_TRADES_COLUMNS",
]
