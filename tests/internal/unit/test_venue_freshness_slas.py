"""Unit tests for venue freshness SLA definitions."""

from __future__ import annotations

import pytest

from unified_api_contracts.internal.domain.data_quality.venue_freshness_slas import (
    VENUE_FRESHNESS_SLAS,
    VenueCategory,
    VenueFreshnessSLA,
    get_sla_for_venue,
    get_slas_by_category,
)


class TestVenueFreshnessSLARegistry:
    """Tests for the VENUE_FRESHNESS_SLAS registry."""

    def test_registry_not_empty(self) -> None:
        assert len(VENUE_FRESHNESS_SLAS) > 0

    def test_registry_has_all_umi_cefi_venues(self) -> None:
        """All CeFi venues from UMI VENUE_REGISTRY must have an SLA."""
        cefi_venues = {"binance", "coinbase", "bybit", "okx", "deribit", "ccxt", "upbit"}
        for venue in cefi_venues:
            assert venue in VENUE_FRESHNESS_SLAS, f"Missing CeFi venue: {venue}"

    def test_registry_has_all_umi_tradfi_venues(self) -> None:
        """All TradFi venues from UMI VENUE_REGISTRY must have an SLA."""
        tradfi_venues = {
            "databento",
            "tardis",
            "yahoo_finance",
            "barchart",
            "fred",
            "ecb",
            "ofr",
            "openbb",
            "ibkr",
        }
        for venue in tradfi_venues:
            assert venue in VENUE_FRESHNESS_SLAS, f"Missing TradFi venue: {venue}"

    def test_registry_has_all_umi_defi_venues(self) -> None:
        """All DeFi venues from UMI VENUE_REGISTRY must have an SLA."""
        defi_venues = {
            "aave_v3",
            "balancer",
            "curve",
            "ethena",
            "fluid",
            "etherfi",
            "lido",
            "morpho",
            "uniswap_v2",
            "uniswap_v3",
            "uniswap_v4",
            "instadapp",
            "defillama",
        }
        for venue in defi_venues:
            assert venue in VENUE_FRESHNESS_SLAS, f"Missing DeFi venue: {venue}"

    def test_registry_has_all_umi_onchain_perps(self) -> None:
        """All onchain perps from UMI VENUE_REGISTRY must have an SLA."""
        onchain_venues = {"hyperliquid", "aster"}
        for venue in onchain_venues:
            assert venue in VENUE_FRESHNESS_SLAS, f"Missing onchain perps venue: {venue}"

    def test_total_venue_count(self) -> None:
        """Registry should cover all 32 UMI VENUE_REGISTRY venues."""
        assert len(VENUE_FRESHNESS_SLAS) == 32

    def test_all_sla_values_positive(self) -> None:
        for venue, sla in VENUE_FRESHNESS_SLAS.items():
            assert sla.max_staleness_seconds > 0, f"SLA for {venue} must be positive"

    def test_cefi_slas_are_fast(self) -> None:
        """CeFi SLAs should be <= 10 seconds."""
        for sla in get_slas_by_category(VenueCategory.CEFI):
            assert sla.max_staleness_seconds <= 10, f"CeFi venue {sla.venue} SLA {sla.max_staleness_seconds}s > 10s"

    def test_defi_slas_are_slower(self) -> None:
        """DeFi SLAs should be >= 15 seconds (block time constraints)."""
        for sla in get_slas_by_category(VenueCategory.DEFI):
            assert sla.max_staleness_seconds >= 15, f"DeFi venue {sla.venue} SLA {sla.max_staleness_seconds}s < 15s"

    def test_specific_sla_values(self) -> None:
        """Spot-check specific SLA values."""
        assert VENUE_FRESHNESS_SLAS["binance"].max_staleness_seconds == 1
        assert VENUE_FRESHNESS_SLAS["deribit"].max_staleness_seconds == 5
        assert VENUE_FRESHNESS_SLAS["okx"].max_staleness_seconds == 2
        assert VENUE_FRESHNESS_SLAS["lido"].max_staleness_seconds == 300
        assert VENUE_FRESHNESS_SLAS["etherfi"].max_staleness_seconds == 300
        assert VENUE_FRESHNESS_SLAS["uniswap_v3"].max_staleness_seconds == 15
        assert VENUE_FRESHNESS_SLAS["hyperliquid"].max_staleness_seconds == 2
        assert VENUE_FRESHNESS_SLAS["aster"].max_staleness_seconds == 5

    def test_venue_names_are_lowercase(self) -> None:
        for venue in VENUE_FRESHNESS_SLAS:
            assert venue == venue.lower(), f"Venue name must be lowercase: {venue}"


class TestVenueFreshnessSLADataclass:
    """Tests for VenueFreshnessSLA frozen dataclass."""

    def test_immutable(self) -> None:
        sla = VenueFreshnessSLA("test", VenueCategory.CEFI, 5)
        with pytest.raises(AttributeError):
            sla.max_staleness_seconds = 10  # type: ignore[misc]

    def test_equality(self) -> None:
        a = VenueFreshnessSLA("binance", VenueCategory.CEFI, 1)
        b = VenueFreshnessSLA("binance", VenueCategory.CEFI, 1)
        assert a == b

    def test_slots(self) -> None:
        sla = VenueFreshnessSLA("test", VenueCategory.CEFI, 5)
        assert not hasattr(sla, "__dict__")


class TestGetSLAForVenue:
    """Tests for get_sla_for_venue()."""

    def test_known_venue(self) -> None:
        sla = get_sla_for_venue("binance")
        assert sla.venue == "binance"
        assert sla.category == VenueCategory.CEFI
        assert sla.max_staleness_seconds == 1

    def test_case_insensitive(self) -> None:
        sla = get_sla_for_venue("BINANCE")
        assert sla.venue == "binance"

    def test_unknown_venue_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown venue"):
            get_sla_for_venue("nonexistent_venue")


class TestGetSLAsByCategory:
    """Tests for get_slas_by_category()."""

    def test_cefi_count(self) -> None:
        cefi = get_slas_by_category(VenueCategory.CEFI)
        assert len(cefi) == 7

    def test_tradfi_count(self) -> None:
        tradfi = get_slas_by_category(VenueCategory.TRADFI)
        assert len(tradfi) == 9

    def test_defi_count(self) -> None:
        defi = get_slas_by_category(VenueCategory.DEFI)
        assert len(defi) == 14

    def test_onchain_perps_count(self) -> None:
        onchain = get_slas_by_category(VenueCategory.ONCHAIN_PERPS)
        assert len(onchain) == 2

    def test_all_returned_have_correct_category(self) -> None:
        for category in VenueCategory:
            slas = get_slas_by_category(category)
            for sla in slas:
                assert sla.category == category


class TestVenueCategory:
    """Tests for VenueCategory enum."""

    def test_all_categories(self) -> None:
        assert set(VenueCategory) == {
            VenueCategory.CEFI,
            VenueCategory.TRADFI,
            VenueCategory.DEFI,
            VenueCategory.ONCHAIN_PERPS,
        }

    def test_category_values(self) -> None:
        assert VenueCategory.CEFI.value == "cefi"
        assert VenueCategory.TRADFI.value == "tradfi"
        assert VenueCategory.DEFI.value == "defi"
        assert VenueCategory.ONCHAIN_PERPS.value == "onchain_perps"
