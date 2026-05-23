#!/usr/bin/env python3
"""Detect drift in FOOTYSTATS_SEASON_IDS against the live FootyStats /league-list API.

Called weekly from .github/workflows/weekly-validation.yml. Exits 0 if no drift, 1 if
drift or unmapped new seasons are detected, 2 on error.

Output: JSON dict on stdout with keys:
    drifted            list[{league, old_id, new_id}]
    new_seasons        list[{season_id, name, canonical_guess}]  # not yet in historical map
    missing_from_api   list[str]  # canonical leagues in SEASON_IDS absent from API response
    historical_additions  list[{season_id, canonical}]  # new entries for FOOTYSTATS_HISTORICAL_SEASON_IDS
"""
from __future__ import annotations

import json
import os
import sys

import requests

from unified_api_contracts.canonical.domain.sports.provider_league_ids import (
    FOOTYSTATS_HISTORICAL_SEASON_IDS,
    FOOTYSTATS_SEASON_IDS,
)

_BASE_URL = "https://api.football-data-api.com"

# FootyStats display name → canonical league ID.
# Used to identify new seasons whose IDs are absent from FOOTYSTATS_HISTORICAL_SEASON_IDS.
_FOOTYSTATS_NAME_TO_CANONICAL: dict[str, str] = {
    "England Premier League": "EPL",
    "Premier League": "EPL",
    "Spain La Liga": "LA_LIGA",
    "La Liga": "LA_LIGA",
    "Germany Bundesliga": "BUNDESLIGA",
    "Bundesliga": "BUNDESLIGA",
    "Germany 2. Bundesliga": "BUNDESLIGA_2",
    "2. Bundesliga": "BUNDESLIGA_2",
    "Italy Serie A": "SERIE_A",
    "Serie A": "SERIE_A",
    "France Ligue 1": "LIGUE_1",
    "Ligue 1": "LIGUE_1",
    "France Ligue 2": "LIGUE_2",
    "Ligue 2": "LIGUE_2",
    "Italy Serie B": "SERIE_B",
    "Serie B": "SERIE_B",
    "Netherlands Eredivisie": "EREDIVISIE",
    "Eredivisie": "EREDIVISIE",
    "Belgium Pro League": "JUPILER_PRO",
    "Belgian Pro League": "JUPILER_PRO",
    "Jupiler Pro League": "JUPILER_PRO",
    "England Championship": "ENG_CHAMPIONSHIP",
    "Championship": "ENG_CHAMPIONSHIP",
    "England League One": "ENG_LEAGUE_ONE",
    "League One": "ENG_LEAGUE_ONE",
    "England League Two": "ENG_LEAGUE_TWO",
    "League Two": "ENG_LEAGUE_TWO",
    "Scotland Premiership": "SCOTTISH_PREMIERSHIP",
    "Scottish Premiership": "SCOTTISH_PREMIERSHIP",
    "Portugal Primeira Liga": "PRIMEIRA_LIGA",
    "Primeira Liga": "PRIMEIRA_LIGA",
    "Turkey Super Lig": "SUPER_LIG",
    "Super Lig": "SUPER_LIG",
    "Spain Segunda Division": "SEGUNDA_DIVISION",
    "Spain La Liga 2": "SEGUNDA_DIVISION",
    "La Liga 2": "SEGUNDA_DIVISION",
    "Germany 3. Liga": "LIGA_3",
    "3. Liga": "LIGA_3",
    "Switzerland Super League": "SWISS_SUPER_LEAGUE",
    "Swiss Super League": "SWISS_SUPER_LEAGUE",
    "Greece Super League": "GREEK_SUPER_LEAGUE",
    "Greek Super League": "GREEK_SUPER_LEAGUE",
    "Denmark Superliga": "DANISH_SUPERLIGA",
    "Danish Superliga": "DANISH_SUPERLIGA",
    "Norway Eliteserien": "ELITESERIEN",
    "Eliteserien": "ELITESERIEN",
    "Sweden Allsvenskan": "ALLSVENSKAN",
    "Allsvenskan": "ALLSVENSKAN",
    "Austria Bundesliga": "AUSTRIAN_BUNDESLIGA",
    "Austrian Bundesliga": "AUSTRIAN_BUNDESLIGA",
    "Poland Ekstraklasa": "EKSTRAKLASA",
    "Ekstraklasa": "EKSTRAKLASA",
    "USA MLS": "MLS",
    "MLS": "MLS",
    "Mexico Liga MX": "LIGA_MX",
    "Liga MX": "LIGA_MX",
    "Argentina Primera Division": "ARGENTINA_PRIMERA",
    "Primera Division": "ARGENTINA_PRIMERA",
    "Brazil Serie A": "BRASILEIRAO",
    "Brasileirao": "BRASILEIRAO",
    "Japan J1 League": "J1_LEAGUE",
    "J1 League": "J1_LEAGUE",
    "South Korea K League 1": "K_LEAGUE_1",
    "K League 1": "K_LEAGUE_1",
    "Chile Primera Division": "CHILE_PRIMERA",
    "Chile Primera División": "CHILE_PRIMERA",
}


def _canonical_from_name(name: str) -> str | None:
    """Map a FootyStats league display name to a canonical league ID."""
    hit = _FOOTYSTATS_NAME_TO_CANONICAL.get(name)
    if hit:
        return hit
    name_lower = name.lower()
    for key, val in _FOOTYSTATS_NAME_TO_CANONICAL.items():
        if key.lower() == name_lower:
            return val
    return None


