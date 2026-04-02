"""Integration tests for registry completeness — InstrumentType coverage.

Validates:
1. All InstrumentType values are valid StrEnum members
2. Every venue in INSTRUMENT_TYPES_BY_VENUE maps to valid InstrumentType values
3. Databento normalizer maps all single-char codes correctly
4. IBKR normalizer maps all IBKR sec types correctly
5. INSTRUMENT_TYPE_FOLDER_MAP covers all InstrumentType values
"""

from __future__ import annotations

from enum import StrEnum

from unified_api_contracts.canonical.domain.reference import InstrumentType
from unified_api_contracts.registry.venue_constants import (
    INSTRUCTION_VALID_INSTRUMENT_TYPES,
    INSTRUMENT_TYPE_FOLDER_MAP,
    INSTRUMENT_TYPES_BY_VENUE,
)


class TestInstrumentTypeEnum:
    """All InstrumentType values are valid StrEnum members."""

    def test_is_str_enum(self) -> None:
        assert issubclass(InstrumentType, StrEnum)

    def test_all_expected_members_exist(self) -> None:
        expected = {
            "SPOT_PAIR",
            "PERPETUAL",
            "FUTURE",
            "OPTION",
            "LST",
            "A_TOKEN",
            "INDEX",
            "BOND",
            "EQUITY",
            "ETF",
            "COMMODITY",
            "CURRENCY",
            "CDS",
            "SPOT_ASSET",
            "YIELD_BEARING",
            "DEBT_TOKEN",
            "POOL",
            "LENDING",
            "STAKING",
            "PREDICTION_MARKET",
            "EXCHANGE_ODDS",
            "FIXED_ODDS",
            "PROP",
        }
        actual = {m.name for m in InstrumentType}
        missing = expected - actual
        assert not missing, f"InstrumentType missing members: {missing}"

    def test_members_are_strings(self) -> None:
        for member in InstrumentType:
            assert isinstance(member, str)
            assert member.value == member.name


class TestInstrumentTypesByVenue:
    """Every venue in INSTRUMENT_TYPES_BY_VENUE maps to valid InstrumentType values."""

    def test_all_venue_types_are_valid_instrument_types(self) -> None:
        valid_values = {m.value for m in InstrumentType}
        for venue, types in INSTRUMENT_TYPES_BY_VENUE.items():
            for t in types:
                assert t in valid_values, f"Venue {venue} references invalid InstrumentType: {t}"

    def test_no_empty_type_sets(self) -> None:
        for venue, types in INSTRUMENT_TYPES_BY_VENUE.items():
            assert len(types) > 0, f"Venue {venue} has empty instrument type set"


class TestDabentoNormalizer:
    """Databento _instrument_class_to_type maps all single-char codes correctly."""

    def test_all_databento_codes(self) -> None:
        from unified_api_contracts.external.databento.normalize import (
            _instrument_class_to_type,
        )

        expected = {
            "F": InstrumentType.FUTURE,
            "O": InstrumentType.OPTION,
            "S": InstrumentType.SPOT_PAIR,
            "B": InstrumentType.BOND,
            "E": InstrumentType.EQUITY,
            "N": InstrumentType.ETF,
            "X": InstrumentType.INDEX,
            "C": InstrumentType.COMMODITY,
        }
        for code, expected_type in expected.items():
            result = _instrument_class_to_type(code)
            assert result == expected_type, f"Databento code '{code}' mapped to {result}, expected {expected_type}"

    def test_none_defaults_to_spot_pair(self) -> None:
        from unified_api_contracts.external.databento.normalize import (
            _instrument_class_to_type,
        )

        assert _instrument_class_to_type(None) == InstrumentType.SPOT_PAIR

    def test_unknown_code_defaults_to_spot_pair(self) -> None:
        from unified_api_contracts.external.databento.normalize import (
            _instrument_class_to_type,
        )

        assert _instrument_class_to_type("Z") == InstrumentType.SPOT_PAIR

    def test_lowercase_codes_work(self) -> None:
        from unified_api_contracts.external.databento.normalize import (
            _instrument_class_to_type,
        )

        assert _instrument_class_to_type("f") == InstrumentType.FUTURE
        assert _instrument_class_to_type("e") == InstrumentType.EQUITY


