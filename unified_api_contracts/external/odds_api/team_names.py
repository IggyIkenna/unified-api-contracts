"""Canonical team ID mappings for Odds API and Understat names."""

from __future__ import annotations

CANONICAL_TO_ODDS_API_EPL: dict[str, str] = {
    "ARSENAL": "Arsenal",
    "CHELSEA": "Chelsea",
    "LIVERPOOL": "Liverpool",
    "MAN_CITY": "Manchester City",
    "MAN_UNITED": "Manchester United",
    "TOTTENHAM": "Tottenham Hotspur",
    "ASTON_VILLA": "Aston Villa",
    "EVERTON": "Everton",
    "LEICESTER": "Leicester City",
    "NEWCASTLE": "Newcastle United",
    "WEST_HAM": "West Ham United",
    "WOLVES": "Wolverhampton Wanderers",
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
    "BAYERN": "Bayern Munich",
    "DORTMUND": "Borussia Dortmund",
    "LEIPZIG": "RB Leipzig",
    "LEVERKUSEN": "Bayer Leverkusen",
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
    "PREUSSEN_MUNSTER": "SC Preußen Münster",
}

# ---------------------------------------------------------------------------
# English Championship (league 40)
# ---------------------------------------------------------------------------

CANONICAL_TO_ODDS_API_ENG_CHAMPIONSHIP: dict[str, str] = {
    "BIRMINGHAM": "Birmingham City",
    "BLACKBURN": "Blackburn Rovers",
    "BRISTOL_CITY": "Bristol City",
    "CHARLTON": "Charlton Athletic",
    "COVENTRY": "Coventry City",
    "DERBY": "Derby County",
    "HULL_CITY": "Hull City",
    "IPSWICH": "Ipswich Town",
    "LEICESTER": "Leicester City",
    "LEEDS": "Leeds United",
    "MIDDLESBROUGH": "Middlesbrough",
    "MILLWALL": "Millwall",
    "NORWICH": "Norwich City",
    "OXFORD_UNITED": "Oxford United",
    "PORTSMOUTH": "Portsmouth",
    "PRESTON": "Preston North End",
    "QPR": "QPR",
    "SHEFFIELD_UNITED": "Sheffield United",
    "SHEFFIELD_WEDNESDAY": "Sheffield Wednesday",
    "SOUTHAMPTON": "Southampton",
    "STOKE_CITY": "Stoke",
    "SWANSEA": "Swansea",
    "WATFORD": "Watford",
    "WEST_BROM": "West Brom",
    "WREXHAM": "Wrexham",
}

# ---------------------------------------------------------------------------
# English League One (league 41)
# ---------------------------------------------------------------------------

CANONICAL_TO_ODDS_API_ENG_LEAGUE_ONE: dict[str, str] = {
    "AFC_WIMBLEDON": "AFC Wimbledon",
    "BARNSLEY": "Barnsley",
    "BLACKPOOL": "Blackpool",
    "BOLTON": "Bolton Wanderers",
    "BRADFORD": "Bradford City",
    "BURTON": "Burton Albion",
    "CARDIFF": "Cardiff",
    "DONCASTER": "Doncaster Rovers",
    "EXETER": "Exeter City",
    "HUDDERSFIELD": "Huddersfield",
    "LEYTON_ORIENT": "Leyton Orient",
    "LINCOLN": "Lincoln City",
    "LUTON": "Luton",
    "MANSFIELD": "Mansfield Town",
    "NORTHAMPTON": "Northampton Town",
    "PETERBOROUGH": "Peterborough United",
    "PLYMOUTH": "Plymouth Argyle",
    "PORT_VALE": "Port Vale",
    "READING": "Reading",
    "ROTHERHAM": "Rotherham United",
    "STEVENAGE": "Stevenage",
    "STOCKPORT": "Stockport County",
    "WIGAN": "Wigan",
    "WYCOMBE": "Wycombe Wanderers",
}

# ---------------------------------------------------------------------------
# English League Two (league 42)
# ---------------------------------------------------------------------------

CANONICAL_TO_ODDS_API_ENG_LEAGUE_TWO: dict[str, str] = {
    "ACCRINGTON": "Accrington Stanley",
    "BARNET": "Barnet",
    "BARROW": "Barrow",
    "BRISTOL_ROVERS": "Bristol Rovers",
    "BROMLEY": "Bromley",
    "CAMBRIDGE_UNITED": "Cambridge United",
    "CHELTENHAM": "Cheltenham Town",
    "CHESTERFIELD": "Chesterfield",
    "COLCHESTER": "Colchester United",
    "CRAWLEY": "Crawley Town",
    "CREWE": "Crewe Alexandra",
    "FLEETWOOD": "Fleetwood Town",
    "GILLINGHAM": "Gillingham",
    "GRIMSBY": "Grimsby Town",
    "HARROGATE": "Harrogate Town",
    "MK_DONS": "Milton Keynes Dons",
    "NEWPORT": "Newport County",
    "NOTTS_COUNTY": "Notts County",
    "OLDHAM": "Oldham Athletic",
    "SALFORD": "Salford City",
    "SHREWSBURY": "Shrewsbury Town",
    "SWINDON": "Swindon Town",
    "TRANMERE": "Tranmere Rovers",
    "WALSALL": "Walsall",
}

