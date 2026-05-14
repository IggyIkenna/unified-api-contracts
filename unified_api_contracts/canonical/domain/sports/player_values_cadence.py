"""Transfermarkt PLAYER_VALUES scrape-cadence constants.

Transfermarkt updates player market values on an approximately weekly cadence —
NOT daily. Empty PLAYER_VALUES manifest rows on non-update weekdays are
``EXPECTED_REFDATA_CADENCE_CHANGE``, not fetch failures.

Canonical update weekday: **Wednesday** (weekday 2, 0=Monday).

Note — ``TRANSFERMARKT_PLAYER_VALUES_UPDATE_WEEKDAYS`` is intentionally a
frozenset so future operators can add multiple weekdays via UAC PR if
Transfermarkt changes its scrape schedule. Change this constant when empirical
sampling (group manifest rows by weekday, count) shows a different dominant day.

SSOT: ``plans/active/issues/sports_classifier_player_values_cadence_2026_05_13.md``
UAC commit: added 2026-05-14 (slot 4 implementation).
"""

from __future__ import annotations

from datetime import date

TRANSFERMARKT_PLAYER_VALUES_UPDATE_WEEKDAYS: frozenset[int] = frozenset({2})
"""Weekday integers (0=Monday … 6=Sunday) on which Transfermarkt scrapes
player market values.  Default: Wednesday only.  Update via UAC PR when
empirical manifest sampling confirms a different cadence.
"""


def is_player_values_update_day(day: date) -> bool:
    """Return True iff ``day`` falls on a known Transfermarkt player-values update weekday.

    Non-update days produce expected-empty PLAYER_VALUES manifests — they are NOT
    fetch failures.  Callers should emit ``EXPECTED_REFDATA_CADENCE_CHANGE`` when
    this returns False for an otherwise-unexplained empty PLAYER_VALUES row.
    """
    return day.weekday() in TRANSFERMARKT_PLAYER_VALUES_UPDATE_WEEKDAYS
