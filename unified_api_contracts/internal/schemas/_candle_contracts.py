"""MDPS processed-candle SchemaContracts — Phase 5b.1.

Plan: data_pipeline_completion_2026_04_18 §Phase 5b. MDPS produces per-
``(category, instrument_type, source_data_type, timeframe)`` OHLCV+extension
candle files, co-located inside the MTDS tick buckets under
``processed_candles/`` (sports uses ``processed/``). Each source produces a
different candle shape:

    ``trades``             → OHLCV + trade_count + volume
    ``book_snapshot_5``    → OHLCV(mid) + spread/depth/imbalance means
    ``derivative_ticker``  → OHLCV + funding/mark/index means
    ``liquidations``       → count + notional aggregates (not pure OHLCV)
    ``dex_pool_swaps``     → OHLCV (swap count = ``trade_count``, USD volume = ``volume``)
    ``dex_pool_state``     → OHLCV(mid) + swap_count
    ``lending_indices``    → OHLCV of supply/borrow index
    ``rate_indices``       → OHLCV of rate_indices
    ``oracle_prices``      → OHLCV of oracle price
    ``lst_rates``          → OHLCV of LST exchange_rate
    ``odds``               → OHLCV of decimal odds + quote_count
    ``prediction_market``  → OHLCV of prediction price + quote_count

Key naming convention — ``data_type`` encodes source + timeframe so the
three-tuple ``(category, instrument_type, data_type)`` remains the single
registry key (parity with the existing ``ohlcv_1m`` contracts on TradFi):

    trades             → ``ohlcv_{tf}``                (preserves existing TradFi key)
    book_snapshot_5    → ``book5_ohlcv_{tf}``
    derivative_ticker  → ``deriv_ohlcv_{tf}``
    liquidations       → ``liq_agg_{tf}``              (count+notional, not OHLCV)
    dex_pool_swaps     → ``swaps_ohlcv_{tf}``
    dex_pool_state     → ``state_ohlcv_{tf}``
    lending_indices    → ``lending_ohlcv_{tf}``
    rate_indices       → ``rate_ohlcv_{tf}``
    oracle_prices      → ``oracle_ohlcv_{tf}``
    lst_rates          → ``lst_ohlcv_{tf}``
    odds               → ``odds_ohlcv_{tf}``
    prediction_market  → ``pred_ohlcv_{tf}``

Timeframes per category (decided by strategy need):

    CeFi       {15s, 1m, 5m, 15m, 1h, 4h, 1d}
    TradFi     {1m, 5m, 15m, 1h, 4h, 1d}              (1m native from Databento)
    DeFi       {15s, 1m, 5m, 15m, 1h, 1d}
    Sports     {1m, 15m, 1h}
    Prediction {1m, 15m, 1h}

Options-chain / futures-chain candles aggregate trades only (book aggregation
not meaningful for illiquid contracts): {1m, 15m, 1h, 1d}.

Registry mutations at module-import time — imported as a side-effect from
``contracts.py``. Do NOT import this module directly; use
``unified_api_contracts.internal.schemas.contracts``.
"""

from __future__ import annotations

from typing import cast

from unified_api_contracts.internal.domain.market_data_processing import (
    BOOK_SUMMARY_COLUMNS,
)
from unified_api_contracts.internal.schemas.contracts import (
    CHAIN_COL,
    CONTRACT_REGISTRY,
    INSTRUMENT_ID_COL,
    SYMBOL_COL,
    TS_EVENT_COL,
    UNDERLYING_COL,
    VENUE_COL,
    AssetGroupLiteral,
    ColumnSpec,
    SchemaContract,
)

# ---------------------------------------------------------------------------
# Base + extension column packs
# ---------------------------------------------------------------------------

_OHLCV_CORE: list[ColumnSpec] = [
    ColumnSpec(name="open", dtype="float64", nullable=False),
    ColumnSpec(name="high", dtype="float64", nullable=False),
    ColumnSpec(name="low", dtype="float64", nullable=False),
    ColumnSpec(name="close", dtype="float64", nullable=False),
    ColumnSpec(name="volume", dtype="float64", nullable=True),
    ColumnSpec(name="trade_count", dtype="int64", nullable=True),
]

