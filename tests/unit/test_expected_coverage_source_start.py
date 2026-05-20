"""Tests for is_before_source_coverage_start / get_source_coverage_start_for_data_type.

Phase 4 of uac_source_capability_metadata_promotion_2026_05_20: verifies that
expected_coverage.py correctly reads SourceCapability.coverage_start[data_type]
and returns the right signal for EXPECTED_PRE_SOURCE_COVERAGE_START reason.
"""

from __future__ import annotations

from datetime import date

import pytest

from unified_api_contracts.registry.capability import SourceCapability, register_capability
from unified_api_contracts.registry.capability_data import bootstrap_capabilities
from unified_api_contracts.registry.expected_coverage import (
    get_source_coverage_start_for_data_type,
    is_before_source_coverage_start,
)

# ---------------------------------------------------------------------------
# Fixtures — isolated test capabilities
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _register_test_capabilities() -> None:
    """Register a minimal set of capabilities for isolation."""
    register_capability(
        SourceCapability(
            source="_test_venue_with_start",
            domains=["market"],
            crosscutting=["errors"],
            coverage_start={"candles": date(2023, 6, 14), "funding_rates": date(2024, 1, 1)},
        )
    )
    register_capability(
        SourceCapability(
            source="_test_venue_no_start",
            domains=["market"],
            crosscutting=["errors"],
            coverage_start=None,
        )
    )


# ---------------------------------------------------------------------------
# get_source_coverage_start_for_data_type
# ---------------------------------------------------------------------------


class TestGetSourceCoverageStart:
    def test_returns_date_for_known_data_type(self) -> None:
        result = get_source_coverage_start_for_data_type("_TEST_VENUE_WITH_START", "candles")
        assert result == date(2023, 6, 14)

    def test_returns_none_for_unknown_data_type(self) -> None:
        result = get_source_coverage_start_for_data_type("_TEST_VENUE_WITH_START", "trades")
        assert result is None

    def test_returns_none_when_coverage_start_is_null(self) -> None:
        result = get_source_coverage_start_for_data_type("_TEST_VENUE_NO_START", "candles")
        assert result is None

    def test_returns_none_for_unregistered_venue(self) -> None:
        result = get_source_coverage_start_for_data_type("NONEXISTENT_VENUE_XYZ", "candles")
        assert result is None

    def test_case_insensitive_venue_lookup(self) -> None:
        assert get_source_coverage_start_for_data_type("_test_venue_with_start", "candles") == date(2023, 6, 14)
        assert get_source_coverage_start_for_data_type("_TEST_VENUE_WITH_START", "candles") == date(2023, 6, 14)

    def test_hyphenated_venue_falls_back_to_base(self) -> None:
        # "_test_venue_with_start-futures" is not registered; base "_test_venue_with_start" is
        result = get_source_coverage_start_for_data_type("_TEST_VENUE_WITH_START-FUTURES", "candles")
        assert result == date(2023, 6, 14)

    def test_second_data_type_returned_correctly(self) -> None:
        result = get_source_coverage_start_for_data_type("_TEST_VENUE_WITH_START", "funding_rates")
        assert result == date(2024, 1, 1)


# ---------------------------------------------------------------------------
# is_before_source_coverage_start — EXPECTED_PRE_SOURCE_COVERAGE_START signal
# ---------------------------------------------------------------------------


class TestIsBeforeSourceCoverageStart:
    def test_date_before_start_returns_true(self) -> None:
        assert is_before_source_coverage_start("_TEST_VENUE_WITH_START", "candles", date(2022, 1, 1))

    def test_date_equal_to_start_returns_false(self) -> None:
        # coverage_start date is inclusive — on the start date, data IS available
        assert not is_before_source_coverage_start("_TEST_VENUE_WITH_START", "candles", date(2023, 6, 14))

    def test_date_after_start_returns_false(self) -> None:
        assert not is_before_source_coverage_start("_TEST_VENUE_WITH_START", "candles", date(2024, 1, 1))

    def test_no_coverage_start_returns_false(self) -> None:
        # No clip — date should never be excluded when coverage_start is unknown
        assert not is_before_source_coverage_start("_TEST_VENUE_NO_START", "candles", date(2010, 1, 1))

    def test_unknown_data_type_returns_false(self) -> None:
        # No entry for "trades" → no clip
        assert not is_before_source_coverage_start("_TEST_VENUE_WITH_START", "trades", date(2010, 1, 1))

    def test_unregistered_venue_returns_false(self) -> None:
        assert not is_before_source_coverage_start("NONEXISTENT_VENUE_XYZ", "candles", date(2010, 1, 1))

    def test_hyphenated_venue_correct_result(self) -> None:
        # "_test_venue_with_start-spot" falls back to "_test_venue_with_start"
        assert is_before_source_coverage_start("_TEST_VENUE_WITH_START-SPOT", "candles", date(2020, 1, 1))
        assert not is_before_source_coverage_start("_TEST_VENUE_WITH_START-SPOT", "candles", date(2024, 1, 1))


# ---------------------------------------------------------------------------
# Smoke test — real declarations (bootstrap required)
# ---------------------------------------------------------------------------


class TestRealDeclarationSmokeTest:
    """Verify real venues from Phase 2 migration work end-to-end."""

    @pytest.fixture(autouse=True)
    def _bootstrap(self) -> None:
        bootstrap_capabilities()

    def test_hyperliquid_candles_before_launch(self) -> None:
        # hyperliquid coverage_start={"candles": date(2023, 6, 14)} from Phase 2 migration
        assert is_before_source_coverage_start("HYPERLIQUID", "candles", date(2022, 1, 1))

    def test_hyperliquid_candles_after_launch(self) -> None:
        assert not is_before_source_coverage_start("HYPERLIQUID", "candles", date(2024, 1, 1))

    def test_hyperliquid_no_funding_rates_clip(self) -> None:
        # funding_rates not in hyperliquid's coverage_start → no clip
        assert not is_before_source_coverage_start("HYPERLIQUID", "funding_rates", date(2020, 1, 1))

    def test_binance_spot_no_clip(self) -> None:
        # binance has coverage_start=None → no clip for any date
        assert not is_before_source_coverage_start("BINANCE-SPOT", "trades", date(2010, 1, 1))

    def test_polymarket_before_launch(self) -> None:
        # polymarket coverage_start={"candles": date(2020, 9, 1)} from Phase 2 migration
        assert is_before_source_coverage_start("POLYMARKET", "candles", date(2019, 1, 1))

    def test_polymarket_after_launch(self) -> None:
        assert not is_before_source_coverage_start("POLYMARKET", "candles", date(2021, 1, 1))
