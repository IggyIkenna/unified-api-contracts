"""CeFi / TradFi snapshot SchemaContracts — options_chain / futures_chain /
combo_chain / tbbo / ohlcv_24h.

Added under ``data_status_institutional_drilldown_2026_04_24`` to close the
DataType-enum ↔ CONTRACT_REGISTRY coverage gap. Distinct from the trade
contracts (``*_CHAIN_TRADES``): snapshots capture a point-in-time surface
(Greeks, IV, BBO, 24h rolling candle) rather than a per-trade event stream.

Split out of ``contracts.py`` to keep that module under the 900-line
codex-compliance limit. Imported at module load time by ``contracts.py`` via
a side-effect import so the mutations to ``CONTRACT_REGISTRY`` happen before
any consumer performs a lookup.

Do NOT import this module directly — import from
``unified_api_contracts.internal.schemas.contracts`` which re-exports the
public SchemaContract names.
"""

from __future__ import annotations

from unified_api_contracts.internal.schemas.contracts import (
    CONTRACT_REGISTRY,
    EXPIRY_DATE_COL,
    INSTRUMENT_ID_COL,
    OPTION_RIGHT_COL,
    STRIKE_COL,
    SYMBOL_COL,
    TS_EVENT_COL,
    UNDERLYING_COL,
    VENUE_COL,
    ColumnSpec,
    SchemaContract,
)

# Aliases for local use
_INSTRUMENT_ID = INSTRUMENT_ID_COL
_SYMBOL = SYMBOL_COL
_TS_EVENT = TS_EVENT_COL
_UNDERLYING = UNDERLYING_COL
_VENUE = VENUE_COL
_STRIKE = STRIKE_COL
_EXPIRY_DATE = EXPIRY_DATE_COL
_OPTION_RIGHT = OPTION_RIGHT_COL

# ---------------------------------------------------------------------------
# Options / futures / combo chain SNAPSHOTS
# ---------------------------------------------------------------------------
# Chain snapshots capture the full per-expiry / per-strike surface at a
# point in time (Tardis options_chain + futures_chain bulk CSVs, Deribit
# combo books, IBKR option chain pulls). ``venue`` is the writing venue —
# not every venue publishes Greeks / IV / mark_iv / underlying_price (only
# Deribit exposes IV via Tardis), so those columns carry
# ``provided_by_venues``.

CEFI_OPTIONS_CHAIN_SNAPSHOT = SchemaContract(
    category="cefi",
    instrument_type="options_chain",
    data_type="options_chain",
    columns=[
        _INSTRUMENT_ID,
        _VENUE,
        _UNDERLYING,
        _TS_EVENT,
        _STRIKE,
        _EXPIRY_DATE,
        _OPTION_RIGHT,
        ColumnSpec(name="bid_price", dtype="float64", nullable=True),
        ColumnSpec(name="ask_price", dtype="float64", nullable=True),
        ColumnSpec(name="bid_size", dtype="float64", nullable=True),
        ColumnSpec(name="ask_size", dtype="float64", nullable=True),
        ColumnSpec(name="last_price", dtype="float64", nullable=True),
        ColumnSpec(name="open_interest", dtype="float64", nullable=True),
        ColumnSpec(name="volume", dtype="float64", nullable=True),
        ColumnSpec(
            name="mark_iv",
            dtype="float64",
            nullable=True,
            required=False,
            provided_by_venues=frozenset({"DERIBIT"}),
            description="Deribit-only mark implied volatility.",
        ),
        ColumnSpec(
            name="greeks_delta",
            dtype="float64",
            nullable=True,
            required=False,
            provided_by_venues=frozenset({"DERIBIT"}),
        ),
        ColumnSpec(
            name="greeks_gamma",
            dtype="float64",
            nullable=True,
            required=False,
            provided_by_venues=frozenset({"DERIBIT"}),
        ),
        ColumnSpec(
            name="greeks_vega",
            dtype="float64",
            nullable=True,
            required=False,
            provided_by_venues=frozenset({"DERIBIT"}),
        ),
        ColumnSpec(
            name="greeks_theta",
            dtype="float64",
            nullable=True,
            required=False,
            provided_by_venues=frozenset({"DERIBIT"}),
        ),
        ColumnSpec(
            name="underlying_price",
            dtype="float64",
            nullable=True,
            required=False,
            provided_by_venues=frozenset({"DERIBIT"}),
        ),
    ],
    symbol_column="underlying",
    required_row_count_min=1,
)

