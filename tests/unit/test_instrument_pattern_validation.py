"""Instrument ID pattern validation tests.

Validates that instrument ID patterns used by strategies match what
instruments-service produces — format rules, venue name validation,
and DeFi strategy instrument requirements.
"""

from __future__ import annotations

import re

from unified_api_contracts.registry.market_data_categories import ALL_VENUES
from unified_api_contracts.registry.token_wrapping import PROTOCOL_TOKEN_PREFERENCE
from unified_api_contracts.registry.venue_collateral import VENUE_COLLATERAL_MATRIX
from unified_api_contracts.registry.venue_constants import (
    INSTRUMENT_TYPE_FOLDER_MAP,
    INSTRUMENT_TYPES_BY_VENUE,
)

# Instrument ID format: {VENUE}:{INSTRUMENT_TYPE}:{DETAILS}
# where VENUE is the canonical venue name, INSTRUMENT_TYPE is from
# INSTRUMENT_TYPE_FOLDER_MAP keys, and DETAILS is asset-specific.
INSTRUMENT_ID_PATTERN = re.compile(
    r"^[A-Z][A-Z0-9_-]+:[A-Z][A-Z0-9_]+:.+$",
)

# Known valid instrument type segments (from INSTRUMENT_TYPE_FOLDER_MAP keys
# plus position-type aliases used in instrument IDs)
VALID_INSTRUMENT_TYPES = set(INSTRUMENT_TYPE_FOLDER_MAP.keys()) | {
    "FLASH_LOAN",
    "OVER_UNDER",
    "SPREAD",
    "OUTRIGHT",
    "EXCHANGE_ODDS",
    "FIXED_ODDS",
    "PREDICTION_MARKET",
    "PROP",
}


# ---------------------------------------------------------------------------
# Instrument ID Format
# ---------------------------------------------------------------------------


class TestInstrumentIdFormat:
    """Validate instrument ID format: VENUE:INSTRUMENT_TYPE:DETAILS."""

    def test_aave_a_token_format(self) -> None:
        """AAVEV3-ETHEREUM:A_TOKEN:aUSDT@ETHEREUM is valid format."""
        instrument_id = "AAVEV3-ETHEREUM:A_TOKEN:aUSDT@ETHEREUM"
        assert INSTRUMENT_ID_PATTERN.match(instrument_id), f"Instrument ID does not match pattern: {instrument_id}"
        parts = instrument_id.split(":")
        assert len(parts) == 3
        assert parts[0] == "AAVEV3-ETHEREUM"
        assert parts[1] == "A_TOKEN"
        assert parts[2] == "aUSDT@ETHEREUM"

    def test_hyperliquid_perpetual_format(self) -> None:
        """HYPERLIQUID:PERPETUAL:ETH-USDC@LIN@HYPERLIQUID is valid format."""
        instrument_id = "HYPERLIQUID:PERPETUAL:ETH-USDC@LIN@HYPERLIQUID"
        assert INSTRUMENT_ID_PATTERN.match(instrument_id), f"Instrument ID does not match pattern: {instrument_id}"
        parts = instrument_id.split(":")
        assert len(parts) == 3
        assert parts[0] == "HYPERLIQUID"
        assert parts[1] == "PERPETUAL"

    def test_wallet_spot_asset_format(self) -> None:
        """WALLET:SPOT_ASSET:ETH is valid format."""
        instrument_id = "WALLET:SPOT_ASSET:ETH"
        assert INSTRUMENT_ID_PATTERN.match(instrument_id), f"Instrument ID does not match pattern: {instrument_id}"
        parts = instrument_id.split(":")
        assert len(parts) == 3
        assert parts[0] == "WALLET"
        assert parts[1] == "SPOT_ASSET"
        assert parts[2] == "ETH"

    def test_etherfi_lst_format(self) -> None:
        """ETHERFI:LST:WEETH@ETHEREUM is valid format."""
        instrument_id = "ETHERFI:LST:WEETH@ETHEREUM"
        assert INSTRUMENT_ID_PATTERN.match(instrument_id), f"Instrument ID does not match pattern: {instrument_id}"
        parts = instrument_id.split(":")
        assert len(parts) == 3
        assert parts[0] == "ETHERFI"
        assert parts[1] == "LST"
        assert parts[2] == "WEETH@ETHEREUM"

    def test_three_part_structure_enforced(self) -> None:
        """Instrument IDs must have exactly 3 colon-separated parts."""
        valid_ids = [
            "AAVEV3-ETHEREUM:A_TOKEN:aUSDT@ETHEREUM",
            "HYPERLIQUID:PERPETUAL:ETH-USDC@LIN@HYPERLIQUID",
            "WALLET:SPOT_ASSET:ETH",
            "ETHERFI:LST:WEETH@ETHEREUM",
            "BINANCE-FUTURES:PERPETUAL:BTC-USDT@LIN@BINANCE",
            "LIDO:LST:STETH@ETHEREUM",
        ]
        for iid in valid_ids:
            parts = iid.split(":")
            assert len(parts) == 3, f"Expected 3 parts, got {len(parts)} for {iid}"

    def test_instrument_type_segment_is_known(self) -> None:
        """The instrument type segment should be a known type."""
        sample_ids = [
            "AAVEV3-ETHEREUM:A_TOKEN:aUSDT@ETHEREUM",
            "HYPERLIQUID:PERPETUAL:ETH-USDC@LIN@HYPERLIQUID",
            "WALLET:SPOT_ASSET:ETH",
            "ETHERFI:LST:WEETH@ETHEREUM",
            "UNISWAPV3-ETHEREUM:POOL:WETH-USDC@3000",
            "AAVEV3-ETHEREUM:DEBT_TOKEN:debtWETH@ETHEREUM",
        ]
        for iid in sample_ids:
            inst_type = iid.split(":")[1]
            assert inst_type in VALID_INSTRUMENT_TYPES, f"Unknown instrument type '{inst_type}' in {iid}"


