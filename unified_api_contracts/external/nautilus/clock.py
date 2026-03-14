"""Clock Protocol and MockClock for NautilusTrader-like timing in execution-services testing.

Mirrors NautilusTrader Clock interface for deterministic time in backtests.
Reference: https://nautilustrader.io/docs/
"""

__api_version__ = "v1"  # matches provider_api_versions.yaml

from datetime import UTC, datetime
from typing import Protocol


class Clock(Protocol):
    """Abstract interface for NautilusTrader-like clock.

    Used for dependency injection in execution-services tests.
    """

    def timestamp(self) -> float:
        """Return current timestamp in seconds (Unix epoch)."""
        ...

    def timestamp_ns(self) -> int:
        """Return current timestamp in nanoseconds (Unix epoch)."""
        ...

    def utc_now(self) -> datetime:
        """Return current UTC datetime."""
        ...


class MockClock:
    """Mock clock with configurable time for deterministic testing."""

    def __init__(self, *, timestamp_ns: int | None = None) -> None:
        """Initialize with optional fixed timestamp (nanoseconds since epoch)."""
        self._timestamp_ns = timestamp_ns

    def set_timestamp_ns(self, ts_ns: int) -> None:
        """Set the fixed timestamp (nanoseconds)."""
        self._timestamp_ns = ts_ns

    def timestamp(self) -> float:
        """Return current timestamp in seconds (Unix epoch)."""
        if self._timestamp_ns is not None:
            return self._timestamp_ns / 1e9
        return datetime.now(UTC).timestamp()

    def timestamp_ns(self) -> int:
        """Return current timestamp in nanoseconds (Unix epoch)."""
        if self._timestamp_ns is not None:
            return self._timestamp_ns
        return int(datetime.now(UTC).timestamp() * 1e9)

    def utc_now(self) -> datetime:
        """Return current UTC datetime."""
        ts = self.timestamp()
        return datetime.fromtimestamp(ts, tz=UTC)