CEFI_FUTURES_CHAIN_SNAPSHOT = SchemaContract(
    category="cefi",
    instrument_type="futures_chain",
    data_type="futures_chain",
    columns=[
        _INSTRUMENT_ID,
        _VENUE,
        _UNDERLYING,
        _TS_EVENT,
        _EXPIRY_DATE,
        ColumnSpec(name="bid_price", dtype="float64", nullable=True),
        ColumnSpec(name="ask_price", dtype="float64", nullable=True),
        ColumnSpec(name="bid_size", dtype="float64", nullable=True),
        ColumnSpec(name="ask_size", dtype="float64", nullable=True),
        ColumnSpec(name="last_price", dtype="float64", nullable=True),
        ColumnSpec(name="open_interest", dtype="float64", nullable=True),
        ColumnSpec(name="volume", dtype="float64", nullable=True),
        ColumnSpec(name="mark_price", dtype="float64", nullable=True),
    ],
    symbol_column="underlying",
    required_row_count_min=1,
)

# Deribit combo instruments (calendar spreads, iron condors, butterflies).
CEFI_COMBO_CHAIN_SNAPSHOT = SchemaContract(
    category="cefi",
    instrument_type="combo_chain",
    data_type="combo_chain",
    columns=[
        _INSTRUMENT_ID,
        _VENUE,
        _UNDERLYING,
        _TS_EVENT,
        ColumnSpec(name="combo_symbol", dtype="string", nullable=False),
        ColumnSpec(
            name="leg_symbols",
            dtype="string",
            nullable=False,
            description="Comma-joined list of per-leg canonical symbols.",
        ),
        ColumnSpec(name="bid_price", dtype="float64", nullable=True),
        ColumnSpec(name="ask_price", dtype="float64", nullable=True),
        ColumnSpec(name="bid_size", dtype="float64", nullable=True),
        ColumnSpec(name="ask_size", dtype="float64", nullable=True),
        ColumnSpec(name="last_price", dtype="float64", nullable=True),
        ColumnSpec(name="open_interest", dtype="float64", nullable=True),
        ColumnSpec(name="volume", dtype="float64", nullable=True),
    ],
    symbol_column="combo_symbol",
    required_row_count_min=1,
)

TRADFI_OPTIONS_CHAIN_SNAPSHOT = SchemaContract(
    category="tradfi",
    instrument_type="options_chain",
    data_type="options_chain",
    columns=[
        _INSTRUMENT_ID,
        _VENUE,
        _UNDERLYING,
        _TS_EVENT,
        _STRIKE,
        _EXPIRY_DATE,
        _OPTION_RIGHT,
        ColumnSpec(name="bid_price", dtype="float64", nullable=True),
        ColumnSpec(name="ask_price", dtype="float64", nullable=True),
        ColumnSpec(name="bid_size", dtype="float64", nullable=True),
        ColumnSpec(name="ask_size", dtype="float64", nullable=True),
        ColumnSpec(name="last_price", dtype="float64", nullable=True),
        ColumnSpec(name="open_interest", dtype="float64", nullable=True),
        ColumnSpec(name="volume", dtype="float64", nullable=True),
    ],
    symbol_column="underlying",
    required_row_count_min=1,
)

TRADFI_FUTURES_CHAIN_SNAPSHOT = SchemaContract(
    category="tradfi",
    instrument_type="futures_chain",
    data_type="futures_chain",
    columns=[
        _INSTRUMENT_ID,
        _VENUE,
        _UNDERLYING,
        _TS_EVENT,
        _EXPIRY_DATE,
        ColumnSpec(name="bid_price", dtype="float64", nullable=True),
        ColumnSpec(name="ask_price", dtype="float64", nullable=True),
        ColumnSpec(name="bid_size", dtype="float64", nullable=True),
        ColumnSpec(name="ask_size", dtype="float64", nullable=True),
        ColumnSpec(name="last_price", dtype="float64", nullable=True),
        ColumnSpec(name="open_interest", dtype="float64", nullable=True),
        ColumnSpec(name="volume", dtype="float64", nullable=True),
    ],
    symbol_column="underlying",
    required_row_count_min=1,
)

# ---------------------------------------------------------------------------
# Top bid/offer snapshots (tbbo) — tick-level NBBO, CeFi spot + perp.
# ---------------------------------------------------------------------------

