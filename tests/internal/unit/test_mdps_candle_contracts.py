"""Unit tests for MDPS processed-candle SchemaContracts.

Phase 5b.1 of ``data_pipeline_completion_2026_04_18``. Verifies the full
matrix of (category x instrument_type x source_data_type x timeframe)
contracts registered via ``_candle_contracts`` is discoverable through
``lookup_contract`` and that the pre-existing TradFi ``ohlcv_1m``
pass-through contracts were not overwritten by the re-aggregate loop.
"""

from __future__ import annotations

import pytest

from unified_api_contracts.internal.domain.market_data_processing import (
    BOOK_SUMMARY_COLUMN_NAMES,
)
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
    MDPS_TIMEFRAMES_PREDICTION_TRADES,
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
    contract = lookup_contract(asset_group="cefi", instrument_type="perpetual", data_type=MDPS_KEY_TRADES(tf))
    assert contract.symbol_column == "symbol"
    names = {c.name for c in contract.columns}
    # OHLCV core + timeframe + anchors
    assert {"open", "high", "low", "close", "volume", "trade_count", "timeframe"}.issubset(names)


@pytest.mark.parametrize("tf", MDPS_TIMEFRAMES_CEFI)
def test_cefi_perpetual_book5_candles(tf: str) -> None:
    contract = lookup_contract(asset_group="cefi", instrument_type="perpetual", data_type=MDPS_KEY_BOOK5(tf))
    names = {c.name for c in contract.columns}
    assert set(BOOK_SUMMARY_COLUMN_NAMES).issubset(names)


@pytest.mark.parametrize("tf", MDPS_TIMEFRAMES_CEFI)
def test_cefi_perpetual_deriv_candles(tf: str) -> None:
    contract = lookup_contract(asset_group="cefi", instrument_type="perpetual", data_type=MDPS_KEY_DERIV(tf))
    names = {c.name for c in contract.columns}
    assert {"funding_rate_mean", "mark_price_mean", "index_price_mean"}.issubset(names)


@pytest.mark.parametrize("tf", MDPS_TIMEFRAMES_CEFI)
def test_cefi_perpetual_deriv_ohlcv_is_nullable(tf: str) -> None:
    """derivative_ticker bars carry NULLABLE OHLC + nullable extension columns.

    The producing adapter no longer LOCF-carries a stale mark price into a
    window that held no observation (operator ruling 2026-07-20 — "the last
    result within the time window we want, else NaN price and 0 volume so we
    don't assume data was in that window and downstream handles"). A
    covered-but-empty window therefore legitimately has no price, and a
    non-nullable OHLC pack would reject the write outright — which is exactly
    the P0 that produced 140 attempted_failed/SCHEMA_VALIDATION_FAILED rows and
    zero objects. ``volume`` stays 0 (a flow quantity), never null.
    """
    contract = lookup_contract(asset_group="cefi", instrument_type="perpetual", data_type=MDPS_KEY_DERIV(tf))
    by_name = {c.name: c for c in contract.columns}
    for col in ("open", "high", "low", "close"):
        assert by_name[col].nullable is True, f"{col} must be nullable on a derivative_ticker bar"
    for col in ("funding_rate_mean", "mark_price_mean", "index_price_mean"):
        assert by_name[col].nullable is True


@pytest.mark.parametrize("tf", MDPS_TIMEFRAMES_CEFI)
def test_cefi_perpetual_liq_aggregates(tf: str) -> None:
    contract = lookup_contract(asset_group="cefi", instrument_type="perpetual", data_type=MDPS_KEY_LIQ(tf))
    names = {c.name for c in contract.columns}
    # Liquidation aggregates are NOT OHLCV — just count + notional.
    assert "liquidation_count" in names
    assert "liquidation_notional_usd" in names
    assert "open" not in names


@pytest.mark.parametrize("tf", MDPS_TIMEFRAMES_CEFI)
def test_cefi_spot_pair_candles(tf: str) -> None:
    trades = lookup_contract(asset_group="cefi", instrument_type="spot_pair", data_type=MDPS_KEY_TRADES(tf))
    book5 = lookup_contract(asset_group="cefi", instrument_type="spot_pair", data_type=MDPS_KEY_BOOK5(tf))
    assert trades.symbol_column == "symbol"
    assert book5.symbol_column == "symbol"


@pytest.mark.parametrize("tf", MDPS_TIMEFRAMES_OPTIONS)
def test_cefi_options_chain_candles_key_on_underlying(tf: str) -> None:
    contract = lookup_contract(asset_group="cefi", instrument_type="options_chain", data_type=MDPS_KEY_TRADES(tf))
    assert contract.symbol_column == "underlying"


@pytest.mark.parametrize("tf", MDPS_TIMEFRAMES_OPTIONS)
def test_cefi_futures_chain_candles_key_on_underlying(tf: str) -> None:
    contract = lookup_contract(asset_group="cefi", instrument_type="futures_chain", data_type=MDPS_KEY_TRADES(tf))
    assert contract.symbol_column == "underlying"


