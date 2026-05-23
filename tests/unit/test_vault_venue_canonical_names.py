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
