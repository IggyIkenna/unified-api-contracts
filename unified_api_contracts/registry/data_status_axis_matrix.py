"""Per-(service, asset_group) shard + display axis SSOT.

Data-status plan ``data_status_multi_axis_shard_propagation_2026_05_06.md``
Phase 0.

The data-status panel has historically slid one breakdown per asset_group
(``venue``, or ``data_type`` for sports) at deployment-api +
deployment-ui. That conflated two distinct concepts:

1. **Shard axes** — columns that earn their place in the manifest row key
   because (a) the writer can fail one value independently of others,
   (b) memory pressure forces per-value parquets, or (c) concurrency is
   orthogonal across values. CeFi-spot per-instrument, DeFi per-chain,
   sports per-league are shard axes; instruments-service per-venue
   instrument_type is NOT.
2. **Display axes** — columns useful for filter/group in the UI but
   without manifest-row inflation.

This module is the single SSOT for both, keyed on
``(service_name, asset_group)``. Every per-service writer gates its
``record_captured(...)`` kwargs on ``SHARD_AXIS_MATRIX[(service, asset_group)]``;
every data-status read endpoint builds its breakdowns from
``BREAKDOWN_AXES``; the deployment-ui axis selector reads from
``/api/config/shard-axis-matrix`` (deployment-api endpoint) and renders
dropdowns via the same SSOT.

Asset_group keys are lowercase per workspace CLAUDE.md (``cefi`` /
``defi`` / ``tradfi`` / ``sports`` / ``prediction``) plus the
``shared`` pseudo-asset-group for cross-asset services
(``ml-training-service``, ``ml-inference-service``,
``features-calendar-service``).
"""

from __future__ import annotations

from typing import Final

# ---------------------------------------------------------------------------
# Asset group constants (lowercase per workspace CLAUDE.md asset-group
# vocabulary rule). ``shared`` is the pseudo-group for cross-asset services.
# ---------------------------------------------------------------------------


CEFI: Final[str] = "cefi"
DEFI: Final[str] = "defi"
TRADFI: Final[str] = "tradfi"
SPORTS: Final[str] = "sports"
PREDICTION: Final[str] = "prediction"
SHARED: Final[str] = "shared"


_KNOWN_ASSET_GROUPS: Final[frozenset[str]] = frozenset({CEFI, DEFI, TRADFI, SPORTS, PREDICTION, SHARED})


# ---------------------------------------------------------------------------
# Shard axes — columns that earn manifest-row inflation per the
# failure-isolation / memory / concurrency criteria. Day is implicit on
# every row and never appears here.
# ---------------------------------------------------------------------------


