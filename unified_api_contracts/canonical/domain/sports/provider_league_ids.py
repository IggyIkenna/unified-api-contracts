"""Cross-provider league ID mappings for prediction leagues.

Maps canonical league IDs to provider-specific league identifiers.
Keyed by UAC LEAGUE_REGISTRY canonical league_id (e.g. "EPL").

Stability:
  - SOCCER_FOOTBALL_INFO_IDS: Stable (hex, doesn't change per season)
  - TRANSFERMARKT_IDS: Stable (short code, doesn't change per season)
  - UNDERSTAT_NAMES: Stable (5 leagues only, fixed strings)
  - FOOTYSTATS_IDS: CHANGES EVERY SEASON. Current values are for the
    2025 season. Must be refreshed each season via FootyStats /league-list.

Source: Ported from archived new-sports-batting-services
extra/league_classification_config.py + mapping/leagues.csv
"""

from __future__ import annotations

# Soccer-Football-Info championship IDs (stable hex, never changes)
SOCCER_FOOTBALL_INFO_IDS: dict[str, str] = {
    "ALLSVENSKAN": "5c67de1074b5a814",
    "ARGENTINA_PRIMERA": "3ba90aa17a307ae4",
    "AUSTRIAN_BUNDESLIGA": "826950098c1cb000",
    "A_LEAGUE": "8407bfa398b058ea",
    "BRASILEIRAO": "59fb92dcf842d738",
    "BUNDESLIGA": "a0d28d6b99d45e79",
    "BUNDESLIGA_2": "3a625640737668e1",
    "CHILE_PRIMERA": "43de84fef5ca092b",
    "DANISH_SUPERLIGA": "f12fb762acaae78b",
    "EKSTRAKLASA": "a82c7ffdce9b4912",
    "ELITESERIEN": "1a8afb27a4db853c",
    "ENG_CHAMPIONSHIP": "d463240b9b236077",
    "ENG_LEAGUE_ONE": "96860b92d421df21",
    "ENG_LEAGUE_TWO": "d90bcc42d24aaf4c",
    "EPL": "eb57e70ef2e7077e",
    "EREDIVISIE": "2713cd487a76d83a",
    "GREEK_SUPER_LEAGUE": "ce970d0823edec4d",
    "J1_LEAGUE": "cc5f9e51bd5cfffe",
    "JUPILER_PRO": "d5dd4e8a0a877908",
    "K_LEAGUE_1": "2af0ce4164de30b4",
    "LA_LIGA": "4809e54e02cc5630",
    "LIGA_3": "5812be929121305a",
    "LIGA_MX": "d4cd47172b514da3",
    "LIGUE_1": "f0644ed72e7c6a5c",
    "LIGUE_2": "6b2fcdc884329586",
    "MLS": "bdc26311f38963da",
    "PRIMEIRA_LIGA": "f8fd56a0150c50eb",
    "SCOTTISH_PREMIERSHIP": "7644713f59fb0c61",
    "SEGUNDA_DIVISION": "f5e5596b0efdef8e",
    "SERIE_A": "52df5453a0628c0a",
    "SERIE_B": "7343482548e0674b",
    "SUPER_LIG": "5359506f8b7705a4",
    "SWISS_SUPER_LEAGUE": "1dd08ad826affff0",
}

# Transfermarkt league codes (stable, never changes)
TRANSFERMARKT_IDS: dict[str, str] = {
    "ALLSVENSKAN": "SE1",
    "ARGENTINA_PRIMERA": "ARGC",
    "AUSTRIAN_BUNDESLIGA": "A1",
    "A_LEAGUE": "AUS1",
    "BRASILEIRAO": "BRA1",
    "BUNDESLIGA": "L1",
    "BUNDESLIGA_2": "L2",
    "CHILE_PRIMERA": "CLPD",
    "DANISH_SUPERLIGA": "DK1",
    "EKSTRAKLASA": "PL1",
    "ELITESERIEN": "NO1",
    "ENG_CHAMPIONSHIP": "GB2",
    "ENG_LEAGUE_ONE": "GB3",
    "ENG_LEAGUE_TWO": "GB4",
    "EPL": "GB1",
    "EREDIVISIE": "NL1",
    "J1_LEAGUE": "JAP1",
    "JUPILER_PRO": "BE1",
    "K_LEAGUE_1": "RSK1",
    "LA_LIGA": "ES1",
    "LIGA_3": "L3",
    "LIGA_MX": "MEXA",
    "LIGUE_1": "FR1",
    "LIGUE_2": "FR2",
    "MLS": "MLS1",
    "PRIMEIRA_LIGA": "PO1",
    "SCOTTISH_PREMIERSHIP": "SC1",
    "SEGUNDA_DIVISION": "ES2",
    "SERIE_A": "IT1",
    "SERIE_B": "IT2",
    "SUPER_LIG": "TR1",
    "SWISS_SUPER_LEAGUE": "C1",
}