# ---------------------------------------------------------------------------
# German 3. Liga (league 80)
# ---------------------------------------------------------------------------

CANONICAL_TO_ODDS_API_LIGA_3: dict[str, str] = {
    "AACHEN": "Alemannia Aachen",
    "ARMINIA_BIELEFELD": "Arminia Bielefeld",
    "COTTBUS": "Energie Cottbus",
    "DRESDEN": "Dynamo Dresden",
    "DUISBURG": "MSV Duisburg",
    "ERZGEBIRGE_AUE": "Erzgebirge Aue",
    "HANSA_ROSTOCK": "Hansa Rostock",
    "INGOLSTADT": "FC Ingolstadt 04",
    "MANNHEIM": "Waldhof Mannheim",
    "MUNSTER": "SC Preußen Münster",
    "OSNABRUECK": "VfL Osnabrück",
    "REGENSBURG": "SSV Jahn Regensburg",
    "ROT_WEISS_ESSEN": "Rot-Weiss Essen",
    "SANDHAUSEN": "SV Sandhausen",
    "SAARBRUECKEN": "1. FC Saarbrücken",
    "UNTERHACHING": "SpVgg Unterhaching",
    "VERL": "SC Verl",
    "VIKTORIA_KOELN": "Viktoria Köln",
    "WEHEN_WIESBADEN": "SV Wehen Wiesbaden",
    "WUERZBURGER_KICKERS": "Würzburger Kickers",
}

CANONICAL_TO_ODDS_API_LA_LIGA: dict[str, str] = {
    "ATHLETIC_CLUB": "Athletic Bilbao",
    "ATLETICO_MADRID": "Atlético Madrid",
    "BARCELONA": "Barcelona",
    "REAL_MADRID": "Real Madrid",
    "REAL_SOCIEDAD": "Real Sociedad",
    "REAL_BETIS": "Real Betis",
    "REAL_VALLADOLID": "Real Valladolid CF",
    "SEVILLA": "Sevilla",
    "VILLARREAL": "Villarreal",
    "CELTA_VIGO": "Celta Vigo",
    "GETAFE": "Getafe",
    "VALENCIA": "Valencia",
    "MALLORCA": "Mallorca",
    "OSASUNA": "Osasuna",
    "RAYO_VALLECANO": "Rayo Vallecano",
    "ALAVES": "Alaves",
    "LEGANES": "Leganes",
    "ESPANYOL": "Espanyol",
    "LAS_PALMAS": "Las Palmas",
    "GIRONA": "Girona",
    # Segunda
    "REAL_SOCIEDAD_B": "Real Sociedad B",
    "BURGOS": "Burgos CF",
    "MIRANDES": "CD Mirandés",
    "SPORTING_GIJON": "Sporting Gijón",
    "CORDOBA": "Córdoba",
    "EIBAR": "Eibar",
    "HUESCA": "Huesca",
    "ELCHE": "Elche",
    "TENERIFE": "Tenerife",
    "ZARAGOZA": "Zaragoza",
    "LEVANTE": "Levante",
    "OVIEDO": "Oviedo",
    "CADIZ": "Cadiz",
    "GRANADA": "Granada",
}

CANONICAL_TO_ODDS_API_SERIE_A: dict[str, str] = {
    "ATALANTA": "Atalanta BC",
    "INTER_MILAN": "Inter Milan",
    "JUVENTUS": "Juventus",
    "AC_MILAN": "AC Milan",
    "NAPOLI": "Napoli",
    "ROMA": "AS Roma",
    "LAZIO": "Lazio",
    "FIORENTINA": "Fiorentina",
    "TORINO": "Torino",
    "BOLOGNA": "Bologna",
    "UDINESE": "Udinese",
    "GENOA": "Genoa",
    "CAGLIARI": "Cagliari",
    "EMPOLI": "Empoli",
    "LECCE": "Lecce",
    "MONZA": "Monza",
    "VERONA": "Hellas Verona",
    "COMO": "Como",
    "PARMA": "Parma",
    "VENEZIA": "Venezia",
    "SALERNITANA": "Salernitana",
    "SASSUOLO": "Sassuolo",
    "FROSINONE": "Frosinone",
    # Serie B
    "SUDTIROL": "Südtirol",
    "AVELLINO": "Avellino",
    "BARI": "Bari",
    "BRESCIA": "Brescia",
    "CARRARESE": "Carrarese",
    "PALERMO": "Palermo",
    "PESCARA": "Pescara",
    "SAMPDORIA": "Sampdoria",
    "SPEZIA": "Spezia",
}

