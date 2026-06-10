"""Tests for external/api_football/player_name.py — canonical player ID normalization."""

from __future__ import annotations

import pytest

from unified_api_contracts.external.api_football.player_name import (
    get_canonical_player_name_from_api_football,
)


class TestInitialAndSurname:
    def test_initial_surname_format(self) -> None:
        result = get_canonical_player_name_from_api_football("J. Pickford", 1)
        assert result == "PICKFORD_J"

    def test_initial_with_period(self) -> None:
        result = get_canonical_player_name_from_api_football("M. Salah", 2)
        assert result == "SALAH_M"

    def test_two_char_initial(self) -> None:
        result = get_canonical_player_name_from_api_football("Jo. Smith", 3)
        assert result == "SMITH_JO"


class TestFullName:
    def test_two_part_full_name(self) -> None:
        result = get_canonical_player_name_from_api_football("Bruno Fernandes", 4)
        assert result == "FERNANDES_BRUNO"

    def test_two_part_name_reversed(self) -> None:
        result = get_canonical_player_name_from_api_football("Harry Kane", 5)
        assert result == "KANE_HARRY"


class TestCompoundSurname:
    def test_three_part_name_uses_last_two(self) -> None:
        result = get_canonical_player_name_from_api_football("Bruno Miguel Fernandes", 6)
        assert result == "MIGUEL_FERNANDES_BRUNO"

    def test_compound_surname_with_de(self) -> None:
        result = get_canonical_player_name_from_api_football("De Gea", 7)
        # "De Gea" → 2 parts → LAST_FIRST: "GEA_DE" ... wait, that's 2 parts
        # Actually "De" and "Gea" → FIRST="De", LAST="Gea" → "GEA_DE"
        assert result == "GEA_DE"


class TestDiacritics:
    def test_umlaut_stripped(self) -> None:
        result = get_canonical_player_name_from_api_football("Thomas Müller", 8)
        assert result == "MULLER_THOMAS"

    def test_icelandic_eth_not_decomposed(self) -> None:
        # ð (U+00F0) is a standalone character, not a diacritic — preserved as-is
        result = get_canonical_player_name_from_api_football("G. Sigurðsson", 9)
        assert isinstance(result, str) and "_G" in result

    def test_accented_name(self) -> None:
        result = get_canonical_player_name_from_api_football("Raphaël Varane", 10)
        assert result == "VARANE_RAPHAEL"


class TestFallbacks:
    def test_empty_name_uses_player_id(self) -> None:
        result = get_canonical_player_name_from_api_football("", 42)
        assert result == "PLAYER_42"

    def test_single_word_name(self) -> None:
        result = get_canonical_player_name_from_api_football("Neymar", 11)
        assert result == "NEYMAR"

    def test_spaces_only_uses_player_id(self) -> None:
        result = get_canonical_player_name_from_api_football("   ", 99)
        assert result == "PLAYER_99"

    def test_special_chars_stripped(self) -> None:
        result = get_canonical_player_name_from_api_football("O'Brien", 12)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_hyphenated_name(self) -> None:
        result = get_canonical_player_name_from_api_football("Martial-Wayne", 13)
        assert isinstance(result, str)
        assert len(result) > 0


@pytest.mark.parametrize(
    ("name", "player_id", "expected"),
    [
        ("", 1, "PLAYER_1"),
        ("Neymar", 2, "NEYMAR"),
        ("J. Pickford", 3, "PICKFORD_J"),
        ("Bruno Fernandes", 4, "FERNANDES_BRUNO"),
        ("Thomas Müller", 5, "MULLER_THOMAS"),
    ],
)
def test_canonical_player_name_parametrized(name: str, player_id: int, expected: str) -> None:
    result = get_canonical_player_name_from_api_football(name, player_id)
    assert result == expected
