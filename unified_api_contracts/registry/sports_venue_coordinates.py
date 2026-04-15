"""Static venue coordinates for football stadiums — SSOT for weather data.

API Football's /teams endpoint returns venue metadata (name, city, capacity,
surface) but NOT geographic coordinates. This registry provides lat/lon for
major stadiums in the top European leagues so the weather pipeline can fetch
Open-Meteo data without a separate geocoding service.

Keys are SCREAMING_SNAKE_CASE venue IDs (matching ``build_venue_id()`` output).
Values are ``VenueCoordinates`` named tuples with latitude and longitude.

Coverage: EPL, La Liga, Bundesliga, Serie A, Ligue 1 (all 20 teams per league).
"""

from __future__ import annotations

from typing import NamedTuple


class VenueCoordinates(NamedTuple):
    """Geographic coordinates for a football stadium."""

    latitude: float
    longitude: float


# ---------------------------------------------------------------------------
# Premier League (England)
# ---------------------------------------------------------------------------
_EPL: dict[str, VenueCoordinates] = {
    "EMIRATES_STADIUM": VenueCoordinates(51.5549, -0.1084),
    "VILLA_PARK": VenueCoordinates(52.5092, -1.8847),
    "VITALITY_STADIUM": VenueCoordinates(50.7352, -1.8384),
    "AMEX_STADIUM": VenueCoordinates(50.8616, -0.0837),
    "AMERICAN_EXPRESS_COMMUNITY_STADIUM": VenueCoordinates(50.8616, -0.0837),
    "TURF_MOOR": VenueCoordinates(53.7890, -2.2302),
    "STAMFORD_BRIDGE": VenueCoordinates(51.4817, -0.1910),
    "SELHURST_PARK": VenueCoordinates(51.3983, -0.0855),
    "GOODISON_PARK": VenueCoordinates(53.4388, -2.9664),
    "CRAVEN_COTTAGE": VenueCoordinates(51.4749, -0.2217),
    "ELLAND_ROAD": VenueCoordinates(53.7778, -1.5722),
    "KING_POWER_STADIUM": VenueCoordinates(52.6204, -1.1422),
    "ANFIELD": VenueCoordinates(53.4308, -2.9608),
    "ETIHAD_STADIUM": VenueCoordinates(53.4831, -2.2004),
    "OLD_TRAFFORD": VenueCoordinates(53.4631, -2.2913),
    "ST_JAMES_PARK": VenueCoordinates(54.9756, -1.6217),
    "ST_JAMES__PARK": VenueCoordinates(54.9756, -1.6217),
    "CARROW_ROAD": VenueCoordinates(52.6222, 1.3094),
    "ST_MARYS_STADIUM": VenueCoordinates(50.9058, -1.3910),
    "ST_MARY_S_STADIUM": VenueCoordinates(50.9058, -1.3910),
    "TOTTENHAM_HOTSPUR_STADIUM": VenueCoordinates(51.6042, -0.0662),
    "VICARAGE_ROAD": VenueCoordinates(51.6498, -0.4014),
    "LONDON_STADIUM": VenueCoordinates(51.5387, -0.0166),
    "MOLINEUX_STADIUM": VenueCoordinates(52.5903, -2.1306),
    "GTECH_COMMUNITY_STADIUM": VenueCoordinates(51.4907, -0.2887),
    "PORTMAN_ROAD": VenueCoordinates(52.0545, 1.1448),
    "CITY_GROUND": VenueCoordinates(52.9400, -1.1325),
    "KENILWORTH_ROAD": VenueCoordinates(51.8842, -0.4317),
    "KC_STADIUM": VenueCoordinates(53.7463, -0.3681),
    "BRAMALL_LANE": VenueCoordinates(53.3703, -1.4710),
}

