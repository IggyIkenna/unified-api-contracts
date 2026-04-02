"""API-Football venue/stadium name → canonical stadium ID mappings.

Canonical stadium IDs follow SCREAMING_SNAKE_CASE convention.
Example: ``"Fußball Arena München"`` → ``"ALLIANZ_ARENA"``

Covers Premier League and Bundesliga stadiums (2019-2026).

Source: Ported from footballbets/utils/mapping.py (API_FOOTBALL_TO_CANONICAL_STADIUMS)
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# API-Football stadium display name → canonical stadium ID
# ---------------------------------------------------------------------------

API_FOOTBALL_TO_CANONICAL_STADIUMS: dict[str, str] = {
    # ===================================================================
    # PREMIER LEAGUE STADIUMS
    # ===================================================================
    "Old Trafford": "OLD_TRAFFORD",
    "St. James' Park": "ST_JAMES_PARK",
    "Craven Cottage": "CRAVEN_COTTAGE",
    "Molineux Stadium": "MOLINEUX",
    "Anfield": "ANFIELD",
    "Emirates Stadium": "EMIRATES",
    "Hill Dickinson Stadium": "GOODISON_PARK",  # Everton's stadium (commercial rename)
    "Tottenham Hotspur Stadium": "TOTTENHAM_HOTSPUR_STADIUM",
    "London Stadium": "LONDON_STADIUM",
    "Stamford Bridge": "STAMFORD_BRIDGE",
    "Etihad Stadium": "ETIHAD",
    "St Andrew's Stadium": "ST_ANDREWS",
    "The Hawthorns": "THE_HAWTHORNS",
    "DW Stadium": "DW_STADIUM",
    "Villa Park": "VILLA_PARK",
    "Ewood Park": "EWOOD_PARK",
    "Toughsheet Community Stadium": "UNIVERSITY_OF_BOLTON_STADIUM",
    "bet365 Stadium": "BET365_STADIUM",
    "Stadium of Light": "STADIUM_OF_LIGHT",
    "Bloomfield Road": "BLOOMFIELD_ROAD",
    "Carrow Road": "CARROW_ROAD",
    "MATRADE Loftus Road": "LOFTUS_ROAD",
    "Swansea.com Stadium": "SWANSEA_STADIUM",
    "St. Mary's Stadium": "ST_MARYS",
    "Select Car Leasing Stadium": "MADEJSKI_STADIUM",
    "Cardiff City Stadium": "CARDIFF_CITY_STADIUM",
    "Selhurst Park": "SELHURST_PARK",
    "The MKM Stadium": "MKM_STADIUM",
    "Turf Moor": "TURF_MOOR",
    "King Power Stadium": "KING_POWER_STADIUM",
    "Vitality Stadium": "VITALITY_STADIUM",
    "Vicarage Road": "VICARAGE_ROAD",
    "Riverside Stadium": "RIVERSIDE_STADIUM",
    "John Smith's Stadium": "JOHN_SMITHS_STADIUM",
    "American Express Stadium": "AMEX_STADIUM",
    "Bramall Lane": "BRAMALL_LANE",
    "Elland Road": "ELLAND_ROAD",
    "Gtech Community Stadium": "GTECH_COMMUNITY_STADIUM",
    "The City Ground": "CITY_GROUND",
    "Kenilworth Road": "KENILWORTH_ROAD",
    "Portman Road": "PORTMAN_ROAD",
    "Goodison Park": "GOODISON_PARK",
    # ===================================================================
    # BUNDESLIGA STADIUMS
    # ===================================================================
    "Fußball Arena München": "ALLIANZ_ARENA",
    "Allianz Arena": "ALLIANZ_ARENA",
    "Europa-Park Stadion": "EUROPA_PARK_STADION",
    "Volkswagen Arena": "VOLKSWAGEN_ARENA",
    "wohninvest WESERSTADION": "WESERSTADION",
    "Weserstadion": "WESERSTADION",
    "BORUSSIA-PARK": "BORUSSIA_PARK",
    "Borussia-Park": "BORUSSIA_PARK",
    "MEWA ARENA": "MEWA_ARENA",
    "BVB Stadion Dortmund": "SIGNAL_IDUNA_PARK",
    "Signal Iduna Park": "SIGNAL_IDUNA_PARK",
    "Heinz von Heiden-Arena": "HEINZ_VON_HEIDEN_ARENA",
    "PreZero Arena": "PREZERO_ARENA",
    "BayArena": "BAYARENA",
    "Frankfurt Arena": "DEUTSCHE_BANK_PARK",
    "Deutsche Bank Park": "DEUTSCHE_BANK_PARK",
    "Max-Morlock-Stadion": "MAX_MORLOCK_STADION",
    "Stuttgart Arena": "MERCEDES_BENZ_ARENA",
    "MHPArena": "MERCEDES_BENZ_ARENA",
    "Arena AufSchalke": "VELTINS_ARENA",
    "Veltins-Arena": "VELTINS_ARENA",
    "Volksparkstadion": "VOLKSPARKSTADION",
    "Millerntor-Stadion": "MILLERNTOR_STADION",
    "Cologne Stadium": "RHEINENERGIESTADION",
    "RheinEnergieStadion": "RHEINENERGIESTADION",
    "Fritz-Walter-Stadion": "FRITZ_WALTER_STADION",
    "Olympiastadion Berlin": "OLYMPIASTADION_BERLIN",
    "WWK Arena": "WWK_ARENA",
    "Düsseldorf Arena": "MERKUR_SPIEL_ARENA",
    "Merkur Spiel-Arena": "MERKUR_SPIEL_ARENA",
    "Sportpark Ronhof Thomas Sommer": "SPORTPARK_RONHOF",
    "Eintracht-Stadion": "EINTRACHT_STADION",
    "Home Deluxe Arena": "HOME_DELUXE_ARENA",
    "Merck-Stadion am Böllenfalltor": "MERCK_STADION",
    "Audi-Sportpark": "AUDI_SPORTPARK",
    "Leipzig Stadium": "RED_BULL_ARENA",
    "Red Bull Arena": "RED_BULL_ARENA",
    "Stadion An der Alten Försterei": "AN_DER_ALTEN_FORSTEREI",
    "An der Alten Försterei": "AN_DER_ALTEN_FORSTEREI",
    "Voith-Arena": "VOITH_ARENA",
    "SchücoArena": "SCHUCO_ARENA",
    "Holstein-Stadion": "HOLSTEIN_STADION",
    "Vonovia Ruhrstadion": "VONOVIA_RUHRSTADION",
    "URSAPHARM-Arena an der Kaiserlinde": "URSAPHARM_ARENA",
}


def get_canonical_stadium_name_from_api_football(api_football_stadium: str) -> str | None:
    """Convert API-Football stadium name to canonical stadium ID.

    Args:
        api_football_stadium: Stadium name from API-Football response
            (e.g. ``"Old Trafford"``, ``"Fußball Arena München"``).

    Returns:
        Canonical stadium ID (e.g. ``"OLD_TRAFFORD"``, ``"ALLIANZ_ARENA"``)
        or ``None`` if the name is not in the mapping.
    """
    if not api_football_stadium:
        return None
    return API_FOOTBALL_TO_CANONICAL_STADIUMS.get(api_football_stadium)


__all__ = [
    "API_FOOTBALL_TO_CANONICAL_STADIUMS",
    "get_canonical_stadium_name_from_api_football",
]
