from datetime import UTC, datetime

from unified_api_contracts.internal.domain.events_service.lifecycle import ResourceMetricsSnapshot


class TestResourceMetrics:
    def test_basic(self) -> None:
        snap = ResourceMetricsSnapshot(
            service_name="execution-service",
            timestamp=datetime.now(UTC),
            cpu_usage_pct=45.2,
            memory_rss_pct=62.1,
            shard_id="2024-01-15_CEFI_binance",
        )
        assert snap.cpu_usage_pct == 45.2
        assert snap.shard_id is not None

    def test_live_service(self) -> None:
        snap = ResourceMetricsSnapshot(
            service_name="execution-service",
            timestamp=datetime.now(UTC),
            venue_id="binance",
            strategy_id="MOM_MACD",
            active_connections=5,
        )
        assert snap.venue_id == "binance"

    def test_defaults_are_none(self) -> None:
        snap = ResourceMetricsSnapshot(
            service_name="test-service",
            timestamp=datetime.now(UTC),
        )
        assert snap.cpu_usage_pct is None
        assert snap.memory_rss_bytes is None
        assert snap.memory_rss_pct is None
        assert snap.active_connections is None
        assert snap.queue_depth is None
        assert snap.shard_id is None
        assert snap.venue_id is None
        assert snap.strategy_id is None

    def test_root_import(self) -> None:
        """Verify ResourceMetricsSnapshot is importable from UIC root."""
        from unified_api_contracts.internal import ResourceMetricsSnapshot

        # Root re-exports from events.py; domain module has its own copy.
        # Verify the root-exported class works identically.
        snap = ResourceMetricsSnapshot(
            service_name="test-service",
            timestamp=datetime.now(UTC),
            cpu_usage_pct=10.0,
        )
        assert snap.service_name == "test-service"
        assert snap.cpu_usage_pct == 10.0
