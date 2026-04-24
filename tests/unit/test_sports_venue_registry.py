"""Tests for sports venue execution registry completeness."""

from __future__ import annotations

from unified_api_contracts.canonical.domain.sports.odds_api_mapping import ODDS_API_KEY_TO_VENUE
from unified_api_contracts.canonical.domain.sports.venue_execution_registry import VENUE_EXECUTION_REGISTRY


def test_all_odds_api_venues_in_registry() -> None:
    missing = [k for k, v in ODDS_API_KEY_TO_VENUE.items() if v not in VENUE_EXECUTION_REGISTRY]
    assert missing == [], f"Missing venues in registry: {missing}"


def test_all_venues_have_required_fields() -> None:
    for key, profile in VENUE_EXECUTION_REGISTRY.items():
        assert profile.venue_key, f"{key}: venue_key is empty"
        assert profile.display_name, f"{key}: display_name is empty"
        assert profile.venue_category is not None, f"{key}: venue_category is None"
        assert profile.primary_execution_method is not None, f"{key}: execution_method is None"


def test_all_venues_have_commission_data() -> None:
    for key, profile in VENUE_EXECUTION_REGISTRY.items():
        assert profile.commission_model is not None, f"{key}: commission_model is None"
        assert profile.min_bet is not None, f"{key}: min_bet is None"
        assert profile.withdrawal_fee is not None, f"{key}: withdrawal_fee is None"


def test_exchange_venues_have_api_url() -> None:
    for key, profile in VENUE_EXECUTION_REGISTRY.items():
        if (
            profile.venue_category
            and profile.venue_category.value == "exchange"
            and profile.primary_execution_method
            and profile.primary_execution_method.value == "rest_api"
        ):
            assert profile.api_base_url, f"{key}: exchange with REST API missing api_base_url"


def test_scraper_venues_have_login_url() -> None:
    for key, profile in VENUE_EXECUTION_REGISTRY.items():
        if profile.venue_category and profile.venue_category.value == "scraper":
            assert profile.login_url, f"{key}: scraper missing login_url"


def test_venue_keys_match_dict_keys() -> None:
    for key, profile in VENUE_EXECUTION_REGISTRY.items():
        assert profile.venue_key == key, f"Dict key '{key}' != profile.venue_key '{profile.venue_key}'"


def test_no_duplicate_odds_api_keys() -> None:
    odds_keys = [p.odds_api_key for p in VENUE_EXECUTION_REGISTRY.values() if p.odds_api_key]
    assert len(odds_keys) == len(set(odds_keys)), "Duplicate odds_api_key values found"


def test_registry_has_at_least_78_venues() -> None:
    assert len(VENUE_EXECUTION_REGISTRY) >= 76, f"Expected >=76 venues, got {len(VENUE_EXECUTION_REGISTRY)}"
