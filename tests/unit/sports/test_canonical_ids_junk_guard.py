"""Unit tests for the junk-symbol guard in canonical_ids._slug.

sports_closeout_batch1_ao_ready_2026_07_24.md CLEANUP todo: "add a junk-symbol
guard rejecting non-ASCII characters in fixture names." The guard rejects genuine
corruption markers (Unicode replacement char, control chars) while legitimate
accented names (e.g. "México", "São Paulo") still pass through and get
diacritic-stripped normally — see canonical_ids._reject_junk_symbols.
"""

from __future__ import annotations

import pytest

from unified_api_contracts.canonical.domain.sports.canonical_ids import (
    JunkSymbolError,
    _slug,
    build_fixture_id,
    build_team_id,
)


def test_slug_rejects_replacement_character() -> None:
    with pytest.raises(JunkSymbolError):
        _slug("Arsenal � Chelsea")


def test_slug_rejects_control_character() -> None:
    with pytest.raises(JunkSymbolError):
        _slug("Arsenal\x00Chelsea")


def test_slug_allows_legitimate_diacritics() -> None:
    assert _slug("México") == "MEXICO"
    assert _slug("São Paulo") == "SAO_PAULO"


def test_build_team_id_rejects_junk_symbol() -> None:
    with pytest.raises(JunkSymbolError):
        build_team_id("Arsenal� FC")


def test_build_fixture_id_still_works_for_clean_teams() -> None:
    fixture_id = build_fixture_id("ENG_PREMIER_LEAGUE", "ARSENAL", "CHELSEA", "2026-03-22")
    assert fixture_id == "ENG_PREMIER_LEAGUE:ARSENAL_v_CHELSEA:20260322"
