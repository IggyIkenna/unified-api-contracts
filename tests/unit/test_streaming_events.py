"""Unit tests for ``unified_api_contracts.events.streaming``.

Plan: ``live_pipeline_mtds_mdps_features_2026_05_08`` Phase 1.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from unified_api_contracts.canonical.crosscutting.service_emission_policy import (
    ServiceEmissionPolicy,
)
from unified_api_contracts.canonical.gcs_paths import AssetGroup
from unified_api_contracts.events.streaming import (
    CandleBoundaryCrossedEvent,
    CandleComputedEvent,
    FeaturesComputedEvent,
    InstrumentCacheRefreshTriggerEvent,
    parse_timeframe,
)
from unified_api_contracts.internal.domain.market_data_processing.candle_schema import (
    DataType,
)

_UTC_PERIOD_START = datetime(2026, 5, 8, 12, 0, 0, tzinfo=UTC)


def _boundary_event(timeframe: str) -> CandleBoundaryCrossedEvent:
    period_end = _UTC_PERIOD_START + parse_timeframe(timeframe)
    return CandleBoundaryCrossedEvent(
        asset_group=AssetGroup.CEFI,
        venue="binance",
        instrument_id="BTC-USDT",
        data_type=DataType.OHLCV_1M,
        timeframe=timeframe,
        period_start=_UTC_PERIOD_START,
        period_end=period_end,
        tick_count=42,
        available_at=period_end + timedelta(seconds=1),
        correlation_id="corr-123",
        vm_name="cefi-binance-spot-20260508-120000",
    )


def _computed_event(
    *,
    data_freshness: str = "FRESH",
    emission_policy: ServiceEmissionPolicy = ServiceEmissionPolicy.STRICT_FAIL,
    emission_outcome: str = "PUBLISHED_OK",
) -> CandleComputedEvent:
    period_end = _UTC_PERIOD_START + parse_timeframe("1m")
    return CandleComputedEvent(
        asset_group=AssetGroup.CEFI,
        venue="binance",
        instrument_id="BTC-USDT",
        data_type=DataType.OHLCV_1M,
        timeframe="1m",
        period_start=_UTC_PERIOD_START,
        period_end=period_end,
        row_count=1,
        available_at=period_end + timedelta(seconds=2),
        data_freshness=data_freshness,  # type: ignore[arg-type]
        emission_policy=emission_policy,
        emission_outcome=emission_outcome,  # type: ignore[arg-type]
        correlation_id="corr-123",
        vm_name="mdps-cefi-20260508-120000",
    )


def _features_computed_event(
    *,
    feature_family: str = "delta_one",
    feature_group: str = "delta_one.spot_mom_15s",
    data_freshness: str = "FRESH",
    emission_policy: ServiceEmissionPolicy = ServiceEmissionPolicy.STRICT_FAIL,
    emission_outcome: str = "PUBLISHED_OK",
) -> FeaturesComputedEvent:
    period_end = _UTC_PERIOD_START + parse_timeframe("1m")
    return FeaturesComputedEvent(
        asset_group=AssetGroup.CEFI,
        feature_family=feature_family,
        feature_group=feature_group,
        venue="binance",
        instrument_id="BTC-USDT",
        data_type=DataType.OHLCV_1M,
        timeframe="1m",
        period_start=_UTC_PERIOD_START,
        period_end=period_end,
        row_count=1,
        available_at=period_end + timedelta(seconds=3),
        data_freshness=data_freshness,  # type: ignore[arg-type]
        emission_policy=emission_policy,
        emission_outcome=emission_outcome,  # type: ignore[arg-type]
        correlation_id="corr-123",
        vm_name="features-cefi-20260508-120000",
    )


def _instrument_cache_event() -> InstrumentCacheRefreshTriggerEvent:
    return InstrumentCacheRefreshTriggerEvent(
        asset_group=AssetGroup.DEFI,
        catalog_refresh_at=_UTC_PERIOD_START,
        row_count_total=12_345,
        row_count_added_since_last=7,
        row_count_removed_since_last=2,
        correlation_id="corr-456",
        vm_name="instr-discovery-20260508-120000",
    )


# ---------------------------------------------------------------------------
# Test 1 — JSON serialization round-trip for all 3 events.
# ---------------------------------------------------------------------------


def test_candle_boundary_crossed_round_trip() -> None:
    original = _boundary_event("1m")
    payload = original.model_dump_json()
    restored = CandleBoundaryCrossedEvent.model_validate_json(payload)
    assert restored == original
    assert restored.event_type == "CANDLE_BOUNDARY_CROSSED"


def test_candle_computed_round_trip() -> None:
    original = _computed_event()
    payload = original.model_dump_json()
    restored = CandleComputedEvent.model_validate_json(payload)
    assert restored == original
    assert restored.event_type == "CANDLE_COMPUTED"


def test_instrument_cache_refresh_trigger_round_trip() -> None:
    original = _instrument_cache_event()
    payload = original.model_dump_json()
    restored = InstrumentCacheRefreshTriggerEvent.model_validate_json(payload)
    assert restored == original
    assert restored.event_type == "INSTRUMENT_CACHE_REFRESH_TRIGGER"


def test_features_computed_round_trip() -> None:
    original = _features_computed_event()
    payload = original.model_dump_json()
    restored = FeaturesComputedEvent.model_validate_json(payload)
    assert restored == original
    assert restored.event_type == "FEATURES_COMPUTED"


def test_features_computed_cross_instrument_no_shard_fields() -> None:
    """Cross-instrument family may omit per-shard fields (venue / chain / ...)."""
    period_end = _UTC_PERIOD_START + parse_timeframe("1m")
    event = FeaturesComputedEvent(
        asset_group=AssetGroup.CEFI,
        feature_family="cross_instrument",
        feature_group="cross_instrument.perp_funding_vs_spot_basis",
        timeframe="1m",
        period_start=_UTC_PERIOD_START,
        period_end=period_end,
        row_count=4,
        available_at=period_end + timedelta(seconds=3),
        correlation_id="corr-xc",
        vm_name="features-xc-20260508-120000",
    )
    assert event.venue is None
    assert event.instrument_id is None
    assert event.data_type is None
    assert event.feature_family == "cross_instrument"


def test_features_computed_degraded_propagation_outcome() -> None:
    """``emission_outcome=PUBLISHED_DEGRADED`` carries downstream per Phase 6.2 fan-in rule."""
    degraded = _features_computed_event(
        data_freshness="STALE",
        emission_outcome="PUBLISHED_DEGRADED",
    )
    assert degraded.emission_outcome == "PUBLISHED_DEGRADED"
    assert degraded.data_freshness == "STALE"


# ---------------------------------------------------------------------------
# Test 2 — period_end - period_start == parse_timeframe(timeframe) invariant.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "timeframe",
    ["15s", "1m", "5m", "15m", "1h", "1d"],
)
def test_boundary_event_period_invariant(timeframe: str) -> None:
    event = _boundary_event(timeframe)
    assert event.period_end - event.period_start == parse_timeframe(timeframe)


def test_parse_timeframe_unknown_token_raises() -> None:
    with pytest.raises(ValueError, match="Unknown timeframe token"):
        parse_timeframe("1w")


# ---------------------------------------------------------------------------
# Test 3 — data_freshness closed-set values exactly.
# ---------------------------------------------------------------------------


def test_boundary_event_data_freshness_accepts_closed_set() -> None:
    fresh = _boundary_event("1m")
    assert fresh.data_freshness == "FRESH"
    period_end = _UTC_PERIOD_START + parse_timeframe("1m")
    stale = CandleBoundaryCrossedEvent(
        asset_group=AssetGroup.CEFI,
        venue="binance",
        instrument_id="BTC-USDT",
        data_type=DataType.OHLCV_1M,
        timeframe="1m",
        period_start=_UTC_PERIOD_START,
        period_end=period_end,
        tick_count=10,
        available_at=period_end + timedelta(seconds=1),
        data_freshness="STALE",
        correlation_id="corr-123",
        vm_name="cefi-binance-spot-20260508-120000",
    )
    assert stale.data_freshness == "STALE"


def test_boundary_event_data_freshness_rejects_zero_activity() -> None:
    """ZERO_ACTIVITY_BAR is a CandleComputedEvent value, not boundary-crossed."""

    period_end = _UTC_PERIOD_START + parse_timeframe("1m")
    with pytest.raises(ValueError):
        CandleBoundaryCrossedEvent(
            asset_group=AssetGroup.CEFI,
            venue="binance",
            instrument_id="BTC-USDT",
            data_type=DataType.OHLCV_1M,
            timeframe="1m",
            period_start=_UTC_PERIOD_START,
            period_end=period_end,
            tick_count=0,
            available_at=period_end + timedelta(seconds=1),
            data_freshness="ZERO_ACTIVITY_BAR",  # type: ignore[arg-type]
            correlation_id="corr-123",
            vm_name="cefi-binance-spot-20260508-120000",
        )


def test_computed_event_data_freshness_accepts_zero_activity() -> None:
    event = _computed_event(data_freshness="ZERO_ACTIVITY_BAR")
    assert event.data_freshness == "ZERO_ACTIVITY_BAR"


def test_computed_event_data_freshness_rejects_unknown() -> None:
    with pytest.raises(ValueError):
        _computed_event(data_freshness="MIXED")


# ---------------------------------------------------------------------------
# Test 4 — emission_outcome defaults to PUBLISHED_OK.
# (emission_policy SSOT default is STRICT_FAIL — we verify both defaults.)
# ---------------------------------------------------------------------------


def test_computed_event_emission_outcome_defaults_to_published_ok() -> None:
    period_end = _UTC_PERIOD_START + parse_timeframe("1m")
    event = CandleComputedEvent(
        asset_group=AssetGroup.CEFI,
        venue="binance",
        instrument_id="BTC-USDT",
        data_type=DataType.OHLCV_1M,
        timeframe="1m",
        period_start=_UTC_PERIOD_START,
        period_end=period_end,
        row_count=1,
        available_at=period_end + timedelta(seconds=2),
        correlation_id="corr-123",
        vm_name="mdps-cefi-20260508-120000",
    )
    assert event.emission_outcome == "PUBLISHED_OK"
    assert event.emission_policy == ServiceEmissionPolicy.STRICT_FAIL
    assert event.data_freshness == "FRESH"


def test_computed_event_emission_outcome_closed_set() -> None:
    for outcome in ("PUBLISHED_OK", "PUBLISHED_DEGRADED", "STALE_DATA", "BLOCKED"):
        event = _computed_event(emission_outcome=outcome)
        assert event.emission_outcome == outcome
    with pytest.raises(ValueError):
        _computed_event(emission_outcome="UNKNOWN")


# ---------------------------------------------------------------------------
# pipeline_mode defaulting to None (producer-unset metadata) on all event types.
# ---------------------------------------------------------------------------


def test_pipeline_mode_defaults_to_none() -> None:
    assert _boundary_event("1m").pipeline_mode is None
    assert _computed_event().pipeline_mode is None
    assert _instrument_cache_event().pipeline_mode is None
