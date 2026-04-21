"""Archetype capability registry parity + structural invariants.

G1.8 — guarantees the committed manifest JSON is a deterministic
round-trip of the live registry, every ``StrategyArchetype`` enum
member is represented, the family mapping matches
``ARCHETYPE_TO_FAMILY``, and the codex narrative markdown
(``category-instrument-coverage.md``) contains a matching section for
every registered archetype.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

from unified_api_contracts.internal.architecture_v2.archetype_capability import (
    ARCHETYPE_CAPABILITY_REGISTRY,
    ArchetypeInstrumentType,
    CoverageStatus,
    all_capabilities,
    archetypes_for_pair,
    archetypes_for_venue,
    capability_for,
)
from unified_api_contracts.internal.architecture_v2.enums import (
    ARCHETYPE_TO_FAMILY,
    StrategyArchetype,
    StrategyFamily,
    VenueCategoryV2,
)


def _find_codex_markdown() -> Path | None:
    """Resolve ``category-instrument-coverage.md`` via workspace root or repo-sibling lookup.

    Returns ``None`` when UAC is running in true isolation (e.g. an
    ephemeral CI container without the PM checkout). Every other context
    resolves to the real file and enforces parity.
    """

    rel = Path("unified-trading-pm/codex/09-strategy/architecture-v2/category-instrument-coverage.md")
    env_root = os.environ.get("UNIFIED_TRADING_WORKSPACE_ROOT")
    if env_root:
        candidate = Path(env_root) / rel
        if candidate.is_file():
            return candidate
    # Fall back to UAC repo's parent (standard multi-repo workspace layout).
    here = Path(__file__).resolve()
    for ancestor in here.parents:
        candidate = ancestor / rel
        if candidate.is_file():
            return candidate
    return None


def test_registry_has_eighteen_archetypes() -> None:
    assert len(ARCHETYPE_CAPABILITY_REGISTRY) == 18
    assert len(all_capabilities()) == 18


def test_every_strategy_archetype_v2_member_is_represented() -> None:
    registered = {entry.archetype_id for entry in ARCHETYPE_CAPABILITY_REGISTRY}
    expected = set(StrategyArchetype)
    assert registered == expected, f"missing: {expected - registered}; extra: {registered - expected}"


def test_family_assignment_matches_uac_canonical_mapping() -> None:
    for entry in ARCHETYPE_CAPABILITY_REGISTRY:
        assert entry.family == ARCHETYPE_TO_FAMILY[entry.archetype_id], (
            f"family mismatch for {entry.archetype_id}: "
            f"registry={entry.family}, canonical={ARCHETYPE_TO_FAMILY[entry.archetype_id]}"
        )


def test_capability_for_returns_none_for_unknown_lookup_via_filter() -> None:
    for member in StrategyArchetype:
        assert capability_for(member) is not None


def test_cefi_perp_query_returns_expected_archetypes() -> None:
    # Spot-check the CeFi x Perp slice. Expected set derived from
    # coverage.ts declarations + drift test catches changes.
    result = archetypes_for_pair(VenueCategoryV2.CEFI, ArchetypeInstrumentType.PERP)
    result_ids = {entry.archetype_id for entry in result}
    # Must contain the three "obvious" archetypes — regression guard.
    assert StrategyArchetype.CARRY_BASIS_PERP in result_ids
    assert StrategyArchetype.MARKET_MAKING_CONTINUOUS in result_ids
    assert StrategyArchetype.ML_DIRECTIONAL_CONTINUOUS in result_ids


def test_archetypes_for_pair_excludes_partial_when_requested() -> None:
    supported_only = archetypes_for_pair(
        VenueCategoryV2.DEFI,
        ArchetypeInstrumentType.PERP,
        include_partial=False,
    )
    with_partial = archetypes_for_pair(VenueCategoryV2.DEFI, ArchetypeInstrumentType.PERP)
    assert len(supported_only) <= len(with_partial)
    for entry in supported_only:
        assert (VenueCategoryV2.DEFI, ArchetypeInstrumentType.PERP) in entry.supported_pairs


def test_pair_status_sets_cover_every_declared_cell() -> None:
    # A single (category, instrument_type) pair can appear in >1 status set
    # when different venues have different statuses (e.g.
    # ML_DIRECTIONAL_EVENT_SETTLED / PREDICTION / event_settled is
    # SUPPORTED on Polymarket but BLOCKED on Kalshi). The invariant we
    # enforce is coverage — every cell's pair lands in at least one of
    # the three derived sets.
    for entry in ARCHETYPE_CAPABILITY_REGISTRY:
        union = entry.supported_pairs | entry.partial_pairs | entry.blocked_pairs
        for cell in entry.cells:
            assert (cell.category, cell.instrument_type) in union


def test_blocked_cells_carry_block_list_refs() -> None:
    for entry in ARCHETYPE_CAPABILITY_REGISTRY:
        for cell in entry.cells:
            if cell.status == CoverageStatus.BLOCKED:
                assert cell.block_list_refs, (
                    f"BLOCKED cell without block_list_refs: {entry.archetype_id}/{cell.category}/{cell.instrument_type}"
                )


def test_archetypes_for_venue_handles_known_venue() -> None:
    # Binance is declared on many CeFi cells.
    result = archetypes_for_venue("binance")
    assert len(result) > 0
    # Kalshi is declared but only on BLOCKED cells → not returned by
    # ``supported_venues`` (which excludes BLOCKED).
    assert archetypes_for_venue("kalshi") == ()


def test_event_driven_archetype_and_family_resolve_distinctly() -> None:
    # StrategyArchetype.EVENT_DRIVEN shares its token with the family
    # StrategyFamily.EVENT_DRIVEN — guard against accidental collapse.
    entry = capability_for(StrategyArchetype.EVENT_DRIVEN)
    assert entry is not None
    assert entry.archetype_id is StrategyArchetype.EVENT_DRIVEN
    assert entry.family is StrategyFamily.EVENT_DRIVEN
    assert entry.archetype_id.value == entry.family.value == "EVENT_DRIVEN"


def test_manifest_is_round_trip_stable() -> None:
    # Re-serialise the live registry and compare against the committed file.
    from scripts.generate_archetype_capability_manifest import MANIFEST_PATH, render_json

    rendered = render_json()
    committed = MANIFEST_PATH.read_text(encoding="utf-8")
    assert rendered == committed, (
        "archetype_capability_manifest.json drifted from the live registry. "
        "Run: python scripts/generate_archetype_capability_manifest.py --write"
    )


def test_every_supported_cell_has_at_least_one_venue() -> None:
    for entry in ARCHETYPE_CAPABILITY_REGISTRY:
        for cell in entry.cells:
            if cell.status == CoverageStatus.SUPPORTED:
                assert cell.venue_ids, (
                    f"SUPPORTED cell without venues: {entry.archetype_id}/{cell.category}/{cell.instrument_type}"
                )


# ---------------------------------------------------------------------------
# Codex narrative markdown parity
# ---------------------------------------------------------------------------


_ARCHETYPE_HEADER_RE = re.compile(r"^###\s+\d+\.\s+`([A-Z_]+)`", re.MULTILINE)
_FAMILY_HEADER_RE = re.compile(r"^##\s+Family\s+\d+:\s+(.+?)\s*$", re.MULTILINE)
_FAMILY_NAME_TO_ENUM = {
    "ML Directional": StrategyFamily.ML_DIRECTIONAL,
    "Rules Directional": StrategyFamily.RULES_DIRECTIONAL,
    "Carry & Yield": StrategyFamily.CARRY_AND_YIELD,
    "Arbitrage / Structural": StrategyFamily.ARBITRAGE_STRUCTURAL,
    "Market Making": StrategyFamily.MARKET_MAKING,
    "Event-Driven": StrategyFamily.EVENT_DRIVEN,
    "Vol Trading": StrategyFamily.VOL_TRADING,
    "Stat Arb / Pairs": StrategyFamily.STAT_ARB_PAIRS,
}


def test_codex_markdown_has_section_for_every_registered_archetype() -> None:
    path = _find_codex_markdown()
    if path is None:
        pytest.skip("codex category-instrument-coverage.md not reachable from UAC repo")

    text = path.read_text(encoding="utf-8")
    codex_archetypes = {match.group(1) for match in _ARCHETYPE_HEADER_RE.finditer(text)}
    registered = {entry.archetype_id.value for entry in ARCHETYPE_CAPABILITY_REGISTRY}

    missing_from_codex = registered - codex_archetypes
    extra_in_codex = codex_archetypes - registered
    assert not missing_from_codex, (
        f"codex missing archetype sections for: {sorted(missing_from_codex)}. "
        f"Add `### N. `<ARCHETYPE>`` headers to "
        f"codex/09-strategy/architecture-v2/category-instrument-coverage.md."
    )
    assert not extra_in_codex, (
        f"codex lists archetypes not in UAC registry: {sorted(extra_in_codex)}. "
        f"Either add to UAC manifest or remove from codex."
    )


def test_codex_markdown_family_groupings_match_uac_family_enum() -> None:
    path = _find_codex_markdown()
    if path is None:
        pytest.skip("codex category-instrument-coverage.md not reachable from UAC repo")

    text = path.read_text(encoding="utf-8")
    family_names = [match.group(1).strip() for match in _FAMILY_HEADER_RE.finditer(text)]
    assert family_names, "no `## Family N: ...` headers found in codex"

    unknown = [name for name in family_names if name not in _FAMILY_NAME_TO_ENUM]
    assert not unknown, (
        f"codex declares family names not in test's name→enum mapping: {unknown}. "
        f"Update ``_FAMILY_NAME_TO_ENUM`` in this test when you rename a family."
    )

    codex_family_enums = {_FAMILY_NAME_TO_ENUM[name] for name in family_names}
    registry_families = {entry.family for entry in ARCHETYPE_CAPABILITY_REGISTRY}
    assert codex_family_enums == registry_families, (
        f"family mismatch — codex={sorted(f.value for f in codex_family_enums)}, "
        f"registry={sorted(f.value for f in registry_families)}"
    )


def test_codex_markdown_archetype_appears_under_correct_family_section() -> None:
    path = _find_codex_markdown()
    if path is None:
        pytest.skip("codex category-instrument-coverage.md not reachable from UAC repo")

    text = path.read_text(encoding="utf-8")

    # Walk headers in document order; track current family context.
    family_pattern = re.compile(
        r"^##\s+Family\s+\d+:\s+(.+?)\s*$|^###\s+\d+\.\s+`([A-Z_]+)`",
        re.MULTILINE,
    )

    current_family: StrategyFamily | None = None
    codex_family_by_archetype: dict[str, StrategyFamily] = {}
    for match in family_pattern.finditer(text):
        family_name, archetype_id = match.group(1), match.group(2)
        if family_name is not None:
            family_name = family_name.strip()
            current_family = _FAMILY_NAME_TO_ENUM.get(family_name)
        elif archetype_id is not None and current_family is not None:
            codex_family_by_archetype[archetype_id] = current_family

    for entry in ARCHETYPE_CAPABILITY_REGISTRY:
        codex_family = codex_family_by_archetype.get(entry.archetype_id.value)
        assert codex_family is not None, f"codex has no family section containing archetype {entry.archetype_id.value}"
        assert codex_family == entry.family, (
            f"archetype {entry.archetype_id.value} — codex says "
            f"family={codex_family.value} but registry says {entry.family.value}"
        )