CANONICAL_TO_ODDS_API_LIGUE_1: dict[str, str] = {
    "PSG": "Paris Saint Germain",
    "MONACO": "AS Monaco",
    "MARSEILLE": "Marseille",
    "LYON": "Lyon",
    "LILLE": "Lille",
    "NICE": "Nice",
    "LENS": "RC Lens",
    "RENNES": "Rennes",
    "STRASBOURG": "Strasbourg",
    "NANTES": "Nantes",
    "MONTPELLIER": "Montpellier",
    "BREST": "Brest",
    "TOULOUSE": "Toulouse",
    "REIMS": "Reims",
    "AUXERRE": "Auxerre",
    "ANGERS": "Angers",
    "LE_HAVRE": "Le Havre",
    "SAINT_ETIENNE": "Saint-Etienne",
    # Ligue 2
    "METZ": "Metz",
    "LORIENT": "Lorient",
    "CAEN": "Caen",
    "BORDEAUX": "Bordeaux",
}

CANONICAL_TO_ODDS_API_EREDIVISIE: dict[str, str] = {
    "AJAX": "Ajax",
    "PSV": "PSV Eindhoven",
    "FEYENOORD": "Feyenoord",
    "AZ": "AZ Alkmaar",
    "TWENTE": "FC Twente",
    "UTRECHT": "FC Utrecht",
    "VITESSE": "Vitesse",
    "HEERENVEEN": "SC Heerenveen",
    "GRONINGEN": "FC Groningen",
    "SPARTA_ROTTERDAM": "Sparta Rotterdam",
    "NEC": "NEC Nijmegen",
    "GO_AHEAD_EAGLES": "Go Ahead Eagles",
    "HERACLES": "Heracles Almelo",
    "FORTUNA_SITTARD": "Fortuna Sittard",
    "ALMERE_CITY": "Almere City FC",
    "WAALWIJK": "RKC Waalwijk",
    "VOLENDAM": "FC Volendam",
    "TELSTAR": "SC Telstar",
}

CANONICAL_TO_ODDS_API_PRIMEIRA_LIGA: dict[str, str] = {
    "BENFICA": "Benfica",
    "PORTO": "FC Porto",
    "SPORTING_CP": "Sporting Lisbon",
    "BRAGA": "Braga",
    "VITORIA_GUIMARAES": "Vitoria de Guimaraes",
    "RIO_AVE": "Rio Ave FC",
    "GIL_VICENTE": "Gil Vicente",
    "BOAVISTA": "Boavista",
    "FAMALICAO": "Famalicao",
    "CASA_PIA": "Casa Pia",
    "AROUCA": "Arouca",
    "MOREIRENSE": "Moreirense",
    "ESTORIL": "Estoril",
    "ESTRELA_AMADORA": "Estrela Amadora",
    "ALVERCA": "Alverca",
}

CANONICAL_TO_ODDS_API_JUPILER_PRO: dict[str, str] = {
    "CLUB_BRUGGE": "Club Brugge",
    "ANDERLECHT": "Anderlecht",
    "GENK": "Genk",
    "GENT": "Gent",
    "ANTWERP": "Royal Antwerp",
    "SINT_TRUIDEN": "Sint Truiden",
    "UNION_SG": "Union Saint-Gilloise",
    "WESTERLO": "Westerlo",
    "CERCLE_BRUGGE": "Cercle Brugge KSV",
    "ZULTE_WAREGEM": "SV Zulte-Waregem",
    "STANDARD_LIEGE": "Standard Liege",
    "MECHELEN": "KV Mechelen",
    "CHARLEROI": "Charleroi",
    "LEUVEN": "OH Leuven",
    "KORTRIJK": "Kortrijk",
    "DENDER": "Dender",
    "RAAL_LA_LOUVIERE": "RAAL La Louvière",
}

CANONICAL_TO_ODDS_API_DANISH_SUPERLIGA: dict[str, str] = {
    "COPENHAGEN": "FC Copenhagen",
    "MIDTJYLLAND": "FC Midtjylland",
    "BRONDBY": "Brondby IF",
    "NORDSJAELLAND": "FC Nordsjaelland",
    "SILKEBORG": "Silkeborg IF",
    "AARHUS": "AGF Aarhus",
    "VIBORG": "Viborg FF",
    "AALBORG": "AaB",
    "RANDERS": "Randers FC",
    "LYNGBY": "Lyngby",
    "HVIDOVRE": "Hvidovre",
    "VEJLE": "Vejle",
    "FREDERICIA": "FC Fredericia",
    "SONDERJYSKE": "SonderjyskE",
}