# ---------------------------------------------------------------------------
# Venue Name Validation
# ---------------------------------------------------------------------------


class TestVenueNameValidation:
    """Validate venue names in registries against the canonical venue list."""

    def test_collateral_matrix_venues_are_known(self) -> None:
        """All venues in VENUE_COLLATERAL_MATRIX should map to known venue names.

        The collateral matrix uses exchange-level names (e.g. BINANCE, OKX)
        while the venue registry uses product-split names (BINANCE-SPOT,
        BINANCE-FUTURES). A collateral venue is valid if it matches exactly
        or is a prefix of a known venue (exchange-level parent).
        """
        collateral_venues = {e.venue for e in VENUE_COLLATERAL_MATRIX}
        all_known = set(ALL_VENUES) | set(INSTRUMENT_TYPES_BY_VENUE.keys())
        for venue in collateral_venues:
            # Exact match or prefix match (BINANCE matches BINANCE-SPOT)
            exact = venue in all_known
            prefix = any(k.startswith(venue + "-") for k in all_known)
            assert exact or prefix, (
                f"Venue '{venue}' in VENUE_COLLATERAL_MATRIX is not in "
                f"the known venue registry (no exact or prefix match)"
            )

    def test_protocol_token_preference_keys_are_protocol_names(self) -> None:
        """All keys in PROTOCOL_TOKEN_PREFERENCE map to real protocol names."""
        expected_protocols = {
            "AAVEV3",
            "MORPHO",
            "ETHERFI",
            "LIDO",
            "UNISWAPV3",
            "HYPERLIQUID",
        }
        actual_protocols = set(PROTOCOL_TOKEN_PREFERENCE.keys())
        assert actual_protocols == expected_protocols, (
            f"PROTOCOL_TOKEN_PREFERENCE keys mismatch. "
            f"Extra: {actual_protocols - expected_protocols}, "
            f"Missing: {expected_protocols - actual_protocols}"
        )

    def test_instrument_types_by_venue_non_empty(self) -> None:
        """Every venue in INSTRUMENT_TYPES_BY_VENUE has at least one type."""
        for venue, types in INSTRUMENT_TYPES_BY_VENUE.items():
            assert len(types) > 0, f"Venue '{venue}' has no instrument types"


# ---------------------------------------------------------------------------
# DeFi Strategy Instrument Requirements
# ---------------------------------------------------------------------------


