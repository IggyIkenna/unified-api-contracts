"""Per-league team-name alias tables for non-soccer prediction sports leagues.

Mirrors the soccer precedent (``external/api_football/team_mappings.py``) so that
Kalshi's city-only venue renderings ("Seattle") and Polymarket's team-name
renderings ("Seattle Mariners") canonicalise to the same ``canonical_team_id``
before :meth:`SportsFixtureKey.pairing_key` is computed.

Canonical team IDs follow SCREAMING_SNAKE_CASE convention, same as the soccer table.

Source: Kalshi event titles sampled live 2026-08-05 from
``api.elections.kalshi.com/trade-api/v2/events?series_ticker=KX{MLBGAME,NFLGAME,NBAGAME}``.
Polymarket names derived from well-known public team rosters (validated against the
existing ``test_prediction_fixture_parsing.py`` test fixtures which confirm the
Kalshi title shape). Each alias set covers the forms BOTH venues actually render,
so the same team ALWAYS produces the same canonical id regardless of source venue.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Final

# ---------------------------------------------------------------------------
# MLB: canonical_team_id → known Kalshi / Polymarket name variations
# ---------------------------------------------------------------------------

MLB_TEAM_ALIASES: dict[str, list[str]] = {
    # American League East
    "BALTIMORE_ORIOLES": [
        "BALTIMORE",
        "BALTIMORE ORIOLES",
        "ORIOLES",
        "Baltimore",
        "Baltimore Orioles",
    ],
    "BOSTON_RED_SOX": [
        "BOSTON",
        "BOSTON RED SOX",
        "RED SOX",
        "Boston",
        "Boston Red Sox",
    ],
    "NEW_YORK_YANKEES": [
        "NEW YORK Y",
        "NEW YORK YANKEES",
        "YANKEES",
        "New York Y",
        "New York Yankees",
    ],
    "TAMPA_BAY_RAYS": [
        "TAMPA BAY",
        "TAMPA BAY RAYS",
        "RAYS",
        "Tampa Bay",
        "Tampa Bay Rays",
    ],
    "TORONTO_BLUE_JAYS": [
        "TORONTO",
        "TORONTO BLUE JAYS",
        "BLUE JAYS",
        "Toronto",
        "Toronto Blue Jays",
    ],
    # American League Central
    "CHICAGO_WHITE_SOX": [
        "CHICAGO W",
        "CHICAGO WHITE SOX",
        "WHITE SOX",
        "Chicago W",
        "Chicago White Sox",
    ],
    "CLEVELAND_GUARDIANS": [
        "CLEVELAND",
        "CLEVELAND GUARDIANS",
        "GUARDIANS",
        "Cleveland",
        "Cleveland Guardians",
    ],
    "DETROIT_TIGERS": [
        "DETROIT",
        "DETROIT TIGERS",
        "TIGERS",
        "Detroit",
        "Detroit Tigers",
    ],
    "KANSAS_CITY_ROYALS": [
        "KANSAS CITY",
        "KANSAS CITY ROYALS",
        "ROYALS",
        "Kansas City",
        "Kansas City Royals",
    ],
    "MINNESOTA_TWINS": [
        "MINNESOTA",
        "MINNESOTA TWINS",
        "TWINS",
        "Minnesota",
        "Minnesota Twins",
    ],
    # American League West
    "HOUSTON_ASTROS": [
        "HOUSTON",
        "HOUSTON ASTROS",
        "ASTROS",
        "Houston",
        "Houston Astros",
    ],
    "LOS_ANGELES_ANGELS": [
        "LOS ANGELES A",
        "LOS ANGELES ANGELS",
        "ANGELS",
        "LA ANGELS",
        "Los Angeles A",
        "Los Angeles Angels",
    ],
    "OAKLAND_ATHLETICS": [
        "A'S",
        "ATHLETICS",
        "OAKLAND",
        "OAKLAND ATHLETICS",
        "OAKLAND A'S",
        "A's",
        "Oakland",
        "Oakland Athletics",
    ],
    "SEATTLE_MARINERS": [
        "SEATTLE",
        "SEATTLE MARINERS",
        "MARINERS",
        "Seattle",
        "Seattle Mariners",
    ],
    "TEXAS_RANGERS": [
        "TEXAS",
        "TEXAS RANGERS",
        "RANGERS",
        "Texas",
        "Texas Rangers",
    ],
    # National League East
    "ATLANTA_BRAVES": [
        "ATLANTA",
        "ATLANTA BRAVES",
        "BRAVES",
        "Atlanta",
        "Atlanta Braves",
    ],
    "MIAMI_MARLINS": [
        "MIAMI",
        "MIAMI MARLINS",
        "MARLINS",
        "Miami",
        "Miami Marlins",
    ],
    "NEW_YORK_METS": [
        "NEW YORK M",
        "NEW YORK METS",
        "METS",
        "New York M",
        "New York Mets",
    ],
    "PHILADELPHIA_PHILLIES": [
        "PHILADELPHIA",
        "PHILADELPHIA PHILLIES",
        "PHILLIES",
        "Philadelphia",
        "Philadelphia Phillies",
    ],
    "WASHINGTON_NATIONALS": [
        "WASHINGTON",
        "WASHINGTON NATIONALS",
        "NATIONALS",
        "Washington",
        "Washington Nationals",
    ],
    # National League Central
    "CHICAGO_CUBS": [
        "CHICAGO C",
        "CHICAGO CUBS",
        "CUBS",
        "Chicago C",
        "Chicago Cubs",
    ],
    "CINCINNATI_REDS": [
        "CINCINNATI",
        "CINCINNATI REDS",
        "REDS",
        "Cincinnati",
        "Cincinnati Reds",
    ],
    "MILWAUKEE_BREWERS": [
        "MILWAUKEE",
        "MILWAUKEE BREWERS",
        "BREWERS",
        "Milwaukee",
        "Milwaukee Brewers",
    ],
    "PITTSBURGH_PIRATES": [
        "PITTSBURGH",
        "PITTSBURGH PIRATES",
        "PIRATES",
        "Pittsburgh",
        "Pittsburgh Pirates",
    ],
    "ST_LOUIS_CARDINALS": [
        "ST. LOUIS",
        "ST LOUIS",
        "ST. LOUIS CARDINALS",
        "ST LOUIS CARDINALS",
        "CARDINALS",
        "St. Louis",
        "St Louis",
        "St. Louis Cardinals",
    ],
    # National League West
    "ARIZONA_DIAMONDBACKS": [
        "ARIZONA",
        "ARIZONA DIAMONDBACKS",
        "DIAMONDBACKS",
        "Arizona",
        "Arizona Diamondbacks",
    ],
    "COLORADO_ROCKIES": [
        "COLORADO",
        "COLORADO ROCKIES",
        "ROCKIES",
        "Colorado",
        "Colorado Rockies",
    ],
    "LOS_ANGELES_DODGERS": [
        "LOS ANGELES D",
        "LOS ANGELES DODGERS",
        "DODGERS",
        "LA DODGERS",
        "Los Angeles D",
        "Los Angeles Dodgers",
    ],
    "SAN_DIEGO_PADRES": [
        "SAN DIEGO",
        "SAN DIEGO PADRES",
        "PADRES",
        "San Diego",
        "San Diego Padres",
    ],
    "SAN_FRANCISCO_GIANTS": [
        "SAN FRANCISCO",
        "SAN FRANCISCO GIANTS",
        "GIANTS",
        "San Francisco",
        "San Francisco Giants",
    ],
}

# ---------------------------------------------------------------------------
# NFL: canonical_team_id → known Kalshi / Polymarket name variations
# ---------------------------------------------------------------------------

NFL_TEAM_ALIASES: dict[str, list[str]] = {
    # AFC East
    "BUFFALO_BILLS": [
        "BUFFALO",
        "BUFFALO BILLS",
        "BILLS",
        "Buffalo",
        "Buffalo Bills",
    ],
    "MIAMI_DOLPHINS": [
        "MIAMI",
        "MIAMI DOLPHINS",
        "DOLPHINS",
        "Miami",
        "Miami Dolphins",
    ],
    "NEW_ENGLAND_PATRIOTS": [
        "NEW ENGLAND",
        "NEW ENGLAND PATRIOTS",
        "PATRIOTS",
        "New England",
        "New England Patriots",
    ],
    "NEW_YORK_JETS": [
        "NEW YORK J",
        "NEW YORK JETS",
        "JETS",
        "New York J",
        "New York Jets",
    ],
    # AFC North
    "BALTIMORE_RAVENS": [
        "BALTIMORE",
        "BALTIMORE RAVENS",
        "RAVENS",
        "Baltimore",
        "Baltimore Ravens",
    ],
    "CINCINNATI_BENGALS": [
        "CINCINNATI",
        "CINCINNATI BENGALS",
        "BENGALS",
        "Cincinnati",
        "Cincinnati Bengals",
    ],
    "CLEVELAND_BROWNS": [
        "CLEVELAND",
        "CLEVELAND BROWNS",
        "BROWNS",
        "Cleveland",
        "Cleveland Browns",
    ],
    "PITTSBURGH_STEELERS": [
        "PITTSBURGH",
        "PITTSBURGH STEELERS",
        "STEELERS",
        "Pittsburgh",
        "Pittsburgh Steelers",
    ],
    # AFC South
    "HOUSTON_TEXANS": [
        "HOUSTON",
        "HOUSTON TEXANS",
        "TEXANS",
        "Houston",
        "Houston Texans",
    ],
    "INDIANAPOLIS_COLTS": [
        "INDIANAPOLIS",
        "INDIANAPOLIS COLTS",
        "COLTS",
        "Indianapolis",
        "Indianapolis Colts",
    ],
    "JACKSONVILLE_JAGUARS": [
        "JACKSONVILLE",
        "JACKSONVILLE JAGUARS",
        "JAGUARS",
        "Jacksonville",
        "Jacksonville Jaguars",
    ],
    "TENNESSEE_TITANS": [
        "TENNESSEE",
        "TENNESSEE TITANS",
        "TITANS",
        "Tennessee",
        "Tennessee Titans",
    ],
    # AFC West
    "DENVER_BRONCOS": [
        "DENVER",
        "DENVER BRONCOS",
        "BRONCOS",
        "Denver",
        "Denver Broncos",
    ],
    "KANSAS_CITY_CHIEFS": [
        "KANSAS CITY",
        "KANSAS CITY CHIEFS",
        "CHIEFS",
        "Kansas City",
        "Kansas City Chiefs",
    ],
    "LAS_VEGAS_RAIDERS": [
        "LAS VEGAS",
        "LAS VEGAS RAIDERS",
        "RAIDERS",
        "Las Vegas",
        "Las Vegas Raiders",
    ],
    "LOS_ANGELES_CHARGERS": [
        "LOS ANGELES C",
        "LOS ANGELES CHARGERS",
        "CHARGERS",
        "LA CHARGERS",
        "Los Angeles C",
        "Los Angeles Chargers",
    ],
    # NFC East
    "DALLAS_COWBOYS": [
        "DALLAS",
        "DALLAS COWBOYS",
        "COWBOYS",
        "Dallas",
        "Dallas Cowboys",
    ],
    "NEW_YORK_GIANTS": [
        "NEW YORK G",
        "NEW YORK GIANTS",
        "GIANTS",
        "New York G",
        "New York Giants",
    ],
    "PHILADELPHIA_EAGLES": [
        "PHILADELPHIA",
        "PHILADELPHIA EAGLES",
        "EAGLES",
        "Philadelphia",
        "Philadelphia Eagles",
    ],
    "WASHINGTON_COMMANDERS": [
        "WASHINGTON",
        "WASHINGTON COMMANDERS",
        "COMMANDERS",
        "Washington",
        "Washington Commanders",
    ],
    # NFC North
    "CHICAGO_BEARS": [
        "CHICAGO",
        "CHICAGO BEARS",
        "BEARS",
        "Chicago",
        "Chicago Bears",
    ],
    "DETROIT_LIONS": [
        "DETROIT",
        "DETROIT LIONS",
        "LIONS",
        "Detroit",
        "Detroit Lions",
    ],
    "GREEN_BAY_PACKERS": [
        "GREEN BAY",
        "GREEN BAY PACKERS",
        "PACKERS",
        "Green Bay",
        "Green Bay Packers",
    ],
    "MINNESOTA_VIKINGS": [
        "MINNESOTA",
        "MINNESOTA VIKINGS",
        "VIKINGS",
        "Minnesota",
        "Minnesota Vikings",
    ],
    # NFC South
    "ATLANTA_FALCONS": [
        "ATLANTA",
        "ATLANTA FALCONS",
        "FALCONS",
        "Atlanta",
        "Atlanta Falcons",
    ],
    "CAROLINA_PANTHERS": [
        "CAROLINA",
        "CAROLINA PANTHERS",
        "PANTHERS",
        "Carolina",
        "Carolina Panthers",
    ],
    "NEW_ORLEANS_SAINTS": [
        "NEW ORLEANS",
        "NEW ORLEANS SAINTS",
        "SAINTS",
        "New Orleans",
        "New Orleans Saints",
    ],
    "TAMPA_BAY_BUCCANEERS": [
        "TAMPA BAY",
        "TAMPA BAY BUCCANEERS",
        "BUCCANEERS",
        "Tampa Bay",
        "Tampa Bay Buccaneers",
    ],
    # NFC West
    "ARIZONA_CARDINALS": [
        "ARIZONA",
        "ARIZONA CARDINALS",
        "CARDINALS",
        "Arizona",
        "Arizona Cardinals",
    ],
    "LOS_ANGELES_RAMS": [
        "LOS ANGELES R",
        "LOS ANGELES RAMS",
        "RAMS",
        "LA RAMS",
        "Los Angeles R",
        "Los Angeles Rams",
    ],
    "SAN_FRANCISCO_49ERS": [
        "SAN FRANCISCO",
        "SAN FRANCISCO 49ERS",
        "49ERS",
        "San Francisco",
        "San Francisco 49ers",
    ],
    "SEATTLE_SEAHAWKS": [
        "SEATTLE",
        "SEATTLE SEAHAWKS",
        "SEAHAWKS",
        "Seattle",
        "Seattle Seahawks",
    ],
}

# ---------------------------------------------------------------------------
# NBA: canonical_team_id → known Kalshi / Polymarket name variations
# ---------------------------------------------------------------------------

NBA_TEAM_ALIASES: dict[str, list[str]] = {
    # Eastern Conference — Atlantic
    "BOSTON_CELTICS": [
        "BOSTON",
        "BOSTON CELTICS",
        "CELTICS",
        "Boston",
        "Boston Celtics",
    ],
    "BROOKLYN_NETS": [
        "BROOKLYN",
        "BROOKLYN NETS",
        "NETS",
        "Brooklyn",
        "Brooklyn Nets",
    ],
    "NEW_YORK_KNICKS": [
        "NEW YORK",
        "NEW YORK KNICKS",
        "KNICKS",
        "New York",
        "New York Knicks",
    ],
    "PHILADELPHIA_76ERS": [
        "PHILADELPHIA",
        "PHILADELPHIA 76ERS",
        "76ERS",
        "SIXERS",
        "Philadelphia",
        "Philadelphia 76ers",
        "Philadelphia Sixers",
    ],
    "TORONTO_RAPTORS": [
        "TORONTO",
        "TORONTO RAPTORS",
        "RAPTORS",
        "Toronto",
        "Toronto Raptors",
    ],
    # Eastern Conference — Central
    "CHICAGO_BULLS": [
        "CHICAGO",
        "CHICAGO BULLS",
        "BULLS",
        "Chicago",
        "Chicago Bulls",
    ],
    "CLEVELAND_CAVALIERS": [
        "CLEVELAND",
        "CLEVELAND CAVALIERS",
        "CAVALIERS",
        "CAVS",
        "Cleveland",
        "Cleveland Cavaliers",
    ],
    "DETROIT_PISTONS": [
        "DETROIT",
        "DETROIT PISTONS",
        "PISTONS",
        "Detroit",
        "Detroit Pistons",
    ],
    "INDIANA_PACERS": [
        "INDIANA",
        "INDIANA PACERS",
        "PACERS",
        "Indiana",
        "Indiana Pacers",
    ],
    "MILWAUKEE_BUCKS": [
        "MILWAUKEE",
        "MILWAUKEE BUCKS",
        "BUCKS",
        "Milwaukee",
        "Milwaukee Bucks",
    ],
    # Eastern Conference — Southeast
    "ATLANTA_HAWKS": [
        "ATLANTA",
        "ATLANTA HAWKS",
        "HAWKS",
        "Atlanta",
        "Atlanta Hawks",
    ],
    "CHARLOTTE_HORNETS": [
        "CHARLOTTE",
        "CHARLOTTE HORNETS",
        "HORNETS",
        "Charlotte",
        "Charlotte Hornets",
    ],
    "MIAMI_HEAT": [
        "MIAMI",
        "MIAMI HEAT",
        "HEAT",
        "Miami",
        "Miami Heat",
    ],
    "ORLANDO_MAGIC": [
        "ORLANDO",
        "ORLANDO MAGIC",
        "MAGIC",
        "Orlando",
        "Orlando Magic",
    ],
    "WASHINGTON_WIZARDS": [
        "WASHINGTON",
        "WASHINGTON WIZARDS",
        "WIZARDS",
        "Washington",
        "Washington Wizards",
    ],
    # Western Conference — Northwest
    "DENVER_NUGGETS": [
        "DENVER",
        "DENVER NUGGETS",
        "NUGGETS",
        "Denver",
        "Denver Nuggets",
    ],
    "MINNESOTA_TIMBERWOLVES": [
        "MINNESOTA",
        "MINNESOTA TIMBERWOLVES",
        "TIMBERWOLVES",
        "WOLVES",
        "Minnesota",
        "Minnesota Timberwolves",
    ],
    "OKLAHOMA_CITY_THUNDER": [
        "OKLAHOMA CITY",
        "OKLAHOMA CITY THUNDER",
        "THUNDER",
        "Oklahoma City",
        "Oklahoma City Thunder",
    ],
    "PORTLAND_TRAIL_BLAZERS": [
        "PORTLAND",
        "PORTLAND TRAIL BLAZERS",
        "TRAIL BLAZERS",
        "BLAZERS",
        "Portland",
        "Portland Trail Blazers",
    ],
    "UTAH_JAZZ": [
        "UTAH",
        "UTAH JAZZ",
        "JAZZ",
        "Utah",
        "Utah Jazz",
    ],
    # Western Conference — Pacific
    "GOLDEN_STATE_WARRIORS": [
        "GOLDEN STATE",
        "GOLDEN STATE WARRIORS",
        "WARRIORS",
        "Golden State",
        "Golden State Warriors",
    ],
    "LOS_ANGELES_CLIPPERS": [
        "LA CLIPPERS",
        "LOS ANGELES CLIPPERS",
        "CLIPPERS",
        "LA Clippers",
        "Los Angeles Clippers",
    ],
    "LOS_ANGELES_LAKERS": [
        "LOS ANGELES",
        "LA LAKERS",
        "LOS ANGELES LAKERS",
        "LAKERS",
        "Los Angeles",
        "LA Lakers",
        "Los Angeles Lakers",
    ],
    "PHOENIX_SUNS": [
        "PHOENIX",
        "PHOENIX SUNS",
        "SUNS",
        "Phoenix",
        "Phoenix Suns",
    ],
    "SACRAMENTO_KINGS": [
        "SACRAMENTO",
        "SACRAMENTO KINGS",
        "KINGS",
        "Sacramento",
        "Sacramento Kings",
    ],
    # Western Conference — Southwest
    "DALLAS_MAVERICKS": [
        "DALLAS",
        "DALLAS MAVERICKS",
        "MAVERICKS",
        "MAVS",
        "Dallas",
        "Dallas Mavericks",
    ],
    "HOUSTON_ROCKETS": [
        "HOUSTON",
        "HOUSTON ROCKETS",
        "ROCKETS",
        "Houston",
        "Houston Rockets",
    ],
    "MEMPHIS_GRIZZLIES": [
        "MEMPHIS",
        "MEMPHIS GRIZZLIES",
        "GRIZZLIES",
        "Memphis",
        "Memphis Grizzlies",
    ],
    "NEW_ORLEANS_PELICANS": [
        "NEW ORLEANS",
        "NEW ORLEANS PELICANS",
        "PELICANS",
        "New Orleans",
        "New Orleans Pelicans",
    ],
    "SAN_ANTONIO_SPURS": [
        "SAN ANTONIO",
        "SAN ANTONIO SPURS",
        "SPURS",
        "San Antonio",
        "San Antonio Spurs",
    ],
}

# ---------------------------------------------------------------------------
# Tennis — player-name aliases (surname-based)
# ---------------------------------------------------------------------------

TENNIS_PLAYER_ALIASES: dict[str, list[str]] = {
    # ATP top names (sampled from live Kalshi ``KXATPMATCH`` titles 2026-08-05
    # + well-known full-name forms Polymarket may render)
    "ALCARAZ": ["ALCARAZ", "CARLOS ALCARAZ", "Carlos Alcaraz"],
    "AUGER_ALIASSIME": [
        "AUGER-ALIASSIME",
        "AUGER ALIASSIME",
        "FELIX AUGER-ALIASSIME",
        "Auger-Aliassime",
        "Felix Auger-Aliassime",
    ],
    "BORGES": ["BORGES", "NUNO BORGES", "Borges", "Nuno Borges"],
    "BROOKSBY": ["BROOKSBY", "JENSON BROOKSBY", "Brooksby", "Jenson Brooksby"],
    "BUSE": ["BUSE", "IGNAZIO BUSE", "Buse", "Ignazio Buse"],
    "COBOLLI": ["COBOLLI", "FLAVIO COBOLLI", "Cobolli", "Flavio Cobolli"],
    "DROGUET": ["DROGUET", "TITOUAN DROGUET", "Droguet", "Titouan Droguet"],
    "ETCHEVERRY": ["ETCHEVERRY", "TOMAS MARTIN ETCHEVERRY", "Etcheverry", "Tomas Martin Etcheverry"],
    "FEARNLEY": ["FEARNLEY", "JACOB FEARNLEY", "Fearnley", "Jacob Fearnley"],
    "HANFMANN": ["HANFMANN", "YANNICK HANFMANN", "Hanfmann", "Yannick Hanfmann"],
    "HUMBERT": ["HUMBERT", "UGO HUMBERT", "Humbert", "Ugo Humbert"],
    "HURKACZ": ["HURKACZ", "HUBERT HURKACZ", "Hurkacz", "Hubert Hurkacz"],
    "KECMANOVIC": ["KECMANOVIC", "MIOMIR KECMANOVIC", "Kecmanovic", "Miomir Kecmanovic"],
    "MEJIA": ["MEJIA", "NICOLAS MEJIA", "Mejia", "Nicolas Mejia"],
    "MENSIK": ["MENSIK", "JAKUB MENSIK", "Mensik", "Jakub Mensik"],
    "MERIDA": ["MERIDA", "DANIEL MERIDA", "Merida", "Daniel Merida"],
    "MUSETTI": ["MUSETTI", "LORENZO MUSETTI", "Musetti", "Lorenzo Musetti"],
    "NAVONE": ["NAVONE", "MARIANO NAVONE", "Navone", "Mariano Navone"],
    "NORRIE": ["NORRIE", "CAMERON NORRIE", "Norrie", "Cameron Norrie"],
    "RINDERKNECH": ["RINDERKNECH", "ARTHUR RINDERKNECH", "Rinderknech", "Arthur Rinderknech"],
    "SHELTON": ["SHELTON", "BEN SHELTON", "Shelton", "Ben Shelton"],
    "SINNER": ["SINNER", "JANNIK SINNER", "Sinner", "Jannik Sinner"],
    "TABILO": ["TABILO", "ALEJANDRO TABILO", "Tabilo", "Alejandro Tabilo"],
    "VACHEROT": ["VACHEROT", "VALENTIN VACHEROT", "Vacherot", "Valentin Vacherot"],
    # WTA top names (sampled from live Kalshi ``KXWTAMATCH`` titles 2026-08-05)
    "ANDREEVA": ["ANDREEVA", "MIRRA ANDREEVA", "Andreeva", "Mirra Andreeva"],
    "BONDAR": ["BONDAR", "ANNA BONDAR", "Bondar", "Anna Bondar"],
    "BOUZKOVA": ["BOUZKOVA", "MARIE BOUZKOVA", "Bouzkova", "Marie Bouzkova"],
    "CIRSTEA": ["CIRSTEA", "SORANA CIRSTEA", "Cirstea", "Sorana Cirstea"],
    "CROSS": ["CROSS", "KAYLA CROSS", "Cross", "Kayla Cross"],
    "DAY": ["DAY", "KAYLA DAY", "Day", "Kayla Day"],
    "FRECH": ["FRECH", "MAGDALENA FRECH", "Frech", "Magdalena Frech"],
    "GAUFF": ["GAUFF", "COCO GAUFF", "Gauff", "Coco Gauff"],
    "JOINT": ["JOINT", "MAYA JOINT", "Joint", "Maya Joint"],
    "JOVIC": ["JOVIC", "IVA JOVIC", "Jovic", "Iva Jovic"],
    "KASATKINA": ["KASATKINA", "DARIA KASATKINA", "Kasatkina", "Daria Kasatkina"],
    "KORNEEVA": ["KORNEEVA", "ALINA KORNEEVA", "Korneeva", "Alina Korneeva"],
    "LI": ["LI", "ANN LI", "Li", "Ann Li"],
    "LINETTE": ["LINETTE", "MAGDA LINETTE", "Linette", "Magda Linette"],
    "MERTENS": ["MERTENS", "ELISE MERTENS", "Mertens", "Elise Mertens"],
    "NAVARRO": ["NAVARRO", "EMMA NAVARRO", "Navarro", "Emma Navarro"],
    "PEGULA": ["PEGULA", "JESSICA PEGULA", "Pegula", "Jessica Pegula"],
    "PLISKOVA": ["PLISKOVA", "KAROLINA PLISKOVA", "Pliskova", "Karolina Pliskova"],
    "RYBAKINA": ["RYBAKINA", "ELENA RYBAKINA", "Rybakina", "Elena Rybakina"],
    "TOWNSEND": ["TOWNSEND", "TAYLOR TOWNSEND", "Townsend", "Taylor Townsend"],
}

# ---------------------------------------------------------------------------
# League → alias-dict dispenser
# ---------------------------------------------------------------------------

_LEAGUE_ALIASES: Final[dict[str, dict[str, list[str]]]] = {
    "MLB": MLB_TEAM_ALIASES,
    "NFL": NFL_TEAM_ALIASES,
    "NBA": NBA_TEAM_ALIASES,
    "TENNIS": TENNIS_PLAYER_ALIASES,
    "ATP": TENNIS_PLAYER_ALIASES,
    "WTA": TENNIS_PLAYER_ALIASES,
}


def _normalize_key(name: str) -> str:
    """Collapse diacritics, uppercase, drop non-alphanumeric chars for reverse lookup."""
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_only = nfkd.encode("ascii", "ignore").decode("ascii")
    collapsed = re.sub(r"[^A-Za-z0-9]", "", ascii_only)
    return collapsed.upper()


def _build_universal_reverse(aliases: dict[str, list[str]]) -> dict[str, str]:
    """Build a normalised-key → canonical_id reverse index from an alias dict."""
    reverse: dict[str, str] = {}
    for canonical_id, variations in aliases.items():
        for variant in variations:
            key = _normalize_key(variant)
            existing = reverse.get(key)
            if existing is not None and existing != canonical_id:
                # Ambiguity guards against false pairs
                raise ValueError(
                    f"Team-name collision: '{variant}' normalised key '{key}' "
                    f"maps to both '{canonical_id}' and '{existing}'"
                )
            reverse[key] = canonical_id
    return reverse


# Pre-built caches
_MLB_REVERSE: Final[dict[str, str]] = _build_universal_reverse(MLB_TEAM_ALIASES)
_NFL_REVERSE: Final[dict[str, str]] = _build_universal_reverse(NFL_TEAM_ALIASES)
_NBA_REVERSE: Final[dict[str, str]] = _build_universal_reverse(NBA_TEAM_ALIASES)
_TENNIS_REVERSE: Final[dict[str, str]] = _build_universal_reverse(TENNIS_PLAYER_ALIASES)

_REVERSE_BY_LEAGUE: Final[dict[str, dict[str, str]]] = {
    "MLB": _MLB_REVERSE,
    "NFL": _NFL_REVERSE,
    "NBA": _NBA_REVERSE,
    "TENNIS": _TENNIS_REVERSE,
    "ATP": _TENNIS_REVERSE,
    "WTA": _TENNIS_REVERSE,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def canonicalize_sports_participant(name: str, league: str) -> str:
    """Resolve a sports participant (team or player) name to its canonical ID.

    For the named ``league``, looks up the normalised form of ``name`` in the
    per-league reverse alias index. On a hit, returns the canonical team/player
    ID (``SEATTLE_MARINERS``, ``ALCARAZ``, etc.). On a miss, returns the
    unmodified output of the existing :func:`normalize_participant`
    (``unified_api_contracts.canonical.domain.predictions.fixture_parsing``)
    — a lower-case, whitespace-collapsed form that preserves the trailing
    same-city qualifier ("new york m" / "new york y"). This fallback is
    identical to the pre-alias behaviour and is an honest-absence signal: an
    unresolved participant still produces a deterministically-keyed row, just not
    a cross-venue join, until its alias is added.

    The caller (fixture parsing) is responsible for calling
    :func:`normalize_participant` first (the existing lower-case +
    whitespace-collapse pass), so ``name`` here is already in that form.
    """
    if not name or not league:
        return name
    reverse = _REVERSE_BY_LEAGUE.get(league.upper())
    if reverse is None:
        return name
    key = _normalize_key(name)
    found = reverse.get(key)
    return found if found is not None else name


def get_team_aliases_for_league(league: str) -> dict[str, list[str]] | None:
    """Return the raw alias dict for a league, or ``None`` for unknown leagues."""
    return _LEAGUE_ALIASES.get(league.upper())


__all__ = [
    "MLB_TEAM_ALIASES",
    "NBA_TEAM_ALIASES",
    "NFL_TEAM_ALIASES",
    "TENNIS_PLAYER_ALIASES",
    "canonicalize_sports_participant",
    "get_team_aliases_for_league",
]