CANONICAL_TO_ODDS_API_MLS: dict[str, str] = {
    "ATLANTA_UNITED": "Atlanta United FC",
    "AUSTIN": "Austin FC",
    "CHARLOTTE": "Charlotte FC",
    "CHICAGO_FIRE": "Chicago Fire FC",
    "CINCINNATI": "FC Cincinnati",
    "COLORADO_RAPIDS": "Colorado Rapids",
    "COLUMBUS_CREW": "Columbus Crew",
    "DC_UNITED": "D.C. United",
    "DALLAS": "FC Dallas",
    "HOUSTON_DYNAMO": "Houston Dynamo FC",
    "INTER_MIAMI": "Inter Miami CF",
    "LA_GALAXY": "LA Galaxy",
    "LAFC": "Los Angeles FC",
    "MINNESOTA_UNITED": "Minnesota United FC",
    "MONTREAL": "CF Montréal",
    "NASHVILLE": "Nashville SC",
    "NEW_ENGLAND_REVOLUTION": "New England Revolution",
    "NEW_YORK_RED_BULLS": "New York Red Bulls",
    "NYCFC": "New York City FC",
    "ORLANDO_CITY": "Orlando City SC",
    "PHILADELPHIA_UNION": "Philadelphia Union",
    "PORTLAND_TIMBERS": "Portland Timbers",
    "REAL_SALT_LAKE": "Real Salt Lake",
    "SAN_DIEGO": "San Diego FC",
    "SAN_JOSE_EARTHQUAKES": "San Jose Earthquakes",
    "SEATTLE_SOUNDERS": "Seattle Sounders FC",
    "SPORTING_KC": "Sporting Kansas City",
    "ST_LOUIS_CITY": "St. Louis City SC",
    "TORONTO": "Toronto FC",
    "VANCOUVER_WHITECAPS": "Vancouver Whitecaps FC",
}

CANONICAL_TO_ODDS_API_AUSTRIAN_BUNDESLIGA: dict[str, str] = {
    "RB_SALZBURG": "Red Bull Salzburg",
    "STURM_GRAZ": "SK Sturm Graz",
    "AUSTRIA_WIEN": "Austria Wien",
    "RAPID_WIEN": "Rapid Wien",
    "WOLFSBERGER": "Wolfsberger AC",
    "HARTBERG": "Hartberg",
    "LASK": "LASK",
    "ALTACH": "SCR Altach",
    "AUSTRIA_KLAGENFURT": "Austria Klagenfurt",
    "BLAU_WEISS_LINZ": "FC Blau-Weiss Linz",
    "GRAZER_AK": "Grazer AK",
}

CANONICAL_TO_ODDS_API_ELITESERIEN: dict[str, str] = {
    "BODO_GLIMT": "FK Bodo/Glimt",
    "MOLDE": "Molde FK",
    "ROSENBORG": "Rosenborg BK",
    "BRANN": "SK Brann",
    "VIKING": "Viking FK",
    "FREDRIKSTAD": "Fredrikstad FK",
    "KFUM_OSLO": "KFUM",
    "SARPSBORG": "Sarpsborg FK",
    "TROMSO": "Tromso IL",
    "LILLESTROM": "Lillestrom SK",
    "HAUGESUND": "FK Haugesund",
    "SANDEFJORD": "Sandefjord",
    "STROMSGODSET": "Stromsgodset IF",
    "KRISTIANSUND": "Kristiansund BK",
    "HAMKAM": "HamKam",
    "ODD": "Odd",
    "VALERENGA": "Vålerenga",
}

CANONICAL_TO_ODDS_API_SWISS_SUPER_LEAGUE: dict[str, str] = {
    "YOUNG_BOYS": "BSC Young Boys",
    "FC_BASEL": "FC Basel",
    "FC_ZURICH": "FC Zurich",
    "SERVETTE": "Servette FC",
    "LUGANO": "FC Lugano",
    "ST_GALLEN": "FC St. Gallen",
    "FC_LAUSANNE": "FC Lausanne-Sport",
    "GRASSHOPPERS": "Grasshoppers",
    "LUZERN": "FC Luzern",
    "WINTERTHUR": "FC Winterthur",
    "SION": "FC Sion",
    "YVERDON": "Yverdon-Sport FC",
}

