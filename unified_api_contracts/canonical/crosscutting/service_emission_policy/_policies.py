"""Service emission policy constants — policy table and state mapping."""

from __future__ import annotations

from typing import Final

from unified_api_contracts.canonical.crosscutting.service_emission_state import (
    ServiceEmissionStateEnum,
)

from ._enums import EmissionLifecycleEvent, ServiceEmissionPolicy

SERVICE_OUTPUT_POLICIES: Final[dict[tuple[str, str], ServiceEmissionPolicy]] = {
    # MDPS — candle outputs at multiple cadences. Current bars are real-time;
    # partial = wrong. Historical re-emission tolerates inner gaps via
    # completeness_fraction.
    ("market-data-processing-service", "ohlcv_1m:current"): ServiceEmissionPolicy.STRICT_FAIL,
    ("market-data-processing-service", "ohlcv_1m:historical"): ServiceEmissionPolicy.PARTIAL_OK,
    ("market-data-processing-service", "ohlcv_1h:current"): ServiceEmissionPolicy.STRICT_FAIL,
    ("market-data-processing-service", "ohlcv_1h:historical"): ServiceEmissionPolicy.PARTIAL_OK,
    ("market-data-processing-service", "ohlcv_24h"): ServiceEmissionPolicy.PARTIAL_OK,
    ("market-data-processing-service", "book_snapshot_5"): ServiceEmissionPolicy.STRICT_FAIL,
    # features-volatility — operator-flagged 24h-high-low example as PARTIAL_OK; rolling
    # vols are NaN_FILL because the ML consumer NaN-fills natively.
    ("features-service", "high_low_24h"): ServiceEmissionPolicy.PARTIAL_OK,
    ("features-service", "vol_30d"): ServiceEmissionPolicy.NAN_FILL,
    ("features-service", "realised_vol_intraday"): ServiceEmissionPolicy.PARTIAL_OK,
    # features-cross-instrument — paired-spec compute is leak-risk-sensitive: both legs
    # MUST be current. Partial = lookahead-bias trap.
    ("features-service", "paired_spec"): ServiceEmissionPolicy.STRICT_FAIL,
    ("features-service", "pairwise_correlation"): ServiceEmissionPolicy.NAN_FILL,
    # ml-training — training a model on incomplete data is the worst-case silent corruption.
    # block_critical forces operator review.
    ("ml-service", "model_version"): ServiceEmissionPolicy.BLOCK_CRITICAL,
    # ml-inference — signals off stale features pollute strategy decisions.
    ("ml-service", "per_strategy_signal"): ServiceEmissionPolicy.STRICT_FAIL,
    # strategy — same as ml-inference; partial-truth signals fire wrong orders.
    ("strategy-service", "per_archetype_signal"): ServiceEmissionPolicy.STRICT_FAIL,
    # execution — orders + fill confirmations are no-partial-truth zones.
    ("execution-service", "order_intent"): ServiceEmissionPolicy.STRICT_FAIL,
    ("execution-service", "fill_confirmation"): ServiceEmissionPolicy.BLOCK_CRITICAL,
    # strategy-service/position —
    # portfolio_state must be authoritative; partial = wrong.
    ("strategy-service", "portfolio_state"): ServiceEmissionPolicy.BLOCK_CRITICAL,
    # position-balance-monitor-service — same portfolio_state contract as strategy-service.
    ("position-balance-monitor-service", "portfolio_state"): ServiceEmissionPolicy.BLOCK_CRITICAL,
    # strategy-service/risk — same constraint.
    ("strategy-service", "risk_state"): ServiceEmissionPolicy.BLOCK_CRITICAL,
    # instruments-service — catalog snapshot is best-effort union of multiple source
    # feeds; partial publish is normal. Per-source partial coverage handled at
    # the manifest layer (per-row capture_status), not at the catalog-publish layer.
    ("instruments-service", "catalog_snapshot"): ServiceEmissionPolicy.PARTIAL_OK,
    # -----------------------------------------------------------------------
    # Phase 6.5 (writegate slice c) seed extension — features-* services.
    # Source: 4-way sub-agent audit 2026-05-11 across features-service
    # sub-packages (onchain/sports/cross_instrument/delta_one/multi_timeframe).
    # Seed-only: per-service wiring deferred to Phase 6.5 consumer work-items.
    # -----------------------------------------------------------------------
    #
    # features-onchain-service — 11 entries.
    # Per-feature_group output of _dispatch_feature_group (11 distinct groups).
    # Real-time current-state + trading-decision inputs → STRICT_FAIL.
    # Authoritative risk/position truth → BLOCK_CRITICAL.
    # Rolling-window aggregates → PARTIAL_OK.
    # lending_rates: PARTIAL_OK — lending protocol data is inherently partial;
    # different markets populate different APY fields. write_gate nan_threshold=0.95
    # enforces quality; strategy tracer does its own None-guard on missing values.
    ("features-service", "lending_rates"): ServiceEmissionPolicy.PARTIAL_OK,
    # lst_yields / lst_native_rates: PARTIAL_OK — per-token yield data is
    # structurally partial (different LSTs populate different yield fields, same
    # shape as lending_rates). _drop_unmapped_tokens() already filters tokens not
    # in the UAC registry; remaining NaN cells are genuine "data not available for
    # this token today" gaps. STRICT_FAIL's all-or-nothing semantics would suppress
    # ALL tokens for a day when even one token is missing one field — too aggressive
    # now that unmapped-token filtering exists as a safety net. Downstream consumer
    # (strategy-service CARRY_* archetypes) does its own None-guard on missing values.
    # Ruling: lst_yields_writegate_permanently_blocked_2026_07_28.md § todo 4 (P3).
    ("features-service", "lst_yields"): ServiceEmissionPolicy.PARTIAL_OK,
    ("features-service", "lst_native_rates"): ServiceEmissionPolicy.PARTIAL_OK,
    ("features-service", "onchain_perps"): ServiceEmissionPolicy.STRICT_FAIL,
    ("features-service", "utilization"): ServiceEmissionPolicy.STRICT_FAIL,
    ("features-service", "flash_loan_availability"): ServiceEmissionPolicy.STRICT_FAIL,
    ("features-service", "rate_impact"): ServiceEmissionPolicy.STRICT_FAIL,
    ("features-service", "risk_params"): ServiceEmissionPolicy.BLOCK_CRITICAL,
    ("features-service", "health_factor"): ServiceEmissionPolicy.BLOCK_CRITICAL,
    ("features-service", "macro_sentiment"): ServiceEmissionPolicy.PARTIAL_OK,
    ("features-service", "rewards"): ServiceEmissionPolicy.PARTIAL_OK,
    ("features-service", "liquidation_events"): ServiceEmissionPolicy.PARTIAL_OK,
    #
    # features-sports-service — 8 entries.
    # Three canonical data_types (FIXTURE_FEATURES / ODDS_FEATURES / DERIVED_FEATURES)
    # split current/historical per slice convention = 6; plus live PubSub
    # subset = 7; plus the odds_targets ML TARGET table (historical-only, no
    # live slice — see odds_targets_exporter.py +
    # sports_clv_target_pit_gated_out_of_odds_features_export_2026_07_26.md
    # [DATA] P2) = 8. Tree-based ML consumer → NaN-fill native (1-10% tolerance).
    # In-play HT-odds = STRICT_FAIL (live pricing input).
    ("features-sports-service", "fixture_features:current"): ServiceEmissionPolicy.NAN_FILL,
    ("features-sports-service", "fixture_features:historical"): ServiceEmissionPolicy.NAN_FILL,
    ("features-sports-service", "odds_features:current"): ServiceEmissionPolicy.STRICT_FAIL,
    ("features-sports-service", "odds_features:historical"): ServiceEmissionPolicy.NAN_FILL,
    ("features-sports-service", "derived_features:current"): ServiceEmissionPolicy.NAN_FILL,
    ("features-sports-service", "derived_features:historical"): ServiceEmissionPolicy.NAN_FILL,
    ("features-sports-service", "live_feature_subset"): ServiceEmissionPolicy.STRICT_FAIL,
    # odds_targets is structurally sparse BY DESIGN (CLV requires both a T-24h
    # and a T-0 leg for the same fixture) — NAN_FILL, same rationale as
    # odds_features:historical, not STRICT_FAIL.
    ("features-sports-service", "odds_targets:historical"): ServiceEmissionPolicy.NAN_FILL,
    #
    # features-cross-instrument-service — 21 entries.
    # Source: CALCULATOR_REGISTRY in features_service/cross_instrument/engine/orchestrator.py
    # (21 distinct feature_groups). ML-tree consumer features → NAN_FILL.
    # Cross-venue / paired-leg / orderbook-snapshot signals → STRICT_FAIL
    # (partial leg = lookahead-bias trap, paired_spec precedent).
    # Rolling-window aggregates → PARTIAL_OK.
    ("features-service", "regime_detection"): ServiceEmissionPolicy.NAN_FILL,
    ("features-service", "cross_asset_correlation"): ServiceEmissionPolicy.NAN_FILL,
    ("features-service", "cross_instrument_dynamics"): ServiceEmissionPolicy.NAN_FILL,
    ("features-service", "realized_implied_vol"): ServiceEmissionPolicy.NAN_FILL,
    ("features-service", "cointegration"): ServiceEmissionPolicy.NAN_FILL,
    ("features-service", "cme_gap"): ServiceEmissionPolicy.PARTIAL_OK,
    ("features-service", "cross_venue_spreads"): ServiceEmissionPolicy.STRICT_FAIL,
    ("features-service", "book_depth_bands"): ServiceEmissionPolicy.STRICT_FAIL,
    ("features-service", "liquidity_walls"): ServiceEmissionPolicy.STRICT_FAIL,
    ("features-service", "liquidation_clusters"): ServiceEmissionPolicy.STRICT_FAIL,
    ("features-service", "liquidation_band_prediction"): ServiceEmissionPolicy.NAN_FILL,
    ("features-service", "flow_interaction"): ServiceEmissionPolicy.STRICT_FAIL,
    ("features-service", "composite_sr"): ServiceEmissionPolicy.STRICT_FAIL,
    ("features-service", "dxy_momentum"): ServiceEmissionPolicy.NAN_FILL,
    ("features-service", "paired_price_dispersion"): ServiceEmissionPolicy.STRICT_FAIL,
    ("features-service", "polymarket_crowd_sentiment"): ServiceEmissionPolicy.NAN_FILL,
    ("features-service", "polymarket_trade_flow"): ServiceEmissionPolicy.NAN_FILL,
    ("features-service", "polymarket_whale_activity"): ServiceEmissionPolicy.NAN_FILL,
    ("features-service", "polymarket_market_microstructure"): ServiceEmissionPolicy.NAN_FILL,
    ("features-service", "polymarket_cross_market"): ServiceEmissionPolicy.STRICT_FAIL,
    ("features-service", "polymarket_temporal_patterns"): ServiceEmissionPolicy.NAN_FILL,
    #
    # features-delta-one-service — 21 entries (all FEATURE_GROUPS from parser.py).
    # NOTE: legacy orphaned entries under ("features-service", ...) below are superseded
    # by these correct-key entries. Default for ML-consumer feature_groups → NAN_FILL
    # (LightGBM NaN-fill native, operator-msg-10 vol_30d anchor). STRICT_FAIL for
    # cross-venue/cross-leg pairings + execution-sensitive signals + ML training targets.
    # (Phase 6.5 P2 fix 2026-05-14: added correct "features-delta-one-service" key +
    # 12 ohlcv-derived NAN_FILL groups that were previously unregistered → STRICT_FAIL
    # fallback; key mismatch for prior 9 entries also fixed here.)
    ("features-delta-one-service", "technical_indicators"): ServiceEmissionPolicy.NAN_FILL,
    ("features-delta-one-service", "moving_averages"): ServiceEmissionPolicy.NAN_FILL,
    ("features-delta-one-service", "oscillators"): ServiceEmissionPolicy.NAN_FILL,
    ("features-delta-one-service", "volatility_realized"): ServiceEmissionPolicy.NAN_FILL,
    ("features-delta-one-service", "momentum"): ServiceEmissionPolicy.NAN_FILL,
    ("features-delta-one-service", "volume_analysis"): ServiceEmissionPolicy.NAN_FILL,
    ("features-delta-one-service", "vwap"): ServiceEmissionPolicy.NAN_FILL,
    ("features-delta-one-service", "candlestick_patterns"): ServiceEmissionPolicy.NAN_FILL,
    ("features-delta-one-service", "market_structure"): ServiceEmissionPolicy.NAN_FILL,
    ("features-delta-one-service", "returns"): ServiceEmissionPolicy.NAN_FILL,
    ("features-delta-one-service", "round_numbers"): ServiceEmissionPolicy.NAN_FILL,
    ("features-delta-one-service", "streaks"): ServiceEmissionPolicy.NAN_FILL,
    ("features-delta-one-service", "temporal"): ServiceEmissionPolicy.NAN_FILL,
    ("features-delta-one-service", "microstructure"): ServiceEmissionPolicy.STRICT_FAIL,
    ("features-delta-one-service", "funding_oi"): ServiceEmissionPolicy.STRICT_FAIL,
    ("features-delta-one-service", "futures_basis"): ServiceEmissionPolicy.STRICT_FAIL,
    ("features-delta-one-service", "volume_flow"): ServiceEmissionPolicy.PARTIAL_OK,
    ("features-delta-one-service", "liquidations"): ServiceEmissionPolicy.PARTIAL_OK,
    ("features-delta-one-service", "economic_events"): ServiceEmissionPolicy.PARTIAL_OK,
    ("features-delta-one-service", "targets"): ServiceEmissionPolicy.STRICT_FAIL,
    ("features-delta-one-service", "swing_outcome_targets"): ServiceEmissionPolicy.STRICT_FAIL,
    #
    # features-onchain-service — 11 entries (Phase 6.5 P2 fix 2026-05-15: added correct
    # "features-onchain-service" key entries; prior seeds used "features-service" key which
    # did not match handler _SERVICE_NAME → all groups fell back to STRICT_FAIL including
    # BLOCK_CRITICAL groups risk_params + health_factor that require P0 alert).
    # lending_rates: PARTIAL_OK (aligned with features-service entry update in a84e012).
    ("features-onchain-service", "lending_rates"): ServiceEmissionPolicy.PARTIAL_OK,
    ("features-onchain-service", "lst_yields"): ServiceEmissionPolicy.PARTIAL_OK,
    ("features-onchain-service", "lst_native_rates"): ServiceEmissionPolicy.PARTIAL_OK,
    ("features-onchain-service", "onchain_perps"): ServiceEmissionPolicy.STRICT_FAIL,
    ("features-onchain-service", "utilization"): ServiceEmissionPolicy.STRICT_FAIL,
    ("features-onchain-service", "flash_loan_availability"): ServiceEmissionPolicy.STRICT_FAIL,
    ("features-onchain-service", "rate_impact"): ServiceEmissionPolicy.STRICT_FAIL,
    ("features-onchain-service", "risk_params"): ServiceEmissionPolicy.BLOCK_CRITICAL,
    ("features-onchain-service", "health_factor"): ServiceEmissionPolicy.BLOCK_CRITICAL,
    ("features-onchain-service", "macro_sentiment"): ServiceEmissionPolicy.PARTIAL_OK,
    ("features-onchain-service", "rewards"): ServiceEmissionPolicy.PARTIAL_OK,
    ("features-onchain-service", "liquidation_events"): ServiceEmissionPolicy.PARTIAL_OK,
    #
    # features-cross-instrument-service — 21 entries (Phase 6.5 P2 fix 2026-05-15: added
    # correct "features-cross-instrument-service" key; prior "features-service" key did not
    # match handler _SERVICE_NAME → all groups fell back to STRICT_FAIL suppressing valid
    # NAN_FILL / PARTIAL_OK group writes).
    ("features-cross-instrument-service", "regime_detection"): ServiceEmissionPolicy.NAN_FILL,
    ("features-cross-instrument-service", "cross_asset_correlation"): ServiceEmissionPolicy.NAN_FILL,
    ("features-cross-instrument-service", "cross_instrument_dynamics"): ServiceEmissionPolicy.NAN_FILL,
    ("features-cross-instrument-service", "realized_implied_vol"): ServiceEmissionPolicy.NAN_FILL,
    ("features-cross-instrument-service", "cointegration"): ServiceEmissionPolicy.NAN_FILL,
    ("features-cross-instrument-service", "cme_gap"): ServiceEmissionPolicy.PARTIAL_OK,
    ("features-cross-instrument-service", "cross_venue_spreads"): ServiceEmissionPolicy.STRICT_FAIL,
    ("features-cross-instrument-service", "book_depth_bands"): ServiceEmissionPolicy.STRICT_FAIL,
    ("features-cross-instrument-service", "liquidity_walls"): ServiceEmissionPolicy.STRICT_FAIL,
    ("features-cross-instrument-service", "liquidation_clusters"): ServiceEmissionPolicy.STRICT_FAIL,
    ("features-cross-instrument-service", "liquidation_band_prediction"): ServiceEmissionPolicy.NAN_FILL,
    ("features-cross-instrument-service", "flow_interaction"): ServiceEmissionPolicy.STRICT_FAIL,
    ("features-cross-instrument-service", "composite_sr"): ServiceEmissionPolicy.STRICT_FAIL,
    ("features-cross-instrument-service", "dxy_momentum"): ServiceEmissionPolicy.NAN_FILL,
    ("features-cross-instrument-service", "paired_price_dispersion"): ServiceEmissionPolicy.STRICT_FAIL,
    ("features-cross-instrument-service", "polymarket_crowd_sentiment"): ServiceEmissionPolicy.NAN_FILL,
    ("features-cross-instrument-service", "polymarket_trade_flow"): ServiceEmissionPolicy.NAN_FILL,
    ("features-cross-instrument-service", "polymarket_whale_activity"): ServiceEmissionPolicy.NAN_FILL,
    ("features-cross-instrument-service", "polymarket_market_microstructure"): ServiceEmissionPolicy.NAN_FILL,
    ("features-cross-instrument-service", "polymarket_cross_market"): ServiceEmissionPolicy.STRICT_FAIL,
    ("features-cross-instrument-service", "polymarket_temporal_patterns"): ServiceEmissionPolicy.NAN_FILL,
    # Legacy entries (key "features-service" does NOT match handler _SERVICE_NAME
    # "features-delta-one-service"; these are orphaned but preserved to avoid
    # breaking any future consumers that may use the consolidated service name).
    ("features-service", "technical_indicators"): ServiceEmissionPolicy.NAN_FILL,
    ("features-service", "microstructure"): ServiceEmissionPolicy.STRICT_FAIL,
    ("features-service", "funding_oi"): ServiceEmissionPolicy.STRICT_FAIL,
    ("features-service", "futures_basis"): ServiceEmissionPolicy.STRICT_FAIL,
    ("features-service", "volatility_realized"): ServiceEmissionPolicy.NAN_FILL,
    ("features-service", "volume_flow"): ServiceEmissionPolicy.PARTIAL_OK,
    ("features-service", "liquidations"): ServiceEmissionPolicy.PARTIAL_OK,
    ("features-service", "economic_events"): ServiceEmissionPolicy.PARTIAL_OK,
    ("features-service", "targets"): ServiceEmissionPolicy.STRICT_FAIL,
    #
    # features-multi-timeframe-service — 8 entries (Phase 6.5 P2 fix 2026-05-14: added
    # correct "features-multi-timeframe-service" key entries for all seeded groups;
    # intraday_regime + micro_regime seeded NAN_FILL 2026-05-15 per slot-9→5 reassignment
    # operator decision; issue mtf_intraday_micro_regime_policy_2026_05_14.md closed).
    # Cross-TF alignment groups: STRICT_FAIL (any stale leg = lookahead-bias trap).
    # Single-TF regime labels: NAN_FILL (partial day still yields computable labels).
    ("features-multi-timeframe-service", "tf_momentum_alignment"): ServiceEmissionPolicy.STRICT_FAIL,
    ("features-multi-timeframe-service", "tf_structure_context"): ServiceEmissionPolicy.STRICT_FAIL,
    ("features-multi-timeframe-service", "tf_vol_compression"): ServiceEmissionPolicy.STRICT_FAIL,
    ("features-multi-timeframe-service", "tf_confluence_signals"): ServiceEmissionPolicy.STRICT_FAIL,
    ("features-multi-timeframe-service", "tf_risk_reward"): ServiceEmissionPolicy.STRICT_FAIL,
    ("features-multi-timeframe-service", "wedge_confluence"): ServiceEmissionPolicy.STRICT_FAIL,
    # intraday_regime + micro_regime: single-TF (1h / 1m OHLCV-derived regime labels).
    # NOT cross-TF — no paired-spec lookahead-bias risk. Partial OHLCV day still yields
    # computable regime labels. ML consumer NaN-fills natively. → NAN_FILL (Option A,
    # operator-acked via slot-9→5 reassignment 2026-05-14).
    ("features-multi-timeframe-service", "intraday_regime"): ServiceEmissionPolicy.NAN_FILL,
    ("features-multi-timeframe-service", "micro_regime"): ServiceEmissionPolicy.NAN_FILL,
    # Legacy entries (key "features-service" does NOT match handler _SERVICE_NAME
    # "features-multi-timeframe-service"; orphaned but preserved as catch-all).
    ("features-service", "tf_momentum_alignment"): ServiceEmissionPolicy.STRICT_FAIL,
    ("features-service", "tf_structure_context"): ServiceEmissionPolicy.STRICT_FAIL,
    ("features-service", "tf_vol_compression"): ServiceEmissionPolicy.STRICT_FAIL,
    ("features-service", "tf_confluence_signals"): ServiceEmissionPolicy.STRICT_FAIL,
    #
    # features-calendar-service — 2 entries (Phase 6.5 extension, 2026-05-12).
    # Calendar features are venue-agnostic and deterministically derived from
    # time (time_features) or economic-calendar sources (economic_events).
    #
    # time_features: purely time-derived cyclic encodings + session flags
    # (day-of-week, month, hour, session overlap, etc.). No upstream source
    # that can be "partially missing" — the generator either runs fully or fails.
    # ML consumers NaN-fill natively. → NAN_FILL.
    #
    # economic_events: sourced from economic calendar (FRED / hardcoded events).
    # Legitimate gaps on holidays/weekends/pre-source-coverage days are expected.
    # Partial upstream source coverage is normal. → PARTIAL_OK.
    ("features-calendar-service", "time_features"): ServiceEmissionPolicy.NAN_FILL,
    ("features-calendar-service", "economic_events"): ServiceEmissionPolicy.PARTIAL_OK,
    #
    # yield_curve / economic_results — 2 entries (wired into CALENDAR_FEATURE_GROUPS
    # 2026-07-30, per issues/macro_micro_econ_data_capture_audit_2026_06_05.md's
    # "Recommended decision" Phase 1). Both are genuinely FRED-sourced with
    # legitimate gaps (yield_curve: weekends/holidays with no treasury print;
    # economic_results: most days have zero releases) — same rationale as
    # economic_events above. → PARTIAL_OK.
    ("features-calendar-service", "yield_curve"): ServiceEmissionPolicy.PARTIAL_OK,
    ("features-calendar-service", "economic_results"): ServiceEmissionPolicy.PARTIAL_OK,
    #
    # features-commodity-service — 6 entries (Phase 6.5 extension, 2026-05-12).
    # Source: FACTOR_REGISTRY in features_service/commodity/engine/factors/__init__.py
    # (6 distinct factor_groups).
    #
    # storage_alpha / crude_storage_alpha: StorageDeviationFactor — OHLCV-derived
    # rolling storage deviation signals. Tree-based ML consumer NaN-fills natively;
    # short gaps on holidays/weekends acceptable. → NAN_FILL.
    #
    # price_momentum: PriceMomentumFactor — OHLCV-derived rolling price momentum.
    # Same ML-consumer NaN-fill tolerance as vol_30d anchor (operator-msg-10). → NAN_FILL.
    #
    # weather_delta: DegreeDayFactor — weather/seasonal degree-day signal.
    # Sourced from NOAA/weather APIs; legitimate gaps on weekends + data-release
    # cadence gaps are expected. Rolling-window aggregate. → PARTIAL_OK.
    #
    # cot_positioning: ManagedMoneyFactor — CFTC Commitment of Traders weekly data.
    # Weekly release cadence means most daily requests hit a gap. Expected source
    # gap is normal; downstream fills with last-known. → PARTIAL_OK.
    #
    # rig_count: RigCountFactor — Baker Hughes weekly rig count release.
    # Same weekly-cadence reasoning as cot_positioning. → PARTIAL_OK.
    ("features-commodity-service", "storage_alpha"): ServiceEmissionPolicy.NAN_FILL,
    ("features-commodity-service", "crude_storage_alpha"): ServiceEmissionPolicy.NAN_FILL,
    ("features-commodity-service", "price_momentum"): ServiceEmissionPolicy.NAN_FILL,
    ("features-commodity-service", "weather_delta"): ServiceEmissionPolicy.PARTIAL_OK,
    ("features-commodity-service", "cot_positioning"): ServiceEmissionPolicy.PARTIAL_OK,
    ("features-commodity-service", "rig_count"): ServiceEmissionPolicy.PARTIAL_OK,
}
"""Per-(service, output_data_type) emission policy seed.

This is **not the final shape** — it is the initial seed per writegate plan
Phase 3.D.5 Wave 4. Per-service rollout (slice c) extends this dict per the
service team's audit. Adding a row that disagrees with the operator-msg-10
framing requires plan annotation explaining why.

**Why STRICT_FAIL is the default for unseeded pairs**: a missing entry means
"the service team has not declared a policy for this output yet." Policy
declaration is a deliberate architectural choice; silently defaulting to
permissive ``PARTIAL_OK`` would let services ship partial-truth outputs
without operator review. Fail-loud forces the decision.
"""


EVENT_TO_STATE: Final[dict[EmissionLifecycleEvent, ServiceEmissionStateEnum]] = {
    EmissionLifecycleEvent.PUBLISHED_OK: ServiceEmissionStateEnum.PUBLISHED_OK,
    EmissionLifecycleEvent.PUBLISHED_DEGRADED: ServiceEmissionStateEnum.PUBLISHED_DEGRADED,
    EmissionLifecycleEvent.STALE_DATA: ServiceEmissionStateEnum.STALE_DATA_HEARTBEAT_ONLY,
    EmissionLifecycleEvent.BLOCKED: ServiceEmissionStateEnum.BLOCKED,
}


__all__ = [
    "EVENT_TO_STATE",
    "SERVICE_OUTPUT_POLICIES",
]