def check_drift(api_key: str) -> dict[str, object]:
    """Fetch /league-list and diff against FOOTYSTATS_SEASON_IDS.

    Args:
        api_key: FootyStats API key.

    Returns:
        Dict with keys: drifted, new_seasons, missing_from_api, historical_additions.
    """
    url = f"{_BASE_URL}/league-list"
    resp = requests.get(url, params={"key": api_key, "chosen_leagues_only": "true"}, timeout=30)
    resp.raise_for_status()

    payload = resp.json()
    if isinstance(payload, dict) and "data" in payload:
        items: list[object] = payload["data"] if isinstance(payload["data"], list) else []
    elif isinstance(payload, list):
        items = payload
    else:
        items = []

    # Build api_canonical_to_season from response
    api_canonical_to_season: dict[str, int] = {}
    new_seasons: list[dict[str, object]] = []
    historical_additions: list[dict[str, object]] = []

    for item in items:
        if not isinstance(item, dict):
            continue
        raw_id = item.get("id")
        name = str(item.get("name", ""))
        if raw_id is None:
            continue
        season_id = int(raw_id)

        canonical = FOOTYSTATS_HISTORICAL_SEASON_IDS.get(season_id)
        if canonical is None:
            # Not in historical map — new season; try name lookup
            canonical = _canonical_from_name(name)
            new_seasons.append({"season_id": season_id, "name": name, "canonical_guess": canonical})
            if canonical:
                historical_additions.append({"season_id": season_id, "canonical": canonical})

        if canonical and canonical not in api_canonical_to_season:
            api_canonical_to_season[canonical] = season_id

    # Diff: compare api result against hardcoded FOOTYSTATS_SEASON_IDS
    drifted: list[dict[str, object]] = []
    missing_from_api: list[str] = []

    for league, current_id in sorted(FOOTYSTATS_SEASON_IDS.items()):
        api_id = api_canonical_to_season.get(league)
        if api_id is None:
            missing_from_api.append(league)
        elif api_id != current_id:
            drifted.append({"league": league, "old_id": current_id, "new_id": api_id})

    return {
        "drifted": drifted,
        "new_seasons": new_seasons,
        "missing_from_api": missing_from_api,
        "historical_additions": historical_additions,
    }


def _format_pr_body(result: dict[str, object]) -> str:
    """Format a GitHub issue/PR body describing required FOOTYSTATS_SEASON_IDS updates."""
    drifted: list[dict[str, object]] = result.get("drifted", [])  # type: ignore[assignment]
    historical_additions: list[dict[str, object]] = result.get("historical_additions", [])  # type: ignore[assignment]
    new_seasons: list[dict[str, object]] = result.get("new_seasons", [])  # type: ignore[assignment]

    lines = ["## FootyStats season ID drift detected\n"]

    if drifted:
        lines.append("### FOOTYSTATS_SEASON_IDS updates required\n")
        lines.append("```python")
        for d in drifted:
            lines.append(f'    "{d["league"]}": {d["new_id"]},  # was {d["old_id"]}')
        lines.append("```\n")

    unknown = [s for s in new_seasons if s.get("canonical_guess") is None]
    if unknown:
        lines.append("### New seasons with unknown canonical mapping (manual review needed)\n")
        for s in unknown:
            lines.append(f"- season_id={s['season_id']} name={s['name']!r}\n")

    if historical_additions:
        lines.append("### FOOTYSTATS_HISTORICAL_SEASON_IDS entries to append\n")
        lines.append("```python")
        for a in historical_additions:
            lines.append(f'    {a["season_id"]}: "{a["canonical"]}",')
        lines.append("```\n")

    lines.append("---\n*Auto-generated by `scripts/check_footystats_season_drift.py`*")
    return "\n".join(lines)


def main() -> int:
    api_key = os.environ.get("FOOTYSTATS_API_KEY", "")
    if not api_key:
        print("ERROR: FOOTYSTATS_API_KEY env var not set", file=sys.stderr)
        return 2

    try:
        result = check_drift(api_key)
    except requests.RequestException as exc:
        print(f"ERROR: FootyStats API request failed: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(result, indent=2))

    drifted: list[dict[str, object]] = result.get("drifted", [])  # type: ignore[assignment]
    new_seasons: list[dict[str, object]] = result.get("new_seasons", [])  # type: ignore[assignment]
    unknown_new = [s for s in new_seasons if s.get("canonical_guess") is None]

    if drifted:
        print(
            f"\n🚨 DRIFT DETECTED: {len(drifted)} league(s) have new season IDs",
            file=sys.stderr,
        )
        for d in drifted:
            print(f"  {d['league']}: {d['old_id']} → {d['new_id']}", file=sys.stderr)

    if unknown_new:
        print(
            f"\n⚠️  {len(unknown_new)} new season(s) with unknown canonical mapping",
            file=sys.stderr,
        )
        for s in unknown_new:
            print(f"  id={s['season_id']} name={s['name']!r}", file=sys.stderr)

    if not drifted and not new_seasons:
        print("✅ No drift: all FOOTYSTATS_SEASON_IDS match live API", file=sys.stderr)

    # Write PR body to file if drift detected (consumed by GHA step)
    if drifted or unknown_new:
        with open("footystats_drift_report.md", "w") as fh:
            fh.write(_format_pr_body(result))

    return 1 if (drifted or unknown_new) else 0


if __name__ == "__main__":
    sys.exit(main())
