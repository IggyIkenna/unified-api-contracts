"""API-Football team name → canonical team ID mappings.

Canonical team IDs follow SCREAMING_SNAKE_CASE convention:
- ``MAN_CITY``, ``TOTTENHAM``, ``DORTMUND``, ``AJAX``

Covers all 33 prediction leagues (2010-2026), including promoted and
recently relegated teams.

Source: Ported from footballbets/utils/mapping.py and
        instruments-service/instruments_service/sports/team_mapping_data*.py
"""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime

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
    "LEIPZIG": ["LEIPZIG", "RB LEIPZIG", "RB Leipzig", "RasenBallsport Leipzig"],
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
    "PREUSSEN_MUNSTER": [
        "SC PREUSSEN MUNSTER",
        "PREUSSEN MUNSTER",
        "SC Preußen Münster",
        "Preußen Münster",
    ],
}

# ---------------------------------------------------------------------------
# La Liga / Segunda Division: canonical_team_id → list of known name variations
# ---------------------------------------------------------------------------

LA_LIGA_TEAM_ALIASES: dict[str, list[str]] = {
    "ATHLETIC_CLUB": ["ATHLETIC CLUB", "ATHLETIC BILBAO", "Athletic Club", "Athletic Bilbao"],
    "ATLETICO_MADRID": [
        "ATLETICO MADRID",
        "ATLETICO DE MADRID",
        "Atlético Madrid",
        "Atletico Madrid",
        "Atletico de Madrid",
    ],
    "BARCELONA": ["BARCELONA", "FC BARCELONA", "Barcelona", "FC Barcelona"],
    "REAL_MADRID": ["REAL MADRID", "Real Madrid", "Real Madrid CF"],
    "REAL_SOCIEDAD": ["REAL SOCIEDAD", "Real Sociedad"],
    "REAL_SOCIEDAD_B": ["REAL SOCIEDAD B", "REAL SOCIEDAD II", "Real Sociedad B", "Real Sociedad II"],
    "REAL_BETIS": ["REAL BETIS", "Real Betis", "Real Betis Balompie"],
    "REAL_VALLADOLID": ["REAL VALLADOLID", "VALLADOLID", "Real Valladolid CF", "Valladolid"],
    "SEVILLA": ["SEVILLA", "SEVILLA FC", "Sevilla", "Sevilla FC"],
    "VILLARREAL": ["VILLARREAL", "Villarreal", "Villarreal CF"],
    "CELTA_VIGO": ["CELTA VIGO", "CELTA", "Celta Vigo", "RC Celta"],
    "GETAFE": ["GETAFE", "Getafe", "Getafe CF"],
    "VALENCIA": ["VALENCIA", "Valencia", "Valencia CF"],
    "MALLORCA": ["MALLORCA", "RCD Mallorca", "Mallorca"],
    "OSASUNA": ["OSASUNA", "CA Osasuna", "Osasuna"],
    "RAYO_VALLECANO": ["RAYO VALLECANO", "Rayo Vallecano"],
    "ALAVES": ["ALAVES", "Deportivo Alaves", "Alaves"],
    "LEGANES": ["LEGANES", "CD Leganes", "Leganes"],
    "ESPANYOL": ["ESPANYOL", "RCD Espanyol", "Espanyol"],
    "LAS_PALMAS": ["LAS PALMAS", "UD Las Palmas", "Las Palmas"],
    "GIRONA": ["GIRONA", "Girona", "Girona FC"],
    "BURGOS": ["BURGOS", "BURGOS CF", "Burgos CF", "Burgos"],
    "MIRANDES": ["MIRANDES", "CD MIRANDES", "CD Mirandés", "Mirandes"],
    "SPORTING_GIJON": ["SPORTING GIJON", "Sporting Gijón", "Sporting Gijon"],
    "CORDOBA": ["CORDOBA", "Córdoba", "Cordoba"],
}

# ---------------------------------------------------------------------------
# Serie A / Serie B: canonical_team_id → list of known name variations
# ---------------------------------------------------------------------------

SERIE_A_TEAM_ALIASES: dict[str, list[str]] = {
    "ATALANTA": ["ATALANTA", "ATALANTA BC", "Atalanta BC", "Atalanta"],
    "INTER_MILAN": ["INTER MILAN", "INTER", "Inter Milan", "Inter", "FC Internazionale"],
    "JUVENTUS": ["JUVENTUS", "Juventus", "Juventus FC"],
    "AC_MILAN": ["AC MILAN", "MILAN", "AC Milan", "Milan"],
    "NAPOLI": ["NAPOLI", "SSC Napoli", "Napoli"],
    "ROMA": ["ROMA", "AS ROMA", "AS Roma", "Roma"],
    "LAZIO": ["LAZIO", "SS Lazio", "Lazio"],
    "FIORENTINA": ["FIORENTINA", "ACF FIORENTINA", "Fiorentina", "ACF Fiorentina"],
    "TORINO": ["TORINO", "Torino", "Torino FC"],
    "BOLOGNA": ["BOLOGNA", "Bologna", "Bologna FC"],
    "UDINESE": ["UDINESE", "Udinese", "Udinese Calcio"],
    "GENOA": ["GENOA", "Genoa", "Genoa CFC"],
    "CAGLIARI": ["CAGLIARI", "Cagliari"],
    "EMPOLI": ["EMPOLI", "Empoli"],
    "LECCE": ["LECCE", "Lecce", "US Lecce"],
    "MONZA": ["MONZA", "Monza", "AC Monza"],
    "VERONA": ["VERONA", "HELLAS VERONA", "Hellas Verona"],
    "COMO": ["COMO", "Como", "Como 1907"],
    "PARMA": ["PARMA", "Parma", "Parma Calcio 1913"],
    "VENEZIA": ["VENEZIA", "Venezia", "Venezia FC"],
    "SALERNITANA": ["SALERNITANA", "Salernitana"],
    "SASSUOLO": ["SASSUOLO", "Sassuolo"],
    "FROSINONE": ["FROSINONE", "Frosinone"],
    "SUDTIROL": ["SUDTIROL", "Südtirol", "Sudtirol", "FC Sudtirol"],
}

# ---------------------------------------------------------------------------
# Ligue 1 / Ligue 2: canonical_team_id → list of known name variations
# ---------------------------------------------------------------------------

LIGUE_1_TEAM_ALIASES: dict[str, list[str]] = {
    "PSG": ["PSG", "PARIS SAINT-GERMAIN", "PARIS SAINT GERMAIN", "Paris Saint Germain"],
    "MONACO": ["MONACO", "AS MONACO", "AS Monaco", "Monaco"],
    "MARSEILLE": ["MARSEILLE", "OLYMPIQUE MARSEILLE", "Olympique Marseille"],
    "LYON": ["LYON", "OLYMPIQUE LYONNAIS", "Olympique Lyonnais"],
    "LILLE": ["LILLE", "LILLE OSC", "Lille", "Lille OSC"],
    "NICE": ["NICE", "OGC NICE", "OGC Nice", "Nice"],
    "LENS": ["LENS", "RC Lens", "Lens"],
    "RENNES": ["RENNES", "Stade Rennais", "Rennes"],
    "STRASBOURG": ["STRASBOURG", "RC Strasbourg", "Strasbourg"],
    "NANTES": ["NANTES", "FC Nantes", "Nantes"],
    "MONTPELLIER": ["MONTPELLIER", "Montpellier HSC", "Montpellier"],
    "BREST": ["BREST", "Stade Brestois", "Brest"],
    "TOULOUSE": ["TOULOUSE", "Toulouse FC", "Toulouse"],
    "REIMS": ["REIMS", "Stade de Reims", "Reims"],
    "AUXERRE": ["AUXERRE", "AJ Auxerre", "Auxerre"],
    "ANGERS": ["ANGERS", "Angers SCO", "Angers"],
    "LE_HAVRE": ["LE HAVRE", "Le Havre", "Le Havre AC"],
    "SAINT_ETIENNE": [
        "SAINT-ETIENNE",
        "SAINT ETIENNE",
        "AS Saint-Etienne",
        "Saint-Etienne",
        "St Etienne",
        "AS St-Etienne",
    ],
}

# ---------------------------------------------------------------------------
# Eredivisie: canonical_team_id → list of known name variations
# ---------------------------------------------------------------------------

EREDIVISIE_TEAM_ALIASES: dict[str, list[str]] = {
    "AJAX": ["AJAX", "Ajax", "AFC Ajax"],
    "PSV": ["PSV", "PSV EINDHOVEN", "PSV Eindhoven"],
    "FEYENOORD": ["FEYENOORD", "Feyenoord"],
    "AZ": ["AZ", "AZ ALKMAAR", "AZ Alkmaar"],
    "TWENTE": ["TWENTE", "FC Twente", "FC TWENTE"],
    "UTRECHT": ["UTRECHT", "FC UTRECHT", "FC Utrecht", "Utrecht"],
    "VITESSE": ["VITESSE", "Vitesse"],
    "HEERENVEEN": ["HEERENVEEN", "SC Heerenveen"],
    "GRONINGEN": ["GRONINGEN", "FC Groningen"],
    "SPARTA_ROTTERDAM": ["SPARTA ROTTERDAM", "Sparta Rotterdam"],
    "NEC": ["NEC", "NEC NIJMEGEN", "NEC Nijmegen"],
    "GO_AHEAD_EAGLES": ["GO AHEAD EAGLES", "Go Ahead Eagles"],
    "HERACLES": ["HERACLES", "Heracles Almelo"],
    "FORTUNA_SITTARD": ["FORTUNA SITTARD", "Fortuna Sittard"],
    "ALMERE_CITY": ["ALMERE CITY", "Almere City FC"],
    "WAALWIJK": ["WAALWIJK", "RKC Waalwijk"],
    "VOLENDAM": ["VOLENDAM", "FC Volendam"],
    "TELSTAR": ["TELSTAR", "SC TELSTAR", "SC Telstar", "Telstar"],
}

# ---------------------------------------------------------------------------
# Primeira Liga (Portugal): canonical_team_id → list of known name variations
# ---------------------------------------------------------------------------

PRIMEIRA_LIGA_TEAM_ALIASES: dict[str, list[str]] = {
    "BENFICA": ["BENFICA", "SL Benfica", "Benfica"],
    "PORTO": ["PORTO", "FC Porto", "Porto"],
    "SPORTING_CP": ["SPORTING CP", "SPORTING LISBON", "Sporting Lisbon", "Sporting CP"],
    "BRAGA": ["BRAGA", "SC BRAGA", "SC Braga", "Braga"],
    "VITORIA_GUIMARAES": ["VITORIA GUIMARAES", "Vitoria de Guimaraes", "Vitoria Guimaraes"],
    "RIO_AVE": ["RIO AVE", "RIO AVE FC", "Rio Ave FC", "Rio Ave"],
    "GIL_VICENTE": ["GIL VICENTE", "Gil Vicente"],
    "BOAVISTA": ["BOAVISTA", "Boavista"],
    "FAMALICAO": ["FAMALICAO", "FC Famalicao", "Famalicao"],
    "CASA_PIA": ["CASA PIA", "Casa Pia AC", "Casa Pia"],
    "AROUCA": ["AROUCA", "FC Arouca", "Arouca"],
    "MOREIRENSE": ["MOREIRENSE", "Moreirense FC", "Moreirense"],
    "ESTORIL": ["ESTORIL", "Estoril Praia", "Estoril"],
    "ESTRELA_AMADORA": ["ESTRELA AMADORA", "Estrela da Amadora", "Estrela Amadora"],
}

# ---------------------------------------------------------------------------
# Belgian First Division: canonical_team_id → list of known name variations
# ---------------------------------------------------------------------------

JUPILER_PRO_TEAM_ALIASES: dict[str, list[str]] = {
    "CLUB_BRUGGE": ["CLUB BRUGGE", "CLUB BRUGGE KV", "Club Brugge", "Club Brugge KV"],
    "ANDERLECHT": ["ANDERLECHT", "RSC Anderlecht", "Anderlecht"],
    "GENK": ["GENK", "KRC Genk", "Genk"],
    "GENT": ["GENT", "KAA Gent", "Gent"],
    "ANTWERP": ["ANTWERP", "Royal Antwerp", "Antwerp FC"],
    "SINT_TRUIDEN": ["SINT TRUIDEN", "ST. TRUIDEN", "STVV", "Sint Truiden", "St. Truiden"],
    "UNION_SG": [
        "UNION SAINT-GILLOISE",
        "UNION ST. GILLOISE",
        "Union Saint-Gilloise",
        "Union St. Gilloise",
    ],
    "WESTERLO": ["WESTERLO", "KVC WESTERLO", "Westerlo", "KVC Westerlo"],
    "CERCLE_BRUGGE": ["CERCLE BRUGGE", "CERCLE BRUGGE KSV", "Cercle Brugge KSV", "Cercle Brugge"],
    "ZULTE_WAREGEM": [
        "ZULTE WAREGEM",
        "SV ZULTE-WAREGEM",
        "SV Zulte-Waregem",
        "Zulte Waregem",
    ],
    "STANDARD_LIEGE": ["STANDARD LIEGE", "Standard Liege", "Standard de Liege"],
    "MECHELEN": ["MECHELEN", "KV Mechelen", "Mechelen"],
    "CHARLEROI": ["CHARLEROI", "Sporting Charleroi", "Charleroi"],
    "LEUVEN": ["LEUVEN", "OH Leuven", "Oud-Heverlee Leuven"],
    "KORTRIJK": ["KORTRIJK", "KV Kortrijk", "Kortrijk"],
}

# ---------------------------------------------------------------------------
# Danish Superliga: canonical_team_id → list of known name variations
# ---------------------------------------------------------------------------

DANISH_SUPERLIGA_TEAM_ALIASES: dict[str, list[str]] = {
    "COPENHAGEN": ["COPENHAGEN", "FC COPENHAGEN", "FC Copenhagen"],
    "MIDTJYLLAND": ["MIDTJYLLAND", "FC Midtjylland"],
    "BRONDBY": ["BRONDBY", "BRONDBY IF", "Brondby IF", "Brondby"],
    "NORDSJAELLAND": ["NORDSJAELLAND", "FC Nordsjaelland"],
    "SILKEBORG": ["SILKEBORG", "SILKEBORG IF", "Silkeborg IF", "Silkeborg"],
    "AARHUS": ["AARHUS", "AGF AARHUS", "AGF", "AGF Aarhus", "Aarhus"],
    "VIBORG": ["VIBORG", "VIBORG FF", "Viborg FF", "Viborg"],
    "AALBORG": ["AALBORG", "AaB", "Aalborg BK"],
    "RANDERS": ["RANDERS", "Randers FC"],
    "LYNGBY": ["LYNGBY", "Lyngby BK"],
    "HVIDOVRE": ["HVIDOVRE", "Hvidovre IF"],
    "VEJLE": ["VEJLE", "Vejle BK"],
}

# ---------------------------------------------------------------------------
# MLS (USA): canonical_team_id → list of known name variations
# ---------------------------------------------------------------------------