# Trades-derived bars: OHLC is nullable when no trades occur in the interval.
# ALSO used by the derivative_ticker bar (``deriv_ohlcv_{tf}``) — see the
# nullable_ohlcv=True note at its _register() call below. Book bars keep
# _OHLCV_CORE (non-nullable): the book adapter still LOCF-densifies its grid,
# so a quote is always present on every emitted bar.
_OHLCV_CORE_TRADES: list[ColumnSpec] = [
    ColumnSpec(name="open", dtype="float64", nullable=True),
    ColumnSpec(name="high", dtype="float64", nullable=True),
    ColumnSpec(name="low", dtype="float64", nullable=True),
    ColumnSpec(name="close", dtype="float64", nullable=True),
    ColumnSpec(name="volume", dtype="float64", nullable=True),
    ColumnSpec(name="trade_count", dtype="int64", nullable=True),
]

_TIMEFRAME_COL = ColumnSpec(
    name="timeframe",
    dtype="string",
    nullable=False,
    description="Bucket size (15s, 1m, 5m, 15m, 1h, 4h, 1d).",
)

_BOOK5_EXT: list[ColumnSpec] = [
    ColumnSpec(name=spec.name, dtype="float64", nullable=True) for spec in BOOK_SUMMARY_COLUMNS
]

# derivative_ticker bar extension.
#
# NAMING vs SEMANTICS: the ``_mean`` suffix is a MISNOMER retained for on-disk
# stability — the value is the LAST OBSERVATION IN THE BAR WINDOW, not an
# arithmetic mean. derivative_ticker is a snapshot stream (funding / mark /
# index are point-in-time states), so a within-bar average would fabricate a
# number that never existed on the wire. The producing adapter
# (``CefiDerivativeAdapter``) and the roll-up rule (``"last"``) are both
# last-in-window; only the column NAME says "mean". All three are nullable
# because a bar whose window contained no ticker observation legitimately has
# no value — see the nullable_ohlcv note on the _register() call below.
_DERIV_EXT: list[ColumnSpec] = [
    ColumnSpec(name="funding_rate_mean", dtype="float64", nullable=True),
    ColumnSpec(name="mark_price_mean", dtype="float64", nullable=True),
    ColumnSpec(name="index_price_mean", dtype="float64", nullable=True),
]

# DEX candle extensions. `swap_count`/`volume_quote_usd` were originally a
# shared `_DEX_EXT` applied to BOTH swaps and state candles, but on the SWAPS
# candle they exactly duplicate the OHLCV-core `trade_count`/`volume` columns
# (verified identical to the last digit/decimal — DeFi #4 / C0-RD6). The split:
#   • swaps candle (`swaps_ohlcv_{tf}`)  → NO extension cols (the duplicates are
#     dropped; the values survive losslessly in `trade_count`/`volume`).
#   • state candle (`state_ohlcv_{tf}`)  → keeps `swap_count` only (NOT a
#     duplicate here — `dex_pool_state` carries no per-bar trade_count semantic;
#     `volume_quote_usd` was never part of the documented state shape).
_DEX_SWAPS_EXT: list[ColumnSpec] = []
_DEX_STATE_EXT: list[ColumnSpec] = [
    ColumnSpec(name="swap_count", dtype="int64", nullable=True),
]

_ODDS_EXT: list[ColumnSpec] = [
    ColumnSpec(name="quote_count", dtype="int64", nullable=True),
    ColumnSpec(name="source_count", dtype="int64", nullable=True),
]

_PRED_EXT: list[ColumnSpec] = [
    ColumnSpec(name="quote_count", dtype="int64", nullable=True),
]


# ---------------------------------------------------------------------------
# Timeframe catalogues
# ---------------------------------------------------------------------------

