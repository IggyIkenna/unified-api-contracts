"""Tardis free-tier access rules — SSOT for schedulers and launchers.

Tardis free tier provides two classes of dates without a paid API key:
  (a) 1st of every month — all historical dates with day == 1
  (b) Recent rolling window — the last N days from today

All other historical dates require an active paid subscription.

Callers that want to launch backfill without a paid key should use
``is_tardis_free_date`` to gate which dates to enqueue.

The rolling window size is kept intentionally conservative at 7 days
(Tardis official free-trial policy as of 2026-05).  If Tardis changes
their free window, update ``TARDIS_FREE_ROLLING_WINDOW_DAYS`` here.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

__all__ = [
    "TARDIS_FREE_ROLLING_WINDOW_DAYS",
    "free_dates_in_range",
    "is_tardis_free_date",
]

TARDIS_FREE_ROLLING_WINDOW_DAYS: int = 7


def is_tardis_free_date(
    target_date: date | str,
    as_of: date | None = None,
) -> bool:
    """Return True if ``target_date`` is accessible on the Tardis free tier.

    Free-tier rules:
      - day-of-month == 1  (first of any historical month)
      - target_date >= as_of - TARDIS_FREE_ROLLING_WINDOW_DAYS (recent window)

    Args:
        target_date: The date to check (str YYYY-MM-DD or date).
        as_of: Reference "today" for the rolling window.  Defaults to UTC today.
    """
    if isinstance(target_date, str):
        target_date = date.fromisoformat(target_date[:10])
    if as_of is None:
        as_of = datetime.now(UTC).date()
    if target_date.day == 1:
        return True
    cutoff = as_of - timedelta(days=TARDIS_FREE_ROLLING_WINDOW_DAYS)
    return target_date >= cutoff


def free_dates_in_range(
    start: date | str,
    end: date | str,
    as_of: date | None = None,
) -> list[date]:
    """Return the subset of dates in [start, end] accessible on the free tier.

    Useful for building the fetchable date list before a Tardis key is renewed.

    Args:
        start: Inclusive start date.
        end: Inclusive end date.
        as_of: Reference "today" for the rolling window.  Defaults to UTC today.
    """
    if isinstance(start, str):
        start = date.fromisoformat(start[:10])
    if isinstance(end, str):
        end = date.fromisoformat(end[:10])
    if as_of is None:
        as_of = datetime.now(UTC).date()
    result: list[date] = []
    current = start
    while current <= end:
        if is_tardis_free_date(current, as_of=as_of):
            result.append(current)
        current += timedelta(days=1)
    return result