MLS_TEAM_ALIASES: dict[str, list[str]] = {
    "ATLANTA_UNITED": ["ATLANTA UNITED", "Atlanta United FC", "Atlanta United"],
    "AUSTIN": ["AUSTIN", "AUSTIN FC", "Austin FC", "Austin"],
    "CHARLOTTE": ["CHARLOTTE", "Charlotte FC"],
    "CHICAGO_FIRE": ["CHICAGO FIRE", "Chicago Fire FC"],
    "CINCINNATI": ["CINCINNATI", "FC Cincinnati"],
    "COLORADO_RAPIDS": ["COLORADO RAPIDS", "Colorado Rapids"],
    "COLUMBUS_CREW": ["COLUMBUS CREW", "Columbus Crew"],
    "DC_UNITED": ["DC UNITED", "D.C. United", "DC United"],
    "DALLAS": ["DALLAS", "FC Dallas"],
    "HOUSTON_DYNAMO": ["HOUSTON DYNAMO", "Houston Dynamo FC"],
    "INTER_MIAMI": ["INTER MIAMI", "INTER MIAMI CF", "Inter Miami CF", "Inter Miami"],
    "LA_GALAXY": ["LA GALAXY", "LOS ANGELES GALAXY", "LA Galaxy", "Los Angeles Galaxy"],
    "LAFC": ["LAFC", "Los Angeles FC"],
    "MINNESOTA_UNITED": ["MINNESOTA UNITED", "Minnesota United FC"],
    "MONTREAL": ["MONTREAL", "CF Montreal", "CF Montréal"],
    "NASHVILLE": ["NASHVILLE", "Nashville SC"],
    "NEW_ENGLAND_REVOLUTION": ["NEW ENGLAND REVOLUTION", "New England Revolution"],
    "NEW_YORK_RED_BULLS": ["NEW YORK RED BULLS", "New York Red Bulls"],
    "NYCFC": ["NYCFC", "New York City FC"],
    "ORLANDO_CITY": ["ORLANDO CITY", "Orlando City SC"],
    "PHILADELPHIA_UNION": ["PHILADELPHIA UNION", "Philadelphia Union"],
    "PORTLAND_TIMBERS": ["PORTLAND TIMBERS", "Portland Timbers"],
    "REAL_SALT_LAKE": ["REAL SALT LAKE", "Real Salt Lake"],
    "SAN_DIEGO": ["SAN DIEGO", "SAN DIEGO FC", "San Diego FC", "San Diego"],
    "SAN_JOSE_EARTHQUAKES": ["SAN JOSE EARTHQUAKES", "San Jose Earthquakes"],
    "SEATTLE_SOUNDERS": [
        "SEATTLE SOUNDERS",
        "SEATTLE SOUNDERS FC",
        "Seattle Sounders FC",
        "Seattle Sounders",
    ],
    "SPORTING_KC": ["SPORTING KC", "Sporting Kansas City"],
    "ST_LOUIS_CITY": ["ST. LOUIS CITY", "ST LOUIS CITY", "St. Louis City SC", "St. Louis City"],
    "TORONTO": ["TORONTO", "Toronto FC"],
    "VANCOUVER_WHITECAPS": [
        "VANCOUVER WHITECAPS",
        "VANCOUVER WHITECAPS FC",
        "Vancouver Whitecaps FC",
        "Vancouver Whitecaps",
    ],
}

# ---------------------------------------------------------------------------
# Austrian Bundesliga: canonical_team_id → list of known name variations
# ---------------------------------------------------------------------------

AUSTRIAN_BUNDESLIGA_TEAM_ALIASES: dict[str, list[str]] = {
    "RB_SALZBURG": ["RB SALZBURG", "Red Bull Salzburg", "FC Salzburg"],
    "STURM_GRAZ": ["STURM GRAZ", "SK Sturm Graz", "Sturm Graz II", "SK Sturm Graz II"],
    "AUSTRIA_WIEN": ["AUSTRIA WIEN", "AUSTRIA VIENNA", "Austria Wien", "Austria Vienna"],
    "RAPID_WIEN": ["RAPID WIEN", "RAPID VIENNA", "Rapid Wien", "Rapid Vienna"],
    "WOLFSBERGER": ["WOLFSBERGER", "Wolfsberger AC"],
    "HARTBERG": ["HARTBERG", "TSV HARTBERG", "Hartberg", "TSV Hartberg"],
    "LASK": ["LASK", "LASK LINZ", "LASK", "Lask Linz"],
    "ALTACH": ["ALTACH", "SCR Altach"],
    "AUSTRIA_KLAGENFURT": ["AUSTRIA KLAGENFURT", "SK Austria Klagenfurt"],
    "BLAU_WEISS_LINZ": ["BLAU WEISS LINZ", "FC Blau-Weiss Linz"],
    "GRAZER_AK": ["GRAZER AK", "GAK", "Grazer AK 1902"],
}

# ---------------------------------------------------------------------------
# Norwegian Eliteserien: canonical_team_id → list of known name variations
# ---------------------------------------------------------------------------

ELITESERIEN_TEAM_ALIASES: dict[str, list[str]] = {
    "BODO_GLIMT": ["BODO/GLIMT", "BODO GLIMT", "FK Bodo/Glimt"],
    "MOLDE": ["MOLDE", "Molde FK"],
    "ROSENBORG": ["ROSENBORG", "Rosenborg BK"],
    "BRANN": ["BRANN", "SK BRANN", "SK Brann", "Brann"],
    "VIKING": ["VIKING", "Viking FK"],
    "FREDRIKSTAD": ["FREDRIKSTAD", "FREDRIKSTAD FK", "Fredrikstad FK", "Fredrikstad"],
    "KFUM_OSLO": ["KFUM OSLO", "KFUM", "KFUM Oslo"],
    "SARPSBORG": ["SARPSBORG", "SARPSBORG FK", "SARPSBORG 08 FF", "Sarpsborg FK", "Sarpsborg 08 FF"],
    "TROMSO": ["TROMSO", "Tromso IL"],
    "LILLESTROM": ["LILLESTROM", "Lillestrom SK"],
    "HAUGESUND": ["HAUGESUND", "FK Haugesund"],
    "SANDEFJORD": ["SANDEFJORD", "Sandefjord Fotball"],
    "STROMSGODSET": ["STROMSGODSET", "Stromsgodset IF"],
    "KRISTIANSUND": ["KRISTIANSUND", "Kristiansund BK"],
    "HAMKAM": ["HAMKAM", "HamKam"],
    "ODD": ["ODD", "Odds BK"],
}

# ---------------------------------------------------------------------------
# Swiss Super League: canonical_team_id → list of known name variations
# ---------------------------------------------------------------------------

SWISS_SUPER_LEAGUE_TEAM_ALIASES: dict[str, list[str]] = {
    "YOUNG_BOYS": ["YOUNG BOYS", "BSC Young Boys"],
    "FC_BASEL": ["FC BASEL", "FC BASEL 1893", "FC Basel", "FC Basel 1893"],
    "FC_ZURICH": ["FC ZURICH", "FC Zurich"],
    "SERVETTE": ["SERVETTE", "Servette FC"],
    "LUGANO": ["LUGANO", "FC Lugano"],
    "ST_GALLEN": ["ST GALLEN", "FC St. Gallen"],
    "FC_LAUSANNE": [
        "FC LAUSANNE",
        "FC LAUSANNE-SPORT",
        "FC Lausanne-Sport",
        "Lausanne-Sport",
    ],
    "GRASSHOPPERS": ["GRASSHOPPERS", "Grasshopper Club Zurich"],
    "LUZERN": ["LUZERN", "FC Luzern"],
    "WINTERTHUR": ["WINTERTHUR", "FC Winterthur"],
    "SION": ["SION", "FC Sion"],
    "YVERDON": ["YVERDON", "Yverdon-Sport FC"],
}

# ---------------------------------------------------------------------------
# Scottish Premiership: canonical_team_id → list of known name variations
# ---------------------------------------------------------------------------

SCOTTISH_PREMIERSHIP_TEAM_ALIASES: dict[str, list[str]] = {
    "CELTIC": ["CELTIC", "Celtic FC", "Celtic"],
    "RANGERS": ["RANGERS", "Rangers FC", "Rangers"],
    "ABERDEEN": ["ABERDEEN", "Aberdeen FC", "Aberdeen"],
    "HEARTS": ["HEARTS", "Heart of Midlothian", "Hearts"],
    "HIBERNIAN": ["HIBERNIAN", "Hibernian FC"],
    "DUNDEE": ["DUNDEE", "Dundee FC", "Dundee"],
    "DUNDEE_UNITED": ["DUNDEE UNITED", "DUNDEE UTD", "Dundee United", "Dundee Utd"],
    "KILMARNOCK": ["KILMARNOCK", "Kilmarnock FC"],
    "MOTHERWELL": ["MOTHERWELL", "Motherwell FC"],
    "ST_MIRREN": ["ST MIRREN", "St. Mirren", "St Mirren"],
    "ST_JOHNSTONE": ["ST JOHNSTONE", "St. Johnstone", "St Johnstone"],
    "ROSS_COUNTY": ["ROSS COUNTY", "Ross County FC"],
}

# ---------------------------------------------------------------------------
# A-League (Australia): canonical_team_id → list of known name variations
# ---------------------------------------------------------------------------

A_LEAGUE_TEAM_ALIASES: dict[str, list[str]] = {
    "MELBOURNE_VICTORY": ["MELBOURNE VICTORY", "Melbourne Victory"],
    "MELBOURNE_CITY": ["MELBOURNE CITY", "Melbourne City FC"],
    "SYDNEY_FC": ["SYDNEY FC", "SYDNEY", "Sydney FC", "Sydney"],
    "WESTERN_SYDNEY": ["WESTERN SYDNEY WANDERERS", "Western Sydney Wanderers"],
    "CENTRAL_COAST_MARINERS": ["CENTRAL COAST MARINERS", "Central Coast Mariners"],
    "NEWCASTLE_JETS": [
        "NEWCASTLE JETS",
        "NEWCASTLE JETS FC",
        "Newcastle Jets FC",
        "Newcastle Jets",
    ],
    "PERTH_GLORY": ["PERTH GLORY", "Perth Glory"],
    "ADELAIDE_UNITED": ["ADELAIDE UNITED", "Adelaide United"],
    "WELLINGTON_PHOENIX": ["WELLINGTON PHOENIX", "Wellington Phoenix"],
    "BRISBANE_ROAR": ["BRISBANE ROAR", "Brisbane Roar"],
    "MACARTHUR": ["MACARTHUR", "Macarthur FC"],
    "WESTERN_UNITED": ["WESTERN UNITED", "Western United FC"],
    "AUCKLAND": ["AUCKLAND FC", "Auckland FC"],
}

# ---------------------------------------------------------------------------
# Liga MX (Mexico): canonical_team_id → list of known name variations
# ---------------------------------------------------------------------------

LIGA_MX_TEAM_ALIASES: dict[str, list[str]] = {
    "CLUB_AMERICA": [
        "CLUB AMERICA",
        "AMERICA",
        "América",
        "Club America",
        "America",
    ],
    "GUADALAJARA": [
        "GUADALAJARA",
        "GUADALAJARA CHIVAS",
        "Guadalajara",
        "Guadalajara Chivas",
        "CD Guadalajara",
    ],
    "CRUZ_AZUL": ["CRUZ AZUL", "Cruz Azul"],
    "PUMAS_UNAM": ["PUMAS UNAM", "PUMAS", "Pumas", "U.N.A.M. - Pumas", "UNAM Pumas"],
    "TIGRES": ["TIGRES", "Tigres UANL"],
    "MONTERREY": ["MONTERREY", "CF Monterrey"],
    "SANTOS_LAGUNA": ["SANTOS LAGUNA", "Santos Laguna"],
    "LEON": ["LEON", "Club Leon"],
    "TOLUCA": ["TOLUCA", "Deportivo Toluca"],
    "PACHUCA": ["PACHUCA", "CF Pachuca"],
    "ATLAS": ["ATLAS", "Atlas FC"],
    "QUERETARO": ["QUERETARO", "Club Queretaro"],
    "PUEBLA": ["PUEBLA", "Club Puebla"],
    "NECAXA": ["NECAXA", "Club Necaxa"],
    "MAZATLAN": ["MAZATLAN", "Mazatlan FC"],
    "JUAREZ": ["JUAREZ", "FC Juarez"],
    "TIJUANA": ["TIJUANA", "Club Tijuana"],
    "SAN_LUIS": ["SAN LUIS", "Atletico San Luis"],
}

# ---------------------------------------------------------------------------
# Argentine Primera: canonical_team_id → list of known name variations
# ---------------------------------------------------------------------------

ARGENTINA_PRIMERA_TEAM_ALIASES: dict[str, list[str]] = {
    "BOCA_JUNIORS": ["BOCA JUNIORS", "Boca Juniors"],
    "RIVER_PLATE": ["RIVER PLATE", "River Plate"],
    "RACING_CLUB": ["RACING CLUB", "Racing Club"],
    "INDEPENDIENTE": ["INDEPENDIENTE", "CA Independiente"],
    "SAN_LORENZO": ["SAN LORENZO", "San Lorenzo"],
    "VELEZ_SARSFIELD": ["VELEZ SARSFIELD", "Velez Sarsfield"],
    "ESTUDIANTES": ["ESTUDIANTES", "Estudiantes LP"],
    "LANUS": ["LANUS", "Lanus"],
    "TALLERES": ["TALLERES", "Talleres Cordoba"],
    "BELGRANO": ["BELGRANO", "BELGRANO DE CORDOBA", "Belgrano de Cordoba", "Belgrano Cordoba"],
    "SARMIENTO": ["SARMIENTO", "SARMIENTO DE JUNIN", "Sarmiento de Junin", "Sarmiento Junin"],
    "ALDOSIVI": ["ALDOSIVI", "ALDOSIVI MAR DEL PLATA", "Aldosivi Mar del Plata", "Aldosivi"],
    "INSTITUTO": [
        "INSTITUTO",
        "INSTITUTO DE CORDOBA",
        "Instituto de Córdoba",
        "Instituto Cordoba",
    ],
    "DEFENSA_JUSTICIA": ["DEFENSA Y JUSTICIA", "Defensa y Justicia"],
    "ARGENTINOS_JUNIORS": ["ARGENTINOS JUNIORS", "Argentinos Juniors"],
    "BANFIELD": ["BANFIELD", "CA Banfield"],
    "CENTRAL_CORDOBA": ["CENTRAL CORDOBA", "Central Cordoba SE"],
    "COLON": ["COLON", "Colon Santa Fe"],
    "GODOY_CRUZ": ["GODOY CRUZ", "Godoy Cruz"],
    "HURACAN": ["HURACAN", "CA Huracan"],
    "NEWELLS_OLD_BOYS": ["NEWELL'S OLD BOYS", "NEWELLS OLD BOYS", "Newell's Old Boys"],
    "PLATENSE": ["PLATENSE", "Club Atletico Platense"],
    "ROSARIO_CENTRAL": ["ROSARIO CENTRAL", "Rosario Central"],
    "TIGRE": ["TIGRE", "CA Tigre"],
    "UNION_SANTA_FE": ["UNION", "UNION SANTA FE", "Union de Santa Fe"],
}

# ---------------------------------------------------------------------------
# Brasileirao: canonical_team_id → list of known name variations
# ---------------------------------------------------------------------------

BRASILEIRAO_TEAM_ALIASES: dict[str, list[str]] = {
    "FLAMENGO": ["FLAMENGO", "Flamengo"],
    "PALMEIRAS": ["PALMEIRAS", "SE Palmeiras"],
    "GREMIO": ["GREMIO", "Grêmio", "Gremio"],
    "INTERNACIONAL": ["INTERNACIONAL", "SC Internacional"],
    "ATHLETICO_PARANAENSE": ["ATHLETICO PARANAENSE", "Athletico-PR", "Athletico Paranaense"],
    "FLUMINENSE": ["FLUMINENSE", "Fluminense FC"],
    "CORINTHIANS": ["CORINTHIANS", "SC Corinthians"],
    "SAO_PAULO": ["SAO PAULO", "Sao Paulo FC"],
    "SANTOS": ["SANTOS", "Santos FC"],
    "BOTAFOGO": ["BOTAFOGO", "Botafogo FR"],
    "VASCO_DA_GAMA": ["VASCO DA GAMA", "Vasco da Gama", "CR Vasco da Gama"],
    "CRUZEIRO": ["CRUZEIRO", "Cruzeiro"],
    "ATLETICO_MINEIRO": ["ATLETICO MINEIRO", "Atletico Mineiro", "Atletico-MG"],
    "BAHIA": ["BAHIA", "EC Bahia"],
    "FORTALEZA": ["FORTALEZA", "Fortaleza EC"],
    "CEARA": ["CEARA", "Ceara SC"],
    "GOIAS": ["GOIAS", "Goias EC"],
    "CORITIBA": ["CORITIBA", "Coritiba FC"],
    "CHAPECOENSE": ["CHAPECOENSE", "CHAPECOENSE-SC", "Chapecoense", "Chapecoense-sc"],
    "JUVENTUDE": ["JUVENTUDE", "EC Juventude"],
    "CUIABA": ["CUIABA", "Cuiaba EC"],
    "AMERICA_MINEIRO": ["AMERICA MINEIRO", "America Mineiro"],
    "BRAGANTINO": ["BRAGANTINO", "Red Bull Bragantino"],
    "VITORIA": ["VITORIA", "EC Vitoria"],
    "CRICIUMA": ["CRICIUMA", "Criciuma EC"],
}

# ---------------------------------------------------------------------------
# Greek Super League: canonical_team_id → list of known name variations
# ---------------------------------------------------------------------------