_TIMEFRAMES_ALL: tuple[str, ...] = ("15s", "1m", "5m", "15m", "1h", "4h", "1d")
_TIMEFRAMES_CEFI: tuple[str, ...] = _TIMEFRAMES_ALL
_TIMEFRAMES_TRADFI: tuple[str, ...] = ("1m", "5m", "15m", "1h", "4h", "1d")
_TIMEFRAMES_DEFI: tuple[str, ...] = ("15s", "1m", "5m", "15m", "1h", "4h", "1d")
_TIMEFRAMES_OPTIONS: tuple[str, ...] = ("1m", "15m", "1h", "1d")
_TIMEFRAMES_SPORTS: tuple[str, ...] = ("1m", "15m", "1h")
_TIMEFRAMES_PREDICTION: tuple[str, ...] = ("1m", "15m", "1h")
_TIMEFRAMES_INDEX: tuple[str, ...] = ("1m", "5m", "15m", "1h", "1d")


# ---------------------------------------------------------------------------
# Data-type key naming (source → key prefix)
# ---------------------------------------------------------------------------


# Each source produces a distinct shape (and therefore a distinct contract).
# The key schema is ``{prefix}_{timeframe}`` so ``data_type`` remains a single
# string usable by the existing three-tuple registry. ``trades`` keeps the
# ``ohlcv_{tf}`` prefix for parity with the existing TradFi ohlcv_1m keys.
def _trades_key(tf: str) -> str:
    return f"ohlcv_{tf}"


def _book5_key(tf: str) -> str:
    return f"book5_ohlcv_{tf}"


def _deriv_key(tf: str) -> str:
    return f"deriv_ohlcv_{tf}"


def _liq_key(tf: str) -> str:
    return f"liq_agg_{tf}"


def _swaps_key(tf: str) -> str:
    return f"swaps_ohlcv_{tf}"


def _pool_state_key(tf: str) -> str:
    return f"state_ohlcv_{tf}"


def _lending_key(tf: str) -> str:
    return f"lending_ohlcv_{tf}"


def _rate_key(tf: str) -> str:
    return f"rate_ohlcv_{tf}"


def _oracle_key(tf: str) -> str:
    return f"oracle_ohlcv_{tf}"


def _lst_key(tf: str) -> str:
    return f"lst_ohlcv_{tf}"


def _odds_key(tf: str) -> str:
    return f"odds_ohlcv_{tf}"


def _pred_key(tf: str) -> str:
    return f"pred_ohlcv_{tf}"


# ---------------------------------------------------------------------------
# Contract factory
# ---------------------------------------------------------------------------


def _build(
    category: str,
    instrument_type: str,
    data_type: str,
    *,
    symbol_column: str,
    extra_cols: list[ColumnSpec],
    include_chain: bool = False,
    ohlcv_core: bool = True,
    nullable_ohlcv: bool = False,
    liq_shape: bool = False,
    anchor_col: ColumnSpec | None = None,
) -> SchemaContract:
    """Build a SchemaContract for an MDPS candle variant.

    ``ohlcv_core=True`` prepends the OHLCV+volume+trade_count pack; pass
    ``False`` for liquidation aggregates which don't carry OHLCV.
    ``nullable_ohlcv=True`` switches to the trades-derived OHLC pack where
    open/high/low/close are nullable (empty intervals have no price formation).
    ``liq_shape=True`` uses the liquidation (count, notional_usd) pair.
    ``anchor_col`` — defaults to ``symbol`` — the per-row symbol anchor
    column declared on the schema alongside instrument_id.
    """
    anchor = anchor_col if anchor_col is not None else SYMBOL_COL
    columns: list[ColumnSpec] = [INSTRUMENT_ID_COL, VENUE_COL]
    if include_chain:
        columns.append(CHAIN_COL)
    columns.extend([anchor, TS_EVENT_COL])
    if liq_shape:
        columns.extend(
            [
                ColumnSpec(name="liquidation_count", dtype="int64", nullable=False),
                ColumnSpec(name="liquidation_notional_usd", dtype="float64", nullable=False),
            ]
        )
    elif ohlcv_core:
        columns.extend(_OHLCV_CORE_TRADES if nullable_ohlcv else _OHLCV_CORE)
    columns.append(_TIMEFRAME_COL)
    columns.extend(extra_cols)
    return SchemaContract(
        asset_group=cast(AssetGroupLiteral, category),
        instrument_type=instrument_type,
        data_type=data_type,
        columns=columns,
        symbol_column=symbol_column,
        required_row_count_min=1,
    )


