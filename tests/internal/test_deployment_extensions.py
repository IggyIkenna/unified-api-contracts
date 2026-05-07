"""Tests for the work-stream-A internal deployment types.

Plan: unified-trading-pm/plans/active/deployment_api_work_stream_a_2026_05_07.plan.md
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from unified_api_contracts.internal import (
    BackfillLaunchRequest,
    BackfillLaunchResult,
    BackfillLaunchTaskKind,
    VMEventListResult,
    VMLifecycleEvent,
)

# ────────────────────────────────────────────────────────────────────────────
# Real-world JSONL fixture captured 2026-05-07 from
# gs://<events-bucket>/events/instruments-service/2026-05-07/
#   af-backfill-20260507-002914/hour=00/1778113506490157_372.jsonl
# Truncated `details.message` for readability — the parse logic is the same.
# ────────────────────────────────────────────────────────────────────────────
SAMPLE_JSONL_ROW: str = json.dumps(
    {
        "event": "SERVICE_ERROR",
        "service": "instruments-service",
        "timestamp": "2026-05-07T00:25:06.490157+00:00",
        "metadata": {
            "timestamp": "2026-05-07T00:25:06.490130+00:00",
            "service_name": "instruments-service",
            "severity": "INFO",
            "details": {
                "error_type": "EnhancedError",
                "message": "429 POST https://...",
                "category": "unknown",
                "severity": "critical",
                "recovery_strategy": "alert",
                "correlation_id": "48583baf-0c72-4147-9049-966151100123",
                "schema_version": "1.0.0",
            },
        },
    }
)


def _parse_jsonl_row(raw: str) -> VMLifecycleEvent:
    """Reference adapter — mirrors the route handler's parse path."""
    parsed = json.loads(raw)
    metadata = parsed.get("metadata", {})
    details_raw = metadata.get("details", {})
    # Severity preference: top-level metadata.severity > details.severity > INFO
    severity = str(metadata.get("severity", details_raw.get("severity", "INFO"))).upper()
    correlation_id = details_raw.get("correlation_id") if isinstance(details_raw, dict) else None
    details_str: dict[str, str] = {}
    if isinstance(details_raw, dict):
        for k, v in details_raw.items():
            if isinstance(v, (str, int, float, bool)):
                details_str[str(k)] = str(v)
    return VMLifecycleEvent(
        event=str(parsed["event"]),
        service=str(parsed["service"]),
        timestamp=datetime.fromisoformat(str(parsed["timestamp"])),
        severity=severity,
        correlation_id=str(correlation_id) if correlation_id else None,
        details=details_str,
        raw_metadata=metadata if isinstance(metadata, dict) else {},
    )


# ────────────────────────────────────────────────────────────────────────────
# BackfillLaunchTaskKind enum
# ────────────────────────────────────────────────────────────────────────────


class TestBackfillLaunchTaskKind:
    def test_required_tasks_present(self) -> None:
        # Every task referenced in the plan's Phase 1 spec must be defined.
        required = {
            "cefi_backfill",
            "cefi_forward_poll",
            "tradfi_backfill",
            "tradfi_forward_poll",
            "defi_forward_poll",
            "prediction_forward_poll",
            "sports_forward_poll",
            "af_backfill",
            "footystats_backfill",
            "sfi_backfill",
            "understat_backfill",
            "transfermarkt_backfill",
            "openmeteo_backfill",
            "mtds_prediction_backfill",
            "mtds_perp_funding_backfill",
            "mtds_gas_fees_backfill",
            "mtds_lst_rates_backfill",
            "mtds_vault_share_price_backfill",
            "mtds_lending_indices_backfill",
            "mdps_backfill",
            "features_backfill",
            "features_sports_backfill",
            "canonical_migration",
        }
        defined = {member.value for member in BackfillLaunchTaskKind}
        assert required.issubset(defined), sorted(required - defined)

    def test_string_construction_round_trip(self) -> None:
        for member in BackfillLaunchTaskKind:
            assert BackfillLaunchTaskKind(member.value) is member


# ────────────────────────────────────────────────────────────────────────────
# BackfillLaunchRequest
# ────────────────────────────────────────────────────────────────────────────


class TestBackfillLaunchRequest:
    def test_minimal_request(self) -> None:
        req = BackfillLaunchRequest(
            task=BackfillLaunchTaskKind.CEFI_BACKFILL,
            asset_group="cefi",
        )
        assert req.task is BackfillLaunchTaskKind.CEFI_BACKFILL
        assert req.asset_group == "cefi"
        assert req.dry_run is False
        assert req.force is False
        assert req.skip_dependency_check is False
        assert req.extra_metadata == {}

    def test_asset_group_pattern_rejects_unknown(self) -> None:
        with pytest.raises(ValueError):
            BackfillLaunchRequest(
                task=BackfillLaunchTaskKind.CEFI_BACKFILL,
                asset_group="CEFI",  # uppercase rejected
            )

    def test_asset_group_pattern_rejects_invalid_value(self) -> None:
        with pytest.raises(ValueError):
            BackfillLaunchRequest(
                task=BackfillLaunchTaskKind.CEFI_BACKFILL,
                asset_group="onchain",  # not in registry
            )

    def test_iso_date_pattern_enforced(self) -> None:
        with pytest.raises(ValueError):
            BackfillLaunchRequest(
                task=BackfillLaunchTaskKind.TRADFI_BACKFILL,
                asset_group="tradfi",
                start_date="2025/01/01",  # wrong separator
            )

    def test_yyyy_mm_pattern_enforced(self) -> None:
        with pytest.raises(ValueError):
            BackfillLaunchRequest(
                task=BackfillLaunchTaskKind.TRADFI_BACKFILL,
                asset_group="tradfi",
                month="2024",  # missing -MM
            )

    def test_full_request_round_trip(self) -> None:
        original = BackfillLaunchRequest(
            task=BackfillLaunchTaskKind.TRADFI_BACKFILL,
            asset_group="tradfi",
            venue="cme",
            start_date="2024-06-01",
            end_date="2024-06-30",
            data_types=["ohlcv_1m", "trades"],
            instrument_ids=["BTC.FUT", "ETH.FUT"],
            tier_plan="crypto-basis-2023-05+2024-06",
            year="2024",
            month="2024-06",
            root_symbol="BTC",
            extra_metadata={"VM_CUSTOM": "value"},
            force=True,
            dry_run=True,
            skip_dependency_check=True,
        )
        as_json = original.model_dump_json()
        round = BackfillLaunchRequest.model_validate_json(as_json)
        assert round == original