GREEK_SUPER_LEAGUE_TEAM_ALIASES: dict[str, list[str]] = {
    "OLYMPIAKOS": ["OLYMPIAKOS", "OLYMPIAKOS PIRAEUS", "Olympiakos Piraeus", "Olympiakos"],
    "PANATHINAIKOS": ["PANATHINAIKOS", "Panathinaikos FC"],
    "AEK_ATHENS": ["AEK ATHENS", "AEK ATHENS FC", "AEK Athens", "AEK Athens FC"],
    "PAOK": ["PAOK", "PAOK THESSALONIKI", "PAOK Thessaloniki", "PAOK"],
    "ARIS": ["ARIS", "ARIS THESSALONIKI", "Aris Thessaloniki", "Aris Thessalonikis"],
    "OFI": ["OFI", "OFI CRETE", "OFI Crete", "OFI"],
    "ATROMITOS": ["ATROMITOS", "ATROMITOS ATHENS", "Atromitos Athens", "Atromitos"],
    "VOLOS": ["VOLOS", "VOLOS FC", "VOLOS NFC", "Volos FC", "Volos NFC"],
    "PANETOLIKOS": [
        "PANETOLIKOS",
        "PANETOLIKOS AGRINIO",
        "Panetolikos Agrinio",
        "Panetolikos",
    ],
    "PANSERRAIKOS": ["PANSERRAIKOS", "PANSERRAIKOS FC", "Panserraikos FC", "Panserraikos"],
    "AEL": ["AEL", "AEL LARISSA", "LARISA", "AEL", "Larisa", "AEL Larissa"],
    "LAMIA": ["LAMIA", "PAS Lamia"],
    "ASTERAS_TRIPOLIS": ["ASTERAS TRIPOLIS", "Asteras Tripolis"],
    "IONIKOS": ["IONIKOS", "Ionikos FC"],
    "LEVADIAKOS": ["LEVADIAKOS", "Levadiakos FC"],
    "GIANNINA": ["GIANNINA", "PAS Giannina"],
}

# ---------------------------------------------------------------------------
# Ekstraklasa (Poland): canonical_team_id → list of known name variations
# ---------------------------------------------------------------------------

EKSTRAKLASA_TEAM_ALIASES: dict[str, list[str]] = {
    "LEGIA_WARSAW": ["LEGIA WARSAW", "Legia Warszawa", "Legia Warsaw"],
    "LECH_POZNAN": ["LECH POZNAN", "Lech Poznań", "Lech Poznan"],
    "RAKOW": ["RAKOW", "Rakow Czestochowa"],
    "JAGIELLONIA": ["JAGIELLONIA", "Jagiellonia Bialystok"],
    "POGON_SZCZECIN": ["POGON SZCZECIN", "Pogon Szczecin"],
    "SLASK_WROCLAW": ["SLASK WROCLAW", "Slask Wroclaw"],
    "WIDZEW_LODZ": ["WIDZEW LODZ", "Widzew Łódź", "Widzew Lodz"],
    "GORNIK_ZABRZE": ["GORNIK ZABRZE", "Górnik Zabrze", "Gornik Zabrze"],
    "CRACOVIA": ["CRACOVIA", "MKS Cracovia"],
    "PIAST_GLIWICE": ["PIAST GLIWICE", "Piast Gliwice"],
    "WARTA_POZNAN": ["WARTA POZNAN", "Warta Poznan"],
    "ZAGLEBIE_LUBIN": ["ZAGLEBIE LUBIN", "Zaglebie Lubin"],
    "STAL_MIELEC": ["STAL MIELEC", "Stal Mielec"],
    "KORONA_KIELCE": ["KORONA KIELCE", "Korona Kielce"],
    "MOTOR_LUBLIN": ["MOTOR LUBLIN", "Motor Lublin"],
    "RADOMIAK": ["RADOMIAK", "Radomiak Radom"],
    "PUSZCZA_NIEPOLOMICE": ["PUSZCZA NIEPOLOMICE", "Puszcza Niepolomice"],
    "GORNIK_LECZNA": ["GORNIK LECZNA", "Gornik Leczna"],
}

# ---------------------------------------------------------------------------
# Super Lig (Turkey): canonical_team_id → list of known name variations
# ---------------------------------------------------------------------------

SUPER_LIG_TEAM_ALIASES: dict[str, list[str]] = {
    "GALATASARAY": ["GALATASARAY", "Galatasaray SK"],
    "FENERBAHCE": ["FENERBAHCE", "Fenerbahce SK"],
    "BESIKTAS": ["BESIKTAS", "Besiktas JK"],
    "TRABZONSPOR": ["TRABZONSPOR", "Trabzonspor"],
    "ISTANBUL_BASAKSEHIR": ["ISTANBUL BASAKSEHIR", "Istanbul Basaksehir FK"],
    "ANTALYASPOR": ["ANTALYASPOR", "Antalyaspor"],
    "ADANA_DEMIRSPOR": ["ADANA DEMIRSPOR", "Adana Demirspor"],
    "KONYASPOR": ["KONYASPOR", "Konyaspor"],
    "SIVASSPOR": ["SIVASSPOR", "Sivasspor"],
    "ALANYASPOR": ["ALANYASPOR", "Alanyaspor"],
    "GAZIANTEP": ["GAZIANTEP", "Gaziantep FK"],
    "KAYSERISPOR": ["KAYSERISPOR", "Kayserispor"],
    "KASIMPASA": ["KASIMPASA", "Kasimpasa SK"],
    "HATAYSPOR": ["HATAYSPOR", "Hatayspor"],
    "PENDIKSPOR": ["PENDIKSPOR", "Pendikspor"],
    "RIZESPOR": ["RIZESPOR", "Caykur Rizespor"],
    "SAMSUNSPOR": ["SAMSUNSPOR", "Samsunspor"],
    "EYUPSPOR": ["EYUPSPOR", "Eyupspor"],
    "BODRUMSPOR": ["BODRUMSPOR", "Bodrumspor"],
    "GOZTEPE": ["GOZTEPE", "Goztepe SK"],
}

# ---------------------------------------------------------------------------
# Allsvenskan (Sweden): canonical_team_id → list of known name variations
# ---------------------------------------------------------------------------

ALLSVENSKAN_TEAM_ALIASES: dict[str, list[str]] = {
    "MALMO": ["MALMO", "Malmo FF"],
    "AIK": ["AIK", "AIK Stockholm", "AIK Solna"],
    "DJURGARDEN": ["DJURGARDEN", "Djurgardens IF"],
    "HAMMARBY": ["HAMMARBY", "Hammarby IF"],
    "IFK_GOTEBORG": ["IFK GOTEBORG", "IFK Gothenburg"],
    "ELFSBORG": ["ELFSBORG", "IF Elfsborg"],
    "NORRKOPING": ["NORRKOPING", "IFK Norrkoping"],
    "HACKEN": ["HACKEN", "BK Hacken"],
    "SIRIUS": ["SIRIUS", "IK Sirius"],
    "HALMSTAD": ["HALMSTAD", "Halmstads BK"],
    "KALMAR": ["KALMAR", "Kalmar FF"],
    "VARBERG": ["VARBERG", "Varbergs BoIS"],
    "MJALLBY": ["MJALLBY", "Mjallby AIF"],
    "DEGERFORS": ["DEGERFORS", "Degerfors IF"],
    "BROMMAPOJKARNA": ["BROMMAPOJKARNA", "IF Brommapojkarna"],
    "VASTERAAS": ["VASTERAAS", "Vasteras SK"],
    "SUNDSVALL": ["SUNDSVALL", "GIF Sundsvall"],
}

# ---------------------------------------------------------------------------
# J1 League (Japan): canonical_team_id → list of known name variations
# ---------------------------------------------------------------------------

J1_LEAGUE_TEAM_ALIASES: dict[str, list[str]] = {
    "VISSEL_KOBE": ["VISSEL KOBE", "Vissel Kobe"],
    "YOKOHAMA_F_MARINOS": ["YOKOHAMA F. MARINOS", "Yokohama F. Marinos"],
    "KAWASAKI_FRONTALE": ["KAWASAKI FRONTALE", "Kawasaki Frontale"],
    "URAWA_REDS": ["URAWA REDS", "Urawa Red Diamonds"],
    "KASHIMA_ANTLERS": ["KASHIMA ANTLERS", "Kashima Antlers"],
    "FC_TOKYO": ["FC TOKYO", "FC Tokyo"],
    "NAGOYA_GRAMPUS": ["NAGOYA GRAMPUS", "Nagoya Grampus"],
    "SANFRECCE_HIROSHIMA": ["SANFRECCE HIROSHIMA", "Sanfrecce Hiroshima"],
    "CEREZO_OSAKA": ["CEREZO OSAKA", "Cerezo Osaka"],
    "GAMBA_OSAKA": ["GAMBA OSAKA", "Gamba Osaka"],
    "CONSADOLE_SAPPORO": ["CONSADOLE SAPPORO", "Hokkaido Consadole Sapporo"],
    "SAGAN_TOSU": ["SAGAN TOSU", "Sagan Tosu"],
    "MACHIDA_ZELVIA": ["MACHIDA ZELVIA", "FC Machida Zelvia"],
    "AVISPA_FUKUOKA": ["AVISPA FUKUOKA", "Avispa Fukuoka"],
    "ALBIREX_NIIGATA": ["ALBIREX NIIGATA", "Albirex Niigata"],
    "TOKYO_VERDY": ["TOKYO VERDY", "Tokyo Verdy"],
    "JUBILO_IWATA": ["JUBILO IWATA", "Jubilo Iwata"],
    "KASHIWA_REYSOL": ["KASHIWA REYSOL", "Kashiwa Reysol"],
}

# ---------------------------------------------------------------------------
# K League 1 (South Korea): canonical_team_id → list of known name variations
# ---------------------------------------------------------------------------

K_LEAGUE_1_TEAM_ALIASES: dict[str, list[str]] = {
    "ULSAN_HD": ["ULSAN HD", "Ulsan HD FC"],
    "JEONBUK": ["JEONBUK", "Jeonbuk Hyundai Motors"],
    "POHANG_STEELERS": ["POHANG STEELERS", "Pohang Steelers"],
    "INCHEON_UNITED": ["INCHEON UNITED", "Incheon United FC"],
    "SUWON_BLUEWINGS": ["SUWON BLUEWINGS", "Suwon Samsung Bluewings"],
    "DAEJEON_CITIZEN": ["DAEJEON CITIZEN", "Daejeon Citizen FC"],
    "DAEGU": ["DAEGU", "Daegu FC"],
    "GWANGJU": ["GWANGJU", "Gwangju FC"],
    "GANGWON": ["GANGWON", "Gangwon FC"],
    "FC_SEOUL": ["FC SEOUL", "FC Seoul"],
    "JEJU_UNITED": ["JEJU UNITED", "Jeju United FC"],
    "GIMCHEON_SANGMU": ["GIMCHEON SANGMU", "Gimcheon Sangmu FC"],
}

# ---------------------------------------------------------------------------
# Chile Primera Division: canonical_team_id → list of known name variations
# ---------------------------------------------------------------------------

CHILE_PRIMERA_TEAM_ALIASES: dict[str, list[str]] = {
    "COLO_COLO": ["COLO COLO", "Colo-Colo"],
    "UNIVERSIDAD_DE_CHILE": ["UNIVERSIDAD DE CHILE", "Universidad de Chile"],
    "UNIVERSIDAD_CATOLICA": ["UNIVERSIDAD CATOLICA", "CD Universidad Catolica"],
    "COBRELOA": ["COBRELOA", "Club de Deportes Cobreloa"],
    "HUACHIPATO": ["HUACHIPATO", "CD Huachipato"],
    "UNION_ESPANOLA": ["UNION ESPANOLA", "Union Espanola"],
    "COBRESAL": ["COBRESAL", "CD Cobresal"],
    "AUDAX_ITALIANO": ["AUDAX ITALIANO", "Audax Italiano"],
    "OHIGGINS": ["O'HIGGINS", "OHIGGINS", "O'Higgins FC"],
    "PALESTINO": ["PALESTINO", "CD Palestino"],
    "EVERTON_CHILE": ["EVERTON DE VINA", "Everton de Vina del Mar"],
    "CURICO_UNIDO": ["CURICO UNIDO", "CD Curico Unido"],
    "NUBLENSE": ["NUBLENSE", "Nublense"],
    "IQUIQUE": ["IQUIQUE", "Deportes Iquique"],
    "LA_CALERA": ["LA CALERA", "Union La Calera"],
}

# ---------------------------------------------------------------------------
# England Championship / League One / League Two
# (shared alias dict — teams move between these divisions)
# ---------------------------------------------------------------------------

ENG_LOWER_TEAM_ALIASES: dict[str, list[str]] = {
    "BURNLEY": ["BURNLEY", "Burnley FC"],
    "SHEFFIELD_WEDNESDAY": ["SHEFFIELD WEDNESDAY", "SHEFF WED", "Sheffield Wednesday"],
    "COVENTRY": ["COVENTRY", "Coventry City"],
    "NORWICH": ["NORWICH", "Norwich City"],
    "SUNDERLAND": ["SUNDERLAND", "Sunderland AFC"],
    "MIDDLESBROUGH": ["MIDDLESBROUGH", "Middlesbrough FC"],
    "WATFORD": ["WATFORD", "Watford FC"],
    "SWANSEA": ["SWANSEA", "Swansea City"],
    "BRISTOL_CITY": ["BRISTOL CITY", "Bristol City"],
    "BLACKBURN": ["BLACKBURN", "Blackburn Rovers"],
    "MILLWALL": ["MILLWALL", "Millwall FC"],
    "STOKE_CITY": ["STOKE CITY", "Stoke City"],
    "HULL_CITY": ["HULL CITY", "Hull City"],
    "PRESTON": ["PRESTON", "Preston North End"],
    "DERBY": ["DERBY", "Derby County"],
    "PORTSMOUTH": ["PORTSMOUTH", "Portsmouth FC"],
    "PLYMOUTH": ["PLYMOUTH", "Plymouth Argyle"],
    "OXFORD_UNITED": ["OXFORD UNITED", "Oxford United"],
    "WEST_BROM": ["WEST BROM", "West Bromwich Albion"],
    "QUEENS_PARK_RANGERS": ["QPR", "Queens Park Rangers"],
    "LUTON": ["LUTON", "Luton Town"],
    "CARDIFF": ["CARDIFF", "Cardiff City"],
    "SHEFFIELD_UNITED": ["SHEFFIELD UNITED", "Sheffield United"],
    "LEEDS": ["LEEDS", "Leeds United"],
}

# ---------------------------------------------------------------------------
# English Championship (league 40): canonical_team_id → name variations
# ---------------------------------------------------------------------------

ENG_CHAMPIONSHIP_TEAM_ALIASES: dict[str, list[str]] = {
    "BIRMINGHAM": ["BIRMINGHAM", "BIRMINGHAM CITY", "Birmingham City"],
    "BLACKBURN": ["BLACKBURN", "BLACKBURN ROVERS", "Blackburn Rovers"],
    "BRISTOL_CITY": ["BRISTOL CITY", "Bristol City"],
    "CHARLTON": ["CHARLTON", "CHARLTON ATHLETIC", "Charlton Athletic"],
    "COVENTRY": ["COVENTRY", "COVENTRY CITY", "Coventry City"],
    "DERBY": ["DERBY", "DERBY COUNTY", "Derby County"],
    "HULL_CITY": ["HULL CITY", "HULL", "Hull City"],
    "IPSWICH": ["IPSWICH", "IPSWICH TOWN", "Ipswich Town"],
    "LEEDS": ["LEEDS", "LEEDS UNITED", "LEEDS UTD", "Leeds United"],
    "LEICESTER": ["LEICESTER", "LEICESTER CITY", "Leicester City"],
    "MIDDLESBROUGH": ["MIDDLESBROUGH", "BORO", "Middlesbrough"],
    "MILLWALL": ["MILLWALL", "MILLWALL FC", "Millwall FC"],
    "NORWICH": ["NORWICH", "NORWICH CITY", "Norwich City"],
    "OXFORD_UNITED": ["OXFORD UNITED", "OXFORD UTD", "Oxford United"],
    "PORTSMOUTH": ["PORTSMOUTH", "POMPEY", "Portsmouth FC"],
    "PRESTON": ["PRESTON", "PRESTON NORTH END", "Preston North End", "PNE"],
    "QPR": ["QPR", "QUEENS PARK RANGERS", "Queens Park Rangers"],
    "SHEFFIELD_UNITED": [
        "SHEFFIELD UNITED",
        "SHEFF UTD",
        "SHEFFIELD UTD",
        "Sheffield United",
        "Sheffield Utd",
    ],
    "SHEFFIELD_WEDNESDAY": ["SHEFFIELD WEDNESDAY", "SHEFF WED", "Sheffield Wednesday"],
    "SOUTHAMPTON": ["SOUTHAMPTON", "SOUTHAMPTON FC", "Southampton FC"],
    "STOKE_CITY": ["STOKE CITY", "STOKE", "Stoke City"],
    "SWANSEA": ["SWANSEA", "SWANSEA CITY", "Swansea City"],
    "WATFORD": ["WATFORD", "WATFORD FC", "Watford FC"],
    "WEST_BROM": ["WEST BROM", "WEST BROMWICH ALBION", "West Bromwich Albion", "WBA"],
    "WREXHAM": ["WREXHAM", "WREXHAM AFC", "Wrexham AFC"],
}

