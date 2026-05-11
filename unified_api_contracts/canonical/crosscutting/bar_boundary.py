"""UAC SSOT for MDPS bar-boundary alignment + per-bar ``available_at`` stamping.

This module is the **contract layer** half of the bar-boundary split: it declares
WHAT the rule is (closed-set timeframes + UTC-midnight-aligned boundaries +
``available_at == t_close``). The HOW (compute the bar-close boundary from a
last-tick timestamp) lives in
:mod:`unified_trading_library.availability_stamping.compute_bar_close_boundary`.

Background
----------
Per the workspace CLAUDE.md "available_at is per-row, write-time" rule and the
operator directive 2026-05-08 (_"candle timestamps must be at the point where
data became available — last-tick-timestamp rounded UP to the bar's boundary
on even UTC midnight-aligned grid. No phase shift."_), every MDPS-emitted bar
satisfies a 4-clause contract:

1. **Closed-set timeframe.** ``timeframe`` ∈ :data:`BAR_TIMEFRAMES`. No
   ad-hoc resolutions (e.g. ``7m``, ``2h30m``) — drift between MDPS
   calculators and downstream consumers would silently shift the manifest
   denominator and break cluster-coverage validation.

2. **UTC-midnight-aligned boundaries.** ``t_close`` lies on the grid
   ``{midnight_utc + N * timeframe : N ∈ ℤ}``. Equivalently, the number of
   ``timeframe``-units between UTC midnight and ``t_close`` is an integer.
   Bars never carry a phase shift relative to the day; daily bars close at
   00:00 UTC, hourly at HH:00, 15m at HH:00/15/30/45, etc. This makes
   cross-instrument joins on bar boundaries trivial (every venue's 15m bars
   share the same grid) and lets the rescan reconciler verify boundary
   alignment per-row.

3. **Bar window is half-open ``[t_open, t_close)``.** ``t_open = t_close -
   timeframe``; the bar contains every tick with ``t_open <= tick_ts <
   t_close``. A tick at the boundary itself belongs to the NEXT bar.

4. **``available_at == t_close``.** A bar could not have been observed live
   before ``t_close`` (the moment the bar closed and the aggregate could be
   computed). Stamping any earlier timestamp would leak future ticks into
   features built on prior bars; stamping ``wall_clock_now`` at replay time
   makes the row replay-non-idempotent. Both are banned by the rule above.

Idempotency
-----------
The bar-boundary contract is **idempotent under replay** by construction: for
fixed ``(last_tick_ts, timeframe)``, the implementation in
:func:`unified_trading_library.availability_stamping.compute_bar_close_boundary`
returns the same ``(t_open, t_close, available_at)`` triple regardless of when
the replay runs. Replaying the same tick stream on day +1, +30, or +365
produces byte-identical bar parquets (modulo any per-row business-logic state
in OHLCV aggregation, which is upstream-aggregator-determined and not in scope
here).

Worked examples
---------------
Last tick at ``2026-04-29T14:23:47.123Z`` with timeframe ``15m``:
* ``t_close = 2026-04-29T14:30:00Z`` (the next 15-minute boundary).
* ``t_open  = 2026-04-29T14:15:00Z`` (= ``t_close - 15m``).
* ``available_at = t_close = 2026-04-29T14:30:00Z``.

Last tick exactly on a boundary, ``2026-04-29T14:15:00Z``, timeframe ``15m``:
* ``t_close = 2026-04-29T14:30:00Z`` (the boundary AFTER the tick; the tick
  itself belongs to the ``[14:15, 14:30)`` bar — ceiling is **strict** on the
  half-open interval).

Last tick at ``2026-04-29T23:59:59.999Z`` with timeframe ``1d``:
* ``t_close = 2026-04-30T00:00:00Z``.
* ``t_open  = 2026-04-29T00:00:00Z``.

Reference
---------
* Plan: ``unified-trading-pm/plans/active/available_at_lookahead_bias_completion_2026_05_08.md``
  Phase 0.
* Workspace CLAUDE.md ``available_at is per-row, write-time`` rule.
* UTL implementation:
  :func:`unified_trading_library.availability_stamping.compute_bar_close_boundary`.
* MDPS write-gate guard (Phase 0.4 — pending):
  ``BarBoundaryViolationError`` raised inside ``record_captured`` whenever
  a bar's triple violates this contract.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Final, Literal

BarTimeframe = Literal[
    "15s",
    "1m",
    "5m",
    "15m",
    "30m",
    "1h",
    "4h",
    "1d",
]
"""Closed set of supported bar timeframes for MDPS + every downstream consumer.

