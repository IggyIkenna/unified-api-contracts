"""Market-data-processing adapter domain contracts.

InstrumentInfo, InstrumentMetadata — typed dicts for instrument metadata
passed from the orchestration layer to candle adapters.

CandleOutput — dataclass returned by every candle adapter; wraps numpy
arrays and provides a to_dataframe() helper for Parquet writing.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass

import pandas as pd
import polars as pl


class InstrumentInfo(dict[str, object]):
    """Minimal instrument identifiers passed to candle adapters.

    Required keys: ``instrument_id`` (str), ``venue`` (str), ``symbol`` (str).

    Implemented as a dict subclass so existing code that passes plain dicts
    is fully compatible; add typed accessors for IDE support.

    Usage::

        info = InstrumentInfo(
            instrument_id="BINANCE:SPOT:BTCUSDT", venue="BINANCE", symbol="BTCUSDT"
        )
        adapter.process_to_candles(tick_data, "1m", instrument_info=info)
    """

    @property
    def instrument_id(self) -> str:
        return str(self["instrument_id"])

    @property
    def venue(self) -> str:
        return str(self["venue"])

    @property
    def symbol(self) -> str:
        return str(self["symbol"])


class InstrumentMetadata(dict[str, object]):
    """Extended instrument metadata for market-state detection.

    Optional keys consumed by MarketStateDetector:
    - ``trading_hours_open`` (str | None) — e.g. "09:30" (local exchange time)
    - ``trading_hours_close`` (str | None) — e.g. "16:00"
    - ``pre_market_open`` (str | None)
    - ``post_market_close`` (str | None)
    - ``holiday_calendar`` (list[str] | None) — ISO date strings of exchange holidays

    Implemented as a dict subclass for mutable key-value access (dict protocol).
    """

    @property
    def trading_hours_open(self) -> str | None:
        v = self.get("trading_hours_open")
        return str(v) if v is not None else None

    @property
    def trading_hours_close(self) -> str | None:
        v = self.get("trading_hours_close")
        return str(v) if v is not None else None

    @property
    def holiday_calendar(self) -> list[str] | None:
        v = self.get("holiday_calendar")
        if v is None:
            return None
        if isinstance(v, list):
            return [str(item) for item in v]  # pyright: ignore[reportUnknownArgumentType,reportUnknownVariableType]
        return None


@dataclass
class CandleOutput:
    """Structured output from a candle adapter.

    All array fields contain numpy ndarrays of shape ``(n_candles,)``.
    The three identifier fields are required; all OHLCV and derived metric
    fields are optional (adapters only populate the columns they produce).

    Calling ``to_dataframe()`` drops ``None`` fields and returns a pandas
    DataFrame ready for schema validation and Parquet writing.
    """

    # Required identifiers
    timestamp: object = None  # np.ndarray[np.int64]  — nanoseconds since epoch
    timestamp_out: object = None  # np.ndarray[np.int64]  — with synthetic delay
    venue: object = None  # np.ndarray[object]
    symbol: object = None  # np.ndarray[object]
    instrument_id: object = None  # np.ndarray[object]

    # Core OHLCV
    open: object = None
    high: object = None
    low: object = None
    close: object = None
    volume: object = None
    trade_count: object = None
    buy_volume: object = None
    sell_volume: object = None
    buy_trade_count: object = None
    sell_trade_count: object = None
    vwap: object = None

    # Trade latency
    delay_median_ms: object = None
    delay_mean_ms: object = None
    delay_min_ms: object = None
    delay_max_ms: object = None

    # Trade size distribution
    trade_size_p10: object = None
    trade_size_p50: object = None
    trade_size_p90: object = None
    trade_size_p99: object = None

    # Microstructure
    tick_direction_momentum: object = None
    whale_trade: object = None
    whale_trade_count: object = None
    whale_trade_volume: object = None
    volume_clock_mean_seconds: object = None
    volume_clock_std_seconds: object = None
    volume_imbalance_ratio: object = None

    # Book snapshot features
    spread_bps: object = None
    mid_price: object = None
    depth_bid: object = None
    depth_ask: object = None
    imbalance_ratio: object = None
    spread_bps_mean_15s: object = None
    depth_bid_mean_15s: object = None
    depth_ask_mean_15s: object = None
    imbalance_ratio_mean_15s: object = None
    bid_vol_0_mean_15s: object = None
    ask_vol_0_mean_15s: object = None
    tob_depth_ratio_mean_15s: object = None
    mid_price_mean_15s: object = None
    weighted_mid_price_5level: object = None
    effective_spread_5level: object = None

    # Book-microstructure intra-bar summary columns (book_snapshot_5 only).
    # SSOT: unified_api_contracts.internal.domain.market_data_processing.book_summary_spec
    # 25 columns produced from L5 book ticks via time-weighted aggregation over the
    # bar interval (right-edge convention: a sample at exactly t_close belongs to the
    # next bar). Populated by CefiBookSnapshotAdapter (and the DefiBookSnapshotAdapter
    # subclass); all other data_types omit them. PROCESSED_CANDLE_SCHEMA scopes via
    # applies_to={"book_snapshot_5"}.
    book_spread_bps_tw_mean: object = None
    book_spread_bps_tw_std: object = None
    book_spread_bps_max: object = None
    book_spread_bps_min: object = None
    book_spread_bps_close: object = None
    book_mid_open: object = None
    book_mid_high: object = None
    book_mid_low: object = None
    book_mid_close: object = None
    book_microprice_tw_mean: object = None
    book_microprice_tilt_bps_tw_mean: object = None
    book_imbalance_tw_mean: object = None
    book_imbalance_tw_std: object = None
    book_imbalance_close: object = None
    book_imbalance_sign_persist: object = None
    book_bid_qty_L1_tw_mean: object = None
    book_bid_qty_L2_tw_mean: object = None
    book_bid_qty_L3_tw_mean: object = None
    book_bid_qty_L4_tw_mean: object = None
    book_bid_qty_L5_tw_mean: object = None
    book_ask_qty_L1_tw_mean: object = None
    book_ask_qty_L2_tw_mean: object = None
    book_ask_qty_L3_tw_mean: object = None
    book_ask_qty_L4_tw_mean: object = None
    book_ask_qty_L5_tw_mean: object = None

    # Market state (TradFi / TBBO adapters)
    market_state: object = None
    is_halted: object = None
    is_auction: object = None

    # Derivative/options fields
    mark_price: object = None
    index_price: object = None
    funding_rate: object = None
    open_interest: object = None

    # derivative_ticker candle contract columns (``deriv_ohlcv_{tf}`` /
    # ``_DERIV_EXT`` in ``_candle_contracts.py``). These are the columns the
    # SchemaContract REQUIRES on a derivative_ticker candle, so the adapter
    # populates them directly rather than relying on a writer-side rename.
    #
    # NAMING vs SEMANTICS — READ BEFORE "FIXING" THIS.
    # The ``_mean`` suffix is a MISNOMER inherited from the original contract
    # sketch. The value is the LAST OBSERVATION IN THE BAR WINDOW, never an
    # arithmetic mean. derivative_ticker is a SNAPSHOT stream (funding / mark /
    # index are point-in-time states, not flows), so averaging them across a
    # window would fabricate a price that never existed on the wire. The
    # roll-up rule in ``aggregation_rules.COLUMN_AGG_RULES`` is therefore
    # ``"last"`` (last VALID observation), matching the bare ``mark_price`` /
    # ``funding_rate`` rules directly above. The contract name is kept because
    # the contract is the SSOT for the on-disk column name; only the semantics
    # documented here are authoritative for what the number MEANS.
    #
    # A bar with NO observation in its window carries NaN here (and NaN OHLC,
    # volume=0) — see the honest-absence note on ``CefiDerivativeAdapter``.
    funding_rate_mean: object = None
    mark_price_mean: object = None
    index_price_mean: object = None
    implied_volatility: object = None
    strike: object = None
    option_type: object = None
    expiration: object = None

    # Liquidations
    liquidation_count: object = None
    liquidation_volume: object = None
    liquidation_notional: object = None

    # DeFi candle schema columns.
    # chain: blockchain name (e.g. "ETHEREUM") — non-nullable in UAC contract.
    # swap_count: kept ONLY for the `state_ohlcv_*` (dex_pool_state) candle; on
    #   the `swaps_ohlcv_*` candle it was an exact duplicate of OHLCV-core
    #   `trade_count` and has been dropped from the swaps contract (DeFi #4 /
    #   C0-RD6 — _DEX_EXT split).
    # volume_quote_usd: an exact duplicate of OHLCV-core `volume`, dropped from
    #   the swaps contract. The MDPS swap_adapter still emits it as a kwarg; once
    #   that emission is removed (paired market-data-processing-service edit) this
    #   field can be deleted here too.
    chain: object = None
    swap_count: object = None
    volume_quote_usd: object = None

    # DeFi / swap fields
    amount_in: object = None
    amount_out: object = None
    price_impact: object = None
    fee: object = None
    protocol: object = None

    # Rate indices
    rate: object = None
    rate_type: object = None

    # Sports arbitrage / odds fields
    home_odds: object = None
    away_odds: object = None
    draw_odds: object = None
    arb_margin_pct: object = None
    best_bookmaker: object = None

    # DeFi lending / flash loan fields
    liquidity_rate: object = None
    borrow_rate: object = None
    utilization_ratio: object = None
    liquidity_index: object = None
    borrow_index: object = None
    available_liquidity: object = None
    max_flash_loan: object = None
    flash_loan_fee: object = None
    total_supply: object = None
    total_borrow: object = None

    # Data quality / staleness (seconds since last real observation)
    # Used by vol surface fitters to weight/exclude stale LOCF data.
    # 0 = fresh observation in this interval. >0 = LOCF-filled, stale by N seconds.
    staleness_seconds: object = None

    def to_dataframe(self) -> pd.DataFrame:
        """Convert non-None array fields to a pandas DataFrame.

        Returns an empty DataFrame if all fields are None.
        """
        data: dict[str, object] = {}
        for f in dataclasses.fields(self):
            v: object = getattr(self, f.name)  # pyright: ignore[reportAny]
            if v is not None:
                data[f.name] = v
        if not data:
            return pd.DataFrame()
        return pd.DataFrame(data)

    def to_polars(self) -> pl.DataFrame:
        """Convert non-None array fields to a polars DataFrame.

        Pure-Polars sibling of to_dataframe() (MDPS pure-Polars migration
        Stage 3 — plans/active/mdps_pure_polars_migration_2026_05_28.md).
        Lets MDPS skip the numpy->pandas->parquet roundtrip on the output
        side; polars writes the parquet directly from arrow arrays.
        Returns an empty DataFrame if all fields are None.
        """
        data: dict[str, object] = {}
        for f in dataclasses.fields(self):
            v: object = getattr(self, f.name)  # pyright: ignore[reportAny]
            if v is not None:
                data[f.name] = v
        if not data:
            return pl.DataFrame()
        return pl.DataFrame(data)


__all__ = ["CandleOutput", "InstrumentInfo", "InstrumentMetadata"]