# ---------------------------------------------------------------------------
# English League One (league 41): canonical_team_id → name variations
# ---------------------------------------------------------------------------

ENG_LEAGUE_ONE_TEAM_ALIASES: dict[str, list[str]] = {
    "AFC_WIMBLEDON": ["AFC WIMBLEDON", "AFC Wimbledon"],
    "BARNSLEY": ["BARNSLEY", "BARNSLEY FC", "Barnsley FC"],
    "BLACKPOOL": ["BLACKPOOL", "BLACKPOOL FC", "Blackpool FC"],
    "BOLTON": ["BOLTON", "BOLTON WANDERERS", "Bolton Wanderers"],
    "BRADFORD": ["BRADFORD", "BRADFORD CITY", "Bradford City"],
    "BURTON": ["BURTON", "BURTON ALBION", "Burton Albion"],
    "CARDIFF": ["CARDIFF", "CARDIFF CITY", "Cardiff City"],
    "DONCASTER": ["DONCASTER", "DONCASTER ROVERS", "Doncaster Rovers"],
    "EXETER": ["EXETER", "EXETER CITY", "Exeter City"],
    "HUDDERSFIELD": ["HUDDERSFIELD", "HUDDERSFIELD TOWN", "Huddersfield Town"],
    "LEYTON_ORIENT": ["LEYTON ORIENT", "Leyton Orient"],
    "LINCOLN": ["LINCOLN", "LINCOLN CITY", "Lincoln City"],
    "LUTON": ["LUTON", "LUTON TOWN", "Luton Town"],
    "MANSFIELD": ["MANSFIELD", "MANSFIELD TOWN", "Mansfield Town"],
    "NORTHAMPTON": ["NORTHAMPTON", "NORTHAMPTON TOWN", "Northampton Town"],
    "PETERBOROUGH": ["PETERBOROUGH", "PETERBOROUGH UNITED", "Peterborough United"],
    "PLYMOUTH": ["PLYMOUTH", "PLYMOUTH ARGYLE", "Plymouth Argyle"],
    "PORT_VALE": ["PORT VALE", "Port Vale"],
    "READING": ["READING", "READING FC", "Reading"],
    "ROTHERHAM": ["ROTHERHAM", "ROTHERHAM UNITED", "Rotherham United"],
    "STEVENAGE": ["STEVENAGE", "STEVENAGE FC", "Stevenage FC"],
    "STOCKPORT": ["STOCKPORT", "STOCKPORT COUNTY", "Stockport County"],
    "WIGAN": ["WIGAN", "WIGAN ATHLETIC", "Wigan Athletic"],
    "WYCOMBE": ["WYCOMBE", "WYCOMBE WANDERERS", "Wycombe Wanderers"],
}

# ---------------------------------------------------------------------------
# English League Two (league 42): canonical_team_id → name variations
# ---------------------------------------------------------------------------

ENG_LEAGUE_TWO_TEAM_ALIASES: dict[str, list[str]] = {
    "ACCRINGTON": ["ACCRINGTON", "ACCRINGTON STANLEY", "Accrington Stanley"],
    "BARNET": ["BARNET", "BARNET FC", "Barnet FC"],
    "BARROW": ["BARROW", "BARROW AFC", "Barrow AFC"],
    "BRISTOL_ROVERS": ["BRISTOL ROVERS", "Bristol Rovers"],
    "BROMLEY": ["BROMLEY", "BROMLEY FC", "Bromley FC"],
    "CAMBRIDGE_UNITED": ["CAMBRIDGE UNITED", "CAMBRIDGE UTD", "Cambridge United"],
    "CHELTENHAM": ["CHELTENHAM", "CHELTENHAM TOWN", "Cheltenham Town"],
    "CHESTERFIELD": ["CHESTERFIELD", "CHESTERFIELD FC", "Chesterfield FC"],
    "COLCHESTER": ["COLCHESTER", "COLCHESTER UNITED", "Colchester United"],
    "CRAWLEY": ["CRAWLEY", "CRAWLEY TOWN", "Crawley Town"],
    "CREWE": ["CREWE", "CREWE ALEXANDRA", "Crewe Alexandra"],
    "FLEETWOOD": ["FLEETWOOD", "FLEETWOOD TOWN", "Fleetwood Town"],
    "GILLINGHAM": ["GILLINGHAM", "GILLINGHAM FC", "Gillingham FC"],
    "GRIMSBY": ["GRIMSBY", "GRIMSBY TOWN", "Grimsby Town"],
    "HARROGATE": ["HARROGATE", "HARROGATE TOWN", "Harrogate Town"],
    "MK_DONS": ["MK DONS", "MILTON KEYNES DONS", "Milton Keynes Dons"],
    "NEWPORT": ["NEWPORT", "NEWPORT COUNTY", "Newport County"],
    "NOTTS_COUNTY": ["NOTTS COUNTY", "Notts County"],
    "OLDHAM": ["OLDHAM", "OLDHAM ATHLETIC", "Oldham Athletic"],
    "SALFORD": ["SALFORD", "SALFORD CITY", "Salford City"],
    "SHREWSBURY": ["SHREWSBURY", "SHREWSBURY TOWN", "Shrewsbury Town"],
    "SWINDON": ["SWINDON", "SWINDON TOWN", "Swindon Town"],
    "TRANMERE": ["TRANMERE", "TRANMERE ROVERS", "Tranmere Rovers"],
    "WALSALL": ["WALSALL", "WALSALL FC", "Walsall FC"],
}

# ---------------------------------------------------------------------------
# Bundesliga 2 / 3. Liga: additional German lower-tier teams
# ---------------------------------------------------------------------------

BUNDESLIGA_2_TEAM_ALIASES: dict[str, list[str]] = {
    "KAISERSLAUTERN": ["KAISERSLAUTERN", "1. FC Kaiserslautern"],
    "KARLSRUHE": ["KARLSRUHE", "Karlsruher SC"],
    "HAMBURG": ["HAMBURG", "Hamburger SV"],
    "HANNOVER": ["HANNOVER", "Hannover 96"],
    "NURNBERG": ["NURNBERG", "1. FC Nürnberg"],
    "DARMSTADT": ["DARMSTADT", "SV Darmstadt 98"],
    "GREUTHER_FURTH": ["GREUTHER FURTH", "SpVgg Greuther Fürth"],
    "PADERBORN": ["PADERBORN", "SC Paderborn 07"],
    "SCHALKE": ["SCHALKE", "FC Schalke 04"],
    "FORTUNA_DUSSELDORF": ["FORTUNA DUSSELDORF", "Fortuna Düsseldorf"],
    "BRAUNSCHWEIG": ["BRAUNSCHWEIG", "Eintracht Braunschweig"],
    "ELVERSBERG": ["ELVERSBERG", "SV Elversberg"],
    "PREUSSEN_MUNSTER": ["PREUSSEN MUNSTER", "SC Preußen Münster"],
    "MAGDEBURG": ["MAGDEBURG", "1. FC Magdeburg"],
    "ULMER": ["ULMER", "SSV Ulm 1846"],
    "REGENSBURG": ["REGENSBURG", "SSV Jahn Regensburg"],
}

# ---------------------------------------------------------------------------
# 3. Liga (Germany, league 80): canonical_team_id → name variations
# ---------------------------------------------------------------------------

LIGA_3_TEAM_ALIASES: dict[str, list[str]] = {
    "AACHEN": ["AACHEN", "ALEMANNIA AACHEN", "Alemannia Aachen"],
    "ARMINIA_BIELEFELD": ["ARMINIA BIELEFELD", "BIELEFELD", "Arminia Bielefeld"],
    "COTTBUS": ["COTTBUS", "ENERGIE COTTBUS", "Energie Cottbus"],
    "DRESDEN": ["DRESDEN", "DYNAMO DRESDEN", "Dynamo Dresden"],
    "DUISBURG": ["DUISBURG", "MSV DUISBURG", "MSV Duisburg"],
    "ERZGEBIRGE_AUE": ["ERZGEBIRGE AUE", "AUE", "Erzgebirge Aue"],
    "HANSA_ROSTOCK": ["HANSA ROSTOCK", "ROSTOCK", "Hansa Rostock"],
    "INGOLSTADT": ["INGOLSTADT", "FC INGOLSTADT 04", "FC Ingolstadt 04"],
    "MANNHEIM": ["MANNHEIM", "WALDHOF MANNHEIM", "Waldhof Mannheim", "SV Waldhof Mannheim"],
    "MUNSTER": ["MUNSTER", "SC PREUSSEN MUNSTER", "SC Preußen Münster", "Preußen Münster"],
    "OSNABRUECK": ["OSNABRUECK", "VFL OSNABRUECK", "VfL Osnabrück", "Osnabrück"],
    "REGENSBURG": ["REGENSBURG", "SSV JAHN REGENSBURG", "SSV Jahn Regensburg"],
    "ROT_WEISS_ESSEN": ["ROT-WEISS ESSEN", "ROT WEISS ESSEN", "Rot-Weiss Essen"],
    "SAARBRUECKEN": ["SAARBRUECKEN", "1. FC SAARBRUECKEN", "1. FC Saarbrücken", "FC Saarbrücken"],
    "SANDHAUSEN": ["SANDHAUSEN", "SV SANDHAUSEN", "SV Sandhausen"],
    "UNTERHACHING": ["UNTERHACHING", "SPVGG UNTERHACHING", "SpVgg Unterhaching"],
    "VERL": ["VERL", "SC VERL", "SC Verl"],
    "VIKTORIA_KOELN": ["VIKTORIA KOELN", "VIKTORIA KOLN", "Viktoria Köln", "Viktoria Koln"],
    "WEHEN_WIESBADEN": ["WEHEN WIESBADEN", "SV WEHEN WIESBADEN", "SV Wehen Wiesbaden"],
    "WUERZBURGER_KICKERS": ["WUERZBURGER KICKERS", "Würzburger Kickers", "Wurzburger Kickers"],
}

# ---------------------------------------------------------------------------
# Segunda Division (Spain): additional Spanish second-tier teams
# ---------------------------------------------------------------------------

SEGUNDA_DIVISION_TEAM_ALIASES: dict[str, list[str]] = {
    "REAL_SOCIEDAD_B": ["REAL SOCIEDAD B", "REAL SOCIEDAD II", "Real Sociedad B", "Real Sociedad II"],
    "REAL_VALLADOLID": ["REAL VALLADOLID", "VALLADOLID", "Real Valladolid CF", "Valladolid"],
    "BURGOS": ["BURGOS", "BURGOS CF", "Burgos CF", "Burgos"],
    "MIRANDES": ["MIRANDES", "CD MIRANDES", "CD Mirandés", "Mirandes"],
    "SPORTING_GIJON": ["SPORTING GIJON", "Sporting Gijón", "Sporting Gijon"],
    "CORDOBA": ["CORDOBA", "Córdoba", "Cordoba"],
    "EIBAR": ["EIBAR", "SD Eibar"],
    "HUESCA": ["HUESCA", "SD Huesca"],
    "RACING_SANTANDER": ["RACING SANTANDER", "Racing Santander"],
    "ELCHE": ["ELCHE", "Elche CF"],
    "TENERIFE": ["TENERIFE", "CD Tenerife"],
    "ZARAGOZA": ["ZARAGOZA", "Real Zaragoza"],
    "LEVANTE": ["LEVANTE", "Levante UD"],
    "OVIEDO": ["OVIEDO", "Real Oviedo"],
    "ALBACETE": ["ALBACETE", "Albacete Balompie"],
    "CADIZ": ["CADIZ", "Cadiz CF"],
    "GRANADA": ["GRANADA", "Granada CF"],
}

# ---------------------------------------------------------------------------
# Serie B (Italy): additional Italian second-tier teams
# ---------------------------------------------------------------------------

SERIE_B_TEAM_ALIASES: dict[str, list[str]] = {
    "SUDTIROL": ["SUDTIROL", "Südtirol", "Sudtirol", "FC Sudtirol"],
    "BARI": ["BARI", "SSC Bari"],
    "BRESCIA": ["BRESCIA", "Brescia Calcio"],
    "CATANZARO": ["CATANZARO", "US Catanzaro"],
    "COSENZA": ["COSENZA", "Cosenza Calcio"],
    "CREMONESE": ["CREMONESE", "US Cremonese"],
    "MODENA": ["MODENA", "Modena FC"],
    "PALERMO": ["PALERMO", "US Palermo"],
    "PISA": ["PISA", "AC Pisa"],
    "REGGIANA": ["REGGIANA", "AC Reggiana"],
    "SAMPDORIA": ["SAMPDORIA", "UC Sampdoria"],
    "SPEZIA": ["SPEZIA", "Spezia Calcio"],
    "TERNANA": ["TERNANA", "Ternana Calcio"],
}

# ---------------------------------------------------------------------------
# Ligue 2 (France): additional French second-tier teams
# ---------------------------------------------------------------------------

LIGUE_2_TEAM_ALIASES: dict[str, list[str]] = {
    "METZ": ["METZ", "FC Metz"],
    "CAEN": ["CAEN", "SM Caen"],
    "LORIENT": ["LORIENT", "FC Lorient"],
    "GUINGAMP": ["GUINGAMP", "EA Guingamp"],
    "AMIENS": ["AMIENS", "Amiens SC"],
    "AJACCIO": ["AJACCIO", "AC Ajaccio"],
    "GRENOBLE": ["GRENOBLE", "Grenoble Foot"],
    "BORDEAUX": ["BORDEAUX", "Girondins de Bordeaux"],
    "LAVAL": ["LAVAL", "Stade Lavallois"],
    "RODEZ": ["RODEZ", "Rodez AF"],
    "DUNKERQUE": ["DUNKERQUE", "USL Dunkerque"],
    "PAU": ["PAU", "Pau FC"],
    "PARIS_FC": ["PARIS FC", "Paris FC"],
    "RED_STAR": ["RED STAR", "Red Star FC"],
    "BASTIA": ["BASTIA", "SC Bastia"],
    "NANCY": ["NANCY", "AS Nancy", "AS Nancy-Lorraine", "Nancy-Lorraine"],
}

# ---------------------------------------------------------------------------
# Eerste Divisie (Netherlands 2nd tier — Telstar etc.)
# ---------------------------------------------------------------------------

EERSTE_DIVISIE_TEAM_ALIASES: dict[str, list[str]] = {
    "TELSTAR": ["TELSTAR", "SC TELSTAR", "SC Telstar", "Telstar"],
    "JONG_AJAX": ["JONG AJAX", "Jong Ajax"],
    "JONG_PSV": ["JONG PSV", "Jong PSV"],
    "JONG_AZ": ["JONG AZ", "Jong AZ"],
    "JONG_UTRECHT": ["JONG UTRECHT", "Jong FC Utrecht"],
    "FC_EINDHOVEN": ["FC EINDHOVEN", "FC Eindhoven"],
    "ADO_DEN_HAAG": ["ADO DEN HAAG", "ADO Den Haag"],
    "DEN_BOSCH": ["DEN BOSCH", "FC Den Bosch"],
    "RODA": ["RODA", "Roda JC Kerkrade"],
    "NAC_BREDA": ["NAC BREDA", "NAC Breda"],
    "MVV": ["MVV", "MVV Maastricht"],
    "CAMBUUR": ["CAMBUUR", "SC Cambuur"],
    "EMMEN": ["EMMEN", "FC Emmen"],
    "EXCELSIOR": ["EXCELSIOR", "SBV Excelsior"],
    "DORDRECHT": ["DORDRECHT", "FC Dordrecht"],
    "ROTTMEERENBURG": ["ROTTMEERENBURG", "TOP Oss"],
}


# ---------------------------------------------------------------------------
# Collect ALL league alias dicts for universal resolution
# ---------------------------------------------------------------------------

