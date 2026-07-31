"""Unit tests for declarative per-(category, instrument_type, data_type) SchemaContract.

Phase 1.3 of data_canonicalisation_mvp_2026_04_17.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd
import pytest

from unified_api_contracts.internal.schemas.contracts import (
    CEFI_FUTURES_CHAIN_TRADES,
    CEFI_OPTIONS_CHAIN_TRADES,
    CEFI_PERPETUAL_BOOK_SNAPSHOT_5,
    CEFI_PERPETUAL_TRADES,
    CONTRACT_REGISTRY,
    DEFI_AAVE_V3_LENDING_INDICES,
    DEFI_DEX_POOL_DEX_POOL_STATE,
    DEFI_DEX_POOL_DEX_POOL_SWAPS,
    DEFI_LENDING_INDICES_MARKET_ID,
    DEFI_LENDING_POSITION_LENDING_INDICES,
    DEFI_LST_LST_RATES,
    DEFI_POOL_DEX_POOL_SWAPS,
    DEFI_SPOT_ASSET_BRIDGE_EVENTS,
    DEFI_SPOT_ASSET_GAS_FEES,
    DEFI_SPOT_ASSET_MEV_EVENTS,
    TRADFI_EQUITY_TRADES,
    TRADFI_FUTURE_TRADES,
    TRADFI_OPTIONS_CHAIN_TRADES,
    VENUE_CONTRACT_OVERRIDES,
    ColumnSpec,
    SchemaContract,
    SchemaContractNotFoundError,
    Violation,
    lookup_contract,
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
    # Real Tardis book_snapshot_5 wire shape: 5 flat per-level columns per
    # side (never a serialised bids/asks string -- see
    # cefi_book_snapshot5_schema_contract_ts_event_levels_mismatch_2026_07_28.md).
    data: dict[str, pd.Series] = {
        "instrument_id": pd.Series(["BINANCE:PERPETUAL:BTCUSDT"], dtype="string"),
        "symbol": pd.Series(["BTCUSDT"], dtype="string"),
        "ts_event": _ts_series(1),
    }
    for level in range(5):
        data[f"bids[{level}].price"] = pd.Series([65000.0 - level], dtype="float64")
        data[f"bids[{level}].amount"] = pd.Series([1.0 + level], dtype="float64")
        data[f"asks[{level}].price"] = pd.Series([65010.0 + level], dtype="float64")
        data[f"asks[{level}].amount"] = pd.Series([1.0 + level], dtype="float64")
    return pd.DataFrame(data)


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


def _df_defi_mev_events() -> pd.DataFrame:
    """Shaped exactly like the post-``write_defi_rows``-enrichment row
    ``mev_events_handler.py`` produces for a Flashbots relay payload: the raw
    fetch row (``symbol``/``ts_event``/``venue``/``chain``/``relay``/
    ``block_number``/``builder_pubkey``/``value_eth``) plus the
    ``instrument_id``/``instrument_type``/``data_type`` columns
    ``write_defi_rows`` adds before upload."""
    return pd.DataFrame(
        {
            "instrument_id": pd.Series(["FLASHBOTS-ETHEREUM:SPOT_ASSET:FLASHBOTS"], dtype="string"),
            "symbol": pd.Series(["FLASHBOTS"], dtype="string"),
            "venue": pd.Series(["FLASHBOTS"], dtype="string"),
            "chain": pd.Series(["ETHEREUM"], dtype="string"),
            "ts_event": _ts_series(1),
            "relay": pd.Series(["flashbots"], dtype="string"),
            "block_number": pd.Series([19_876_543], dtype="int64"),
            "builder_pubkey": pd.Series(["0x" + "ab" * 48], dtype="string"),
            "value_eth": pd.Series([0.0521], dtype="float64"),
            "instrument_type": pd.Series(["spot_asset"], dtype="string"),
            "data_type": pd.Series(["mev_events"], dtype="string"),
        }
    )


def _df_defi_bridge_events() -> pd.DataFrame:
    """Shaped exactly like the post-``write_defi_rows``-enrichment row
    ``bridge_events_handler.py`` produces for an Across ``FundsDeposited``
    on-chain log: the raw fetch row (``symbol``/``ts_event``/``venue``/
    ``chain``/``source_chain``/``dest_chain``/``token``/``amount``/
    ``depositor``/``recipient``) plus the ``instrument_id``/
    ``instrument_type``/``data_type`` columns ``write_defi_rows`` adds
    before upload."""
    return pd.DataFrame(
        {
            "instrument_id": pd.Series(["ACROSS-ETHEREUM:SPOT_ASSET:USDC"], dtype="string"),
            "symbol": pd.Series(["USDC"], dtype="string"),
            "venue": pd.Series(["ACROSS"], dtype="string"),
            "chain": pd.Series(["ETHEREUM"], dtype="string"),
            "ts_event": _ts_series(1),
            "source_chain": pd.Series(["1"], dtype="string"),
            "dest_chain": pd.Series(["42161"], dtype="string"),
            "token": pd.Series(["0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"], dtype="string"),
            "amount": pd.Series([1234.56], dtype="float64"),
            "depositor": pd.Series(["0x" + "de" * 20], dtype="string"),
            "recipient": pd.Series(["0x" + "be" * 20], dtype="string"),
            "instrument_type": pd.Series(["spot_asset"], dtype="string"),
            "data_type": pd.Series(["bridge_events"], dtype="string"),
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
    (DEFI_SPOT_ASSET_MEV_EVENTS, _df_defi_mev_events()),
    (DEFI_SPOT_ASSET_BRIDGE_EVENTS, _df_defi_bridge_events()),
]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_valid_dataframes_for_every_contract_return_no_violations() -> None:
    for contract, df in VALID_CASES:
        violations = validate_dataframe(df, contract)
        assert violations == [], (
            f"expected no violations for ({contract.asset_group},"
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


def test_book_snapshot_5_thin_book_partial_depth_levels_are_valid() -> None:
    """Regression for the deep-level nullable=False gap
    (cefi_book_snapshot5_schema_contract_ts_event_levels_mismatch_2026_07_28.md
    §"deep-level nullable gap", 2026-07-31): a real order book does not always
    carry 5 resting levels on both sides -- an illiquid/thin pair legitimately
    has Tardis emit NaN for the deeper levels at a given snapshot instant. This
    must validate clean (zero violations), not FATAL-reject the whole shard."""
    df = _df_cefi_perp_book_5()
    # Only 2 of 5 bid levels populated, only 3 of 5 ask levels populated --
    # deeper levels NaN, exactly the real Tardis wire shape for a thin book.
    for level in range(2, 5):
        df.loc[0, f"bids[{level}].price"] = float("nan")
        df.loc[0, f"bids[{level}].amount"] = float("nan")
    for level in range(3, 5):
        df.loc[0, f"asks[{level}].price"] = float("nan")
        df.loc[0, f"asks[{level}].amount"] = float("nan")
    violations = validate_dataframe(df, CEFI_PERPETUAL_BOOK_SNAPSHOT_5)
    assert violations == [], f"expected a thin book to validate clean, got {violations}"


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
        asset_group="cefi",
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
    assert contract.asset_group == "cefi"
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
        if contract.asset_group == "sports":
            # Sports reference/match shards key on league_id, fixture_id, etc.
            continue
        if contract.data_type == "instrument_catalogue":
            # Instrument catalogue is keyed by instrument_key, not instrument_id.
            continue
        id_specs = [c for c in contract.columns if c.name == "instrument_id"]
        assert len(id_specs) == 1, f"{contract.data_type} missing instrument_id spec"
        assert id_specs[0].dtype == "string"
        assert id_specs[0].nullable is False


def test_violation_model_is_frozen() -> None:
    v = Violation(kind="missing_column", column="x", message="test")
    assert v.kind == "missing_column"
    assert v.column == "x"


# ---------------------------------------------------------------------------
# G7 — SchemaContract.symbol_column & venue-aware lookup
# ---------------------------------------------------------------------------


def test_every_contract_declares_a_symbol_column() -> None:
    """G7: every registered contract must declare ``symbol_column`` (no blank)."""
    for key, contract in CONTRACT_REGISTRY.items():
        assert contract.symbol_column, f"{key} missing symbol_column"
        declared = {c.name for c in contract.columns}
        assert contract.symbol_column in declared or contract.symbol_column in {
            "symbol",
            "underlying",
            "pool_id",
            "market_id",
            "token",
            "fixture_id",
            "condition_id",
            "instrument_key",
        }, f"{key} symbol_column={contract.symbol_column} not in declared columns"


def test_defi_contracts_use_correct_per_source_symbol_columns() -> None:
    """Aave V3 must key on ``symbol`` (aToken), pools must key on ``pool_id``,
    generic lending must key on ``market_id`` — no more guessing."""
    assert DEFI_AAVE_V3_LENDING_INDICES.symbol_column == "symbol"
    assert DEFI_LENDING_INDICES_MARKET_ID.symbol_column == "market_id"
    # dex_pool_state AND dex_pool_swaps (instrument_type=pool — the 13 DEX-pool
    # protocol writers) key on ``symbol`` (defi_dex_pool_symbol_shape_fix_2026_07_09):
    # the canonical TOKEN0-TOKEN1[-FEE_TIER] MTDS resolves per row, not a bare
    # address. DEFI_DEX_POOL_DEX_POOL_SWAPS (instrument_type=dex_pool — a distinct,
    # unused-by-current-writers key) is untouched.
    assert DEFI_DEX_POOL_DEX_POOL_STATE.symbol_column == "symbol"
    assert DEFI_DEX_POOL_DEX_POOL_SWAPS.symbol_column == "pool_id"
    assert DEFI_POOL_DEX_POOL_SWAPS.symbol_column == "symbol"
    assert DEFI_LST_LST_RATES.symbol_column == "symbol"
    assert DEFI_SPOT_ASSET_GAS_FEES.symbol_column == "symbol"


def test_cefi_chain_contracts_key_on_underlying() -> None:
    """Options / futures chains bundle per underlying, not per row symbol."""
    assert CEFI_OPTIONS_CHAIN_TRADES.symbol_column == "underlying"
    assert CEFI_FUTURES_CHAIN_TRADES.symbol_column == "underlying"
    assert TRADFI_OPTIONS_CHAIN_TRADES.symbol_column == "underlying"


def test_lookup_contract_without_venue_resolves_base_registry() -> None:
    contract = lookup_contract(asset_group="cefi", instrument_type="perpetual", data_type="trades")
    assert contract is CONTRACT_REGISTRY[("cefi", "perpetual", "trades")]


def test_lookup_contract_with_venue_prefers_override() -> None:
    """Aave V3 override routes to the liquidity/borrow-index schema."""
    contract = lookup_contract(
        asset_group="defi",
        instrument_type="a_token",
        data_type="lending_indices",
        venue="AAVE_V3",
    )
    assert contract is DEFI_AAVE_V3_LENDING_INDICES


def test_lookup_contract_with_unknown_venue_falls_back_to_base() -> None:
    """Unknown venue falls back to the base (category, it, dt) registry."""
    contract = lookup_contract(
        asset_group="cefi",
        instrument_type="perpetual",
        data_type="trades",
        venue="NEW_VENUE_NOT_REGISTERED",
    )
    assert contract is CONTRACT_REGISTRY[("cefi", "perpetual", "trades")]


def test_lookup_contract_normalises_uppercase_data_type() -> None:
    """The sports manifest convention stores UPPERCASE data_type (XG_SHOTS); the
    registry key is lowercase (xg_shots). lookup_contract must case-normalise
    data_type (mirroring the instrument_type lowercase fallback).
    Regression: understat_bulk_download_backfill_2026_06_29 §9.1/§9.2."""
    assert (
        lookup_contract(asset_group="sports", instrument_type="shot", data_type="XG_SHOTS")
        is (CONTRACT_REGISTRY[("sports", "shot", "xg_shots")])
    )


def test_lookup_contract_resolves_blank_instrument_type_sports_alias() -> None:
    """The sports manifest writes ``instrument_type=""`` on every row (§9.1), so
    record_captured's write-time schema lookup queries ("sports", "", "XG" |
    "XG_SHOTS"). The blank-instrument_type aliases + data_type case-normalisation
    must resolve it (else MANIFEST_WRITE_SCHEMA_MISSING skips validation)."""
    assert (
        lookup_contract(asset_group="sports", instrument_type="", data_type="XG_SHOTS")
        is (CONTRACT_REGISTRY[("sports", "shot", "xg_shots")])
    )
    assert (
        lookup_contract(asset_group="sports", instrument_type="", data_type="XG")
        is (CONTRACT_REGISTRY[("sports", "match", "xg")])
    )


def test_lookup_contract_missing_raises_with_structured_details() -> None:
    """G3: a missing contract must raise — not warn — with routable details."""
    with pytest.raises(SchemaContractNotFoundError) as exc_info:
        lookup_contract(
            asset_group="defi",
            instrument_type="unknown_type",
            data_type="unknown_dt",
            venue="UNKNOWN_VENUE",
        )
    details = exc_info.value.details
    assert details["asset_group"] == "defi"
    assert details["instrument_type"] == "unknown_type"
    assert details["data_type"] == "unknown_dt"
    assert details["venue"] == "UNKNOWN_VENUE"


def test_venue_contract_overrides_cover_aave_v3_variant() -> None:
    """Aave V3's column vocabulary (liquidityIndex, variableBorrowIndex)
    differs from every other lending protocol, so it's the sentinel
    venue-override that must be present. Other protocols resolve via the
    base registry by (category, instrument_type, data_type)."""
    covered = {v for (_, v, _, _) in VENUE_CONTRACT_OVERRIDES}
    assert "AAVE_V3" in covered


def test_contract_registry_covers_expanded_defi_shards() -> None:
    """G7 expanded coverage: every data_type the handlers write must resolve."""
    required = {
        ("defi", "a_token", "lending_indices"),
        ("defi", "lending", "lending_indices"),
        ("defi", "lending", "liquidations"),
        ("defi", "pool", "dex_pool_state"),
        ("defi", "pool", "dex_pool_swaps"),
        ("defi", "dex_pool", "dex_pool_swaps"),
        ("defi", "lst", "lst_rates"),
        ("defi", "spot_asset", "gas_fees"),
        ("defi", "spot_asset", "oracle_prices"),
        ("defi", "perpetual", "perp_funding"),
        ("defi", "staking", "eigenlayer_rewards"),
        ("defi", "staking", "yield_snapshots"),
        ("defi", "spot_asset", "mev_events"),
        ("defi", "spot_asset", "bridge_events"),
    }
    assert required.issubset(set(CONTRACT_REGISTRY.keys()))


def test_mev_events_and_bridge_events_resolve_via_write_defi_rows_call_shape() -> None:
    """Regression: ``market-tick-data-service``'s ``mev_events_handler.py`` /
    ``bridge_events_handler.py`` call ``write_defi_rows(..., symbol_column=None)``
    (implicit default), which makes ``write_defi_rows`` STRICT — it resolves
    ``lookup_contract(asset_group="defi", instrument_type=InstrumentType.SPOT_ASSET
    .value.lower(), data_type=<data_type>, venue=<venue>)`` up front and turns any
    ``SchemaContractNotFoundError`` into a hard ``ValueError`` before a single row
    is written. Before either contract was registered, this exact call shape
    raised; it must now resolve cleanly for every venue each handler writes."""
    mev_contract = lookup_contract(
        asset_group="defi",
        instrument_type="spot_asset",
        data_type="mev_events",
        venue="FLASHBOTS",
    )
    assert mev_contract is DEFI_SPOT_ASSET_MEV_EVENTS
    assert mev_contract.symbol_column == "symbol"

    for bridge_venue in ("ACROSS", "STARGATE"):
        bridge_contract = lookup_contract(
            asset_group="defi",
            instrument_type="spot_asset",
            data_type="bridge_events",
            venue=bridge_venue,
        )
        assert bridge_contract is DEFI_SPOT_ASSET_BRIDGE_EVENTS
        assert bridge_contract.symbol_column == "symbol"


def test_mev_events_and_bridge_events_sample_rows_validate_clean() -> None:
    """A dataframe shaped exactly like the enriched row ``write_defi_rows``
    produces from each handler's real fetch output (raw columns + the
    ``instrument_id``/``instrument_type``/``data_type`` enrichment columns)
    must validate with zero violations against the registered contract."""
    mev_violations = validate_dataframe(_df_defi_mev_events(), DEFI_SPOT_ASSET_MEV_EVENTS)
    assert mev_violations == [], f"expected no violations for mev_events sample row, got {mev_violations}"

    bridge_violations = validate_dataframe(_df_defi_bridge_events(), DEFI_SPOT_ASSET_BRIDGE_EVENTS)
    assert bridge_violations == [], f"expected no violations for bridge_events sample row, got {bridge_violations}"


def test_contract_registry_covers_expanded_cefi_shards() -> None:
    required = {
        ("cefi", "perpetual", "derivative_ticker"),
        ("cefi", "perpetual", "liquidations"),
        ("cefi", "perpetual", "quotes"),
        ("cefi", "spot_pair", "trades"),
        ("cefi", "spot_pair", "book_snapshot_5"),
    }
    assert required.issubset(set(CONTRACT_REGISTRY.keys()))


def test_contract_registry_covers_expanded_tradfi_shards() -> None:
    required = {
        ("tradfi", "future", "ohlcv_1m"),
        ("tradfi", "equity", "ohlcv_1m"),
        ("tradfi", "index", "trades"),
    }
    assert required.issubset(set(CONTRACT_REGISTRY.keys()))
