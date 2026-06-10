"""Tests for registry/venue_mapping.py — VenueMapping class."""

from __future__ import annotations

from datetime import date

import pytest

from unified_api_contracts.registry.venue_mapping import VenueMapping


@pytest.fixture(scope="module")
def vm() -> VenueMapping:
    return VenueMapping()


class TestInstantiation:
    def test_can_instantiate_no_args(self) -> None:
        mapping = VenueMapping()
        assert isinstance(mapping, VenueMapping)


class TestAllExchanges:
    def test_returns_non_empty_list(self, vm: VenueMapping) -> None:
        assert len(vm.all_exchanges) > 0

    def test_binance_in_exchanges(self, vm: VenueMapping) -> None:
        assert "binance" in vm.all_exchanges

    def test_deribit_in_exchanges(self, vm: VenueMapping) -> None:
        assert "deribit" in vm.all_exchanges

    def test_entries_are_strings(self, vm: VenueMapping) -> None:
        for ex in vm.all_exchanges[:10]:
            assert isinstance(ex, str)

    def test_returns_list(self, vm: VenueMapping) -> None:
        assert isinstance(vm.all_exchanges, list)


class TestAllCefiVenues:
    def test_returns_non_empty_list(self, vm: VenueMapping) -> None:
        assert len(vm.all_cefi_venues) > 0

    def test_binance_futures_in_cefi(self, vm: VenueMapping) -> None:
        assert "BINANCE-FUTURES" in vm.all_cefi_venues

    def test_binance_spot_in_cefi(self, vm: VenueMapping) -> None:
        assert "BINANCE-SPOT" in vm.all_cefi_venues

    def test_sorted(self, vm: VenueMapping) -> None:
        cefi = vm.all_cefi_venues
        assert cefi == sorted(cefi)

    def test_uppercase_entries(self, vm: VenueMapping) -> None:
        for venue in vm.all_cefi_venues[:5]:
            assert venue == venue.upper(), f"Expected uppercase, got: {venue}"


class TestAllTradfiVenues:
    def test_returns_non_empty_list(self, vm: VenueMapping) -> None:
        assert len(vm.all_tradfi_venues) > 0

    def test_cme_in_tradfi(self, vm: VenueMapping) -> None:
        assert "CME" in vm.all_tradfi_venues

    def test_nasdaq_in_tradfi(self, vm: VenueMapping) -> None:
        assert "NASDAQ" in vm.all_tradfi_venues

    def test_returns_list(self, vm: VenueMapping) -> None:
        assert isinstance(vm.all_tradfi_venues, list)


class TestIsTardisExchange:
    def test_binance_is_tardis(self, vm: VenueMapping) -> None:
        assert vm.is_tardis_exchange("binance") is True

    def test_deribit_is_tardis(self, vm: VenueMapping) -> None:
        assert vm.is_tardis_exchange("deribit") is True

    def test_unknown_exchange_not_tardis(self, vm: VenueMapping) -> None:
        assert vm.is_tardis_exchange("COMPLETELY_UNKNOWN_XY_ZZ") is False

    def test_case_sensitive_lowercase(self, vm: VenueMapping) -> None:
        # tardis exchanges are lowercase
        assert vm.is_tardis_exchange("binance") is True


class TestIsDatabentoVenue:
    def test_cme_is_databento(self, vm: VenueMapping) -> None:
        assert vm.is_databento_venue("CME") is True

    def test_unknown_not_databento(self, vm: VenueMapping) -> None:
        assert vm.is_databento_venue("COMPLETELY_UNKNOWN_VENUE") is False

    def test_returns_bool(self, vm: VenueMapping) -> None:
        assert isinstance(vm.is_databento_venue("CME"), bool)


class TestIsDefiVenue:
    def test_aave_v3_ethereum_is_defi(self, vm: VenueMapping) -> None:
        assert vm.is_defi_venue("AAVE_V3-ETHEREUM") is True

    def test_uniswap_v3_ethereum_is_defi(self, vm: VenueMapping) -> None:
        assert vm.is_defi_venue("UNISWAP_V3-ETHEREUM") is True

    def test_binance_not_defi(self, vm: VenueMapping) -> None:
        assert vm.is_defi_venue("BINANCE") is False

    def test_cme_not_defi(self, vm: VenueMapping) -> None:
        assert vm.is_defi_venue("CME") is False


