"""Closed-set guard: the sports data_type vocabulary must not contain
case-variant duplicate pairs.

sports_shard_enumeration_cartesian_blowup_2026_07_20.md Part 2 item 2.2.
``DATA_TYPES_BY_ASSET_GROUP["sports"]`` currently registers BOTH ``"odds"``
and ``"ODDS"`` (and would have the same issue for any other case-duplicated
member), splitting one logical stream into two vocabulary entries.

This guard is SKIPPED for now (TODO(K0-b) below) — the operator has decided
(2026-07-2x, live chat, not yet codified when this test was written) to
REVERSE K0-DECISION(b) in
``unified-trading-pm/codex/02-data/sports-data-types-catalog.md`` (lowercase
``odds`` is canonical, not uppercase ``ODDS`` — GCS physically holds only
lowercase ``data_type=odds`` directories on every sampled day; uppercase
``ODDS`` is a manifest-only phantom with no backing objects). That reversal,
plus Part 3 item 3.4 (dropping the phantom uppercase ``ODDS`` manifest rows),
must land before ``DATA_TYPES_BY_ASSET_GROUP["sports"]`` itself can drop the
uppercase case-variant members this test asserts are absent.
"""

from __future__ import annotations

import pytest

from unified_api_contracts.registry.market_data_categories import DATA_TYPES_BY_ASSET_GROUP

# reason: TODO(K0-b) — unskip once sports-data-types-catalog.md K0-DECISION(b) is reversed
# (lowercase 'odds' becomes the codified canonical form) AND Part 3 item 3.4 (dropping the
# phantom uppercase ODDS manifest rows) has landed, so the case-variant duplicate members can
# actually be removed from DATA_TYPES_BY_ASSET_GROUP['sports'] without contradicting a
# still-live codex decision. See unified-trading-pm/plans/active/issues/
# sports_shard_enumeration_cartesian_blowup_2026_07_20.md Part 2 items 2.1/2.2/3.4.
_SKIP_REASON_K0B = (
    "TODO(K0-b): unskip once sports-data-types-catalog.md K0-DECISION(b) is reversed "
    "(lowercase 'odds' becomes the codified canonical form) AND Part 3 item 3.4 "
    "(dropping the phantom uppercase ODDS manifest rows) has landed, so the case-variant "
    "duplicate members can actually be removed from DATA_TYPES_BY_ASSET_GROUP['sports'] "
    "without contradicting a still-live codex decision. "
    "See unified-trading-pm/plans/active/issues/"
    "sports_shard_enumeration_cartesian_blowup_2026_07_20.md Part 2 items 2.1/2.2/3.4."
)


@pytest.mark.skip(reason=_SKIP_REASON_K0B)
def test_sports_data_type_set_has_no_case_variant_pairs() -> None:
    """Every logical sports data_type stream must appear exactly once — never
    as both an UPPER and a lower spelling (e.g. ``ODDS``/``odds``).

    Currently FAILS (hence the skip above): ``DATA_TYPES_BY_ASSET_GROUP["sports"]``
    registers both ``"odds"`` and ``"ODDS"`` as case-variant duplicates.
    """
    sports_data_types = DATA_TYPES_BY_ASSET_GROUP["sports"]
    assert len({d.lower() for d in sports_data_types}) == len(sports_data_types), (
        f"sports data_type vocabulary contains case-variant duplicate pairs: {sorted(sports_data_types)}"
    )
