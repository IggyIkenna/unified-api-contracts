"""Mode-contextual precedence resolver (GATE-0 M4).

When a reader consumes a cell that the cross-mode UNION reconciliation has
populated in more than one :class:`~unified_api_contracts.canonical.crosscutting.pipeline_mode.Mode`
(``batch`` / ``live`` / ``replay``), it must pick exactly one mode's value. The
choice is **CONTEXTUAL** — it depends on the consumer's own mode-context — but
``replay`` is ALWAYS the middle (gap-fill) tier:

* A **LIVE-context** consumer prefers ``[LIVE, REPLAY, BATCH]`` — it wants the
  freshest live value, falls back to an intraday replay gap-fill, and only then
  to the T+1 batch floor.
* A **BATCH-context** consumer prefers ``[BATCH, REPLAY, LIVE]`` — it wants the
  authoritative deep-history batch value, falls back to replay, and only then to
  whatever live happened to capture.
* A **REPLAY-context** consumer reuses the LIVE-context order ``[LIVE, REPLAY,
  BATCH]``. Replay exists to back-fill the live read-path (a window live missed),
  so a replay-context reader has the same freshness goal as a live reader — it
  prefers a real live value if one is now present, then replay, then batch. This
  keeps the resolver from ever preferring stale batch over a fresher live/replay
  value for a freshness-seeking consumer.

This is the read-side companion to M1's :func:`~...pipeline_mode.mode_of`: M1
classifies a concrete ``pipeline_mode`` into its abstract :class:`Mode`; M4 then
selects WHICH abstract :class:`Mode` a reader consumes from the set the manifest
says is available for that cell.

Plan: ``pipeline_mode_source_batch_live_replay_standardisation_2026_06_05.md``
(GATE-0 M4).
"""

from __future__ import annotations

from typing import Final

from .pipeline_mode import Mode

# Context-order precedence lists. ``replay`` is the invariant middle (gap-fill)
# tier in every order; only the live/batch endpoints flip by context.
_LIVE_CONTEXT_ORDER: Final[tuple[Mode, ...]] = (Mode.LIVE, Mode.REPLAY, Mode.BATCH)
_BATCH_CONTEXT_ORDER: Final[tuple[Mode, ...]] = (Mode.BATCH, Mode.REPLAY, Mode.LIVE)
# A replay-context consumer is freshness-seeking like a live reader → reuse the
# live-context order (documented above).
_REPLAY_CONTEXT_ORDER: Final[tuple[Mode, ...]] = _LIVE_CONTEXT_ORDER

_CONTEXT_ORDER_FOR_MODE: Final[dict[Mode, tuple[Mode, ...]]] = {
    Mode.LIVE: _LIVE_CONTEXT_ORDER,
    Mode.BATCH: _BATCH_CONTEXT_ORDER,
    Mode.REPLAY: _REPLAY_CONTEXT_ORDER,
}


def select_for_mode(consumer_mode: Mode, available_modes: frozenset[Mode]) -> Mode:
    """Return the :class:`Mode` a ``consumer_mode``-context reader should consume.

    Resolves the mode-contextual read precedence (M4): a LIVE-context consumer
    prefers ``[LIVE, REPLAY, BATCH]``; a BATCH-context consumer prefers
    ``[BATCH, REPLAY, LIVE]``; a REPLAY-context consumer reuses the live order
    ``[LIVE, REPLAY, BATCH]``. ``replay`` is ALWAYS the middle (gap-fill) tier.

    Returns the first :class:`Mode` in the consumer's context-order that is
    present in ``available_modes``.

    :param consumer_mode: the reader's own mode-context.
    :param available_modes: the set of :class:`Mode` values the manifest reports
        as available (captured) for the cell being read.
    :raises ValueError: if ``available_modes`` is empty, or if no mode in the
        context-order is present in ``available_modes``.
    """
    if not available_modes:
        raise ValueError(
            f"select_for_mode: available_modes is empty — nothing to select for "
            f"consumer_mode {consumer_mode.value!r}."
        )

    order = _CONTEXT_ORDER_FOR_MODE[consumer_mode]
    for candidate in order:
        if candidate in available_modes:
            return candidate

    # Unreachable in practice: order spans all three Modes, so any non-empty
    # subset of Mode must match. Kept as a clear guard against a future Mode
    # member being added without extending the context orders.
    raise ValueError(
        f"select_for_mode: no mode in context-order {[m.value for m in order]!r} "
        f"is present in available_modes "
        f"{sorted(m.value for m in available_modes)!r} (consumer_mode "
        f"{consumer_mode.value!r})."
    )


__all__ = [
    "select_for_mode",
]
