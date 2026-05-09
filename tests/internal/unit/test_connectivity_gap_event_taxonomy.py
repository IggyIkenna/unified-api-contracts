"""Tests for live-mode connectivity-gap event taxonomy.

Phase 1 of ``mdps_streaming_and_backpressure_2026_05_07.md`` ("Migrated
issue 2026-05-08 — Live data recovery self-detect") — adds 3 typed
``LifecycleEventType`` members + 3 Pydantic detail models + 3 typed
event wrappers for the MTDS ``LiveConnectivityWatchdog`` 3-event family.

Per CLAUDE.md "Live = batch — same data, same fields, same timing
semantics, different sources OK" — the 4-state capture taxonomy in batch
mode (``captured`` / ``empty_confirmed`` / ``attempted_failed`` /
``expected_unattempted``) needs an upstream-detected counterpart in live
mode for connectivity outages. This event family is what
``LiveConnectivityWatchdog`` emits per (venue, data_type) heartbeat
state transitions; downstream consumers (alerting-service rule engine,
auto-backfill loop, manifest reconciler) read these events to keep
live-mode capture honest.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from unified_api_contracts.internal.events import (
    ConnectivityGapBackfilledDetails,
    ConnectivityGapBackfilledEvent,
    ConnectivityGapDetectedDetails,
    ConnectivityGapDetectedEvent,
    ConnectivityRecoveredDetails,
    ConnectivityRecoveredEvent,
    LifecycleEventType,
)

# ═══════════════════════════════════════════════════════════════════════════
# Enum-member existence + closed-set membership
# ═══════════════════════════════════════════════════════════════════════════


class TestConnectivityGapEventEnumMembers:
    """All 3 connectivity-gap event types exist as valid enum members."""

    def test_gap_detected_exists(self) -> None:
        assert LifecycleEventType.CONNECTIVITY_GAP_DETECTED == "CONNECTIVITY_GAP_DETECTED"

    def test_recovered_exists(self) -> None:
        assert LifecycleEventType.CONNECTIVITY_RECOVERED == "CONNECTIVITY_RECOVERED"

    def test_gap_backfilled_exists(self) -> None:
        assert LifecycleEventType.CONNECTIVITY_GAP_BACKFILLED == "CONNECTIVITY_GAP_BACKFILLED"

    def test_three_members_added(self) -> None:
        """Phase 1 declares exactly 3 new CONNECTIVITY_* members."""
        connectivity_members = {m for m in LifecycleEventType if m.value.startswith("CONNECTIVITY_")}
        assert len(connectivity_members) == 3


# ═══════════════════════════════════════════════════════════════════════════
# CONNECTIVITY_GAP_DETECTED detail + event
# ═══════════════════════════════════════════════════════════════════════════


class TestConnectivityGapDetected:
    def test_minimal_construction(self) -> None:
        gap_start = datetime(2026, 5, 9, 12, 0, 0, tzinfo=UTC)
        last_received = datetime(2026, 5, 9, 11, 59, 30, tzinfo=UTC)
        details = ConnectivityGapDetectedDetails(
            venue="BINANCE_FUTURES",
            data_type="trades",
            gap_start=gap_start,
            last_received_at=last_received,
            classification="STALE_HEARTBEAT",
        )
        assert details.venue == "BINANCE_FUTURES"
        assert details.data_type == "trades"
        assert details.classification == "STALE_HEARTBEAT"
        # message_count_during_gap defaults to 0
        assert details.message_count_during_gap == 0

    def test_classification_closed_set_rejects_unknown_values(self) -> None:
        """The Literal classification field must reject typos / unknown classes."""
        with pytest.raises(ValidationError):
            ConnectivityGapDetectedDetails(
                venue="BYBIT",
                data_type="book_snapshot_5",
                gap_start=datetime(2026, 5, 9, 12, 0, 0, tzinfo=UTC),
                last_received_at=datetime(2026, 5, 9, 11, 59, 30, tzinfo=UTC),
                classification="HEARTBEAT_LATE",  # type: ignore[arg-type]
            )

    def test_event_wrapper_pins_event_type(self) -> None:
        details = ConnectivityGapDetectedDetails(
            venue="OKX",
            data_type="derivative_ticker",
            gap_start=datetime(2026, 5, 9, 12, 0, 0, tzinfo=UTC),
            last_received_at=datetime(2026, 5, 9, 11, 59, 30, tzinfo=UTC),
            classification="WS_DISCONNECT",
        )
        evt = ConnectivityGapDetectedEvent(
            service="market-tick-data-service",
            timestamp=datetime(2026, 5, 9, 12, 0, 0, tzinfo=UTC),
            details=details,
        )
        assert evt.event == LifecycleEventType.CONNECTIVITY_GAP_DETECTED


# ═══════════════════════════════════════════════════════════════════════════
# CONNECTIVITY_RECOVERED detail + event
# ═══════════════════════════════════════════════════════════════════════════


class TestConnectivityRecovered:
    def test_minimal_construction(self) -> None:
        gap_start = datetime(2026, 5, 9, 12, 0, 0, tzinfo=UTC)
        gap_end = datetime(2026, 5, 9, 12, 5, 0, tzinfo=UTC)
        details = ConnectivityRecoveredDetails(
            venue="BINANCE_FUTURES",
            data_type="trades",
            gap_start=gap_start,
            gap_end=gap_end,
            gap_duration_seconds=300.0,
            last_received_at=gap_end,
        )
        assert details.gap_duration_seconds == 300.0
        assert details.gap_start == gap_start

    def test_event_wrapper_pins_event_type(self) -> None:
        gap_end = datetime(2026, 5, 9, 12, 5, 0, tzinfo=UTC)
        details = ConnectivityRecoveredDetails(
            venue="DERIBIT",
            data_type="trades",
            gap_start=datetime(2026, 5, 9, 12, 0, 0, tzinfo=UTC),
            gap_end=gap_end,
            gap_duration_seconds=300.0,
            last_received_at=gap_end,
        )
        evt = ConnectivityRecoveredEvent(
            service="market-tick-data-service",
            timestamp=gap_end,
            details=details,
        )
        assert evt.event == LifecycleEventType.CONNECTIVITY_RECOVERED


# ═══════════════════════════════════════════════════════════════════════════
# CONNECTIVITY_GAP_BACKFILLED detail + event
# ═══════════════════════════════════════════════════════════════════════════


class TestConnectivityGapBackfilled:
    def test_minimal_construction(self) -> None:
        gap_start = datetime(2026, 5, 9, 12, 0, 0, tzinfo=UTC)
        gap_end = datetime(2026, 5, 9, 12, 5, 0, tzinfo=UTC)
        backfilled_at = datetime(2026, 5, 9, 12, 6, 30, tzinfo=UTC)
        details = ConnectivityGapBackfilledDetails(
            venue="HYPERLIQUID",
            data_type="trades",
            gap_start=gap_start,
            gap_end=gap_end,
            backfill_completed_at=backfilled_at,
            rows_backfilled=1542,
        )
        assert details.rows_backfilled == 1542
        assert details.backfill_completed_at == backfilled_at

    def test_event_wrapper_pins_event_type(self) -> None:
        gap_end = datetime(2026, 5, 9, 12, 5, 0, tzinfo=UTC)
        backfilled_at = datetime(2026, 5, 9, 12, 6, 30, tzinfo=UTC)
        details = ConnectivityGapBackfilledDetails(
            venue="ASTER",
            data_type="trades",
            gap_start=datetime(2026, 5, 9, 12, 0, 0, tzinfo=UTC),
            gap_end=gap_end,
            backfill_completed_at=backfilled_at,
            rows_backfilled=320,
        )
        evt = ConnectivityGapBackfilledEvent(
            service="market-tick-data-service",
            timestamp=backfilled_at,
            details=details,
        )
        assert evt.event == LifecycleEventType.CONNECTIVITY_GAP_BACKFILLED


# ═══════════════════════════════════════════════════════════════════════════
# Cross-event consistency
# ═══════════════════════════════════════════════════════════════════════════


class TestConnectivityGapEventFamilyConsistency:
    """Three-event family forms a coherent state-transition lifecycle."""

    def test_all_three_share_venue_and_data_type_axes(self) -> None:
        """The (venue, data_type) pair is the shared shard-axis across all 3 events."""
        # GAP_DETECTED
        detected = ConnectivityGapDetectedDetails(
            venue="BINANCE_FUTURES",
            data_type="trades",
            gap_start=datetime(2026, 5, 9, 12, 0, 0, tzinfo=UTC),
            last_received_at=datetime(2026, 5, 9, 11, 59, 30, tzinfo=UTC),
            classification="STALE_HEARTBEAT",
        )
        # RECOVERED
        recovered = ConnectivityRecoveredDetails(
            venue="BINANCE_FUTURES",
            data_type="trades",
            gap_start=datetime(2026, 5, 9, 12, 0, 0, tzinfo=UTC),
            gap_end=datetime(2026, 5, 9, 12, 5, 0, tzinfo=UTC),
            gap_duration_seconds=300.0,
            last_received_at=datetime(2026, 5, 9, 12, 5, 0, tzinfo=UTC),
        )
        # BACKFILLED
        backfilled = ConnectivityGapBackfilledDetails(
            venue="BINANCE_FUTURES",
            data_type="trades",
            gap_start=datetime(2026, 5, 9, 12, 0, 0, tzinfo=UTC),
            gap_end=datetime(2026, 5, 9, 12, 5, 0, tzinfo=UTC),
            backfill_completed_at=datetime(2026, 5, 9, 12, 6, 30, tzinfo=UTC),
            rows_backfilled=1542,
        )
        assert detected.venue == recovered.venue == backfilled.venue
        assert detected.data_type == recovered.data_type == backfilled.data_type
