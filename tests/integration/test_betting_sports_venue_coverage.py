"""Integration tests validating BETTING_SPORTS_VENUES covers all UMI adapter keys.

These tests verify that the UAC venue manifest is complete enough for
downstream consumers (UMI sports registry) to validate against.
"""

from __future__ import annotations

from unified_api_contracts.registry.venue_manifest import BETTING_SPORTS_VENUES


def test_betting_sports_venues_non_empty() -> None:
    """BETTING_SPORTS_VENUES must contain venue contracts."""
    assert len(BETTING_SPORTS_VENUES) > 0


def test_exchange_venues_present() -> None:
    """All sports exchange venues must be in the manifest."""
    for key in ("betfair", "matchbook"):
        assert key in BETTING_SPORTS_VENUES, f"Exchange venue {key} missing"


def test_bookmaker_api_venues_present() -> None:
    """Bookmaker API venues must be in the manifest."""
    for key in ("pinnacle", "onexbet"):
        assert key in BETTING_SPORTS_VENUES, f"Bookmaker API venue {key} missing"


def test_prediction_market_venues_present() -> None:
    """Prediction market venues must be in the manifest."""
    for key in ("polymarket", "kalshi", "novig", "betopenly", "prophetx"):
        assert key in BETTING_SPORTS_VENUES, f"Prediction market venue {key} missing"


def test_scraper_venues_present() -> None:
    """UK bookmaker scraper venues must be in the manifest."""
    scraper_keys = [
        "skybet",
        "coral",
        "paddypower",
        "betfred",
        "betvictor",
        "boylesports",
        "bwin",
        "ladbrokes",
        "williamhill",
        "betway",
        "unibet",
        "bet888sport",
        "bet365",
        "sbo",
    ]
    for key in scraper_keys:
        assert key in BETTING_SPORTS_VENUES, f"Scraper venue {key} missing"


def test_aggregator_venues_present() -> None:
    """Odds aggregator venues must be in the manifest."""
    for key in ("odds_api", "opticodds", "sharpapi", "odds_engine", "metabet"):
        assert key in BETTING_SPORTS_VENUES, f"Aggregator venue {key} missing"


def test_all_venue_contracts_have_required_fields() -> None:
    """Every venue contract must have the VenueContract TypedDict fields."""
    required_fields = {
        "has_rest",
        "has_websocket",
        "has_fix",
        "config_secret_field",
        "response_schema_classes",
        "error_schema_classes",
        "example_schema_map",
    }
    for venue_key, contract in BETTING_SPORTS_VENUES.items():
        for field in required_fields:
            assert field in contract, f"Venue {venue_key} missing field: {field}"


def test_scraper_venues_have_no_rest() -> None:
    """Scraper-based venues should have has_rest=False."""
    scraper_keys = [
        "skybet",
        "coral",
        "paddypower",
        "betfred",
        "betvictor",
        "boylesports",
        "bwin",
        "ladbrokes",
        "williamhill",
        "betway",
        "unibet",
        "bet888sport",
        "bet365",
        "sbo",
    ]
    for key in scraper_keys:
        contract = BETTING_SPORTS_VENUES[key]
        assert contract["has_rest"] is False, f"Scraper venue {key} should have has_rest=False"


def test_api_venues_have_rest() -> None:
    """API-based venues should have has_rest=True."""
    api_keys = ["betfair", "pinnacle", "polymarket", "kalshi", "odds_api"]
    for key in api_keys:
        contract = BETTING_SPORTS_VENUES[key]
        assert contract["has_rest"] is True, f"API venue {key} should have has_rest=True"