def _register(contract: SchemaContract) -> None:
    CONTRACT_REGISTRY[(contract.asset_group, contract.instrument_type, contract.data_type)] = contract


# ---------------------------------------------------------------------------
# CeFi candles — perpetual x (trades | book_snapshot_5 | derivative_ticker |
#                            liquidations)
#                spot_pair x (trades | book_snapshot_5)
#                options_chain x trades (bundled per-underlying)
#                futures_chain x trades (bundled per-underlying)
# ---------------------------------------------------------------------------

for _tf in _TIMEFRAMES_CEFI:
    # perpetual
    _register(_build("cefi", "perpetual", _trades_key(_tf), symbol_column="symbol", extra_cols=[], nullable_ohlcv=True))
    _register(_build("cefi", "perpetual", _book5_key(_tf), symbol_column="symbol", extra_cols=_BOOK5_EXT))
    # nullable_ohlcv=True (2026-07-20): the derivative_ticker bar's OHLC is
    # driven from the mark-price snapshot, and the adapter no longer carries a
    # stale value forward into a window that had no observation (LOCF removed —
    # operator ruling: "the last result within the time window we want, else NaN
    # price and 0 volume, so we don't assume data was in that window and
    # downstream handles"). A covered-but-empty window therefore has genuinely
    # no price, and the row is written with NaN OHLC + NaN _DERIV_EXT + volume=0.
    #
    # The two "no value here" signals stay SEPARATE and must not be conflated:
    #   • parquet, per BIN  → row present + NaN price + 0 volume
    #                         == "we derived this window; nothing to aggregate in it"
    #   • manifest, per SHARD-DAY → capture_status answers "did we even derive it"
    #                         (captured / empty_confirmed+reason / attempted_failed /
    #                          expected_unattempted)
    # A consumer must never infer "was this fetched?" from a NaN in the parquet.
    # SSOT: codex/02-data/honest-absence-downstream-handling.md.
    _register(
        _build(
            "cefi",
            "perpetual",
            _deriv_key(_tf),
            symbol_column="symbol",
            extra_cols=_DERIV_EXT,
            nullable_ohlcv=True,
        )
    )
    _register(
        _build(
            "cefi",
            "perpetual",
            _liq_key(_tf),
            symbol_column="symbol",
            extra_cols=[],
            ohlcv_core=False,
            liq_shape=True,
        )
    )
    # spot_pair — no derivative_ticker / liquidations
    _register(_build("cefi", "spot_pair", _trades_key(_tf), symbol_column="symbol", extra_cols=[], nullable_ohlcv=True))
    _register(_build("cefi", "spot_pair", _book5_key(_tf), symbol_column="symbol", extra_cols=_BOOK5_EXT))
    # standalone dated future (non-chain-bundled per-contract futures, e.g. DERIBIT
    # BTC-USD@INV-20260627) — mirrors TradFi's `future` registration below (trades
    # only, no derivative_ticker/liquidations: those are perp-specific funding/
    # liquidation events that dated futures don't emit).
    # cefi_future_instrument_type_no_candle_schema_contract_2026_07_21: this
    # instrument_type is deliberately excluded from CEFI_CHAIN_INSTRUMENT_TYPES
    # (unified_api_contracts.gcs_paths, frozenset({"options_chain", "futures_chain"}))
    # so raw per-contract future ticks correctly route here rather than through the
    # chain-bundle path — the gap was a missing contract registration, not a routing
    # bug (confirmed: TradFi already registers standalone `future` the same way).
    _register(_build("cefi", "future", _trades_key(_tf), symbol_column="symbol", extra_cols=[], nullable_ohlcv=True))

for _tf in _TIMEFRAMES_OPTIONS:
    _register(
        _build(
            "cefi",
            "options_chain",
            _trades_key(_tf),
            symbol_column="underlying",
            extra_cols=[],
            anchor_col=UNDERLYING_COL,
            nullable_ohlcv=True,
        )
    )
    _register(
        _build(
            "cefi",
            "futures_chain",
            _trades_key(_tf),
            symbol_column="underlying",
            extra_cols=[],
            anchor_col=UNDERLYING_COL,
            nullable_ohlcv=True,
        )
    )