class TestIsCefiVenue:
    def test_binance_futures_is_cefi(self, vm: VenueMapping) -> None:
        assert vm.is_cefi_venue("BINANCE-FUTURES") is True

    def test_binance_spot_is_cefi(self, vm: VenueMapping) -> None:
        assert vm.is_cefi_venue("BINANCE-SPOT") is True

    def test_cme_not_cefi(self, vm: VenueMapping) -> None:
        assert vm.is_cefi_venue("CME") is False

    def test_defi_venue_not_cefi(self, vm: VenueMapping) -> None:
        assert vm.is_cefi_venue("AAVE_V3-ETHEREUM") is False

    def test_unknown_not_cefi(self, vm: VenueMapping) -> None:
        assert vm.is_cefi_venue("COMPLETELY_UNKNOWN_VENUE") is False


class TestGetVenueStartDate:
    def test_binance_spot_has_start_date(self, vm: VenueMapping) -> None:
        start = vm.get_venue_start_date("BINANCE-SPOT")
        assert start is not None
        assert isinstance(start, str)

    def test_unknown_venue_returns_none(self, vm: VenueMapping) -> None:
        start = vm.get_venue_start_date("COMPLETELY_UNKNOWN_VENUE")
        assert start is None

    def test_start_date_is_iso_format(self, vm: VenueMapping) -> None:
        start = vm.get_venue_start_date("BINANCE-SPOT")
        assert start is not None
        # Should be parseable as ISO date
        parsed = date.fromisoformat(start)
        assert parsed.year >= 2010


class TestIsVenueAvailableOnDate:
    def test_binance_futures_available_recent(self, vm: VenueMapping) -> None:
        result = vm.is_venue_available_on_date("BINANCE-FUTURES", "2024-01-01")
        assert result is True

    def test_venue_not_available_before_start(self, vm: VenueMapping) -> None:
        # Most venues didn't exist in 2000
        result = vm.is_venue_available_on_date("BINANCE-SPOT", "2000-01-01")
        assert result is False

    def test_date_object_accepted(self, vm: VenueMapping) -> None:
        result = vm.is_venue_available_on_date("BINANCE-FUTURES", date(2024, 1, 1))
        assert isinstance(result, bool)

    def test_unknown_venue_returns_bool(self, vm: VenueMapping) -> None:
        # No start date set → defaults to available (True)
        result = vm.is_venue_available_on_date("COMPLETELY_UNKNOWN_VENUE", "2024-01-01")
        assert isinstance(result, bool)


class TestGetTardisExchangeForVenue:
    def test_binance_spot_tardis_is_binance(self, vm: VenueMapping) -> None:
        result = vm.get_tardis_exchange_for_venue("BINANCE-SPOT")
        assert result == "binance"

    def test_unknown_venue_returns_none(self, vm: VenueMapping) -> None:
        result = vm.get_tardis_exchange_for_venue("COMPLETELY_UNKNOWN_VENUE")
        assert result is None

    def test_returns_lowercase(self, vm: VenueMapping) -> None:
        result = vm.get_tardis_exchange_for_venue("BINANCE-SPOT")
        assert result is not None
        assert result == result.lower()


class TestGetDefiMvpTokens:
    def test_returns_non_empty_list(self, vm: VenueMapping) -> None:
        tokens = vm.get_defi_mvp_tokens()
        assert len(tokens) > 0

    def test_eth_in_mvp_tokens(self, vm: VenueMapping) -> None:
        tokens = vm.get_defi_mvp_tokens()
        assert "ETH" in tokens

    def test_returns_list(self, vm: VenueMapping) -> None:
        assert isinstance(vm.get_defi_mvp_tokens(), list)


class TestGetInstrumentDiscoveryStart:
    def test_hyperliquid_has_override(self, vm: VenueMapping) -> None:
        result = vm.get_instrument_discovery_start("HYPERLIQUID")
        assert result == "2023-11-01"

    def test_known_venue_returns_start_date(self, vm: VenueMapping) -> None:
        result = vm.get_instrument_discovery_start("BINANCE-SPOT")
        assert result is not None
        assert isinstance(result, str)

    def test_unknown_venue_returns_none(self, vm: VenueMapping) -> None:
        result = vm.get_instrument_discovery_start("COMPLETELY_UNKNOWN_VENUE_XY_ZZ")
        assert result is None