CANONICAL_TO_ODDS_API_SCOTTISH_PREMIERSHIP: dict[str, str] = {
    "CELTIC": "Celtic",
    "RANGERS": "Rangers",
    "ABERDEEN": "Aberdeen",
    "HEARTS": "Hearts",
    "HIBERNIAN": "Hibernian",
    "DUNDEE": "Dundee FC",
    "DUNDEE_UNITED": "Dundee United",
    "KILMARNOCK": "Kilmarnock",
    "MOTHERWELL": "Motherwell",
    "ST_MIRREN": "St. Mirren",
    "ST_JOHNSTONE": "St. Johnstone",
    "ROSS_COUNTY": "Ross County",
}

CANONICAL_TO_ODDS_API_A_LEAGUE: dict[str, str] = {
    "MELBOURNE_VICTORY": "Melbourne Victory",
    "MELBOURNE_CITY": "Melbourne City FC",
    "SYDNEY_FC": "Sydney FC",
    "WESTERN_SYDNEY": "Western Sydney Wanderers",
    "CENTRAL_COAST_MARINERS": "Central Coast Mariners",
    "NEWCASTLE_JETS": "Newcastle Jets FC",
    "PERTH_GLORY": "Perth Glory",
    "ADELAIDE_UNITED": "Adelaide United",
    "WELLINGTON_PHOENIX": "Wellington Phoenix",
    "BRISBANE_ROAR": "Brisbane Roar",
    "MACARTHUR": "Macarthur FC",
    "WESTERN_UNITED": "Western United FC",
    "AUCKLAND": "Auckland FC",
}

CANONICAL_TO_ODDS_API_LIGA_MX: dict[str, str] = {
    "CLUB_AMERICA": "América",
    "GUADALAJARA": "Guadalajara",
    "CRUZ_AZUL": "Cruz Azul",
    "PUMAS_UNAM": "Pumas",
    "TIGRES": "Tigres",
    "MONTERREY": "Monterrey",
    "SANTOS_LAGUNA": "Santos Laguna",
    "LEON": "Leon",
    "TOLUCA": "Toluca",
    "PACHUCA": "Pachuca",
    "ATLAS": "Atlas",
    "QUERETARO": "Queretaro",
    "PUEBLA": "Puebla",
    "NECAXA": "Necaxa",
    "MAZATLAN": "Mazatlan",
    "JUAREZ": "Juarez",
    "TIJUANA": "Tijuana",
    "SAN_LUIS": "Atletico San Luis",
}

CANONICAL_TO_ODDS_API_ARGENTINA_PRIMERA: dict[str, str] = {
    "BOCA_JUNIORS": "Boca Juniors",
    "RIVER_PLATE": "River Plate",
    "RACING_CLUB": "Racing Club",
    "INDEPENDIENTE": "Independiente",
    "SAN_LORENZO": "San Lorenzo",
    "VELEZ_SARSFIELD": "Velez Sarsfield",
    "ESTUDIANTES": "Estudiantes",
    "LANUS": "Lanus",
    "TALLERES": "Talleres Cordoba",
    "BELGRANO": "Belgrano de Cordoba",
    "SARMIENTO": "Sarmiento de Junin",
    "ALDOSIVI": "Aldosivi Mar del Plata",
    "INSTITUTO": "Instituto de Córdoba",
    "DEFENSA_JUSTICIA": "Defensa y Justicia",
    "ARGENTINOS_JUNIORS": "Argentinos Juniors",
    "BANFIELD": "Banfield",
    "CENTRAL_CORDOBA": "Central Cordoba",
    "COLON": "Colon",
    "GODOY_CRUZ": "Godoy Cruz",
    "HURACAN": "Huracan",
    "NEWELLS_OLD_BOYS": "Newell's Old Boys",
    "PLATENSE": "Platense",
    "ROSARIO_CENTRAL": "Rosario Central",
    "TIGRE": "Tigre",
    "UNION_SANTA_FE": "Union",
    "ESTUDIANTES_RIO_CUARTO": "Estudiantes de Río Cuarto",
}

