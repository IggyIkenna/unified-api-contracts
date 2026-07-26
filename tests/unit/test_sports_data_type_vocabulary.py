"""Closed-set guard: the sports data_type vocabulary must not contain
ACCIDENTAL case-variant duplicate pairs.

sports_shard_enumeration_cartesian_blowup_2026_07_20.md Part 2 item 2.2.
``DATA_TYPES_BY_ASSET_GROUP["sports"]`` used to register BOTH ``"odds"`` and
``"ODDS"``, splitting one logical stream into two vocabulary entries.

**UNSKIPPED 2026-07-26**: K0-DECISION(b) was reversed 2026-07-22 (lowercase
``odds`` is canonical, not uppercase ``ODDS`` — GCS physically holds only
lowercase ``data_type=odds`` directories; uppercase ``ODDS`` was a
manifest-only phantom with no backing objects, per the same doc's §4.3). The
uppercase ``"ODDS"`` entry has been dropped from
``DATA_TYPES_BY_ASSET_GROUP["sports"]``. Note this guard only asserts the
CODE-level registry is consistent — the phantom uppercase ``ODDS`` manifest
rows themselves (Part 3 item 3.4) remain gated on the standing human-only
prod-bucket-write trigger and are tracked separately.

**``TRADES``/``trades`` is a DELIBERATE, separately-decided exception, not a
bug this guard should catch.** Unlike the accidental ``ODDS``/``odds``
duplication, ``TRADES`` (K1, ``mtds@2536b91c``, 2026-07-22) is a genuinely
different logical stream registered under a case-variant name on purpose —
see the registry's own comment block at ``DATA_TYPES_BY_ASSET_GROUP["sports"]``
for the full rationale (post-kickoff in-play quotes vs. pre-match ``trades``,
kept inert for the live fleet via 3 deliberate non-registrations elsewhere).
Blindly extending this guard to also flag that pair would either force
deleting a settled, cited decision outside this test's scope, or force a
skip again — instead this test allowlists exactly that one documented pair
and still catches ANY other case-variant duplicate (which is what actually
caught the original ``ODDS``/``odds`` bug).
"""

from __future__ import annotations

from unified_api_contracts.registry.market_data_categories import DATA_TYPES_BY_ASSET_GROUP

# The one deliberate, decided exception (see module docstring) -- both
# spellings of `.lower()` are allowed to coexist for this logical stream.
_DELIBERATE_CASE_VARIANT_EXCEPTIONS: frozenset[str] = frozenset({"trades"})


def test_sports_data_type_set_has_no_case_variant_pairs() -> None:
    """Every logical sports data_type stream must appear exactly once — never
    as both an UPPER and a lower spelling (e.g. ``ODDS``/``odds``) — except
    the one documented, deliberate exception (``TRADES``/``trades``, see
    module docstring).
    """
    sports_data_types = DATA_TYPES_BY_ASSET_GROUP["sports"]
    checked = [d for d in sports_data_types if d.lower() not in _DELIBERATE_CASE_VARIANT_EXCEPTIONS]
    assert len({d.lower() for d in checked}) == len(checked), (
        f"sports data_type vocabulary contains undocumented case-variant duplicate pairs: {sorted(checked)}"
    )