# Understat league names (stable, only 5 leagues covered)
UNDERSTAT_NAMES: dict[str, str] = {
    "BUNDESLIGA": "Bundesliga",
    "EPL": "EPL",
    "LA_LIGA": "La_Liga",
    "LIGUE_1": "Ligue_1",
    "SERIE_A": "Serie_A",
}

# FootyStats season IDs — CHANGES EVERY SEASON
# These are for the 2025 season (current as of March 2026).
# Refresh by calling FootyStats /league-list at season start.
FOOTYSTATS_SEASON_IDS: dict[str, int] = {
    "ALLSVENSKAN": 16263,
    "ARGENTINA_PRIMERA": 15746,
    "AUSTRIAN_BUNDESLIGA": 14923,
    "BRASILEIRAO": 14231,
    "BUNDESLIGA": 14968,
    "BUNDESLIGA_2": 14931,
    "CHILE_PRIMERA": 14116,
    "DANISH_SUPERLIGA": 15055,
    "EKSTRAKLASA": 15031,
    "ELITESERIEN": 16260,
    "ENG_CHAMPIONSHIP": 14930,
    "ENG_LEAGUE_ONE": 14934,
    "ENG_LEAGUE_TWO": 14935,
    "EPL": 15050,
    "EREDIVISIE": 14936,
    "GREEK_SUPER_LEAGUE": 15163,
    "J1_LEAGUE": 16242,
    "JUPILER_PRO": 14937,
    "K_LEAGUE_1": 16243,
    "LA_LIGA": 14956,
    "LIGA_3": 14977,
    "LIGA_MX": 15234,
    "LIGUE_1": 14932,
    "LIGUE_2": 14954,
    "MLS": 13973,
    "PRIMEIRA_LIGA": 15115,
    "SCOTTISH_PREMIERSHIP": 15000,
    "SEGUNDA_DIVISION": 15066,
    "SERIE_A": 15068,
    "SERIE_B": 15632,
    "SUPER_LIG": 14972,
    "SWISS_SUPER_LEAGUE": 15047,
}


# Polymarket series slugs — CHANGES EVERY SEASON (year-suffixed)
# Current values are for the 2025 season. Polymarket appends the year
# to the slug (e.g. "premier-league-2025"). Refresh when season rolls over.
POLYMARKET_SERIES_SLUGS: dict[str, str] = {
    "ALLSVENSKAN": "allsvenskan-2025",
    "ARGENTINA_PRIMERA": "argentina-primera-division-2025",
    "AUSTRIAN_BUNDESLIGA": "austrian-bundesliga-2025",
    "A_LEAGUE": "a-league-2025",
    "BRASILEIRAO": "brazil-serie-a",
    "BUNDESLIGA": "bundesliga-2025",
    "BUNDESLIGA_2": "bundesliga-2",
    "DANISH_SUPERLIGA": "danish-superliga-2025",
    "EKSTRAKLASA": "ekstraklasa-2025",
    "ELITESERIEN": "eliteserien-2025",
    "ENG_CHAMPIONSHIP": "efl-championship",
    "EPL": "premier-league-2025",
    "EREDIVISIE": "eredivisie-2025",
    "GREEK_SUPER_LEAGUE": "greek-super-league-2025",
    "JUPILER_PRO": "jupiler-pro-league-2025",
    "LA_LIGA": "la-liga-2025",
    "LIGA_MX": "liga-mx-2025",
    "LIGUE_1": "ligue-1-2025",
    "LIGUE_2": "ligue-2-2025",
    "MLS": "mls-2025",
    "PRIMEIRA_LIGA": "primeira-liga-2025",
    "SCOTTISH_PREMIERSHIP": "scottish-premiership-2025",
    "SEGUNDA_DIVISION": "la-liga-2",
    "SERIE_A": "serie-a-2025",
    "SERIE_B": "serie-b-2025",
    "SUPER_LIG": "super-lig-2025",
    "SWISS_SUPER_LEAGUE": "swiss-super-league-2025",
}

