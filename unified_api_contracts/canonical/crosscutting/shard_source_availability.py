"""Per-shard available-source registry + the ``could_exist(shard, mode)`` guardrail.

GATE-0 M3 — the third tranche of the source-aware ``pipeline_mode`` standardisation
(``pipeline_mode_source_batch_live_replay_standardisation_2026_06_05.md``). M1 shipped
the source-aware :class:`~unified_api_contracts.canonical.crosscutting.pipeline_mode.Mode`
enum + ``mode_of``; M2 shipped
:func:`~unified_api_contracts.canonical.crosscutting.source_priority.modes_for_source`
(``source -> frozenset[Mode]``). This module adds the SHARD dimension:

* :func:`sources_for_shard` — which ``data_source``s serve a given
  ``(asset_group, data_type)`` shard.
* :func:`could_exist` — whether a ``(shard, mode)`` combination is even *possible*
  to capture, i.e. ``any(mode in modes_for_source(s) for s in sources_for_shard(...))``.

The guardrail composes M2-REFINEMENT (per-``(source, data_type)`` mode capability)
with the shard→source registry (M3) so a writer / manifest-seeder /
phantom-auditor can ask "is a ``live_<source>`` row even reachable for this
shard?" before it materialises an ``expected_unattempted`` cell or flags a
phantom. A shard whose only source is batch-only (e.g. a Tardis-only CeFi shard
reasoned about WITHOUT the venue overlay) returns ``False`` for :attr:`Mode.LIVE`
— an HONEST absence, not a decision.

Per-``(source, data_type)`` capability (M2-REFINEMENT — landed)
==============================================================
``could_exist`` calls
:func:`~unified_api_contracts.canonical.crosscutting.source_priority.modes_for`
(per-``(source, data_type)``), NOT the coarse per-source ``modes_for_source``, so a
shard where a source serves only a SUBSET of its modes is answered honestly. E.g.
hyperliquid is LIVE for ``trades``/``l2_book`` (it declares ``ws_*`` ops) but
REST/BATCH-only for ``funding_rates`` — so ``could_exist("cefi", "funding_rates",
Mode.LIVE)`` is ``False`` even though hyperliquid is a live source for OTHER
data_types. The refinement derives from the per-operation
``SourceCapability.operations`` ws/REST split (``registry/capability_declarations``)
— see :func:`modes_for`. ``data_type`` remains the shard dimension here; the fuller
``(asset_group, data_type, instrument_type)`` IS-catalogue shard key is a separate
follow-on (the ``instrument_type`` axis), tracked in the GATE-0 plan.

Source derivation
=================
:func:`sources_for_shard` derives the source set from
:data:`~unified_api_contracts.canonical.crosscutting.source_priority.SOURCE_PRIORITY`
(the batch-priority registry, keyed ``(asset_group, data_type)``) UNION the CeFi
per-venue live/replay overlay (:data:`~unified_api_contracts.canonical.crosscutting.source_priority.CEFI_LIVE_VENUES`).
The overlay matters because a CeFi shard's SOURCE_PRIORITY entry lists only the
BATCH source (``tardis`` — a batch-only source); its LIVE/REPLAY source is the
EXCHANGE (``binance``/``deribit``/…), which is NOT in SOURCE_PRIORITY. Without the
overlay every CeFi shard would read as batch-only — wrong. The ``DataTypeCapability``
registry's ``sources`` field (``registry/data_type_capability.py``) is NOT unioned
in: that field holds ADAPTER FILE PATHS (e.g.
``"market_tick_data_service/.../binance/"``), a different vocabulary from the
``data_source`` strings :func:`modes_for_source` is keyed on — unioning it would
inject non-source tokens that ``modes_for_source`` would mode-default to ``{BATCH}``.
"""

from __future__ import annotations

from unified_api_contracts.canonical.crosscutting._source_priority_data import (
    CEFI_LIVE_VENUES,
    SOURCE_PRIORITY,
)
from unified_api_contracts.canonical.crosscutting.pipeline_mode import Mode
from unified_api_contracts.canonical.crosscutting.source_priority import modes_for

_CEFI_ASSET_GROUP = "cefi"


def sources_for_shard(asset_group: str, data_type: str) -> frozenset[str]:
    """Return the ``data_source``s that serve a ``(asset_group, data_type)`` shard.

    Derived from :data:`SOURCE_PRIORITY` (the batch-priority registry) UNION the
    CeFi per-venue live/replay overlay (:data:`CEFI_LIVE_VENUES`). The overlay
    only applies to ``cefi`` shards — a CeFi shard's SOURCE_PRIORITY entry lists
    only the BATCH source (``tardis``); its LIVE/REPLAY source is the exchange
    venue, which lives in :data:`CEFI_LIVE_VENUES`, not SOURCE_PRIORITY.

    Returns an EMPTY frozenset for an unregistered shard (non-raising — the
    membership/possibility question is a soft guardrail, distinct from
    :func:`~unified_api_contracts.canonical.crosscutting.source_priority.get_source_priority`
    which fails loud). An empty result means "no known source serves this shard"
    → :func:`could_exist` is ``False`` for every mode.

    Args:
        asset_group: ``cefi`` / ``defi`` / ``tradfi`` / ``prediction`` / ``sports``
            / ``reference``.
        data_type: Canonical data_type string.

    Returns:
        Frozenset of source strings (each a valid :func:`modes_for_source` key).
    """
    priority_sources = SOURCE_PRIORITY.get((asset_group, data_type), ())
    sources: set[str] = set(priority_sources)
    if asset_group == _CEFI_ASSET_GROUP:
        # The CeFi live/replay source is the EXCHANGE (tardis is batch-only); add
        # the per-venue overlay so a CeFi shard reads as live/replay-capable.
        sources |= CEFI_LIVE_VENUES
    return frozenset(sources)


def could_exist(asset_group: str, data_type: str, mode: Mode) -> bool:
    """True if ``mode`` is reachable for the ``(asset_group, data_type)`` shard.

    The M3 guardrail: a ``(shard, mode)`` combination is POSSIBLE iff at least one
    source serving the shard can run that mode FOR THIS data_type —
    ``any(mode in modes_for(s, data_type) for s in sources_for_shard(...))``. It
    calls the per-``(source, data_type)``
    :func:`~unified_api_contracts.canonical.crosscutting.source_priority.modes_for`
    (M2-REFINEMENT), NOT the coarse per-source ``modes_for_source`` — so a source
    that is live for SOME data_types but batch-only for this one (hyperliquid for
    ``funding_rates``) does not falsely make ``LIVE`` reachable. A writer /
    manifest-seeder / phantom-auditor asks this before materialising a
    ``{mode}_<source>`` cell so it never seeds an impossible row (e.g. a
    ``live_<source>`` cell for a shard whose sources only batch-archive that
    data_type) — an HONEST absence, not a silent placeholder.

    Returns ``False`` for an unregistered shard (no sources → nothing can run any
    mode) and for a registered shard whose every source lacks ``mode`` for this
    data_type.

    Args:
        asset_group: ``cefi`` / ``defi`` / ``tradfi`` / ``prediction`` / ``sports``
            / ``reference``.
        data_type: Canonical data_type string.
        mode: The reconciliation :class:`Mode` to test (``BATCH`` / ``LIVE`` /
            ``REPLAY``).

    Returns:
        ``True`` iff some source serving the shard supports ``mode`` for
        ``data_type``.
    """
    return any(mode in modes_for(source, data_type) for source in sources_for_shard(asset_group, data_type))


__all__ = [
    "could_exist",
    "sources_for_shard",
]
