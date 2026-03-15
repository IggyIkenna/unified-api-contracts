"""Integration tests validating registry covers all consumer expectations."""

from __future__ import annotations

from unified_api_contracts.registry.venue_constants import (
    CLOB_VENUES,
    DEX_VENUES,
    INSTRUMENT_TYPES_BY_VENUE,
    SPORTS_BET_PLACEMENT_VENUES,
    SPORTS_DATA_VENUES,
    SPORTS_DFS_VENUES,
    SPORTS_VENUES,
    ZERO_ALPHA_VENUES,
)
from unified_api_contracts.registry.venue_manifest import BETTING_SPORTS_VENUES


def test_all_clob_venues_in_instrument_types() -> None:
    """Every CLOB venue has an INSTRUMENT_TYPES_BY_VENUE entry."""
    for venue in CLOB_VENUES:
        assert venue in INSTRUMENT_TYPES_BY_VENUE, f"CLOB venue missing from INSTRUMENT_TYPES_BY_VENUE: {venue}"


def test_all_dex_venues_in_instrument_types() -> None:
    """Every DEX venue has an INSTRUMENT_TYPES_BY_VENUE entry."""
    for venue in DEX_VENUES:
        assert venue in INSTRUMENT_TYPES_BY_VENUE, f"DEX venue missing from INSTRUMENT_TYPES_BY_VENUE: {venue}"


def test_all_zero_alpha_venues_in_instrument_types() -> None:
    """Every ZERO_ALPHA venue has an INSTRUMENT_TYPES_BY_VENUE entry."""
    for venue in ZERO_ALPHA_VENUES:
        assert venue in INSTRUMENT_TYPES_BY_VENUE, f"ZERO_ALPHA venue missing from INSTRUMENT_TYPES_BY_VENUE: {venue}"


def test_all_bet_placement_venues_in_instrument_types() -> None:
    """Every bet-placement sports venue has an INSTRUMENT_TYPES_BY_VENUE entry."""
    for venue in SPORTS_BET_PLACEMENT_VENUES:
        assert venue in INSTRUMENT_TYPES_BY_VENUE, (
            f"SPORTS_BET_PLACEMENT venue missing from INSTRUMENT_TYPES_BY_VENUE: {venue}"
        )


def test_all_dfs_venues_in_instrument_types() -> None:
    """Every DFS venue has an INSTRUMENT_TYPES_BY_VENUE entry."""
    for venue in SPORTS_DFS_VENUES:
        assert venue in INSTRUMENT_TYPES_BY_VENUE, f"DFS venue missing from INSTRUMENT_TYPES_BY_VENUE: {venue}"


def test_data_venues_are_subset_of_sports() -> None:
    """SPORTS_DATA_VENUES are a subset of SPORTS_VENUES (data-only, no instrument types)."""
    assert SPORTS_DATA_VENUES.issubset(SPORTS_VENUES), (
        f"SPORTS_DATA_VENUES not subset of SPORTS_VENUES: {SPORTS_DATA_VENUES - SPORTS_VENUES}"
    )


def test_betting_sports_venues_keys_exist() -> None:
    """Every key in BETTING_SPORTS_VENUES manifest has expected fields."""
    for venue_key, contract in BETTING_SPORTS_VENUES.items():
        assert isinstance(venue_key, str), f"Venue key must be str, got {type(venue_key)}"
        assert "has_rest" in contract, f"BETTING_SPORTS venue {venue_key} missing has_rest"
        assert "response_schema_classes" in contract, (
            f"BETTING_SPORTS venue {venue_key} missing response_schema_classes"
        )
