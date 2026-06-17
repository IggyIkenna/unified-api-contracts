"""Lock the canonical names + legacy aliases for vault / yield-bearing DeFi
venues — MORPHOVAULTS, YEARN_V3, FRAX, MAKER (added 2026-05-06 as part of
Phase 1.5a-1 of plans/active/market_tick_data_to_100pct_2026_05_05.plan).

Pre-2026-05-06 MTDS ``vault_share_price_handler`` emitted manifest rows with
underscore protocol forms (``MORPHO_VAULTS``, ``YEARN_V3``) that did not match
the no-underscore canonical convention used by every other DeFi venue
(``AAVE_V3-ETHEREUM``, ``COMPOUND_V3-ETHEREUM``, ``UNISWAP_V2-ETHEREUM``). Without
this test, a future refactor could re-introduce the underscore form, leaving
the manifest with two parallel canonical names for the same protocol-chain.

Lock-test asserts:
  1. Each of the 4 vault venues appears in ``ALL_DEFI_VENUES`` in canonical
     ``PROTOCOLNOUNDERSCORE-CHAIN`` form.
  2. The legacy underscore forms (``MORPHO_VAULTS``, ``YEARN_V3``) and bare
     forms (``FRAX``, ``MAKER``) resolve to the canonical via
     ``LEGACY_DEFI_VENUE_ALIASES`` so historical manifest rows can be normalised.
"""

from __future__ import annotations

from unified_api_contracts.registry.capability_declarations._defi import (
    canonicalize_defi_venue_combined,
)
from unified_api_contracts.registry.capability_declarations._defi_coverage import (
    DEPRECATED_DEFI_GHOST_VENUE_NAMES,
)
from unified_api_contracts.registry.defi_venues import (
    ALL_DEFI_VENUES,
    LEGACY_DEFI_VENUE_ALIASES,
)


class TestVaultVenueCanonicalNamesSSOT:
    """Lock vault / yield-bearing venue canonical naming."""

    def test_morphovaults_canonical_in_all_defi_venues(self) -> None:
        assert "MORPHOVAULTS-ETHEREUM" in ALL_DEFI_VENUES

    def test_yearnv3_canonical_in_all_defi_venues(self) -> None:
        assert "YEARN_V3-ETHEREUM" in ALL_DEFI_VENUES

    def test_frax_canonical_in_all_defi_venues(self) -> None:
        assert "FRAX-ETHEREUM" in ALL_DEFI_VENUES

    def test_maker_canonical_in_all_defi_venues(self) -> None:
        assert "MAKER-ETHEREUM" in ALL_DEFI_VENUES

    def test_morpho_vaults_legacy_alias_resolves(self) -> None:
        """Legacy underscore form from pre-2026-05-06 manifest rows."""
        assert LEGACY_DEFI_VENUE_ALIASES["MORPHO_VAULTS"] == "MORPHOVAULTS-ETHEREUM"
        assert LEGACY_DEFI_VENUE_ALIASES["MORPHOVAULTS"] == "MORPHOVAULTS-ETHEREUM"

    def test_yearn_v3_legacy_alias_resolves(self) -> None:
        """Legacy underscore form from pre-2026-05-06 manifest rows."""
        assert LEGACY_DEFI_VENUE_ALIASES["YEARN_V3"] == "YEARN_V3-ETHEREUM"
        assert LEGACY_DEFI_VENUE_ALIASES["YEARN_V3"] == "YEARN_V3-ETHEREUM"

    def test_frax_bare_alias_resolves(self) -> None:
        assert LEGACY_DEFI_VENUE_ALIASES["FRAX"] == "FRAX-ETHEREUM"

    def test_maker_bare_alias_resolves(self) -> None:
        assert LEGACY_DEFI_VENUE_ALIASES["MAKER"] == "MAKER-ETHEREUM"

    def test_no_underscore_in_canonical_protocol_segment(self) -> None:
        """Sanity: every newly-added canonical name follows the no-underscore
        convention in the protocol segment (everything before the hyphen)."""
        for canonical in [
            # Compound-word vaults: no underscore (MORPHO_VAULTS was renamed to MORPHOVAULTS)
            "MORPHOVAULTS-ETHEREUM",
            "FRAX-ETHEREUM",
            "MAKER-ETHEREUM",
            # YEARN_V3 follows the AAVE_V3 / UNISWAP_V3 version-underscore convention —
            # excluded from the no-underscore assertion intentionally.
        ]:
            protocol, _, chain = canonical.partition("-")
            assert "_" not in protocol, f"{canonical}: protocol segment must not contain underscore"
            assert chain, f"{canonical}: missing chain segment"


