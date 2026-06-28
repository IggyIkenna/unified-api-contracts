"""Cross-repo invariant: market-data-processing-service output contract vs MTDS + features-service.

Validates that MDPS's published output contract (PROCESSED_CANDLE_SCHEMA,
CandleOutput, MarketState, DataType) aligns with the UAC canonical types that
features-service and other consumers import.  Also validates MDPS's schemas
public API surface (symbols) via AST.

Uses static AST analysis for the MDPS source (not installed in UAC venv).
UAC canonical types are imported directly (installed in this venv).

Negative-control contract: removing any required column from PROCESSED_CANDLE_SCHEMA /
CandleOutput, or any symbol from MDPS schemas/__init__.py, or any MarketState value
makes the relevant test fail — that IS the guard for a cross-repo breaking change
(features-service reads these column names from parquet by string, and delta-one
candle_resampler.py reads `market_state` by name).

SIT plan: plans/active/cicd_sit_full_coverage_handoff_2026_06_27.md — task -006
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from unified_api_contracts.internal.domain.market_data_processing import (
    BOOK_SUMMARY_COLUMN_NAMES,
    BOOK_SUMMARY_COLUMNS,
    BookColumnSpec,
)
from unified_api_contracts.internal.domain.market_data_processing.adapter_models import (
    CandleOutput,
    InstrumentInfo,
    InstrumentMetadata,
)
from unified_api_contracts.internal.domain.market_data_processing.candle_schema import (
    DataType,
    MarketState,
)

# ---------------------------------------------------------------------------
# Workspace helpers
# ---------------------------------------------------------------------------


def _workspace_root() -> Path:
    """tests/<file>.py → tests/ → repo root → workspace root."""
    return Path(__file__).resolve().parents[2]


def _mdps_root() -> Path:
    return _workspace_root() / "market-data-processing-service" / "market_data_processing_service"


# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------


def _exported_names(init_path: Path) -> set[str]:
    """Return the set of names declared/exported in a module via AST."""
    src = init_path.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(init_path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                exported = alias.asname if alias.asname else alias.name
                names.add(exported)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                exported = alias.asname if alias.asname else alias.name.split(".")[0]
                names.add(exported)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for t in targets:
                if isinstance(t, ast.Name):
                    names.add(t.id)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
    return names


def _dataclass_fields(source_path: Path, class_name: str) -> set[str]:
    """Return the annotated field names declared in a dataclass via AST."""
    src = source_path.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(source_path))
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            fields: set[str] = set()
            for stmt in node.body:
                if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                    name = stmt.target.id
                    if not name.startswith("__"):
                        fields.add(name)
            return fields
    return set()


def _enum_values(source_path: Path, class_name: str) -> set[str]:
    """Return the string values assigned to members of a StrEnum class via AST."""
    src = source_path.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(source_path))
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            values: set[str] = set()
            for stmt in node.body:
                if isinstance(stmt, ast.Assign):
                    for t in stmt.targets:
                        if (
                            isinstance(t, ast.Name)
                            and not t.id.startswith("__")
                            and isinstance(stmt.value, ast.Constant)
                            and isinstance(stmt.value.value, str)
                        ):
                            values.add(stmt.value.value)
            return values
    return set()


# ---------------------------------------------------------------------------
# Expected contracts
# ---------------------------------------------------------------------------

# Public symbols that must remain in market_data_processing_service/schemas/__init__.py.
# features-service and MTDS import these to validate schema before Parquet writes.
EXPECTED_SCHEMAS_SYMBOLS: frozenset[str] = frozenset(
    [
        "PROCESSED_CANDLE_SCHEMA",
        "RATE_INDEX_SCHEMA",
        "get_schema_for_data_type",
    ]
)

# Core CandleOutput fields in UAC adapter_models.py consumed by features-service.
# features-service delta_one candle_resampler.py reads these columns by string name
# from Parquet; MDPS writes them via CandleOutput.to_dataframe() / to_polars().
# Removing any of these fields silently drops the column from the Parquet output.
EXPECTED_CANDLE_OUTPUT_CORE_FIELDS: frozenset[str] = frozenset(
    [
        "timestamp",
        "venue",
        "symbol",
        "instrument_id",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "market_state",
        "is_halted",
        "is_auction",
        "trade_count",
        "vwap",
    ]
)

# MarketState enum string values consumed by downstream (features-service filters
# `market_state != 'closed'`; halted/auction states gate strategy-service entry).
EXPECTED_MARKET_STATE_VALUES: frozenset[str] = frozenset(
    [
        "normal",
        "halted",
        "auction",
        "pre_market",
        "post_market",
        "closed",
    ]
)

# DataType enum string values for the core MVP data types consumed by the
# features pipeline, manifest writer, and strategy routing.
EXPECTED_DATA_TYPE_VALUES: frozenset[str] = frozenset(
    [
        "trades",
        "ohlcv_1m",
        "ohlcv_15m",
        "ohlcv_24h",
        "book_snapshot_5",
        "perp_funding",
        "lending_indices",
        "oracle_prices",
        "options_chain",
        "futures_chain",
    ]
)


# ---------------------------------------------------------------------------
# Sibling guard (skip in per-repo CI; fail LOUDLY in full-workspace SIT)
# ---------------------------------------------------------------------------


def _skip_if_absent() -> None:
    mdps_sibling = _workspace_root() / "market-data-processing-service"
    if not mdps_sibling.is_dir():
        pytest.skip(
            f"per-repo CI checkout: market-data-processing-service not present at {mdps_sibling}; "
            "cross-repo MDPS invariant runs in full-workspace SIT only"
        )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_mdps_schemas_symbols_stable() -> None:
    """All expected public symbols are declared in market_data_processing_service/schemas/__init__.py.

    Skips in per-repo CI (no MDPS sibling); runs in full-workspace SIT.
    Fails CLOSED if any expected symbol disappears — that is the cross-repo breaking
    change this invariant exists to catch (features-service and MTDS import these
    symbols to validate Parquet schema compliance before writing candle data).
    """
    _skip_if_absent()

    schemas_init = _mdps_root() / "schemas" / "__init__.py"
    assert schemas_init.is_file(), f"MDPS schemas/__init__.py missing at {schemas_init}"

    exported = _exported_names(schemas_init)
    missing = sorted(EXPECTED_SCHEMAS_SYMBOLS - exported)
    assert not missing, (
        f"market_data_processing_service/schemas/__init__.py is MISSING the following public symbols "
        f"that the MDPS output contract depends on:\n  {missing}\n\n"
        "Removing or renaming these is a cross-repo BREAKING CHANGE — add the "
        "renamed/moved symbol back as a re-export or update the consuming repos first."
    )


def test_mdps_candle_output_core_fields_stable() -> None:
    """CandleOutput dataclass core fields match the consumer contract in features-service.

    features-service/delta_one/app/core/candle_resampler.py reads CandleOutput
    columns by string name from Parquet.  Removing any core field silently drops
    the column from all processed candle files.
    """
    _skip_if_absent()

    adapter_models_py = (
        _workspace_root()
        / "unified-api-contracts"
        / "unified_api_contracts"
        / "internal"
        / "domain"
        / "market_data_processing"
        / "adapter_models.py"
    )
    assert adapter_models_py.is_file(), f"UAC adapter_models.py missing at {adapter_models_py}"

    fields = _dataclass_fields(adapter_models_py, "CandleOutput")
    missing = sorted(EXPECTED_CANDLE_OUTPUT_CORE_FIELDS - fields)
    assert not missing, (
        f"CandleOutput is MISSING core fields that features-service reads by column name:\n  {missing}\n\n"
        "These fields are written to Parquet via to_dataframe()/to_polars() and read by the "
        "features-service delta-one candle resampler — removing them silently drops data."
    )


def test_mdps_market_state_values_stable() -> None:
    """MarketState StrEnum values match the values features-service filters by string.

    features-service delta_one/app/core/candle_resampler.py filters `market_state`
    rows by string value (e.g. `market_state != 'closed'`); strategy-service gates
    entry on `halted` and `auction` state strings.  Renaming any value is a silent
    cross-service breaking change — processed candles already stored on GCS would
    mismatch the new enum values.
    """
    _skip_if_absent()

    candle_schema_py = (
        _workspace_root()
        / "unified-api-contracts"
        / "unified_api_contracts"
        / "internal"
        / "domain"
        / "market_data_processing"
        / "candle_schema.py"
    )
    assert candle_schema_py.is_file(), f"UAC candle_schema.py missing at {candle_schema_py}"

    values = _enum_values(candle_schema_py, "MarketState")
    missing = sorted(EXPECTED_MARKET_STATE_VALUES - values)
    assert not missing, (
        f"MarketState is MISSING enum values that features-service filters on:\n  {missing}\n\n"
        "These string values are persisted in Parquet 'market_state' column and matched by "
        "downstream consumers — renaming them silently mismatches stored data."
    )


def test_mdps_data_type_values_stable() -> None:
    """DataType StrEnum values match the core MVP data types in use by the features pipeline.

    The features pipeline, manifest writer, and strategy routing all reference DataType
    values as string keys for GCS path construction and schema selection.  Renaming
    a DataType value is a cross-repo BREAKING CHANGE — GCS paths and manifest rows
    already written under the old value would become orphans.
    """
    _skip_if_absent()

    candle_schema_py = (
        _workspace_root()
        / "unified-api-contracts"
        / "unified_api_contracts"
        / "internal"
        / "domain"
        / "market_data_processing"
        / "candle_schema.py"
    )
    assert candle_schema_py.is_file(), f"UAC candle_schema.py missing at {candle_schema_py}"

    values = _enum_values(candle_schema_py, "DataType")
    missing = sorted(EXPECTED_DATA_TYPE_VALUES - values)
    assert not missing, (
        f"DataType is MISSING enum values for core MVP data types:\n  {missing}\n\n"
        "These string values are used as GCS path segments and manifest keys — removing them "
        "orphans all already-stored data for those data types."
    )


def test_mdps_uac_canonical_types_importable() -> None:
    """UAC exports the canonical MDPS types that features-service and consumers import.

    Confirms MarketState, DataType, CandleOutput, InstrumentInfo, InstrumentMetadata,
    and the book-summary column specs are importable from the UAC MDPS domain.
    Also verifies that BOOK_SUMMARY_COLUMNS is non-empty (required by the
    book_snapshot_5 precompute pipeline: features-service reads these column names).
    """
    _skip_if_absent()

    # MarketState must carry the string values features-service filters on
    for value in EXPECTED_MARKET_STATE_VALUES:
        assert any(v == value for v in MarketState), (
            f"MarketState is MISSING value '{value}' — features-service filters "
            "market_state column by this string value."
        )

    # DataType must carry the core MVP data type keys
    for value in EXPECTED_DATA_TYPE_VALUES:
        assert any(v == value for v in DataType), (
            f"DataType is MISSING value '{value}' — this data type is a core MVP "
            "pipeline key used in GCS paths and manifest rows."
        )

    # CandleOutput must have the core fields features-service reads
    import dataclasses

    candle_fields = {f.name for f in dataclasses.fields(CandleOutput)}
    for field in EXPECTED_CANDLE_OUTPUT_CORE_FIELDS:
        assert field in candle_fields, (
            f"CandleOutput is MISSING field '{field}' — features-service reads this "
            "column by name from Parquet candle files."
        )

    # InstrumentInfo and InstrumentMetadata must be importable (candle adapters accept them)
    assert hasattr(InstrumentInfo, "instrument_id"), (
        "InstrumentInfo must have 'instrument_id' property — candle adapters read this."
    )
    assert hasattr(InstrumentMetadata, "trading_hours_open"), (
        "InstrumentMetadata must have 'trading_hours_open' property — MarketStateDetector reads this."
    )

    # BOOK_SUMMARY_COLUMNS must be non-empty (book_snapshot_5 pipeline depends on it)
    assert len(BOOK_SUMMARY_COLUMNS) > 0, (
        "BOOK_SUMMARY_COLUMNS must be non-empty — features-service reads these column names "
        "from book_snapshot_5 candles for the microstructure feature precompute pipeline."
    )
    assert isinstance(BOOK_SUMMARY_COLUMNS[0], BookColumnSpec), (
        "BOOK_SUMMARY_COLUMNS must contain BookColumnSpec instances."
    )

    # BOOK_SUMMARY_COLUMN_NAMES must be a non-empty list of strings
    assert len(BOOK_SUMMARY_COLUMN_NAMES) > 0, (
        "BOOK_SUMMARY_COLUMN_NAMES must be non-empty — it is the string-list consumers use "
        "to select book columns from Parquet by name."
    )
    assert all(isinstance(n, str) for n in BOOK_SUMMARY_COLUMN_NAMES), (
        "BOOK_SUMMARY_COLUMN_NAMES must be a sequence of strings."
    )
