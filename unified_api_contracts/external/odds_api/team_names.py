"""Canonical team ID → The Odds API / Understat display name mappings.

Used for:
- CLV tracking: matching OddsAPI team names back to canonical IDs
- Understat xG data joins: mapping canonical IDs to Understat's display names

Covers EPL (2014-2026) and Bundesliga (2014-2026).

Source: Ported from footballbets/utils/mapping.py (CANONICAL_TO_ODDS_API_*
        and CANONICAL_TO_UNDERSTAT_*)
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Canonical → OddsAPI display name
# ---------------------------------------------------------------------------

CANONICAL_TO_ODDS_API_EPL: dict[str, str] = {
    # Big 6
    "ARSENAL": "Arsenal",
    "CHELSEA": "Chelsea",
    "LIVERPOOL": "Liverpool",
    "MAN_CITY": "Manchester City",
    "MAN_UNITED": "Manchester United",
    "TOTTENHAM": "Tottenham Hotspur",
    # Established clubs
    "ASTON_VILLA": "Aston Villa",
    "EVERTON": "Everton",
    "LEICESTER": "Leicester City",
    "NEWCASTLE": "Newcastle United",
    "WEST_HAM": "West Ham United",
    "WOLVES": "Wolverhampton Wanderers",
    # Mid-table / recently promoted (2016-2026)
    "BOURNEMOUTH": "Bournemouth",
    "BRENTFORD": "Brentford",
    "BRIGHTON": "Brighton and Hove Albion",
    "BURNLEY": "Burnley",
    "CRYSTAL_PALACE": "Crystal Palace",
    "FULHAM": "Fulham",
    "LEEDS": "Leeds United",
    "NOTTM_FOREST": "Nottingham Forest",
    "SHEFFIELD_UNITED": "Sheffield United",
    "SOUTHAMPTON": "Southampton",
    "SUNDERLAND": "Sunderland",
    "IPSWICH": "Ipswich Town",
    "WATFORD": "Watford",
    # Relegated / historic
    "CARDIFF": "Cardiff",
    "HUDDERSFIELD": "Huddersfield",
    "HULL_CITY": "Hull City",
    "LUTON": "Luton",
    "MIDDLESBROUGH": "Middlesbrough",
    "NORWICH": "Norwich City",
    "QPR": "QPR",
    "READING": "Reading",
    "STOKE_CITY": "Stoke",
    "SWANSEA": "Swansea",
    "WEST_BROM": "West Brom",
    "WIGAN": "Wigan",
}

CANONICAL_TO_ODDS_API_BUNDESLIGA: dict[str, str] = {
    # Top clubs
    "BAYERN": "Bayern Munich",
    "DORTMUND": "Borussia Dortmund",
    "LEIPZIG": "RB Leipzig",
    "LEVERKUSEN": "Bayer Leverkusen",
    # Established clubs
    "FRANKFURT": "Eintracht Frankfurt",
    "FREIBURG": "SC Freiburg",
    "HOFFENHEIM": "TSG Hoffenheim",
    "MGLADBACH": "Borussia Monchengladbach",
    "MAINZ": "FSV Mainz 05",
    "STUTTGART": "VfB Stuttgart",
    "UNION_BERLIN": "Union Berlin",
    "WERDER_BREMEN": "Werder Bremen",
    "WOLFSBURG": "VfL Wolfsburg",
    # Mid-table / recently promoted
    "ARMINIA_BIELEFELD": "Arminia Bielefeld",
    "AUGSBURG": "Augsburg",
    "BOCHUM": "VfL Bochum",
    "COLOGNE": "FC Koln",
    "DARMSTADT": "Darmstadt",
    "FORTUNA_DUSSELDORF": "Fortuna Dusseldorf",
    "GREUTHER_FURTH": "Greuther Furth",
    "HAMBURG": "Hamburg",
    "HANNOVER": "Hannover",
    "HEIDENHEIM": "1. FC Heidenheim",
    "HERTHA": "Hertha Berlin",
    "HOLSTEIN_KIEL": "Holstein Kiel",
    "INGOLSTADT": "FC Ingolstadt 04",
    "NURNBERG": "FC Nurnberg",
    "PADERBORN": "Paderborn",
    "SCHALKE": "Schalke 04",
    "ST_PAULI": "FC St. Pauli",
}

# ---------------------------------------------------------------------------
# Canonical → Understat display name
# ---------------------------------------------------------------------------

CANONICAL_TO_UNDERSTAT_EPL: dict[str, str] = {
    "ARSENAL": "Arsenal",
    "ASTON_VILLA": "Aston Villa",
    "BOURNEMOUTH": "Bournemouth",
    "BRENTFORD": "Brentford",
    "BRIGHTON": "Brighton",
    "BURNLEY": "Burnley",
    "CARDIFF": "Cardiff",
    "CHELSEA": "Chelsea",
    "CRYSTAL_PALACE": "Crystal Palace",
    "EVERTON": "Everton",
    "FULHAM": "Fulham",
    "HUDDERSFIELD": "Huddersfield",
    "HULL_CITY": "Hull",
    "IPSWICH": "Ipswich",
    "LEEDS": "Leeds",
    "LEICESTER": "Leicester",
    "LIVERPOOL": "Liverpool",
    "LUTON": "Luton",
    "MAN_CITY": "Manchester City",
    "MAN_UNITED": "Manchester United",
    "MIDDLESBROUGH": "Middlesbrough",
    "NEWCASTLE": "Newcastle United",
    "NORWICH": "Norwich",
    "NOTTM_FOREST": "Nottingham Forest",
    "QPR": "Queens Park Rangers",
    "SHEFFIELD_UNITED": "Sheffield United",
    "SOUTHAMPTON": "Southampton",
    "STOKE_CITY": "Stoke",
    "SUNDERLAND": "Sunderland",
    "SWANSEA": "Swansea",
    "TOTTENHAM": "Tottenham",
    "WATFORD": "Watford",
    "WEST_BROM": "West Bromwich Albion",
    "WEST_HAM": "West Ham",
    "WOLVES": "Wolverhampton Wanderers",
}

CANONICAL_TO_UNDERSTAT_BUNDESLIGA: dict[str, str] = {
    "ARMINIA_BIELEFELD": "Arminia Bielefeld",
    "AUGSBURG": "Augsburg",
    "LEVERKUSEN": "Bayer Leverkusen",
    "BAYERN": "Bayern Munich",
    "BOCHUM": "Bochum",
    "DORTMUND": "Borussia Dortmund",
    "MGLADBACH": "Borussia M.Gladbach",
    "DARMSTADT": "Darmstadt",
    "FRANKFURT": "Eintracht Frankfurt",
    "COLOGNE": "FC Cologne",
    "HEIDENHEIM": "FC Heidenheim",
    "FORTUNA_DUSSELDORF": "Fortuna Duesseldorf",
    "FREIBURG": "Freiburg",
    "GREUTHER_FURTH": "Greuther Fuerth",
    "HAMBURG": "Hamburger SV",
    "HANNOVER": "Hannover 96",
    "HERTHA": "Hertha Berlin",
    "HOFFENHEIM": "Hoffenheim",
    "HOLSTEIN_KIEL": "Holstein Kiel",
    "INGOLSTADT": "Ingolstadt",
    "MAINZ": "Mainz 05",
    "NURNBERG": "Nuernberg",
    "PADERBORN": "Paderborn",
    "LEIPZIG": "RasenBallsport Leipzig",
    "SCHALKE": "Schalke 04",
    "ST_PAULI": "St. Pauli",
    "UNION_BERLIN": "Union Berlin",
    "STUTTGART": "VfB Stuttgart",
    "WERDER_BREMEN": "Werder Bremen",
    "WOLFSBURG": "Wolfsburg",
}


# ---------------------------------------------------------------------------
# Lookup functions
# ---------------------------------------------------------------------------


def get_odds_api_team_name(canonical_name: str, api_football_league_id: int) -> str | None:
    """Convert canonical team ID to OddsAPI display name.

    Args:
        canonical_name: Canonical team ID (e.g. ``"MAN_UNITED"``).
        api_football_league_id: API-Football league ID (39 = EPL, 78 = Bundesliga).

    Returns:
        OddsAPI display name (e.g. ``"Manchester United"``) or ``None`` if not found.
    """
    if api_football_league_id == 39:
        return CANONICAL_TO_ODDS_API_EPL.get(canonical_name)
    if api_football_league_id == 78:
        return CANONICAL_TO_ODDS_API_BUNDESLIGA.get(canonical_name)
    # Try both for other leagues
    result = CANONICAL_TO_ODDS_API_EPL.get(canonical_name)
    if result is not None:
        return result
    return CANONICAL_TO_ODDS_API_BUNDESLIGA.get(canonical_name)


def get_understat_team_name(canonical_name: str, league_id: str) -> str | None:
    """Convert canonical team ID to Understat display name.

    Args:
        canonical_name: Canonical team ID (e.g. ``"Bayern"``).
        league_id: Canonical league ID string (e.g. ``"EPL"``, ``"BUNDESLIGA"``).

    Returns:
        Understat display name (e.g. ``"Bayern Munich"``) or ``None`` if not found.
    """
    if "EPL" in league_id.upper() or "PREMIER" in league_id.upper():
        return CANONICAL_TO_UNDERSTAT_EPL.get(canonical_name)
    if "BUNDESLIGA" in league_id.upper() or "BUN" in league_id.upper():
        return CANONICAL_TO_UNDERSTAT_BUNDESLIGA.get(canonical_name)
    result = CANONICAL_TO_UNDERSTAT_EPL.get(canonical_name)
    if result is not None:
        return result
    return CANONICAL_TO_UNDERSTAT_BUNDESLIGA.get(canonical_name)


__all__ = [
    "CANONICAL_TO_ODDS_API_BUNDESLIGA",
    "CANONICAL_TO_ODDS_API_EPL",
    "CANONICAL_TO_UNDERSTAT_BUNDESLIGA",
    "CANONICAL_TO_UNDERSTAT_EPL",
    "get_odds_api_team_name",
    "get_understat_team_name",
]
