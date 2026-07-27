"""Features SchemaContracts — Phase 5c.1.

Plan: data_pipeline_completion_2026_04_18 §Phase 5c. One
SchemaContract per ``(category, instrument_type, feature_group)`` for the
eight feature services' GCS parquet outputs. The ``feature_group`` is
recorded under ``data_type`` in the three-tuple registry key so the existing
``CONTRACT_REGISTRY`` lookup works without schema changes.

Core columns enforced on every feature parquet (all feature services share
these — the per-group feature columns themselves are declared in each
service's ``feature_definitions.yaml`` and are NOT duplicated in the
SchemaContract; doing so would couple UAC to service-internal calculator
renames. The contract enforces the shard shape; service QG enforces the
per-feature columns).

    instrument_id      — canonical id (VENUE:INSTRUMENT_TYPE:SYMBOL)
    venue              — shard dim
    chain              — shard dim (DeFi / Prediction only)
    ts_event           — UTC event timestamp
    ts_event_out       — UTC time feature became available (+synthetic delay)
    feature_group      — shard column
    timeframe          — shard column (1m / 5m / 15m / 1h / 4h / 1d)

Enumeration source (as of 2026-04-18):

    features-delta-one         ``{BUILDER_REGISTRY}``: 30+ groups
                               covering technical_indicators, moving_averages,
                               oscillators, volatility_realized, momentum,
                               volume_analysis, vwap, candlestick_patterns,
                               market_structure, returns, round_numbers,
                               streaks, targets, swing_outcome_targets,
                               microstructure, funding_oi, liquidations,
                               futures_basis, volume_flow, temporal,
                               economic_events, supply_demand_zones,
                               fibonacci, level_confluence,
                               market_structure_sequence, sr_memory,
                               signal_confirmation, statistical_anomaly,
                               order_flow_inference, return_kurtosis,
                               polynomial_trendlines, risk_reward,
                               wedge_quality, confluence
    features-volatility        options_iv, futures_term_structure,
                               gamma_exposure, variance_risk_premium,
                               second_order_greeks, tradfi_vol_surface,
                               vol_surface_term_structure
    features-onchain           lending_rates, utilization,
                               risk_params, lst_yields, macro_sentiment,
                               rewards, flash_loan_availability,
                               rate_impact
    features-sports            team_form, team_goals, team_xg, team_derived,
                               h2h, league, advanced_stats, venue_context,
                               weather, season_context, halftime,
                               goal_timing, referee, player_lineup,
                               multisource_xg, poisson_xg, elo, manager,
                               injury_impact, travel, formation,
                               european_fatigue, transfer_window,
                               squad_value, xg_decomposition,
                               relative_context, bench_sub,
                               replacement_model, bucketed_features,
                               meta_features
    features-calendar          temporal, economic_events, economic_calendar,
                               corporate_actions, earnings_results,
                               yield_curve, sentiment, economic_results
    features-multi-timeframe   tf_momentum_alignment, tf_structure_context,
                               tf_vol_compression, tf_session_context,
                               intraday_regime, micro_regime,
                               wedge_confluence, tf_risk_reward,
                               tf_confluence_signals
    features-cross-instrument  regime_detection, cross_venue_spreads,
                               realized_implied_vol, cross_asset_correlation,
                               cross_instrument_dynamics, cme_gap,
                               book_depth_bands, liquidity_walls,
                               liquidation_clusters,
                               liquidation_band_prediction, flow_interaction,
                               dxy_momentum, cointegration, composite_sr,
                               polymarket_crowd_sentiment,
                               polymarket_trade_flow,
                               polymarket_whale_activity,
                               polymarket_market_microstructure,
                               polymarket_cross_market,
                               polymarket_temporal_patterns
    features-commodity         price_momentum, storage_alpha, cot_positioning,
                               rig_count, weather_delta

Canonical category / instrument_type pairs per service:

    features-delta-one        → applies to {cefi, tradfi} x {perpetual,
                                spot_pair, future, equity, options_chain,
                                futures_chain, index}. Contract registered
                                under ``cefi/perpetual`` (primary) + per-pair
                                duplicates.
    features-volatility       → {cefi/options_chain, cefi/futures_chain,
                                tradfi/options_chain}
    features-onchain          → defi x {a_token, lending, lst, pool,
                                spot_asset, staking}
    features-sports           → sports/odds
    features-calendar         → cross-category; canonical home = tradfi/index
                                (macro events live there); also registered
                                for cefi/perpetual for crypto-native
                                calendar features.
    features-multi-timeframe  → {cefi/perpetual, cefi/spot_pair,
                                tradfi/future, tradfi/equity}
    features-cross-instrument → {cefi/perpetual, cefi/spot_pair,
                                tradfi/future, tradfi/equity, defi/pool,
                                prediction/prediction_market}
    features-commodity        → tradfi/future (commodity futures)

Do NOT import this module directly; use
``unified_api_contracts.internal.schemas.contracts``.
"""

