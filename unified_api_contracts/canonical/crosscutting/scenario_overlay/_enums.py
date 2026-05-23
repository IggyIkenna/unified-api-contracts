"""Scenario overlay enums — basic taxonomy and categories."""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Final

_SCENARIO_ID_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[a-z][a-z0-9_]+$")


class ScenarioCategory(StrEnum):
    """High-level scenario taxonomy.

    Closed-set 7. A scenario may declare ONE primary category; secondary
    categories are captured in the per-scenario design fragment but not
    surfaced on the :class:`ScenarioOverlay` Pydantic instance (one-of-N
    keeps consumer dispatchers narrow).

    § 7 SSOT reconciliation
    ~~~~~~~~~~~~~~~~~~~~~~~

    Orthogonal to :class:`EmptyConfirmedReason` (manifest-side honest-absence
    vocabulary). Where both apply, the scenario emits both:
    `ScenarioCategory.TOPOLOGY_GAP` + manifest `record_empty(reason=...)`
    with the appropriate reason. Categories DO NOT shadow reasons.
    """

    TOPOLOGY_GAP = "TOPOLOGY_GAP"
    """Pipeline-topology rows missing (data gap, not a price move)."""
    STALENESS = "STALENESS"
    """Last-tick / heartbeat age exceeds threshold."""
    PRICE_SHOCK = "PRICE_SHOCK"
    """Mid-price / funding / basis / peg moves >= N sigma."""
    VENUE_OUTAGE = "VENUE_OUTAGE"
    """Venue / chain / protocol stops responding (REST + WS both down)."""
    DATA_CORRUPTION = "DATA_CORRUPTION"
    """Row content invalid (wild-print oracle, sandwich-attack signature, ...)."""
    CROSS_ASSET = "CROSS_ASSET"
    """Multi-instrument / multi-asset_group correlated event."""
    OPERATIONAL = "OPERATIONAL"
    """Operational dynamics (gas spike / mempool congestion / tx-inclusion delay)."""


class ScenarioOverlayLayer(StrEnum):
    """Pipeline-tap injection point for the mutation.

    Closed-set 6. A scenario may declare ONE primary layer; multi-layer
    mutations decompose into N scenarios composing via :attr:`ScenarioOverlay.composes_with`.

    Reuse-prod-codepath principle: every layer here corresponds to a real
    boundary in the unified pipeline (MTDS → MDPS → features-* → strategy →
    execution → matching engine; manifest writer + event stream are
    cross-cutting). No standalone backtest engine.
    """

    RAW_TICK = "RAW_TICK"
    """MTDS adapter `_post_fetch` hook — tick + book + funding rows."""
    FEATURE = "FEATURE"
    """features-service `_compute_*` exit OR mdps feature-layer hook."""
    SIGNAL = "SIGNAL"
    """strategy-service `signal_generator` emit boundary."""
    ORDER = "ORDER"
    """execution-service order submit + matching-engine adversarial mode."""
    EVENT = "EVENT"
    """Cross-cutting event stream injection (chain-slot / venue-halt / tx-status)."""
    MANIFEST = "MANIFEST"
    """ManifestWriter `record_*` hook — phantom-row or honest-empty injection."""


class OutcomeCategory(StrEnum):
    """Closed-set assertion category — what the scenario expects to observe.

    9 members covering the cross-product of `RiskRuleConsequence` x
    `CircuitBreakerId` x `KillSwitchId` x `AlertCode` plus P&L bounds +
    reconciliation hooks. Per the handshake doc fragment 11 § "Outcome
    assertion → expected-state cross-product."
    """

    STRATEGY_HALTED = "STRATEGY_HALTED"
    """No new signals emitted on (archetype, instrument) within SLA."""
    STRATEGY_SCALED_DOWN = "STRATEGY_SCALED_DOWN"
    """Signal size <= baseline * scale_factor within SLA."""
    RISK_BREAKER_TRIPPED = "RISK_BREAKER_TRIPPED"
    """Named :class:`CircuitBreakerId` transitions OPEN or DEGRADED."""
    ORDER_REJECTED = "ORDER_REJECTED"
    """execution-service refuses order at pre-flight."""
    ORDER_CANCELLED_ON_STALE = "ORDER_CANCELLED_ON_STALE"
    """Cancellation tx submitted within SLA after staleness signal."""
    KILL_SWITCH_ARMED = "KILL_SWITCH_ARMED"
    """Named :class:`KillSwitchId` armed by named provenance."""
    ALERT_FIRED = "ALERT_FIRED"
    """Named :class:`AlertCode` rule evaluates true with synthetic=true."""
    PNL_BOUNDED_BY = "PNL_BOUNDED_BY"
    """Per-archetype P&L stays within [lower, upper] bound post-scenario."""
    RECONCILIATION_FLAGGED = "RECONCILIATION_FLAGGED"
    """Named reconciler emits ``RECONCILIATION_DRIFT_DETECTED`` event."""


__all__ = [
    "_SCENARIO_ID_PATTERN",
    "OutcomeCategory",
    "ScenarioCategory",
    "ScenarioOverlayLayer",
]