# ---------------------------------------------------------------------------
# TradFi re-aggregated + options / index
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("tf", MDPS_TIMEFRAMES_TRADFI_RE_AGGREGATED)
def test_tradfi_future_higher_timeframes(tf: str) -> None:
    contract = lookup_contract(asset_group="tradfi", instrument_type="future", data_type=MDPS_KEY_TRADES(tf))
    assert contract.symbol_column == "symbol"


@pytest.mark.parametrize("tf", MDPS_TIMEFRAMES_TRADFI_RE_AGGREGATED)
def test_tradfi_equity_higher_timeframes(tf: str) -> None:
    contract = lookup_contract(asset_group="tradfi", instrument_type="equity", data_type=MDPS_KEY_TRADES(tf))
    assert contract.symbol_column == "symbol"


@pytest.mark.parametrize("tf", MDPS_TIMEFRAMES_OPTIONS)
def test_tradfi_options_chain_candles(tf: str) -> None:
    contract = lookup_contract(asset_group="tradfi", instrument_type="options_chain", data_type=MDPS_KEY_TRADES(tf))
    assert contract.symbol_column == "underlying"


@pytest.mark.parametrize("tf", MDPS_TIMEFRAMES_INDEX)
def test_tradfi_index_candles(tf: str) -> None:
    contract = lookup_contract(asset_group="tradfi", instrument_type="index", data_type=MDPS_KEY_TRADES(tf))
    assert contract.symbol_column == "symbol"


# ---------------------------------------------------------------------------
# DeFi candles
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("tf", MDPS_TIMEFRAMES_DEFI)
def test_defi_pool_swap_candles_include_chain(tf: str) -> None:
    contract = lookup_contract(asset_group="defi", instrument_type="pool", data_type=MDPS_KEY_SWAPS(tf))
    names = {c.name for c in contract.columns}
    assert "chain" in names
    # swap-count / USD-volume live in the OHLCV-core `trade_count` / `volume`
    # columns; the old DeFi-specific `swap_count` / `volume_quote_usd` aliases
    # were exact duplicates and have been dropped from the swaps candle
    # (DeFi #4 / C0-RD6 — _DEX_EXT split).
    assert "trade_count" in names
    assert "volume" in names
    assert "swap_count" not in names
    assert "volume_quote_usd" not in names
    assert contract.symbol_column == "pool_id"


@pytest.mark.parametrize("tf", MDPS_TIMEFRAMES_DEFI)
def test_defi_pool_state_candles_include_chain(tf: str) -> None:
    contract = lookup_contract(asset_group="defi", instrument_type="pool", data_type=MDPS_KEY_POOL_STATE(tf))
    names = {c.name for c in contract.columns}
    assert "chain" in names
    # state candle legitimately keeps `swap_count` (not a duplicate here) and
    # never carried `volume_quote_usd`.
    assert "swap_count" in names
    assert "volume_quote_usd" not in names
    assert contract.symbol_column == "symbol"


@pytest.mark.parametrize("tf", MDPS_TIMEFRAMES_OPTIONS)
def test_defi_a_token_candles_include_chain_and_key_on_token(tf: str) -> None:
    for key_fn in (MDPS_KEY_LENDING, MDPS_KEY_RATE, MDPS_KEY_ORACLE):
        contract = lookup_contract(asset_group="defi", instrument_type="a_token", data_type=key_fn(tf))
        names = {c.name for c in contract.columns}
        assert "chain" in names
        assert contract.symbol_column == "token"


@pytest.mark.parametrize("tf", MDPS_TIMEFRAMES_OPTIONS)
def test_defi_lst_candles_include_chain(tf: str) -> None:
    for key_fn in (MDPS_KEY_LST, MDPS_KEY_ORACLE):
        contract = lookup_contract(asset_group="defi", instrument_type="lst", data_type=key_fn(tf))
        names = {c.name for c in contract.columns}
        assert "chain" in names
        assert contract.symbol_column == "symbol"


# ---------------------------------------------------------------------------
# Sports + Prediction candles
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("tf", MDPS_TIMEFRAMES_SPORTS)
def test_sports_odds_candles(tf: str) -> None:
    contract = lookup_contract(asset_group="sports", instrument_type="odds", data_type=MDPS_KEY_ODDS(tf))
    assert contract.symbol_column == "fixture_id"
    names = {c.name for c in contract.columns}
    assert "quote_count" in names
    assert "source_count" in names


@pytest.mark.parametrize("tf", MDPS_TIMEFRAMES_PREDICTION)
def test_prediction_market_candles(tf: str) -> None:
    contract = lookup_contract(
        asset_group="prediction",
        instrument_type="prediction_market",
        data_type=MDPS_KEY_PRED(tf),
    )
    assert contract.symbol_column == "condition_id"
    names = {c.name for c in contract.columns}
    assert "chain" in names
    assert "quote_count" in names


