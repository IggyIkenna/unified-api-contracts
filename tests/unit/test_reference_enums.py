"""Tests for canonical reference enums: InstrumentType, InstructionType, Sport."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


class TestInstrumentType:
    """InstrumentType enum completeness and consistency with venue_constants."""

    def test_prediction_market_member_exists(self) -> None:
        from unified_api_contracts.canonical.domain.reference import InstrumentType

        assert InstrumentType.PREDICTION_MARKET == "PREDICTION_MARKET"

    def test_sports_instrument_types_present(self) -> None:
        from unified_api_contracts.canonical.domain.reference import InstrumentType

        assert InstrumentType.EXCHANGE_ODDS == "EXCHANGE_ODDS"
        assert InstrumentType.FIXED_ODDS == "FIXED_ODDS"
        assert InstrumentType.PROP == "PROP"

    def test_instrument_type_folder_map_covers_new_types(self) -> None:
        """INSTRUMENT_TYPE_FOLDER_MAP must have entries for all sports types."""
        from unified_api_contracts.registry.venue_constants import (
            INSTRUMENT_TYPE_FOLDER_MAP,
        )

        for key in ("PREDICTION_MARKET", "EXCHANGE_ODDS", "FIXED_ODDS", "PROP"):
            assert key in INSTRUMENT_TYPE_FOLDER_MAP, f"Missing folder mapping for {key}"


class TestInstructionType:
    """InstructionType enum completeness."""

    def test_core_instruction_types(self) -> None:
        from unified_api_contracts.canonical.domain.reference import InstructionType

        assert InstructionType.TRADE == "TRADE"
        assert InstructionType.SWAP == "SWAP"
        assert InstructionType.ZERO_ALPHA == "ZERO_ALPHA"

    def test_new_instruction_types(self) -> None:
        from unified_api_contracts.canonical.domain.reference import InstructionType

        assert InstructionType.PREDICTION_BET == "PREDICTION_BET"
        assert InstructionType.SPORTS_BET == "SPORTS_BET"
        assert InstructionType.SPORTS_EXCHANGE_ORDER == "SPORTS_EXCHANGE_ORDER"
        assert InstructionType.FUTURES_ROLL == "FUTURES_ROLL"
        assert InstructionType.OPTIONS_COMBO == "OPTIONS_COMBO"

    def test_instruction_valid_domains_covers_new_types(self) -> None:
        from unified_api_contracts.registry.venue_constants import (
            INSTRUCTION_VALID_DOMAINS,
        )

        for key in (
            "PREDICTION_BET",
            "SPORTS_BET",
            "SPORTS_EXCHANGE_ORDER",
            "FUTURES_ROLL",
            "OPTIONS_COMBO",
        ):
            assert key in INSTRUCTION_VALID_DOMAINS, f"Missing domain mapping for {key}"

    def test_instruction_valid_instrument_types_covers_new_types(self) -> None:
        from unified_api_contracts.registry.venue_constants import (
            INSTRUCTION_VALID_INSTRUMENT_TYPES,
        )

        for key in (
            "PREDICTION_BET",
            "SPORTS_BET",
            "SPORTS_EXCHANGE_ORDER",
            "FUTURES_ROLL",
            "OPTIONS_COMBO",
        ):
            assert key in INSTRUCTION_VALID_INSTRUMENT_TYPES, f"Missing instrument type mapping for {key}"


class TestSportEnum:
    """Sport StrEnum completeness."""

    def test_sport_enum_values(self) -> None:
        from unified_api_contracts.canonical.domain.reference import Sport

        assert Sport.FOOTBALL == "FOOTBALL"
        assert Sport.BASKETBALL == "BASKETBALL"
        assert Sport.BASEBALL == "BASEBALL"
        assert Sport.HOCKEY == "HOCKEY"
        assert Sport.TENNIS == "TENNIS"
        assert Sport.CRICKET == "CRICKET"
        assert Sport.RUGBY == "RUGBY"
        assert Sport.GOLF == "GOLF"
        assert Sport.MMA == "MMA"
        assert Sport.BOXING == "BOXING"
        assert Sport.MOTORSPORT == "MOTORSPORT"
        assert Sport.AMERICAN_FOOTBALL == "AMERICAN_FOOTBALL"
        assert Sport.HANDBALL == "HANDBALL"
        assert Sport.VOLLEYBALL == "VOLLEYBALL"
        assert Sport.TABLE_TENNIS == "TABLE_TENNIS"
        assert Sport.DARTS == "DARTS"
        assert Sport.SNOOKER == "SNOOKER"
        assert Sport.ESPORTS == "ESPORTS"
        assert Sport.SOCCER == "SOCCER"

    def test_sport_exported_from_top_level(self) -> None:
        from unified_api_contracts import Sport

        assert Sport.FOOTBALL == "FOOTBALL"

    def test_sport_is_str_enum(self) -> None:
        from enum import StrEnum

        from unified_api_contracts.canonical.domain.reference import Sport

        assert issubclass(Sport, StrEnum)
        # StrEnum members are also strings
        assert isinstance(Sport.FOOTBALL, str)