SHARD_AXIS_MATRIX: Final[dict[tuple[str, str], tuple[str, ...]]] = {
    # instruments-service: per-venue bulk fetches; DEFI adds chain because
    # each chain is a separate RPC/subgraph endpoint with independent
    # failure modes; sports keys on (data_type, league_id); prediction
    # keys on (venue, canonical_question_group).
    ("instruments-service", CEFI): ("venue",),
    ("instruments-service", TRADFI): ("venue",),
    ("instruments-service", DEFI): ("venue", "chain"),
    ("instruments-service", SPORTS): ("data_type", "league_id"),
    ("instruments-service", PREDICTION): ("venue", "canonical_question_group"),
    # MTDS: per-instrument is a real shard (35GB+ per venue per day);
    # bundle root for options_chain / futures_chain; DEFI adds chain;
    # sports per-(data_type, league_id) — fixture_id is display-only;
    # prediction bundles per canonical_question_group.
    #
    # Axis ORDER matches the codex per-asset-group shard-key matrix in
    # CLAUDE.md so the deployment-UI drilldown follows the natural
    # operator navigation:
    #   CeFi / TradFi: venue → data_type → instrument_type → instrument_id → day
    #   DeFi:          venue → chain → data_type → instrument_id → day
    #   Sports:        data_type → league_id → day
    #   Prediction:    venue → canonical_question_group → data_type → day
    # (Plan: data_status_drilldown_shard_atom_alignment_2026_05_07 § Phase 6
    # operator finding 2026-05-07 evening — drilldown depth must match the
    # codex shard atom.)
    ("market-tick-data-service", CEFI): (
        "venue",
        "data_type",
        "instrument_type",
        "instrument_id",
    ),
    ("market-tick-data-service", TRADFI): (
        "venue",
        "data_type",
        "instrument_type",
        "instrument_id",
    ),
    ("market-tick-data-service", DEFI): (
        "venue",
        "chain",
        "data_type",
        "instrument_id",
    ),
    ("market-tick-data-service", SPORTS): ("data_type", "league_id"),
    ("market-tick-data-service", PREDICTION): (
        "venue",
        "canonical_question_group",
        "data_type",
    ),
    # MDPS: same shard atoms as MTDS per asset_group (it processes MTDS
    # output downstream).
    ("market-data-processing-service", CEFI): (
        "venue",
        "data_type",
        "instrument_type",
        "instrument_id",
    ),
    ("market-data-processing-service", TRADFI): (
        "venue",
        "data_type",
        "instrument_type",
        "instrument_id",
    ),
    ("market-data-processing-service", DEFI): (
        "venue",
        "chain",
        "data_type",
        "instrument_id",
    ),
    ("market-data-processing-service", SPORTS): ("data_type", "league_id"),
    ("market-data-processing-service", PREDICTION): (
        "venue",
        "canonical_question_group",
        "data_type",
    ),
    # features-service (consolidated from features-{family}-service repos).
    # Uses delta-one shard granularity as canonical — the most comprehensive
    # shape across active families. CEFI/TRADFI shard on
    # (venue, feature_group, timeframe, instrument_id); DEFI adds chain;
    # SPORTS = (feature_group, league_id); SHARED = (feature_group, timeframe);
    # PREDICTION = (venue, canonical_question_group, feature_group, timeframe).
    # Onchain DEFI and volatility share the delta-one DEFI shape.
    ("features-service", CEFI): (
        "venue",
        "feature_group",
        "timeframe",
        "instrument_id",
    ),
    ("features-service", TRADFI): (
        "venue",
        "feature_group",
        "timeframe",
        "instrument_id",
    ),
    ("features-service", DEFI): (
        "venue",
        "chain",
        "feature_group",
        "timeframe",
        "instrument_id",
    ),
    ("features-service", SPORTS): ("feature_group", "league_id"),
    ("features-service", SHARED): ("feature_group", "timeframe"),
    ("features-service", PREDICTION): (
        "venue",
        "canonical_question_group",
        "feature_group",
        "timeframe",
    ),
    # ml-training: experiment-based; cross-asset; job_id required for
    # multi-experiment tracking.
    ("ml-training-service", SHARED): (
        "model_family",
        "training_period",
        "job_id",
    ),
    # ml-inference: experiment-based; cross-asset.
    ("ml-inference-service", SHARED): ("model_family", "job_id"),
    # strategy-service: per asset_group; experiment-keyed.
    ("strategy-service", CEFI): ("strategy_id", "job_id"),
    ("strategy-service", TRADFI): ("strategy_id", "job_id"),
    ("strategy-service", DEFI): ("strategy_id", "job_id"),
    ("strategy-service", SPORTS): ("strategy_id", "job_id"),
    ("strategy-service", PREDICTION): ("strategy_id", "job_id"),
    # execution-service: per asset_group; experiment-keyed; instruction_type
    # discriminates simulation type.
    ("execution-service", CEFI): (
        "strategy_id",
        "instruction_type",
        "job_id",
    ),
    ("execution-service", TRADFI): (
        "strategy_id",
        "instruction_type",
        "job_id",
    ),
    ("execution-service", DEFI): (
        "strategy_id",
        "instruction_type",
        "job_id",
    ),
    ("execution-service", SPORTS): (
        "strategy_id",
        "instruction_type",
        "job_id",
    ),
    ("execution-service", PREDICTION): (
        "strategy_id",
        "instruction_type",
        "job_id",
    ),
}


# ---------------------------------------------------------------------------
# Display axes — columns kept on each row for filter/group in the UI but
# NOT shard atoms. Pure UI aid; no manifest-row inflation.
# ---------------------------------------------------------------------------