# ────────────────────────────────────────────────────────────────────────────
# BackfillLaunchResult
# ────────────────────────────────────────────────────────────────────────────


class TestBackfillLaunchResult:
    def test_round_trip(self) -> None:
        original = BackfillLaunchResult(
            vm_name="cefi-binance-spot-2024-light-20260507-150000",
            vm_name_prefix="cefi-binance-",
            zone="asia-northeast1-c",
            project_id="test-project",
            launched_at=datetime(2026, 5, 7, 15, 0, 0, tzinfo=UTC),
            correlation_id="48583baf-0c72-4147-9049-966151100123",
            launcher_script="launch-cefi-sharded-backfill.sh",
            dry_run=False,
            events_uri=(
                "gs://test-project-events/events/market-tick-data-service/"
                "2026-05-07/cefi-binance-spot-2024-light-20260507-150000/"
            ),
            argv=["bash", "/path/to/launch-cefi-sharded-backfill.sh"],
            env_diff={"VM_NAME": "cefi-binance-spot-2024-light-20260507-150000"},
        )
        as_json = original.model_dump_json()
        round = BackfillLaunchResult.model_validate_json(as_json)
        assert round == original


# ────────────────────────────────────────────────────────────────────────────
# VMLifecycleEvent — including real-world JSONL fixture
# ────────────────────────────────────────────────────────────────────────────


class TestVMLifecycleEvent:
    def test_minimal_event(self) -> None:
        ev = VMLifecycleEvent(
            event="STARTED",
            service="market-tick-data-service",
            timestamp=datetime(2026, 5, 7, 0, 0, 0, tzinfo=UTC),
        )
        assert ev.severity == "INFO"
        assert ev.correlation_id is None
        assert ev.details == {}

    def test_round_trip_full_event(self) -> None:
        original = VMLifecycleEvent(
            event="INSTRUMENT_PROCESSED",
            service="market-tick-data-service",
            timestamp=datetime(2026, 5, 7, 1, 23, 45, tzinfo=UTC),
            severity="INFO",
            correlation_id="cefi-binance-spot-2024-light-20260507-150000",
            details={"instrument_id": "BTC-USDT-PERP", "row_count": "1440"},
            raw_metadata={"nested": {"k": "v"}, "list": [1, 2, 3]},
        )
        as_json = original.model_dump_json()
        round = VMLifecycleEvent.model_validate_json(as_json)
        assert round.event == original.event
        assert round.severity == original.severity
        assert round.correlation_id == original.correlation_id
        assert round.details == original.details

    def test_parses_canonical_jsonl_row(self) -> None:
        """Verbatim-from-bucket JSONL row parses into the VMLifecycleEvent shape."""
        ev = _parse_jsonl_row(SAMPLE_JSONL_ROW)
        assert ev.event == "SERVICE_ERROR"
        assert ev.service == "instruments-service"
        assert ev.severity == "INFO"
        assert ev.correlation_id == "48583baf-0c72-4147-9049-966151100123"
        assert ev.details["error_type"] == "EnhancedError"
        assert ev.details["category"] == "unknown"
        # raw_metadata preserves the full nested structure including details dict.
        assert ev.raw_metadata["service_name"] == "instruments-service"
        assert "details" in ev.raw_metadata


# ────────────────────────────────────────────────────────────────────────────
# VMEventListResult
# ────────────────────────────────────────────────────────────────────────────


class TestVMEventListResult:
    def test_empty_round_trip(self) -> None:
        original = VMEventListResult(
            vm_name="cefi-binance-spot-2024-light-20260507-150000",
            service="market-tick-data-service",
            date="2026-05-07",
            hours_scanned=[0, 1, 2],
            total_events=0,
            events=[],
            truncated=False,
        )
        as_json = original.model_dump_json()
        round = VMEventListResult.model_validate_json(as_json)
        assert round == original

    def test_truncated_with_token(self) -> None:
        ev = VMLifecycleEvent(
            event="STARTED",
            service="market-tick-data-service",
            timestamp=datetime(2026, 5, 7, 0, 0, 0, tzinfo=UTC),
        )
        result = VMEventListResult(
            vm_name="cefi-binance-spot-2024-light-20260507-150000",
            service="market-tick-data-service",
            date="2026-05-07",
            hours_scanned=[0],
            total_events=1,
            events=[ev],
            truncated=True,
            next_page_token="eyJsYXN0X3RpbWVzdGFtcCI6IjIwMjYtMDUtMDdUMDA6MDA6MDArMDA6MDAifQ==",
        )
        assert result.truncated is True
        assert result.next_page_token is not None

    def test_date_pattern_enforced(self) -> None:
        with pytest.raises(ValueError):
            VMEventListResult(
                vm_name="x",
                service="y",
                date="2026/05/07",  # wrong separator
                total_events=0,
            )
