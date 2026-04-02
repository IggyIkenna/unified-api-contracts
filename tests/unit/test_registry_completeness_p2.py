"""Registry Completeness P2 — fixture example, provider versions, sports aggregator.

Covers:
1. fixture_example.json loads and contains BTTS/draw_no_bet/double_chance markets
2. provider_api_versions.yaml validates structure and status values
3. SportsAggregatorType enum and VENUE_AGGREGATOR_TYPE mapping
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import ClassVar

import pytest
import yaml

from unified_api_contracts.external.odds_api.schemas import (
    OddsApiFixture,
)
from unified_api_contracts.registry._sports_venue_constants import (
    VENUE_AGGREGATOR_TYPE,
    SportsAggregatorType,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# 1. fixture_example.json — BTTS, draw_no_bet, double_chance markets
# ---------------------------------------------------------------------------


class TestFixtureExample:
    """fixture_example.json loads and contains the required market types."""

    FIXTURE_PATH = (
        Path(__file__).resolve().parents[2]
        / "unified_api_contracts"
        / "external"
        / "odds_api"
        / "examples"
        / "fixture_example.json"
    )

    def test_fixture_file_exists(self) -> None:
        assert self.FIXTURE_PATH.exists(), f"fixture_example.json not found at {self.FIXTURE_PATH}"

    def test_fixture_loads_as_valid_json(self) -> None:
        data = json.loads(self.FIXTURE_PATH.read_text())
        assert isinstance(data, dict)

    def test_fixture_parses_as_odds_api_fixture(self) -> None:
        data = json.loads(self.FIXTURE_PATH.read_text())
        fixture = OddsApiFixture.model_validate(data)
        assert fixture.id is not None
        assert fixture.home_team is not None
        assert fixture.away_team is not None
        assert fixture.bookmakers is not None
        assert len(fixture.bookmakers) > 0

    def test_fixture_has_btts_market(self) -> None:
        data = json.loads(self.FIXTURE_PATH.read_text())
        market_keys = _extract_market_keys(data)
        assert "btts" in market_keys, "fixture_example.json missing BTTS market"

    def test_btts_market_has_yes_no_outcomes(self) -> None:
        data = json.loads(self.FIXTURE_PATH.read_text())
        btts_market = _find_market(data, "btts")
        assert btts_market is not None, "BTTS market not found"
        outcome_names = {o["name"] for o in btts_market["outcomes"]}
        assert "Yes" in outcome_names, "BTTS missing 'Yes' outcome"
        assert "No" in outcome_names, "BTTS missing 'No' outcome"

    def test_fixture_has_draw_no_bet_market(self) -> None:
        data = json.loads(self.FIXTURE_PATH.read_text())
        market_keys = _extract_market_keys(data)
        assert "draw_no_bet" in market_keys, "fixture_example.json missing draw_no_bet market"

    def test_draw_no_bet_has_two_outcomes(self) -> None:
        data = json.loads(self.FIXTURE_PATH.read_text())
        dnb_market = _find_market(data, "draw_no_bet")
        assert dnb_market is not None, "draw_no_bet market not found"
        assert len(dnb_market["outcomes"]) == 2, "draw_no_bet should have exactly 2 outcomes"

    def test_fixture_has_double_chance_market(self) -> None:
        data = json.loads(self.FIXTURE_PATH.read_text())
        market_keys = _extract_market_keys(data)
        assert "double_chance" in market_keys, "fixture_example.json missing double_chance market"

    def test_double_chance_has_three_outcomes(self) -> None:
        data = json.loads(self.FIXTURE_PATH.read_text())
        dc_market = _find_market(data, "double_chance")
        assert dc_market is not None, "double_chance market not found"
        assert len(dc_market["outcomes"]) == 3, "double_chance should have exactly 3 outcomes"

    def test_all_outcome_prices_are_numeric(self) -> None:
        data = json.loads(self.FIXTURE_PATH.read_text())
        for bookmaker in data.get("bookmakers", []):
            for market in bookmaker.get("markets", []):
                for outcome in market.get("outcomes", []):
                    assert isinstance(outcome["price"], (int, float)), (
                        f"Non-numeric price in market {market['key']}: {outcome['price']}"
                    )


# ---------------------------------------------------------------------------
# 2. provider_api_versions.yaml — structure validation
# ---------------------------------------------------------------------------


class TestProviderApiVersionsYaml:
    """provider_api_versions.yaml has valid structure and status values."""

    CONFIG_YAML_PATH = (
        Path(__file__).resolve().parents[2] / "unified_api_contracts" / "config" / "provider_api_versions.yaml"
    )

    VALID_STATUSES: ClassVar[set[str]] = {"green", "yellow", "red", "dormant"}

    def test_yaml_file_exists(self) -> None:
        assert self.CONFIG_YAML_PATH.exists(), f"provider_api_versions.yaml not found at {self.CONFIG_YAML_PATH}"

    def test_yaml_loads(self) -> None:
        data = yaml.safe_load(self.CONFIG_YAML_PATH.read_text())
        assert isinstance(data, dict)
        assert "providers" in data

    def test_all_providers_have_required_fields(self) -> None:
        data = yaml.safe_load(self.CONFIG_YAML_PATH.read_text())
        providers: dict[str, dict[str, object]] = data["providers"]
        for name, spec in providers.items():
            assert "api_version" in spec, f"Provider {name} missing api_version"
            assert "spec_url" in spec, f"Provider {name} missing spec_url"
            assert "last_verified" in spec, f"Provider {name} missing last_verified"
            assert "status" in spec, f"Provider {name} missing status"

    def test_all_statuses_are_valid(self) -> None:
        data = yaml.safe_load(self.CONFIG_YAML_PATH.read_text())
        providers: dict[str, dict[str, object]] = data["providers"]
        for name, spec in providers.items():
            status = spec["status"]
            assert status in self.VALID_STATUSES, (
                f"Provider {name} has invalid status '{status}'; expected one of {self.VALID_STATUSES}"
            )

    def test_no_yellow_providers_with_schemas_and_cassettes(self) -> None:
        """Yellow providers that have both schemas.py AND cassettes should be green."""
        data = yaml.safe_load(self.CONFIG_YAML_PATH.read_text())
        providers: dict[str, dict[str, object]] = data["providers"]
        external_root = self.CONFIG_YAML_PATH.parents[1] / "external"

        violations: list[str] = []
        for name, spec in providers.items():
            if spec["status"] != "yellow":
                continue
            provider_dir = external_root / name
            has_schema = (provider_dir / "schemas.py").exists()
            has_cassette = (
                any((provider_dir / "mocks").glob("*cassette*")) if (provider_dir / "mocks").exists() else False
            )
            if has_schema and has_cassette:
                violations.append(name)

        assert not violations, f"Providers with schemas + cassettes should be green, not yellow: {violations}"

    def test_dormant_providers_have_no_schemas(self) -> None:
        """Dormant providers should not have a schemas.py."""
        data = yaml.safe_load(self.CONFIG_YAML_PATH.read_text())
        providers: dict[str, dict[str, object]] = data["providers"]
        external_root = self.CONFIG_YAML_PATH.parents[1] / "external"

        for name, spec in providers.items():
            if spec["status"] != "dormant":
                continue
            provider_dir = external_root / name
            # Dormant providers may or may not have a directory
            if provider_dir.exists():
                assert not (provider_dir / "schemas.py").exists(), (
                    f"Dormant provider {name} has schemas.py — should not be dormant"
                )

    def test_provider_count_reasonable(self) -> None:
        """Sanity check: at least 40 providers registered."""
        data = yaml.safe_load(self.CONFIG_YAML_PATH.read_text())
        providers: dict[str, dict[str, object]] = data["providers"]
        assert len(providers) >= 40, f"Only {len(providers)} providers — expected at least 40"


# ---------------------------------------------------------------------------
# 3. SportsAggregatorType enum and VENUE_AGGREGATOR_TYPE mapping
# ---------------------------------------------------------------------------


class TestSportsAggregatorType:
    """SportsAggregatorType enum has the expected members."""

    def test_is_str_enum(self) -> None:
        from enum import StrEnum

        assert issubclass(SportsAggregatorType, StrEnum)

    def test_expected_members(self) -> None:
        expected = {
            "DIRECT_EXECUTION",
            "ODDS_AGGREGATOR",
            "EXECUTION_AGGREGATOR",
            "POSITION_AGGREGATOR",
        }
        actual = {m.name for m in SportsAggregatorType}
        missing = expected - actual
        assert not missing, f"SportsAggregatorType missing members: {missing}"

    def test_odds_aggregator_value(self) -> None:
        assert SportsAggregatorType.ODDS_AGGREGATOR == "odds_aggregator"

    def test_direct_execution_value(self) -> None:
        assert SportsAggregatorType.DIRECT_EXECUTION == "direct_execution"


class TestVenueAggregatorTypeMapping:
    """VENUE_AGGREGATOR_TYPE maps venues to their aggregator classification."""

    def test_odds_aggregators_mapped(self) -> None:
        from unified_api_contracts.registry.venue_constants import (
            ODDS_API,
            ODDSJAM,
            OPTICODDS,
        )

        for venue in (ODDS_API, ODDSJAM, OPTICODDS):
            assert venue in VENUE_AGGREGATOR_TYPE, f"Venue {venue} missing from VENUE_AGGREGATOR_TYPE"
            assert VENUE_AGGREGATOR_TYPE[venue] == SportsAggregatorType.ODDS_AGGREGATOR

    def test_exchange_venues_are_direct_execution(self) -> None:
        from unified_api_contracts.registry.venue_constants import SPORTS_EXCHANGE_VENUES

        for venue in SPORTS_EXCHANGE_VENUES:
            assert venue in VENUE_AGGREGATOR_TYPE, f"Exchange venue {venue} missing"
            assert VENUE_AGGREGATOR_TYPE[venue] == SportsAggregatorType.DIRECT_EXECUTION

    def test_all_values_are_aggregator_type(self) -> None:
        for venue, agg_type in VENUE_AGGREGATOR_TYPE.items():
            assert isinstance(agg_type, SportsAggregatorType), (
                f"Venue {venue} has non-SportsAggregatorType value: {agg_type}"
            )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_market_keys(fixture_data: dict[str, object]) -> set[str]:
    """Extract all market keys from a fixture JSON dict."""
    keys: set[str] = set()
    bookmakers = fixture_data.get("bookmakers", [])
    if not isinstance(bookmakers, list):
        return keys
    for bookmaker in bookmakers:
        if not isinstance(bookmaker, dict):
            continue
        markets = bookmaker.get("markets", [])
        if not isinstance(markets, list):
            continue
        for market in markets:
            if isinstance(market, dict) and "key" in market:
                key = market["key"]
                if isinstance(key, str):
                    keys.add(key)
    return keys


def _find_market(fixture_data: dict[str, object], market_key: str) -> dict[str, object] | None:
    """Find a specific market by key in a fixture JSON dict."""
    bookmakers = fixture_data.get("bookmakers", [])
    if not isinstance(bookmakers, list):
        return None
    for bookmaker in bookmakers:
        if not isinstance(bookmaker, dict):
            continue
        markets = bookmaker.get("markets", [])
        if not isinstance(markets, list):
            continue
        for market in markets:
            if isinstance(market, dict) and market.get("key") == market_key:
                return market
    return None
