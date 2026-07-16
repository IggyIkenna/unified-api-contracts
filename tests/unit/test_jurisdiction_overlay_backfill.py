"""Tests for the jurisdiction overlay registry (Wave-2 #12, 2026-06-13).

Validates that the JURISDICTION_VENUE_POLICIES registry is well-formed, that
every policy cites a source_note, that the filter is deterministic, and — the
load-bearing compliance invariant — that an unknown jurisdiction / unmodelled
pair returns a SAFE CONSERVATIVE DEFAULT (block + needs_legal_review), never
silently allowed.

Plan: ``plans/active/capability_wizard_and_manifest_2026_06_11.md`` Phase 2
"Registry backfills".
"""

from __future__ import annotations

from unified_api_contracts.internal.architecture_v2.jurisdiction_overlay import (
    JURISDICTION_VENUE_POLICIES,
    KNOWN_VENUE_IDS,
    Jurisdiction,
    JurisdictionAccess,
    allowed_venues_for_jurisdiction,
    is_venue_allowed,
)

# ---------------------------------------------------------------------------
# Registry well-formedness
# ---------------------------------------------------------------------------


def test_registry_non_empty() -> None:
    assert len(JURISDICTION_VENUE_POLICIES) > 0


def test_no_duplicate_venue_jurisdiction_pairs() -> None:
    """Each (venue, jurisdiction) appears at most once."""
    keys = [(p.venue_id, p.jurisdiction) for p in JURISDICTION_VENUE_POLICIES]
    assert len(keys) == len(set(keys)), "duplicate (venue, jurisdiction) rows"


def test_every_policy_venue_is_known() -> None:
    for p in JURISDICTION_VENUE_POLICIES:
        assert p.venue_id in KNOWN_VENUE_IDS, f"unknown venue in registry: {p.venue_id}"


def test_unknown_jurisdiction_never_in_seeded_policies() -> None:
    """No row carries the UNKNOWN jurisdiction (it is the unclassified bucket,
    handled by the conservative default, never seeded)."""
    for p in JURISDICTION_VENUE_POLICIES:
        assert p.jurisdiction is not Jurisdiction.UNKNOWN


# ---------------------------------------------------------------------------
# Provenance — every policy cites a source_note + reason
# ---------------------------------------------------------------------------


def test_every_policy_has_source_note() -> None:
    for p in JURISDICTION_VENUE_POLICIES:
        assert p.source_note.strip(), f"{p.venue_id}/{p.jurisdiction.value}: empty source_note"


def test_every_policy_has_reason() -> None:
    for p in JURISDICTION_VENUE_POLICIES:
        assert p.reason.strip(), f"{p.venue_id}/{p.jurisdiction.value}: empty reason"


def test_unknown_access_implies_needs_legal_review() -> None:
    """An UNKNOWN access row MUST be flagged for legal review (no silent
    uncertainty); ALLOWED/BLOCKED rows are NOT flagged."""
    for p in JURISDICTION_VENUE_POLICIES:
        if p.access is JurisdictionAccess.UNKNOWN:
            assert p.needs_legal_review, f"{p.venue_id}/{p.jurisdiction.value}: UNKNOWN without needs_legal_review"
        else:
            assert not p.needs_legal_review, (
                f"{p.venue_id}/{p.jurisdiction.value}: non-UNKNOWN row should not need legal review"
            )


# ---------------------------------------------------------------------------
# CONSERVATIVE DEFAULT — the compliance-critical invariant
# ---------------------------------------------------------------------------


def test_unknown_jurisdiction_blocks_every_venue() -> None:
    """An unknown/unclassified jurisdiction allows NOTHING (fail safe)."""
    assert allowed_venues_for_jurisdiction(Jurisdiction.UNKNOWN) == set()
    for venue in KNOWN_VENUE_IDS:
        allowed, reason = is_venue_allowed(venue, Jurisdiction.UNKNOWN)
        assert allowed is False
        assert "needs_legal_review" in reason.lower() or "unknown" in reason.lower()