ALL_LEAGUE_ALIASES: list[dict[str, list[str]]] = [
    EPL_TEAM_ALIASES,
    BUNDESLIGA_TEAM_ALIASES,
    LA_LIGA_TEAM_ALIASES,
    SERIE_A_TEAM_ALIASES,
    LIGUE_1_TEAM_ALIASES,
    EREDIVISIE_TEAM_ALIASES,
    PRIMEIRA_LIGA_TEAM_ALIASES,
    JUPILER_PRO_TEAM_ALIASES,
    DANISH_SUPERLIGA_TEAM_ALIASES,
    MLS_TEAM_ALIASES,
    AUSTRIAN_BUNDESLIGA_TEAM_ALIASES,
    ELITESERIEN_TEAM_ALIASES,
    SWISS_SUPER_LEAGUE_TEAM_ALIASES,
    SCOTTISH_PREMIERSHIP_TEAM_ALIASES,
    A_LEAGUE_TEAM_ALIASES,
    LIGA_MX_TEAM_ALIASES,
    ARGENTINA_PRIMERA_TEAM_ALIASES,
    BRASILEIRAO_TEAM_ALIASES,
    GREEK_SUPER_LEAGUE_TEAM_ALIASES,
    EKSTRAKLASA_TEAM_ALIASES,
    SUPER_LIG_TEAM_ALIASES,
    ALLSVENSKAN_TEAM_ALIASES,
    J1_LEAGUE_TEAM_ALIASES,
    K_LEAGUE_1_TEAM_ALIASES,
    CHILE_PRIMERA_TEAM_ALIASES,
    ENG_LOWER_TEAM_ALIASES,
    ENG_CHAMPIONSHIP_TEAM_ALIASES,
    ENG_LEAGUE_ONE_TEAM_ALIASES,
    ENG_LEAGUE_TWO_TEAM_ALIASES,
    BUNDESLIGA_2_TEAM_ALIASES,
    LIGA_3_TEAM_ALIASES,
    SEGUNDA_DIVISION_TEAM_ALIASES,
    SERIE_B_TEAM_ALIASES,
    LIGUE_2_TEAM_ALIASES,
    EERSTE_DIVISIE_TEAM_ALIASES,
]

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

# Universal reverse lookup: raw name (upper, accent-stripped) → canonical_team_id
_UNIVERSAL_REVERSE: dict[str, str] = {}


def _strip_accents(text: str) -> str:
    """Strip diacritics: e.g. ü → u, é → e, ñ → n."""
    nfkd = unicodedata.normalize("NFKD", text)
    return nfkd.encode("ascii", "ignore").decode("ascii")


def _normalize_key(name: str) -> str:
    """Normalize a team name for reverse lookup: strip accents, uppercase, collapse whitespace."""
    stripped = _strip_accents(name)
    # Replace common separators with space
    cleaned = re.sub(r"[\-/&.]+", " ", stripped)
    # Remove non-alphanumeric (keep spaces)
    cleaned = re.sub(r"[^A-Za-z0-9 ]", "", cleaned)
    # Collapse whitespace
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned.upper()


for _alias_dict in ALL_LEAGUE_ALIASES:
    for _canonical, _variations in _alias_dict.items():
        for _var in _variations:
            _key = _normalize_key(_var)
            # First mapping wins — don't overwrite
            if _key not in _UNIVERSAL_REVERSE:
                _UNIVERSAL_REVERSE[_key] = _canonical

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
    "SC Preußen Münster": "PREUSSEN_MUNSTER",
    "Preußen Münster": "PREUSSEN_MUNSTER",
}

API_FOOTBALL_TO_CANONICAL_LA_LIGA: dict[str, str] = {
    "Athletic Club": "ATHLETIC_CLUB",
    "Athletic Bilbao": "ATHLETIC_CLUB",
    "Atletico Madrid": "ATLETICO_MADRID",
    "Atlético Madrid": "ATLETICO_MADRID",
    "Atletico de Madrid": "ATLETICO_MADRID",
    "Barcelona": "BARCELONA",
    "FC Barcelona": "BARCELONA",
    "Real Madrid": "REAL_MADRID",
    "Real Sociedad": "REAL_SOCIEDAD",
    "Real Sociedad B": "REAL_SOCIEDAD_B",
    "Real Sociedad II": "REAL_SOCIEDAD_B",
    "Real Betis": "REAL_BETIS",
    "Real Valladolid CF": "REAL_VALLADOLID",
    "Valladolid": "REAL_VALLADOLID",
    "Sevilla": "SEVILLA",
    "Sevilla FC": "SEVILLA",
    "Villarreal": "VILLARREAL",
    "Celta Vigo": "CELTA_VIGO",
    "Getafe": "GETAFE",
    "Valencia": "VALENCIA",
    "Mallorca": "MALLORCA",
    "RCD Mallorca": "MALLORCA",
    "Osasuna": "OSASUNA",
    "CA Osasuna": "OSASUNA",
    "Rayo Vallecano": "RAYO_VALLECANO",
    "Alaves": "ALAVES",
    "Deportivo Alaves": "ALAVES",
    "Leganes": "LEGANES",
    "CD Leganes": "LEGANES",
    "Espanyol": "ESPANYOL",
    "RCD Espanyol": "ESPANYOL",
    "Las Palmas": "LAS_PALMAS",
    "UD Las Palmas": "LAS_PALMAS",
    "Girona": "GIRONA",
    "Girona FC": "GIRONA",
    "Burgos CF": "BURGOS",
    "Burgos": "BURGOS",
    "CD Mirandés": "MIRANDES",
    "Mirandes": "MIRANDES",
    "Sporting Gijón": "SPORTING_GIJON",
    "Sporting Gijon": "SPORTING_GIJON",
    "Córdoba": "CORDOBA",
    "Cordoba": "CORDOBA",
    # Segunda additional
    "Eibar": "EIBAR",
    "SD Eibar": "EIBAR",
    "Huesca": "HUESCA",
    "SD Huesca": "HUESCA",
    "Racing Santander": "RACING_SANTANDER",
    "Elche": "ELCHE",
    "Elche CF": "ELCHE",
    "Tenerife": "TENERIFE",
    "CD Tenerife": "TENERIFE",
    "Zaragoza": "ZARAGOZA",
    "Real Zaragoza": "ZARAGOZA",
    "Levante": "LEVANTE",
    "Levante UD": "LEVANTE",
    "Oviedo": "OVIEDO",
    "Real Oviedo": "OVIEDO",
    "Cadiz": "CADIZ",
    "Cadiz CF": "CADIZ",
    "Granada": "GRANADA",
    "Granada CF": "GRANADA",
}

API_FOOTBALL_TO_CANONICAL_SERIE_A: dict[str, str] = {
    "Atalanta": "ATALANTA",
    "Atalanta BC": "ATALANTA",
    "Inter": "INTER_MILAN",
    "Inter Milan": "INTER_MILAN",
    "FC Internazionale": "INTER_MILAN",
    "Juventus": "JUVENTUS",
    "AC Milan": "AC_MILAN",
    "Milan": "AC_MILAN",
    "Napoli": "NAPOLI",
    "SSC Napoli": "NAPOLI",
    "AS Roma": "ROMA",
    "Roma": "ROMA",
    "Lazio": "LAZIO",
    "SS Lazio": "LAZIO",
    "Fiorentina": "FIORENTINA",
    "ACF Fiorentina": "FIORENTINA",
    "Torino": "TORINO",
    "Bologna": "BOLOGNA",
    "Bologna FC": "BOLOGNA",
    "Udinese": "UDINESE",
    "Genoa": "GENOA",
    "Cagliari": "CAGLIARI",
    "Empoli": "EMPOLI",
    "Lecce": "LECCE",
    "US Lecce": "LECCE",
    "Monza": "MONZA",
    "AC Monza": "MONZA",
    "Hellas Verona": "VERONA",
    "Verona": "VERONA",
    "Como": "COMO",
    "Como 1907": "COMO",
    "Parma": "PARMA",
    "Venezia": "VENEZIA",
    "Salernitana": "SALERNITANA",
    "Sassuolo": "SASSUOLO",
    "Frosinone": "FROSINONE",
    # Serie B
    "Südtirol": "SUDTIROL",
    "Sudtirol": "SUDTIROL",
    "FC Sudtirol": "SUDTIROL",
    "Bari": "BARI",
    "SSC Bari": "BARI",
    "Brescia": "BRESCIA",
    "Palermo": "PALERMO",
    "US Palermo": "PALERMO",
    "Sampdoria": "SAMPDORIA",
    "UC Sampdoria": "SAMPDORIA",
    "Spezia": "SPEZIA",
    "Cremonese": "CREMONESE",
    "US Cremonese": "CREMONESE",
}

API_FOOTBALL_TO_CANONICAL_LIGUE_1: dict[str, str] = {
    "Paris Saint Germain": "PSG",
    "Paris Saint-Germain": "PSG",
    "PSG": "PSG",
    "AS Monaco": "MONACO",
    "Monaco": "MONACO",
    "Olympique Marseille": "MARSEILLE",
    "Marseille": "MARSEILLE",
    "Olympique Lyonnais": "LYON",
    "Lyon": "LYON",
    "Lille": "LILLE",
    "Lille OSC": "LILLE",
    "OGC Nice": "NICE",
    "Nice": "NICE",
    "RC Lens": "LENS",
    "Lens": "LENS",
    "Stade Rennais": "RENNES",
    "Rennes": "RENNES",
    "RC Strasbourg": "STRASBOURG",
    "Strasbourg": "STRASBOURG",
    "FC Nantes": "NANTES",
    "Nantes": "NANTES",
    "Montpellier HSC": "MONTPELLIER",
    "Montpellier": "MONTPELLIER",
    "Stade Brestois": "BREST",
    "Brest": "BREST",
    "Toulouse FC": "TOULOUSE",
    "Toulouse": "TOULOUSE",
    "Stade de Reims": "REIMS",
    "Reims": "REIMS",
    "AJ Auxerre": "AUXERRE",
    "Auxerre": "AUXERRE",
    "Angers SCO": "ANGERS",
    "Angers": "ANGERS",
    "Le Havre": "LE_HAVRE",
    "Le Havre AC": "LE_HAVRE",
    "AS Saint-Etienne": "SAINT_ETIENNE",
    "Saint-Etienne": "SAINT_ETIENNE",
    # Ligue 2
    "FC Metz": "METZ",
    "Metz": "METZ",
    "FC Lorient": "LORIENT",
    "Lorient": "LORIENT",
    "SM Caen": "CAEN",
    "Caen": "CAEN",
    "Girondins de Bordeaux": "BORDEAUX",
    "Bordeaux": "BORDEAUX",
}

API_FOOTBALL_TO_CANONICAL_EREDIVISIE: dict[str, str] = {
    "Ajax": "AJAX",
    "AFC Ajax": "AJAX",
    "PSV Eindhoven": "PSV",
    "PSV": "PSV",
    "Feyenoord": "FEYENOORD",
    "AZ Alkmaar": "AZ",
    "AZ": "AZ",
    "FC Twente": "TWENTE",
    "FC Utrecht": "UTRECHT",
    "Utrecht": "UTRECHT",
    "Vitesse": "VITESSE",
    "SC Heerenveen": "HEERENVEEN",
    "FC Groningen": "GRONINGEN",
    "Sparta Rotterdam": "SPARTA_ROTTERDAM",
    "NEC Nijmegen": "NEC",
    "NEC": "NEC",
    "Go Ahead Eagles": "GO_AHEAD_EAGLES",
    "Heracles Almelo": "HERACLES",
    "Fortuna Sittard": "FORTUNA_SITTARD",
    "Almere City FC": "ALMERE_CITY",
    "RKC Waalwijk": "WAALWIJK",
    "FC Volendam": "VOLENDAM",
    "SC Telstar": "TELSTAR",
    "Telstar": "TELSTAR",
}

API_FOOTBALL_TO_CANONICAL_PRIMEIRA_LIGA: dict[str, str] = {
    "SL Benfica": "BENFICA",
    "Benfica": "BENFICA",
    "FC Porto": "PORTO",
    "Porto": "PORTO",
    "Sporting CP": "SPORTING_CP",
    "Sporting Lisbon": "SPORTING_CP",
    "SC Braga": "BRAGA",
    "Braga": "BRAGA",
    "Vitoria de Guimaraes": "VITORIA_GUIMARAES",
    "Rio Ave FC": "RIO_AVE",
    "Rio Ave": "RIO_AVE",
    "Gil Vicente": "GIL_VICENTE",
    "Boavista": "BOAVISTA",
    "FC Famalicao": "FAMALICAO",
    "Famalicao": "FAMALICAO",
    "Casa Pia AC": "CASA_PIA",
    "Casa Pia": "CASA_PIA",
    "FC Arouca": "AROUCA",
    "Arouca": "AROUCA",
    "Moreirense FC": "MOREIRENSE",
    "Moreirense": "MOREIRENSE",
    "Estoril Praia": "ESTORIL",
    "Estoril": "ESTORIL",
    "Estrela da Amadora": "ESTRELA_AMADORA",
}

API_FOOTBALL_TO_CANONICAL_JUPILER_PRO: dict[str, str] = {
    "Club Brugge": "CLUB_BRUGGE",
    "Club Brugge KV": "CLUB_BRUGGE",
    "RSC Anderlecht": "ANDERLECHT",
    "Anderlecht": "ANDERLECHT",
    "KRC Genk": "GENK",
    "Genk": "GENK",
    "KAA Gent": "GENT",
    "Gent": "GENT",
    "Royal Antwerp": "ANTWERP",
    "Antwerp FC": "ANTWERP",
    "Sint Truiden": "SINT_TRUIDEN",
    "St. Truiden": "SINT_TRUIDEN",
    "STVV": "SINT_TRUIDEN",
    "Union Saint-Gilloise": "UNION_SG",
    "Union St. Gilloise": "UNION_SG",
    "Westerlo": "WESTERLO",
    "KVC Westerlo": "WESTERLO",
    "Cercle Brugge KSV": "CERCLE_BRUGGE",
    "Cercle Brugge": "CERCLE_BRUGGE",
    "SV Zulte-Waregem": "ZULTE_WAREGEM",
    "Zulte Waregem": "ZULTE_WAREGEM",
    "Standard Liege": "STANDARD_LIEGE",
    "Standard de Liege": "STANDARD_LIEGE",
    "KV Mechelen": "MECHELEN",
    "Sporting Charleroi": "CHARLEROI",
    "Charleroi": "CHARLEROI",
    "OH Leuven": "LEUVEN",
    "KV Kortrijk": "KORTRIJK",
}

API_FOOTBALL_TO_CANONICAL_DANISH_SUPERLIGA: dict[str, str] = {
    "FC Copenhagen": "COPENHAGEN",
    "FC Midtjylland": "MIDTJYLLAND",
    "Brondby IF": "BRONDBY",
    "Brondby": "BRONDBY",
    "FC Nordsjaelland": "NORDSJAELLAND",
    "Silkeborg IF": "SILKEBORG",
    "Silkeborg": "SILKEBORG",
    "AGF Aarhus": "AARHUS",
    "AGF": "AARHUS",
    "Aarhus": "AARHUS",
    "Viborg FF": "VIBORG",
    "Viborg": "VIBORG",
    "AaB": "AALBORG",
    "Aalborg BK": "AALBORG",
    "Randers FC": "RANDERS",
    "Lyngby BK": "LYNGBY",
    "Hvidovre IF": "HVIDOVRE",
    "Vejle BK": "VEJLE",
}

API_FOOTBALL_TO_CANONICAL_MLS: dict[str, str] = {
    "Atlanta United FC": "ATLANTA_UNITED",
    "Atlanta United": "ATLANTA_UNITED",
    "Austin FC": "AUSTIN",
    "Austin": "AUSTIN",
    "Charlotte FC": "CHARLOTTE",
    "Chicago Fire FC": "CHICAGO_FIRE",
    "FC Cincinnati": "CINCINNATI",
    "Colorado Rapids": "COLORADO_RAPIDS",
    "Columbus Crew": "COLUMBUS_CREW",
    "D.C. United": "DC_UNITED",
    "DC United": "DC_UNITED",
    "FC Dallas": "DALLAS",
    "Houston Dynamo FC": "HOUSTON_DYNAMO",
    "Inter Miami CF": "INTER_MIAMI",
    "Inter Miami": "INTER_MIAMI",
    "LA Galaxy": "LA_GALAXY",
    "Los Angeles Galaxy": "LA_GALAXY",
    "Los Angeles FC": "LAFC",
    "LAFC": "LAFC",
    "Minnesota United FC": "MINNESOTA_UNITED",
    "CF Montréal": "MONTREAL",
    "CF Montreal": "MONTREAL",
    "Nashville SC": "NASHVILLE",
    "New England Revolution": "NEW_ENGLAND_REVOLUTION",
    "New York Red Bulls": "NEW_YORK_RED_BULLS",
    "New York City FC": "NYCFC",
    "Orlando City SC": "ORLANDO_CITY",
    "Philadelphia Union": "PHILADELPHIA_UNION",
    "Portland Timbers": "PORTLAND_TIMBERS",
    "Real Salt Lake": "REAL_SALT_LAKE",
    "San Diego FC": "SAN_DIEGO",
    "San Diego": "SAN_DIEGO",
    "San Jose Earthquakes": "SAN_JOSE_EARTHQUAKES",
    "Seattle Sounders FC": "SEATTLE_SOUNDERS",
    "Seattle Sounders": "SEATTLE_SOUNDERS",
    "Sporting Kansas City": "SPORTING_KC",
    "St. Louis City SC": "ST_LOUIS_CITY",
    "St. Louis City": "ST_LOUIS_CITY",
    "Toronto FC": "TORONTO",
    "Vancouver Whitecaps FC": "VANCOUVER_WHITECAPS",
    "Vancouver Whitecaps": "VANCOUVER_WHITECAPS",
}

