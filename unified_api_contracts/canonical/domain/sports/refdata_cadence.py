"""Transfermarkt PLAYER_VALUES update cadence constants.

Transfermarkt scrapes player market values on a NON-DAILY cadence — typically
once or twice per week when transfer-fee rankings are updated. Daily empty rows
are NOT honest source-return-zero failures; they are expected non-scrape days.

The classifier uses these constants to emit ``EXPECTED_REFDATA_CADENCE_CHANGE``
instead of the misleading ``SOURCE_RETURNED_ZERO`` for off-cadence PLAYER_VALUES
days. This prevents:

- Spurious alert inflation (~6/7 PLAYER_VALUES empty rows per week misclassified
  as data failures).
- Script 3 apply-flips being blocked on incorrectly-classified source failures.

Plan: ``sports_classifier_player_values_cadence_2026_05_13.md`` (slot 4 ownership).

Cadence evidence: transfermarkt updates their player valuation tables on
Wednesday market runs (primary) and sometimes Tuesday. The weekly cadence is
documented in their scraping patterns — updates cluster heavily on Wed/Thu.

Consumer: ``unified_trading_library.legacy_reason_classifier._classify_sports``
reads ``TRANSFERMARKT_PLAYER_VALUES_UPDATE_WEEKDAYS`` to decide per-day.
"""

from __future__ import annotations

from typing import Final

TRANSFERMARKT_PLAYER_VALUES_UPDATE_WEEKDAYS: Final[frozenset[int]] = frozenset({1, 2})
"""Weekdays (0=Monday, 6=Sunday) when transfermarkt updates PLAYER_VALUES.

Tuesday (1) and Wednesday (2) are the canonical update days based on transfermarkt's
weekly valuation cycle. On other weekdays, PLAYER_VALUES empty rows should be
classified as ``EXPECTED_REFDATA_CADENCE_CHANGE`` rather than ``SOURCE_RETURNED_ZERO``.

Note: This is a weekly-cadence constant, not a day-of-month or season schedule.
If empirical sampling shows a different dominant weekday, update this frozenset
and redeploy — no structural change needed.
"""

__all__ = ["TRANSFERMARKT_PLAYER_VALUES_UPDATE_WEEKDAYS"]
