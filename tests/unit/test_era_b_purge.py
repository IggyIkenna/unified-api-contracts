"""Unit tests for the Era-B legacy-read retirement purge guard.

Proves :func:`assert_era_b_purge_safe` passes for the LIVE registries today (so the
closed-set is purge-ready), that it actually catches a broken purge, and that the
live registries are NOT mutated by the in-memory simulation.
"""

from __future__ import annotations

import pytest

from unified_api_contracts.canonical.crosscutting.availability_semantics import (
    AVAILABILITY_AT_SEMANTICS,
)
from unified_api_contracts.canonical.crosscutting.era_b_legacy_purge import (
    ERA_B_LEGACY_ASSET_GROUPS,
    ERA_B_LEGACY_DATA_TYPES,
    ERA_B_PURGEABLE_KEYS,
    assert_era_b_purge_safe,
)
from unified_api_contracts.canonical.crosscutting.source_priority import (
    SOURCE_PRIORITY,
)


def test_full_fleet_purge_is_safe_today() -> None:
    """The full cefi+tradfi options_chain/futures_chain purge keeps every
    closed-set round-trip intact for the live registries."""
    assert_era_b_purge_safe()  # default = ERA_B_PURGEABLE_KEYS, must not raise


@pytest.mark.parametrize("asset_group", sorted(ERA_B_LEGACY_ASSET_GROUPS))
def test_single_asset_group_purge_is_safe(asset_group: str) -> None:
    """A single-AG migrator dropping only its own legacy entries is also safe."""
    keys = frozenset((asset_group, dt) for dt in ERA_B_LEGACY_DATA_TYPES)
    assert_era_b_purge_safe(keys)


def test_purgeable_keys_are_present_in_both_registries() -> None:
    """Sanity: the keys the migrators drop actually exist in BOTH registries today
    (they are the retained-for-round-trip legacy entries)."""
    for key in ERA_B_PURGEABLE_KEYS:
        assert key in SOURCE_PRIORITY, f"{key} missing from SOURCE_PRIORITY"
        assert key in AVAILABILITY_AT_SEMANTICS, f"{key} missing from AVAILABILITY_AT_SEMANTICS"


def test_guard_does_not_mutate_live_registries() -> None:
    """The in-memory simulation must NEVER touch the live dicts."""
    before_priority = dict(SOURCE_PRIORITY)
    before_availability = dict(AVAILABILITY_AT_SEMANTICS)
    assert_era_b_purge_safe()
    assert before_priority == SOURCE_PRIORITY
    assert before_availability == AVAILABILITY_AT_SEMANTICS


def test_guard_catches_broken_symmetry(monkeypatch: pytest.MonkeyPatch) -> None:
    """If the registries become asymmetric (a SOURCE_PRIORITY key with no
    AVAILABILITY_AT_SEMANTICS twin), the guard's symmetry check must fire — this is
    exactly the breakage a careless legacy drop could introduce. Modelled by
    monkeypatching an unmatched key into SOURCE_PRIORITY for the duration."""
    import unified_api_contracts.canonical.crosscutting.source_priority as sp_mod

    broken = dict(sp_mod.SOURCE_PRIORITY)
    broken[("cefi", "era_b_guard_unmatched_xyz")] = ["tardis"]  # no AVAILABILITY twin
    monkeypatch.setattr(sp_mod, "SOURCE_PRIORITY", broken)
    with pytest.raises(AssertionError, match="symmetry"):
        assert_era_b_purge_safe()