# ---------------------------------------------------------------------------
# TradFi candles — future x (trades | ohlcv_1m native → re-aggregated higher)
#                  equity x (trades | ohlcv_1m)
#                  options_chain x trades (bundled per-underlying)
#                  index x trades
# ---------------------------------------------------------------------------

# ``ohlcv_1m`` for future/equity already exists in contracts.py as the
# Databento pass-through — registering it here via factory would overwrite
# the canonical shape. So TradFi 1m keys are *deliberately* skipped for
# those two instrument_types; higher timeframes (5m / 15m / 1h / 4h / 1d)
# are re-aggregated and registered below.
_TIMEFRAMES_TRADFI_RE_AGGREGATED: tuple[str, ...] = tuple(tf for tf in _TIMEFRAMES_TRADFI if tf != "1m")

for _tf in _TIMEFRAMES_TRADFI_RE_AGGREGATED:
    _register(_build("tradfi", "future", _trades_key(_tf), symbol_column="symbol", extra_cols=[], nullable_ohlcv=True))
    _register(_build("tradfi", "equity", _trades_key(_tf), symbol_column="symbol", extra_cols=[], nullable_ohlcv=True))

for _tf in _TIMEFRAMES_OPTIONS:
    _register(
        _build(
            "tradfi",
            "options_chain",
            _trades_key(_tf),
            symbol_column="underlying",
            extra_cols=[],
            anchor_col=UNDERLYING_COL,
            nullable_ohlcv=True,
        )
    )

for _tf in _TIMEFRAMES_INDEX:
    _register(_build("tradfi", "index", _trades_key(_tf), symbol_column="symbol", extra_cols=[], nullable_ohlcv=True))


# ---------------------------------------------------------------------------
# DeFi candles — pool x (dex_pool_swaps | dex_pool_state)
#                a_token x (lending_indices | rate_indices | oracle_prices)
#                lst x (lst_rates | oracle_prices)
# ---------------------------------------------------------------------------
# OHLC semantics for `swaps_ohlcv_{tf}` (pool x dex_pool_swaps): open/high/low/
# close are the pool's **USD-normalized spot price**, computed per swap as
# `amountUSD / |base_amount|` (3-method fallback: amountUSD/base, then
# amount_in_usd/amount_in, then the raw token0/token1 ratio). This is a
# price-per-base-token-in-USD-terms, NOT the spot price of the quote asset — so
# for a USDC/WETH pool the values land near ≈1.0 (USDC-per-WETH expressed in USD
# units), which is correct and expected, not a bug. Downstream consumers that
# want ETH spot must read the WETH/USDC orientation accordingly.
# (features_service_defi_data_loading_blockers_2026_05_29 #3.)

for _tf in _TIMEFRAMES_DEFI:
    # pool
    _register(
        _build(
            "defi",
            "pool",
            _swaps_key(_tf),
            symbol_column="pool_id",
            extra_cols=_DEX_SWAPS_EXT,
            include_chain=True,
            nullable_ohlcv=True,
        )
    )
    # Fallback for migrated DEX files whose instrument_type cannot be inferred
    # (no instrument_type column + instrument_id lacks the ":pool:" colon-token).
    # Mirrors the tradfi UNKNOWN pattern at contracts.py:773. include_chain=False
    # because CandleOutput from the swap adapter does not populate a chain column.
    _register(
        _build(
            "defi",
            "UNKNOWN",
            _swaps_key(_tf),
            symbol_column="symbol",
            extra_cols=_DEX_SWAPS_EXT,
            include_chain=False,
            nullable_ohlcv=True,
        )
    )
    _register(
        _build(
            "defi",
            "pool",
            _pool_state_key(_tf),
            symbol_column="symbol",
            extra_cols=_DEX_STATE_EXT,
            include_chain=True,
        )
    )

