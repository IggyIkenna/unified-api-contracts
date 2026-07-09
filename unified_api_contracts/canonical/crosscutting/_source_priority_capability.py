"""Per-source / per-(source, data_type) :class:`Mode` capability resolution.

Split out of ``source_priority.py`` (900-line file-size QG, 2026-07-09) —
pure file-organization move, no behavior change. ``source_priority.py``
re-exports everything here so the public import path
(``unified_api_contracts.canonical.crosscutting.source_priority``) is
unchanged.

:func:`modes_for_source` is the COARSE per-source answer; :func:`modes_for`
is the M2-REFINEMENT per-``(source, data_type)`` answer derived from the
source's :class:`~unified_api_contracts.registry.capability.SourceCapability`
``operations`` (the ws_/REST split). SSOT:
``pipeline_mode_source_batch_live_replay_standardisation_2026_06_05.md``
§ M2-REFINEMENT.
"""

from __future__ import annotations

from functools import cache
from typing import TYPE_CHECKING

from unified_api_contracts.canonical.crosscutting._source_priority_data import (
    MOCK_SOURCE,
    SOURCE_MODE_CAPABILITY,
)
from unified_api_contracts.canonical.crosscutting.pipeline_mode import Mode

if TYPE_CHECKING:
    from unified_api_contracts.registry.capability import SourceCapability

_WS_OP_PREFIX = "ws_"
"""Operation-name prefix that marks a WEBSOCKET (streaming → LIVE) operation in a
:class:`~unified_api_contracts.registry.capability.SourceCapability` ``operations``
declaration (e.g. ``ws_trades``). A non-prefixed op is REST → BATCH. This is the
``modes_for`` per-``(source, data_type)`` derivation key (M2-REFINEMENT)."""


def modes_for_source(source: str) -> frozenset[Mode]:
    """Return the COARSE per-source set of :class:`Mode`s ``source`` can run.

    ``mock`` ⇒ all modes (a fixture can stand in for any). Unregistered external
    source ⇒ ``{BATCH}`` (the safe default — everything is at least
    batch-archivable). The per-source mode sets are RATIFIED + load-bearing (the
    ``source_mode_capability_matrix_2026_06_07.md`` rows).

    This is the COARSE answer: it over-approximates for a source that streams
    only SOME of its data_types live (e.g. hyperliquid is LIVE for
    ``trades``/``l2_book`` but REST/BATCH-only for ``funding_rates``). The
    per-``(source, data_type)`` refinement is :func:`modes_for` (M2-REFINEMENT,
    derived from the ``SourceCapability.operations`` ws/REST split). Keep using
    THIS helper for source-level questions (capability matrices, the
    replay-capable set); use :func:`modes_for` when the data_type is known.
    SSOT: ``pipeline_mode_source_batch_live_replay_standardisation_2026_06_05.md``
    § M2-REFINEMENT."""
    if source == MOCK_SOURCE:
        return frozenset({Mode.BATCH, Mode.LIVE, Mode.REPLAY})
    return SOURCE_MODE_CAPABILITY.get(source, frozenset({Mode.BATCH}))


@cache
def _capability_by_source() -> dict[str, SourceCapability]:
    """Source → :class:`SourceCapability` lookup, built once from the static list.

    Lazy (function-local) import: ``registry.capability_data`` transitively loads
    THIS module (``canonical.crosscutting.source_priority``) through the registry
    package ``__init__``, so a module-level import would be a circular import. We
    read the STATIC ``CAPABILITY_DECLARATIONS`` list rather than the runtime
    ``register_capability`` registry, which is not bootstrapped at import time.
    Memoised — the declaration list is immutable at runtime.
    """
    from unified_api_contracts.registry.capability_data import CAPABILITY_DECLARATIONS

    return {cap.source: cap for cap in CAPABILITY_DECLARATIONS}


def _data_type_served_by_op(operation: str, data_type: str) -> bool:
    """True when ``operation`` (``ws_``-stripped) names the ``data_type`` concept.

    Token-subset match on ``_``-delimited words: data_type ``trades`` is served by
    ``trades`` / ``recent_trades`` / ``agg_trades`` / ``ws_trades`` (``{trades}``
    is a subset of the op's word set) but NOT by ``funding_rate`` — and substring
    false positives (``trades`` inside an unrelated token) cannot occur because the
    match is on whole ``_``-delimited words. An exact match short-circuits.
    """
    base = operation.removeprefix(_WS_OP_PREFIX).lower()
    data_type_lower = data_type.lower()
    if base == data_type_lower:
        return True
    return set(data_type_lower.split("_")) <= set(base.split("_"))