CANONICAL_TO_ODDS_API_BRASILEIRAO: dict[str, str] = {
    "FLAMENGO": "Flamengo",
    "PALMEIRAS": "Palmeiras",
    "GREMIO": "Grêmio",
    "INTERNACIONAL": "Internacional",
    "ATHLETICO_PARANAENSE": "Athletico-PR",
    "FLUMINENSE": "Fluminense",
    "CORINTHIANS": "Corinthians",
    "SAO_PAULO": "Sao Paulo",
    "SANTOS": "Santos",
    "BOTAFOGO": "Botafogo",
    "VASCO_DA_GAMA": "Vasco da Gama",
    "CRUZEIRO": "Cruzeiro",
    "ATLETICO_MINEIRO": "Atletico Mineiro",
    "BAHIA": "Bahia",
    "FORTALEZA": "Fortaleza",
    "CEARA": "Ceara",
    "GOIAS": "Goias",
    "CORITIBA": "Coritiba",
    "CHAPECOENSE": "Chapecoense",
    "JUVENTUDE": "Juventude",
    "CUIABA": "Cuiaba",
    "AMERICA_MINEIRO": "America Mineiro",
    "BRAGANTINO": "Bragantino",
    "VITORIA": "Vitoria",
    "CRICIUMA": "Criciuma",
    "MIRASSOL": "Mirassol",
    "REMO": "Remo",
}

CANONICAL_TO_ODDS_API_GREEK_SUPER_LEAGUE: dict[str, str] = {
    "OLYMPIAKOS": "Olympiakos Piraeus",
    "PANATHINAIKOS": "Panathinaikos",
    "AEK_ATHENS": "AEK Athens",
    "PAOK": "PAOK Thessaloniki",
    "ARIS": "Aris Thessaloniki",
    "OFI": "OFI Crete",
    "ATROMITOS": "Atromitos Athens",
    "VOLOS": "Volos FC",
    "PANETOLIKOS": "Panetolikos Agrinio",
    "PANSERRAIKOS": "Panserraikos FC",
    "AEL": "AEL",
    "LAMIA": "Lamia",
    "ASTERAS_TRIPOLIS": "Asteras Tripolis",
    "IONIKOS": "Ionikos",
    "LEVADIAKOS": "Levadiakos",
    "GIANNINA": "PAS Giannina",
    "KIFISIA": "AE Kifisia FC",
}

CANONICAL_TO_ODDS_API_EKSTRAKLASA: dict[str, str] = {
    "LEGIA_WARSAW": "Legia Warsaw",
    "LECH_POZNAN": "Lech Poznań",
    "RAKOW": "Rakow Czestochowa",
    "JAGIELLONIA": "Jagiellonia Bialystok",
    "POGON_SZCZECIN": "Pogon Szczecin",
    "SLASK_WROCLAW": "Slask Wroclaw",
    "WIDZEW_LODZ": "Widzew Łódź",
    "GORNIK_ZABRZE": "Górnik Zabrze",
    "CRACOVIA": "Cracovia",
    "PIAST_GLIWICE": "Piast Gliwice",
    "WARTA_POZNAN": "Warta Poznan",
    "ZAGLEBIE_LUBIN": "Zaglebie Lubin",
    "STAL_MIELEC": "Stal Mielec",
    "KORONA_KIELCE": "Korona Kielce",
    "MOTOR_LUBLIN": "Motor Lublin",
    "RADOMIAK": "Radomiak Radom",
    "NIECIECZA": "Nieciecza",
    "ARKA_GDYNIA": "Arka Gdynia",
}

CANONICAL_TO_ODDS_API_SUPER_LIG: dict[str, str] = {
    "GALATASARAY": "Galatasaray",
    "FENERBAHCE": "Fenerbahce",
    "BESIKTAS": "Besiktas",
    "TRABZONSPOR": "Trabzonspor",
    "ISTANBUL_BASAKSEHIR": "Istanbul Basaksehir",
    "ANTALYASPOR": "Antalyaspor",
    "ADANA_DEMIRSPOR": "Adana Demirspor",
    "KONYASPOR": "Konyaspor",
    "SIVASSPOR": "Sivasspor",
    "ALANYASPOR": "Alanyaspor",
    "GAZIANTEP": "Gaziantep",
    "KAYSERISPOR": "Kayserispor",
    "KASIMPASA": "Kasimpasa",
    "SAMSUNSPOR": "Samsunspor",
    "EYUPSPOR": "Eyupspor",
    "BODRUMSPOR": "Bodrumspor",
    "GOZTEPE": "Goztepe",
}

CANONICAL_TO_ODDS_API_ALLSVENSKAN: dict[str, str] = {
    "MALMO": "Malmo FF",
    "AIK": "AIK",
    "DJURGARDEN": "Djurgardens IF",
    "HAMMARBY": "Hammarby",
    "IFK_GOTEBORG": "IFK Gothenburg",
    "ELFSBORG": "IF Elfsborg",
    "NORRKOPING": "IFK Norrkoping",
    "HACKEN": "BK Hacken",
    "SIRIUS": "IK Sirius",
    "HALMSTAD": "Halmstad",
    "KALMAR": "Kalmar FF",
}

