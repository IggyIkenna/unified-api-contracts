"""Unit tests for the instruments-live preflight-chain SSOT.

Covers Phase A.9 — the upstream-required-before-downstream DAG SSOT,
:class:`PreflightTrigger` taxonomy, :data:`INSTRUMENTS_PREFLIGHT_REQUIREMENTS`
seed, and the :func:`validate_preflight_for_trigger` helper's per-asset-group
behaviour (sports lineups / weather / injuries / fixtures / teams / player
values, cefi 15m, tradfi 15m, prediction market-discovery).

Plan: ``plans/epics/instruments_master.md`` § Phase A.9.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, date, datetime, timedelta

import pytest

from unified_api_contracts.canonical.crosscutting.instruments_preflight_dag import (
    INSTRUMENTS_PREFLIGHT_REQUIREMENTS,
    STATIC_SSOT_NO_STALENESS_CHECK,
    TRIGGER_TO_DOWNSTREAM_ENTITY,
    PreflightFailed,
    PreflightOK,
    PreflightRequirement,
    PreflightTrigger,
    get_preflight_requirements,
    get_trigger_definition,
    validate_preflight_for_trigger,
)
from unified_api_contracts.canonical.gcs_paths import AssetGroup as MarketAssetGroup

# ---------------------------------------------------------------------------
# Test ManifestReader fake — last_seen_at injected per (asset_group, entity, date).
# ---------------------------------------------------------------------------


class _FakeManifestReader:
    """In-memory ManifestReader for deterministic tests."""

    def __init__(
        self,
        seed: Mapping[tuple[MarketAssetGroup, str, date], datetime | None] | None = None,
    ) -> None:
        self._seed: dict[tuple[MarketAssetGroup, str, date], datetime | None] = dict(seed or {})

    def set(
        self,
        asset_group: MarketAssetGroup,
        upstream_entity_type: str,
        on_date: date,
        last_seen: datetime | None,
    ) -> None:
        self._seed[(asset_group, upstream_entity_type, on_date)] = last_seen

    def get_last_attempted_at(
        self,
        asset_group: MarketAssetGroup,
        upstream_entity_type: str,
        on_date: date,
    ) -> datetime | None:
        return self._seed.get((asset_group, upstream_entity_type, on_date), None)


_FIXTURE_DAY: date = date(2026, 5, 15)
_NOW: datetime = datetime(2026, 5, 15, 12, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Trigger taxonomy + DAG-shape integrity.
# ---------------------------------------------------------------------------


def test_every_trigger_resolves_to_a_downstream_entity() -> None:
    """Every PreflightTrigger MUST appear in TRIGGER_TO_DOWNSTREAM_ENTITY."""
    for trigger in PreflightTrigger:
        assert trigger in TRIGGER_TO_DOWNSTREAM_ENTITY, f"missing mapping for {trigger}"


def test_every_trigger_downstream_pair_has_a_dag_entry() -> None:
    """Every (asset_group, downstream_entity) reachable via a trigger MUST be in the DAG."""
    for trigger, downstream in TRIGGER_TO_DOWNSTREAM_ENTITY.items():
        # Infer asset_group from the trigger name prefix — closed set.
        if trigger.value.startswith("sports_"):
            asset_group = MarketAssetGroup.SPORTS
        elif trigger.value.startswith("cefi_"):
            asset_group = MarketAssetGroup.CEFI
        elif trigger.value.startswith("tradfi_"):
            asset_group = MarketAssetGroup.TRADFI
        elif trigger.value.startswith("prediction_"):
            asset_group = MarketAssetGroup.PREDICTION
        else:
            pytest.fail(f"trigger {trigger} has no asset_group prefix")
        assert (asset_group, downstream) in INSTRUMENTS_PREFLIGHT_REQUIREMENTS, (
            f"DAG missing entry for ({asset_group}, {downstream})"
        )


def test_get_trigger_definition_round_trip() -> None:
    trigger, downstream = get_trigger_definition("sports_lineups_kickoff_minus_60m")
    assert trigger is PreflightTrigger.SPORTS_LINEUPS_KICKOFF_MINUS_60M
    assert downstream == "lineups"


def test_get_trigger_definition_unknown_raises() -> None:
    with pytest.raises(ValueError):
        get_trigger_definition("not-a-real-trigger")


# ---------------------------------------------------------------------------
# Per-asset-group dependency-rule shape — declarative assertions.
# ---------------------------------------------------------------------------


def test_sports_lineups_requires_fixtures_with_24h_tolerance() -> None:
    reqs = get_preflight_requirements(MarketAssetGroup.SPORTS, "lineups")
    assert len(reqs) == 1
    assert reqs[0].upstream_entity_type == "fixtures"
    assert reqs[0].max_staleness_seconds == 24 * 3600


def test_sports_weather_requires_fixtures_with_24h_tolerance() -> None:
    reqs = get_preflight_requirements(MarketAssetGroup.SPORTS, "weather_forecast")
    assert len(reqs) == 1
    assert reqs[0].upstream_entity_type == "fixtures"
    assert reqs[0].max_staleness_seconds == 24 * 3600


def test_sports_injuries_requires_teams_and_fixtures() -> None:
    reqs = get_preflight_requirements(MarketAssetGroup.SPORTS, "injuries")
    upstream_types = {r.upstream_entity_type for r in reqs}
    assert upstream_types == {"teams", "fixtures"}


def test_sports_player_values_requires_teams_and_fixtures() -> None:
    reqs = get_preflight_requirements(MarketAssetGroup.SPORTS, "player_values")
    upstream_types = {r.upstream_entity_type for r in reqs}
    assert upstream_types == {"teams", "fixtures"}


def test_sports_fixtures_has_no_upstream() -> None:
    """Fixtures is a root entity — no preflight upstream."""
    reqs = get_preflight_requirements(MarketAssetGroup.SPORTS, "fixtures")
    assert reqs == ()


def test_sports_teams_has_no_upstream() -> None:
    """Teams is a root entity — no preflight upstream."""
    reqs = get_preflight_requirements(MarketAssetGroup.SPORTS, "teams")
    assert reqs == ()


def test_cefi_ohlcv_15m_requires_instrument_catalog_24h() -> None:
    reqs = get_preflight_requirements(MarketAssetGroup.CEFI, "ohlcv_15m")
    assert len(reqs) == 1
    assert reqs[0].upstream_entity_type == "instrument-catalog"
    assert reqs[0].max_staleness_seconds == 24 * 3600


def test_tradfi_ohlcv_15m_requires_instrument_catalog_24h() -> None:
    reqs = get_preflight_requirements(MarketAssetGroup.TRADFI, "ohlcv_15m")
    assert len(reqs) == 1
    assert reqs[0].upstream_entity_type == "instrument-catalog"
    assert reqs[0].max_staleness_seconds == 24 * 3600


def test_prediction_market_discovery_uses_static_ssot_sentinel() -> None:
    """Prediction market-discovery requires a UAC-static SSOT — staleness check skipped."""
    reqs = get_preflight_requirements(MarketAssetGroup.PREDICTION, "prediction_markets")
    assert len(reqs) == 1
    assert reqs[0].upstream_entity_type == "canonical_question_group_registry"
    assert reqs[0].max_staleness_seconds == STATIC_SSOT_NO_STALENESS_CHECK


# ---------------------------------------------------------------------------
# validate_preflight_for_trigger — success paths.
# ---------------------------------------------------------------------------


def test_validate_returns_ok_when_no_upstream_requirements() -> None:
    """Root entities (fixtures / teams) always pass preflight."""
    reader = _FakeManifestReader()
    result = validate_preflight_for_trigger(
        trigger_name=PreflightTrigger.SPORTS_FIXTURES_DAILY_REPOLL.value,
        asset_group=MarketAssetGroup.SPORTS,
        on_date=_FIXTURE_DAY,
        manifest_reader=reader,
        now=_NOW,
    )
    assert isinstance(result, PreflightOK)
    assert result.trigger_name == "sports_fixtures_daily_repoll"


def test_validate_returns_ok_when_upstream_is_fresh() -> None:
    """CeFi 15m: catalog last seen 1h ago, within 24h tolerance => OK."""
    reader = _FakeManifestReader()
    reader.set(
        asset_group=MarketAssetGroup.CEFI,
        upstream_entity_type="instrument-catalog",
        on_date=_FIXTURE_DAY,
        last_seen=_NOW - timedelta(hours=1),
    )
    result = validate_preflight_for_trigger(
        trigger_name=PreflightTrigger.CEFI_OHLCV_15M_REFRESH.value,
        asset_group=MarketAssetGroup.CEFI,
        on_date=_FIXTURE_DAY,
        manifest_reader=reader,
        now=_NOW,
    )
    assert isinstance(result, PreflightOK)


def test_validate_returns_ok_for_static_ssot_dependency() -> None:
    """Prediction market-discovery: static-SSOT sentinel => OK without manifest probe."""
    # Reader is empty — but the static-SSOT short-circuit bypasses it.
    reader = _FakeManifestReader()
    result = validate_preflight_for_trigger(
        trigger_name=PreflightTrigger.PREDICTION_MARKET_DISCOVERY.value,
        asset_group=MarketAssetGroup.PREDICTION,
        on_date=_FIXTURE_DAY,
        manifest_reader=reader,
        now=_NOW,
    )
    assert isinstance(result, PreflightOK)


# ---------------------------------------------------------------------------
# validate_preflight_for_trigger — failure paths.
# ---------------------------------------------------------------------------


def test_validate_returns_failed_when_upstream_missing() -> None:
    """Sports lineups: fixture-day fixtures shard is missing => FAILED."""
    reader = _FakeManifestReader()  # empty — fixtures missing
    result = validate_preflight_for_trigger(
        trigger_name=PreflightTrigger.SPORTS_LINEUPS_KICKOFF_MINUS_60M.value,
        asset_group=MarketAssetGroup.SPORTS,
        on_date=_FIXTURE_DAY,
        manifest_reader=reader,
        now=_NOW,
    )
    assert isinstance(result, PreflightFailed)
    assert len(result.missing) == 1
    dep = result.missing[0]
    assert dep.entity_type == "fixtures"
    assert dep.actual_age_seconds is None
    assert dep.last_seen_at is None


def test_validate_returns_failed_when_upstream_is_stale() -> None:
    """CeFi 15m: catalog last seen 30h ago, 24h tolerance => FAILED."""
    reader = _FakeManifestReader()
    last_seen = _NOW - timedelta(hours=30)
    reader.set(
        asset_group=MarketAssetGroup.CEFI,
        upstream_entity_type="instrument-catalog",
        on_date=_FIXTURE_DAY,
        last_seen=last_seen,
    )
    result = validate_preflight_for_trigger(
        trigger_name=PreflightTrigger.CEFI_OHLCV_15M_REFRESH.value,
        asset_group=MarketAssetGroup.CEFI,
        on_date=_FIXTURE_DAY,
        manifest_reader=reader,
        now=_NOW,
    )
    assert isinstance(result, PreflightFailed)
    assert len(result.missing) == 1
    dep = result.missing[0]
    assert dep.entity_type == "instrument-catalog"
    assert dep.actual_age_seconds is not None
    assert dep.actual_age_seconds == int(timedelta(hours=30).total_seconds())
    assert dep.last_seen_at == last_seen


def test_validate_aggregates_multiple_missing_deps() -> None:
    """Sports injuries: BOTH teams (stale) AND fixtures (missing) => one FAILED w/ both deps."""
    reader = _FakeManifestReader()
    # Teams stale beyond 7d.
    reader.set(
        asset_group=MarketAssetGroup.SPORTS,
        upstream_entity_type="teams",
        on_date=_FIXTURE_DAY,
        last_seen=_NOW - timedelta(days=10),
    )
    # Fixtures missing entirely.
    result = validate_preflight_for_trigger(
        trigger_name=PreflightTrigger.SPORTS_INJURIES_DAILY_REPOLL.value,
        asset_group=MarketAssetGroup.SPORTS,
        on_date=_FIXTURE_DAY,
        manifest_reader=reader,
        now=_NOW,
    )
    assert isinstance(result, PreflightFailed)
    assert len(result.missing) == 2
    by_entity = {d.entity_type: d for d in result.missing}
    assert "teams" in by_entity
    assert "fixtures" in by_entity
    assert by_entity["teams"].actual_age_seconds is not None  # stale
    assert by_entity["fixtures"].actual_age_seconds is None  # missing


def test_validate_aggregates_partial_failure_when_one_upstream_ok() -> None:
    """Player values: teams fresh (OK), fixtures missing => FAILED with only fixtures listed."""
    reader = _FakeManifestReader()
    reader.set(
        asset_group=MarketAssetGroup.SPORTS,
        upstream_entity_type="teams",
        on_date=_FIXTURE_DAY,
        last_seen=_NOW - timedelta(hours=1),  # fresh
    )
    # fixtures absent.
    result = validate_preflight_for_trigger(
        trigger_name=PreflightTrigger.SPORTS_PLAYER_VALUES_TRANSFER_WINDOW.value,
        asset_group=MarketAssetGroup.SPORTS,
        on_date=_FIXTURE_DAY,
        manifest_reader=reader,
        now=_NOW,
    )
    assert isinstance(result, PreflightFailed)
    assert len(result.missing) == 1
    assert result.missing[0].entity_type == "fixtures"


def test_preflight_failed_rejects_empty_missing_tuple() -> None:
    """Constructing PreflightFailed with empty missing-deps is a contract violation."""
    with pytest.raises(ValueError):
        PreflightFailed(
            trigger_name="x",
            asset_group=MarketAssetGroup.CEFI,
            on_date=_FIXTURE_DAY,
            checked_at=_NOW,
            missing=(),
        )


def test_validate_handles_naive_datetime_from_manifest() -> None:
    """Manifest may return naive datetimes; validator coerces to UTC for the diff."""
    reader = _FakeManifestReader()
    naive_last_seen = (_NOW - timedelta(hours=2)).replace(tzinfo=None)
    reader.set(
        asset_group=MarketAssetGroup.TRADFI,
        upstream_entity_type="instrument-catalog",
        on_date=_FIXTURE_DAY,
        last_seen=naive_last_seen,
    )
    result = validate_preflight_for_trigger(
        trigger_name=PreflightTrigger.TRADFI_OHLCV_15M_REFRESH.value,
        asset_group=MarketAssetGroup.TRADFI,
        on_date=_FIXTURE_DAY,
        manifest_reader=reader,
        now=_NOW,
    )
    assert isinstance(result, PreflightOK)


def test_preflight_requirement_is_frozen() -> None:
    """PreflightRequirement is a frozen dataclass — defensive against accidental mutation."""
    req = PreflightRequirement(
        upstream_entity_type="x",
        max_staleness_seconds=60,
        rationale="test",
    )
    with pytest.raises((AttributeError, Exception)):  # frozen=True raises FrozenInstanceError
        req.max_staleness_seconds = 120  # type: ignore[misc]