class TestDefiVenueNameCanonicalReconciliation:
    """Lock the DeFi venue-name canonicalisation decisions reconciled against the
    UAC registry SSOT (mvp_instrument_universe_gap_audit_2026_06_17.md DeFi section).

    The audit flagged dual-format / deprecated venue spellings. The single canonical
    spelling per protocol (confirmed against ``defi_venues.py`` / ``defi_venue_capabilities.py``
    / ``capability_declarations/_defi.py``):

      - **versioned** protocols use the underscore form: ``UNISWAP_V3`` / ``YEARN_V3`` /
        ``TRADER_JOE_V2`` — the glued legacy form (``UNISWAPV3`` / ``YEARNV3`` /
        ``TRADERJOEV2``) canonicalises back to it.
      - **compound-word, non-versioned** protocols are a single token: ``MORPHOVAULTS``
        (NOT ``MORPHO_VAULTS`` — the underscore form is the pre-2026-05-06 LEGACY spelling).
    """

    def test_uniswap_v3_glued_canonicalises_to_underscore(self) -> None:
        assert canonicalize_defi_venue_combined("UNISWAPV3-ETHEREUM") == "UNISWAP_V3-ETHEREUM"

    def test_yearn_v3_glued_canonicalises_to_underscore(self) -> None:
        assert canonicalize_defi_venue_combined("YEARNV3-ETHEREUM") == "YEARN_V3-ETHEREUM"

    def test_trader_joe_v2_underscore_is_canonical_not_retired(self) -> None:
        """TRADER_JOE_V2 stays an underscore-canonical venue (operator 2026-06-01 DF-17
        reversal) — still in ALL_DEFI_VENUES (Avalanche MVP set), NOT retired. The glued
        legacy form maps back to the underscore-canonical combined form."""
        assert "TRADER_JOE_V2-AVALANCHE" in ALL_DEFI_VENUES
        assert canonicalize_defi_venue_combined("TRADERJOEV2-AVALANCHE") == "TRADER_JOE_V2-AVALANCHE"
        assert LEGACY_DEFI_VENUE_ALIASES["TRADER_JOEV2"] == "TRADER_JOE_V2-AVALANCHE"

    def test_morphovaults_glued_is_canonical_underscore_is_legacy(self) -> None:
        """The compound-word vault protocol: glued MORPHOVAULTS is canonical; the
        underscore MORPHO_VAULTS is the legacy alias that resolves to it. The
        ghost-venue drop-set must filter the LEGACY underscore prefix, NEVER the
        canonical glued prefix (else cleanup_ghost_venue_manifest_rows.py would drop
        the live MetaMorpho rows)."""
        assert "MORPHOVAULTS-ETHEREUM" in ALL_DEFI_VENUES
        assert LEGACY_DEFI_VENUE_ALIASES["MORPHO_VAULTS"] == "MORPHOVAULTS-ETHEREUM"
        # The ghost-drop set is matched on the protocol PREFIX (df["venue"].split("-")[0]),
        # so the canonical prefix MUST NOT be in it; the legacy underscore prefix SHOULD be.
        assert "MORPHOVAULTS" not in DEPRECATED_DEFI_GHOST_VENUE_NAMES
        assert "MORPHO_VAULTS" in DEPRECATED_DEFI_GHOST_VENUE_NAMES

    def test_glued_versioned_forms_are_ghost_dropped(self) -> None:
        """The glued versioned spellings the audit flagged are dropped as ghosts so
        they never pollute the manifest alongside the underscore canonical."""
        for ghost in ("UNISWAPV3", "YEARNV3", "PANCAKESWAPV3", "AAVEV3", "COMPOUNDV3"):
            assert ghost in DEPRECATED_DEFI_GHOST_VENUE_NAMES

    def test_rocketpool_reth_is_an_expected_lst_venue(self) -> None:
        """rETH (ROCKETPOOL-ETHEREUM) is a carry_staked_basis LST venue — present in the
        canonical registry as a live venue with its bare-name alias (audit P1 DeFi gap)."""
        assert "ROCKETPOOL-ETHEREUM" in ALL_DEFI_VENUES
        assert LEGACY_DEFI_VENUE_ALIASES["ROCKETPOOL"] == "ROCKETPOOL-ETHEREUM"
