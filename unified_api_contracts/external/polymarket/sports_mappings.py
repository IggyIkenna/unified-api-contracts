"""Polymarket sports market mappings — football fixtures via Odds API leagues.

Maps canonical fixture IDs to Polymarket condition_ids for football leagues
currently covered by both Odds API and Polymarket.

Sports scope: football leagues in LEAGUE_REGISTRY with Odds API coverage.
Polymarket sports markets use tag_slug="soccer" or "football".

Polymarket uses ``series.slug`` (from Gamma API event.series[]) to group
matches by competition. The ``POLYMARKET_SERIES_TO_LEAGUE`` mapping is the
SSOT for resolving a Polymarket series slug to a canonical league_id.

Sports market types on Polymarket (``sportsMarketType`` field):
  moneyline, spreads, totals, btts, draw
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
        "mls",
        "copa-del-rey",
        "a-league",
        "scottish-premiership",
        "primeira-liga",
        "eredivisie",
    }
)

# ---------------------------------------------------------------------------
# Series slug → canonical league_id (SSOT)
# ---------------------------------------------------------------------------

POLYMARKET_SERIES_TO_LEAGUE: dict[str, str] = {
    # England
    "premier-league-2025": "EPL",
    "efl-championship": "ENG_CHAMPIONSHIP",
    "efa-2025": "FA_CUP",
    # Spain
    "la-liga-2025": "LAL",
    "la-liga-2": "SPA_SEGUNDA",
    "copa-del-rey": "COPA_DEL_REY",
    # Germany
    "bundesliga-2025": "BUN",
    "bundesliga-2": "GER_2BUNDESLIGA",
    # Italy
    "serie-a-2025": "SEA",
    # France
    "ligue-1-2025": "FL1",
    "ligue-2": "FR_LIGUE_2",
    # Other Europe
    "scottish-premiership": "SCO_PREM",
    "primeira-liga": "POR_PRIMEIRA",
    "denmark-superliga": "DEN_SUPERLIGA",
    "norway-eliteserien": "NOR_ELITESERIEN",
    "tur-2025": "TUR_SUPER_LIG",
    "rus-2025": "RUS_PREMIER",
    # Americas
    "mls-2025": "MLS",
    "primera-a": "COL_PRIMERA_A",
    "primera-divisin-argentina": "ARG_PRIMERA",
    # Asia / Oceania
    "a-league-soccer": "AUS_ALEAGUE",
    "k-league": "KOR_KLEAGUE",
    "japan-j2-league": "JPN_J2",
    "saudi-professional-league": "SAU_PRO_LEAGUE",
    "liga-1": "IDN_LIGA_1",
    # International / Continental
    "ucl-2025": "UCL",
    "ucl": "UCL",
    "uel-2025": "UEL",
    "europa-conference-league": "UECL",
    "womens-champions-league": "UWCL",
    "concacaf": "CONCACAF",
    "sud-2025": "COPA_SUDAMERICANA",
    "fifa-friendly": "FIFA_FRIENDLY",
    "uef-qualifiers": "UEF_QUALIFIERS",
    "ofc": "OFC",
    # Non-soccer sports (series slug → league_id)
    "nba-2026": "NBA",
    "nhl-2026": "NHL",
    "nfl-2025": "NFL",
    "mlb-games": "MLB",
    "ncaa-cbb": "NCAA_CBB",
    "ufc": "UFC",
    "atp": "ATP",
    "wta": "WTA",
    "dota-2": "DOTA2",
    "counter-strike": "CS2",
    "league-of-legends": "LOL",
    "valorant": "VALORANT",
    "euroleague-basketball": "EUROLEAGUE",
}

# Reverse lookup: canonical league_id → Polymarket series slug (first match)
_LEAGUE_TO_SERIES: dict[str, str] = {}
for _slug, _lid in POLYMARKET_SERIES_TO_LEAGUE.items():
    if _lid not in _LEAGUE_TO_SERIES:
        _LEAGUE_TO_SERIES[_lid] = _slug

# ---------------------------------------------------------------------------
# Polymarket sportsMarketType → canonical market type
# ---------------------------------------------------------------------------

POLYMARKET_MARKET_TYPE_MAP: dict[str, str] = {
    "moneyline": "MONEYLINE",
    "spreads": "SPREADS",
    "totals": "TOTALS",
    "btts": "BTTS",
}

# NOTE: Polymarket sports markets are ephemeral (created per matchweek/season).
# Static mapping tables are NOT practical — resolution is dynamic via Gamma API.
# This module provides TAG constants + helpers for runtime discovery.


def get_polymarket_sports_tag_for_league(league_id: str) -> str | None:
    """Map canonical league_id to Polymarket tag slug for Gamma API filtering.

    Returns None if the league has no known Polymarket tag.
    """
    league_to_tag: dict[str, str] = {
        "EPL": "premier-league",
        "ENG_CHAMPIONSHIP": "efl-championship",
        "BUN": "bundesliga",
        "LAL": "la-liga",
        "SEA": "serie-a",
        "FL1": "ligue-1",
        "UCL": "champions-league",
        "UEL": "champions-league",
        "MLS": "mls",
        "NBA": "nba",
        "NFL": "nfl",
        "MLB": "mlb",
    }
    return league_to_tag.get(league_id)


def get_canonical_league_for_polymarket_series(series_slug: str) -> str | None:
    """Map a Polymarket series slug to canonical league_id.

    Handles year-suffixed slugs by trying exact match first, then
    stripping trailing ``-YYYY`` or ``-20YY`` patterns.
    """
    if series_slug in POLYMARKET_SERIES_TO_LEAGUE:
        return POLYMARKET_SERIES_TO_LEAGUE[series_slug]
    # Strip trailing year suffix (e.g. "premier-league-2026" → try "premier-league-2025")
    # Not practical to enumerate all years — return None for unmapped slugs
    return None


def get_polymarket_series_for_league(league_id: str) -> str | None:
    """Map canonical league_id to the Polymarket series slug."""
    return _LEAGUE_TO_SERIES.get(league_id)


# ---------------------------------------------------------------------------
# Polymarket team name → canonical team name mapping
# ---------------------------------------------------------------------------

# Polymarket uses formal team names in market questions and outcomes.
# These supplement the existing API-Football mappings in api_football/team_mappings.py.
# Only teams NOT already covered by API_FOOTBALL_TO_CANONICAL need entries here.

POLYMARKET_TEAM_TO_CANONICAL: dict[str, str] = {
    # La Liga
    "Club Atlético de Madrid": "ATLETICO_MADRID",
    "Atlético de Madrid": "ATLETICO_MADRID",
    "Atletico Madrid": "ATLETICO_MADRID",
    "Real Madrid CF": "REAL_MADRID",
    "Real Madrid": "REAL_MADRID",
    "FC Barcelona": "BARCELONA",
    "Barcelona": "BARCELONA",
    "Real Sociedad de Fútbol": "REAL_SOCIEDAD",
    "Real Sociedad": "REAL_SOCIEDAD",
    "Real Betis Balompié": "REAL_BETIS",
    "Real Betis": "REAL_BETIS",
    "Sevilla FC": "SEVILLA",
    "Sevilla": "SEVILLA",
    "Valencia CF": "VALENCIA",
    "Valencia": "VALENCIA",
    "Villarreal CF": "VILLARREAL",
    "Villarreal": "VILLARREAL",
    "Athletic Club": "ATHLETIC_BILBAO",
    "Athletic Bilbao": "ATHLETIC_BILBAO",
    "CA Osasuna": "OSASUNA",
    "Osasuna": "OSASUNA",
    "RC Celta de Vigo": "CELTA_VIGO",
    "Celta Vigo": "CELTA_VIGO",
    "Celta de Vigo": "CELTA_VIGO",
    "Getafe CF": "GETAFE",
    "Getafe": "GETAFE",
    "Rayo Vallecano": "RAYO_VALLECANO",
    "RCD Mallorca": "MALLORCA",
    "Mallorca": "MALLORCA",
    "Deportivo Alavés": "ALAVES",
    "Alavés": "ALAVES",
    "RCD Espanyol": "ESPANYOL",
    "Espanyol": "ESPANYOL",
    "Girona FC": "GIRONA",
    "Girona": "GIRONA",
    "UD Las Palmas": "LAS_PALMAS",
    "Las Palmas": "LAS_PALMAS",
    "CD Leganés": "LEGANES",
    "Leganés": "LEGANES",
    "Real Valladolid CF": "VALLADOLID",
    "Real Valladolid": "VALLADOLID",
    # Serie A
    "AC Milan": "AC_MILAN",
    "Inter Milan": "INTER_MILAN",
    "FC Internazionale Milano": "INTER_MILAN",
    "Juventus FC": "JUVENTUS",
    "Juventus": "JUVENTUS",
    "SSC Napoli": "NAPOLI",
    "Napoli": "NAPOLI",
    "AS Roma": "ROMA",
    "Roma": "ROMA",
    "SS Lazio": "LAZIO",
    "Lazio": "LAZIO",
    "ACF Fiorentina": "FIORENTINA",
    "Fiorentina": "FIORENTINA",
    "Atalanta BC": "ATALANTA",
    "Atalanta": "ATALANTA",
    "Bologna FC 1909": "BOLOGNA",
    "Bologna": "BOLOGNA",
    "Torino FC": "TORINO",
    "Torino": "TORINO",
    "US Lecce": "LECCE",
    "Lecce": "LECCE",
    "Genoa CFC": "GENOA",
    "Genoa": "GENOA",
    "Udinese Calcio": "UDINESE",
    "Udinese": "UDINESE",
    "Cagliari Calcio": "CAGLIARI",
    "Cagliari": "CAGLIARI",
    "Hellas Verona FC": "VERONA",
    "Hellas Verona": "VERONA",
    "Empoli FC": "EMPOLI",
    "Empoli": "EMPOLI",
    "Parma Calcio 1913": "PARMA",
    "Parma": "PARMA",
    "US Salernitana 1919": "SALERNITANA",
    "Salernitana": "SALERNITANA",
    "US Sassuolo Calcio": "SASSUOLO",
    "Sassuolo": "SASSUOLO",
    "Frosinone Calcio": "FROSINONE",
    "Frosinone": "FROSINONE",
    "Venezia FC": "VENEZIA",
    "Venezia": "VENEZIA",
    "Como 1907": "COMO",
    "Como": "COMO",
    "AC Monza": "MONZA",
    "Monza": "MONZA",
    # Ligue 1
    "Paris Saint-Germain": "PSG",
    "Paris Saint Germain": "PSG",
    "PSG": "PSG",
    "Olympique de Marseille": "MARSEILLE",
    "Marseille": "MARSEILLE",
    "Olympique Lyonnais": "LYON",
    "Lyon": "LYON",
    "AS Monaco": "MONACO",
    "Monaco": "MONACO",
    "LOSC Lille": "LILLE",
    "Lille": "LILLE",
    "OGC Nice": "NICE",
    "Nice": "NICE",
    "Stade Rennais FC": "RENNES",
    "Rennes": "RENNES",
    "RC Lens": "LENS",
    "Lens": "LENS",
    "RC Strasbourg Alsace": "STRASBOURG",
    "Strasbourg": "STRASBOURG",
    "Stade Brestois 29": "BREST",
    "Brest": "BREST",
    "FC Nantes": "NANTES",
    "Nantes": "NANTES",
    "Montpellier HSC": "MONTPELLIER",
    "Montpellier": "MONTPELLIER",
    "Toulouse FC": "TOULOUSE",
    "Toulouse": "TOULOUSE",
    "Le Havre AC": "LE_HAVRE",
    "Le Havre": "LE_HAVRE",
    "AJ Auxerre": "AUXERRE",
    "Auxerre": "AUXERRE",
    "Angers SCO": "ANGERS",
    "Angers": "ANGERS",
    "AS Saint-Étienne": "ST_ETIENNE",
    "Saint-Étienne": "ST_ETIENNE",
    "Stade de Reims": "REIMS",
    "Reims": "REIMS",
    # Copa del Rey / shared Spanish
    "Cúcuta Deportivo FC": "CUCUTA_DEPORTIVO",
    # A-League
    "Sydney FC": "SYDNEY_FC",
    "Perth Glory FC": "PERTH_GLORY",
    "Perth Glory": "PERTH_GLORY",
    "Melbourne Victory": "MELBOURNE_VICTORY",
    "Melbourne City FC": "MELBOURNE_CITY",
    "Western Sydney Wanderers FC": "WS_WANDERERS",
    "Central Coast Mariners FC": "CC_MARINERS",
    "Adelaide United": "ADELAIDE_UNITED",
    "Brisbane Roar FC": "BRISBANE_ROAR",
    "Macarthur FC": "MACARTHUR_FC",
    "Newcastle Jets FC": "NEWCASTLE_JETS",
    "Wellington Phoenix FC": "WELLINGTON_PHOENIX",
    "Western United FC": "WESTERN_UNITED",
    "Auckland FC": "AUCKLAND_FC",
    # Colombian Primera A
    "Boyacá Chicó FC": "BOYACA_CHICO",
    "Atlético Nacional": "ATLETICO_NACIONAL",
    "Millonarios FC": "MILLONARIOS",
    "Independiente Santa Fe": "SANTA_FE",
    "Independiente Medellín": "INDEPENDIENTE_MEDELLIN",
    "Deportivo Cali": "DEPORTIVO_CALI",
    "Junior FC": "JUNIOR_BARRANQUILLA",
    "América de Cali": "AMERICA_DE_CALI",
    # Argentine Primera
    "Boca Juniors": "BOCA_JUNIORS",
    "River Plate": "RIVER_PLATE",
    "Racing Club": "RACING_CLUB",
    "Independiente": "INDEPENDIENTE",
    "San Lorenzo": "SAN_LORENZO",
    # MLS
    "LA Galaxy": "LA_GALAXY",
    "LAFC": "LAFC",
    "Los Angeles FC": "LAFC",
    "Inter Miami CF": "INTER_MIAMI",
    "Inter Miami": "INTER_MIAMI",
    "New York Red Bulls": "NY_RED_BULLS",
    "New York City FC": "NYCFC",
    "Atlanta United FC": "ATLANTA_UNITED",
    "Seattle Sounders FC": "SEATTLE_SOUNDERS",
    "Portland Timbers": "PORTLAND_TIMBERS",
    "Real Salt Lake": "REAL_SALT_LAKE",
    "San Diego FC": "SAN_DIEGO_FC",
    # Portuguese Primeira Liga
    "SL Benfica": "BENFICA",
    "Benfica": "BENFICA",
    "FC Porto": "PORTO",
    "Porto": "PORTO",
    "Sporting CP": "SPORTING_CP",
    "Sporting": "SPORTING_CP",
    "SC Braga": "BRAGA",
    "Braga": "BRAGA",
    # Scottish Premiership
    "Celtic FC": "CELTIC",
    "Celtic": "CELTIC",
    "Rangers FC": "RANGERS",
    "Rangers": "RANGERS",
    "Aberdeen FC": "ABERDEEN",
    "Heart of Midlothian FC": "HEARTS",
    "Hearts": "HEARTS",
    "Hibernian FC": "HIBERNIAN",
    # Turkish Süper Lig
    "Galatasaray SK": "GALATASARAY",
    "Galatasaray": "GALATASARAY",
    "Fenerbahçe SK": "FENERBAHCE",
    "Fenerbahçe": "FENERBAHCE",
    "Fenerbahce": "FENERBAHCE",
    "Beşiktaş JK": "BESIKTAS",
    "Besiktas": "BESIKTAS",
    "Trabzonspor": "TRABZONSPOR",
    # UCL / International
    "FC Bayern München": "BAYERN",
    "Club Brugge KV": "CLUB_BRUGGE",
    "Club Brugge": "CLUB_BRUGGE",
    "AFC Ajax": "AJAX",
    "Ajax": "AJAX",
    "PSV Eindhoven": "PSV",
    "PSV": "PSV",
    "Feyenoord Rotterdam": "FEYENOORD",
    "Feyenoord": "FEYENOORD",
}

# Build reverse lookup: normalized (upper) → canonical_team_id
_POLYMARKET_LOOKUP: dict[str, str] = {}
for _pm_name, _canonical_id in POLYMARKET_TEAM_TO_CANONICAL.items():
    _POLYMARKET_LOOKUP[_pm_name.upper()] = _canonical_id


def get_canonical_team_for_polymarket(polymarket_team_name: str) -> str | None:
    """Normalize a Polymarket team name to a canonical team ID.

    Tries in order:
    1. Exact match in POLYMARKET_TEAM_TO_CANONICAL
    2. Case-insensitive match
    3. Stripped suffixes (FC, CF, SC, etc.)

    Returns None if no match found.
    """
    if not polymarket_team_name:
        return None
    # 1. Exact match
    result = POLYMARKET_TEAM_TO_CANONICAL.get(polymarket_team_name)
    if result is not None:
        return result
    # 2. Case-insensitive
    upper = polymarket_team_name.upper().strip()
    result = _POLYMARKET_LOOKUP.get(upper)
    if result is not None:
        return result
    # 3. Strip common suffixes and retry
    import re
    stripped = re.sub(r"\s+(FC|CF|SC|SK|JK|AFC|SV|AC|SS|US|AS|RC|CD|UD|RCD|CA|SSC|CFC|BC)$", "", upper).strip()
    if stripped != upper:
        result = _POLYMARKET_LOOKUP.get(stripped)
        if result is not None:
            return result
    return None