API_FOOTBALL_TO_CANONICAL_AUSTRIAN_BUNDESLIGA: dict[str, str] = {
    "Red Bull Salzburg": "RB_SALZBURG",
    "FC Salzburg": "RB_SALZBURG",
    "SK Sturm Graz": "STURM_GRAZ",
    "Austria Wien": "AUSTRIA_WIEN",
    "Austria Vienna": "AUSTRIA_WIEN",
    "Rapid Wien": "RAPID_WIEN",
    "Rapid Vienna": "RAPID_WIEN",
    "Wolfsberger AC": "WOLFSBERGER",
    "Hartberg": "HARTBERG",
    "TSV Hartberg": "HARTBERG",
    "LASK": "LASK",
    "Lask Linz": "LASK",
    "SCR Altach": "ALTACH",
    "SK Austria Klagenfurt": "AUSTRIA_KLAGENFURT",
    "FC Blau-Weiss Linz": "BLAU_WEISS_LINZ",
    "Grazer AK 1902": "GRAZER_AK",
    "GAK": "GRAZER_AK",
}

API_FOOTBALL_TO_CANONICAL_ELITESERIEN: dict[str, str] = {
    "FK Bodo/Glimt": "BODO_GLIMT",
    "Bodo/Glimt": "BODO_GLIMT",
    "Molde FK": "MOLDE",
    "Rosenborg BK": "ROSENBORG",
    "SK Brann": "BRANN",
    "Brann": "BRANN",
    "Viking FK": "VIKING",
    "Fredrikstad FK": "FREDRIKSTAD",
    "Fredrikstad": "FREDRIKSTAD",
    "KFUM": "KFUM_OSLO",
    "KFUM Oslo": "KFUM_OSLO",
    "Sarpsborg FK": "SARPSBORG",
    "Sarpsborg 08 FF": "SARPSBORG",
    "Tromso IL": "TROMSO",
    "Lillestrom SK": "LILLESTROM",
    "FK Haugesund": "HAUGESUND",
    "Sandefjord Fotball": "SANDEFJORD",
    "Stromsgodset IF": "STROMSGODSET",
    "Kristiansund BK": "KRISTIANSUND",
    "HamKam": "HAMKAM",
    "Odds BK": "ODD",
}

API_FOOTBALL_TO_CANONICAL_SWISS_SUPER_LEAGUE: dict[str, str] = {
    "BSC Young Boys": "YOUNG_BOYS",
    "Young Boys": "YOUNG_BOYS",
    "FC Basel": "FC_BASEL",
    "FC Basel 1893": "FC_BASEL",
    "FC Zurich": "FC_ZURICH",
    "Servette FC": "SERVETTE",
    "FC Lugano": "LUGANO",
    "FC St. Gallen": "ST_GALLEN",
    "FC Lausanne-Sport": "FC_LAUSANNE",
    "Lausanne-Sport": "FC_LAUSANNE",
    "Grasshopper Club Zurich": "GRASSHOPPERS",
    "FC Luzern": "LUZERN",
    "FC Winterthur": "WINTERTHUR",
    "FC Sion": "SION",
    "Yverdon-Sport FC": "YVERDON",
}

API_FOOTBALL_TO_CANONICAL_SCOTTISH_PREMIERSHIP: dict[str, str] = {
    "Celtic": "CELTIC",
    "Celtic FC": "CELTIC",
    "Rangers": "RANGERS",
    "Rangers FC": "RANGERS",
    "Aberdeen": "ABERDEEN",
    "Hearts": "HEARTS",
    "Heart of Midlothian": "HEARTS",
    "Hibernian": "HIBERNIAN",
    "Dundee": "DUNDEE",
    "Dundee United": "DUNDEE_UNITED",
    "Dundee Utd": "DUNDEE_UNITED",
    "Kilmarnock": "KILMARNOCK",
    "Motherwell": "MOTHERWELL",
    "St. Mirren": "ST_MIRREN",
    "St Mirren": "ST_MIRREN",
    "St. Johnstone": "ST_JOHNSTONE",
    "St Johnstone": "ST_JOHNSTONE",
    "Ross County": "ROSS_COUNTY",
}

API_FOOTBALL_TO_CANONICAL_A_LEAGUE: dict[str, str] = {
    "Melbourne Victory": "MELBOURNE_VICTORY",
    "Melbourne City FC": "MELBOURNE_CITY",
    "Sydney FC": "SYDNEY_FC",
    "Sydney": "SYDNEY_FC",
    "Western Sydney Wanderers": "WESTERN_SYDNEY",
    "Central Coast Mariners": "CENTRAL_COAST_MARINERS",
    "Newcastle Jets FC": "NEWCASTLE_JETS",
    "Newcastle Jets": "NEWCASTLE_JETS",
    "Perth Glory": "PERTH_GLORY",
    "Adelaide United": "ADELAIDE_UNITED",
    "Wellington Phoenix": "WELLINGTON_PHOENIX",
    "Brisbane Roar": "BRISBANE_ROAR",
    "Macarthur FC": "MACARTHUR",
    "Western United FC": "WESTERN_UNITED",
    "Auckland FC": "AUCKLAND",
}

API_FOOTBALL_TO_CANONICAL_LIGA_MX: dict[str, str] = {
    "América": "CLUB_AMERICA",
    "Club America": "CLUB_AMERICA",
    "America": "CLUB_AMERICA",
    "Guadalajara": "GUADALAJARA",
    "Guadalajara Chivas": "GUADALAJARA",
    "CD Guadalajara": "GUADALAJARA",
    "Cruz Azul": "CRUZ_AZUL",
    "Pumas": "PUMAS_UNAM",
    "U.N.A.M. - Pumas": "PUMAS_UNAM",
    "UNAM Pumas": "PUMAS_UNAM",
    "Tigres UANL": "TIGRES",
    "Tigres": "TIGRES",
    "CF Monterrey": "MONTERREY",
    "Monterrey": "MONTERREY",
    "Santos Laguna": "SANTOS_LAGUNA",
    "Club Leon": "LEON",
    "Leon": "LEON",
    "Deportivo Toluca": "TOLUCA",
    "Toluca": "TOLUCA",
    "CF Pachuca": "PACHUCA",
    "Pachuca": "PACHUCA",
    "Atlas FC": "ATLAS",
    "Atlas": "ATLAS",
    "Club Queretaro": "QUERETARO",
    "Queretaro": "QUERETARO",
    "Club Puebla": "PUEBLA",
    "Puebla": "PUEBLA",
    "Club Necaxa": "NECAXA",
    "Necaxa": "NECAXA",
    "Mazatlan FC": "MAZATLAN",
    "Club Tijuana": "TIJUANA",
    "Tijuana": "TIJUANA",
    "Atletico San Luis": "SAN_LUIS",
    "FC Juarez": "JUAREZ",
}

API_FOOTBALL_TO_CANONICAL_ARGENTINA_PRIMERA: dict[str, str] = {
    "Boca Juniors": "BOCA_JUNIORS",
    "River Plate": "RIVER_PLATE",
    "Racing Club": "RACING_CLUB",
    "CA Independiente": "INDEPENDIENTE",
    "Independiente": "INDEPENDIENTE",
    "San Lorenzo": "SAN_LORENZO",
    "Velez Sarsfield": "VELEZ_SARSFIELD",
    "Estudiantes LP": "ESTUDIANTES",
    "Estudiantes": "ESTUDIANTES",
    "Lanus": "LANUS",
    "Talleres Cordoba": "TALLERES",
    "Talleres": "TALLERES",
    "Belgrano de Cordoba": "BELGRANO",
    "Belgrano Cordoba": "BELGRANO",
    "Belgrano": "BELGRANO",
    "Sarmiento de Junin": "SARMIENTO",
    "Sarmiento Junin": "SARMIENTO",
    "Sarmiento": "SARMIENTO",
    "Aldosivi Mar del Plata": "ALDOSIVI",
    "Aldosivi": "ALDOSIVI",
    "Instituto de Córdoba": "INSTITUTO",
    "Instituto Cordoba": "INSTITUTO",
    "Instituto": "INSTITUTO",
    "Defensa y Justicia": "DEFENSA_JUSTICIA",
    "Argentinos Juniors": "ARGENTINOS_JUNIORS",
    "CA Banfield": "BANFIELD",
    "Banfield": "BANFIELD",
    "Central Cordoba SE": "CENTRAL_CORDOBA",
    "Colon Santa Fe": "COLON",
    "Godoy Cruz": "GODOY_CRUZ",
    "CA Huracan": "HURACAN",
    "Huracan": "HURACAN",
    "Newell's Old Boys": "NEWELLS_OLD_BOYS",
    "Club Atletico Platense": "PLATENSE",
    "Platense": "PLATENSE",
    "Rosario Central": "ROSARIO_CENTRAL",
    "CA Tigre": "TIGRE",
    "Tigre": "TIGRE",
    "Union de Santa Fe": "UNION_SANTA_FE",
}

API_FOOTBALL_TO_CANONICAL_BRASILEIRAO: dict[str, str] = {
    "Flamengo": "FLAMENGO",
    "SE Palmeiras": "PALMEIRAS",
    "Palmeiras": "PALMEIRAS",
    "Grêmio": "GREMIO",
    "Gremio": "GREMIO",
    "SC Internacional": "INTERNACIONAL",
    "Internacional": "INTERNACIONAL",
    "Athletico-PR": "ATHLETICO_PARANAENSE",
    "Athletico Paranaense": "ATHLETICO_PARANAENSE",
    "Fluminense FC": "FLUMINENSE",
    "Fluminense": "FLUMINENSE",
    "SC Corinthians": "CORINTHIANS",
    "Corinthians": "CORINTHIANS",
    "Sao Paulo FC": "SAO_PAULO",
    "Sao Paulo": "SAO_PAULO",
    "Santos FC": "SANTOS",
    "Santos": "SANTOS",
    "Botafogo FR": "BOTAFOGO",
    "Botafogo": "BOTAFOGO",
    "Vasco da Gama": "VASCO_DA_GAMA",
    "CR Vasco da Gama": "VASCO_DA_GAMA",
    "Cruzeiro": "CRUZEIRO",
    "Atletico Mineiro": "ATLETICO_MINEIRO",
    "Atletico-MG": "ATLETICO_MINEIRO",
    "EC Bahia": "BAHIA",
    "Bahia": "BAHIA",
    "Fortaleza EC": "FORTALEZA",
    "Fortaleza": "FORTALEZA",
    "Ceara SC": "CEARA",
    "Ceara": "CEARA",
    "Goias EC": "GOIAS",
    "Goias": "GOIAS",
    "Coritiba FC": "CORITIBA",
    "Coritiba": "CORITIBA",
    "Chapecoense": "CHAPECOENSE",
    "Chapecoense-sc": "CHAPECOENSE",
    "EC Juventude": "JUVENTUDE",
    "Juventude": "JUVENTUDE",
    "Cuiaba EC": "CUIABA",
    "Cuiaba": "CUIABA",
    "America Mineiro": "AMERICA_MINEIRO",
    "Red Bull Bragantino": "BRAGANTINO",
    "Bragantino": "BRAGANTINO",
    "EC Vitoria": "VITORIA",
    "Vitoria": "VITORIA",
    "Criciuma EC": "CRICIUMA",
    "Criciuma": "CRICIUMA",
}

API_FOOTBALL_TO_CANONICAL_GREEK_SUPER_LEAGUE: dict[str, str] = {
    "Olympiakos Piraeus": "OLYMPIAKOS",
    "Olympiakos": "OLYMPIAKOS",
    "Panathinaikos FC": "PANATHINAIKOS",
    "Panathinaikos": "PANATHINAIKOS",
    "AEK Athens": "AEK_ATHENS",
    "AEK Athens FC": "AEK_ATHENS",
    "PAOK Thessaloniki": "PAOK",
    "PAOK": "PAOK",
    "Aris Thessaloniki": "ARIS",
    "Aris Thessalonikis": "ARIS",
    "Aris": "ARIS",
    "OFI Crete": "OFI",
    "OFI": "OFI",
    "Atromitos Athens": "ATROMITOS",
    "Atromitos": "ATROMITOS",
    "Volos FC": "VOLOS",
    "Volos NFC": "VOLOS",
    "Panetolikos Agrinio": "PANETOLIKOS",
    "Panetolikos": "PANETOLIKOS",
    "Panserraikos FC": "PANSERRAIKOS",
    "Panserraikos": "PANSERRAIKOS",
    "AEL": "AEL",
    "Larisa": "AEL",
    "AEL Larissa": "AEL",
    "PAS Lamia": "LAMIA",
    "Lamia": "LAMIA",
    "Asteras Tripolis": "ASTERAS_TRIPOLIS",
    "Ionikos FC": "IONIKOS",
    "Ionikos": "IONIKOS",
    "Levadiakos FC": "LEVADIAKOS",
    "Levadiakos": "LEVADIAKOS",
    "PAS Giannina": "GIANNINA",
}

API_FOOTBALL_TO_CANONICAL_EKSTRAKLASA: dict[str, str] = {
    "Legia Warszawa": "LEGIA_WARSAW",
    "Legia Warsaw": "LEGIA_WARSAW",
    "Lech Poznań": "LECH_POZNAN",
    "Lech Poznan": "LECH_POZNAN",
    "Rakow Czestochowa": "RAKOW",
    "Jagiellonia Bialystok": "JAGIELLONIA",
    "Pogon Szczecin": "POGON_SZCZECIN",
    "Slask Wroclaw": "SLASK_WROCLAW",
    "Widzew Łódź": "WIDZEW_LODZ",
    "Widzew Lodz": "WIDZEW_LODZ",
    "Górnik Zabrze": "GORNIK_ZABRZE",
    "Gornik Zabrze": "GORNIK_ZABRZE",
    "MKS Cracovia": "CRACOVIA",
    "Cracovia": "CRACOVIA",
    "Piast Gliwice": "PIAST_GLIWICE",
    "Warta Poznan": "WARTA_POZNAN",
    "Zaglebie Lubin": "ZAGLEBIE_LUBIN",
    "Stal Mielec": "STAL_MIELEC",
    "Korona Kielce": "KORONA_KIELCE",
    "Motor Lublin": "MOTOR_LUBLIN",
    "Radomiak Radom": "RADOMIAK",
}

API_FOOTBALL_TO_CANONICAL_SUPER_LIG: dict[str, str] = {
    "Galatasaray SK": "GALATASARAY",
    "Galatasaray": "GALATASARAY",
    "Fenerbahce SK": "FENERBAHCE",
    "Fenerbahce": "FENERBAHCE",
    "Besiktas JK": "BESIKTAS",
    "Besiktas": "BESIKTAS",
    "Trabzonspor": "TRABZONSPOR",
    "Istanbul Basaksehir FK": "ISTANBUL_BASAKSEHIR",
    "Istanbul Basaksehir": "ISTANBUL_BASAKSEHIR",
    "Antalyaspor": "ANTALYASPOR",
    "Adana Demirspor": "ADANA_DEMIRSPOR",
    "Konyaspor": "KONYASPOR",
    "Sivasspor": "SIVASSPOR",
    "Alanyaspor": "ALANYASPOR",
    "Gaziantep FK": "GAZIANTEP",
    "Gaziantep": "GAZIANTEP",
    "Kayserispor": "KAYSERISPOR",
    "Kasimpasa SK": "KASIMPASA",
    "Kasimpasa": "KASIMPASA",
    "Samsunspor": "SAMSUNSPOR",
    "Eyupspor": "EYUPSPOR",
    "Bodrumspor": "BODRUMSPOR",
    "Goztepe SK": "GOZTEPE",
    "Goztepe": "GOZTEPE",
}

