"""Instruments-live preflight-chain SSOT — upstream-required-before-downstream graph.

The dependency graph that gates every downstream trigger (sports lineups,
weather-cascade, injuries, cefi 15-min OHLCV, tradfi 15-min OHLCV, prediction
market-discovery) on the freshness of its required upstream entities. Lifts the
implicit graph (currently expressed inline across per-service ``_check_dependencies``
/ ``check_shard_freshness`` helpers — see CLAUDE.md "Honest absence vs fake
placeholders" § 2 unexpected-upstream-pipeline-gap rule) into a single
workspace-readable contract that BOTH batch and live MUST enforce identically.

**Live = batch invariant**: this module is the SSOT consulted by both modes.
The validator helper :func:`validate_preflight_for_trigger` is invoked from
the batch entrypoint AND the live entrypoint with the same arguments —
live-only is the *invocation cadence* (Cloud Scheduler triggers the live
path on a per-asset-group cron), not the *validation logic*. Per CLAUDE.md
"Live = batch — same data, same fields, same timing semantics" rule: zero
shape divergence between modes.

**Why this exists.** Without a single SSOT, the implicit graph drifts as
services evolve: one calculator's dependency tightens while another loosens,
and the May-23 live-DeFi cutover surface gets wedged at the wrong layer.
Codifying the graph here lets every consumer (instruments-service triggers,
features-* preflight, strategy preflight, deployment-UI Scheduled Jobs tab,
alerting-service rule (f) PREFLIGHT_FAILED + rule (g) UPSTREAM_STALE) read
from the same table.

**Companion docs.**

* Codex SSOT: ``codex/04-architecture/instruments-preflight-chain.md``
  (NEW 2026-05-08 — design + live=batch invariant + per-asset-group rules).
* UAC events: :class:`unified_api_contracts.internal.events.MissingDependency`
  + :class:`InstrumentsLivePreflightFailedDetails` (Phase A.5 — already shipped).
* UTL helper: :func:`unified_trading_library.instruments_preflight.run_preflight`
  (Phase A.10 — the runtime caller of :func:`validate_preflight_for_trigger`).

**Plan**: ``plans/epics/instruments_master.md`` § Phase A.9.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from datetime import date as _date
from enum import StrEnum
from typing import TYPE_CHECKING, Final, Protocol

from unified_api_contracts.canonical.gcs_paths import AssetGroup as MarketAssetGroup

if TYPE_CHECKING:
    # Avoid runtime import — `unified_api_contracts.internal.events`
    # transitively re-imports the top-level UAC namespace via
    # `internal.alerting`, causing a circular import when this module
    # is loaded during `canonical/__init__.py`. The runtime reference
    # is lazily resolved inside `validate_preflight_for_trigger`.
    from unified_api_contracts.internal.events import MissingDependency

__all__ = [
    "INSTRUMENTS_PREFLIGHT_REQUIREMENTS",
    "TRIGGER_TO_DOWNSTREAM_ENTITY",
    "ManifestReader",
    "PreflightFailed",
    "PreflightOK",
    "PreflightRequirement",
    "PreflightResult",
    "PreflightTrigger",
    "get_preflight_requirements",
    "get_trigger_definition",
    "validate_preflight_for_trigger",
]


# ---------------------------------------------------------------------------
# Trigger taxonomy — closed set of downstream-trigger names per asset_group.
# ---------------------------------------------------------------------------


class PreflightTrigger(StrEnum):
    """Closed set of downstream triggers that require preflight validation.

    Each trigger maps to a downstream entity-type that depends on one or more
    upstream entity-types being fresh. The mapping :data:`TRIGGER_TO_DOWNSTREAM_ENTITY`
    resolves a trigger to its produced entity-type, and
    :data:`INSTRUMENTS_PREFLIGHT_REQUIREMENTS` declares the upstream graph
    keyed by ``(asset_group, downstream_entity)``.

    NEW triggers MUST be added here AND seeded in
    :data:`INSTRUMENTS_PREFLIGHT_REQUIREMENTS`; the test suite asserts the
    two stay in lockstep.
    """

    # Sports — trigger-driven per ``trigger_based_reference_data_2026_04_13``.
    SPORTS_LINEUPS_KICKOFF_MINUS_60M = "sports_lineups_kickoff_minus_60m"
    SPORTS_WEATHER_CASCADE = "sports_weather_cascade"
    SPORTS_INJURIES_DAILY_REPOLL = "sports_injuries_daily_repoll"
    SPORTS_FIXTURES_DAILY_REPOLL = "sports_fixtures_daily_repoll"
    SPORTS_TEAMS_SEASON_ROLL = "sports_teams_season_roll"
    SPORTS_PLAYER_VALUES_TRANSFER_WINDOW = "sports_player_values_transfer_window"

    # CeFi 15-min cron — replaces Tardis T+1 batch with CCXT live polls.
    CEFI_OHLCV_15M_REFRESH = "cefi_ohlcv_15m_refresh"

    # TradFi 15-min cron — Polygon/Yahoo as Databento alternates.
    TRADFI_OHLCV_15M_REFRESH = "tradfi_ohlcv_15m_refresh"

    # Prediction 15-min cron — Polymarket/Kalshi market-discovery polls.
    PREDICTION_MARKET_DISCOVERY = "prediction_market_discovery"


# Maps each trigger to its produced downstream entity-type. The downstream
# entity name is what the trigger writes; the upstream-required graph is
# keyed by (asset_group, downstream_entity).
TRIGGER_TO_DOWNSTREAM_ENTITY: Final[Mapping[PreflightTrigger, str]] = {
    PreflightTrigger.SPORTS_LINEUPS_KICKOFF_MINUS_60M: "lineups",
    PreflightTrigger.SPORTS_WEATHER_CASCADE: "weather_forecast",
    PreflightTrigger.SPORTS_INJURIES_DAILY_REPOLL: "injuries",
    PreflightTrigger.SPORTS_FIXTURES_DAILY_REPOLL: "fixtures",
    PreflightTrigger.SPORTS_TEAMS_SEASON_ROLL: "teams",
    PreflightTrigger.SPORTS_PLAYER_VALUES_TRANSFER_WINDOW: "player_values",
    PreflightTrigger.CEFI_OHLCV_15M_REFRESH: "ohlcv_15m",
    PreflightTrigger.TRADFI_OHLCV_15M_REFRESH: "ohlcv_15m",
    PreflightTrigger.PREDICTION_MARKET_DISCOVERY: "prediction_markets",
}


# ---------------------------------------------------------------------------
# PreflightRequirement — one upstream entity that a downstream trigger needs.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PreflightRequirement:
    """One upstream-entity dependency for a downstream trigger.

    Attributes:
        upstream_entity_type: UAC entity-type name (e.g. ``"fixtures"``,
            ``"instrument-catalog"``, ``"teams"``). Matches the
            ``service_name`` / ``entity`` axis the manifest indexes by.
        max_staleness_seconds: Maximum age of the most-recent
            ``attempted_at`` in the upstream manifest beyond which the
            dependency is considered stale. Special value ``-1`` means
            "no staleness check — UAC-static SSOT, always fresh" (e.g.
            the prediction canonical_question_group registry).
        rationale: Human-readable explanation of why this dependency
            exists — surfaces in failure events + alerting messages.
    """

    upstream_entity_type: str
    max_staleness_seconds: int
    rationale: str


# Sentinel for UAC-static SSOTs that don't have a staleness check.
STATIC_SSOT_NO_STALENESS_CHECK: Final[int] = -1

# Convenience constants for readable seconds-tolerance literals.
_24H_SECONDS: Final[int] = 24 * 3600
_36H_SECONDS: Final[int] = 36 * 3600  # rolling-window fixtures (current ± 1d)
_7D_SECONDS: Final[int] = 7 * 24 * 3600  # season-roll teams freshness
_KICKOFF_MINUS_24H_SECONDS: Final[int] = 24 * 3600  # fixture-day fixtures freshness


# ---------------------------------------------------------------------------
# The DAG — per-(asset_group, downstream_entity) upstream-required entries.
#
# Each value is the ordered list of upstream entities that must satisfy
# their staleness tolerance before the downstream trigger fires. Fixture-day
# downstream entities (sports lineups / weather) require fixtures FRESH for
# the *fixture day*, not just the rolling window — the validator passes
# ``on_date=fixture_date`` to ``manifest_reader.get_freshness`` so the
# fixture-day shard is what's probed.
# ---------------------------------------------------------------------------


INSTRUMENTS_PREFLIGHT_REQUIREMENTS: Final[Mapping[tuple[MarketAssetGroup, str], tuple[PreflightRequirement, ...]]] = {
    # ── Sports ────────────────────────────────────────────────────────────
    # Lineups REQUIRES fixtures-for-the-fixture-day not older than kickoff - 24h.
    # The 24h tolerance is conservative — fixtures rarely change in the final
    # day before kickoff; if the fixture day's fixtures shard is older than
    # 24h we have NOT yet confirmed today's match will go ahead, so the
    # lineups capture must wait.
    (MarketAssetGroup.SPORTS, "lineups"): (
        PreflightRequirement(
            upstream_entity_type="fixtures",
            max_staleness_seconds=_KICKOFF_MINUS_24H_SECONDS,
            rationale=(
                "Lineups capture for fixture F requires that F's fixture-day fixtures "
                "shard is fresh within 24h of kickoff. Stale fixtures => match may "
                "have moved/cancelled => lineups capture is wasted API quota."
            ),
        ),
    ),
    # Weather-cascade REQUIRES fixtures-for-the-fixture-day. Same rule as
    # lineups — weather is requested for the venue + kickoff time of fixtures
    # we believe will go ahead; stale fixtures => wrong target lat/lon/time.
    (MarketAssetGroup.SPORTS, "weather_forecast"): (
        PreflightRequirement(
            upstream_entity_type="fixtures",
            max_staleness_seconds=_KICKOFF_MINUS_24H_SECONDS,
            rationale=(
                "Weather forecast cascade uses fixture venue + kickoff time as the "
                "target lat/lon/time triple. Stale fixtures => incorrect weather "
                "fetch parameters."
            ),
        ),
    ),
    # Injuries (event-time-stamped per CLAUDE.md "available_at is per-row,
    # write-time" rule) REQUIRES teams-current-season AND fixtures rolling
    # window. Injuries belong to a player; player belongs to a team; without
    # a fresh team roster the injury report can't be normalised. The rolling
    # fixtures window catches fixture-events that derive injuries.
    (MarketAssetGroup.SPORTS, "injuries"): (
        PreflightRequirement(
            upstream_entity_type="teams",
            max_staleness_seconds=_7D_SECONDS,
            rationale=(
                "Injury normalisation joins player_id => team_id; stale team "
                "roster => orphan injury rows that downstream features-* drop."
            ),
        ),
        PreflightRequirement(
            upstream_entity_type="fixtures",
            max_staleness_seconds=_36H_SECONDS,
            rationale=(
                "Injuries from fixture_events stream require a fresh rolling-window "
                "fixtures shard so the injury event_time can be tied to the right "
                "fixture context (home/away, kickoff time)."
            ),
        ),
    ),
    # Fixtures daily re-poll itself has no preflight upstream — it IS the
    # rolling-window source. Empty tuple = no-deps, validator returns OK.
    (MarketAssetGroup.SPORTS, "fixtures"): (),
    # Teams season-roll: requires the prior season's teams shard as basis
    # for the diff. First-ever-season case is handled by the validator
    # treating "no upstream data" as expected (per CLAUDE.md honest-absence
    # discipline) — the rolling-window check fires for incremental rolls only.
    (MarketAssetGroup.SPORTS, "teams"): (),
    # Player values during transfer-window REQUIRES teams (so player => team
    # joins resolve) AND fixtures (to anchor `available_at` per the value
    # report's publish-day in fixture-context).
    (MarketAssetGroup.SPORTS, "player_values"): (
        PreflightRequirement(
            upstream_entity_type="teams",
            max_staleness_seconds=_7D_SECONDS,
            rationale=(
                "Player value snapshots tie player_id => team_id; stale teams => "
                "orphaned values that downstream feature-cascades drop."
            ),
        ),
        PreflightRequirement(
            upstream_entity_type="fixtures",
            max_staleness_seconds=_36H_SECONDS,
            rationale=(
                "Player values are stamped with `available_at = transfer_report_publish_time`; "
                "the rolling-window fixtures shard provides the anchor calendar for the "
                "rate-of-change features that consume player_values."
            ),
        ),
    ),
    # ── CeFi ──────────────────────────────────────────────────────────────
    # CeFi 15-min OHLCV REQUIRES the instrument-catalog not older than 24h.
    # The catalog tells us which instruments are alive on the day; without
    # a fresh catalog we'd either fetch delisted instruments (rate-limit
    # waste) or miss freshly-listed ones (data gap).
    (MarketAssetGroup.CEFI, "ohlcv_15m"): (
        PreflightRequirement(
            upstream_entity_type="instrument-catalog",
            max_staleness_seconds=_24H_SECONDS,
            rationale=(
                "Per CLAUDE.md catalog-aware write-gate: CeFi 15-min OHLCV must "
                "fetch the cross-product (catalog x time-shards). Stale catalog => "
                "fetching delisted instruments (waste) or missing newly-listed "
                "instruments (silent gap)."
            ),
        ),
    ),
    # ── TradFi ────────────────────────────────────────────────────────────
    # TradFi 15-min OHLCV: same catalog-freshness rule as CeFi. The calendar
    # axis (HOLIDAY / WEEKEND / PARTIAL_HALF_DAY) is checked separately by
    # `venue_trading_calendar` — that's structural, not staleness.
    (MarketAssetGroup.TRADFI, "ohlcv_15m"): (
        PreflightRequirement(
            upstream_entity_type="instrument-catalog",
            max_staleness_seconds=_24H_SECONDS,
            rationale=(
                "TradFi 15-min OHLCV needs the active-instrument catalog fresh for "
                "the fetch-day cross-product. Calendar pre-skip handled separately "
                "via venue_trading_calendar; this check is for catalog drift only."
            ),
        ),
    ),
    # ── Prediction ────────────────────────────────────────────────────────
    # Prediction market-discovery REQUIRES the canonical_question_group SSOT.
    # That SSOT lives in UAC (static), not in a manifest — so the staleness
    # check sentinel is `STATIC_SSOT_NO_STALENESS_CHECK`. Validator returns
    # OK for this dependency without probing manifest.
    (MarketAssetGroup.PREDICTION, "prediction_markets"): (
        PreflightRequirement(
            upstream_entity_type="canonical_question_group_registry",
            max_staleness_seconds=STATIC_SSOT_NO_STALENESS_CHECK,
            rationale=(
                "Prediction market_id => canonical_question_group mapping is a "
                "UAC-static SSOT (not a manifest-tracked entity); staleness check "
                "is structurally not applicable. Presence is asserted at import-time "
                "by the UAC registry."
            ),
        ),
    ),
}


# ---------------------------------------------------------------------------
# ManifestReader protocol — minimal surface this module needs from the manifest.
# ---------------------------------------------------------------------------


class ManifestReader(Protocol):
    """Minimum interface the preflight validator needs from a manifest.

    Implementations live in UTL (:mod:`unified_trading_library.manifest_freshness`)
    and per-service adapters; this module declares the contract abstractly so
    UAC has zero runtime dependency on UTL or any service.

    The single method returns the most recent ``attempted_at`` for the
    ``(asset_group, entity_type, on_date)`` shard, OR ``None`` if no row
    exists in the upstream manifest. The validator interprets ``None`` as
    "missing entirely" and stamps :class:`MissingDependency` with
    ``actual_age_seconds=None``.
    """

    def get_last_attempted_at(
        self,
        asset_group: MarketAssetGroup,
        upstream_entity_type: str,
        on_date: _date,
    ) -> datetime | None:
        """Most recent ``attempted_at`` for the upstream shard, or ``None``."""
        ...


# ---------------------------------------------------------------------------
# PreflightResult — frozen sum-type returned by the validator.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PreflightOK:
    """Preflight passed — every required upstream is fresh.

    Attributes:
        trigger_name: Name of the trigger that was validated.
        asset_group: Asset group of the trigger.
        on_date: Date the validation was performed for.
        checked_at: UTC timestamp when the validation completed.
    """

    trigger_name: str
    asset_group: MarketAssetGroup
    on_date: _date
    checked_at: datetime


@dataclass(frozen=True)
class PreflightFailed:
    """Preflight failed — at least one required upstream is missing or stale.

    Attributes:
        trigger_name: Name of the trigger that was validated.
        asset_group: Asset group of the trigger.
        on_date: Date the validation was performed for.
        checked_at: UTC timestamp when the validation completed.
        missing: One :class:`MissingDependency` per failed upstream — used
            verbatim by the UTL helper to populate the
            :class:`InstrumentsLivePreflightFailedDetails` event payload.
            Guaranteed non-empty (a ``Failed`` with no missing-deps would
            be a contract violation; the validator returns ``OK`` in that
            case instead).
    """

    trigger_name: str
    asset_group: MarketAssetGroup
    on_date: _date
    checked_at: datetime
    missing: tuple[MissingDependency, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.missing:
            raise ValueError(
                "PreflightFailed.missing must be non-empty — a failure with no "
                "missing-deps is a contract violation. Return PreflightOK instead."
            )


# Discriminated-union alias — every consumer pattern-matches on isinstance.
PreflightResult = PreflightOK | PreflightFailed


# ---------------------------------------------------------------------------
# Public helpers.
# ---------------------------------------------------------------------------


def get_preflight_requirements(
    asset_group: MarketAssetGroup,
    downstream_entity: str,
) -> tuple[PreflightRequirement, ...]:
    """Return the upstream-required graph for one (asset_group, downstream_entity).

    Args:
        asset_group: The asset group axis (cefi / defi / tradfi / sports /
            prediction).
        downstream_entity: Entity-type name produced by the trigger
            (e.g. ``"lineups"``, ``"ohlcv_15m"``).

    Returns:
        Tuple of :class:`PreflightRequirement` — empty when the downstream
        entity has no upstream dependencies (legitimate, e.g.
        ``(SPORTS, "fixtures")`` is a root entity).

    Raises:
        KeyError: If ``(asset_group, downstream_entity)`` is not in the
            DAG SSOT. Adding a new downstream entity requires seeding it
            here AND in :data:`TRIGGER_TO_DOWNSTREAM_ENTITY`.
    """
    return INSTRUMENTS_PREFLIGHT_REQUIREMENTS[(asset_group, downstream_entity)]


def get_trigger_definition(trigger_name: str) -> tuple[PreflightTrigger, str]:
    """Resolve a trigger name to its (PreflightTrigger, downstream_entity) pair.

    Args:
        trigger_name: String form of a :class:`PreflightTrigger` enum value.

    Returns:
        Tuple ``(trigger_enum, downstream_entity)`` — the trigger's
        produced entity-type, used to look up requirements in the DAG.

    Raises:
        KeyError: If ``trigger_name`` is not a known trigger.
    """
    trigger = PreflightTrigger(trigger_name)
    downstream = TRIGGER_TO_DOWNSTREAM_ENTITY[trigger]
    return trigger, downstream


def validate_preflight_for_trigger(
    trigger_name: str,
    asset_group: MarketAssetGroup,
    on_date: _date,
    manifest_reader: ManifestReader,
    *,
    now: datetime | None = None,
) -> PreflightResult:
    """Validate that every upstream of a downstream trigger is fresh.

    Args:
        trigger_name: String form of a :class:`PreflightTrigger`.
        asset_group: Asset group axis the trigger belongs to.
        on_date: Date the trigger is firing for. For sports lineups /
            weather, this is the *fixture day* — the manifest reader is
            asked for the fixture-day shard's freshness, NOT today's.
        manifest_reader: Implements :class:`ManifestReader`. UTL ships
            the canonical implementation; tests inject fakes.
        now: Override "current time" for deterministic tests. Defaults
            to ``datetime.now(timezone.utc)``.

    Returns:
        :class:`PreflightOK` when every required upstream is fresh
        (or the entity has no requirements). :class:`PreflightFailed`
        when at least one upstream is missing or stale; the
        ``missing`` tuple lists every failed dependency so the caller
        can emit a single ``INSTRUMENTS_LIVE_PREFLIGHT_FAILED`` event
        with full detail.

    Raises:
        KeyError: If ``trigger_name`` is unknown OR the
            ``(asset_group, downstream_entity)`` pair is missing from
            the DAG SSOT.
    """
    checked_at = now if now is not None else datetime.now(tz=UTC)
    _trigger, downstream = get_trigger_definition(trigger_name)
    requirements = get_preflight_requirements(asset_group, downstream)

    # No requirements => OK by construction (root entity in the DAG).
    if not requirements:
        return PreflightOK(
            trigger_name=trigger_name,
            asset_group=asset_group,
            on_date=on_date,
            checked_at=checked_at,
        )

    # Lazy-import `MissingDependency` to avoid the circular-import cycle
    # `canonical/__init__.py` → `crosscutting/__init__.py` → this module
    # → `internal.events` → `internal.alerting/__init__.py` → top-level UAC.
    from unified_api_contracts.internal.events import MissingDependency as _MissingDependency

    missing_list: list[MissingDependency] = []

    for req in requirements:
        # UAC-static SSOTs are skipped — they have no manifest row to probe;
        # presence is asserted at UAC import-time. Per the dataclass docs,
        # max_staleness_seconds == STATIC_SSOT_NO_STALENESS_CHECK signals this.
        if req.max_staleness_seconds == STATIC_SSOT_NO_STALENESS_CHECK:
            continue

        last_seen = manifest_reader.get_last_attempted_at(
            asset_group=asset_group,
            upstream_entity_type=req.upstream_entity_type,
            on_date=on_date,
        )

        if last_seen is None:
            # Missing entirely — no row in upstream manifest.
            missing_list.append(
                _MissingDependency(
                    entity_type=req.upstream_entity_type,
                    expected_max_age_seconds=req.max_staleness_seconds,
                    actual_age_seconds=None,
                    last_seen_at=None,
                )
            )
            continue

        # Present — compare ages. Coerce naive datetimes to UTC for the diff.
        last_seen_utc = last_seen if last_seen.tzinfo is not None else last_seen.replace(tzinfo=UTC)
        actual_age = int((checked_at - last_seen_utc).total_seconds())

        if actual_age > req.max_staleness_seconds:
            missing_list.append(
                _MissingDependency(
                    entity_type=req.upstream_entity_type,
                    expected_max_age_seconds=req.max_staleness_seconds,
                    actual_age_seconds=actual_age,
                    last_seen_at=last_seen_utc,
                )
            )

    if missing_list:
        return PreflightFailed(
            trigger_name=trigger_name,
            asset_group=asset_group,
            on_date=on_date,
            checked_at=checked_at,
            missing=tuple(missing_list),
        )

    return PreflightOK(
        trigger_name=trigger_name,
        asset_group=asset_group,
        on_date=on_date,
        checked_at=checked_at,
    )