# ---------------------------------------------------------------------------
# La Liga (Spain)
# ---------------------------------------------------------------------------
_LA_LIGA: dict[str, VenueCoordinates] = {
    "CAMP_NOU": VenueCoordinates(41.3809, 2.1228),
    "SPOTIFY_CAMP_NOU": VenueCoordinates(41.3809, 2.1228),
    "ESTADI_OLIMPIC_LLUIS_COMPANYS": VenueCoordinates(41.3649, 2.1556),
    "SANTIAGO_BERNABEU": VenueCoordinates(40.4531, -3.6883),
    "ESTADIO_SANTIAGO_BERNABEU": VenueCoordinates(40.4531, -3.6883),
    "CIVITAS_METROPOLITANO": VenueCoordinates(40.4361, -3.5994),
    "ESTADIO_METROPOLITANO": VenueCoordinates(40.4361, -3.5994),
    "WANDA_METROPOLITANO": VenueCoordinates(40.4361, -3.5994),
    "ESTADIO_DE_MESTALLA": VenueCoordinates(39.4745, -0.3583),
    "MESTALLA": VenueCoordinates(39.4745, -0.3583),
    "SAN_MAMES": VenueCoordinates(43.2641, -2.9494),
    "ESTADIO_SAN_MAMES": VenueCoordinates(43.2641, -2.9494),
    "ESTADIO_BENITO_VILLAMARIN": VenueCoordinates(37.3564, -5.9817),
    "BENITO_VILLAMARIN": VenueCoordinates(37.3564, -5.9817),
    "REALE_ARENA": VenueCoordinates(43.3013, -1.9736),
    "ANOETA": VenueCoordinates(43.3013, -1.9736),
    "ESTADIO_DE_LA_CERAMICA": VenueCoordinates(39.9444, -0.1036),
    "LA_CERAMICA": VenueCoordinates(39.9444, -0.1036),
    "RAMON_SANCHEZ_PIZJUAN": VenueCoordinates(37.3841, -5.9706),
    "RCDE_STADIUM": VenueCoordinates(41.3478, 2.0756),
    "ESTADIO_COLISEUM_ALFONSO_PEREZ": VenueCoordinates(40.3258, -3.7147),
    "MONTILIVI": VenueCoordinates(41.9617, 2.8286),
    "ESTADIO_DE_MONTILIVI": VenueCoordinates(41.9617, 2.8286),
    "ESTADIO_RAMON_DE_CARRANZA": VenueCoordinates(36.5008, -6.2700),
    "NUEVO_MIRANDILLA": VenueCoordinates(36.5008, -6.2700),
    "BALAIDOS": VenueCoordinates(42.2117, -8.7392),
    "ABANCA_BALAIDOS": VenueCoordinates(42.2117, -8.7392),
    "MENDIZORROZA": VenueCoordinates(42.8372, -2.6878),
    "ESTADIO_DE_MENDIZORROZA": VenueCoordinates(42.8372, -2.6878),
    "SON_MOIX": VenueCoordinates(39.5900, 2.6300),
    "ESTADIO_SON_MOIX": VenueCoordinates(39.5900, 2.6300),
    "EL_SADAR": VenueCoordinates(42.7964, -1.6367),
    "ESTADIO_EL_SADAR": VenueCoordinates(42.7964, -1.6367),
    "ESTADIO_MUNICIPAL_DE_BUTARQUE": VenueCoordinates(40.3244, -3.7617),
    "ESTADIO_DE_VALLECAS": VenueCoordinates(40.3917, -3.6589),
}

