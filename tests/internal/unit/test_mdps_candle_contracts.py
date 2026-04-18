"""Unit tests for MDPS processed-candle SchemaContracts.

Phase 5b.1 of ``data_pipeline_completion_2026_04_18``. Verifies the full
matrix of (category × instrument_type × source_data_type × timeframe)
contracts registered via ``_candle_contracts`` is discoverable through
``lookup_contract`` and that the pre-existing TradFi ``ohlcv_1m``
pass-through contracts were not overwritten by the re-aggregate loop.
"""

from __future__ import annotations

import pytest

from unified_api_contracts.internal.schemas._candle_contracts import (
    MDPS_KEY_BOOK5,
    MDPS_KEY_DERIV,
    MDPS_KEY_LENDING,
    MDPS_KEY_LIQ,
    MDPS_KEY_LST,
    MDPS_KEY_ODDS,
    MDPS_KEY_ORACLE,
    MDPS_KEY_POOL_STATE,
    MDPS_KEY_PRED,
    MDPS_KEY_RATE,
    MDPS_KEY_SWAPS,
    MDPS_KEY_TRADES,
    MDPS_TIMEFRAMES_CEFI,
    MDPS_TIMEFRAMES_DEFI,
    MDPS_TIMEFRAMES_INDEX,
    MDPS_TIMEFRAMES_OPTIONS,
    MDPS_TIMEFRAMES_PREDICTION,
    MDPS_TIMEFRAMES_SPORTS,
    MDPS_TIMEFRAMES_TRADFI_RE_AGGREGATED,
)
from unified_api_contracts.internal.schemas.contracts import (
    CONTRACT_REGISTRY,
    TRADFI_EQUITY_OHLCV_1M,
    TRADFI_FUTURE_OHLCV_1M,
    lookup_contract,
)

# ---------------------------------------------------------------------------
# Pre-existing 1m contracts preserved
# ---------------------------------------------------------------------------


def test_tradfi_future_ohlcv_1m_not_overwritten() -> None:
    """Pre-existing Databento pass-through ohlcv_1m contract must stay intact."""
    contract = CONTRACT_REGISTRY[("tradfi", "future", "ohlcv_1m")]
    assert contract is TRADFI_FUTURE_OHLCV_1M


def test_tradfi_equity_ohlcv_1m_not_overwritten() -> None:
    contract = CONTRACT_REGISTRY[("tradfi", "equity", "ohlcv_1m")]
    assert contract is TRADFI_EQUITY_OHLCV_1M


def test_tradfi_factory_skipped_1m_timeframe() -> None:
    """Factory must NOT re-register ``ohlcv_1m`` for tradfi future/equity —
    those are the pre-existing Databento pass-through contracts."""
    assert "1m" not in MDPS_TIMEFRAMES_TRADFI_RE_AGGREGATED


# ---------------------------------------------------------------------------
# CeFi matrix
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("tf", MDPS_TIMEFRAMES_CEFI)
def test_cefi_perpetual_trades_candles(tf: str) -> None:
    contract = lookup_contract(category="cefi", instrument_type="perpetual", data_type=MDPS_KEY_TRADES(tf))
    assert contract.symbol_column == "symbol"
    names = {c.name for c in contract.columns}
    # OHLCV core + timeframe + anchors
    assert {"open", "high", "low", "close", "volume", "trade_count", "timeframe"}.issubset(names)


@pytest.mark.parametrize("tf", MDPS_TIMEFRAMES_CEFI)
def test_cefi_perpetual_book5_candles(tf: str) -> None:
    contract = lookup_contract(category="cefi", instrument_type="perpetual", data_type=MDPS_KEY_BOOK5(tf))
    names = {c.name for c in contract.columns}
    assert {
        "spread_bps_mean",
        "depth_bid_mean",
        "depth_ask_mean",
        "imbalance_ratio_mean",
        "mid_price_mean",
    }.issubset(names)


@pytest.mark.parametrize("tf", MDPS_TIMEFRAMES_CEFI)
def test_cefi_perpetual_deriv_candles(tf: str) -> None:
    contract = lookup_contract(category="cefi", instrument_type="perpetual", data_type=MDPS_KEY_DERIV(tf))
    names = {c.name for c in contract.columns}
    assert {"funding_rate_mean", "mark_price_mean", "index_price_mean"}.issubset(names)


@pytest.mark.parametrize("tf", MDPS_TIMEFRAMES_CEFI)
def test_cefi_perpetual_liq_aggregates(tf: str) -> None:
    contract = lookup_contract(category="cefi", instrument_type="perpetual", data_type=MDPS_KEY_LIQ(tf))
    names = {c.name for c in contract.columns}
    # Liquidation aggregates are NOT OHLCV — just count + notional.
    assert "liquidation_count" in names
    assert "liquidation_notional_usd" in names
    assert "open" not in names


@pytest.mark.parametrize("tf", MDPS_TIMEFRAMES_CEFI)
def test_cefi_spot_pair_candles(tf: str) -> None:
    trades = lookup_contract(category="cefi", instrument_type="spot_pair", data_type=MDPS_KEY_TRADES(tf))
    book5 = lookup_contract(category="cefi", instrument_type="spot_pair", data_type=MDPS_KEY_BOOK5(tf))
    assert trades.symbol_column == "symbol"
    assert book5.symbol_column == "symbol"


@pytest.mark.parametrize("tf", MDPS_TIMEFRAMES_OPTIONS)
def test_cefi_options_chain_candles_key_on_underlying(tf: str) -> None:
    contract = lookup_contract(category="cefi", instrument_type="options_chain", data_type=MDPS_KEY_TRADES(tf))
    assert contract.symbol_column == "underlying"


