"""Static venue coordinates for football stadiums — SSOT for weather data.

API Football's /teams endpoint returns venue metadata (name, city, capacity,
surface) but NOT geographic coordinates. This registry provides lat/lon for
major stadiums in the top European leagues so the weather pipeline can fetch
Open-Meteo data without a separate geocoding service.

Keys are SCREAMING_SNAKE_CASE venue IDs (matching ``build_venue_id()`` output).
Values are ``VenueCoordinates`` named tuples with latitude and longitude.

Coverage: EPL, La Liga, Bundesliga, Serie A, Ligue 1 (all 20 teams per league)
plus ~800 auto-geocoded venues from fixture data.

Data lives in ``data/sports_venue_coordinates.json`` — this module is a thin
loader that preserves the same public API (VENUE_COORDINATES dict,
VenueCoordinates named tuple, get_venue_coordinates function).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import NamedTuple


class VenueCoordinates(NamedTuple):
    """Geographic coordinates for a football stadium."""

    latitude: float
    longitude: float


_DATA_PATH = Path(__file__).parent / "data" / "sports_venue_coordinates.json"

_raw: dict[str, dict[str, float]] = json.loads(_DATA_PATH.read_text())

VENUE_COORDINATES: dict[str, VenueCoordinates] = {
    k: VenueCoordinates(latitude=v["latitude"], longitude=v["longitude"]) for k, v in _raw.items()
}


def get_venue_coordinates(venue_id: str) -> VenueCoordinates | None:
    """Look up coordinates by canonical venue_id (SCREAMING_SNAKE_CASE).

    Returns None if the venue is not in the registry.
    """
    return VENUE_COORDINATES.get(venue_id)