def modes_for(source: str, data_type: str) -> frozenset[Mode]:
    """Per-``(source, data_type)`` refinement of :func:`modes_for_source` (M2-REFINEMENT).

    The data-type-aware capability lookup. :func:`modes_for_source` answers "what
    can this source do AT ALL"; this answers "what can this source do for THIS
    data_type" — derived from the source's
    :class:`~unified_api_contracts.registry.capability.SourceCapability`
    ``operations`` (the EXISTING per-operation REST/WS declarations, NOT a parallel
    registry). The contract:

    * **LIVE** is the only genuinely per-data_type dimension — a live source
      STREAMS some data_types (a ``ws_<data_type>`` operation) but only batch-
      archives others (REST-only). So LIVE is kept iff a ``ws_`` op serves the
      data_type, else dropped.
    * **BATCH** is the universal floor (everything is at least batch-archivable),
      carried straight from :func:`modes_for_source`.
    * **REPLAY** is the live-gap-fill tier (M4 — "replay is ALWAYS the middle
      tier"): it drops WITH live (no live stream → no live-downtime gap to
      replay → the data_type is its batch role only).

    The refinement ONLY applies to a source that is BOTH live-capable AND expresses
    the per-operation ws/REST split (the CeFi exchange venues + hyperliquid). For
    every other source — batch-only (``tardis``/``yahoo``/sports vendors), or
    live-capable-but-no-ws-convention (``databento``/``massive`` vendor feeds, chain
    RPCs, internal services) — it returns the coarse :func:`modes_for_source` set
    unchanged (the ws/REST distinction is meaningless there). This narrows the M3
    :func:`~unified_api_contracts.canonical.crosscutting.shard_source_availability.could_exist`
    over-approximation exactly where it lived (hyperliquid reading ``{BATCH, LIVE,
    REPLAY}`` for every shard) without regressing the coarse answer anywhere else.

    Worked example (hyperliquid)::

        modes_for("hyperliquid", "trades")        # {BATCH, LIVE, REPLAY} (ws_trades)
        modes_for("hyperliquid", "funding_rates") # {BATCH} (REST-only — no ws op)

    Args:
        source: A source string (a :func:`modes_for_source` key — a vendor /
            exchange venue / internal emitter).
        data_type: Canonical data_type string (e.g. ``trades`` / ``funding_rates``
            / ``l2_book``).

    Returns:
        The :class:`Mode` set ``source`` can run FOR ``data_type``. A subset of
        ``modes_for_source(source)`` (the refinement only narrows, never widens);
        ``frozenset()`` when a ws-convention live source declares no operation for
        the data_type (it serves that data_type in no mode — an honest absence).
    """
    coarse = modes_for_source(source)
    # A source that can't run LIVE at all has no per-data_type live/batch split to
    # refine — its coarse set already IS the answer (and the mock all-modes source
    # stands in for any data_type).
    if Mode.LIVE not in coarse or source == MOCK_SOURCE:
        return coarse
    capability = _capability_by_source().get(source)
    if capability is None:
        return coarse  # no per-operation declarations → coarse is the best we have
    operations = [op for ops in capability.operations.values() for op in ops]
    if not any(op.startswith(_WS_OP_PREFIX) for op in operations):
        # The source does not express the ws-(live) / REST-(batch) split per
        # operation (e.g. databento/massive vendor feeds) → can't refine LIVE.
        return coarse
    streams_data_type_live = any(
        op.startswith(_WS_OP_PREFIX) and _data_type_served_by_op(op, data_type) for op in operations
    )
    if streams_data_type_live:
        return coarse
    # ws-convention source with NO ``ws_<data_type>`` op → it does not stream this
    # data_type live; drop LIVE and its REPLAY gap-fill tier (honest absence). The
    # BATCH floor survives where the source carries it (hyperliquid), giving
    # ``{BATCH}``; a live/replay-only venue (binance) collapses to ``frozenset()``.
    return frozenset(coarse - {Mode.LIVE, Mode.REPLAY})


def source_supports(source: str, mode: Mode) -> bool:
    """True if ``source`` can run in reconciliation ``mode`` (M2 guardrail)."""
    return mode in modes_for_source(source)


def sources_supporting(mode: Mode) -> set[str]:
    """All registered sources capable of ``mode`` (e.g. the replay-capable set)."""
    return {src for src, modes in SOURCE_MODE_CAPABILITY.items() if mode in modes}
