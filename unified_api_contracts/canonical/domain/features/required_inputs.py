"""SSOT for the ``feature_group -> required_inputs`` DAG.

Single declaration consumed by:

* writegate's ``LookaheadBiasError.assert_no_lookahead(...)`` — every input
  row consumed by a feature compute must satisfy
  ``input.available_at <= target_ts - horizon``. The DAG drives the check.
* deployment-api ``data_status`` denominator — when the UI asks
  "is feature_group X covered for date D?", the denominator is
  ``required_inputs(X)`` clipped to source-coverage windows.
* features-* phantom audit — denominator + per-feature_group probe.

Today the DAG is inlined per-service across features-onchain, features-sports,
and features-delta-one (their respective ``feature_builder_registry.py``
modules). Per writegate's "Temporary states" table, those inlined DAGs
are the temporary state and this module is the named successor.

Layer discipline (CLAUDE.md "Shard-granularity SSOT"):

* **[UAC]** — this module declares WHAT inputs each feature_group requires.
* **[UTL]** — ``LookaheadBiasError`` reads this declaration.
* **[per-service]** — feature_builder_registry imports from here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from typing import Final

from unified_api_contracts.canonical.crosscutting.availability_semantics import (
    AVAILABILITY_AT_SEMANTICS,
    AvailabilitySemantic,
)


@dataclass(frozen=True)
class InputReq:
    """A single ``(asset_group, data_type)`` input requirement for a feature_group.

    The ``available_at_rule`` mirrors writegate's ``AVAILABILITY_AT_SEMANTICS``
    taxonomy — it MUST equal ``AVAILABILITY_AT_SEMANTICS[(asset_group, data_type)]``
    or the lookahead-bias check will use the wrong stamping rule. Validation
    is enforced by ``validate_required_inputs()`` and the UAC test suite.

    ``source`` is optional. Set it when the feature group is bound to a
    specific adapter (e.g. ``"lido_api"`` for Lido LST yields, or
    ``"defillama_api"`` for DefiLlama TVL); leave it ``None`` for inputs
    that may come from any source for the ``(asset_group, data_type)``
    pair (e.g. CeFi ``ohlcv_1m`` from Tardis OR Databento).

    ``horizon`` is the lookahead buffer. ``timedelta(0)`` means "available
    by the target timestamp itself"; positive means "available at least
    ``horizon`` before target." Sports features use ``timedelta(hours=24)``
    or larger to model the kickoff-time lookahead window.
    """

    asset_group: str
    data_type: str
    available_at_rule: AvailabilitySemantic
    horizon: timedelta = field(default_factory=lambda: timedelta(0))
    source: str | None = None


# ---------------------------------------------------------------------------
# Registry — feature_group -> list[InputReq]
# ---------------------------------------------------------------------------
#
# Populated for feature_groups whose ``(asset_group, data_type)`` inputs are
# already registered in ``AVAILABILITY_AT_SEMANTICS``. Feature groups whose
# upstream data_types are not yet in availability_semantics (defi
# ``lending_indices`` / ``risk_params`` / ``rewards`` / ``flash_loan_events``
# / ``eigenlayer_rewards``; sports ``required_inputs`` reference-entity-name
# vocabulary) are deliberately omitted from this dict for now. They appear
# in ``EXPECTED_FEATURE_GROUPS_BY_SERVICE`` (denominator coverage), but the
# lookahead-bias check skips groups absent here. See
# ``## Temporary states + their canonical follow-up plans`` in
# ``feature_dag_uac_ssot_and_features_coverage_2026_05_06.md``.

FEATURE_REQUIRED_INPUTS: Final[dict[str, list[InputReq]]] = {
    # ---- features-onchain (defi) ----------------------------------------
    # Phase 1A.2 follow-up shipped 2026-05-07: 8 of the 10 deferred onchain
    # feature_groups now lifted in here, after the
    # ``AVAILABILITY_AT_SEMANTICS`` defi vocabulary gap closed (UAC@2f40c9d
    # registered lending_indices / risk_params / rewards / flash_loan_events
    # / eigenlayer_rewards as ``tick_timestamp``). Mapping derived from
    # ``features_onchain_service.schemas.feature_builder_registry._metadata``
    # SSOT: each calculator's ``sources`` list points at the source API,
    # which writes into the corresponding raw DeFi data_type bucket the
    # calculator reads on the next pipeline stage. The remaining 2 are
    # genuine external API live-reads that bypass the manifest entirely
    # (see Temporary states section in the feature_dag plan).
    "lst_yields": [
        InputReq(
            asset_group="defi",
            data_type="lst_yields",
            available_at_rule="tick_timestamp",
            source=None,  # multi-source: lido_api + etherfi_contract + jito_solana
        ),
    ],
    "lending_rates": [
        InputReq(
            asset_group="defi",
            data_type="lending_indices",
            available_at_rule="tick_timestamp",
            source="aave_v3_subgraph",
        ),
    ],
    "utilization": [
        InputReq(
            asset_group="defi",
            data_type="lending_indices",
            available_at_rule="tick_timestamp",
            source="aave_v3_subgraph",
        ),
    ],
    "risk_params": [
        InputReq(
            asset_group="defi",
            data_type="risk_params",
            available_at_rule="tick_timestamp",
            source="aave_v3_rpc",
        ),
    ],
    "rewards": [
        InputReq(
            asset_group="defi",
            data_type="eigenlayer_rewards",
            available_at_rule="tick_timestamp",
            source="eigenlayer_api",
        ),
    ],
    "flash_loan_availability": [
        InputReq(
            asset_group="defi",
            data_type="flash_loan_events",
            available_at_rule="tick_timestamp",
            source="morpho_subgraph",
        ),
    ],
    "rate_impact": [
        # Phase 1 calculator — depends on lending_rates + utilization
        # outputs, which both consume lending_indices upstream. Lookahead-bias
        # enforcement walks the dependency graph; declaring the leaf data_type
        # here is sufficient.
        InputReq(
            asset_group="defi",
            data_type="lending_indices",
            available_at_rule="tick_timestamp",
            source="aave_v3_subgraph",
        ),
    ],
    # NOT lifted (and intentionally so):
    #   * macro_sentiment — live HTTP fetches from CoinGecko + DefiLlama
    #     APIs; same situation. The DefiLlama leg COULD point at
    #     ``(defi, liquidity)`` but the CoinGecko macro feeds (BTC dominance,
    #     total market cap) have no registered data_type at all. Defer until
    #     either we register ``crypto_sentiment`` / ``macro_metrics`` as
    #     defi data_types OR move these calculators behind a captured-tick
    #     adapter that writes into a registered data_type.
    # Successor: ``feature_dag_uac_ssot_and_features_coverage_2026_05_06.md``
    # § "Temporary states + their canonical follow-up plans" — bullet
    # "External-sentiment-API live-read pass-throughs".
    # ---- features-delta-one (cefi / tradfi candle-derived) --------------
    # Price-based feature groups all read ohlcv_1m. We use ohlcv_1m as the
    # canonical base data_type (other timeframes derive from it via
    # resampling — same available_at semantic).
    "technical_indicators": [
        InputReq(asset_group="cefi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
        InputReq(asset_group="tradfi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
    ],
    "moving_averages": [
        InputReq(asset_group="cefi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
        InputReq(asset_group="tradfi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
    ],
    "oscillators": [
        InputReq(asset_group="cefi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
        InputReq(asset_group="tradfi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
    ],
    "volatility_realized": [
        InputReq(asset_group="cefi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
        InputReq(asset_group="tradfi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
    ],
    "momentum": [
        InputReq(asset_group="cefi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
        InputReq(asset_group="tradfi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
    ],
    "volume_analysis": [
        InputReq(asset_group="cefi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
        InputReq(asset_group="tradfi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
    ],
    "vwap": [
        InputReq(asset_group="cefi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
        InputReq(asset_group="tradfi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
    ],
    "candlestick_patterns": [
        InputReq(asset_group="cefi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
        InputReq(asset_group="tradfi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
    ],
    "market_structure": [
        InputReq(asset_group="cefi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
        InputReq(asset_group="tradfi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
    ],
    "returns": [
        InputReq(asset_group="cefi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
        InputReq(asset_group="tradfi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
    ],
    "round_numbers": [
        InputReq(asset_group="cefi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
        InputReq(asset_group="tradfi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
    ],
    "streaks": [
        InputReq(asset_group="cefi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
        InputReq(asset_group="tradfi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
    ],
    "targets": [
        InputReq(asset_group="cefi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
        InputReq(asset_group="tradfi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
    ],
    "swing_outcome_targets": [
        InputReq(asset_group="cefi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
        InputReq(asset_group="tradfi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
    ],
    # Microstructure pulls book + tbbo (tradfi only — book_snapshot is a
    # CeFi-only AVAILABILITY_AT_SEMANTICS entry; tradfi uses tbbo).
    "microstructure": [
        InputReq(asset_group="cefi", data_type="book_snapshot", available_at_rule="tick_timestamp"),
        InputReq(asset_group="tradfi", data_type="tbbo", available_at_rule="tick_timestamp"),
    ],
    "liquidations": [
        InputReq(asset_group="cefi", data_type="liquidations", available_at_rule="tick_timestamp"),
    ],
    "volume_flow": [
        InputReq(asset_group="cefi", data_type="trades", available_at_rule="tick_timestamp"),
        InputReq(asset_group="tradfi", data_type="trades", available_at_rule="tick_timestamp"),
    ],
    # S/R + enrichment groups all read ohlcv_1m.
    "supply_demand_zones": [
        InputReq(asset_group="cefi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
        InputReq(asset_group="tradfi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
    ],
    "fibonacci": [
        InputReq(asset_group="cefi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
        InputReq(asset_group="tradfi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
    ],
    "level_confluence": [
        InputReq(asset_group="cefi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
        InputReq(asset_group="tradfi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
    ],
    "market_structure_sequence": [
        InputReq(asset_group="cefi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
        InputReq(asset_group="tradfi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
    ],
    "sr_memory": [
        InputReq(asset_group="cefi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
        InputReq(asset_group="tradfi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
    ],
    "signal_confirmation": [
        InputReq(asset_group="cefi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
        InputReq(asset_group="tradfi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
    ],
    "statistical_anomaly": [
        InputReq(asset_group="cefi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
        InputReq(asset_group="tradfi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
    ],
    "order_flow_inference": [
        InputReq(asset_group="cefi", data_type="trades", available_at_rule="tick_timestamp"),
        InputReq(asset_group="cefi", data_type="book_snapshot", available_at_rule="tick_timestamp"),
    ],
    "return_kurtosis": [
        InputReq(asset_group="cefi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
        InputReq(asset_group="tradfi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
    ],
    "polynomial_trendlines": [
        InputReq(asset_group="cefi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
        InputReq(asset_group="tradfi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
    ],
    "risk_reward": [
        InputReq(asset_group="cefi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
        InputReq(asset_group="tradfi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
    ],
    "wedge_quality": [
        InputReq(asset_group="cefi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
        InputReq(asset_group="tradfi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
    ],
    "confluence": [
        InputReq(asset_group="cefi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
        InputReq(asset_group="tradfi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
    ],
    # ---- features-cross-instrument (CeFi/TradFi multi-asset + Prediction) -
    # Phase 4 expansion 2026-05-11 (`ikenna-available-at-tab`). Mapping
    # derived from features-cross-instrument's BuilderEntry registry
    # ``sources`` declarations, normalised to UAC canonical data_type names.
    # All upstream pairs verified against ``AVAILABILITY_AT_SEMANTICS``;
    # ``validate_required_inputs()`` is the runtime gate.
    "regime_detection": [
        InputReq(asset_group="cefi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
        InputReq(asset_group="tradfi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
    ],
    "cross_venue_spreads": [
        InputReq(asset_group="cefi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
        InputReq(asset_group="tradfi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
    ],
    "realized_implied_vol": [
        InputReq(asset_group="cefi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
        InputReq(asset_group="cefi", data_type="options_chain", available_at_rule="tick_timestamp"),
        InputReq(asset_group="tradfi", data_type="options_chain", available_at_rule="tick_timestamp"),
    ],
    "cross_asset_correlation": [
        InputReq(asset_group="cefi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
        InputReq(asset_group="tradfi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
    ],
    "cross_instrument_dynamics": [
        InputReq(asset_group="cefi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
        InputReq(asset_group="tradfi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
    ],
    "cme_gap": [
        # CME Globex tradfi-only — captures the weekend / overnight gap on
        # CME crypto futures markets.
        InputReq(asset_group="tradfi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
    ],
    "book_depth_bands": [
        InputReq(asset_group="cefi", data_type="book_snapshot", available_at_rule="tick_timestamp"),
    ],
    "liquidity_walls": [
        InputReq(asset_group="cefi", data_type="book_snapshot", available_at_rule="tick_timestamp"),
    ],
    "liquidation_clusters": [
        InputReq(asset_group="cefi", data_type="liquidations", available_at_rule="tick_timestamp"),
        InputReq(asset_group="cefi", data_type="book_snapshot", available_at_rule="tick_timestamp"),
    ],
    "liquidation_band_prediction": [
        InputReq(asset_group="cefi", data_type="funding_rate", available_at_rule="tick_timestamp"),
        InputReq(asset_group="cefi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
    ],
    "flow_interaction": [
        InputReq(asset_group="cefi", data_type="trades", available_at_rule="tick_timestamp"),
        InputReq(asset_group="cefi", data_type="book_snapshot", available_at_rule="tick_timestamp"),
    ],
    "cointegration": [
        InputReq(asset_group="cefi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
        InputReq(asset_group="tradfi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
    ],
    # ---- features-cross-instrument — Polymarket prediction-market reads -
    # All 6 Polymarket-derived feature_groups consume the canonical
    # ``(prediction, trades)`` shard (Polymarket CLOB tick capture).
    "polymarket_crowd_sentiment": [
        InputReq(asset_group="prediction", data_type="trades", available_at_rule="tick_timestamp"),
    ],
    "polymarket_trade_flow": [
        InputReq(asset_group="prediction", data_type="trades", available_at_rule="tick_timestamp"),
    ],
    "polymarket_whale_activity": [
        InputReq(asset_group="prediction", data_type="trades", available_at_rule="tick_timestamp"),
    ],
    "polymarket_market_microstructure": [
        InputReq(asset_group="prediction", data_type="trades", available_at_rule="tick_timestamp"),
        InputReq(asset_group="prediction", data_type="book_snapshot_5", available_at_rule="tick_timestamp"),
    ],
    "polymarket_cross_market": [
        InputReq(asset_group="prediction", data_type="trades", available_at_rule="tick_timestamp"),
    ],
    "polymarket_temporal_patterns": [
        InputReq(asset_group="prediction", data_type="trades", available_at_rule="tick_timestamp"),
    ],
    # ---- Phase 1 (depends on walls + clusters; leaf data_types only) ----
    "composite_sr": [
        InputReq(asset_group="cefi", data_type="book_snapshot", available_at_rule="tick_timestamp"),
        InputReq(asset_group="cefi", data_type="liquidations", available_at_rule="tick_timestamp"),
    ],
    # ---- features-volatility (tradfi options + futures chains) -----------
    # Reads bundled options_chain / futures_chain shards for the TradFi
    # archetype universe (CME ES.OPT clusters, CBOE VIX, NASDAQ ETF options
    # post-cutover). Cross-listed for cefi where Deribit/Tardis supply
    # parallel coverage (per `tradfi_master` § feature_groups).
    "options_iv": [
        InputReq(asset_group="cefi", data_type="options_chain", available_at_rule="tick_timestamp"),
        InputReq(asset_group="tradfi", data_type="options_chain", available_at_rule="tick_timestamp"),
    ],
    "futures_term_structure": [
        InputReq(asset_group="cefi", data_type="futures_chain", available_at_rule="tick_timestamp"),
        InputReq(asset_group="tradfi", data_type="futures_chain", available_at_rule="tick_timestamp"),
    ],
    "gamma_exposure": [
        InputReq(asset_group="cefi", data_type="options_chain", available_at_rule="tick_timestamp"),
        InputReq(asset_group="tradfi", data_type="options_chain", available_at_rule="tick_timestamp"),
    ],
    "variance_risk_premium": [
        InputReq(asset_group="cefi", data_type="options_chain", available_at_rule="tick_timestamp"),
        InputReq(asset_group="tradfi", data_type="options_chain", available_at_rule="tick_timestamp"),
    ],
    "second_order_greeks": [
        InputReq(asset_group="cefi", data_type="options_chain", available_at_rule="tick_timestamp"),
        InputReq(asset_group="tradfi", data_type="options_chain", available_at_rule="tick_timestamp"),
    ],
    "tradfi_vol_surface": [
        InputReq(asset_group="tradfi", data_type="options_chain", available_at_rule="tick_timestamp"),
    ],
    "vol_surface_term_structure": [
        InputReq(asset_group="tradfi", data_type="options_chain", available_at_rule="tick_timestamp"),
    ],
    # CBOE VIX 15m + 1m OHLCV — the VIX-specific feature calculator
    # (features-service@b3814675 — vix_calculator.py) consumes ohlcv at
    # multiple timeframes. VIX 15m has its own data_type per CLAUDE.md
    # "VIX 15m" rule (VX futures via Databento XCBF.PITCH; Yahoo rolling 60d cross-check).
    "vix_features": [
        InputReq(asset_group="tradfi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
        InputReq(asset_group="tradfi", data_type="ohlcv_15m", available_at_rule="tick_timestamp"),
    ],
    # ---- features-sports (sports) ----------------------------------------
    # Mapping derived from features_sports_service.calculators + the
    # FEATURE_UPSTREAM_REQUIREMENTS registry in
    # unified_api_contracts.canonical.domain.sports.feature_upstream.
    # All sports data_types use asset_group="sports". Derived inputs (those
    # whose source="derived" in FEATURE_UPSTREAM_REQUIREMENTS) declare the
    # transitive leaf data_types so the lookahead-bias check can walk the DAG
    # without needing a separate inter-feature-group topological sort.
    # Stage A — single-source calculators
    # P1 2026-08-08: IS reference vocabulary lowercased (operator ruling).
    "team_form": [
        InputReq(asset_group="sports", data_type="fixtures", available_at_rule="announced_at"),
    ],
    "team_goals": [
        InputReq(asset_group="sports", data_type="fixtures", available_at_rule="announced_at"),
    ],
    "season_context": [
        InputReq(asset_group="sports", data_type="fixtures", available_at_rule="announced_at"),
        InputReq(asset_group="sports", data_type="standings", available_at_rule="fetch_completed_at"),
    ],
    "goal_timing": [
        InputReq(asset_group="sports", data_type="fixture_events", available_at_rule="event_time"),
    ],
    "ht_features": [
        InputReq(asset_group="sports", data_type="matches", available_at_rule="match_end_time"),
    ],
    "manager_calculator": [
        InputReq(asset_group="sports", data_type="fixtures", available_at_rule="announced_at"),
        InputReq(asset_group="sports", data_type="teams", available_at_rule="fetch_completed_at"),
    ],
    "formation_calculator": [
        InputReq(asset_group="sports", data_type="fixture_lineups", available_at_rule="kickoff_minus_60min"),
        InputReq(asset_group="sports", data_type="fixtures", available_at_rule="announced_at"),
    ],
    "injury_impact_calculator": [
        InputReq(asset_group="sports", data_type="injuries", available_at_rule="report_time"),
    ],
    "travel_calculator": [
        InputReq(asset_group="sports", data_type="fixtures", available_at_rule="announced_at"),
        InputReq(asset_group="sports", data_type="VENUES", available_at_rule="fetch_completed_at"),
    ],
    "european_fatigue_calculator": [
        InputReq(asset_group="sports", data_type="fixtures", available_at_rule="announced_at"),
    ],
    "elo_calculator": [
        InputReq(asset_group="sports", data_type="fixtures", available_at_rule="announced_at"),
    ],
    "h2h_calculator": [
        InputReq(asset_group="sports", data_type="fixtures", available_at_rule="announced_at"),
    ],
    "advanced_stats_calculator": [
        InputReq(asset_group="sports", data_type="fixture_stats", available_at_rule="match_end_time"),
        InputReq(asset_group="sports", data_type="fixtures", available_at_rule="announced_at"),
    ],
    "venue_context": [
        InputReq(asset_group="sports", data_type="fixtures", available_at_rule="announced_at"),
        InputReq(asset_group="sports", data_type="VENUES", available_at_rule="fetch_completed_at"),
    ],
    "league_calculator": [
        InputReq(asset_group="sports", data_type="fixtures", available_at_rule="announced_at"),
        InputReq(asset_group="sports", data_type="standings", available_at_rule="fetch_completed_at"),
    ],
    "referee_features": [
        InputReq(asset_group="sports", data_type="fixtures", available_at_rule="announced_at"),
    ],
    "squad_value_calculator": [
        InputReq(asset_group="sports", data_type="player_values", available_at_rule="fetch_completed_at"),
        InputReq(asset_group="sports", data_type="TRANSFER_RECORDS", available_at_rule="fetch_completed_at"),
    ],
    "weather_calculator": [
        InputReq(asset_group="sports", data_type="weather", available_at_rule="match_end_time"),
        InputReq(asset_group="sports", data_type="fixtures", available_at_rule="announced_at"),
    ],
    "sfi_progressive": [
        InputReq(asset_group="sports", data_type="sfi_progressive_stats", available_at_rule="match_end_time"),
    ],
    "footystats_predictions": [
        InputReq(asset_group="sports", data_type="predictions", available_at_rule="announced_at"),
    ],
    # Stage C — cross-source join calculators
    "team_xg": [
        InputReq(asset_group="sports", data_type="xg", available_at_rule="match_end_time"),
        InputReq(asset_group="sports", data_type="fixtures", available_at_rule="announced_at"),
    ],
    "halftime_calculator": [
        InputReq(asset_group="sports", data_type="matches", available_at_rule="match_end_time"),
        InputReq(asset_group="sports", data_type="fixture_stats", available_at_rule="match_end_time"),
    ],
    "transfer_window_calculator": [
        InputReq(asset_group="sports", data_type="player_values", available_at_rule="fetch_completed_at"),
        InputReq(asset_group="sports", data_type="TRANSFER_RECORDS", available_at_rule="fetch_completed_at"),
        InputReq(asset_group="sports", data_type="fixture_lineups", available_at_rule="kickoff_minus_60min"),
    ],
    "player_lineup_calculator": [
        InputReq(asset_group="sports", data_type="fixture_lineups", available_at_rule="kickoff_minus_60min"),
        InputReq(asset_group="sports", data_type="player_values", available_at_rule="fetch_completed_at"),
    ],
    "bench_sub_calculator": [
        InputReq(asset_group="sports", data_type="fixture_events", available_at_rule="event_time"),
        InputReq(asset_group="sports", data_type="fixture_lineups", available_at_rule="kickoff_minus_60min"),
    ],
    "odds_calculator": [
        # odds (IS footystats) removed 2026-06-25 (#6 coherent unit) — MTDS/odds-api owns raw odds.
        InputReq(asset_group="sports", data_type="odds_horizon_bucket", available_at_rule="publication_time"),
    ],
    "multisource_xg": [
        InputReq(asset_group="sports", data_type="xg", available_at_rule="match_end_time"),
        InputReq(asset_group="sports", data_type="matches", available_at_rule="match_end_time"),
    ],
    "xg_decomposition": [
        InputReq(asset_group="sports", data_type="fixture_stats", available_at_rule="match_end_time"),
        InputReq(asset_group="sports", data_type="xg", available_at_rule="match_end_time"),
    ],
    # Stage D — enriched / derived calculators (declare transitive leaf inputs)
    "team_derived": [
        InputReq(asset_group="sports", data_type="fixtures", available_at_rule="announced_at"),
    ],
    "relative_context": [
        InputReq(asset_group="sports", data_type="fixtures", available_at_rule="announced_at"),
        InputReq(asset_group="sports", data_type="standings", available_at_rule="fetch_completed_at"),
    ],
    "meta_features": [
        InputReq(asset_group="sports", data_type="fixtures", available_at_rule="announced_at"),
        InputReq(asset_group="sports", data_type="xg", available_at_rule="match_end_time"),
    ],
    "ml_predictions": [
        InputReq(asset_group="sports", data_type="fixtures", available_at_rule="announced_at"),
        InputReq(asset_group="sports", data_type="xg", available_at_rule="match_end_time"),
        # odds (IS footystats) removed 2026-06-25 (#6 coherent unit).
    ],
    "replacement_model": [
        InputReq(asset_group="sports", data_type="player_values", available_at_rule="fetch_completed_at"),
    ],
    "bucketed_features": [
        InputReq(asset_group="sports", data_type="fixtures", available_at_rule="announced_at"),
    ],
    "poisson_xg_calculator": [
        InputReq(asset_group="sports", data_type="xg", available_at_rule="match_end_time"),
    ],
    "shot_quality": [
        InputReq(asset_group="sports", data_type="xg_shots", available_at_rule="match_end_time"),
        InputReq(asset_group="sports", data_type="fixtures", available_at_rule="announced_at"),
    ],
}
"""Registry — feature_group -> list of upstream input requirements.