@pytest.mark.parametrize("tf", MDPS_TIMEFRAMES_OPTIONS)
def test_cefi_futures_chain_candles_key_on_underlying(tf: str) -> None:
    contract = lookup_contract(category="cefi", instrument_type="futures_chain", data_type=MDPS_KEY_TRADES(tf))
    assert contract.symbol_column == "underlying"


# ---------------------------------------------------------------------------
# TradFi re-aggregated + options / index
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("tf", MDPS_TIMEFRAMES_TRADFI_RE_AGGREGATED)
def test_tradfi_future_higher_timeframes(tf: str) -> None:
    contract = lookup_contract(category="tradfi", instrument_type="future", data_type=MDPS_KEY_TRADES(tf))
    assert contract.symbol_column == "symbol"


@pytest.mark.parametrize("tf", MDPS_TIMEFRAMES_TRADFI_RE_AGGREGATED)
def test_tradfi_equity_higher_timeframes(tf: str) -> None:
    contract = lookup_contract(category="tradfi", instrument_type="equity", data_type=MDPS_KEY_TRADES(tf))
    assert contract.symbol_column == "symbol"


@pytest.mark.parametrize("tf", MDPS_TIMEFRAMES_OPTIONS)
def test_tradfi_options_chain_candles(tf: str) -> None:
    contract = lookup_contract(category="tradfi", instrument_type="options_chain", data_type=MDPS_KEY_TRADES(tf))
    assert contract.symbol_column == "underlying"


@pytest.mark.parametrize("tf", MDPS_TIMEFRAMES_INDEX)
def test_tradfi_index_candles(tf: str) -> None:
    contract = lookup_contract(category="tradfi", instrument_type="index", data_type=MDPS_KEY_TRADES(tf))
    assert contract.symbol_column == "symbol"


# ---------------------------------------------------------------------------
# DeFi candles
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("tf", MDPS_TIMEFRAMES_DEFI)
def test_defi_pool_swap_candles_include_chain(tf: str) -> None:
    contract = lookup_contract(category="defi", instrument_type="pool", data_type=MDPS_KEY_SWAPS(tf))
    names = {c.name for c in contract.columns}
    assert "chain" in names
    assert "swap_count" in names
    assert "volume_quote_usd" in names
    assert contract.symbol_column == "pool_id"


@pytest.mark.parametrize("tf", MDPS_TIMEFRAMES_DEFI)
def test_defi_pool_state_candles_include_chain(tf: str) -> None:
    contract = lookup_contract(category="defi", instrument_type="pool", data_type=MDPS_KEY_POOL_STATE(tf))
    names = {c.name for c in contract.columns}
    assert "chain" in names
    assert contract.symbol_column == "symbol"


@pytest.mark.parametrize("tf", MDPS_TIMEFRAMES_OPTIONS)
def test_defi_a_token_candles_include_chain_and_key_on_token(tf: str) -> None:
    for key_fn in (MDPS_KEY_LENDING, MDPS_KEY_RATE, MDPS_KEY_ORACLE):
        contract = lookup_contract(category="defi", instrument_type="a_token", data_type=key_fn(tf))
        names = {c.name for c in contract.columns}
        assert "chain" in names
        assert contract.symbol_column == "token"


@pytest.mark.parametrize("tf", MDPS_TIMEFRAMES_OPTIONS)
def test_defi_lst_candles_include_chain(tf: str) -> None:
    for key_fn in (MDPS_KEY_LST, MDPS_KEY_ORACLE):
        contract = lookup_contract(category="defi", instrument_type="lst", data_type=key_fn(tf))
        names = {c.name for c in contract.columns}
        assert "chain" in names
        assert contract.symbol_column == "symbol"


# ---------------------------------------------------------------------------
# Sports + Prediction candles
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("tf", MDPS_TIMEFRAMES_SPORTS)
def test_sports_odds_candles(tf: str) -> None:
    contract = lookup_contract(category="sports", instrument_type="odds", data_type=MDPS_KEY_ODDS(tf))
    assert contract.symbol_column == "fixture_id"
    names = {c.name for c in contract.columns}
    assert "quote_count" in names
    assert "source_count" in names


@pytest.mark.parametrize("tf", MDPS_TIMEFRAMES_PREDICTION)
def test_prediction_market_candles(tf: str) -> None:
    contract = lookup_contract(
        category="prediction",
        instrument_type="prediction_market",
        data_type=MDPS_KEY_PRED(tf),
    )
    assert contract.symbol_column == "condition_id"
    names = {c.name for c in contract.columns}
    assert "chain" in names
    assert "quote_count" in names


# ---------------------------------------------------------------------------
# Cardinality invariant — every registered candle contract has a timeframe
# column and a valid timeframe suffix on its data_type key.
# ---------------------------------------------------------------------------


def test_every_candle_contract_has_timeframe_column() -> None:
    """Any data_type whose key ends with a known timeframe suffix MUST carry
    a ``timeframe`` column — G7 (single source of truth for shard dims)."""
    valid_tf = set(MDPS_TIMEFRAMES_CEFI) | set(MDPS_TIMEFRAMES_DEFI) | {"1m", "5m", "15m", "1h", "4h", "1d", "15s"}
    for (category, itype, dt), contract in CONTRACT_REGISTRY.items():
        tail = dt.rsplit("_", 1)[-1] if "_" in dt else dt
        if tail not in valid_tf:
            continue
        # Candle data_types end with a recognised timeframe suffix.
        names = {c.name for c in contract.columns}
        if "timeframe" not in names:
            # OK only for the 2 pre-existing tradfi ohlcv_1m pass-throughs.
            assert dt == "ohlcv_1m" and category == "tradfi" and itype in {"future", "equity"}, (
                f"candle contract {(category, itype, dt)} missing 'timeframe' column"
            )
