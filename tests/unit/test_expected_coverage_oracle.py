"""Tests for the deterministic availability oracle in `registry/expected_coverage.py`.

Mega-audit Phase A2 — covers the closed-set of gates the oracle composes:
scope policy, venue launch, chain genesis, US trading calendar (weekend /
holiday / half-day).
"""

from __future__ import annotations

from datetime import date

import pytest

from unified_api_contracts.registry.expected_coverage import (
    ExpectedCoverageResult,
    ExpectedState,
    expected_coverage,
)


class TestScopePolicy:
    def test_out_of_scope_tuple_returns_not_in_scope(self) -> None:
        # XYZVENUE is not in EXPECTED_COVERAGE_BY_ASSET_GROUP.
        result = expected_coverage("cefi", "XYZVENUE", "trades", date(2025, 6, 15))
        assert result.state is ExpectedState.NOT_IN_SCOPE
        assert result.reason is None
        assert "not in EXPECTED_COVERAGE_BY_ASSET_GROUP" in result.diagnostic

    def test_out_of_scope_data_type_returns_not_in_scope(self) -> None:
        # BINANCE-SPOT is in scope but only for {trades, book_snapshot_5}; "oracle_prices" is not.
        result = expected_coverage("cefi", "BINANCE-SPOT", "oracle_prices", date(2025, 6, 15))
        assert result.state is ExpectedState.NOT_IN_SCOPE


class TestVenueLaunch:
    def test_cefi_pre_venue_launch_fires_not_yet_live(self) -> None:
        # HYPERLIQUID launched 2023-06-14 — query a date a year earlier.
        result = expected_coverage("cefi", "HYPERLIQUID", "trades", date(2022, 6, 14))
        assert result.state is ExpectedState.NOT_YET_LIVE
        assert result.reason == "EXPECTED_PRE_VENUE_LAUNCH"
        assert "HYPERLIQUID" in result.diagnostic

    def test_cefi_post_venue_launch_falls_through(self) -> None:
        # HYPERLIQUID launched 2023-06-14 — a date well after should be SHOULD_HAVE_DATA.
        result = expected_coverage("cefi", "HYPERLIQUID", "trades", date(2025, 6, 15))
        assert result.state is ExpectedState.SHOULD_HAVE_DATA
        assert result.reason is None

    def test_prediction_pre_polymarket_launch_fires_not_yet_live(self) -> None:
        # POLYMARKET launched 2020-09-01.
        result = expected_coverage("prediction", "POLYMARKET", "trades", date(2020, 1, 1))
        assert result.state is ExpectedState.NOT_YET_LIVE
        assert result.reason == "EXPECTED_PRE_VENUE_LAUNCH"


class TestDefiChainGenesis:
    def test_pre_chain_genesis_fires_not_yet_live(self) -> None:
        # AAVEV3-LINEA: LINEA chain has its own genesis date. A date pre-2018 must precede most chains.
        result = expected_coverage("defi", "AAVEV3-LINEA", "lending_indices", date(2018, 1, 1))
        # Either pre-venue-launch OR pre-chain-genesis fires — both yield NOT_YET_LIVE.
        assert result.state is ExpectedState.NOT_YET_LIVE
        assert result.reason in {"EXPECTED_PRE_VENUE_LAUNCH", "EXPECTED_PRE_GENESIS_CHAIN"}


class TestUsTradfiCalendar:
    def test_weekend_returns_expected_weekend(self) -> None:
        # 2024-06-15 is a Saturday.
        result = expected_coverage("tradfi", "CME", "trades", date(2024, 6, 15))
        assert result.state is ExpectedState.EXPECTED_EMPTY
        assert result.reason == "EXPECTED_WEEKEND"

    def test_sunday_returns_expected_weekend(self) -> None:
        # 2024-06-16 is a Sunday.
        result = expected_coverage("tradfi", "CME", "trades", date(2024, 6, 16))
        assert result.state is ExpectedState.EXPECTED_EMPTY
        assert result.reason == "EXPECTED_WEEKEND"

    def test_us_holiday_returns_expected_holiday(self) -> None:
        # 2024-07-04 = Independence Day, in US_MARKET_HOLIDAYS.
        result = expected_coverage("tradfi", "CME", "trades", date(2024, 7, 4))
        assert result.state is ExpectedState.EXPECTED_EMPTY
        assert result.reason == "EXPECTED_HOLIDAY"

    def test_regular_weekday_returns_should_have_data(self) -> None:
        # 2024-06-17 = Monday, not a holiday.
        result = expected_coverage("tradfi", "CME", "trades", date(2024, 6, 17))
        assert result.state is ExpectedState.SHOULD_HAVE_DATA
        assert result.reason is None


class TestCryptoAlwaysOn:
    def test_cefi_weekend_returns_should_have_data(self) -> None:
        # Crypto trades 24/7 — weekends are not gaps.
        result = expected_coverage("cefi", "BINANCE-SPOT", "trades", date(2024, 6, 15))
        assert result.state is ExpectedState.SHOULD_HAVE_DATA

    def test_defi_weekend_returns_should_have_data(self) -> None:
        # 2024-06-15 = Saturday; DeFi has no weekend.
        result = expected_coverage("defi", "AAVEV3-ETHEREUM", "lending_indices", date(2024, 6, 15))
        assert result.state is ExpectedState.SHOULD_HAVE_DATA


class TestResultShape:
    def test_result_is_frozen(self) -> None:
        result = expected_coverage("cefi", "BINANCE-SPOT", "trades", date(2024, 6, 17))
        with pytest.raises(AttributeError):
            result.state = ExpectedState.EXPECTED_EMPTY  # type: ignore[misc]

    def test_diagnostic_non_empty(self) -> None:
        result = expected_coverage("cefi", "BINANCE-SPOT", "trades", date(2024, 6, 17))
        assert isinstance(result, ExpectedCoverageResult)
        assert result.diagnostic