for _tf in _TIMEFRAMES_OPTIONS:
    # a_token reserve candles — 1m/15m/1h/1d (intraday is 15s-noisy for
    # infrequent lending index updates, so skip sub-minute).
    _register(
        _build(
            "defi",
            "a_token",
            _lending_key(_tf),
            symbol_column="token",
            extra_cols=[],
            include_chain=True,
        )
    )
    _register(
        _build(
            "defi",
            "a_token",
            _rate_key(_tf),
            symbol_column="token",
            extra_cols=[],
            include_chain=True,
        )
    )
    _register(
        _build(
            "defi",
            "a_token",
            _oracle_key(_tf),
            symbol_column="token",
            extra_cols=[],
            include_chain=True,
        )
    )
    # lst candles — same cadence.
    _register(
        _build(
            "defi",
            "lst",
            _lst_key(_tf),
            symbol_column="symbol",
            extra_cols=[],
            include_chain=True,
        )
    )
    _register(
        _build(
            "defi",
            "lst",
            _oracle_key(_tf),
            symbol_column="symbol",
            extra_cols=[],
            include_chain=True,
        )
    )


# ---------------------------------------------------------------------------
# Sports candles — odds x trades (1m / 15m / 1h)
# ---------------------------------------------------------------------------

for _tf in _TIMEFRAMES_SPORTS:
    _register(
        _build(
            "sports",
            "odds",
            _odds_key(_tf),
            symbol_column="fixture_id",
            extra_cols=_ODDS_EXT,
            anchor_col=ColumnSpec(name="fixture_id", dtype="string", nullable=False),
            nullable_ohlcv=True,
        )
    )


# ---------------------------------------------------------------------------
# Sports derived candles — odds_movement, odds_snapshot, odds_horizon_bucket,
#                           arbitrage_opportunity  (1m / 15m / 1h)
#
# These adapters all produce standard CandleOutput (OHLCV + trade_count) with
# ``symbol`` as the instrument anchor.  Unlike the base ``odds_ohlcv`` shape
# they do NOT emit ``quote_count``/``source_count``.
# base granularity for all four is 15m (UAC BASE_GRANULARITY_BY_DATA_TYPE) so
# the MDPS timeframe loop skips 1m at runtime — registering 1m here is harmless
# and keeps the sports timeframe catalogue consistent.
#
# ``odds_snapshot`` was missing from this loop until 2026-07-27 (it registers
# a CandleAdapterRegistry adapter — SportsOddsSnapshotAdapter — identically to
# its 3 siblings, but had no corresponding SchemaContract entry, so every
# odds_snapshot_{tf} write hard-failed with SchemaContractNotFoundError). See
# plans/active/issues/mdps_t1_recon_job_oom_failing_7_days_2026_07_26.md Update 5.
# ---------------------------------------------------------------------------

for _tf in _TIMEFRAMES_SPORTS:
    for _sports_derived_dt in ("odds_movement", "odds_snapshot", "odds_horizon_bucket", "arbitrage_opportunity"):
        _register(
            _build(
                "sports",
                "odds",
                f"{_sports_derived_dt}_{_tf}",
                symbol_column="symbol",
                extra_cols=[],
                anchor_col=None,
                nullable_ohlcv=True,
            )
        )


# ---------------------------------------------------------------------------
# Prediction candles — prediction_market x trades (1m / 15m / 1h)
# ---------------------------------------------------------------------------

for _tf in _TIMEFRAMES_PREDICTION:
    _register(
        _build(
            "prediction",
            "prediction_market",
            _pred_key(_tf),
            symbol_column="condition_id",
            extra_cols=_PRED_EXT,
            include_chain=True,
            anchor_col=ColumnSpec(name="condition_id", dtype="string", nullable=False),
            nullable_ohlcv=True,
        )
    )


# ---------------------------------------------------------------------------
# Prediction trades-derived candles — PREDICTION_MARKET x trades
#
# The Polymarket MTDS tick parquets store instrument_type="PREDICTION_MARKET"
# (uppercase) as the canonical row value. When MDPS aggregates those rows into
# OHLCV bars via the trades→ohlcv prefix mapping, it calls lookup_contract with
# instrument_type="PREDICTION_MARKET". These entries close that registry gap so
# every MDPS default timeframe resolves without SchemaContractNotFoundError.
# ---------------------------------------------------------------------------

_TIMEFRAMES_PREDICTION_TRADES: tuple[str, ...] = ("15s", "1m", "5m", "15m", "1h", "4h", "1d")