DISPLAY_AXES: Final[dict[tuple[str, str], tuple[str, ...]]] = {
    ("instruments-service", CEFI): ("instrument_type", "data_type"),
    ("instruments-service", TRADFI): ("instrument_type", "data_type"),
    ("instruments-service", DEFI): ("instrument_type", "data_type"),
    ("instruments-service", SPORTS): ("source",),
    ("instruments-service", PREDICTION): ("data_type",),
    # MTDS / MDPS CeFi+TradFi: ``instrument_type`` is now a shard axis
    # (codex shard-key matrix in CLAUDE.md — drilldown
    # ``venue → data_type → instrument_type → instrument_id → day``);
    # promoted from DISPLAY → SHARD per Phase 6 operator finding
    # 2026-05-07. DeFi: ``instrument_type`` (POOL/LENDING/LST) is
    # redundant with ``data_type`` for navigation purposes — kept as
    # display-only so DeFi drilldown stays
    # ``venue → chain → data_type → instrument_id → day``.
    ("market-tick-data-service", CEFI): (),
    ("market-tick-data-service", TRADFI): (),
    ("market-tick-data-service", DEFI): ("instrument_type",),
    ("market-tick-data-service", SPORTS): ("source", "fixture_id"),
    ("market-tick-data-service", PREDICTION): (),
    ("market-data-processing-service", CEFI): (),
    ("market-data-processing-service", TRADFI): (),
    ("market-data-processing-service", DEFI): ("instrument_type",),
    ("market-data-processing-service", SPORTS): ("source", "fixture_id"),
    ("market-data-processing-service", PREDICTION): (),
    ("features-service", CEFI): ("instrument_type",),
    ("features-service", TRADFI): ("instrument_type",),
    ("features-service", DEFI): ("instrument_type",),
    ("features-service", SPORTS): ("source", "data_type"),
    ("features-service", SHARED): (),
    ("features-service", PREDICTION): (),
    ("ml-training-service", SHARED): ("client_id", "asset_group"),
    ("ml-inference-service", SHARED): ("client_id", "asset_group"),
    ("strategy-service", CEFI): ("archetype", "client_id"),
    ("strategy-service", TRADFI): ("archetype", "client_id"),
    ("strategy-service", DEFI): ("archetype", "client_id"),
    ("strategy-service", SPORTS): ("archetype", "client_id"),
    ("strategy-service", PREDICTION): ("archetype", "client_id"),
    ("execution-service", CEFI): ("venue", "client_id"),
    ("execution-service", TRADFI): ("venue", "client_id"),
    ("execution-service", DEFI): ("venue", "client_id"),
    ("execution-service", SPORTS): ("venue", "client_id"),
    ("execution-service", PREDICTION): ("venue", "client_id"),
}


# ---------------------------------------------------------------------------
# Primary axis — the single axis the cell-grid uses for its main
# dimension. Other axes (shard + display) become secondary breakdowns
# in the data-status panel + drill-downs in the UI.
# ---------------------------------------------------------------------------


PRIMARY_AXIS: Final[dict[tuple[str, str], str]] = {
    # Pricing pipeline default = venue. Sports = data_type because
    # league_id is too granular for a default UI dimension.
    ("instruments-service", CEFI): "venue",
    ("instruments-service", TRADFI): "venue",
    ("instruments-service", DEFI): "venue",
    ("instruments-service", SPORTS): "data_type",
    ("instruments-service", PREDICTION): "venue",
    ("market-tick-data-service", CEFI): "venue",
    ("market-tick-data-service", TRADFI): "venue",
    ("market-tick-data-service", DEFI): "venue",
    ("market-tick-data-service", SPORTS): "data_type",
    ("market-tick-data-service", PREDICTION): "venue",
    ("market-data-processing-service", CEFI): "venue",
    ("market-data-processing-service", TRADFI): "venue",
    ("market-data-processing-service", DEFI): "venue",
    ("market-data-processing-service", SPORTS): "data_type",
    ("market-data-processing-service", PREDICTION): "venue",
    ("features-service", CEFI): "venue",
    ("features-service", TRADFI): "venue",
    ("features-service", DEFI): "venue",
    ("features-service", SPORTS): "feature_group",
    ("features-service", SHARED): "feature_group",
    ("features-service", PREDICTION): "venue",
    # Experiment-based services — primary axis = the experiment unit
    # that operators look at first.
    ("ml-training-service", SHARED): "model_family",
    ("ml-inference-service", SHARED): "model_family",
    ("strategy-service", CEFI): "strategy_id",
    ("strategy-service", TRADFI): "strategy_id",
    ("strategy-service", DEFI): "strategy_id",
    ("strategy-service", SPORTS): "strategy_id",
    ("strategy-service", PREDICTION): "strategy_id",
    ("execution-service", CEFI): "instruction_type",
    ("execution-service", TRADFI): "instruction_type",
    ("execution-service", DEFI): "instruction_type",
    ("execution-service", SPORTS): "instruction_type",
    ("execution-service", PREDICTION): "instruction_type",
}