@pytest.mark.parametrize("tf", MDPS_TIMEFRAMES_PREDICTION_TRADES)
def test_prediction_market_uppercase_trades_candles(tf: str) -> None:
    """PREDICTION_MARKET (uppercase) contracts are for MDPS candle output.

    Polymarket MTDS tick parquets use instrument_type="PREDICTION_MARKET" (uppercase).
    MDPS aggregates them via the trades→ohlcv key mapping. These contracts must:
    - NOT include chain (prediction is not DeFi onchain)
    - use symbol as anchor (CandleOutput.symbol, not condition_id)
    - have nullable OHLCV (alive market with zero trades → Category D NaN bars)
    """
    contract = lookup_contract(
        asset_group="prediction",
        instrument_type="PREDICTION_MARKET",
        data_type=MDPS_KEY_TRADES(tf),
    )
    assert contract.symbol_column == "symbol"
    names = {c.name for c in contract.columns}
    assert "chain" not in names
    open_col = next(c for c in contract.columns if c.name == "open")
    assert open_col.nullable is True, "OHLCV must be nullable for Category D prediction bars"


@pytest.mark.parametrize("tf", MDPS_TIMEFRAMES_PREDICTION_TRADES)
def test_prediction_unknown_fallback_candles(tf: str) -> None:
    """UNKNOWN fallback contracts guard edge-cases where instrument_type resolves to UNKNOWN."""
    contract = lookup_contract(
        asset_group="prediction",
        instrument_type="UNKNOWN",
        data_type=MDPS_KEY_TRADES(tf),
    )
    assert contract.symbol_column == "symbol"
    names = {c.name for c in contract.columns}
    assert "chain" not in names
    open_col = next(c for c in contract.columns if c.name == "open")
    assert open_col.nullable is True


@pytest.mark.parametrize(
    "source_dt",
    ("odds_movement", "odds_snapshot", "odds_horizon_bucket", "arbitrage_opportunity"),
)
@pytest.mark.parametrize("tf", MDPS_TIMEFRAMES_SPORTS)
def test_sports_derived_candles_registered(tf: str, source_dt: str) -> None:
    """§6E P1: odds_movement / odds_snapshot / odds_horizon_bucket /
    arbitrage_opportunity contracts exist. ``odds_snapshot`` was missing from
    the registration loop until 2026-07-27 — its CandleAdapterRegistry
    adapter (SportsOddsSnapshotAdapter) existed but had no SchemaContract,
    so every write hard-failed. Regression:
    plans/active/issues/mdps_t1_recon_job_oom_failing_7_days_2026_07_26.md
    Update 5."""
    contract = lookup_contract(
        asset_group="sports",
        instrument_type="odds",
        data_type=f"{source_dt}_{tf}",
    )
    assert contract.symbol_column == "symbol"
    names = {c.name for c in contract.columns}
    assert "instrument_id" in names
    assert "venue" in names
    assert "symbol" in names
    open_col = next(c for c in contract.columns if c.name == "open")
    assert open_col.nullable is True
    assert "quote_count" not in names, f"{source_dt} adapter does not emit quote_count"


@pytest.mark.parametrize(
    "source_dt",
    ("odds_movement", "odds_snapshot", "odds_horizon_bucket", "arbitrage_opportunity"),
)
@pytest.mark.parametrize("tf", MDPS_TIMEFRAMES_SPORTS)
@pytest.mark.parametrize(
    "market_instrument_type",
    (
        "MATCH_ODDS",
        "MATCH_ODDS_LAY",
        "ASIAN_HANDICAP_0_25",
        "ASIAN_HANDICAP_M1_5",
        "OVER_UNDER_2_5",
        "BOTH_TEAMS_TO_SCORE",
        "SOME_FUTURE_MARKET_TYPE_NOT_YET_INVENTED",
    ),
)
def test_sports_derived_candles_resolve_per_market_instrument_type(
    tf: str, source_dt: str, market_instrument_type: str
) -> None:
    """Regression for the t1-recon sports leg failure (2026-07-27): MDPS's
    ``_infer_instrument_type`` extracts the raw per-market token (MATCH_ODDS,
    ASIAN_HANDICAP_0_25, OVER_UNDER_2_5, ...) from the canonical instrument_id
    for these candle writes — an open-ended vocabulary (handicap/total points
    are arbitrary floats per ``build_instrument_id``'s ``point`` arg) that can
    never be fully enumerated. Every real market must still resolve to the
    single generic ``("sports", "odds", data_type)`` contract because all
    four adapters emit the identical CandleOutput shape regardless of market.
    Deliberately includes a nonsense/never-registered market-type string to
    prove the fallback is genuinely open-ended, not a disguised enumeration.
    """
    generic = CONTRACT_REGISTRY[("sports", "odds", f"{source_dt}_{tf}")]
    contract = lookup_contract(
        asset_group="sports",
        instrument_type=market_instrument_type,
        data_type=f"{source_dt}_{tf}",
    )
    assert contract is generic


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
            # OK for pre-existing tradfi ohlcv_1m Databento pass-throughs (future, equity,
            # futures_chain, combo, UNKNOWN aliases all share TRADFI_FUTURE_OHLCV_1M schema).
            assert (
                dt == "ohlcv_1m"
                and category == "tradfi"
                and itype in {"future", "equity", "futures_chain", "combo", "UNKNOWN"}
            ), f"candle contract {(category, itype, dt)} missing 'timeframe' column"
