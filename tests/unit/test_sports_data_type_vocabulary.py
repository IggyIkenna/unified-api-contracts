"""Closed-set guard: the sports data_type vocabulary must not contain
case-variant duplicate pairs.

sports_shard_enumeration_cartesian_blowup_2026_07_20.md Part 2 item 2.2.
``DATA_TYPES_BY_ASSET_GROUP["sports"]`` used to register BOTH ``"odds"`` and
``"ODDS"``, splitting one logical stream into two vocabulary entries.

K0-DECISION(b) was reversed 2026-07-22 (lowercase ``odds`` is canonical, not
uppercase ``ODDS`` — GCS physically holds only lowercase ``data_type=odds``
directories; uppercase ``ODDS`` was a manifest-only phantom with no backing
objects, per the same doc's §4.3). The uppercase ``"ODDS"`` entry was dropped
from ``DATA_TYPES_BY_ASSET_GROUP["sports"]`` 2026-07-26.

**``TRADES``/``trades`` is NOT a deliberate exception — this guard briefly
(2026-07-26) allowlisted it based on stale context.** K1 (``mtds@2536b91c``,
2026-07-22) had flipped the live writer to emit uppercase
``instrument_type=ODDS/data_type=TRADES``; that same day's later
reconciliation (``sports_consolidated_closeout_2026_07_19.md``, "Canonical
target") REVERSED K1/K2 and decided sports data_type/instrument_type is
lower-case for the WHOLE vocabulary, no UPPER exception at all. The allowlist
this test briefly carried was written without cross-referencing that later
decision — corrected 2026-07-27 alongside the writer/registry revert. This
guard is unconditional again: any case-variant pair, including a future
``TRADES``/``trades``, is a real bug.
"""

from __future__ import annotations

from unified_api_contracts.registry.market_data_categories import DATA_TYPES_BY_ASSET_GROUP


def test_sports_data_type_set_has_no_case_variant_pairs() -> None:
    """Every logical sports data_type stream must appear exactly once — never
    as both an UPPER and a lower spelling (e.g. ``ODDS``/``odds``).
    """
    sports_data_types = DATA_TYPES_BY_ASSET_GROUP["sports"]
    assert len({d.lower() for d in sports_data_types}) == len(sports_data_types), (
        f"sports data_type vocabulary contains case-variant duplicate pairs: {sorted(sports_data_types)}"
    )