from __future__ import annotations

from typing import cast

from unified_api_contracts.internal.schemas.contracts import (
    CHAIN_COL,
    CONTRACT_REGISTRY,
    INSTRUMENT_ID_COL,
    TS_EVENT_COL,
    VENUE_COL,
    AssetGroupLiteral,
    ColumnSpec,
    SchemaContract,
)

# ---------------------------------------------------------------------------
# Shared feature-output base columns
# ---------------------------------------------------------------------------

_TS_EVENT_OUT = ColumnSpec(
    name="ts_event_out",
    dtype="datetime64[ns, UTC]",
    nullable=False,
    description="UTC time the feature became available (ts_event + synthetic delay).",
)
_FEATURE_GROUP_COL = ColumnSpec(
    name="feature_group",
    dtype="string",
    nullable=False,
    description="Feature group name (e.g. technical_indicators, options_iv).",
)
_FEATURE_TIMEFRAME_COL = ColumnSpec(
    name="timeframe",
    dtype="string",
    nullable=False,
    description="Timeframe (15s / 1m / 5m / 15m / 1h / 4h / 1d).",
)


def _core_columns(*, include_chain: bool) -> list[ColumnSpec]:
    cols: list[ColumnSpec] = [INSTRUMENT_ID_COL, VENUE_COL]
    if include_chain:
        cols.append(CHAIN_COL)
    cols.extend([TS_EVENT_COL, _TS_EVENT_OUT, _FEATURE_GROUP_COL, _FEATURE_TIMEFRAME_COL])
    return cols


def _register(
    category: str,
    instrument_type: str,
    feature_group: str,
    *,
    include_chain: bool = False,
    symbol_column: str = "symbol",
) -> SchemaContract:
    contract = SchemaContract(
        asset_group=cast(AssetGroupLiteral, category),
        instrument_type=instrument_type,
        data_type=feature_group,
        columns=_core_columns(include_chain=include_chain),
        symbol_column=symbol_column,
        required_row_count_min=1,
    )
    CONTRACT_REGISTRY[(category, instrument_type, feature_group)] = contract
    return contract


# ---------------------------------------------------------------------------
# Feature-group enumerations per service
# ---------------------------------------------------------------------------

DELTA_ONE_FEATURE_GROUPS: tuple[str, ...] = (
    "technical_indicators",
    "moving_averages",
    "oscillators",
    "volatility_realized",
    "momentum",
    "volume_analysis",
    "vwap",
    "candlestick_patterns",
    "market_structure",
    "returns",
    "round_numbers",
    "streaks",
    "targets",
    "swing_outcome_targets",
    "microstructure",
    "funding_oi",
    "liquidations",
    "futures_basis",
    "volume_flow",
    "temporal",
    "economic_events",
    "supply_demand_zones",
    "fibonacci",
    "level_confluence",
    "market_structure_sequence",
    "sr_memory",
    "signal_confirmation",
    "statistical_anomaly",
    "order_flow_inference",
    "return_kurtosis",
    "polynomial_trendlines",
    "risk_reward",
    "wedge_quality",
    "confluence",
)

VOLATILITY_FEATURE_GROUPS: tuple[str, ...] = (
    "options_iv",
    "futures_term_structure",
    "gamma_exposure",
    "variance_risk_premium",
    "second_order_greeks",
    "tradfi_vol_surface",
    "vol_surface_term_structure",
)

ONCHAIN_FEATURE_GROUPS: tuple[str, ...] = (
    "lending_rates",
    "utilization",
    "risk_params",
    "rate_impact",
    "lst_yields",
    "macro_sentiment",
    "rewards",
    "flash_loan_availability",
)

SPORTS_FEATURE_GROUPS: tuple[str, ...] = (
    "team_form",
    "team_goals",
    "team_xg",
    "team_derived",
    "h2h",
    "league",
    "advanced_stats",
    "venue_context",
    "weather",
    "season_context",
    "halftime",
    "goal_timing",
    "referee",
    "player_lineup",
    "multisource_xg",
    "poisson_xg",
    "elo",
    "manager",
    "injury_impact",
    "travel",
    "formation",
    "european_fatigue",
    "transfer_window",
    "squad_value",
    "xg_decomposition",
    "relative_context",
    "bench_sub",
    "replacement_model",
    "bucketed_features",
    "meta_features",
)

CALENDAR_FEATURE_GROUPS: tuple[str, ...] = (
    "temporal",
    "economic_events",
    "economic_calendar",
    "corporate_actions",
    "earnings_results",
    "yield_curve",
    "sentiment",
    "economic_results",
)

