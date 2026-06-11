"""TradFi hand-written ``SchemaSpec`` column tuples (CF-18 CITADEL — carry ALL
source columns; operator ratification 2026-06-11 decision #2).

Derived from ACTUAL prod parquet footers (CF-18 sampling over
``orphan_sweep_tradfi.parquet``, 2026-06-11) canonicalised from the
databento contract surface in ``unified_api_contracts.external.databento``
(``DatabentoOhlcvBar`` / ``DatabentoTrade`` / ``DatabentoTbbo``): the MTDS
databento adapter renames ``ts_event``→``timestamp`` and ``size``→``amount``
at ingestion (declared here as ``source_aliases`` so the legacy corpus that
still carries the raw names is CARRIED, not silently truncated) and enriches
with symbology (``symbol`` / ``underlying``) + session metadata
(``phase`` / ``session`` / ``lifecycle_phase``).

Sampled venue epochs covered: CME / ICE / NASDAQ / NYSE (databento, current +
legacy), CBOE + blank-venue legacy nautilus-shaped bars (``ts_event`` /
``ts_init`` / ``instrument_key``), FX daily bars.
"""

from __future__ import annotations

from unified_api_contracts.registry._schema_spec_types import ColumnSpec

# Shared OHLCV bar — one canonical bar contract for ohlcv_1m / ohlcv_15m /
# ohlcv_24h (timeframe is a path/manifest axis, never a schema fork).
TRADFI_OHLCV_COLUMNS: tuple[ColumnSpec, ...] = (
    ColumnSpec("open", "float64"),
    ColumnSpec("high", "float64"),
    ColumnSpec("low", "float64"),
    ColumnSpec("close", "float64"),
    ColumnSpec("volume", "float64", nullable=True),
    ColumnSpec("timestamp", "timestamp[us, UTC]", nullable=True, description="Canonical bar timestamp (close edge)"),
    ColumnSpec(
        "ts_event",
        "int64",
        nullable=True,
        description="Legacy databento/nautilus event stamp (ns, open edge) — carried verbatim",
    ),
    ColumnSpec("ts_init", "int64", nullable=True, description="Legacy nautilus init stamp (ns) — carried verbatim"),
    ColumnSpec("symbol", "string", nullable=True),
    ColumnSpec("underlying", "string", nullable=True),
    ColumnSpec(
        "instrument_key", "string", nullable=True, description="Legacy pre-v9 instrument key (carried verbatim)"
    ),
    ColumnSpec("publisher_id", "int64", nullable=True, description="Databento publisher/venue id"),
    ColumnSpec("rtype", "int64", nullable=True, description="Databento record type"),
    ColumnSpec("phase", "string", nullable=True, description="Trading-session phase"),
    ColumnSpec("session", "string", nullable=True),
    ColumnSpec("lifecycle_phase", "string", nullable=True, description="Instrument lifecycle phase at capture"),
)

TRADFI_TRADES_COLUMNS: tuple[ColumnSpec, ...] = (
    ColumnSpec(
        "timestamp",
        "timestamp[us, UTC]",
        source_aliases=("ts_event",),
        description="Trade timestamp (databento ts_event canonicalised)",
    ),
    ColumnSpec("action", "string", nullable=True, description="Databento action (T=trade)"),
    ColumnSpec("side", "string", nullable=True, description="Aggressor side (A=ask/sell, B=bid/buy, N=none)"),
    ColumnSpec("price", "float64"),
    ColumnSpec("amount", "float64", source_aliases=("size",), description="Trade size (databento size canonicalised)"),
    ColumnSpec("depth", "int64", nullable=True),
    ColumnSpec("flags", "int64", nullable=True),
    ColumnSpec("sequence", "int64", nullable=True),
    ColumnSpec("ts_in_delta", "int64", nullable=True, description="Matching-engine send delta (ns)"),
    ColumnSpec("publisher_id", "int64", nullable=True),
    ColumnSpec("rtype", "int64", nullable=True),
    ColumnSpec("symbol", "string", nullable=True),
    ColumnSpec("underlying", "string", nullable=True),
    ColumnSpec("phase", "string", nullable=True),
    ColumnSpec("session", "string", nullable=True),
    ColumnSpec("lifecycle_phase", "string", nullable=True),
)

TRADFI_TBBO_COLUMNS: tuple[ColumnSpec, ...] = (
    ColumnSpec("timestamp", "timestamp[us, UTC]", nullable=True, description="Canonical trade timestamp"),
    ColumnSpec("ts_event", "int64", nullable=True, description="Legacy databento event stamp (ns) — carried verbatim"),
    ColumnSpec("action", "string", nullable=True, description="Always T for TBBO"),
    ColumnSpec("side", "string", nullable=True),
    ColumnSpec("price", "float64"),
    ColumnSpec("amount", "float64", source_aliases=("size",), description="Trade size (databento size canonicalised)"),
    ColumnSpec("depth", "int64", nullable=True),
    ColumnSpec("flags", "int64", nullable=True),
    ColumnSpec("sequence", "int64", nullable=True),
    ColumnSpec("ts_in_delta", "int64", nullable=True),
    ColumnSpec("publisher_id", "int64", nullable=True),
    ColumnSpec("rtype", "int64", nullable=True),
    ColumnSpec("symbol", "string", nullable=True),
    ColumnSpec("underlying", "string", nullable=True),
    ColumnSpec("bid_px_00", "float64"),
    ColumnSpec("ask_px_00", "float64"),
    ColumnSpec("bid_sz_00", "float64"),
    ColumnSpec("ask_sz_00", "float64"),
    ColumnSpec("bid_ct_00", "int64", nullable=True),
    ColumnSpec("ask_ct_00", "int64", nullable=True),
)

# Legacy CME options corpus is OHLCV-shaped (per-contract bars under
# data_type=options_chain) — carried alongside the chain-snapshot fields.
TRADFI_OPTIONS_CHAIN_LEGACY_BAR_COLUMNS: tuple[ColumnSpec, ...] = (
    ColumnSpec("open", "float64", nullable=True, description="Legacy CME per-contract bar (options_chain corpus)"),
    ColumnSpec("high", "float64", nullable=True),
    ColumnSpec("low", "float64", nullable=True),
    ColumnSpec("close", "float64", nullable=True),
    ColumnSpec("volume", "float64", nullable=True),
    ColumnSpec(
        "ts_event", "int64", nullable=True, description="Legacy databento/nautilus event stamp (ns) — carried verbatim"
    ),
    ColumnSpec("ts_init", "int64", nullable=True),
    ColumnSpec(
        "instrument_key", "string", nullable=True, description="Legacy pre-v9 instrument key (carried verbatim)"
    ),
)

__all__ = [
    "TRADFI_OHLCV_COLUMNS",
    "TRADFI_OPTIONS_CHAIN_LEGACY_BAR_COLUMNS",
    "TRADFI_TBBO_COLUMNS",
    "TRADFI_TRADES_COLUMNS",
]