# ---------------------------------------------------------------------------
# Bundesliga (Germany)
# ---------------------------------------------------------------------------
_BUNDESLIGA: dict[str, VenueCoordinates] = {
    "ALLIANZ_ARENA": VenueCoordinates(48.2188, 11.6247),
    "SIGNAL_IDUNA_PARK": VenueCoordinates(51.4926, 7.4518),
    "WESTFALENSTADION": VenueCoordinates(51.4926, 7.4518),
    "VELTINS_ARENA": VenueCoordinates(51.5536, 7.0678),
    "ARENA_AUFSCHALKE": VenueCoordinates(51.5536, 7.0678),
    "RED_BULL_ARENA": VenueCoordinates(51.3458, 12.3481),
    "MERCEDES_BENZ_ARENA": VenueCoordinates(48.7922, 9.2319),
    "MHP_ARENA": VenueCoordinates(48.7922, 9.2319),
    "VOLKSWAGEN_ARENA": VenueCoordinates(52.4319, 10.8039),
    "BORUSSIA_PARK": VenueCoordinates(51.1747, 6.3856),
    "COMMERZBANK_ARENA": VenueCoordinates(50.0686, 8.6456),
    "DEUTSCHE_BANK_PARK": VenueCoordinates(50.0686, 8.6456),
    "OLYMPIASTADION_BERLIN": VenueCoordinates(52.5147, 13.2394),
    "OLYMPIASTADION": VenueCoordinates(52.5147, 13.2394),
    "BAYARENA": VenueCoordinates(51.0383, 7.0022),
    "BAY_ARENA": VenueCoordinates(51.0383, 7.0022),
    "OPEL_ARENA": VenueCoordinates(49.9844, 8.2244),
    "MEWA_ARENA": VenueCoordinates(49.9844, 8.2244),
    "RHEINENERGIESTADION": VenueCoordinates(50.9336, 6.8750),
    "RHEIN_ENERGIE_STADION": VenueCoordinates(50.9336, 6.8750),
    "WWK_ARENA": VenueCoordinates(48.3233, 10.8861),
    "SCHWARZWALD_STADION": VenueCoordinates(47.9892, 7.8536),
    "EUROPA_PARK_STADION": VenueCoordinates(47.9892, 7.8536),
    "PREZERO_ARENA": VenueCoordinates(49.2381, 8.8878),
    "WIRSOL_RHEIN_NECKAR_ARENA": VenueCoordinates(49.2381, 8.8878),
    "VONOVIA_RUHRSTADION": VenueCoordinates(51.4900, 7.2186),
    "STADION_AN_DER_ALTEN_FORSTEREI": VenueCoordinates(52.4572, 13.5678),
    "AN_DER_ALTEN_FORSTEREI": VenueCoordinates(52.4572, 13.5678),
    "WESERSTADION": VenueCoordinates(53.0664, 8.8378),
    "WOHNINVEST_WESERSTADION": VenueCoordinates(53.0664, 8.8378),
    "VOLKSPARKSTADION": VenueCoordinates(53.5872, 9.8986),
    "SCHUCO_ARENA": VenueCoordinates(52.0319, 8.5167),
    "BENTELER_ARENA": VenueCoordinates(51.7142, 8.7406),
}

# ---------------------------------------------------------------------------
# Serie A (Italy)
# ---------------------------------------------------------------------------
_SERIE_A: dict[str, VenueCoordinates] = {
    "STADIO_GIUSEPPE_MEAZZA": VenueCoordinates(45.4781, 9.1240),
    "SAN_SIRO": VenueCoordinates(45.4781, 9.1240),
    "ALLIANZ_STADIUM": VenueCoordinates(45.1097, 7.6411),
    "STADIO_OLIMPICO": VenueCoordinates(41.9340, 12.4547),
    "STADIO_DIEGO_ARMANDO_MARADONA": VenueCoordinates(40.8279, 14.1931),
    "STADIO_SAN_PAOLO": VenueCoordinates(40.8279, 14.1931),
    "GEWISS_STADIUM": VenueCoordinates(45.7089, 9.6808),
    "STADIO_ATLETI_AZZURRI_D_ITALIA": VenueCoordinates(45.7089, 9.6808),
    "MAPEI_STADIUM": VenueCoordinates(44.7144, 10.6494),
    "STADIO_CITTA_DEL_TRICOLORE": VenueCoordinates(44.7144, 10.6494),
    "STADIO_ARTEMIO_FRANCHI": VenueCoordinates(43.7808, 11.2822),
    "STADIO_RENATO_DALL_ARA": VenueCoordinates(44.4922, 11.3097),
    "STADIO_LUIGI_FERRARIS": VenueCoordinates(44.4164, 8.9525),
    "STADIO_MARC_ANTONIO_BENTEGODI": VenueCoordinates(45.4353, 10.9686),
    "STADIO_FRIULI": VenueCoordinates(46.0814, 13.1997),
    "DACIA_ARENA": VenueCoordinates(46.0814, 13.1997),
    "UNIPOL_DOMUS": VenueCoordinates(39.2000, 9.1378),
    "SARDEGNA_ARENA": VenueCoordinates(39.2000, 9.1378),
    "U_POWER_STADIUM": VenueCoordinates(45.5836, 9.2772),
    "STADIO_BRIANTEO": VenueCoordinates(45.5836, 9.2772),
    "STADIO_VIA_DEL_MARE": VenueCoordinates(40.3569, 18.1828),
    "STADIO_ARECHI": VenueCoordinates(40.6594, 14.7975),
    "STADIO_GRANDE_TORINO": VenueCoordinates(45.0419, 7.6497),
    "STADIO_OLIMPICO_GRANDE_TORINO": VenueCoordinates(45.0419, 7.6497),
    "STADIO_ENNIO_TARDINI": VenueCoordinates(44.7956, 10.3381),
    "STADIO_PIER_LUIGI_PENZO": VenueCoordinates(45.4250, 12.3631),
    "STADIO_CARLO_CASTELLANI": VenueCoordinates(43.7261, 10.9494),
    "STADIO_CIRO_VIGORITO": VenueCoordinates(41.1175, 14.7836),
    "STADIO_ALBERTO_PICCO": VenueCoordinates(44.1044, 9.8319),
}

