"""Unit tests for canonicalize_league_id (CF-7 reverse canonicalizer).

Registry facts used in these tests (verified against UAC registry 2026-06-02):
- SCOTTISH_LEAGUE_CUP: registered, api_football_id=182 (NOT 185).
  SCOTTISH_LEAGUE_CUP_185 was a retired duplicate where the suffix leaked
  a historical api_football season id, not the canonical league id.
  So _185 suffix is NOT a registered provider id → function returns unchanged.
  Registry-gap note: to strip SCOTTISH_LEAGUE_CUP_185 correctly, either
  185 needs to be added as an alias api_football id on the SCOTTISH_LEAGUE_CUP
  registry entry, or the manifest migration needs a direct rewrite table.
- EPL: registered, api_football_id=39. EPL_39 → strips to EPL.
- BUNDESLIGA_2: registered canonical key (tier-2 name, not a suffix). Returns
  unchanged at step 2 (already canonical).
- EPL_15050: footystats season id 15050 maps to EPL → strips to EPL.
- UNKNOWN_LEAGUE_99: not in registry → returns unchanged.
"""

from __future__ import annotations

import pytest


@pytest.mark.unit
class TestCanonicalizeLeagueId:
    """Tests for canonicalize_league_id CF-7 semantics."""

    def test_already_canonical_returns_unchanged(self) -> None:
        """An already-canonical id (e.g. EPL) is returned as-is at step 2."""
        from unified_api_contracts.sports import canonicalize_league_id

        assert canonicalize_league_id("EPL") == "EPL"
        assert canonicalize_league_id("epl") == "EPL"  # normalise case
        assert canonicalize_league_id("  EPL  ") == "EPL"  # normalise whitespace

    def test_bundesliga_2_not_stripped(self) -> None:
        """BUNDESLIGA_2 is a canonical tier-2 key — must NOT strip the _2 suffix.

        Step 2: get_league("BUNDESLIGA_2") resolves → return unchanged immediately.
        The trailing digit 2 is a division tier, not a provider id.
        """
        from unified_api_contracts.sports import canonicalize_league_id

        assert canonicalize_league_id("BUNDESLIGA_2") == "BUNDESLIGA_2"
        assert canonicalize_league_id("bundesliga_2") == "BUNDESLIGA_2"

    def test_epl_39_strips_via_api_football_id(self) -> None:
        """EPL_39 strips to EPL because api_football_id=39 is registered for EPL."""
        from unified_api_contracts.sports import canonicalize_league_id

        result = canonicalize_league_id("EPL_39")
        assert result == "EPL", "EPL has api_football_id=39 in the registry; EPL_39 should strip to EPL"

    def test_epl_15050_strips_via_footystats_id(self) -> None:
        """EPL_15050 strips to EPL because footystats season id 15050 maps to EPL."""
        from unified_api_contracts.sports import canonicalize_league_id

        result = canonicalize_league_id("EPL_15050")
        assert result == "EPL", "EPL has footystats season id 15050; EPL_15050 should strip to EPL"

    def test_scottish_league_cup_185_returns_unchanged(self) -> None:
        """SCOTTISH_LEAGUE_CUP_185 is NOT stripped because 185 is not the
        registered api_football_id for SCOTTISH_LEAGUE_CUP (which is 182).

        185 was a historical api_football season id that leaked into manifest
        league_ids as a suffix (retired registry entry SCOTTISH_LEAGUE_CUP_185).
        The function conservatively returns it unchanged — the 278,268 manifest
        rows carrying _185 need a direct rewrite table in the IS/MTDS migrator.

        REGISTRY-GAP: to auto-strip via this function, either add 185 as an
        alternative api_football id on SCOTTISH_LEAGUE_CUP, or add a direct
        entry in the migrator's static rewrite table.
        See: sports_manifest_canonicalisation_2026_06_01.md § registry-gap notes.
        """
        from unified_api_contracts.sports import canonicalize_league_id

        result = canonicalize_league_id("SCOTTISH_LEAGUE_CUP_185")
        assert result == "SCOTTISH_LEAGUE_CUP_185", (
            "185 is NOT the registered api_football_id for SCOTTISH_LEAGUE_CUP "
            "(which is 182). Conservative: return unchanged; migrator needs "
            "direct rewrite table for this registry-gap case."
        )

    def test_idempotent(self) -> None:
        """canonicalize_league_id(canonicalize_league_id(x)) == canonicalize_league_id(x)."""
        from unified_api_contracts.sports import canonicalize_league_id

        cases = [
            "EPL",
            "EPL_39",
            "BUNDESLIGA_2",
            "SCOTTISH_LEAGUE_CUP_185",
            "UNKNOWN_LEAGUE_99",
        ]
        for case in cases:
            first = canonicalize_league_id(case)
            second = canonicalize_league_id(first)
            assert first == second, f"Not idempotent for {case!r}: {first!r} != {second!r}"

    def test_unknown_league_returns_unchanged(self) -> None:
        """League not in registry → returned unchanged (no guessing)."""
        from unified_api_contracts.sports import canonicalize_league_id

        assert canonicalize_league_id("UNKNOWN_LEAGUE_99") == "UNKNOWN_LEAGUE_99"
        assert canonicalize_league_id("TOTALLY_FAKE_999") == "TOTALLY_FAKE_999"

    def test_import_from_sports_facade(self) -> None:
        """canonicalize_league_id is importable from unified_api_contracts.sports."""
        from unified_api_contracts import sports

        assert hasattr(sports, "canonicalize_league_id")
        assert callable(sports.canonicalize_league_id)