# Odds API display league names → canonical league IDs
# Used to join V3 odds data (which uses display names in the GCS path)
# with canonical IDs used everywhere else in the system.
ODDS_API_DISPLAY_TO_CANONICAL: dict[str, str] = {
    "Premier League": "EPL",
    "Championship": "ENG_CHAMPIONSHIP",
    "League One": "ENG_LEAGUE_ONE",
    "League Two": "ENG_LEAGUE_TWO",
    "La Liga": "LA_LIGA",
    "La Liga 2": "SEGUNDA_DIVISION",
    "Bundesliga": "BUNDESLIGA",
    "2. Bundesliga": "BUNDESLIGA_2",
    "3. Liga": "LIGA_3",
    "Serie A": "SERIE_A",
    "Serie B": "SERIE_B",
    "Ligue 1": "LIGUE_1",
    "Ligue 2": "LIGUE_2",
    "Eredivisie": "EREDIVISIE",
    "Primeira Liga": "PRIMEIRA_LIGA",
    "Jupiler Pro League": "JUPILER_PRO",
    "Super Lig": "SUPER_LIG",
    "Süper Lig": "SUPER_LIG",
    "Super League": "SWISS_SUPER_LEAGUE",
    "Greek Super League": "GREEK_SUPER_LEAGUE",
    "Premiership": "SCOTTISH_PREMIERSHIP",
    "Danish Superliga": "DANISH_SUPERLIGA",
    "Eliteserien": "ELITESERIEN",
    "Allsvenskan": "ALLSVENSKAN",
    "Austrian Bundesliga": "AUSTRIAN_BUNDESLIGA",
    "Ekstraklasa": "EKSTRAKLASA",
    "MLS": "MLS",
    "Liga MX": "LIGA_MX",
    "Primera Division": "ARGENTINA_PRIMERA",
    "Brasileirão": "BRASILEIRAO",
    "A-League": "A_LEAGUE",
    "J1 League": "J1_LEAGUE",
    "K League 1": "K_LEAGUE_1",
    "Chile Primera División": "CHILE_PRIMERA",
}

# Reverse lookup: canonical → Odds API display name
_CANONICAL_TO_ODDS_API_DISPLAY: dict[str, str] = {v: k for k, v in ODDS_API_DISPLAY_TO_CANONICAL.items()}


def get_odds_api_display_league(canonical_league_id: str) -> str | None:
    """Get the Odds API display league name from a canonical league ID."""
    return _CANONICAL_TO_ODDS_API_DISPLAY.get(canonical_league_id)


def get_provider_league_id(canonical_league_id: str, provider: str) -> str | int | None:
    """Look up a provider-specific league ID from canonical league ID.

    Args:
        canonical_league_id: UAC league key (e.g. "EPL")
        provider: Provider name — "soccer_football_info", "transfermarkt",
                  "understat", "footystats"

    Returns:
        Provider-specific ID, or None if not mapped.
    """
    if provider == "soccer_football_info":
        return SOCCER_FOOTBALL_INFO_IDS.get(canonical_league_id)
    if provider == "transfermarkt":
        return TRANSFERMARKT_IDS.get(canonical_league_id)
    if provider == "understat":
        return UNDERSTAT_NAMES.get(canonical_league_id)
    if provider == "footystats":
        return FOOTYSTATS_SEASON_IDS.get(canonical_league_id)
    if provider == "polymarket":
        return POLYMARKET_SERIES_SLUGS.get(canonical_league_id)
    if provider == "odds_api":
        return _CANONICAL_TO_ODDS_API_DISPLAY.get(canonical_league_id)
    return None