class TestDefiStrategyInstrumentRequirements:
    """Validate that instrument types needed by DeFi strategies exist."""

    def test_basis_trade_instrument_types_exist(self) -> None:
        """Basis trade needs SPOT_ASSET + PERPETUAL (2 legs)."""
        all_types = set(INSTRUMENT_TYPE_FOLDER_MAP.keys())
        assert "SPOT_ASSET" in all_types, "SPOT_ASSET type required for basis trade spot leg"
        assert "PERPETUAL" in all_types, "PERPETUAL type required for basis trade hedge leg"

    def test_basis_trade_venues_exist(self) -> None:
        """At least one venue supports PERPETUAL for basis trade hedge leg."""
        perp_venues = [v for v, types in INSTRUMENT_TYPES_BY_VENUE.items() if "PERPETUAL" in types]
        assert len(perp_venues) > 0, "No venue supports PERPETUAL instruments"

    def test_staked_basis_instrument_types_exist(self) -> None:
        """Staked basis needs LST + PERPETUAL (2 legs)."""
        all_types = set(INSTRUMENT_TYPE_FOLDER_MAP.keys())
        assert "LST" in all_types, "LST type required for staked basis staking leg"
        assert "PERPETUAL" in all_types, "PERPETUAL type required for staked basis hedge leg"

    def test_staked_basis_venues_exist(self) -> None:
        """At least one venue supports STAKING for staked basis LST leg."""
        staking_venues = [v for v, types in INSTRUMENT_TYPES_BY_VENUE.items() if "STAKING" in types]
        assert len(staking_venues) > 0, "No venue supports STAKING instruments for LST"

    def test_lending_instrument_types_exist(self) -> None:
        """Lending needs A_TOKEN (1 leg)."""
        all_types = set(INSTRUMENT_TYPE_FOLDER_MAP.keys())
        assert "A_TOKEN" in all_types, "A_TOKEN type required for lending strategy"

    def test_lending_venues_exist(self) -> None:
        """At least one venue supports LENDING for lending strategy."""
        lending_venues = [v for v, types in INSTRUMENT_TYPES_BY_VENUE.items() if "LENDING" in types]
        assert len(lending_venues) > 0, "No venue supports LENDING instruments"

    def test_recursive_strategy_instrument_types_exist(self) -> None:
        """Recursive needs FLASH_LOAN + LST + A_TOKEN + DEBT_TOKEN + PERPETUAL (5 legs)."""
        all_types = set(INSTRUMENT_TYPE_FOLDER_MAP.keys())
        # FLASH_LOAN is a capability, not in INSTRUMENT_TYPE_FOLDER_MAP,
        # but it must exist in the instruction valid instrument types
        from unified_api_contracts.registry.venue_constants import (
            INSTRUCTION_VALID_INSTRUMENT_TYPES,
        )

        assert "FLASH_LOAN" in INSTRUCTION_VALID_INSTRUMENT_TYPES, (
            "FLASH_LOAN instruction type required for recursive strategy"
        )
        assert "LST" in all_types, "LST type required for recursive strategy staking leg"
        assert "A_TOKEN" in all_types, "A_TOKEN type required for recursive strategy supply leg"
        assert "DEBT_TOKEN" in all_types, "DEBT_TOKEN type required for recursive strategy borrow leg"
        assert "PERPETUAL" in all_types, "PERPETUAL type required for recursive strategy hedge leg"

    def test_recursive_strategy_flash_loan_venues_exist(self) -> None:
        """At least one venue has FLASH_LOAN capability for recursive strategy."""
        from unified_api_contracts.registry.venue_constants import (
            VENUE_CAPABILITIES,
            VenueCapability,
        )

        flash_loan_venues = [v for v, caps in VENUE_CAPABILITIES.items() if VenueCapability.FLASH_LOAN in caps]
        assert len(flash_loan_venues) > 0, "No venue has FLASH_LOAN capability for recursive strategy"

    def test_all_instrument_types_have_folder_mapping(self) -> None:
        """Every instrument type used by DeFi strategies has a folder mapping."""
        defi_types = {"A_TOKEN", "DEBT_TOKEN", "LST", "YIELD_BEARING", "LENDING", "STAKING", "POOL"}
        for t in defi_types:
            assert t in INSTRUMENT_TYPE_FOLDER_MAP, (
                f"Instrument type '{t}' has no folder mapping in INSTRUMENT_TYPE_FOLDER_MAP"
            )