Adding a new timeframe is a deliberate, workspace-wide decision: every MDPS
calculator, downstream features-* compute, deployment-UI rollup widget, and
cluster-validation registry must understand it. Do NOT introduce a new
timeframe without (1) extending this literal, (2) extending
:data:`BAR_TIMEFRAME_SECONDS`, (3) auditing every ``record_captured`` callsite
that writes bars, and (4) updating downstream consumers (features-* DAG,
data-status drill-down, etc.) in the same commit.
"""

BAR_TIMEFRAMES: Final[tuple[BarTimeframe, ...]] = (
    "15s",
    "1m",
    "5m",
    "15m",
    "30m",
    "1h",
    "4h",
    "1d",
)
"""Tuple form of :data:`BarTimeframe` — usable as an ``in`` membership test
at runtime (Literal is a static-type-only construct)."""

BAR_TIMEFRAME_SECONDS: Final[dict[BarTimeframe, int]] = {
    "15s": 15,
    "1m": 60,
    "5m": 5 * 60,
    "15m": 15 * 60,
    "30m": 30 * 60,
    "1h": 60 * 60,
    "4h": 4 * 60 * 60,
    "1d": 24 * 60 * 60,
}
"""Width of each timeframe in whole seconds.

All values divide evenly into 86400 (seconds in a UTC day), so the
midnight-aligned grid is uniform: every timeframe's boundaries are a strict
subset of the daily-bar boundaries (00:00 UTC). This is what makes clause-2
of the contract enforceable.
"""


class BarBoundaryViolationError(ValueError):
    """Raised when a bar's ``(t_open, t_close, available_at, timeframe)``
    tuple violates the contract declared in this module.

    Surfaces at the MDPS write-gate (``ManifestWriter.record_captured``
    boundary, per Phase 0.5 of the available_at plan) so a broken bar is
    rejected before it can pollute the manifest. The four failure modes are
    enumerated in :func:`assert_bar_boundary_contract` below.
    """


def _is_midnight_aligned(ts: datetime, timeframe: BarTimeframe) -> bool:
    """Return ``True`` iff ``ts`` lies on the UTC-midnight-aligned grid for
    ``timeframe`` (clause 2 of the contract).

    ``ts`` must be tz-aware UTC; passing naive or non-UTC raises (callers
    should normalise via :func:`unified_trading_library.availability_stamping`
    helpers before invoking the validator).
    """
    if ts.tzinfo is None:
        msg = f"_is_midnight_aligned requires tz-aware UTC datetime, got naive: {ts!r}"
        raise BarBoundaryViolationError(msg)
    if ts.utcoffset() != timedelta(0):
        msg = f"_is_midnight_aligned requires UTC datetime, got tz-offset {ts.utcoffset()!r} for {ts!r}"
        raise BarBoundaryViolationError(msg)
    midnight = ts.replace(hour=0, minute=0, second=0, microsecond=0)
    delta = ts - midnight
    width = BAR_TIMEFRAME_SECONDS[timeframe]
    # Total seconds must be an exact integer multiple of `width`, with zero
    # sub-second remainder (microseconds == 0).
    if ts.microsecond != 0:
        return False
    total_seconds = int(delta.total_seconds())
    if total_seconds * 1_000_000 != int(delta.total_seconds() * 1_000_000):
        # Defensive: float-second equality check. Should be unreachable since
        # we already gated `microsecond == 0`, but kept for clarity.
        return False
    return total_seconds % width == 0


def assert_bar_boundary_contract(
    *,
    t_open: datetime,
    t_close: datetime,
    available_at: datetime,
    timeframe: BarTimeframe,
) -> None:
    """Raise :class:`BarBoundaryViolationError` iff the 4-clause contract is
    violated.

    Used at MDPS write-time (per Phase 0.5 of
    ``available_at_lookahead_bias_completion_2026_05_08.md``) to gate every
    bar row before it lands on disk + in the manifest. Each violation has a
    distinct, typed message so the operator can route the fix without
    reading the full validator.

    Args:
        t_open: Bar window start (inclusive). UTC tz-aware datetime.
        t_close: Bar window end (exclusive). UTC tz-aware datetime.
        available_at: Stamped availability timestamp for the bar. UTC
            tz-aware datetime.
        timeframe: One of :data:`BAR_TIMEFRAMES`.

    Raises:
        BarBoundaryViolationError: On any of:

        * Unknown ``timeframe`` (not in :data:`BAR_TIMEFRAMES`).
        * Either timestamp is not tz-aware UTC (clause 2 prerequisite).
        * ``t_close`` is not midnight-aligned for ``timeframe`` (clause 2).
        * ``t_close - t_open != timeframe`` (clause 3).
        * ``available_at != t_close`` (clause 4).
    """
    if timeframe not in BAR_TIMEFRAME_SECONDS:
        msg = (
            f"bar_boundary_contract: timeframe={timeframe!r} not in the "
            f"closed set {BAR_TIMEFRAMES!r}. Adding a new timeframe is a "
            f"workspace-wide decision — see the module docstring."
        )
        raise BarBoundaryViolationError(msg)
    for label, ts in (("t_open", t_open), ("t_close", t_close), ("available_at", available_at)):
        if ts.tzinfo is None:
            msg = (
                f"bar_boundary_contract: {label} must be tz-aware UTC, got "
                f"naive datetime {ts!r}. Bars are always UTC; the caller "
                f"must normalise before invoking the validator."
            )
            raise BarBoundaryViolationError(msg)
        if ts.utcoffset() != timedelta(0):
            msg = f"bar_boundary_contract: {label} must be UTC, got tz-offset {ts.utcoffset()!r} for {ts!r}."
            raise BarBoundaryViolationError(msg)
    if not _is_midnight_aligned(t_close, timeframe):
        msg = (
            f"bar_boundary_contract: t_close={t_close!r} is not aligned to "
            f"the UTC-midnight {timeframe} grid (clause 2). Every bar must "
            f"close on a boundary of the form midnight_utc + N * "
            f"{BAR_TIMEFRAME_SECONDS[timeframe]}s."
        )
        raise BarBoundaryViolationError(msg)
    expected_width = timedelta(seconds=BAR_TIMEFRAME_SECONDS[timeframe])
    actual_width = t_close - t_open
    if actual_width != expected_width:
        msg = (
            f"bar_boundary_contract: t_close - t_open = {actual_width!r} does "
            f"not equal timeframe={timeframe!r} width ({expected_width!r}) "
            f"(clause 3). Half-open window [t_open, t_close) must span exactly "
            f"one timeframe."
        )
        raise BarBoundaryViolationError(msg)
    if available_at != t_close:
        msg = (
            f"bar_boundary_contract: available_at={available_at!r} != "
            f"t_close={t_close!r} (clause 4). Bars become observable at "
            f"close, never earlier (would leak), never at wall-clock-now "
            f"(would be replay-non-idempotent)."
        )
        raise BarBoundaryViolationError(msg)


def bar_window_for_close(
    t_close: datetime,
    timeframe: BarTimeframe,
) -> tuple[datetime, datetime, datetime]:
    """Derive ``(t_open, t_close, available_at)`` from a ``t_close`` and
    ``timeframe`` per the contract.

    Convenience for downstream consumers that have only the close timestamp
    on hand (e.g. data-status drilldown reading a manifest row). Validates
    the input via :func:`assert_bar_boundary_contract` before returning.

    Args:
        t_close: Bar close (UTC tz-aware).
        timeframe: One of :data:`BAR_TIMEFRAMES`.

    Returns:
        ``(t_open, t_close, available_at)`` triple. ``available_at`` is
        always ``== t_close`` per clause 4.

    Raises:
        BarBoundaryViolationError: If ``t_close`` is not midnight-aligned for
            ``timeframe``, or if ``timeframe`` is not in the closed set.
    """
    if timeframe not in BAR_TIMEFRAME_SECONDS:
        msg = f"bar_window_for_close: unknown timeframe={timeframe!r}; expected one of {BAR_TIMEFRAMES!r}."
        raise BarBoundaryViolationError(msg)
    t_open = t_close - timedelta(seconds=BAR_TIMEFRAME_SECONDS[timeframe])
    # Round-trip through the validator so callers get the same loud error
    # set the write-gate uses.
    assert_bar_boundary_contract(t_open=t_open, t_close=t_close, available_at=t_close, timeframe=timeframe)
    return t_open, t_close, t_close


# Re-exported for convenience: callers needing the literal "epoch UTC midnight"
# anchor used by the rounding rule can read it from one place. Kept module-
# private since the rounding implementation lives in UTL; UAC just declares
# WHAT the anchor is.
EPOCH_UTC: Final[datetime] = datetime(1970, 1, 1, tzinfo=UTC)


__all__ = [
    "BAR_TIMEFRAMES",
    "BAR_TIMEFRAME_SECONDS",
    "EPOCH_UTC",
    "BarBoundaryViolationError",
    "BarTimeframe",
    "assert_bar_boundary_contract",
    "bar_window_for_close",
]