API_FOOTBALL_TO_CANONICAL_ALLSVENSKAN: dict[str, str] = {
    "Malmo FF": "MALMO",
    "Malmo": "MALMO",
    "AIK": "AIK",
    "AIK Stockholm": "AIK",
    "Djurgardens IF": "DJURGARDEN",
    "Hammarby IF": "HAMMARBY",
    "Hammarby": "HAMMARBY",
    "IFK Gothenburg": "IFK_GOTEBORG",
    "IFK Goteborg": "IFK_GOTEBORG",
    "IF Elfsborg": "ELFSBORG",
    "Elfsborg": "ELFSBORG",
    "IFK Norrkoping": "NORRKOPING",
    "BK Hacken": "HACKEN",
    "IK Sirius": "SIRIUS",
    "Halmstads BK": "HALMSTAD",
    "Halmstad": "HALMSTAD",
    "Kalmar FF": "KALMAR",
}

API_FOOTBALL_TO_CANONICAL_J1_LEAGUE: dict[str, str] = {
    "Vissel Kobe": "VISSEL_KOBE",
    "Yokohama F. Marinos": "YOKOHAMA_F_MARINOS",
    "Kawasaki Frontale": "KAWASAKI_FRONTALE",
    "Urawa Red Diamonds": "URAWA_REDS",
    "Kashima Antlers": "KASHIMA_ANTLERS",
    "FC Tokyo": "FC_TOKYO",
    "Nagoya Grampus": "NAGOYA_GRAMPUS",
    "Sanfrecce Hiroshima": "SANFRECCE_HIROSHIMA",
    "Cerezo Osaka": "CEREZO_OSAKA",
    "Gamba Osaka": "GAMBA_OSAKA",
    "Hokkaido Consadole Sapporo": "CONSADOLE_SAPPORO",
    "Sagan Tosu": "SAGAN_TOSU",
    "FC Machida Zelvia": "MACHIDA_ZELVIA",
    "Avispa Fukuoka": "AVISPA_FUKUOKA",
    "Albirex Niigata": "ALBIREX_NIIGATA",
    "Tokyo Verdy": "TOKYO_VERDY",
    "Jubilo Iwata": "JUBILO_IWATA",
    "Kashiwa Reysol": "KASHIWA_REYSOL",
}

API_FOOTBALL_TO_CANONICAL_K_LEAGUE_1: dict[str, str] = {
    "Ulsan HD FC": "ULSAN_HD",
    "Jeonbuk Hyundai Motors": "JEONBUK",
    "Jeonbuk": "JEONBUK",
    "Pohang Steelers": "POHANG_STEELERS",
    "Incheon United FC": "INCHEON_UNITED",
    "Incheon United": "INCHEON_UNITED",
    "Suwon Samsung Bluewings": "SUWON_BLUEWINGS",
    "Daejeon Citizen FC": "DAEJEON_CITIZEN",
    "Daegu FC": "DAEGU",
    "Gwangju FC": "GWANGJU",
    "Gangwon FC": "GANGWON",
    "FC Seoul": "FC_SEOUL",
    "Jeju United FC": "JEJU_UNITED",
    "Gimcheon Sangmu FC": "GIMCHEON_SANGMU",
}

API_FOOTBALL_TO_CANONICAL_CHILE_PRIMERA: dict[str, str] = {
    "Colo-Colo": "COLO_COLO",
    "Colo Colo": "COLO_COLO",
    "Universidad de Chile": "UNIVERSIDAD_DE_CHILE",
    "CD Universidad Catolica": "UNIVERSIDAD_CATOLICA",
    "Club de Deportes Cobreloa": "COBRELOA",
    "Cobreloa": "COBRELOA",
    "CD Huachipato": "HUACHIPATO",
    "Huachipato": "HUACHIPATO",
    "Union Espanola": "UNION_ESPANOLA",
    "CD Cobresal": "COBRESAL",
    "Cobresal": "COBRESAL",
    "Audax Italiano": "AUDAX_ITALIANO",
    "O'Higgins FC": "OHIGGINS",
    "O'Higgins": "OHIGGINS",
    "CD Palestino": "PALESTINO",
    "Everton de Vina del Mar": "EVERTON_CHILE",
    "CD Curico Unido": "CURICO_UNIDO",
    "Nublense": "NUBLENSE",
    "Deportes Iquique": "IQUIQUE",
    "Union La Calera": "LA_CALERA",
}

# ---------------------------------------------------------------------------
# English Championship (league 40) — API-Football display name → canonical
# ---------------------------------------------------------------------------

API_FOOTBALL_TO_CANONICAL_ENG_CHAMPIONSHIP: dict[str, str] = {
    "Birmingham": "BIRMINGHAM",
    "Birmingham City": "BIRMINGHAM",
    "Blackburn": "BLACKBURN",
    "Blackburn Rovers": "BLACKBURN",
    "Bristol City": "BRISTOL_CITY",
    "Charlton": "CHARLTON",
    "Charlton Athletic": "CHARLTON",
    "Coventry": "COVENTRY",
    "Coventry City": "COVENTRY",
    "Derby": "DERBY",
    "Derby County": "DERBY",
    "Hull City": "HULL_CITY",
    "Ipswich": "IPSWICH",
    "Ipswich Town": "IPSWICH",
    "Leeds": "LEEDS",
    "Leeds United": "LEEDS",
    "Leicester": "LEICESTER",
    "Leicester City": "LEICESTER",
    "Middlesbrough": "MIDDLESBROUGH",
    "Millwall": "MILLWALL",
    "Norwich": "NORWICH",
    "Norwich City": "NORWICH",
    "Oxford United": "OXFORD_UNITED",
    "Portsmouth": "PORTSMOUTH",
    "Preston": "PRESTON",
    "Preston North End": "PRESTON",
    "QPR": "QPR",
    "Queens Park Rangers": "QPR",
    "Sheffield Utd": "SHEFFIELD_UNITED",
    "Sheffield United": "SHEFFIELD_UNITED",
    "Sheffield Wednesday": "SHEFFIELD_WEDNESDAY",
    "Southampton": "SOUTHAMPTON",
    "Stoke City": "STOKE_CITY",
    "Swansea": "SWANSEA",
    "Swansea City": "SWANSEA",
    "Watford": "WATFORD",
    "West Brom": "WEST_BROM",
    "West Bromwich Albion": "WEST_BROM",
    "Wrexham": "WREXHAM",
}

# ---------------------------------------------------------------------------
# English League One (league 41) — API-Football display name → canonical
# ---------------------------------------------------------------------------

API_FOOTBALL_TO_CANONICAL_ENG_LEAGUE_ONE: dict[str, str] = {
    "AFC Wimbledon": "AFC_WIMBLEDON",
    "Barnsley": "BARNSLEY",
    "Blackpool": "BLACKPOOL",
    "Bolton": "BOLTON",
    "Bolton Wanderers": "BOLTON",
    "Bradford": "BRADFORD",
    "Bradford City": "BRADFORD",
    "Burton Albion": "BURTON",
    "Cardiff": "CARDIFF",
    "Cardiff City": "CARDIFF",
    "Doncaster": "DONCASTER",
    "Doncaster Rovers": "DONCASTER",
    "Exeter City": "EXETER",
    "Huddersfield": "HUDDERSFIELD",
    "Huddersfield Town": "HUDDERSFIELD",
    "Leyton Orient": "LEYTON_ORIENT",
    "Lincoln": "LINCOLN",
    "Lincoln City": "LINCOLN",
    "Luton": "LUTON",
    "Luton Town": "LUTON",
    "Mansfield Town": "MANSFIELD",
    "Northampton": "NORTHAMPTON",
    "Northampton Town": "NORTHAMPTON",
    "Peterborough": "PETERBOROUGH",
    "Peterborough United": "PETERBOROUGH",
    "Plymouth": "PLYMOUTH",
    "Plymouth Argyle": "PLYMOUTH",
    "Port Vale": "PORT_VALE",
    "Reading": "READING",
    "Rotherham": "ROTHERHAM",
    "Rotherham United": "ROTHERHAM",
    "Stevenage": "STEVENAGE",
    "Stockport County": "STOCKPORT",
    "Wigan": "WIGAN",
    "Wigan Athletic": "WIGAN",
    "Wycombe": "WYCOMBE",
    "Wycombe Wanderers": "WYCOMBE",
}

# ---------------------------------------------------------------------------
# English League Two (league 42) — API-Football display name → canonical
# ---------------------------------------------------------------------------

API_FOOTBALL_TO_CANONICAL_ENG_LEAGUE_TWO: dict[str, str] = {
    "Accrington ST": "ACCRINGTON",
    "Accrington Stanley": "ACCRINGTON",
    "Barnet": "BARNET",
    "Barrow": "BARROW",
    "Bristol Rovers": "BRISTOL_ROVERS",
    "Bromley": "BROMLEY",
    "Cambridge United": "CAMBRIDGE_UNITED",
    "Cheltenham": "CHELTENHAM",
    "Cheltenham Town": "CHELTENHAM",
    "Chesterfield": "CHESTERFIELD",
    "Colchester": "COLCHESTER",
    "Colchester United": "COLCHESTER",
    "Crawley Town": "CRAWLEY",
    "Crewe": "CREWE",
    "Crewe Alexandra": "CREWE",
    "Fleetwood Town": "FLEETWOOD",
    "Gillingham": "GILLINGHAM",
    "Grimsby": "GRIMSBY",
    "Grimsby Town": "GRIMSBY",
    "Harrogate Town": "HARROGATE",
    "Milton Keynes Dons": "MK_DONS",
    "Newport County": "NEWPORT",
    "Notts County": "NOTTS_COUNTY",
    "Oldham": "OLDHAM",
    "Oldham Athletic": "OLDHAM",
    "Salford City": "SALFORD",
    "Shrewsbury": "SHREWSBURY",
    "Shrewsbury Town": "SHREWSBURY",
    "Swindon Town": "SWINDON",
    "Tranmere": "TRANMERE",
    "Tranmere Rovers": "TRANMERE",
    "Walsall": "WALSALL",
}

# ---------------------------------------------------------------------------
# German 3. Liga (league 80) — API-Football display name → canonical
# ---------------------------------------------------------------------------

API_FOOTBALL_TO_CANONICAL_LIGA_3: dict[str, str] = {
    "Alemannia Aachen": "AACHEN",
    "Arminia Bielefeld": "ARMINIA_BIELEFELD",
    "Energie Cottbus": "COTTBUS",
    "Dynamo Dresden": "DRESDEN",
    "MSV Duisburg": "DUISBURG",
    "Erzgebirge Aue": "ERZGEBIRGE_AUE",
    "Hansa Rostock": "HANSA_ROSTOCK",
    "FC Ingolstadt 04": "INGOLSTADT",
    "Waldhof Mannheim": "MANNHEIM",
    "VfL Osnabrück": "OSNABRUECK",
    "VfL Osnabrueck": "OSNABRUECK",
    "SSV Jahn Regensburg": "REGENSBURG",
    "Rot-Weiss Essen": "ROT_WEISS_ESSEN",
    "1. FC Saarbrücken": "SAARBRUECKEN",
    "FC Saarbrucken": "SAARBRUECKEN",
    "SV Sandhausen": "SANDHAUSEN",
    "SpVgg Unterhaching": "UNTERHACHING",
    "SC Verl": "VERL",
    "Viktoria Köln": "VIKTORIA_KOELN",
    "Viktoria Koln": "VIKTORIA_KOELN",
    "SV Wehen Wiesbaden": "WEHEN_WIESBADEN",
    "Würzburger Kickers": "WUERZBURGER_KICKERS",
}

# Combined API-Football → canonical (all leagues)
API_FOOTBALL_TO_CANONICAL: dict[str, str] = {
    **API_FOOTBALL_TO_CANONICAL_EPL,
    **API_FOOTBALL_TO_CANONICAL_BUNDESLIGA,
    **API_FOOTBALL_TO_CANONICAL_LA_LIGA,
    **API_FOOTBALL_TO_CANONICAL_SERIE_A,
    **API_FOOTBALL_TO_CANONICAL_LIGUE_1,
    **API_FOOTBALL_TO_CANONICAL_EREDIVISIE,
    **API_FOOTBALL_TO_CANONICAL_PRIMEIRA_LIGA,
    **API_FOOTBALL_TO_CANONICAL_JUPILER_PRO,
    **API_FOOTBALL_TO_CANONICAL_DANISH_SUPERLIGA,
    **API_FOOTBALL_TO_CANONICAL_MLS,
    **API_FOOTBALL_TO_CANONICAL_AUSTRIAN_BUNDESLIGA,
    **API_FOOTBALL_TO_CANONICAL_ELITESERIEN,
    **API_FOOTBALL_TO_CANONICAL_SWISS_SUPER_LEAGUE,
    **API_FOOTBALL_TO_CANONICAL_SCOTTISH_PREMIERSHIP,
    **API_FOOTBALL_TO_CANONICAL_A_LEAGUE,
    **API_FOOTBALL_TO_CANONICAL_LIGA_MX,
    **API_FOOTBALL_TO_CANONICAL_ARGENTINA_PRIMERA,
    **API_FOOTBALL_TO_CANONICAL_BRASILEIRAO,
    **API_FOOTBALL_TO_CANONICAL_GREEK_SUPER_LEAGUE,
    **API_FOOTBALL_TO_CANONICAL_EKSTRAKLASA,
    **API_FOOTBALL_TO_CANONICAL_SUPER_LIG,
    **API_FOOTBALL_TO_CANONICAL_ALLSVENSKAN,
    **API_FOOTBALL_TO_CANONICAL_J1_LEAGUE,
    **API_FOOTBALL_TO_CANONICAL_K_LEAGUE_1,
    **API_FOOTBALL_TO_CANONICAL_CHILE_PRIMERA,
    **API_FOOTBALL_TO_CANONICAL_ENG_CHAMPIONSHIP,
    **API_FOOTBALL_TO_CANONICAL_ENG_LEAGUE_ONE,
    **API_FOOTBALL_TO_CANONICAL_ENG_LEAGUE_TWO,
    **API_FOOTBALL_TO_CANONICAL_LIGA_3,
}

# ---------------------------------------------------------------------------
# Cross-provider aliases (Odds API, OddsPapi, Betfair name variants)
# These names appear in data from The Odds API, OddsPapi, and Betfair but
# are not in the API-Football display-name dicts above. Added to ensure
# resolve_team_to_canonical() never falls back to slugification for any
# team in our 20 prediction leagues.
# ---------------------------------------------------------------------------

