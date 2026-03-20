"""Kalshi sports market mappings — football fixtures via structured tickers.

Kalshi uses structured event tickers for sports: {SPORT}-{LEAGUE}-{TEAM1}-{TEAM2}-{DATE}
Example: SOCCER-EPL-ARS-CHE-26MAR22

Sports scope: football leagues with Odds API coverage (same as Polymarket).
"""

from __future__ import annotations

# Kalshi ticker prefixes for sports leagues
KALSHI_SPORTS_TICKER_PREFIXES: dict[str, str] = {
    "EPL": "SOCCER-EPL",
    "BUN": "SOCCER-BUN",
    "LAL": "SOCCER-LAL",
    "SEA": "SOCCER-SEA",
    "FL1": "SOCCER-FL1",
    "UCL": "SOCCER-UCL",
    "NBA": "NBA",
    "NFL": "NFL",
    "MLB": "MLB",
}


def build_kalshi_sports_ticker(
    league_id: str,
    home_team_id: str,
    away_team_id: str,
    date_str: str,
) -> str | None:
    """Build a Kalshi event ticker from canonical IDs.

    Args:
        league_id: Canonical league ID (e.g. "EPL")
        home_team_id: Canonical team ID (e.g. "ARS")
        away_team_id: Canonical team ID (e.g. "CHE")
        date_str: Date in DDMMMYY format (e.g. "22MAR26")

    Returns:
        Kalshi ticker (e.g. "SOCCER-EPL-ARS-CHE-22MAR26") or None if league not mapped.
    """
    prefix = KALSHI_SPORTS_TICKER_PREFIXES.get(league_id)
    if prefix is None:
        return None
    return f"{prefix}-{home_team_id}-{away_team_id}-{date_str}"


def parse_kalshi_sports_ticker(ticker: str) -> dict[str, str] | None:
    """Parse a Kalshi sports ticker into components.

    Returns dict with keys: league_id, home_team, away_team, date
    or None if not a recognized sports ticker format.
    """
    parts = ticker.split("-")
    if len(parts) < 4:
        return None

    # Find matching prefix
    for league_id, prefix in KALSHI_SPORTS_TICKER_PREFIXES.items():
        prefix_parts = prefix.split("-")
        if parts[: len(prefix_parts)] == prefix_parts:
            remaining = parts[len(prefix_parts) :]
            if len(remaining) >= 3:
                return {
                    "league_id": league_id,
                    "home_team": remaining[0],
                    "away_team": remaining[1],
                    "date": remaining[2],
                }
    return None
