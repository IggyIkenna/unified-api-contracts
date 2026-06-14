"""Tests for the OFFERED_SIGNING_SURFACES registry (Wave A, F49 re-kind).

Validates that the registry is well-formed, every entry cites its source, the
schema REUSES the existing ``SigningSurface`` enum (no duplicate enum), and the
documented rollout statuses are correct (CLOUD_KMS_ENCRYPTED = active_may23,
FIREBLOCKS_MPC = out_of_scope).

Plan: ``plans/active/issues/capability_wizard_analysis_findings_2026_06_11.md``
Wave A (F49).
"""

from __future__ import annotations

from unified_api_contracts.internal.architecture_v2.custody_surfaces import (
    CEFFU_ROUTES_VIA_COPPER_NOTE,
    OFFERED_SIGNING_SURFACES,
    SigningSurfacePolicy,
    SigningSurfaceStatus,
    surface_policy_for,
)
from unified_api_contracts.internal.domain.defi.wallet_config import SigningSurface

# ---------------------------------------------------------------------------
# Well-formedness
# ---------------------------------------------------------------------------


def _by_surface(surface: SigningSurface) -> SigningSurfacePolicy:
    return next(p for p in OFFERED_SIGNING_SURFACES if p.surface == surface)


def test_registry_non_empty_and_unique() -> None:
    """Registry is seeded and has no duplicate surfaces."""
    assert OFFERED_SIGNING_SURFACES
    surfaces = [p.surface for p in OFFERED_SIGNING_SURFACES]
    assert len(surfaces) == len(set(surfaces))


def test_every_entry_is_well_typed() -> None:
    for p in OFFERED_SIGNING_SURFACES:
        assert isinstance(p, SigningSurfacePolicy)
        assert isinstance(p.surface, SigningSurface)
        assert isinstance(p.status, SigningSurfaceStatus)
        assert isinstance(p.asset_groups, tuple)


# ---------------------------------------------------------------------------
# Provenance — every entry cites custody-providers.md
# ---------------------------------------------------------------------------


def test_every_entry_cites_source() -> None:
    """Every offered surface carries a non-empty custody-providers.md citation."""
    for p in OFFERED_SIGNING_SURFACES:
        assert p.source_note.strip(), f"{p.surface}: empty source_note"
        assert "custody-providers.md" in p.source_note, p.surface


# ---------------------------------------------------------------------------
# Enum reuse — NO duplicate SigningSurface enum
# ---------------------------------------------------------------------------


def test_reuses_existing_signing_surface_enum() -> None:
    """The schema's surface field is the EXISTING UAC SigningSurface enum.

    Re-export identity check: the symbol exported from custody_surfaces is the
    same object as the canonical wallet_config.SigningSurface (not a redefinition).
    """
    from unified_api_contracts.internal.architecture_v2 import custody_surfaces
    from unified_api_contracts.internal.domain.defi import wallet_config

    assert custody_surfaces.SigningSurface is wallet_config.SigningSurface
    # Every seeded surface is a genuine member of that one enum.
    for p in OFFERED_SIGNING_SURFACES:
        assert p.surface in set(SigningSurface)


# ---------------------------------------------------------------------------
# Documented-status spot checks (the load-bearing facts)
# ---------------------------------------------------------------------------


def test_cloud_kms_is_active_may23() -> None:
    """May-23 cutover ships on CLOUD_KMS_ENCRYPTED (custody-providers.md § R9)."""
    kms = _by_surface(SigningSurface.CLOUD_KMS_ENCRYPTED)
    assert kms.status is SigningSurfaceStatus.ACTIVE_MAY23
    assert "defi" in kms.asset_groups


def test_copper_is_active_june1() -> None:
    copper = _by_surface(SigningSurface.COPPER_MPC)
    assert copper.status is SigningSurfaceStatus.ACTIVE_JUNE1


def test_fireblocks_is_out_of_scope() -> None:
    """Fireblocks is OUT OF SCOPE per POD stack choice (custody-providers.md)."""
    fb = _by_surface(SigningSurface.FIREBLOCKS_MPC)
    assert fb.status is SigningSurfaceStatus.OUT_OF_SCOPE
    assert fb.asset_groups == ()


# ---------------------------------------------------------------------------
# Honest exclusions — dev/test surfaces + CEFFU not offered
# ---------------------------------------------------------------------------


def test_dev_test_surfaces_not_offered() -> None:
    """LOCAL_KEY / MOCK are dev/test only — not in the OFFERED registry."""
    assert surface_policy_for(SigningSurface.LOCAL_KEY) is None
    assert surface_policy_for(SigningSurface.MOCK) is None


def test_ceffu_documented_as_routes_via_copper() -> None:
    """CEFFU has no SigningSurface enum member — documented, not invented."""
    assert "CEFFU" in CEFFU_ROUTES_VIA_COPPER_NOTE
    assert "Copper" in CEFFU_ROUTES_VIA_COPPER_NOTE
    assert not hasattr(SigningSurface, "CEFFU")
