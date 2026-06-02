"""Unit tests for canonicalize_league_id (CF-7 reverse canonicalizer).

Registry facts used in these tests (verified against UAC registry 2026-06-02):
- SCOTTISH_LEAGUE_CUP: registered, api_football_id=182 (NOT 185).
  SCOTTISH_LEAGUE_CUP_185: 185 >= 100 (3-digit season/AF id, never a tier).
  The 3-digit rule (Step 3a) strips SCOTTISH_LEAGUE_CUP_185 → SCOTTISH_LEAGUE_CUP
  because base resolves AND num >= 100, regardless of provider-id registration.
  Real league tiers never exceed 2 digits (LIGA_3, LIGUE_2, etc.).
- EPL: registered, api_football_id=39. EPL_39 → strips to EPL (provider-id match).
- BUNDESLIGA_2: registered canonical key (tier-2 name, not a suffix). Returns
  unchanged at step 2 (already canonical).
- EPL_15050: footystats season id 15050 (3-digit rule) → strips to EPL.
- UNKNOWN_LEAGUE_99: base not in registry → returns unchanged.
- LA_LIGA_2 / FRANCE_NATIONAL_1: 1–2-digit suffix, NOT stripped unless the digit
  is a registered provider id for the base league. LA_LIGA_2 is canonical; it
  resolves at step 2 and is returned unchanged. These ambiguous tier-vs-season
  cases remain operator-decision-only; this function does not touch them.
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

    def test_scottish_league_cup_185_strips_via_3digit_rule(self) -> None:
        """SCOTTISH_LEAGUE_CUP_185 → SCOTTISH_LEAGUE_CUP via 3-digit season-id rule.

        185 >= 100 (3+ digits) AND get_league("SCOTTISH_LEAGUE_CUP") resolves →
        strip unconditionally. Real league tiers never reach 3 digits; any 3+-digit
        suffix is a provider season/AF id, not a tier qualifier.

        NOTE: LA_LIGA_2 / LIGUE_1 / BUNDESLIGA_2 are untouched — their 1-2-digit
        suffixes are ambiguous (could be a tier name). Step 2 resolves BUNDESLIGA_2
        immediately (already canonical key); LA_LIGA_2 similarly stays unchanged
        because it is already canonical. These cases are operator-decision-only.
        """
        from unified_api_contracts.sports import canonicalize_league_id

        result = canonicalize_league_id("SCOTTISH_LEAGUE_CUP_185")
        assert result == "SCOTTISH_LEAGUE_CUP", (
            "185 >= 100 (3-digit season id, never a tier). SCOTTISH_LEAGUE_CUP resolves in registry → strip to base."
        )

    def test_la_liga_2_unchanged_already_canonical(self) -> None:
        """LA_LIGA_2 is a canonical key in the registry — step 2 returns it unchanged."""
        from unified_api_contracts.sports import canonicalize_league_id

        assert canonicalize_league_id("LA_LIGA_2") == "LA_LIGA_2"
        assert canonicalize_league_id("la_liga_2") == "LA_LIGA_2"

    def test_ligue_1_unchanged_already_canonical(self) -> None:
        """LIGUE_1 is already canonical — step 2 returns it unchanged."""
        from unified_api_contracts.sports import canonicalize_league_id

        assert canonicalize_league_id("LIGUE_1") == "LIGUE_1"

    def test_idempotent(self) -> None:
        """canonicalize_league_id(canonicalize_league_id(x)) == canonicalize_league_id(x)."""
        from unified_api_contracts.sports import canonicalize_league_id

        cases = [
            "EPL",
            "EPL_39",
            "BUNDESLIGA_2",
            "LA_LIGA_2",
            "LIGUE_1",
            # 3-digit rule: SCOTTISH_LEAGUE_CUP_185 → SCOTTISH_LEAGUE_CUP (idempotent)
            "SCOTTISH_LEAGUE_CUP_185",
            "SCOTTISH_LEAGUE_CUP",
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
