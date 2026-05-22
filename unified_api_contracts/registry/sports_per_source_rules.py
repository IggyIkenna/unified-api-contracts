"""Sports per-source expected-coverage rules.

Single entry point for classifier logic that decides whether a sports shard is
*expected* for a given ``(source, league_id, day)`` triple.  Returns a typed
``EmptyConfirmedReason`` string (or ``None`` when the shard IS expected).

Mirrors the pattern of:
- ``chain_env.CHAIN_GENESIS_DATES``  (DeFi — chain did not exist yet)
- ``venue_launch_dates.CEFI_VENUE_LAUNCH_DATES``  (CeFi — venue did not exist)
- ``sports.SOURCE_COVERAGE_START`` / ``DATA_TYPE_COVERAGE_START``  (sports — source archive starts)

All three express "no data possible on this date" for different asset_groups.

## Supported sources

| Source key   | Coverage rule                                                        |
|--------------|----------------------------------------------------------------------|
| ``understat`` | Only the 5 European leagues in ``UNDERSTAT_COVERED_LEAGUES``         |
| ``footystats``| Only within the league's active season window (PRE_SEASON/POST_SEASON) |
| ``api_football`` | Covered whenever source archive started (SOURCE_COVERAGE_START)  |
| ``transfer_records`` | `transfer_records` shard only expected inside transfer window  |

Used by:
- ``classify_venue_error._classify_sports`` in UTL
- Phase 3.D.5 v2 enumerator sports branch
"""

from __future__ import annotations

from datetime import date

from unified_api_contracts.canonical.domain.sports.league_data import (
    SOURCE_COVERAGE_START,
    get_source_coverage_start,
)
from unified_api_contracts.canonical.domain.sports.provider_league_ids import (
    UNDERSTAT_COVERED_LEAGUES,
)
from unified_api_contracts.canonical.domain.sports.season_dates import (
    footystats_season_status_for_day,
)
from unified_api_contracts.canonical.domain.sports.transfer_windows import (
    is_transfer_window_open,
)


def is_expected_for_source(
    source: str,
    league_id: str,
    day: date,
    *,
    data_type: str | None = None,
) -> tuple[bool, str | None]:
    """Return ``(is_expected, reason_if_not)`` for a sports shard.

    Args:
        source: Source key as stored in the manifest — e.g. ``"understat"``,
            ``"footystats"``, ``"api_football"``.
        league_id: Canonical league identifier — e.g. ``"EPL"``, ``"LALIGA"``.
        day: The shard date being classified.
        data_type: Optional data_type for data-type-specific rules (e.g.
            ``"transfer_records"`` for transfer-window gating).

    Returns:
        ``(True, None)`` when the shard IS expected — caller should treat a
        zero-row result as a real absence (``attempted_failed`` or retry).
        ``(False, reason)`` when the shard is NOT expected — caller should emit
        ``empty_confirmed`` with ``reason=reason``.

    The ``reason`` strings are exact values of
    ``EmptyConfirmedReason`` from ``honest_coverage`` — the caller must import
    that enum to construct the ``record_empty`` call.
    """
    source_key = source.lower()

    # ── Transfer-window gate (data_type-specific, any source) ─────────────────
    if data_type == "transfer_records" and not is_transfer_window_open(league_id, day):
        return False, "EXPECTED_OUTSIDE_TRANSFER_WINDOW"
    # If data_type == "transfer_records" and window IS open, fall through to source checks.

    # ── Understat: fixed league whitelist ─────────────────────────────────────
    if source_key == "understat":
        if league_id.upper() not in UNDERSTAT_COVERED_LEAGUES:
            return False, "EXPECTED_SOURCE_DOES_NOT_COVER_LEAGUE"
        coverage_start = get_source_coverage_start(source_key)
        if coverage_start is not None and day < coverage_start:
            return False, "EXPECTED_PRE_SOURCE_COVERAGE_START"
        return True, None

    # ── FootyStats: season-bounds gate ───────────────────────────────────────
    if source_key == "footystats":
        coverage_start = get_source_coverage_start(source_key)
        if coverage_start is not None and day < coverage_start:
            return False, "EXPECTED_PRE_SOURCE_COVERAGE_START"
        season_status = footystats_season_status_for_day(league_id, day)
        if season_status is not None:
            # season_status is "EXPECTED_PRE_SEASON" or "EXPECTED_POST_SEASON"
            return False, season_status
        return True, None

    # ── api_football and all other sources: coverage-start only ──────────────
    coverage_start = SOURCE_COVERAGE_START.get(source_key)
    if coverage_start is not None and day < coverage_start:
        return False, "EXPECTED_PRE_SOURCE_COVERAGE_START"
    return True, None


def is_understat_league(league_id: str) -> bool:
    """Whether ``league_id`` is covered by Understat.

    Thin convenience wrapper over ``UNDERSTAT_COVERED_LEAGUES`` for callers
    that only need the boolean, not the full reason tuple.
    """
    return league_id.upper() in UNDERSTAT_COVERED_LEAGUES


def is_in_transfer_window(league_id: str, day: date) -> bool:
    """Whether ``day`` falls inside a transfer window for ``league_id``.

    Delegates to ``transfer_windows.is_transfer_window_open`` — exists here
    so the sports-per-source registry is the single import needed by
    classifiers that apply all sports expected-gap rules.
    """
    return is_transfer_window_open(league_id, day)