# ---------------------------------------------------------------------------
# Breakdown axes — for the data-status ``breakdowns`` accordion: the
# union of shard + display axes minus the primary axis. Derived at
# import time from the three matrices above; never edit directly.
# ---------------------------------------------------------------------------


def _derive_breakdown_axes() -> dict[tuple[str, str], tuple[str, ...]]:
    """Build BREAKDOWN_AXES = (SHARD union DISPLAY) - {PRIMARY} per key.

    Preserves the SHARD-then-DISPLAY ordering so the deployment-ui
    accordion shows shard axes first, display axes second, primary axis
    not at all (it's the cell-grid main dimension already).
    """
    breakdowns: dict[tuple[str, str], tuple[str, ...]] = {}
    for key, shard_axes in SHARD_AXIS_MATRIX.items():
        display_axes = DISPLAY_AXES.get(key, ())
        primary = PRIMARY_AXIS.get(key)
        seen: set[str] = set()
        ordered: list[str] = []
        for axis in (*shard_axes, *display_axes):
            if axis == primary or axis in seen:
                continue
            seen.add(axis)
            ordered.append(axis)
        breakdowns[key] = tuple(ordered)
    return breakdowns


BREAKDOWN_AXES: Final[dict[tuple[str, str], tuple[str, ...]]] = _derive_breakdown_axes()


# ---------------------------------------------------------------------------
# Helpers — thin lookup wrappers. Callers can use the dicts directly
# but these give a stable signature for the deployment-api consumer +
# /api/config/shard-axis-matrix endpoint.
# ---------------------------------------------------------------------------


def get_shard_axes(service: str, asset_group: str) -> tuple[str, ...]:
    """Return shard axes for ``(service, asset_group)`` or ``()`` if absent.

    Empty tuple = service does not cover that asset_group (e.g.
    ``features-onchain-service`` only ships ``defi``).
    """
    return SHARD_AXIS_MATRIX.get((service, asset_group.lower()), ())


def get_display_axes(service: str, asset_group: str) -> tuple[str, ...]:
    """Return display axes for ``(service, asset_group)`` or ``()`` if absent."""
    return DISPLAY_AXES.get((service, asset_group.lower()), ())


def get_primary_axis(service: str, asset_group: str) -> str | None:
    """Return primary axis for ``(service, asset_group)`` or ``None`` if absent.

    ``None`` is the signal to fall back to the asset-group-default axis
    in the deployment-api consumer (``venue`` for pricing pipeline,
    ``data_type`` for sports).
    """
    return PRIMARY_AXIS.get((service, asset_group.lower()))


def get_breakdown_axes(service: str, asset_group: str) -> tuple[str, ...]:
    """Return breakdown axes (shard + display - primary) or ``()`` if absent."""
    return BREAKDOWN_AXES.get((service, asset_group.lower()), ())


def is_shard_axis(service: str, asset_group: str, axis: str) -> bool:
    """Return True iff ``axis`` is a shard atom for ``(service, asset_group)``."""
    return axis in get_shard_axes(service, asset_group)


__all__ = [
    "BREAKDOWN_AXES",
    "CEFI",
    "DEFI",
    "DISPLAY_AXES",
    "PREDICTION",
    "PRIMARY_AXIS",
    "SHARD_AXIS_MATRIX",
    "SHARED",
    "SPORTS",
    "TRADFI",
    "get_breakdown_axes",
    "get_display_axes",
    "get_primary_axis",
    "get_shard_axes",
    "is_shard_axis",
]