CANONICAL_TO_ODDS_API_J1_LEAGUE: dict[str, str] = {
    "VISSEL_KOBE": "Vissel Kobe",
    "YOKOHAMA_F_MARINOS": "Yokohama F. Marinos",
    "KAWASAKI_FRONTALE": "Kawasaki Frontale",
    "URAWA_REDS": "Urawa Red Diamonds",
    "KASHIMA_ANTLERS": "Kashima Antlers",
    "FC_TOKYO": "FC Tokyo",
    "NAGOYA_GRAMPUS": "Nagoya Grampus",
    "SANFRECCE_HIROSHIMA": "Sanfrecce Hiroshima",
    "CEREZO_OSAKA": "Cerezo Osaka",
    "GAMBA_OSAKA": "Gamba Osaka",
    "CONSADOLE_SAPPORO": "Consadole Sapporo",
    "SAGAN_TOSU": "Sagan Tosu",
    "MACHIDA_ZELVIA": "Machida Zelvia",
    "AVISPA_FUKUOKA": "Avispa Fukuoka",
    "ALBIREX_NIIGATA": "Albirex Niigata",
    "TOKYO_VERDY": "Tokyo Verdy",
    "JUBILO_IWATA": "Jubilo Iwata",
    "KASHIWA_REYSOL": "Kashiwa Reysol",
}

CANONICAL_TO_ODDS_API_K_LEAGUE_1: dict[str, str] = {
    "ULSAN_HD": "Ulsan HD FC",
    "JEONBUK": "Jeonbuk",
    "POHANG_STEELERS": "Pohang Steelers",
    "INCHEON_UNITED": "Incheon United",
    "SUWON_BLUEWINGS": "Suwon Bluewings",
    "DAEJEON_CITIZEN": "Daejeon Citizen",
    "DAEGU": "Daegu FC",
    "GWANGJU": "Gwangju FC",
    "GANGWON": "Gangwon FC",
    "FC_SEOUL": "FC Seoul",
    "JEJU_UNITED": "Jeju United",
    "GIMCHEON_SANGMU": "Gimcheon Sangmu",
}