class TestIbkrNormalizer:
    """IBKR _ibkr_instrument_type maps all IBKR sec types correctly."""

    def test_all_ibkr_sec_types(self) -> None:
        from unified_api_contracts.external.ibkr.normalize import (
            _ibkr_instrument_type,
        )

        expected = {
            "STK": "EQUITY",
            "CASH": "CURRENCY",
            "CFD": "SPOT_PAIR",
            "IND": "INDEX",
            "FUND": "ETF",
            "CMDTY": "COMMODITY",
            "FUT": "FUTURE",
            "OPT": "OPTION",
            "FOP": "OPTION",
            "WAR": "OPTION",
            "BAG": "FUTURE",
            "BOND": "BOND",
        }
        for sec_type, expected_type in expected.items():
            result = _ibkr_instrument_type(sec_type)
            assert result == expected_type, f"IBKR sec_type '{sec_type}' mapped to {result}, expected {expected_type}"

    def test_none_defaults_to_spot_pair(self) -> None:
        from unified_api_contracts.external.ibkr.normalize import (
            _ibkr_instrument_type,
        )

        assert _ibkr_instrument_type(None) == "SPOT_PAIR"

    def test_unknown_defaults_to_spot_pair(self) -> None:
        from unified_api_contracts.external.ibkr.normalize import (
            _ibkr_instrument_type,
        )

        assert _ibkr_instrument_type("UNKNOWN") == "SPOT_PAIR"

    def test_ibkr_market_state_type_map_includes_fund(self) -> None:
        """The type_map in normalize_ibkr_market_state must map FUND to ETF."""
        from unified_api_contracts.external.ibkr.normalize import (
            normalize_ibkr_market_state,
        )

        result = normalize_ibkr_market_state(
            trading_phase="OPEN",
            symbol="SPY",
            sec_type="FUND",
        )
        assert "ETF" in result.instrument_key, f"Expected ETF in instrument_key, got {result.instrument_key}"

    def test_ibkr_market_state_type_map_all_sec_types(self) -> None:
        """The type_map in normalize_ibkr_market_state covers key IBKR sec types."""
        from unified_api_contracts.external.ibkr.normalize import (
            normalize_ibkr_market_state,
        )

        expected_mappings = {
            "STK": "EQUITY",
            "FUT": "FUTURE",
            "OPT": "OPTION",
            "CASH": "CURRENCY",
            "IND": "INDEX",
            "FUND": "ETF",
            "CMDTY": "COMMODITY",
            "BOND": "BOND",
        }
        for sec_type, expected_inst_type in expected_mappings.items():
            result = normalize_ibkr_market_state(
                trading_phase="OPEN",
                symbol="TEST",
                sec_type=sec_type,
            )
            assert expected_inst_type in result.instrument_key, (
                f"sec_type '{sec_type}' should produce '{expected_inst_type}' "
                f"in instrument_key, got {result.instrument_key}"
            )


class TestInstrumentTypeFolderMap:
    """INSTRUMENT_TYPE_FOLDER_MAP covers all InstrumentType values."""

    def test_all_instrument_types_have_folder_mapping(self) -> None:
        missing: list[str] = []
        for member in InstrumentType:
            if member.value not in INSTRUMENT_TYPE_FOLDER_MAP:
                missing.append(member.value)
        assert not missing, f"InstrumentType members missing from INSTRUMENT_TYPE_FOLDER_MAP: {missing}"

    def test_folder_values_are_valid_directory_names(self) -> None:
        """Folder names should be lowercase, no spaces, filesystem-safe."""
        for itype, folder in INSTRUMENT_TYPE_FOLDER_MAP.items():
            assert folder == folder.lower(), f"Folder for {itype} should be lowercase: {folder}"
            assert " " not in folder, f"Folder for {itype} should not contain spaces: {folder}"
            assert folder.isidentifier() or "_" in folder, f"Folder for {itype} should be a valid identifier: {folder}"

    def test_no_duplicate_folder_names(self) -> None:
        """Different instrument types should not map to the same folder."""
        seen: dict[str, str] = {}
        for itype, folder in INSTRUMENT_TYPE_FOLDER_MAP.items():
            assert folder not in seen, f"Duplicate folder name '{folder}' for {seen.get(folder)} and {itype}"
            seen[folder] = itype


class TestInstructionValidInstrumentTypes:
    """INSTRUCTION_VALID_INSTRUMENT_TYPES references only valid InstrumentType values."""

    def test_all_referenced_types_are_valid(self) -> None:
        valid_values = {m.value for m in InstrumentType}
        # Allow legacy aliases used in venue mappings
        valid_values.add("SPREAD")
        valid_values.add("OVER_UNDER")
        valid_values.add("OUTRIGHT")
        for instruction, types in INSTRUCTION_VALID_INSTRUMENT_TYPES.items():
            for t in types:
                assert t in valid_values, f"Instruction {instruction} references invalid InstrumentType: {t}"
