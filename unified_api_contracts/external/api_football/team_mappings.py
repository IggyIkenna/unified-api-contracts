"""API-Football team name → canonical team ID mappings.

Canonical team IDs follow SCREAMING_SNAKE_CASE convention:
- ``MAN_CITY``, ``TOTTENHAM``, ``DORTMUND``, ``AJAX``

Covers EPL (2010-2026) and Bundesliga (2010-2026), including promoted and
recently relegated teams.

Source: Ported from footballbets/utils/mapping.py and
        instruments-service/instruments_service/sports/team_mapping_data*.py
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# EPL: canonical_team_id → list of known Betfair/display name variations
# ---------------------------------------------------------------------------

EPL_TEAM_ALIASES: dict[str, list[str]] = {
    # Current + recent EPL teams (2019-2026)
    "ARSENAL": ["ARSENAL", "ARSENAL FC", "Arsenal FC", "AFC"],
    "ASTON_VILLA": ["ASTON VILLA", "VILLA", "Aston Villa"],
    "BOURNEMOUTH": ["BOURNEMOUTH", "AFC BOURNEMOUTH", "Bournemouth"],
    "BRENTFORD": ["BRENTFORD", "BRENTFORD FC", "Brentford"],
    "BRIGHTON": [
        "BRIGHTON",
        "BRIGHTON & HOVE ALBION",
        "BRIGHTON AND HOVE ALBION",
        "Brighton and Hove Albion",
    ],
    "BURNLEY": ["BURNLEY", "BURNLEY FC", "Burnley"],
    "CARDIFF": ["CARDIFF", "CARDIFF CITY", "Cardiff City"],
    "CHELSEA": ["CHELSEA", "CHELSEA FC", "Chelsea FC"],
    "CRYSTAL_PALACE": ["CRYSTAL PALACE", "C PALACE", "PALACE", "Crystal Palace"],
    "EVERTON": ["EVERTON", "EVERTON FC", "Everton FC"],
    "FULHAM": ["FULHAM", "FULHAM FC", "Fulham FC"],
    "HUDDERSFIELD": ["HUDDERSFIELD", "HUDDERSFIELD TOWN", "Huddersfield Town"],
    "IPSWICH": ["IPSWICH", "IPSWICH TOWN", "Ipswich Town"],
    "LEEDS": ["LEEDS", "LEEDS UNITED", "LEEDS UTD", "Leeds United"],
    "LEICESTER": ["LEICESTER", "LEICESTER CITY", "Leicester City"],
    "LIVERPOOL": ["LIVERPOOL", "LIVERPOOL FC", "Liverpool FC"],
    "LUTON": ["LUTON", "LUTON TOWN", "Luton Town"],
    "MAN_CITY": ["MANCHESTER CITY", "MAN CITY", "MAN C", "Manchester City"],
    "MAN_UNITED": [
        "MANCHESTER UNITED",
        "MAN UNITED",
        "MAN UTD",
        "MANCHESTER UTD",
        "Manchester United",
    ],
    "NEWCASTLE": ["NEWCASTLE", "NEWCASTLE UNITED", "NEWCASTLE UTD", "Newcastle United"],
    "NORWICH": ["NORWICH", "NORWICH CITY", "Norwich City"],
    "NOTTM_FOREST": [
        "NOTTINGHAM FOREST",
        "NOTT'M FOREST",
        "NOTTM FOREST",
        "FOREST",
        "Nottingham Forest",
    ],
    "SHEFFIELD_UNITED": [
        "SHEFFIELD UNITED",
        "SHEFF UTD",
        "SHEFF UNITED",
        "SHEFFIELD UTD",
        "SHEFFIELD U",
        "Sheffield United",
        "Sheffield Utd",
    ],
    "SOUTHAMPTON": ["SOUTHAMPTON", "SOUTHAMPTON FC", "Southampton FC"],
    "SUNDERLAND": ["SUNDERLAND", "SUNDERLAND AFC", "Sunderland AFC"],
    "TOTTENHAM": ["TOTTENHAM", "TOTTENHAM HOTSPUR", "SPURS", "Tottenham Hotspur"],
    "WATFORD": ["WATFORD", "WATFORD FC", "Watford FC"],
    "WEST_HAM": ["WEST HAM", "WEST HAM UNITED", "WEST HAM UTD", "West Ham United"],
    "WOLVES": ["WOLVES", "WOLVERHAMPTON", "WOLVERHAMPTON WANDERERS", "Wolverhampton Wanderers"],
    # Historic EPL teams (2010-2019)
    "BIRMINGHAM": ["BIRMINGHAM", "BIRMINGHAM CITY", "Birmingham City"],
    "BLACKBURN": ["BLACKBURN", "BLACKBURN ROVERS", "Blackburn Rovers"],
    "BLACKPOOL": ["BLACKPOOL", "Blackpool"],
    "BOLTON": ["BOLTON", "BOLTON WANDERERS", "Bolton Wanderers"],
    "HULL_CITY": ["HULL CITY", "HULL", "Hull City"],
    "MIDDLESBROUGH": ["MIDDLESBROUGH", "BORO", "Middlesbrough"],
    "QPR": ["QPR", "QUEENS PARK RANGERS", "Queens Park Rangers"],
    "READING": ["READING", "Reading"],
    "STOKE_CITY": ["STOKE CITY", "STOKE", "Stoke City"],
    "SWANSEA": ["SWANSEA", "SWANSEA CITY", "Swansea City"],
    "WEST_BROM": ["WEST BROM", "WEST BROMWICH ALBION", "West Bromwich Albion", "WBA"],
    "WIGAN": ["WIGAN", "WIGAN ATHLETIC", "Wigan Athletic"],
}

# ---------------------------------------------------------------------------
# Bundesliga: canonical_team_id → list of known Betfair/display name variations
# ---------------------------------------------------------------------------

BUNDESLIGA_TEAM_ALIASES: dict[str, list[str]] = {
    "ARMINIA_BIELEFELD": ["ARMINIA BIELEFELD", "BIELEFELD", "ARMINIA", "Arminia Bielefeld"],
    "AUGSBURG": ["AUGSBURG", "FC AUGSBURG", "FC Augsburg"],
    "BAYERN": ["BAYERN", "BAYERN MUNICH", "FC BAYERN MUNICH", "BAYERN MUNCHEN", "Bayern Munich"],
    "BOCHUM": ["BOCHUM", "VFL BOCHUM", "VfL Bochum"],
    "DORTMUND": ["BORUSSIA DORTMUND", "DORTMUND", "BVB", "Borussia Dortmund"],
    "MGLADBACH": [
        "BORUSSIA MONCHENGLADBACH",
        "BORUSSIA M'GLADBACH",
        "MGLADBACH",
        "MONCHENGLADBACH",
        "M'GLADBACH",
        "Borussia Monchengladbach",
        "Borussia Mönchengladbach",
    ],
    "COLOGNE": ["COLOGNE", "FC KOLN", "FC COLOGNE", "KOLN", "FC Cologne", "1.FC Köln", "FC Koln"],
    "DARMSTADT": ["DARMSTADT", "DARMSTADT 98", "SV Darmstadt 98"],
    "FRANKFURT": ["EINTRACHT FRANKFURT", "FRANKFURT", "Eintracht Frankfurt"],
    "FREIBURG": ["FREIBURG", "SC FREIBURG", "SC Freiburg"],
    "GREUTHER_FURTH": [
        "GREUTHER FURTH",
        "GREUTHER FÜRTH",
        "SpVgg Greuther Fürth",
        "Greuther Furth",
    ],
    "HAMBURG": ["HAMBURGER SV", "HAMBURG", "HSV", "Hamburger SV"],
    "HANNOVER": ["HANNOVER", "HANNOVER 96", "Hannover 96"],
    "HERTHA": ["HERTHA BERLIN", "HERTHA", "HERTHA BSC", "Hertha Berlin", "Hertha BSC"],
    "HOFFENHEIM": ["HOFFENHEIM", "TSG HOFFENHEIM", "1899 Hoffenheim", "TSG Hoffenheim"],
    "HEIDENHEIM": ["HEIDENHEIM", "FC HEIDENHEIM", "1. FC Heidenheim", "FC Heidenheim"],
    "HOLSTEIN_KIEL": ["HOLSTEIN KIEL", "KIEL", "Holstein Kiel"],
    "KAISERSLAUTERN": ["KAISERSLAUTERN", "FC KAISERSLAUTERN", "1. FC Kaiserslautern"],
    "KARLSRUHE": ["KARLSRUHE", "KARLSRUHER SC", "Karlsruher SC"],
    "LEVERKUSEN": ["LEVERKUSEN", "BAYER LEVERKUSEN", "Bayer Leverkusen"],
    "MAINZ": ["MAINZ", "MAINZ 05", "FSV MAINZ 05", "FSV Mainz 05", "Mainz 05"],
    "PADERBORN": ["PADERBORN", "SC PADERBORN", "SC Paderborn 07"],
    "LEIPZIG": ["LEIPZIG", "RB LEIPZIG", "RB Leipzig"],
    "SCHALKE": ["SCHALKE", "SCHALKE 04", "FC SCHALKE 04", "Schalke 04", "FC Schalke 04"],
    "ST_PAULI": ["ST PAULI", "ST. PAULI", "FC ST PAULI", "FC St. Pauli", "St Pauli"],
    "STUTTGART": ["STUTTGART", "VFB STUTTGART", "VfB Stuttgart"],
    "UNION_BERLIN": ["UNION BERLIN", "UNION", "FC UNION BERLIN", "Union Berlin"],
    "WERDER_BREMEN": ["WERDER BREMEN", "BREMEN", "SV WERDER BREMEN", "Werder Bremen"],
    "WOLFSBURG": ["WOLFSBURG", "VFL WOLFSBURG", "VfL Wolfsburg"],
    # Historical Bundesliga teams
    "BRAUNSCHWEIG": ["BRAUNSCHWEIG", "Eintracht Braunschweig"],
    "ELVERSBERG": ["ELVERSBERG", "SV Elversberg"],
    "FORTUNA_DUSSELDORF": ["FORTUNA DUSSELDORF", "Fortuna Düsseldorf", "Fortuna Dusseldorf"],
    "INGOLSTADT": ["INGOLSTADT", "FC INGOLSTADT 04", "FC Ingolstadt 04"],
    "NURNBERG": ["NURNBERG", "FC NURNBERG", "1. FC Nürnberg", "FC Nurnberg"],
}

# ---------------------------------------------------------------------------
# Build reverse lookup dicts: raw name (upper) → canonical_team_id
# ---------------------------------------------------------------------------

_BETFAIR_EPL: dict[str, str] = {}
for _canonical, _variations in EPL_TEAM_ALIASES.items():
    for _var in _variations:
        _BETFAIR_EPL[_var.upper()] = _canonical

_BETFAIR_BL: dict[str, str] = {}
for _canonical, _variations in BUNDESLIGA_TEAM_ALIASES.items():
    for _var in _variations:
        _BETFAIR_BL[_var.upper()] = _canonical

# Combined Betfair → canonical (both leagues)
BETFAIR_TO_CANONICAL: dict[str, str] = {**_BETFAIR_EPL, **_BETFAIR_BL}

# ---------------------------------------------------------------------------
# API-Football display names → canonical team IDs
# ---------------------------------------------------------------------------

API_FOOTBALL_TO_CANONICAL_EPL: dict[str, str] = {
    # Current EPL Teams (2019-2026)
    "Arsenal": "ARSENAL",
    "Aston Villa": "ASTON_VILLA",
    "Bournemouth": "BOURNEMOUTH",
    "Brentford": "BRENTFORD",
    "Brighton": "BRIGHTON",
    "Brighton & Hove Albion": "BRIGHTON",
    "Burnley": "BURNLEY",
    "Cardiff": "CARDIFF",
    "Chelsea": "CHELSEA",
    "Crystal Palace": "CRYSTAL_PALACE",
    "Everton": "EVERTON",
    "Fulham": "FULHAM",
    "Huddersfield": "HUDDERSFIELD",
    "Ipswich": "IPSWICH",
    "Leeds": "LEEDS",
    "Leeds United": "LEEDS",
    "Leicester": "LEICESTER",
    "Leicester City": "LEICESTER",
    "Liverpool": "LIVERPOOL",
    "Luton": "LUTON",
    "Luton Town": "LUTON",
    "Manchester City": "MAN_CITY",
    "Manchester United": "MAN_UNITED",
    "Newcastle": "NEWCASTLE",
    "Newcastle United": "NEWCASTLE",
    "Norwich": "NORWICH",
    "Norwich City": "NORWICH",
    "Nottingham Forest": "NOTTM_FOREST",
    "Sheffield Utd": "SHEFFIELD_UNITED",
    "Sheffield United": "SHEFFIELD_UNITED",
    "Southampton": "SOUTHAMPTON",
    "Sunderland": "SUNDERLAND",
    "Tottenham": "TOTTENHAM",
    "Tottenham Hotspur": "TOTTENHAM",
    "Watford": "WATFORD",
    "West Ham": "WEST_HAM",
    "West Ham United": "WEST_HAM",
    "Wolves": "WOLVES",
    "Wolverhampton Wanderers": "WOLVES",
    # Historical EPL (2010-2019)
    "Birmingham": "BIRMINGHAM",
    "West Brom": "WEST_BROM",
    "West Bromwich Albion": "WEST_BROM",
    "Wigan": "WIGAN",
    "Blackburn": "BLACKBURN",
    "Blackburn Rovers": "BLACKBURN",
    "Bolton": "BOLTON",
    "Bolton Wanderers": "BOLTON",
    "Stoke City": "STOKE_CITY",
    "Stoke": "STOKE_CITY",
    "Blackpool": "BLACKPOOL",
    "Swansea": "SWANSEA",
    "Swansea City": "SWANSEA",
    "Reading": "READING",
    "Hull City": "HULL_CITY",
    "Hull": "HULL_CITY",
    "Middlesbrough": "MIDDLESBROUGH",
    "QPR": "QPR",
    "Queens Park Rangers": "QPR",
}

API_FOOTBALL_TO_CANONICAL_BUNDESLIGA: dict[str, str] = {
    "Arminia Bielefeld": "ARMINIA_BIELEFELD",
    "Augsburg": "AUGSBURG",
    "FC Augsburg": "AUGSBURG",
    "Bayern Munich": "BAYERN",
    "Bayern München": "BAYERN",
    "Bochum": "BOCHUM",
    "VfL Bochum": "BOCHUM",
    "Borussia Dortmund": "DORTMUND",
    "Borussia Monchengladbach": "MGLADBACH",
    "Borussia Mönchengladbach": "MGLADBACH",
    "FC Cologne": "COLOGNE",
    "Koln": "COLOGNE",
    "1.FC Köln": "COLOGNE",
    "FC Köln": "COLOGNE",
    "Darmstadt": "DARMSTADT",
    "SV Darmstadt 98": "DARMSTADT",
    "Eintracht Frankfurt": "FRANKFURT",
    "Freiburg": "FREIBURG",
    "SC Freiburg": "FREIBURG",
    "Greuther Furth": "GREUTHER_FURTH",
    "SpVgg Greuther Fürth": "GREUTHER_FURTH",
    "Hamburger SV": "HAMBURG",
    "Hamburg": "HAMBURG",
    "Hannover 96": "HANNOVER",
    "Hannover": "HANNOVER",
    "Hertha Berlin": "HERTHA",
    "Hertha BSC": "HERTHA",
    "Hoffenheim": "HOFFENHEIM",
    "1899 Hoffenheim": "HOFFENHEIM",
    "TSG Hoffenheim": "HOFFENHEIM",
    "Heidenheim": "HEIDENHEIM",
    "1. FC Heidenheim": "HEIDENHEIM",
    "Holstein Kiel": "HOLSTEIN_KIEL",
    "Kaiserslautern": "KAISERSLAUTERN",
    "1. FC Kaiserslautern": "KAISERSLAUTERN",
    "Karlsruhe": "KARLSRUHE",
    "Karlsruher SC": "KARLSRUHE",
    "Bayer Leverkusen": "LEVERKUSEN",
    "Mainz": "MAINZ",
    "Mainz 05": "MAINZ",
    "FSV Mainz 05": "MAINZ",
    "Paderborn": "PADERBORN",
    "SC Paderborn 07": "PADERBORN",
    "RB Leipzig": "LEIPZIG",
    "Schalke 04": "SCHALKE",
    "FC Schalke 04": "SCHALKE",
    "FC St. Pauli": "ST_PAULI",
    "St Pauli": "ST_PAULI",
    "VfB Stuttgart": "STUTTGART",
    "Stuttgart": "STUTTGART",
    "Union Berlin": "UNION_BERLIN",
    "Werder Bremen": "WERDER_BREMEN",
    "Wolfsburg": "WOLFSBURG",
    "VfL Wolfsburg": "WOLFSBURG",
    # Historical
    "1. FC Nürnberg": "NURNBERG",
    "Fortuna Düsseldorf": "FORTUNA_DUSSELDORF",
    "Fortuna Dusseldorf": "FORTUNA_DUSSELDORF",
    "Eintracht Braunschweig": "BRAUNSCHWEIG",
    "FC Ingolstadt 04": "INGOLSTADT",
    "SV Elversberg": "ELVERSBERG",
}

# Combined API-Football → canonical (both leagues)
API_FOOTBALL_TO_CANONICAL: dict[str, str] = {
    **API_FOOTBALL_TO_CANONICAL_EPL,
    **API_FOOTBALL_TO_CANONICAL_BUNDESLIGA,
}


# ---------------------------------------------------------------------------
# Lookup functions
# ---------------------------------------------------------------------------


def get_canonical_team_name_from_api_football(api_football_name: str) -> str | None:
    """Convert API-Football team display name to canonical team ID.

    Args:
        api_football_name: Team name as returned by the API-Football API
            (e.g. ``"Manchester United"``, ``"Bayern Munich"``).

    Returns:
        Canonical team ID (e.g. ``"MAN_UNITED"``, ``"BAYERN"``) or ``None``
        if not found in the mapping.
    """
    if not api_football_name:
        return None
    return API_FOOTBALL_TO_CANONICAL.get(api_football_name)


def get_canonical_team_name_from_betfair(betfair_name: str) -> str | None:
    """Convert a Betfair team name variation to the canonical team ID.

    The lookup is case-insensitive (the input is uppercased before matching).

    Args:
        betfair_name: Team name as it appears in Betfair market data.

    Returns:
        Canonical team ID (e.g. ``"MAN_CITY"``) or ``None`` if not found.
    """
    if not betfair_name:
        return None
    normalized = betfair_name.upper().strip()
    result = BETFAIR_TO_CANONICAL.get(normalized)
    if result is not None:
        return result
    # Fuzzy fallback: substring match
    for key, canonical in BETFAIR_TO_CANONICAL.items():
        if normalized in key or key in normalized:
            return canonical
    return None


__all__ = [
    "API_FOOTBALL_TO_CANONICAL",
    "API_FOOTBALL_TO_CANONICAL_BUNDESLIGA",
    "API_FOOTBALL_TO_CANONICAL_EPL",
    "BETFAIR_TO_CANONICAL",
    "BUNDESLIGA_TEAM_ALIASES",
    "EPL_TEAM_ALIASES",
    "get_canonical_team_name_from_api_football",
    "get_canonical_team_name_from_betfair",
]