CANONICAL_TO_ODDS_API_CHILE_PRIMERA: dict[str, str] = {
    "COLO_COLO": "Colo-Colo",
    "UNIVERSIDAD_DE_CHILE": "Universidad de Chile",
    "UNIVERSIDAD_CATOLICA": "Universidad Catolica",
    "COBRELOA": "Cobreloa",
    "HUACHIPATO": "Huachipato",
    "UNION_ESPANOLA": "Union Espanola",
    "COBRESAL": "Cobresal",
    "AUDAX_ITALIANO": "Audax Italiano",
    "OHIGGINS": "O'Higgins",
    "PALESTINO": "Palestino",
    "EVERTON_CHILE": "Everton de Vina del Mar",
    "CURICO_UNIDO": "Curico Unido",
    "NUBLENSE": "Nublense",
    "IQUIQUE": "Iquique",
    "LA_CALERA": "La Calera",
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


# ---------------------------------------------------------------------------
# League ID → CANONICAL_TO_ODDS_API_* dict mapping (API-Football league IDs)
# ---------------------------------------------------------------------------

_LEAGUE_ID_TO_ODDS_API_DICT: dict[int, dict[str, str]] = {
    39: CANONICAL_TO_ODDS_API_EPL,
    40: CANONICAL_TO_ODDS_API_ENG_CHAMPIONSHIP,
    41: CANONICAL_TO_ODDS_API_ENG_LEAGUE_ONE,
    42: CANONICAL_TO_ODDS_API_ENG_LEAGUE_TWO,
    78: CANONICAL_TO_ODDS_API_BUNDESLIGA,
    79: CANONICAL_TO_ODDS_API_BUNDESLIGA,  # 2. Bundesliga
    80: CANONICAL_TO_ODDS_API_LIGA_3,
    140: CANONICAL_TO_ODDS_API_LA_LIGA,
    141: CANONICAL_TO_ODDS_API_LA_LIGA,  # Segunda
    135: CANONICAL_TO_ODDS_API_SERIE_A,
    136: CANONICAL_TO_ODDS_API_SERIE_A,  # Serie B
    61: CANONICAL_TO_ODDS_API_LIGUE_1,
    62: CANONICAL_TO_ODDS_API_LIGUE_1,  # Ligue 2
    88: CANONICAL_TO_ODDS_API_EREDIVISIE,
    94: CANONICAL_TO_ODDS_API_PRIMEIRA_LIGA,
    144: CANONICAL_TO_ODDS_API_JUPILER_PRO,
    119: CANONICAL_TO_ODDS_API_DANISH_SUPERLIGA,
    253: CANONICAL_TO_ODDS_API_MLS,
    218: CANONICAL_TO_ODDS_API_AUSTRIAN_BUNDESLIGA,
    103: CANONICAL_TO_ODDS_API_ELITESERIEN,
    207: CANONICAL_TO_ODDS_API_SWISS_SUPER_LEAGUE,
    179: CANONICAL_TO_ODDS_API_SCOTTISH_PREMIERSHIP,
    188: CANONICAL_TO_ODDS_API_A_LEAGUE,
    262: CANONICAL_TO_ODDS_API_LIGA_MX,
    128: CANONICAL_TO_ODDS_API_ARGENTINA_PRIMERA,
    71: CANONICAL_TO_ODDS_API_BRASILEIRAO,
    197: CANONICAL_TO_ODDS_API_GREEK_SUPER_LEAGUE,
    106: CANONICAL_TO_ODDS_API_EKSTRAKLASA,
    203: CANONICAL_TO_ODDS_API_SUPER_LIG,
    113: CANONICAL_TO_ODDS_API_ALLSVENSKAN,
    98: CANONICAL_TO_ODDS_API_J1_LEAGUE,
    292: CANONICAL_TO_ODDS_API_K_LEAGUE_1,
    265: CANONICAL_TO_ODDS_API_CHILE_PRIMERA,
}

# Combined lookup across all leagues (for fallback)
_ALL_ODDS_API: dict[str, str] = {}
for _d in _LEAGUE_ID_TO_ODDS_API_DICT.values():
    _ALL_ODDS_API.update(_d)


def get_odds_api_team_name(canonical_name: str, api_football_league_id: int) -> str | None:
    """Convert canonical team ID to OddsAPI display name.

    Args:
        canonical_name: Canonical team ID (e.g. ``"MAN_UNITED"``).
        api_football_league_id: API-Football league ID (39 = EPL, 78 = Bundesliga, etc.).

    Returns:
        OddsAPI display name (e.g. ``"Manchester United"``) or ``None`` if not found.
    """
    # Try league-specific dict first
    league_dict = _LEAGUE_ID_TO_ODDS_API_DICT.get(api_football_league_id)
    if league_dict is not None:
        result = league_dict.get(canonical_name)
        if result is not None:
            return result
    # Fall back to combined dict across all leagues
    return _ALL_ODDS_API.get(canonical_name)


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
    "CANONICAL_TO_ODDS_API_ALLSVENSKAN",
    "CANONICAL_TO_ODDS_API_ARGENTINA_PRIMERA",
    "CANONICAL_TO_ODDS_API_AUSTRIAN_BUNDESLIGA",
    "CANONICAL_TO_ODDS_API_A_LEAGUE",
    "CANONICAL_TO_ODDS_API_BRASILEIRAO",
    "CANONICAL_TO_ODDS_API_BUNDESLIGA",
    "CANONICAL_TO_ODDS_API_CHILE_PRIMERA",
    "CANONICAL_TO_ODDS_API_DANISH_SUPERLIGA",
    "CANONICAL_TO_ODDS_API_EKSTRAKLASA",
    "CANONICAL_TO_ODDS_API_ELITESERIEN",
    "CANONICAL_TO_ODDS_API_ENG_CHAMPIONSHIP",
    "CANONICAL_TO_ODDS_API_ENG_LEAGUE_ONE",
    "CANONICAL_TO_ODDS_API_ENG_LEAGUE_TWO",
    "CANONICAL_TO_ODDS_API_EPL",
    "CANONICAL_TO_ODDS_API_EREDIVISIE",
    "CANONICAL_TO_ODDS_API_GREEK_SUPER_LEAGUE",
    "CANONICAL_TO_ODDS_API_J1_LEAGUE",
    "CANONICAL_TO_ODDS_API_JUPILER_PRO",
    "CANONICAL_TO_ODDS_API_K_LEAGUE_1",
    "CANONICAL_TO_ODDS_API_LA_LIGA",
    "CANONICAL_TO_ODDS_API_LIGA_3",
    "CANONICAL_TO_ODDS_API_LIGA_MX",
    "CANONICAL_TO_ODDS_API_LIGUE_1",
    "CANONICAL_TO_ODDS_API_MLS",
    "CANONICAL_TO_ODDS_API_PRIMEIRA_LIGA",
    "CANONICAL_TO_ODDS_API_SCOTTISH_PREMIERSHIP",
    "CANONICAL_TO_ODDS_API_SERIE_A",
    "CANONICAL_TO_ODDS_API_SUPER_LIG",
    "CANONICAL_TO_ODDS_API_SWISS_SUPER_LEAGUE",
    "CANONICAL_TO_UNDERSTAT_BUNDESLIGA",
    "CANONICAL_TO_UNDERSTAT_EPL",
    "get_odds_api_team_name",
    "get_understat_team_name",
]
