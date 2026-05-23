"""Service-output emission-policy SSOT — the orthogonal axis to manifest 4-state.

Manifest ``capture_status`` describes raw-shard capture state per
``(venue, data_type, instrument_id, day)``. This module describes **what each
service publishes for its own derived/aggregated output when upstream is
incomplete** — a separate concern that's invisible to the manifest but critical
for downstream service reasoning.

Operator framing 2026-05-07 evening (msg 10): _"missing data unexpected feels
more like something which should fail to deliver data for the downstream
client if it needs constant data ... whereas for lets say 24h high low you
still want that to probably record if you missing some data which is expected
because its tradfi and market isnt continuously open ... batch = live symmetry
and this happens like you would wanna alert/warn downstream that data is stale
by not publishing which is same as publishing nothing in batch ... heartbeat
you are alive just stale data so services know its not a disconnect but it is
a bad data event."_

Three stacked layers — net architecture:

* **Manifest 4-state** (``EmptyConfirmedReason``) — "What's the raw shard's
  capture state?" Per ``(venue, data_type, instrument_id, day)``. Lives in
  :mod:`~unified_api_contracts.canonical.crosscutting.honest_coverage`.
* **Service emission policy** (this module) — "What does service X publish
  for output Y when upstream is incomplete?"
* **Service output completeness** (UTL ``emission_publisher`` writes
  ``completeness_fraction`` + ``incomplete_window`` columns on derived
  parquets) — "What % of the upstream window made it into THIS published
  row + which inner shards are gaps?"

Plan: ``writegate_honest_coverage_endtoend_2026_05_06.md`` § Phase 3.D.5
Wave 4. UTL companion: :mod:`unified_trading_library.emission_publisher`.

Wave-4 scope — slice (a) only (the schema floor): enum + seed dict + helper.
No consumer wiring. Per-service rollout (slice c) is multi-week. Each
service-team owns its row of the policy table + the per-(service, output_data_type)
declaration.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final

from unified_api_contracts.canonical.crosscutting.service_emission_state import (
    ServiceEmissionStateEnum,
)


class ServiceEmissionPolicy(StrEnum):
    """Closed-set policy for what a service publishes when upstream input is incomplete.

    Every (service, output_data_type) pair MUST resolve to exactly one of these. The default
    for unknown pairs is :attr:`STRICT_FAIL` — fail-loud — to force explicit declaration as
    services migrate. See :data:`SERVICE_OUTPUT_POLICIES` for the seeded pairs.
    """

    STRICT_FAIL = "strict_fail"
    """Current-window upstream gap → DON'T publish the output row. Emit ``STALE_DATA``
    lifecycle event (heartbeat-only, no metric). Downstream sees: service is UP but data
    is stale.

    Use for: real-time current-bar metrics (``ohlcv_1m`` current, derivative_ticker
    snapshots), per-archetype signals, per-strategy orders, fills — anywhere partial
    truth is wrong (would mislead a trading decision)."""

    PARTIAL_OK = "partial_ok"
    """Inner-window upstream gaps → publish output row WITH ``completeness_fraction``
    column. Downstream branches its own policy on that fraction.

    Use for: rolling-window aggregates whose denominator is the WINDOW not the inner-bar
    count (``ohlcv_24h`` high/low, daily volume, weekly correlation matrices).
    Catalog-snapshot-style outputs where partial-best-effort is normal."""

    NAN_FILL = "nan_fill"
    """Inner-window upstream gaps → publish output row with NaN where affected.
    Downstream (typically ML) NaN-fills per its own training-time rule.

    Use for: features tree-based models can NaN-fill natively (per CLAUDE.md
    "Honest absence vs fake placeholders" — 1-10% missing tolerance is fine for
    rank-based allocators and tree learners). Rolling vols, autocorrelation matrices,
    feature_groups whose downstream consumer is ML."""

    BLOCK_CRITICAL = "block_critical"
    """Any upstream gap → don't publish + fire P0 alert. No heartbeat-only fallback.

    Use for: position-balance-monitor portfolio_state, execution fill confirmation,
    risk-and-exposure risk_state, ml-training model_version — anywhere "partial truth"
    is worse than "no truth + alert"."""


# ---------------------------------------------------------------------------
# Lifecycle event types — re-export-friendly string constants.
#
# UTL ``emission_publisher.publish_with_policy`` emits one of these at every
# emission cycle. Schema lives in UTL events module; the names + semantics
# are pinned here so producers + consumers share a single SSOT.
# ---------------------------------------------------------------------------


class EmissionLifecycleEvent(StrEnum):
    """Lifecycle event names emitted by the publish boundary on every emission cycle.

    Downstream branching:

    * **Service-down** (no heartbeat at all over N intervals) → service alarm.
    * **Data-stale** (heartbeat + ``STALE_DATA``) → upstream-data alarm, service is fine.
    * **Degraded-but-running** (``PUBLISHED_DEGRADED``) → operator watch-list, service
      decisions tolerated.
    * **Broken** (``BLOCKED``) → P0, manual intervention required.
    """

    PUBLISHED_OK = "PUBLISHED_OK"
    """``completeness_fraction == 1.0`` — full upstream window represented. Default-happy path."""

    PUBLISHED_DEGRADED = "PUBLISHED_DEGRADED"
    """Gaps present but published per ``PARTIAL_OK`` / ``NAN_FILL`` policy. Event metadata
    carries ``completeness_fraction`` + ``incomplete_window`` (list of upstream
    ``(venue, data_type, instrument_id, iso_window_start, iso_window_end)`` tuples)."""

    STALE_DATA = "STALE_DATA"
    """``STRICT_FAIL`` policy fired — heartbeat-only, no metric row written. Distinguishes
    upstream-data outage from service-process outage (no heartbeat at all)."""

    BLOCKED = "BLOCKED"
    """``BLOCK_CRITICAL`` policy fired — no metric row, P0 alert dispatched.
    Manual operator intervention required."""


EMISSION_LIFECYCLE_EVENTS: Final[frozenset[str]] = frozenset(member.value for member in EmissionLifecycleEvent)
"""String-membership view of :class:`EmissionLifecycleEvent`. UTL event-emission
hot path validates names against this set — unknown event names raise the same
fail-loud pattern as :data:`unified_api_contracts.canonical.crosscutting.honest_coverage.EMPTY_CONFIRMED_REASONS`."""


# ---------------------------------------------------------------------------
# Per-(service, output_data_type) policy SSOT — initial seed.
#
# Service-team owners extend per their domain. The default for any unseeded pair
# is STRICT_FAIL (via :func:`get_emission_policy`) — fail-loud — so an unowned
# pair surfaces as a deliberate operator decision rather than a silent
# permissive policy.
#
# Conventions:
# * ``service`` is the canonical service name as it appears in ``setup_events(service_name=...)``
#   (e.g. ``"market-tick-data-service"``, ``"features-service"``,
#   ``"strategy-service"``, ``"execution-service"``).
# * ``output_data_type`` is the data_type the SERVICE PUBLISHES — distinct from
#   any input data_type the service reads. ``ohlcv_1m`` is consumed by MDPS as
#   input AND emitted by MDPS as output (different policies for current vs
#   historical re-emission).
# * Real-time ``current`` slices and historical re-emissions for the same
#   data_type can carry different policies — encode that with a
#   ``"<data_type>:<slice>"`` key shape (e.g. ``"ohlcv_1m:current"`` vs
#   ``"ohlcv_1m:historical"``).
# ---------------------------------------------------------------------------


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
    # strategy-service (position sub-package) — portfolio_state must be authoritative; partial = wrong.
    ("strategy-service", "portfolio_state"): ServiceEmissionPolicy.BLOCK_CRITICAL,
    # strategy-service (risk sub-package) — same constraint.
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
    ("features-service", "lst_yields"): ServiceEmissionPolicy.STRICT_FAIL,
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
    # features-sports-service — 7 entries.
    # Three canonical data_types (FIXTURE_FEATURES / ODDS_FEATURES / DERIVED_FEATURES)
    # split current/historical per slice convention = 6; plus live PubSub
    # subset = 7. Tree-based ML consumer → NaN-fill native (1-10% tolerance).
    # In-play HT-odds = STRICT_FAIL (live pricing input).
    ("features-sports-service", "fixture_features:current"): ServiceEmissionPolicy.NAN_FILL,
    ("features-sports-service", "fixture_features:historical"): ServiceEmissionPolicy.NAN_FILL,
    ("features-sports-service", "odds_features:current"): ServiceEmissionPolicy.STRICT_FAIL,
    ("features-sports-service", "odds_features:historical"): ServiceEmissionPolicy.NAN_FILL,
    ("features-sports-service", "derived_features:current"): ServiceEmissionPolicy.NAN_FILL,
    ("features-sports-service", "derived_features:historical"): ServiceEmissionPolicy.NAN_FILL,
    ("features-sports-service", "live_feature_subset"): ServiceEmissionPolicy.STRICT_FAIL,
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
    ("features-onchain-service", "lst_yields"): ServiceEmissionPolicy.STRICT_FAIL,
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


def get_emission_policy(service: str, output_data_type: str) -> ServiceEmissionPolicy:
    """Resolve the emission policy for ``(service, output_data_type)``.

    Args:
        service: Canonical service name (e.g. ``"market-data-processing-service"``).
            Must match the ``service_name`` passed to
            :func:`unified_trading_library.events.setup_events`.
        output_data_type: The data_type the service publishes. Use the
            ``"<data_type>:<slice>"`` shape (e.g. ``"ohlcv_1m:current"``) when
            real-time vs historical re-emission warrant different policies.

    Returns:
        The declared :class:`ServiceEmissionPolicy`, or
        :attr:`ServiceEmissionPolicy.STRICT_FAIL` for unseeded pairs (see module
        docstring rationale).
    """
    return SERVICE_OUTPUT_POLICIES.get((service, output_data_type), ServiceEmissionPolicy.STRICT_FAIL)


def is_emission_policy_declared(service: str, output_data_type: str) -> bool:
    """Return ``True`` if ``(service, output_data_type)`` has an explicit policy entry.

    The companion to :func:`get_emission_policy` — the writer-side guard in UTL
    ``emission_publisher.publish_with_policy`` warns when a service publishes
    to an undeclared output_data_type so service-team owners notice missing
    seed entries during rollout.
    """
    return (service, output_data_type) in SERVICE_OUTPUT_POLICIES


def policy_is_publish_row(policy: ServiceEmissionPolicy) -> bool:
    """Return ``True`` if ``policy`` writes a parquet row, ``False`` if heartbeat-only.

    * :attr:`ServiceEmissionPolicy.PARTIAL_OK` + :attr:`ServiceEmissionPolicy.NAN_FILL` write rows.
    * :attr:`ServiceEmissionPolicy.STRICT_FAIL` + :attr:`ServiceEmissionPolicy.BLOCK_CRITICAL`
      do NOT write rows (heartbeat-only / blocked).

    Used by UTL ``emission_publisher.publish_with_policy`` to drive the
    write-row-or-emit-event-only branch without re-implementing the policy
    table per call site.
    """
    return policy in {ServiceEmissionPolicy.PARTIAL_OK, ServiceEmissionPolicy.NAN_FILL}


def policy_is_alert(policy: ServiceEmissionPolicy) -> bool:
    """Return ``True`` if ``policy`` should fire a P0 alert (no heartbeat fallback).

    Only :attr:`ServiceEmissionPolicy.BLOCK_CRITICAL` triggers an alert; the other
    three policies emit lifecycle events (``PUBLISHED_OK`` / ``PUBLISHED_DEGRADED`` /
    ``STALE_DATA``) without escalating to alerting-service.
    """
    return policy is ServiceEmissionPolicy.BLOCK_CRITICAL


# ---------------------------------------------------------------------------
# next_state — Phase 1.B of manifest_schema_final_gate plan.
#
# Resolves a (policy, event) pair to the manifest-row column value
# (ServiceEmissionStateEnum). Pure function, no I/O. UTL
# ``emission_publisher.publish_with_policy`` consumes this when filling the
# v8 ``service_emission_state`` manifest column.
#
# The mapping derives the manifest state from the lifecycle event:
#
#   * EmissionLifecycleEvent.PUBLISHED_OK       → ServiceEmissionStateEnum.PUBLISHED_OK
#   * EmissionLifecycleEvent.PUBLISHED_DEGRADED → ServiceEmissionStateEnum.PUBLISHED_DEGRADED
#   * EmissionLifecycleEvent.STALE_DATA         → ServiceEmissionStateEnum.STALE_DATA_HEARTBEAT_ONLY
#   * EmissionLifecycleEvent.BLOCKED            → ServiceEmissionStateEnum.BLOCKED
#
# The ``policy`` argument is currently advisory — state derives from the
# event alone under the slice-b spec — but stays in the signature so future
# policy-specific state nuances (e.g. a fifth policy that publishes a row
# under DEGRADED conditions with a slimmer schema) can extend the resolver
# without breaking callers.
# ---------------------------------------------------------------------------


_EVENT_TO_STATE: Final[dict[EmissionLifecycleEvent, ServiceEmissionStateEnum]] = {
    EmissionLifecycleEvent.PUBLISHED_OK: ServiceEmissionStateEnum.PUBLISHED_OK,
    EmissionLifecycleEvent.PUBLISHED_DEGRADED: ServiceEmissionStateEnum.PUBLISHED_DEGRADED,
    EmissionLifecycleEvent.STALE_DATA: ServiceEmissionStateEnum.STALE_DATA_HEARTBEAT_ONLY,
    EmissionLifecycleEvent.BLOCKED: ServiceEmissionStateEnum.BLOCKED,
}


def next_state(
    *,
    policy: ServiceEmissionPolicy,
    event: EmissionLifecycleEvent,
) -> ServiceEmissionStateEnum:
    """Resolve a publish-boundary ``(policy, event)`` to the manifest-row state.

    Pure function. UTL ``emission_publisher.publish_with_policy`` calls this
    after emitting the lifecycle event so the v8 manifest write carries the
    structured state column. Downstream consumers reading the manifest can
    then reason about absence semantics from the column alone — no
    event-stream replay needed.

    The :class:`EmissionLifecycleEvent` taxonomy maps 1:1 to
    :class:`ServiceEmissionStateEnum` except for ``STALE_DATA`` →
    ``STALE_DATA_HEARTBEAT_ONLY`` (the manifest column name elaborates
    "heartbeat only" so downstream readers know the service is up). All four
    combinations are covered.

    Args:
        policy: The resolved policy from :func:`get_emission_policy`. Echoed
            into the signature for caller-side documentation + forward-compat
            with future policy-specific state nuances. Currently advisory —
            state derives from ``event`` alone.
        event: The lifecycle event the publish boundary just emitted (one of
            the 4 :class:`EmissionLifecycleEvent` members).

    Returns:
        The resolved :class:`ServiceEmissionStateEnum` value to write into
        the v8 ``service_emission_state`` manifest column.

    Reference: ``manifest_schema_final_gate_2026_05_09.md`` Phase 1.B.
    """
    # Mark as referenced — caller-side documentation contract.
    _ = policy
    return _EVENT_TO_STATE[event]


__all__ = [
    "EMISSION_LIFECYCLE_EVENTS",
    "SERVICE_OUTPUT_POLICIES",
    "EmissionLifecycleEvent",
    "ServiceEmissionPolicy",
    "get_emission_policy",
    "is_emission_policy_declared",
    "next_state",
    "policy_is_alert",
    "policy_is_publish_row",
]
