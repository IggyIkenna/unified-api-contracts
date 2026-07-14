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

import re

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

# ---------------------------------------------------------------------------
# Prediction leagues with confirmed Polymarket coverage (SSOT)
# ---------------------------------------------------------------------------
# Only these leagues have sports markets on Polymarket. Services should skip
# leagues not in this set to avoid wasted API calls. Verified by scanning
# 9 days of Polymarket data (2026-03-18 to 2026-03-26).
POLYMARKET_PREDICTION_LEAGUES: frozenset[str] = frozenset(
    {
        "EPL",
        "ENG_CHAMPIONSHIP",
        "LA_LIGA",
        "SEGUNDA_DIVISION",
        "BUNDESLIGA",
        "BUNDESLIGA_2",
        "SERIE_A",
        "SERIE_B",
        "LIGUE_1",
        "LIGUE_2",
        "EREDIVISIE",
        "PRIMEIRA_LIGA",
        "SCOTTISH_PREMIERSHIP",
        "SUPER_LIG",
        "DANISH_SUPERLIGA",
        "ELITESERIEN",
        "MLS",
        "LIGA_MX",
        "ARGENTINA_PRIMERA",
        "BRASILEIRAO",
        "A_LEAGUE",
        "J1_LEAGUE",
        "K_LEAGUE_1",
    }
)

# ---------------------------------------------------------------------------
# Series slug → canonical league_id (SSOT)
# ---------------------------------------------------------------------------

POLYMARKET_SERIES_TO_LEAGUE: dict[str, str] = {
    # England — canonical IDs from PREDICTION_LEAGUES registry
    "premier-league-2025": "EPL",
    "efl-championship": "ENG_CHAMPIONSHIP",
    # Spain
    "la-liga-2025": "LA_LIGA",
    "la-liga-2": "SEGUNDA_DIVISION",
    # Germany
    "bundesliga-2025": "BUNDESLIGA",
    "bundesliga-2": "BUNDESLIGA_2",
    # Italy
    "serie-a-2025": "SERIE_A",
    "serie-b": "SERIE_B",
    # France
    "ligue-1-2025": "LIGUE_1",
    "ligue-2": "LIGUE_2",
    # Netherlands
    "ere-2025": "EREDIVISIE",
    "eredivisie-2025": "EREDIVISIE",
    # Portugal
    "primeira-liga": "PRIMEIRA_LIGA",
    "primeira-liga-2025": "PRIMEIRA_LIGA",
    # Belgium
    "jupiler-pro-league-2025": "JUPILER_PRO",
    # Scotland
    "scottish-premiership": "SCOTTISH_PREMIERSHIP",
    "scottish-premiership-2025": "SCOTTISH_PREMIERSHIP",
    # Turkey
    "tur-2025": "SUPER_LIG",
    "super-lig-2025": "SUPER_LIG",
    # Greece
    "greek-super-league-2025": "GREEK_SUPER_LEAGUE",
    # Denmark
    "denmark-superliga": "DANISH_SUPERLIGA",
    "danish-superliga-2025": "DANISH_SUPERLIGA",
    # Norway
    "norway-eliteserien": "ELITESERIEN",
    "eliteserien-2025": "ELITESERIEN",
    # Sweden
    "allsvenskan-2025": "ALLSVENSKAN",
    # Austria
    "austrian-bundesliga-2025": "AUSTRIAN_BUNDESLIGA",
    # Switzerland
    "swiss-super-league-2025": "SWISS_SUPER_LEAGUE",
    # Poland
    "ekstraklasa-2025": "EKSTRAKLASA",
    # Americas
    "mls-2025": "MLS",
    "mex-2025": "LIGA_MX",
    "liga-mx-2025": "LIGA_MX",
    "primera-divisin-argentina": "ARGENTINA_PRIMERA",
    "argentina-primera-division-2025": "ARGENTINA_PRIMERA",
    "brazil-serie-a": "BRASILEIRAO",
    "brasileirao-2025": "BRASILEIRAO",
    "chile-primera-2025": "CHILE_PRIMERA",
    # Asia / Oceania
    "a-league-soccer": "A_LEAGUE",
    "a-league-2025": "A_LEAGUE",
    "japan-j-league": "J1_LEAGUE",
    "j1-league-2025": "J1_LEAGUE",
    "k-league": "K_LEAGUE_1",
    "k-league-2025": "K_LEAGUE_1",
    # Continental — canonical league_id from LEAGUE_REGISTRY (tier 0 / Reference,
    # not in POLYMARKET_PREDICTION_LEAGUES: unlike the domestic leagues above,
    # UCL coverage on Polymarket has not been re-verified against live scan data).
    # "champions-league-2025" follows the established tag+year slug convention
    # (POLYMARKET_SPORTS_TAG_SLUGS already carries "champions-league"); "ucl-2025"
    # is kept as an alias since it's the slug assumed by the existing e2e test.
    "champions-league-2025": "UCL",
    "ucl-2025": "UCL",
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
        "BUNDESLIGA": "bundesliga",
        "LA_LIGA": "la-liga",
        "SERIE_A": "serie-a",
        "LIGUE_1": "ligue-1",
        "MLS": "mls",
        "EREDIVISIE": "eredivisie",
        "PRIMEIRA_LIGA": "primeira-liga",
        "SCOTTISH_PREMIERSHIP": "scottish-premiership",
        "A_LEAGUE": "a-league",
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
    stripped = re.sub(r"\s+(FC|CF|SC|SK|JK|AFC|SV|AC|SS|US|AS|RC|CD|UD|RCD|CA|SSC|CFC|BC)$", "", upper).strip()
    if stripped != upper:
        result = _POLYMARKET_LOOKUP.get(stripped)
        if result is not None:
            return result
    return None
