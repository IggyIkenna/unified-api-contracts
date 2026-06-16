"""Unit tests for the mode-contextual precedence resolver (GATE-0 M4).

Covers ``select_for_mode``: the contextual read precedence where a LIVE-context
consumer prefers ``[LIVE, REPLAY, BATCH]``, a BATCH-context consumer prefers
``[BATCH, REPLAY, LIVE]``, a REPLAY-context consumer reuses the live order, and
``replay`` is ALWAYS the middle (gap-fill) tier.

Plan: ``pipeline_mode_source_batch_live_replay_standardisation_2026_06_05.md`` M4.
"""

from __future__ import annotations

import pytest

from unified_api_contracts import select_for_mode
from unified_api_contracts.canonical.crosscutting.mode_precedence import (
    select_for_mode as select_for_mode_direct,
)
from unified_api_contracts.canonical.crosscutting.pipeline_mode import Mode


def test_facade_export_is_the_same_callable() -> None:
    """``from unified_api_contracts import select_for_mode`` is the canonical export."""
    assert select_for_mode is select_for_mode_direct


def test_live_context_prefers_live() -> None:
    assert select_for_mode(Mode.LIVE, frozenset({Mode.LIVE, Mode.BATCH})) == Mode.LIVE


def test_batch_context_prefers_batch() -> None:
    assert select_for_mode(Mode.BATCH, frozenset({Mode.LIVE, Mode.BATCH})) == Mode.BATCH


def test_replay_is_always_the_middle_gap_fill_tier_live_context() -> None:
    # Live context, live absent → replay (not batch).
    assert select_for_mode(Mode.LIVE, frozenset({Mode.REPLAY, Mode.BATCH})) == Mode.REPLAY


def test_replay_is_always_the_middle_gap_fill_tier_batch_context() -> None:
    # Batch context, batch absent → replay (not live).
    assert select_for_mode(Mode.BATCH, frozenset({Mode.REPLAY, Mode.LIVE})) == Mode.REPLAY


def test_live_context_full_order() -> None:
    assert select_for_mode(Mode.LIVE, frozenset(Mode)) == Mode.LIVE
    assert select_for_mode(Mode.LIVE, frozenset({Mode.REPLAY})) == Mode.REPLAY
    assert select_for_mode(Mode.LIVE, frozenset({Mode.BATCH})) == Mode.BATCH


def test_batch_context_full_order() -> None:
    assert select_for_mode(Mode.BATCH, frozenset(Mode)) == Mode.BATCH
    assert select_for_mode(Mode.BATCH, frozenset({Mode.REPLAY})) == Mode.REPLAY
    assert select_for_mode(Mode.BATCH, frozenset({Mode.LIVE})) == Mode.LIVE


def test_replay_context_reuses_live_order() -> None:
    # Replay context is freshness-seeking → same order as live: [LIVE, REPLAY, BATCH].
    assert select_for_mode(Mode.REPLAY, frozenset(Mode)) == Mode.LIVE
    assert select_for_mode(Mode.REPLAY, frozenset({Mode.REPLAY, Mode.BATCH})) == Mode.REPLAY
    assert select_for_mode(Mode.REPLAY, frozenset({Mode.BATCH})) == Mode.BATCH


def test_single_available_mode_returns_it_for_every_context() -> None:
    for context in Mode:
        for only in Mode:
            assert select_for_mode(context, frozenset({only})) == only


def test_empty_available_modes_raises() -> None:
    with pytest.raises(ValueError, match="available_modes is empty"):
        select_for_mode(Mode.LIVE, frozenset())