class TestGetVenueToTardisExchanges:
    def test_returns_dict(self, vm: VenueMapping) -> None:
        result = vm.get_venue_to_tardis_exchanges()
        assert isinstance(result, dict)

    def test_non_empty(self, vm: VenueMapping) -> None:
        result = vm.get_venue_to_tardis_exchanges()
        assert len(result) > 0

    def test_values_are_lists(self, vm: VenueMapping) -> None:
        result = vm.get_venue_to_tardis_exchanges()
        for v in result.values():
            assert isinstance(v, list)

    def test_binance_spot_maps_to_binance(self, vm: VenueMapping) -> None:
        result = vm.get_venue_to_tardis_exchanges()
        assert "BINANCE-SPOT" in result
        assert "binance" in result["BINANCE-SPOT"]


class TestConvertToTardisExchange:
    def test_uppercase_canonical_venue(self, vm: VenueMapping) -> None:
        result = vm.convert_to_tardis_exchange("BINANCE-SPOT")
        assert result == "binance"

    def test_already_lowercase_tardis(self, vm: VenueMapping) -> None:
        result = vm.convert_to_tardis_exchange("binance")
        assert result == "binance"

    def test_deribit_converts(self, vm: VenueMapping) -> None:
        result = vm.convert_to_tardis_exchange("DERIBIT")
        assert isinstance(result, str)
        assert result == result.lower()

    def test_unknown_returns_lowercase(self, vm: VenueMapping) -> None:
        result = vm.convert_to_tardis_exchange("COMPLETELY_UNKNOWN_VENUE_XY_ZZ")
        assert result == "completely_unknown_venue_xy_zz"


class TestGetDatabentExchangeId:
    def test_cme_returns_value(self, vm: VenueMapping) -> None:
        result = vm.get_databento_exchange_id("CME")
        assert result is not None

    def test_unknown_returns_none(self, vm: VenueMapping) -> None:
        result = vm.get_databento_exchange_id("COMPLETELY_UNKNOWN_VENUE_XY_ZZ")
        assert result is None


class TestGetExpectedTradingDates:
    def test_crypto_venue_includes_weekends(self, vm: VenueMapping) -> None:
        dates = vm.get_expected_trading_dates("BINANCE-SPOT", "2024-01-01", "2024-01-07")
        assert len(dates) == 7  # Full week including weekend

    def test_returns_list_of_strings(self, vm: VenueMapping) -> None:
        dates = vm.get_expected_trading_dates("BINANCE-SPOT", "2024-01-01", "2024-01-07")
        for d in dates:
            assert isinstance(d, str)

    def test_tradfi_venue_excludes_weekends(self, vm: VenueMapping) -> None:
        dates = vm.get_expected_trading_dates("CME", "2024-01-01", "2024-01-07")
        # 2024-01-01 is Monday, so 2024-01-06 (Sat) and 2024-01-07 (Sun) should be excluded
        # Also 2024-01-01 is a US holiday
        for d in dates:
            from datetime import datetime

            parsed = datetime.strptime(d, "%Y-%m-%d")
            assert parsed.weekday() < 5  # Not Saturday (5) or Sunday (6)

    def test_start_equals_end_returns_one_date(self, vm: VenueMapping) -> None:
        dates = vm.get_expected_trading_dates("BINANCE-SPOT", "2024-06-15", "2024-06-15")
        assert len(dates) == 1
        assert dates[0] == "2024-06-15"


class TestIsVenueAvailableOnDateExtended:
    def test_datetime_object_accepted(self, vm: VenueMapping) -> None:
        from datetime import datetime

        result = vm.is_venue_available_on_date(
            "BINANCE-SPOT",
            datetime(2024, 1, 1, 12, 0, 0),
        )
        assert isinstance(result, bool)

    def test_string_date_accepted(self, vm: VenueMapping) -> None:
        result = vm.is_venue_available_on_date("BINANCE-SPOT", "2024-01-01")
        assert isinstance(result, bool)

    def test_date_object_accepted(self, vm: VenueMapping) -> None:
        result = vm.is_venue_available_on_date("BINANCE-SPOT", date(2024, 1, 1))
        assert isinstance(result, bool)
