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
    MDPS_KEY_ODDS_SNAP,
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
from unified_api_contracts.registry.market_data_categories import (
    VALID_DATA_TYPES_BY_AG_AND_INSTRUMENT_TYPE,
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


@pytest.mark.parametrize("instrument_type", ["future", "futures_chain", "combo", "UNKNOWN"])
def test_tradfi_ohlcv_1s_registered(instrument_type: str) -> None:
    """Databento ohlcv_1s pass-through must resolve for CME future/futures_chain/
    combo/UNKNOWN, reusing the timeframe-agnostic TRADFI_FUTURE_OHLCV_1M schema.

    Regression for dp_vm_gone_no_capture_mdps_tradfi_ohlcv_1s_missing_contract_2026_07_31:
    a full-year tradfi backfill VM raised SchemaContractNotFoundError on every
    ohlcv_1s file (and the 15m/1h/4h/24h candles derived from it), all year,
    because this key was never registered.
    """
    contract = CONTRACT_REGISTRY[("tradfi", instrument_type, "ohlcv_1s")]
    assert contract is TRADFI_FUTURE_OHLCV_1M
    resolved = lookup_contract(asset_group="tradfi", instrument_type=instrument_type, data_type="ohlcv_1s")
    assert resolved is TRADFI_FUTURE_OHLCV_1M


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


@pytest.mark.parametrize("tf", MDPS_TIMEFRAMES_CEFI)
def test_cefi_future_trades_candles(tf: str) -> None:
    """Standalone dated future (e.g. DERIBIT BTC-USD@INV-20260627), not chain-bundled.

    Regression for cefi_future_instrument_type_no_candle_schema_contract_2026_07_21:
    every CEFI FUTURE candle write failed "No SchemaContract registered" because this
    instrument_type had no contract at all (CEFI's perpetual/spot_pair loop never
    covered it, unlike TradFi's `future`, which already registers the same shape).
    """
    contract = lookup_contract(asset_group="cefi", instrument_type="future", data_type=MDPS_KEY_TRADES(tf))
    assert contract.symbol_column == "symbol"


@pytest.mark.parametrize("tf", MDPS_TIMEFRAMES_CEFI)
def test_cefi_future_liq_aggregates(tf: str) -> None:
    """Dated CeFi futures (e.g. BINANCE-FUTURES ETH-USDT@LIN-20260925) DO emit
    liquidation events — regression for
    mdps_liq_agg_contract_missing_future_instrument_type_2026_07_27: a real-VM
    proof-sweep found 4 dated-futures instruments failing "No SchemaContract
    registered ... instrument_type='FUTURE' data_type='liq_agg_1d'" because the
    contract only ever covered `perpetual`.
    """
    contract = lookup_contract(asset_group="cefi", instrument_type="future", data_type=MDPS_KEY_LIQ(tf))
    names = {c.name for c in contract.columns}
    assert "liquidation_count" in names
    assert "liquidation_notional_usd" in names
    assert "open" not in names


@pytest.mark.parametrize("tf", MDPS_TIMEFRAMES_CEFI)
def test_cefi_future_book5_candles(tf: str) -> None:
    """Dated CeFi futures (e.g. DERIBIT/OKX-FUTURES) carry their own live order book,
    captured separately from perpetuals — regression for the follow-up audit in
    mdps_liq_agg_contract_missing_future_instrument_type_2026_07_27 (todo 2): a scoped
    live GCS sample (2026-07-29, DERIBIT + OKX-FUTURES, 4 days) confirmed real, ongoing
    `instrument_type=future/data_type=book_snapshot_5` raw-tick capture with no
    registered candle contract — the same "No SchemaContract registered" crash class as
    the already-fixed trades/liq_agg gaps, just not yet triggered by a live VM run.
    """
    contract = lookup_contract(asset_group="cefi", instrument_type="future", data_type=MDPS_KEY_BOOK5(tf))
    names = {c.name for c in contract.columns}
    assert set(BOOK_SUMMARY_COLUMN_NAMES).issubset(names)


@pytest.mark.parametrize("tf", MDPS_TIMEFRAMES_OPTIONS)
def test_cefi_options_chain_candles_key_on_underlying(tf: str) -> None:
    contract = lookup_contract(asset_group="cefi", instrument_type="options_chain", data_type=MDPS_KEY_TRADES(tf))
    assert contract.symbol_column == "underlying"


@pytest.mark.parametrize("tf", MDPS_TIMEFRAMES_OPTIONS)
def test_cefi_futures_chain_candles_key_on_underlying(tf: str) -> None:
    contract = lookup_contract(asset_group="cefi", instrument_type="futures_chain", data_type=MDPS_KEY_TRADES(tf))
    assert contract.symbol_column == "underlying"


# ---------------------------------------------------------------------------
# Class-of-bug regression — every CEFI raw-tick-capturable instrument_type has
# a registered candle contract for every capturable data_type that has an MDPS
# candle equivalent.
#
# Closes cefi_future_instrument_type_no_candle_schema_contract_2026_07_21 todo
# 3 ("closes the class of bug, not just this instance") — cross-checks the
# per-instrument_type candle coverage directly against
# ``VALID_DATA_TYPES_BY_AG_AND_INSTRUMENT_TYPE`` (the SSOT for what a CEFI
# instrument_type genuinely captures at the raw-tick layer) rather than
# hand-listing an expected set, so a future raw-tick capability the registry
# grows without a matching candle-contract addition fails THIS test instead of
# crashing silently on the next real MDPS run.
#
# ``derivative_ticker`` is intentionally excluded for ``future``: a scoped live
# GCS sample (2026-07-29, DERIBIT + OKX-FUTURES, 4 days) found ZERO real
# objects at that (instrument_type, data_type) pair — dated futures settle on
# expiry, not via a funding/mark-price ticker stream, so
# ``VALID_DATA_TYPES_BY_AG_AND_INSTRUMENT_TYPE[("cefi", "future")]``'s own
# "UNCERTAIN — cefi-owner verify" tag over-states real capture for this one
# data_type; registering an unused contract would be speculative, not a fix for
# an observed gap (see the `future`/book5 registration's comment in
# ``_candle_contracts.py`` for the full evidence).
_CEFI_RAW_DATA_TYPE_TO_CANDLE_KEY_FN = {
    "trades": MDPS_KEY_TRADES,
    "book_snapshot_5": MDPS_KEY_BOOK5,
    "derivative_ticker": MDPS_KEY_DERIV,
    "liquidations": MDPS_KEY_LIQ,
}
# Raw data_types with NO MDPS candle equivalent (skip, don't fail on these):
#   - ohlcv_1m: already a pre-aggregated OHLCV capture, not MDPS-derived input.
#   - perp_funding: settlement events, no candle-shaped rollup defined.
_CEFI_NO_CANDLE_EQUIVALENT = frozenset({"ohlcv_1m", "perp_funding"})
# Known, evidence-backed exclusions from the registry's raw claim (see docstring above).
_CEFI_CANDLE_COVERAGE_EXCLUSIONS: frozenset[tuple[str, str]] = frozenset({("future", "derivative_ticker")})
# Leaf instrument_types only — bundle grains (options_chain/futures_chain) and
# roll-up-only leaves (option/combo, frozenset()) are covered by their own
# dedicated tests above, not this per-raw-data_type sweep.
_CEFI_LEAF_INSTRUMENT_TYPES = ("perpetual", "spot_pair", "future")


def _cefi_candle_coverage_cases() -> list[tuple[str, str]]:
    cases: list[tuple[str, str]] = []
    for itype in _CEFI_LEAF_INSTRUMENT_TYPES:
        raw_data_types = VALID_DATA_TYPES_BY_AG_AND_INSTRUMENT_TYPE[("cefi", itype)]
        for raw_dt in raw_data_types:
            if raw_dt in _CEFI_NO_CANDLE_EQUIVALENT:
                continue
            if (itype, raw_dt) in _CEFI_CANDLE_COVERAGE_EXCLUSIONS:
                continue
            assert raw_dt in _CEFI_RAW_DATA_TYPE_TO_CANDLE_KEY_FN, (
                f"cefi/{itype}/{raw_dt} has no candle-key mapping in this test — add one "
                "(or an explicit, evidence-backed exclusion) before this raw data_type can "
                "be asserted covered."
            )
            cases.append((itype, raw_dt))
    return cases


@pytest.mark.parametrize("itype,raw_dt", _cefi_candle_coverage_cases())
@pytest.mark.parametrize("tf", MDPS_TIMEFRAMES_CEFI)
def test_cefi_every_capturable_instrument_type_has_candle_contract(tf: str, itype: str, raw_dt: str) -> None:
    key_fn = _CEFI_RAW_DATA_TYPE_TO_CANDLE_KEY_FN[raw_dt]
    # Must not raise — a raise here is exactly the live "No SchemaContract
    # registered for asset_group='cefi' instrument_type=... data_type=..."
    # crash this test class exists to catch before it reaches a real VM.
    lookup_contract(asset_group="cefi", instrument_type=itype, data_type=key_fn(tf))


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
# TradFi ohlcv_24h alias (mdps_tradfi_ohlcv_15m_24h_conversion_still_zero_2026_07_27.md,
# 2026-08-03 live re-run): future/equity ohlcv_24h shard writes crashed
# "No SchemaContract registered" — the live write path's data_type token is
# the literal "ohlcv_24h" the CLI/manifest use, not this module's internal
# "ohlcv_1d". combo/futures_chain deliberately excluded (see
# _candle_contracts.py's registration-loop comment — tradfi-owner-verified
# VALID_DATA_TYPES_BY_AG_AND_INSTRUMENT_TYPE policy, not a gap).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("instrument_type", ["future", "equity"])
def test_tradfi_ohlcv_24h_alias_resolves(instrument_type: str) -> None:
    contract = lookup_contract(asset_group="tradfi", instrument_type=instrument_type, data_type="ohlcv_24h")
    assert contract.symbol_column == "symbol"
    assert contract.data_type == "ohlcv_24h"


def test_tradfi_options_chain_ohlcv_24h_alias_resolves() -> None:
    contract = lookup_contract(asset_group="tradfi", instrument_type="options_chain", data_type="ohlcv_24h")
    assert contract.symbol_column == "underlying"
    assert contract.data_type == "ohlcv_24h"


def test_tradfi_index_ohlcv_24h_alias_resolves() -> None:
    contract = lookup_contract(asset_group="tradfi", instrument_type="index", data_type="ohlcv_24h")
    assert contract.symbol_column == "symbol"
    assert contract.data_type == "ohlcv_24h"


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


@pytest.mark.parametrize("tf", MDPS_TIMEFRAMES_SPORTS)
def test_sports_odds_snap_candles_registered(tf: str) -> None:
    """Snapshot-vs-candle discriminator (2026-08-08, sports_taxonomy_p1):
    ``odds_snap_{tf}`` — the collapsed model's target key for the LOCF
    point-in-time form — is discoverable and distinct from the OHLC candle
    key (``odds_ohlcv_{tf}``, ``MDPS_KEY_ODDS``)."""
    contract = lookup_contract(asset_group="sports", instrument_type="odds", data_type=MDPS_KEY_ODDS_SNAP(tf))
    assert contract.symbol_column == "symbol"
    names = {c.name for c in contract.columns}
    assert "instrument_id" in names
    assert "venue" in names
    open_col = next(c for c in contract.columns if c.name == "open")
    assert open_col.nullable is True
    assert MDPS_KEY_ODDS_SNAP(tf) != MDPS_KEY_ODDS(tf), "snapshot key must never collide with the OHLC candle key"


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