Feature groups absent here are *not* unsupported; they're feature groups
whose upstream ``(asset_group, data_type)`` is not yet in
``AVAILABILITY_AT_SEMANTICS``. The lookahead-bias check skips them rather
than asserting against an unregistered semantic. See module docstring +
the named successor plan.

Derived feature groups (e.g. ``rate_impact``, ``confluence``,
``risk_reward``) declare the TRANSITIVE upstream inputs
as if they were leaf inputs — the orchestrator's topological sort handles
the inter-feature_group dependency separately. This keeps lookahead-bias
checks simple: every feature_group's input list is the closure over
external data_types.
"""


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def get_required_inputs(feature_group: str) -> list[InputReq]:
    """Return the list of upstream inputs declared for ``feature_group``.

    Args:
        feature_group: A feature_group name (e.g. ``"lst_yields"``,
            ``"technical_indicators"``).

    Returns:
        The list of ``InputReq`` declarations. Returns an empty list when
        the feature_group is unregistered — callers should treat this as
        "no lookahead-bias enforcement on this group" until the registry
        is filled in.
    """
    return FEATURE_REQUIRED_INPUTS.get(feature_group, [])


def has_required_inputs(feature_group: str) -> bool:
    """Return ``True`` iff ``feature_group`` has a non-empty input declaration."""
    return bool(FEATURE_REQUIRED_INPUTS.get(feature_group))


def list_feature_groups() -> list[str]:
    """Return the sorted list of feature_groups with declared input requirements."""
    return sorted(FEATURE_REQUIRED_INPUTS)


def validate_required_inputs() -> list[str]:
    """Validate the registry. Returns a list of human-readable issues.

    Empty list = registry is internally consistent. Used by the UAC test
    suite (``tests/test_feature_dag_ssot.py``).

    Checks:

    1. Every ``(asset_group, data_type)`` in ``FEATURE_REQUIRED_INPUTS``
       MUST be a key in ``AVAILABILITY_AT_SEMANTICS``.
    2. Every ``InputReq.available_at_rule`` MUST equal
       ``AVAILABILITY_AT_SEMANTICS[(asset_group, data_type)]``.
    3. Every ``feature_group`` key MUST have at least one ``InputReq``
       (no empty lists — omit the key instead).
    """
    issues: list[str] = []
    for feature_group, reqs in FEATURE_REQUIRED_INPUTS.items():
        if not reqs:
            issues.append(
                f"feature_group {feature_group!r} has empty required_inputs list — "
                "omit the key instead of declaring an empty list"
            )
            continue
        for req in reqs:
            key = (req.asset_group, req.data_type)
            registered = AVAILABILITY_AT_SEMANTICS.get(key)
            if registered is None:
                issues.append(
                    f"feature_group {feature_group!r} declares input "
                    f"asset_group={req.asset_group!r}, data_type={req.data_type!r} "
                    "but no AVAILABILITY_AT_SEMANTICS entry exists for that pair"
                )
                continue
            if registered != req.available_at_rule:
                issues.append(
                    f"feature_group {feature_group!r} declares "
                    f"available_at_rule={req.available_at_rule!r} for "
                    f"({req.asset_group}, {req.data_type}), but "
                    f"AVAILABILITY_AT_SEMANTICS says {registered!r}"
                )
    return issues


__all__ = [
    "FEATURE_REQUIRED_INPUTS",
    "InputReq",
    "get_required_inputs",
    "has_required_inputs",
    "list_feature_groups",
    "validate_required_inputs",
]
