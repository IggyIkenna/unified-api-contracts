"""API-Football team ID to corrected display name mapping.

Maps API-Football numeric ``team_id`` values to the canonical display name
used throughout the system, correcting inconsistencies in the raw API response
(e.g. diacritics, abbreviations, local name variants).

Source: Ported from instruments-service/instruments_service/sports/team_mapping_data_bundesliga.py
(originally from footballbets/utils/team_name_changes.py, 44 entries).
"""

from __future__ import annotations

TEAM_NAME_CORRECTIONS: dict[int, str] = {
    111: "Le Havre",
    157: "Bayern Munich",
    158: "Fortuna Dusseldorf",
    159: "Hertha Berlin",
    163: "Borussia Monchengladbach",
    171: "FC Nurnberg",
    176: "Vfl Bochum",
    177: "Jahn Regensburg",
    178: "SpVgg Greuther Furth",
    179: "FC Magdeburg",
    180: "FC Heidenheim",
    190: "Erzgebirge AUE",
    192: "FC Koln",
    372: "IF Elfsborg",
    397: "FC Midtjylland",
    553: "Olympiakos Piraeus",
    596: "Zenit Saint Petersburg",
    597: "Lokomotiv Moscow",
    621: "FC Krasnodar",
    632: "Universitatea Craiova",
    745: "FC Kaiserslautern",
    784: "FC Wurzburger Kickers",
    870: "Calcio Padova",
    895: "Como",
    1079: "Krylia Sovetov",
    1080: "FC Orenburg",
    1081: "TOM Tomsk",
    1085: "Akhmat Grozny",
    1088: "Dynamo Moscow",
    1313: "Preussen Munster",
    1324: "VfL Osnabruck",
    1325: "Carl Zeiss Jena",
    1620: "FC Viktoria Koln",
    1621: "Rot-weiss Essen",
    1625: "VfB Lubeck",
    1630: "Bremer SV",
    1639: "FC Saarbrucken",
    1652: "SSV Ulm 1846",
    1993: "Fakel Voronezh",
    2012: "PFC Sochi",
    6813: "Dinamo Makhachkala",
    10137: "Nuova Cosenza",
}

__all__ = ["TEAM_NAME_CORRECTIONS"]