for _tf in _TIMEFRAMES_PREDICTION_TRADES:
    _register(
        _build(
            "prediction",
            "PREDICTION_MARKET",
            _trades_key(_tf),
            symbol_column="symbol",
            extra_cols=[],
            include_chain=False,
            anchor_col=None,
            nullable_ohlcv=True,
        )
    )


# ---------------------------------------------------------------------------
# Prediction UNKNOWN fallback — defensive safety net
#
# 2-segment legacy instrument_ids (``POLYMARKET:condition_id``) flow through
# ``_infer_instrument_type`` step-5 fallback and emerge as instrument_type=
# the condition_id string, NOT "UNKNOWN". The root fix for §6F P0 is in
# ``PredictionTradesAdapter.preprocess()`` (3-segment keys); this UNKNOWN
# fallback guards any residual edge-cases where the outer instrument_id is
# empty or single-segment, causing step-6 to return "UNKNOWN".
# Mirrors the defi UNKNOWN swaps_ohlcv pattern (lines 374-386 above).
# ---------------------------------------------------------------------------

for _tf in _TIMEFRAMES_PREDICTION_TRADES:
    _register(
        _build(
            "prediction",
            "UNKNOWN",
            _trades_key(_tf),
            symbol_column="symbol",
            extra_cols=[],
            include_chain=False,
            anchor_col=None,
            nullable_ohlcv=True,
        )
    )


# ---------------------------------------------------------------------------
# Public API — timeframe catalogues + key helpers (exported for downstream
# MDPS writers + ml-training / features backfills).
# ---------------------------------------------------------------------------

MDPS_TIMEFRAMES_CEFI = _TIMEFRAMES_CEFI
MDPS_TIMEFRAMES_TRADFI = _TIMEFRAMES_TRADFI
MDPS_TIMEFRAMES_TRADFI_RE_AGGREGATED = _TIMEFRAMES_TRADFI_RE_AGGREGATED
MDPS_TIMEFRAMES_DEFI = _TIMEFRAMES_DEFI
MDPS_TIMEFRAMES_OPTIONS = _TIMEFRAMES_OPTIONS
MDPS_TIMEFRAMES_SPORTS = _TIMEFRAMES_SPORTS
MDPS_TIMEFRAMES_PREDICTION = _TIMEFRAMES_PREDICTION
MDPS_TIMEFRAMES_PREDICTION_TRADES = _TIMEFRAMES_PREDICTION_TRADES
MDPS_TIMEFRAMES_INDEX = _TIMEFRAMES_INDEX

MDPS_KEY_TRADES = _trades_key
MDPS_KEY_BOOK5 = _book5_key
MDPS_KEY_DERIV = _deriv_key
MDPS_KEY_LIQ = _liq_key
MDPS_KEY_SWAPS = _swaps_key
MDPS_KEY_POOL_STATE = _pool_state_key
MDPS_KEY_LENDING = _lending_key
MDPS_KEY_RATE = _rate_key
MDPS_KEY_ORACLE = _oracle_key
MDPS_KEY_LST = _lst_key
MDPS_KEY_ODDS = _odds_key
MDPS_KEY_PRED = _pred_key


__all__ = [
    "MDPS_KEY_BOOK5",
    "MDPS_KEY_DERIV",
    "MDPS_KEY_LENDING",
    "MDPS_KEY_LIQ",
    "MDPS_KEY_LST",
    "MDPS_KEY_ODDS",
    "MDPS_KEY_ORACLE",
    "MDPS_KEY_POOL_STATE",
    "MDPS_KEY_PRED",
    "MDPS_KEY_RATE",
    "MDPS_KEY_SWAPS",
    "MDPS_KEY_TRADES",
    "MDPS_TIMEFRAMES_CEFI",
    "MDPS_TIMEFRAMES_DEFI",
    "MDPS_TIMEFRAMES_INDEX",
    "MDPS_TIMEFRAMES_OPTIONS",
    "MDPS_TIMEFRAMES_PREDICTION",
    "MDPS_TIMEFRAMES_PREDICTION_TRADES",
    "MDPS_TIMEFRAMES_SPORTS",
    "MDPS_TIMEFRAMES_TRADFI",
    "MDPS_TIMEFRAMES_TRADFI_RE_AGGREGATED",
]