_CROSS_PROVIDER_ALIASES: dict[str, str] = {
    # English lower leagues
    "AFC Wimbledon": "AFC_WIMBLEDON",
    "Accrington Stanley": "ACCRINGTON",
    "Barnet FC": "BARNET",
    "Barnsley FC": "BARNSLEY",
    "Barrow AFC": "BARROW",
    "Blackpool FC": "BLACKPOOL",
    "Bradford City FC": "BRADFORD",
    "Bristol Rovers": "BRISTOL_ROVERS",
    "Bromley FC": "BROMLEY",
    "Burton Albion": "BURTON",
    "Cambridge United": "CAMBRIDGE_UNITED",
    "Charlton Athletic": "CHARLTON",
    "Cheltenham Town": "CHELTENHAM",
    "Chesterfield FC": "CHESTERFIELD",
    "Colchester United": "COLCHESTER",
    "Crawley Town": "CRAWLEY",
    "Crewe Alexandra": "CREWE",
    "Doncaster Rovers": "DONCASTER",
    "Exeter City": "EXETER",
    "Fleetwood Town": "FLEETWOOD",
    "Gillingham FC": "GILLINGHAM",
    "Grimsby Town": "GRIMSBY",
    "Harrogate Town": "HARROGATE",
    "Leyton Orient London": "LEYTON_ORIENT",
    "Lincoln City": "LINCOLN",
    "Mansfield Town": "MANSFIELD",
    "Milton Keynes Dons": "MK_DONS",
    "Newport County": "NEWPORT",
    "Northampton Town": "NORTHAMPTON",
    "Notts County": "NOTTS_COUNTY",
    "Oldham Athletic": "OLDHAM",
    "Peterborough United": "PETERBOROUGH",
    "Port Vale": "PORT_VALE",
    "Reading FC": "READING",
    "Rotherham United": "ROTHERHAM",
    "Salford City": "SALFORD",
    "Shrewsbury Town": "SHREWSBURY",
    "Stevenage FC": "STEVENAGE",
    "Stockport County FC": "STOCKPORT",
    "Swindon Town": "SWINDON",
    "Tranmere Rovers FC": "TRANMERE",
    "Walsall FC": "WALSALL",
    "Wrexham AFC": "WREXHAM",
    "Wycombe Wanderers": "WYCOMBE",
    # Dutch
    "Ajax Amsterdam": "AJAX",
    "Excelsior Rotterdam": "EXCELSIOR",
    "Feyenoord Rotterdam": "FEYENOORD",
    "FC Twente Enschede": "TWENTE",
    "FC Zwolle": "PEC_ZWOLLE",
    "PEC Zwolle": "PEC_ZWOLLE",
    # German
    "1 FC Nuremberg": "NURNBERG",
    "1. FC Cologne": "KOLN",
    "Dynamo Dresden": "DRESDEN",
    "FSV Mainz": "MAINZ",
    "SC Preussen 06 Munster": "PREUSSEN_MUNSTER",
    "SV 07 Elversberg": "ELVERSBERG",
    # Italian
    "Cagliari Calcio": "CAGLIARI",
    "Calcio Padova": "PADOVA",
    "Carrarese Calcio": "CARRARESE",
    "Cesena FC": "CESENA",
    "Delfino Pescara": "PESCARA",
    "Empoli FC": "EMPOLI",
    "FC Sudtirol Bolzano": "SUDTIROL",
    "Frosinone Calcio": "FROSINONE",
    "Inter Milano": "INTER_MILAN",
    "Internazionale": "INTER_MILAN",
    "Juve Stabia": "JUVE_STABIA",
    "Lazio Rome": "LAZIO",
    "Mantova 1911": "MANTOVA",
    "Palermo FC": "PALERMO",
    "Pisa SC": "PISA",
    "Reggiana 1919": "REGGIANA",
    "Sampdoria Genoa": "SAMPDORIA",
    "Sassuolo Calcio": "SASSUOLO",
    "US Avellino": "AVELLINO",
    "Virtus Entella": "ENTELLA",
    # French
    "Clermont Foot 63": "CLERMONT",
    "ESTAC Troyes": "TROYES",
    "FC Annecy": "ANNECY",
    "Le Mans FC": "LE_MANS",
    "Nancy-Lorraine": "NANCY",
    "Olympique Lyon": "LYON",
    "Racing Club De Lens": "LENS",
    "Rodez Aveyron Football": "RODEZ",
    "Stade Brest 29": "BREST",
    "Stade Lavallois MFC": "LAVAL",
    "Stade Reims": "REIMS",
    "Stade Rennais FC": "RENNES",
    "Strasbourg Alsace": "STRASBOURG",
    "US Boulogne": "BOULOGNE",
    # Turkish
    "Besiktas Istanbul": "BESIKTAS",
    "Fatih Karagumruk Istanbul": "KARAGUMRUK",
    "Fenerbahce Istanbul": "FENERBAHCE",
    "Genclerbirligi SK": "GENCLERBIRLIGI",
    "Kasimpasa Istanbul": "KASIMPASA",
    "Kocaelispor": "KOCAELISPOR",
    # Brazilian
    "Atletico Mineiro MG": "ATLETICO_MG",
    "Botafogo FR RJ": "BOTAFOGO",
    "CA Paranaense PR": "ATHLETICO_PR",
    "CR Flamengo RJ": "FLAMENGO",
    "CR Vasco da Gama RJ": "VASCO",
    "Clube do Remo PA": "REMO",
    "Coritiba FC PR": "CORITIBA",
    "Cruzeiro EC MG": "CRUZEIRO",
    "EC Bahia BA": "BAHIA",
    "EC Vitoria BA": "VITORIA",
    "Fluminense FC RJ": "FLUMINENSE",
    "Gremio FB Porto Alegrense RS": "GREMIO",
    "Mirassol FC SP": "MIRASSOL",
    "Red Bull Bragantino SP": "BRAGANTINO",
    "SC Corinthians SP": "CORINTHIANS",
    "SC Internacional RS": "INTERNACIONAL",
    "SE Palmeiras SP": "PALMEIRAS",
    "Santos FC SP": "SANTOS",
    "Sao Paulo FC SP": "SAO_PAULO",
    # Mexican
    "CF America": "AMERICA",
    "CF Cruz Azul": "CRUZ_AZUL",
    "Club Santos Laguna": "SANTOS_LAGUNA",
    "Club Tijuana de Caliente": "TIJUANA",
    "Deportivo Toluca FC": "TOLUCA",
    "Queretaro FC": "QUERETARO",
    # MLS
    "Saint Louis City SC": "ST_LOUIS_CITY",
    # API-Football Turkish variants (diacritics differ from OddsPapi)
    "Kasımpaşa": "KASIMPASA",  # noqa: RUF001 - Turkish dotless-i is intentional
    "Gençlerbirliği S.K.": "GENCLERBIRLIGI",
    "Başakşehir": "ISTANBUL_BASAKSEHIR",
    "Eyüpspor": "EYUPSPOR",
    "Beşiktaş": "BESIKTAS",
    "Fenerbahçe": "FENERBAHCE",
    "Göztepe": "GOZTEPE",
    "Fatih Karagümrük": "KARAGUMRUK",
    "Istanbul Basaksehir": "ISTANBUL_BASAKSEHIR",
    # API-Football Brazilian variants
    "Vasco DA Gama": "VASCO",
    "Atletico Paranaense": "ATHLETICO_PR",
    "Atletico-MG": "ATLETICO_MG",
    "Chapecoense-sc": "CHAPECOENSE",
    "RB Bragantino": "BRAGANTINO",
    "Club America": "AMERICA",
    "U.N.A.M. - Pumas": "PUMAS_UNAM",
    # API-Football name variants that differ from OddsPapi
    "Stockport County": "STOCKPORT",
    "Accrington ST": "ACCRINGTON",
    "Stade Brestois 29": "BREST",
    "Estac Troyes": "TROYES",
    "RED Star FC 93": "RED_STAR",
    "Clermont Foot": "CLERMONT",
    "Northampton": "NORTHAMPTON",
    # Australian
    "Adelaide United FC": "ADELAIDE_UNITED",
    "Brisbane Roar FC": "BRISBANE_ROAR",
    "Newcastle United Jets": "NEWCASTLE_JETS",
    "Perth Glory FC": "PERTH_GLORY",
    "Wellington Phoenix FC": "WELLINGTON_PHOENIX",
}

# Merge into the main lookup dict
API_FOOTBALL_TO_CANONICAL.update(_CROSS_PROVIDER_ALIASES)


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


def _build_team_id(team_name: str) -> str:
    """Build canonical team ID from display name (SCREAMING_SNAKE_CASE).

    Local copy of the logic from canonical_ids._slug to avoid circular imports.
    Strips diacritics, replaces separators, uppercases.
    """
    nfkd = unicodedata.normalize("NFKD", team_name)
    ascii_only = nfkd.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[\s\-/&.]+", "_", ascii_only)
    slug = re.sub(r"[^A-Za-z0-9_]", "", slug)
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug.upper()


def resolve_team_to_canonical(name: str) -> str:
    """Resolve any provider's team name to canonical ID. Checks all leagues.

    Resolution order:
      1. Exact match in API_FOOTBALL_TO_CANONICAL dict
      2. Accent-stripped, case-normalised match in universal reverse index
         (covers all alias dicts for all 33 prediction leagues)
      3. Fall back to ``build_team_id()`` — SCREAMING_SNAKE_CASE slug

    Args:
        name: Team name from any provider (Odds API, API-Football, Betfair,
              Understat, FootyStats, Polymarket, etc.).

    Returns:
        Canonical team ID (e.g. ``"MAN_CITY"``, ``"ATLETICO_MADRID"``).
        Always returns a non-empty string.
    """
    if not name:
        return ""

    # 1. Exact match in API-Football combined dict (preserves case)
    exact = API_FOOTBALL_TO_CANONICAL.get(name)
    if exact is not None:
        return exact

    # 2. Normalised match in universal reverse index
    key = _normalize_key(name)
    found = _UNIVERSAL_REVERSE.get(key)
    if found is not None:
        return found

    # 3. Fallback: build from raw name
    return _build_team_id(name)


class TeamResolutionError(ValueError):
    """Raised when a team name cannot be resolved to a known canonical ID."""


class FixtureAlignmentError(ValueError):
    """Raised when fixtures from different sources don't align."""


def validate_team_resolution(name: str, provider: str = "") -> str:
    """Resolve team name to canonical ID, raising if it falls back to slugification.

    Use this instead of ``resolve_team_to_canonical()`` when silent fallback
    is not acceptable (ML features, arb detection, fixture matching).

    Args:
        name: Team name from any provider.
        provider: Optional provider name for error context (e.g. "odds_api", "oddspapi").

    Returns:
        Canonical team ID from tier 1 (exact) or tier 2 (normalised) resolution.

    Raises:
        TeamResolutionError: If the name falls through to tier 3 (slugification),
            meaning it's not in any alias dict.
    """
    if not name:
        raise TeamResolutionError(f"Empty team name from {provider or 'unknown'}")

    # Tier 1: exact match
    exact = API_FOOTBALL_TO_CANONICAL.get(name)
    if exact is not None:
        return exact

    # Tier 2: normalised match
    key = _normalize_key(name)
    found = _UNIVERSAL_REVERSE.get(key)
    if found is not None:
        return found

    # Tier 3: slugification fallback — NOT acceptable, raise
    slug = _build_team_id(name)
    raise TeamResolutionError(
        f"Team '{name}' from {provider or 'unknown'} resolved to slug '{slug}' "
        f"(not in any alias dict). Add it to _CROSS_PROVIDER_ALIASES in team_mappings.py."
    )


def validate_fixture_alignment(
    home_a: str,
    away_a: str,
    kickoff_a: str,
    home_b: str,
    away_b: str,
    kickoff_b: str,
    source_a: str = "source_a",
    source_b: str = "source_b",
    kickoff_tolerance_mins: int = 30,
) -> tuple[str, str]:
    """Validate that two fixtures from different sources refer to the same match.

    Checks:
      1. Both home teams resolve to the same canonical ID
      2. Both away teams resolve to the same canonical ID
      3. Kickoff times are within tolerance (UTC alignment)

    Args:
        home_a/away_a: Team names from source A.
        home_b/away_b: Team names from source B.
        kickoff_a/kickoff_b: ISO 8601 kickoff timestamps.
        source_a/source_b: Source names for error messages.
        kickoff_tolerance_mins: Max allowed kickoff difference in minutes.

    Returns:
        Tuple of (canonical_home, canonical_away).

    Raises:
        FixtureAlignmentError: If teams don't match or kickoffs diverge.
    """
    h_a = resolve_team_to_canonical(home_a)
    h_b = resolve_team_to_canonical(home_b)
    a_a = resolve_team_to_canonical(away_a)
    a_b = resolve_team_to_canonical(away_b)

    if h_a != h_b:
        raise FixtureAlignmentError(f"Home team mismatch: {source_a}='{home_a}'→{h_a} vs {source_b}='{home_b}'→{h_b}")
    if a_a != a_b:
        raise FixtureAlignmentError(f"Away team mismatch: {source_a}='{away_a}'→{a_a} vs {source_b}='{away_b}'→{a_b}")

    # Kickoff alignment check
    if kickoff_a and kickoff_b:
        try:
            dt_a = datetime.fromisoformat(kickoff_a.replace("Z", "+00:00"))
            dt_b = datetime.fromisoformat(kickoff_b.replace("Z", "+00:00"))
            diff_mins = abs((dt_a - dt_b).total_seconds()) / 60
            if diff_mins > kickoff_tolerance_mins:
                raise FixtureAlignmentError(
                    f"Kickoff time mismatch: {source_a}={kickoff_a} vs "
                    f"{source_b}={kickoff_b} (diff={diff_mins:.0f}m, "
                    f"tolerance={kickoff_tolerance_mins}m)"
                )
        except (ValueError, TypeError):
            pass  # Can't parse — skip time check

    return h_a, a_a


__all__ = [
    "ALLSVENSKAN_TEAM_ALIASES",
    "ALL_LEAGUE_ALIASES",
    "API_FOOTBALL_TO_CANONICAL",
    "API_FOOTBALL_TO_CANONICAL_ALLSVENSKAN",
    "API_FOOTBALL_TO_CANONICAL_ARGENTINA_PRIMERA",
    "API_FOOTBALL_TO_CANONICAL_AUSTRIAN_BUNDESLIGA",
    "API_FOOTBALL_TO_CANONICAL_A_LEAGUE",
    "API_FOOTBALL_TO_CANONICAL_BRASILEIRAO",
    "API_FOOTBALL_TO_CANONICAL_BUNDESLIGA",
    "API_FOOTBALL_TO_CANONICAL_CHILE_PRIMERA",
    "API_FOOTBALL_TO_CANONICAL_DANISH_SUPERLIGA",
    "API_FOOTBALL_TO_CANONICAL_EKSTRAKLASA",
    "API_FOOTBALL_TO_CANONICAL_ELITESERIEN",
    "API_FOOTBALL_TO_CANONICAL_ENG_CHAMPIONSHIP",
    "API_FOOTBALL_TO_CANONICAL_ENG_LEAGUE_ONE",
    "API_FOOTBALL_TO_CANONICAL_ENG_LEAGUE_TWO",
    "API_FOOTBALL_TO_CANONICAL_EPL",
    "API_FOOTBALL_TO_CANONICAL_EREDIVISIE",
    "API_FOOTBALL_TO_CANONICAL_GREEK_SUPER_LEAGUE",
    "API_FOOTBALL_TO_CANONICAL_J1_LEAGUE",
    "API_FOOTBALL_TO_CANONICAL_JUPILER_PRO",
    "API_FOOTBALL_TO_CANONICAL_K_LEAGUE_1",
    "API_FOOTBALL_TO_CANONICAL_LA_LIGA",
    "API_FOOTBALL_TO_CANONICAL_LIGA_3",
    "API_FOOTBALL_TO_CANONICAL_LIGA_MX",
    "API_FOOTBALL_TO_CANONICAL_LIGUE_1",
    "API_FOOTBALL_TO_CANONICAL_MLS",
    "API_FOOTBALL_TO_CANONICAL_PRIMEIRA_LIGA",
    "API_FOOTBALL_TO_CANONICAL_SCOTTISH_PREMIERSHIP",
    "API_FOOTBALL_TO_CANONICAL_SERIE_A",
    "API_FOOTBALL_TO_CANONICAL_SUPER_LIG",
    "API_FOOTBALL_TO_CANONICAL_SWISS_SUPER_LEAGUE",
    "ARGENTINA_PRIMERA_TEAM_ALIASES",
    "AUSTRIAN_BUNDESLIGA_TEAM_ALIASES",
    "A_LEAGUE_TEAM_ALIASES",
    "BETFAIR_TO_CANONICAL",
    "BRASILEIRAO_TEAM_ALIASES",
    "BUNDESLIGA_2_TEAM_ALIASES",
    "BUNDESLIGA_TEAM_ALIASES",
    "CHILE_PRIMERA_TEAM_ALIASES",
    "DANISH_SUPERLIGA_TEAM_ALIASES",
    "EERSTE_DIVISIE_TEAM_ALIASES",
    "EKSTRAKLASA_TEAM_ALIASES",
    "ELITESERIEN_TEAM_ALIASES",
    "ENG_CHAMPIONSHIP_TEAM_ALIASES",
    "ENG_LEAGUE_ONE_TEAM_ALIASES",
    "ENG_LEAGUE_TWO_TEAM_ALIASES",
    "ENG_LOWER_TEAM_ALIASES",
    "EPL_TEAM_ALIASES",
    "EREDIVISIE_TEAM_ALIASES",
    "GREEK_SUPER_LEAGUE_TEAM_ALIASES",
    "J1_LEAGUE_TEAM_ALIASES",
    "JUPILER_PRO_TEAM_ALIASES",
    "K_LEAGUE_1_TEAM_ALIASES",
    "LA_LIGA_TEAM_ALIASES",
    "LIGA_3_TEAM_ALIASES",
    "LIGA_MX_TEAM_ALIASES",
    "LIGUE_1_TEAM_ALIASES",
    "LIGUE_2_TEAM_ALIASES",
    "MLS_TEAM_ALIASES",
    "PRIMEIRA_LIGA_TEAM_ALIASES",
    "SCOTTISH_PREMIERSHIP_TEAM_ALIASES",
    "SEGUNDA_DIVISION_TEAM_ALIASES",
    "SERIE_A_TEAM_ALIASES",
    "SERIE_B_TEAM_ALIASES",
    "SUPER_LIG_TEAM_ALIASES",
    "SWISS_SUPER_LEAGUE_TEAM_ALIASES",
    "FixtureAlignmentError",
    "TeamResolutionError",
    "get_canonical_team_name_from_api_football",
    "get_canonical_team_name_from_betfair",
    "resolve_team_to_canonical",
    "validate_fixture_alignment",
    "validate_team_resolution",
]
