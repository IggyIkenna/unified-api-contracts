"""Unit tests for declarative per-(category, instrument_type, data_type) SchemaContract.

Phase 1.3 of data_canonicalisation_mvp_2026_04_17.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd

from unified_api_contracts.internal.schemas.contracts import (
    CEFI_FUTURES_CHAIN_TRADES,
    CEFI_OPTIONS_CHAIN_TRADES,
    CEFI_PERPETUAL_BOOK_SNAPSHOT_5,
    CEFI_PERPETUAL_TRADES,
    CONTRACT_REGISTRY,
    DEFI_DEX_POOL_DEX_POOL_SWAPS,
    DEFI_LENDING_POSITION_LENDING_INDICES,
    DEFI_LST_LST_RATES,
    TRADFI_EQUITY_TRADES,
    TRADFI_FUTURE_TRADES,
    TRADFI_OPTIONS_CHAIN_TRADES,
    ColumnSpec,
    SchemaContract,
    Violation,
    validate_dataframe,
)

# ---------------------------------------------------------------------------
# Helpers — minimal valid dataframes per contract
# ---------------------------------------------------------------------------


def _ts_series(n: int = 2) -> pd.Series:
    return pd.Series(
        [datetime(2026, 4, 17, 0, i, tzinfo=UTC) for i in range(n)],
        dtype="datetime64[ns, UTC]",
    )


def _df_cefi_perp_trades() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "instrument_id": pd.Series(["BINANCE:PERPETUAL:BTCUSDT", "BINANCE:PERPETUAL:BTCUSDT"], dtype="string"),
            "symbol": pd.Series(["BTCUSDT", "BTCUSDT"], dtype="string"),
            "ts_event": _ts_series(),
            "price": pd.Series([65000.0, 65001.0], dtype="float64"),
            "size": pd.Series([0.1, 0.2], dtype="float64"),
            "side": pd.Series(["buy", "sell"], dtype="string"),
        }
    )


def _df_cefi_perp_book_5() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "instrument_id": pd.Series(["BINANCE:PERPETUAL:BTCUSDT"], dtype="string"),
            "symbol": pd.Series(["BTCUSDT"], dtype="string"),
            "ts_event": _ts_series(1),
            "bids": pd.Series(["[[65000.0,1.0]]"], dtype="string"),
            "asks": pd.Series(["[[65010.0,1.0]]"], dtype="string"),
        }
    )


def _df_cefi_options_chain_trades() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "instrument_id": pd.Series(["DERIBIT:OPTION:BTC-25APR26-70000-C"], dtype="string"),
            "underlying": pd.Series(["BTC"], dtype="string"),
            "ts_event": _ts_series(1),
            "price": pd.Series([0.015], dtype="float64"),
            "size": pd.Series([1.0], dtype="float64"),
            "side": pd.Series(["buy"], dtype="string"),
            "strike": pd.Series([70000.0], dtype="float64"),
            "expiry_date": pd.Series([datetime(2026, 4, 25, tzinfo=UTC)], dtype="datetime64[ns, UTC]"),
            "option_right": pd.Series(["call"], dtype="string"),
        }
    )


def _df_cefi_futures_chain_trades() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "instrument_id": pd.Series(["BINANCE:FUTURE:BTC-0628"], dtype="string"),
            "underlying": pd.Series(["BTC"], dtype="string"),
            "ts_event": _ts_series(1),
            "price": pd.Series([65100.0], dtype="float64"),
            "size": pd.Series([0.5], dtype="float64"),
            "side": pd.Series(["buy"], dtype="string"),
            "expiry_date": pd.Series([datetime(2026, 6, 28, tzinfo=UTC)], dtype="datetime64[ns, UTC]"),
        }
    )


def _df_tradfi_future_trades() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "instrument_id": pd.Series(["CME:FUTURE:ESM6"], dtype="string"),
            "symbol": pd.Series(["ESM6"], dtype="string"),
            "ts_event": _ts_series(1),
            "price": pd.Series([5400.25], dtype="float64"),
            "size": pd.Series([1.0], dtype="float64"),
        }
    )


def _df_tradfi_options_chain_trades() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "instrument_id": pd.Series(["CME:OPTION:ESM6-5500C"], dtype="string"),
            "underlying": pd.Series(["ES"], dtype="string"),
            "ts_event": _ts_series(1),
            "price": pd.Series([12.5], dtype="float64"),
            "size": pd.Series([1.0], dtype="float64"),
            "strike": pd.Series([5500.0], dtype="float64"),
            "expiry_date": pd.Series([datetime(2026, 6, 20, tzinfo=UTC)], dtype="datetime64[ns, UTC]"),
            "option_right": pd.Series(["call"], dtype="string"),
        }
    )


def _df_tradfi_equity_trades() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "instrument_id": pd.Series(["NASDAQ:EQUITY:AAPL"], dtype="string"),
            "symbol": pd.Series(["AAPL"], dtype="string"),
            "ts_event": _ts_series(1),
            "price": pd.Series([190.5], dtype="float64"),
            "size": pd.Series([100.0], dtype="float64"),
        }
    )


def _df_defi_lending_indices() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "instrument_id": pd.Series(["AAVE_V3:LENDING:ETHEREUM:USDC"], dtype="string"),
            "venue": pd.Series(["AAVE_V3"], dtype="string"),
            "chain": pd.Series(["ETHEREUM"], dtype="string"),
            "ts_event": _ts_series(1),
            "supply_index": pd.Series([1.05], dtype="float64"),
            "borrow_index": pd.Series([1.08], dtype="float64"),
        }
    )


def _df_defi_dex_pool_swaps() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "instrument_id": pd.Series(["UNIV3:POOL:ETHEREUM:USDC-WETH-500"], dtype="string"),
            "venue": pd.Series(["UNIV3"], dtype="string"),
            "chain": pd.Series(["ETHEREUM"], dtype="string"),
            "ts_event": _ts_series(1),
            "amount0": pd.Series([1000.0], dtype="float64"),
            "amount1": pd.Series([-0.3], dtype="float64"),
            "price": pd.Series([3300.0], dtype="float64"),
        }
    )


def _df_defi_lst_rates() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "instrument_id": pd.Series(["LIDO:LST:ETHEREUM:STETH"], dtype="string"),
            "venue": pd.Series(["LIDO"], dtype="string"),
            "chain": pd.Series(["ETHEREUM"], dtype="string"),
            "ts_event": _ts_series(1),
            "exchange_rate": pd.Series([1.04], dtype="float64"),
        }
    )


# ---------------------------------------------------------------------------
# Contract/fixture pairs for parametric tests
# ---------------------------------------------------------------------------

VALID_CASES: list[tuple[SchemaContract, pd.DataFrame]] = [
    (CEFI_PERPETUAL_TRADES, _df_cefi_perp_trades()),
    (CEFI_PERPETUAL_BOOK_SNAPSHOT_5, _df_cefi_perp_book_5()),
    (CEFI_OPTIONS_CHAIN_TRADES, _df_cefi_options_chain_trades()),
    (CEFI_FUTURES_CHAIN_TRADES, _df_cefi_futures_chain_trades()),
    (TRADFI_FUTURE_TRADES, _df_tradfi_future_trades()),
    (TRADFI_OPTIONS_CHAIN_TRADES, _df_tradfi_options_chain_trades()),
    (TRADFI_EQUITY_TRADES, _df_tradfi_equity_trades()),
    (DEFI_LENDING_POSITION_LENDING_INDICES, _df_defi_lending_indices()),
    (DEFI_DEX_POOL_DEX_POOL_SWAPS, _df_defi_dex_pool_swaps()),
    (DEFI_LST_LST_RATES, _df_defi_lst_rates()),
]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_valid_dataframes_for_every_contract_return_no_violations() -> None:
    for contract, df in VALID_CASES:
        violations = validate_dataframe(df, contract)
        assert violations == [], (
            f"expected no violations for ({contract.category},"
            f" {contract.instrument_type}, {contract.data_type}), "
            f"got {violations}"
        )


def test_missing_instrument_id_column_reports_missing_column() -> None:
    df = _df_cefi_perp_trades().drop(columns=["instrument_id"])
    violations = validate_dataframe(df, CEFI_PERPETUAL_TRADES)
    assert any(v.kind == "missing_column" and v.column == "instrument_id" for v in violations)


def test_null_instrument_id_reports_extra_required_null() -> None:
    df = _df_cefi_perp_trades()
    df.loc[0, "instrument_id"] = None
    violations = validate_dataframe(df, CEFI_PERPETUAL_TRADES)
    assert any(v.kind == "extra_required_null" and v.column == "instrument_id" for v in violations)


def test_wrong_dtype_on_price_reports_wrong_dtype() -> None:
    df = _df_cefi_perp_trades()
    df["price"] = pd.Series(["65000.0", "65001.0"], dtype="string")
    violations = validate_dataframe(df, CEFI_PERPETUAL_TRADES)
    assert any(v.kind == "wrong_dtype" and v.column == "price" for v in violations)


def test_low_row_count_reports_row_count_too_low() -> None:
    # All contracts have required_row_count_min=1; pass an empty df.
    empty = pd.DataFrame(
        {
            "instrument_id": pd.Series([], dtype="string"),
            "symbol": pd.Series([], dtype="string"),
            "ts_event": pd.Series([], dtype="datetime64[ns, UTC]"),
            "price": pd.Series([], dtype="float64"),
            "size": pd.Series([], dtype="float64"),
            "side": pd.Series([], dtype="string"),
        }
    )
    violations = validate_dataframe(empty, CEFI_PERPETUAL_TRADES)
    assert any(v.kind == "row_count_too_low" for v in violations)


def test_null_rate_cap_exceeded_reports_null_rate_exceeded() -> None:
    contract = SchemaContract(
        category="cefi",
        instrument_type="perpetual",
        data_type="trades",
        columns=[
            ColumnSpec(name="instrument_id", dtype="string", nullable=False),
            ColumnSpec(name="ts_event", dtype="datetime64[ns, UTC]", nullable=False),
            ColumnSpec(name="optional_col", dtype="float64", nullable=True),
        ],
        required_row_count_min=1,
        null_rate_max={"optional_col": 0.1},
    )
    df = pd.DataFrame(
        {
            "instrument_id": pd.Series(["X:Y:Z"] * 4, dtype="string"),
            "ts_event": _ts_series(4),
            "optional_col": pd.Series([1.0, None, None, None], dtype="float64"),
        }
    )
    violations = validate_dataframe(df, contract)
    assert any(v.kind == "null_rate_exceeded" and v.column == "optional_col" for v in violations)


def test_contract_registry_lookup_cefi_perpetual_trades() -> None:
    contract = CONTRACT_REGISTRY[("cefi", "perpetual", "trades")]
    assert contract is CEFI_PERPETUAL_TRADES
    assert contract.category == "cefi"
    assert contract.instrument_type == "perpetual"
    assert contract.data_type == "trades"


def test_contract_registry_covers_all_required_triples() -> None:
    required = {
        ("cefi", "perpetual", "trades"),
        ("cefi", "perpetual", "book_snapshot_5"),
        ("cefi", "options_chain", "trades"),
        ("cefi", "futures_chain", "trades"),
        ("tradfi", "future", "trades"),
        ("tradfi", "options_chain", "trades"),
        ("tradfi", "equity", "trades"),
        ("defi", "lending_position", "lending_indices"),
        ("defi", "dex_pool", "dex_pool_swaps"),
        ("defi", "lst", "lst_rates"),
    }
    assert required.issubset(set(CONTRACT_REGISTRY.keys()))


def test_every_contract_requires_instrument_id_non_nullable_string() -> None:
    for contract in CONTRACT_REGISTRY.values():
        id_specs = [c for c in contract.columns if c.name == "instrument_id"]
        assert len(id_specs) == 1, f"{contract.data_type} missing instrument_id spec"
        assert id_specs[0].dtype == "string"
        assert id_specs[0].nullable is False


def test_violation_model_is_frozen() -> None:
    v = Violation(kind="missing_column", column="x", message="test")
    assert v.kind == "missing_column"
    assert v.column == "x"