MULTI_TIMEFRAME_FEATURE_GROUPS: tuple[str, ...] = (
    "tf_momentum_alignment",
    "tf_structure_context",
    "tf_vol_compression",
    "tf_session_context",
    "intraday_regime",
    "micro_regime",
    "wedge_confluence",
    "tf_risk_reward",
    "tf_confluence_signals",
)

CROSS_INSTRUMENT_FEATURE_GROUPS: tuple[str, ...] = (
    "regime_detection",
    "cross_venue_spreads",
    "realized_implied_vol",
    "cross_asset_correlation",
    "cross_instrument_dynamics",
    "cme_gap",
    "book_depth_bands",
    "liquidity_walls",
    "liquidation_clusters",
    "liquidation_band_prediction",
    "flow_interaction",
    "dxy_momentum",
    "cointegration",
    "composite_sr",
    "paired_price_dispersion",
    "polymarket_crowd_sentiment",
    "polymarket_trade_flow",
    "polymarket_whale_activity",
    "polymarket_market_microstructure",
    "polymarket_cross_market",
    "polymarket_temporal_patterns",
)
# `paired_price_dispersion` (Phase 9) has a DIFFERENT shard atom than the
# rest of the cross-instrument family. The other groups are
# (asset_group, instrument_type, instrument_id, day) — per-instrument.
# `paired_price_dispersion` is
# (asset_group, left_venue, left_root, right_venue, right_root, day) —
# per-pair, computed from two simultaneously-aligned legs. The standard
# `_register(...)` per-instrument loop is intentionally skipped for this
# group; the calculator consumes pre-aligned `(left_close, right_close,
# expiry, days_to_expiry)` columns and emits `spread_bps`,
# `annualised_apy_bps`. The leg-resolver + raw_tick_data fetch lives
# upstream of the calculator (catalog spec param parser → MTDS read).
_PAIRED_PRICE_DISPERSION_REQUIRED_COLUMNS: tuple[str, ...] = (
    "timestamp",
    "left_venue",
    "left_root",
    "right_venue",
    "right_root",
    "left_close",
    "right_close",
    "expiry",
    "days_to_expiry",
)

COMMODITY_FEATURE_GROUPS: tuple[str, ...] = (
    "price_momentum",
    "storage_alpha",
    "cot_positioning",
    "rig_count",
    "weather_delta",
)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

# Delta-one runs against both CeFi and TradFi directional instruments.
_DELTA_ONE_TARGETS: tuple[tuple[str, str, str], ...] = (
    ("cefi", "perpetual", "symbol"),
    ("cefi", "spot_pair", "symbol"),
    ("tradfi", "future", "symbol"),
    ("tradfi", "equity", "symbol"),
    ("tradfi", "index", "symbol"),
)

for _cat, _itype, _symcol in _DELTA_ONE_TARGETS:
    for _fg in DELTA_ONE_FEATURE_GROUPS:
        _register(_cat, _itype, _fg, symbol_column=_symcol)

# Volatility targets: all options / futures chains (derive IV + term-structure).
_VOL_TARGETS: tuple[tuple[str, str, str], ...] = (
    ("cefi", "options_chain", "underlying"),
    ("cefi", "futures_chain", "underlying"),
    ("tradfi", "options_chain", "underlying"),
)

for _cat, _itype, _symcol in _VOL_TARGETS:
    for _fg in VOLATILITY_FEATURE_GROUPS:
        _register(_cat, _itype, _fg, symbol_column=_symcol)

# Onchain: DeFi only — one contract per feature-group x instrument_type combo
# that the feature group actually consumes.
_ONCHAIN_AAVE_TARGETS = ("a_token", "lending")
_ONCHAIN_LST_TARGETS = ("lst",)
_ONCHAIN_SPOT_TARGETS = ("spot_asset",)
_ONCHAIN_STAKING_TARGETS = ("staking",)

_ONCHAIN_ROUTE: dict[str, tuple[str, ...]] = {
    # Aave-specific groups
    "lending_rates": _ONCHAIN_AAVE_TARGETS,
    "utilization": _ONCHAIN_AAVE_TARGETS,
    "risk_params": _ONCHAIN_AAVE_TARGETS,
    "rate_impact": _ONCHAIN_AAVE_TARGETS,
    # Morpho / flash-loan availability also scoped to lending
    "flash_loan_availability": _ONCHAIN_AAVE_TARGETS,
    "rewards": _ONCHAIN_STAKING_TARGETS,
    # LST staking yields
    "lst_yields": _ONCHAIN_LST_TARGETS,
    # Macro / sentiment cross-asset — scoped at spot_asset + pool.
    "macro_sentiment": _ONCHAIN_SPOT_TARGETS,
}

