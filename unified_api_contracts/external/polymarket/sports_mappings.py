"""Polymarket sports market mappings — football fixtures via Odds API leagues.

Maps canonical fixture IDs to Polymarket condition_ids for football leagues
currently covered by both Odds API and Polymarket.

Sports scope: football leagues in LEAGUE_REGISTRY with Odds API coverage.
Polymarket sports markets use tag_slug="soccer" or "football".
"""

from __future__ import annotations

POLYMARKET_SPORTS_TAG_SLUGS: frozenset[str] = frozenset(
    {
        "soccer",
        "football",
        "premier-league",
        "champions-league",
        "bundesliga",
        "la-liga",
        "serie-a",
        "ligue-1",
        "nba",
        "nfl",
        "mlb",
    }
)

# NOTE: Polymarket sports markets are ephemeral (created per matchweek/season).
# Static mapping tables are NOT practical — resolution is dynamic via Gamma API.
# This module provides TAG constants + helpers for runtime discovery.


def get_polymarket_sports_tag_for_league(league_id: str) -> str | None:
    """Map canonical league_id to Polymarket tag slug for Gamma API filtering.

    Returns None if the league has no known Polymarket tag.
    """
    league_to_tag: dict[str, str] = {
        "EPL": "premier-league",
        "BUN": "bundesliga",
        "LAL": "la-liga",
        "SEA": "serie-a",
        "FL1": "ligue-1",
        "UCL": "champions-league",
        "UEL": "champions-league",  # Europa uses same tag
        "NBA": "nba",
        "NFL": "nfl",
        "MLB": "mlb",
    }
    return league_to_tag.get(league_id)
