"""Verify BookmakerRegistry has all 20 entries with correct categories."""

from __future__ import annotations

import pytest

from unified_api_contracts.unified_api_contracts_external.sports.canonical.bookmaker import (
    BOOKMAKER_REGISTRY,
    BookmakerCategory,
    BookmakerInfo,
    BookmakerRegistry,
)


@pytest.mark.unit
class TestBookmakerRegistry:
    def test_registry_has_20_entries(self) -> None:
        assert len(BOOKMAKER_REGISTRY) == 23

    def test_registry_alias(self) -> None:
        assert BookmakerRegistry is BOOKMAKER_REGISTRY

    def test_all_values_are_bookmaker_info(self) -> None:
        for key, info in BOOKMAKER_REGISTRY.items():
            assert isinstance(info, BookmakerInfo), f"{key} is not BookmakerInfo"

    def test_key_matches_info_key(self) -> None:
        for key, info in BOOKMAKER_REGISTRY.items():
            assert key == info.key, f"Registry key {key!r} != info.key {info.key!r}"

    def test_exchanges_count(self) -> None:
        exchanges = [k for k, v in BOOKMAKER_REGISTRY.items() if v.category == BookmakerCategory.EXCHANGE]
        assert len(exchanges) == 4
        assert set(exchanges) == {"betfair", "smarkets", "matchbook", "betdaq"}

    def test_bookmaker_api_count(self) -> None:
        apis = [k for k, v in BOOKMAKER_REGISTRY.items() if v.category == BookmakerCategory.BOOKMAKER_API]
        assert len(apis) == 2
        assert set(apis) == {"pinnacle", "onexbet"}

    def test_aggregator_count(self) -> None:
        aggs = [k for k, v in BOOKMAKER_REGISTRY.items() if v.category == BookmakerCategory.AGGREGATOR]
        assert len(aggs) == 1
        assert aggs[0] == "odds_api"

    def test_scraper_count(self) -> None:
        scrapers = [k for k, v in BOOKMAKER_REGISTRY.items() if v.category == BookmakerCategory.SCRAPER]
        assert len(scrapers) == 14

    def test_all_have_required_fields(self) -> None:
        for key, info in BOOKMAKER_REGISTRY.items():
            assert info.display_name, f"{key} missing display_name"
            assert info.currency, f"{key} missing currency"
            assert info.min_bet_gbp is not None, f"{key} missing min_bet_gbp"

    def test_exchanges_have_api_docs(self) -> None:
        for key, info in BOOKMAKER_REGISTRY.items():
            if info.category == BookmakerCategory.EXCHANGE:
                assert info.api_docs_url is not None, f"Exchange {key} missing api_docs_url"

    def test_scrapers_have_scrape_url(self) -> None:
        for key, info in BOOKMAKER_REGISTRY.items():
            if info.category == BookmakerCategory.SCRAPER:
                assert info.scrape_url is not None, f"Scraper {key} missing scrape_url"