for _fg, _itypes in _ONCHAIN_ROUTE.items():
    for _itype in _itypes:
        _sym = "token" if _itype in {"a_token", "lending"} else "pool_id" if _itype == "pool" else "symbol"
        _register("defi", _itype, _fg, include_chain=True, symbol_column=_sym)

# Sports — all groups key on fixture_id.
for _fg in SPORTS_FEATURE_GROUPS:
    _register("sports", "odds", _fg, symbol_column="fixture_id")

# Calendar — cross-asset applicability. Primary shard = tradfi/index (macro
# events live there); also cefi/perpetual for crypto-native calendar feats.
_CALENDAR_TARGETS: tuple[tuple[str, str, str], ...] = (
    ("tradfi", "index", "symbol"),
    ("tradfi", "future", "symbol"),
    ("tradfi", "equity", "symbol"),
    ("cefi", "perpetual", "symbol"),
    ("cefi", "spot_pair", "symbol"),
)

for _cat, _itype, _symcol in _CALENDAR_TARGETS:
    for _fg in CALENDAR_FEATURE_GROUPS:
        _register(_cat, _itype, _fg, symbol_column=_symcol)

# Multi-timeframe — directional CeFi + TradFi instruments.
_MTF_TARGETS: tuple[tuple[str, str, str], ...] = (
    ("cefi", "perpetual", "symbol"),
    ("cefi", "spot_pair", "symbol"),
    ("tradfi", "future", "symbol"),
    ("tradfi", "equity", "symbol"),
)

for _cat, _itype, _symcol in _MTF_TARGETS:
    for _fg in MULTI_TIMEFRAME_FEATURE_GROUPS:
        _register(_cat, _itype, _fg, symbol_column=_symcol)

# Cross-instrument — broadest scope including DeFi pool and Polymarket for
# the polymarket_*/cross-market groups.
_XINST_DIRECTIONAL_TARGETS: tuple[tuple[str, str, str], ...] = (
    ("cefi", "perpetual", "symbol"),
    ("cefi", "spot_pair", "symbol"),
    ("tradfi", "future", "symbol"),
    ("tradfi", "equity", "symbol"),
)
_XINST_DEFI_TARGETS: tuple[tuple[str, str, str], ...] = (("defi", "pool", "pool_id"),)
_XINST_PRED_TARGETS: tuple[tuple[str, str, str], ...] = (("prediction", "prediction_market", "condition_id"),)

for _cat, _itype, _symcol in _XINST_DIRECTIONAL_TARGETS:
    for _fg in CROSS_INSTRUMENT_FEATURE_GROUPS:
        # Polymarket-* feature groups aggregate Polymarket trades into
        # directional-instrument-level features — register them here too.
        # `paired_price_dispersion` is per-pair not per-instrument — skip
        # the per-instrument registration; its shard atom is registered
        # separately downstream (deployment-api `data_status_axis_matrix`
        # SSOT picks up the per-pair shape).
        if _fg == "paired_price_dispersion":
            continue
        _register(_cat, _itype, _fg, symbol_column=_symcol)

for _cat, _itype, _symcol in _XINST_DEFI_TARGETS:
    # Only cross-asset / regime-level groups apply to DeFi pools; skip
    # Polymarket-specific rows (those only land on directional feeds).
    for _fg in (
        "regime_detection",
        "cross_venue_spreads",
        "cross_asset_correlation",
        "cross_instrument_dynamics",
        "book_depth_bands",
        "liquidity_walls",
        "flow_interaction",
        "cointegration",
    ):
        _register(_cat, _itype, _fg, include_chain=True, symbol_column=_symcol)

for _cat, _itype, _symcol in _XINST_PRED_TARGETS:
    for _fg in (
        "polymarket_crowd_sentiment",
        "polymarket_trade_flow",
        "polymarket_whale_activity",
        "polymarket_market_microstructure",
        "polymarket_cross_market",
        "polymarket_temporal_patterns",
    ):
        _register(_cat, _itype, _fg, include_chain=True, symbol_column=_symcol)

# Commodity — tradfi/future (NG, CL, etc).
for _fg in COMMODITY_FEATURE_GROUPS:
    _register("tradfi", "future", _fg, symbol_column="symbol")


__all__ = [
    "CALENDAR_FEATURE_GROUPS",
    "COMMODITY_FEATURE_GROUPS",
    "CROSS_INSTRUMENT_FEATURE_GROUPS",
    "DELTA_ONE_FEATURE_GROUPS",
    "MULTI_TIMEFRAME_FEATURE_GROUPS",
    "ONCHAIN_FEATURE_GROUPS",
    "SPORTS_FEATURE_GROUPS",
    "VOLATILITY_FEATURE_GROUPS",
    "_PAIRED_PRICE_DISPERSION_REQUIRED_COLUMNS",
]