CEFI_PERPETUAL_TBBO = SchemaContract(
    category="cefi",
    instrument_type="perpetual",
    data_type="tbbo",
    columns=[
        _INSTRUMENT_ID,
        _SYMBOL,
        _TS_EVENT,
        ColumnSpec(name="bid_price", dtype="float64", nullable=False),
        ColumnSpec(name="ask_price", dtype="float64", nullable=False),
        ColumnSpec(name="bid_size", dtype="float64", nullable=True),
        ColumnSpec(name="ask_size", dtype="float64", nullable=True),
    ],
    symbol_column="symbol",
    required_row_count_min=1,
)

CEFI_SPOT_PAIR_TBBO = SchemaContract(
    category="cefi",
    instrument_type="spot_pair",
    data_type="tbbo",
    columns=[
        _INSTRUMENT_ID,
        _SYMBOL,
        _TS_EVENT,
        ColumnSpec(name="bid_price", dtype="float64", nullable=False),
        ColumnSpec(name="ask_price", dtype="float64", nullable=False),
        ColumnSpec(name="bid_size", dtype="float64", nullable=True),
        ColumnSpec(name="ask_size", dtype="float64", nullable=True),
    ],
    symbol_column="symbol",
    required_row_count_min=1,
)

# ---------------------------------------------------------------------------
# 24-hour rolling OHLCV — single row per instrument.
# ---------------------------------------------------------------------------

CEFI_PERPETUAL_OHLCV_24H = SchemaContract(
    category="cefi",
    instrument_type="perpetual",
    data_type="ohlcv_24h",
    columns=[
        _INSTRUMENT_ID,
        _SYMBOL,
        _TS_EVENT,
        ColumnSpec(name="open", dtype="float64", nullable=False),
        ColumnSpec(name="high", dtype="float64", nullable=False),
        ColumnSpec(name="low", dtype="float64", nullable=False),
        ColumnSpec(name="close", dtype="float64", nullable=False),
        ColumnSpec(name="volume", dtype="float64", nullable=True),
    ],
    symbol_column="symbol",
    required_row_count_min=1,
)

CEFI_SPOT_PAIR_OHLCV_24H = SchemaContract(
    category="cefi",
    instrument_type="spot_pair",
    data_type="ohlcv_24h",
    columns=[
        _INSTRUMENT_ID,
        _SYMBOL,
        _TS_EVENT,
        ColumnSpec(name="open", dtype="float64", nullable=False),
        ColumnSpec(name="high", dtype="float64", nullable=False),
        ColumnSpec(name="low", dtype="float64", nullable=False),
        ColumnSpec(name="close", dtype="float64", nullable=False),
        ColumnSpec(name="volume", dtype="float64", nullable=True),
    ],
    symbol_column="symbol",
    required_row_count_min=1,
)


# ---------------------------------------------------------------------------
# Registry side-effects
# ---------------------------------------------------------------------------

CONTRACT_REGISTRY.update(
    {
        ("cefi", "options_chain", "options_chain"): CEFI_OPTIONS_CHAIN_SNAPSHOT,
        ("cefi", "futures_chain", "futures_chain"): CEFI_FUTURES_CHAIN_SNAPSHOT,
        ("cefi", "combo_chain", "combo_chain"): CEFI_COMBO_CHAIN_SNAPSHOT,
        ("cefi", "perpetual", "tbbo"): CEFI_PERPETUAL_TBBO,
        ("cefi", "spot_pair", "tbbo"): CEFI_SPOT_PAIR_TBBO,
        ("cefi", "perpetual", "ohlcv_24h"): CEFI_PERPETUAL_OHLCV_24H,
        ("cefi", "spot_pair", "ohlcv_24h"): CEFI_SPOT_PAIR_OHLCV_24H,
        ("tradfi", "options_chain", "options_chain"): TRADFI_OPTIONS_CHAIN_SNAPSHOT,
        ("tradfi", "futures_chain", "futures_chain"): TRADFI_FUTURES_CHAIN_SNAPSHOT,
    }
)


__all__ = [
    "CEFI_COMBO_CHAIN_SNAPSHOT",
    "CEFI_FUTURES_CHAIN_SNAPSHOT",
    "CEFI_OPTIONS_CHAIN_SNAPSHOT",
    "CEFI_PERPETUAL_OHLCV_24H",
    "CEFI_PERPETUAL_TBBO",
    "CEFI_SPOT_PAIR_OHLCV_24H",
    "CEFI_SPOT_PAIR_TBBO",
    "TRADFI_FUTURES_CHAIN_SNAPSHOT",
    "TRADFI_OPTIONS_CHAIN_SNAPSHOT",
]
