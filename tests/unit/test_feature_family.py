"""Unit tests for the ``FeatureFamily`` enum + ``FEATURE_GROUP_TO_FAMILY``
registry shipped in Phase 1A of ``features_repo_consolidation_2026_05_08``.

The plan invariants asserted here:

1. ``FeatureFamily`` is a closed set of exactly 8 values matching the
   ``features-{family}-service`` repos.
2. Every ``feature_group`` declared in ``EXPECTED_FEATURE_GROUPS_BY_SERVICE``
   maps to exactly ONE ``FeatureFamily`` (no orphans, no cross-family
   collisions).
3. JSON round-trip (encode + decode) preserves the canonical string value.

Plan: ``unified-trading-pm/plans/active/features_repo_consolidation_2026_05_08.plan.md``
Phase 1A.
"""

from __future__ import annotations

import json

from unified_api_contracts.canonical.domain.features import (
    EXPECTED_FEATURE_GROUPS_BY_SERVICE,
    FEATURE_GROUP_TO_FAMILY,
    FeatureFamily,
    get_feature_family,
    is_known_feature_family,
)

# ---------------------------------------------------------------------------
# Invariant 1 — ``FeatureFamily`` is a closed set of exactly 8 values.
# ---------------------------------------------------------------------------


def test_feature_family_closed_set() -> None:
    """``FeatureFamily`` enumerates EXACTLY the 8 values declared in the plan."""
    expected = {
        FeatureFamily.CALENDAR,
        FeatureFamily.COMMODITY,
        FeatureFamily.CROSS_INSTRUMENT,
        FeatureFamily.DELTA_ONE,
        FeatureFamily.MULTI_TIMEFRAME,
        FeatureFamily.ONCHAIN,
        FeatureFamily.SPORTS,
        FeatureFamily.VOLATILITY,
    }
    assert set(FeatureFamily) == expected
    assert len(FeatureFamily) == 8


def test_feature_family_string_values_are_canonical_lower_snake() -> None:
    """Every member value is the canonical lower_snake form so manifest
    columns and deployment-api filter strings round-trip cleanly."""
    expected_values = {
        "calendar",
        "commodity",
        "cross_instrument",
        "delta_one",
        "multi_timeframe",
        "onchain",
        "sports",
        "volatility",
    }
    assert {member.value for member in FeatureFamily} == expected_values


# ---------------------------------------------------------------------------
# Invariant 2 — every feature_group maps to exactly ONE FeatureFamily.
# ---------------------------------------------------------------------------


def test_feature_group_to_family_no_orphans() -> None:
    """Every value in ``EXPECTED_FEATURE_GROUPS_BY_SERVICE`` appears in
    ``FEATURE_GROUP_TO_FAMILY`` and maps to a real ``FeatureFamily`` member."""
    declared: set[str] = set()
    for groups in EXPECTED_FEATURE_GROUPS_BY_SERVICE.values():
        declared.update(groups)
    mapped = set(FEATURE_GROUP_TO_FAMILY)
    missing = declared - mapped
    assert not missing, f"feature_groups declared but absent from FEATURE_GROUP_TO_FAMILY: {sorted(missing)}"
    extra = mapped - declared
    assert not extra, (
        f"FEATURE_GROUP_TO_FAMILY contains feature_groups not in EXPECTED_FEATURE_GROUPS_BY_SERVICE: {sorted(extra)}"
    )


def test_feature_group_to_family_values_are_feature_family_members() -> None:
    """Every dict value is a real ``FeatureFamily`` member (not a string)."""
    for feature_group, family in FEATURE_GROUP_TO_FAMILY.items():
        assert isinstance(family, FeatureFamily), (
            f"FEATURE_GROUP_TO_FAMILY[{feature_group!r}] = {family!r} is not a FeatureFamily member"
        )


def test_feature_group_to_family_matches_owning_service() -> None:
    """Every feature_group declared in EXPECTED_FEATURE_GROUPS_BY_SERVICE has
    an explicit FeatureFamily assignment in FEATURE_GROUP_TO_FAMILY.

    After features-{family}-service consolidation to features-service, the
    family can no longer be derived from service name — it is explicitly
    declared in _GROUP_FAMILY_MAP. This test verifies no group is left
    untagged (orphaned) after the consolidation.
    """
    all_declared: set[str] = set()
    for groups in EXPECTED_FEATURE_GROUPS_BY_SERVICE.values():
        all_declared.update(groups)
    for group in all_declared:
        family = FEATURE_GROUP_TO_FAMILY.get(group)
        assert family is not None, (
            f"feature_group {group!r} is declared in EXPECTED_FEATURE_GROUPS_BY_SERVICE "
            "but has no FeatureFamily assignment in FEATURE_GROUP_TO_FAMILY"
        )
        assert isinstance(family, FeatureFamily), (
            f"FEATURE_GROUP_TO_FAMILY[{group!r}] = {family!r} is not a FeatureFamily member"
        )


def test_get_feature_family_round_trip() -> None:
    """``get_feature_family`` matches direct dict access for known groups
    and returns ``None`` for unknown groups."""
    for feature_group, family in FEATURE_GROUP_TO_FAMILY.items():
        assert get_feature_family(feature_group) == family
    assert get_feature_family("definitely-not-a-real-feature-group") is None


def test_is_known_feature_family_round_trip() -> None:
    """``is_known_feature_family`` is True for every member's string value
    and False for unregistered strings."""
    for member in FeatureFamily:
        assert is_known_feature_family(member.value) is True
    assert is_known_feature_family("not_a_family") is False
    # Case-sensitive: uppercase form is NOT a member value.
    assert is_known_feature_family("ONCHAIN") is False


# ---------------------------------------------------------------------------
# Invariant 3 — JSON round-trip preserves the canonical string value.
# ---------------------------------------------------------------------------


def test_feature_family_json_round_trip_single_value() -> None:
    """``FeatureFamily.<member>.value`` survives a JSON encode/decode cycle."""
    for member in FeatureFamily:
        encoded = json.dumps(member.value)
        decoded = json.loads(encoded)
        assert decoded == member.value
        # And the round-tripped string is recognised by is_known_feature_family.
        assert is_known_feature_family(decoded) is True


def test_feature_family_json_round_trip_manifest_row_shape() -> None:
    """A manifest row carrying ``feature_family`` + ``feature_group`` round-trips
    through JSON cleanly (the on-the-wire shape between writer + reader)."""
    row: dict[str, str | None] = {
        "feature_group": "lst_staking_yields",
        "feature_family": FeatureFamily.ONCHAIN.value,
    }
    decoded = json.loads(json.dumps(row))
    assert decoded["feature_group"] == "lst_staking_yields"
    assert decoded["feature_family"] == "onchain"
    assert get_feature_family(decoded["feature_group"]) == FeatureFamily.ONCHAIN