def test_unmodelled_pair_blocks() -> None:
    """A venue with no policy row for a jurisdiction is BLOCKED, not allowed."""
    allowed, reason = is_venue_allowed("a_venue_that_does_not_exist", Jurisdiction.UK_FCA)
    assert allowed is False
    assert "needs_legal_review" in reason.lower()


def test_unknown_access_row_evaluates_to_blocked() -> None:
    """An UNKNOWN-access (needs_legal_review) row is never treated as allowed."""
    # gmx_v2 / US_CFTC is a seeded UNKNOWN row.
    allowed, reason = is_venue_allowed("gmx_v2", Jurisdiction.US_CFTC)
    assert allowed is False
    assert "blocked" in reason.lower()


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_filter_is_deterministic() -> None:
    for jur in Jurisdiction:
        first = allowed_venues_for_jurisdiction(jur)
        for _ in range(3):
            assert allowed_venues_for_jurisdiction(jur) == first


def test_allowed_venues_subset_of_known() -> None:
    for jur in Jurisdiction:
        assert allowed_venues_for_jurisdiction(jur) <= set(KNOWN_VENUE_IDS)


def test_allowed_set_consistent_with_is_venue_allowed() -> None:
    for jur in Jurisdiction:
        allowed_set = allowed_venues_for_jurisdiction(jur)
        for venue in KNOWN_VENUE_IDS:
            ok, _ = is_venue_allowed(venue, jur)
            assert (venue in allowed_set) is ok


# ---------------------------------------------------------------------------
# Load-bearing documented facts (the seeded BLOCKS / ALLOWS)
# ---------------------------------------------------------------------------


def test_us_persons_blocked_from_geofenced_cex() -> None:
    """The well-known US-person geofences are BLOCKED."""
    for venue in ("binance", "bybit", "okx", "deribit", "hyperliquid"):
        allowed, _ = is_venue_allowed(venue, Jurisdiction.US_CFTC)
        assert allowed is False, f"{venue} should be blocked for US persons"


def test_deribit_not_available_to_us_persons() -> None:
    allowed, reason = is_venue_allowed("deribit", Jurisdiction.US_CFTC)
    assert allowed is False
    assert "us person" in reason.lower() or "deribit" in reason.lower()


def test_uk_and_cayman_home_entities_have_venue_access() -> None:
    """UK_FCA and CAYMAN home entities have documented access to the CEX set."""
    for jur in (Jurisdiction.UK_FCA, Jurisdiction.CAYMAN):
        allowed = allowed_venues_for_jurisdiction(jur)
        assert {"binance", "bybit", "okx", "deribit"} <= allowed, jur


def test_us_persons_get_fewer_venues_than_home_entity() -> None:
    us = allowed_venues_for_jurisdiction(Jurisdiction.US_CFTC)
    uk = allowed_venues_for_jurisdiction(Jurisdiction.UK_FCA)
    assert len(us) < len(uk)


def test_retail_restricted_blocks_derivative_venues() -> None:
    """A retail-restricted entity sees no leveraged-derivative venues.

    "drift" (Solana perp DEX) removed from this set 2026-07-16 (operator ruling: all Solana
    perp DEXes dropped except Jupiter, not integrated) — it is no longer a KNOWN_VENUE_ID at
    all, so asserting it "not in allowed" would pass vacuously off the absence-default rather
    than exercising a real RETAIL_RESTRICTED _block row. The remaining venues below each carry
    an explicit _block(..., Jurisdiction.RETAIL_RESTRICTED, ...) row, so coverage stays real.
    """
    allowed = allowed_venues_for_jurisdiction(Jurisdiction.RETAIL_RESTRICTED)
    for venue in ("binance", "bybit", "okx", "deribit", "hyperliquid", "gmx_v2"):
        assert venue not in allowed, f"{venue} must be blocked for RETAIL_RESTRICTED"


def test_allowed_returns_reason_prefix() -> None:
    """An ALLOWED verdict carries an ALLOWED-prefixed reason."""
    allowed, reason = is_venue_allowed("binance", Jurisdiction.UK_FCA)
    assert allowed is True
    assert reason.startswith("ALLOWED")