# ---------------------------------------------------------------------------
# Ligue 1 (France)
# ---------------------------------------------------------------------------
_LIGUE_1: dict[str, VenueCoordinates] = {
    "PARC_DES_PRINCES": VenueCoordinates(48.8414, 2.2530),
    "GROUPAMA_STADIUM": VenueCoordinates(45.7653, 4.9822),
    "PARC_OLYMPIQUE_LYONNAIS": VenueCoordinates(45.7653, 4.9822),
    "STADE_VELODROME": VenueCoordinates(43.2697, 5.3956),
    "ORANGE_VELODROME": VenueCoordinates(43.2697, 5.3956),
    "STADE_PIERRE_MAUROY": VenueCoordinates(50.6119, 3.1303),
    "DECATHLON_ARENA": VenueCoordinates(50.6119, 3.1303),
    "ALLIANZ_RIVIERA": VenueCoordinates(43.7050, 7.1925),
    "ROAZHON_PARK": VenueCoordinates(48.1075, -1.7128),
    "STADE_DE_LA_BEAUJOIRE": VenueCoordinates(47.2558, -1.5247),
    "BEAUJOIRE__LOUIS_FONTENEAU": VenueCoordinates(47.2558, -1.5247),
    "STADE_BOLLAERT_DELELIS": VenueCoordinates(50.4328, 2.8153),
    "STADE_FELIX_BOLLAERT": VenueCoordinates(50.4328, 2.8153),
    "STADE_DE_LA_MOSSON": VenueCoordinates(43.6222, 3.8119),
    "STADE_LOUIS_II": VenueCoordinates(43.7275, 7.4153),
    "STADE_AUGUSTE_DELAUNE": VenueCoordinates(49.2469, 3.9931),
    "STADE_AUGUSTE_DELAUNE_II": VenueCoordinates(49.2469, 3.9931),
    "MATMUT_ATLANTIQUE": VenueCoordinates(44.8975, -0.5614),
    "STADE_GEOFFROY_GUICHARD": VenueCoordinates(45.4608, 4.3903),
    "STADE_RAYMOND_KOPA": VenueCoordinates(47.4603, -0.5317),
    "STADE_DE_LA_MEINAU": VenueCoordinates(48.5600, 7.7550),
    "STADE_ABBE_DESCHAMPS": VenueCoordinates(47.7886, 3.5772),
    "STADE_FRANCIS_LE_BLE": VenueCoordinates(48.4033, -4.4622),
    "STADE_GABRIEL_MONTPIED": VenueCoordinates(45.8158, 3.1267),
    "STADE_OCEANE": VenueCoordinates(49.5353, 0.1064),
    "STADE_DU_MOUSTOIR": VenueCoordinates(47.7500, -3.3667),
    "STADE_DE_LA_LICORNE": VenueCoordinates(49.9000, 2.2833),
}

# ---------------------------------------------------------------------------
# Merged registry
# ---------------------------------------------------------------------------

VENUE_COORDINATES: dict[str, VenueCoordinates] = {
    **_EPL,
    **_LA_LIGA,
    **_BUNDESLIGA,
    **_SERIE_A,
    **_LIGUE_1,
}


def get_venue_coordinates(venue_id: str) -> VenueCoordinates | None:
    """Look up coordinates by canonical venue_id (SCREAMING_SNAKE_CASE).

    Returns None if the venue is not in the registry.
    """
    return VENUE_COORDINATES.get(venue_id)
