"""Instrument ID pattern validation tests.

Validates that instrument ID format conventions used across the system
are consistent -- regex validators for each pattern, known valid/invalid IDs,
and cross-strategy instrument coverage matrix ensuring each strategy has
the instrument types it needs.
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Instrument ID Pattern Regexes
# ---------------------------------------------------------------------------

# Pattern: WALLET:SPOT_ASSET:{TOKEN} -- TOKEN is uppercase alpha
SPOT_ASSET_PATTERN = re.compile(r"^WALLET:SPOT_ASSET:[A-Z]+$")

# Pattern: {VENUE}:PERPETUAL:{BASE}-{QUOTE}@LIN@{VENUE}
# Venue is uppercase alphanumeric with optional chain suffix (e.g. BINANCE-FUTURES)
PERPETUAL_PATTERN = re.compile(r"^[A-Z][A-Z0-9-]+:PERPETUAL:[A-Z0-9]+-[A-Z0-9]+@LIN@[A-Z][A-Z0-9-]+$")

# Pattern: AAVE_V3-{CHAIN}:A_TOKEN:A{TOKEN}@{CHAIN}
# Note: historical IDs use lowercase 'a' prefix (aUSDT) so we allow both
A_TOKEN_PATTERN = re.compile(r"^AAVE_V3-[A-Z]+:A_TOKEN:[aA][A-Za-z0-9]+@[A-Z]+$")

# Pattern: AAVE_V3-{CHAIN}:DEBT_TOKEN:DEBT{TOKEN}@{CHAIN}
# Note: historical IDs use lowercase 'debt' prefix so we allow both
DEBT_TOKEN_PATTERN = re.compile(r"^AAVE_V3-[A-Z]+:DEBT_TOKEN:[dD][eE][bB][tT][A-Za-z0-9]+@[A-Z]+$")

# Pattern: {PROTOCOL}:LST:{TOKEN}@{CHAIN}
LST_PATTERN = re.compile(r"^[A-Z][A-Z0-9]+:LST:[A-Z0-9]+@[A-Z]+$")

# Pattern: {CHAIN}:SWAP:{TOKEN_IN}-{TOKEN_OUT}
SWAP_PATTERN = re.compile(r"^[A-Z][A-Z0-9_-]+:SWAP:[A-Z0-9]+-[A-Z0-9]+$")

# Pattern: {PROTOCOL}:REWARD:{TOKEN}@{CHAIN}
REWARD_PATTERN = re.compile(r"^[A-Z][A-Z0-9]+:REWARD:[A-Z0-9]+@[A-Z]+$")

# Pattern: {PROVIDER}:FLASH_LOAN:{TOKEN}@{CHAIN}
FLASH_LOAN_PATTERN = re.compile(r"^[A-Z][A-Z0-9_-]+:FLASH_LOAN:[A-Z0-9]+@[A-Z]+$")

# Pattern: {PROTOCOL}-{CHAIN}:YIELD_BEARING:{TOKEN}@{CHAIN}
YIELD_BEARING_PATTERN = re.compile(r"^[A-Z][A-Z0-9]+-[A-Z]+:YIELD_BEARING:[A-Za-z0-9]+@[A-Z]+$")

# Generic three-part pattern: {VENUE}:{TYPE}:{DETAILS}
INSTRUMENT_ID_GENERIC = re.compile(
    r"^[A-Z][A-Z0-9_-]+:[A-Z][A-Z0-9_]+:.+$",
)


# ---------------------------------------------------------------------------
# Instrument ID Format Rules
# ---------------------------------------------------------------------------


class TestSpotAssetPattern:
    """WALLET:SPOT_ASSET:{TOKEN} format."""

    def test_valid_eth(self) -> None:
        assert SPOT_ASSET_PATTERN.match("WALLET:SPOT_ASSET:ETH")

    def test_valid_usdt(self) -> None:
        assert SPOT_ASSET_PATTERN.match("WALLET:SPOT_ASSET:USDT")

    def test_valid_wbtc(self) -> None:
        assert SPOT_ASSET_PATTERN.match("WALLET:SPOT_ASSET:WBTC")

    def test_invalid_lowercase(self) -> None:
        assert not SPOT_ASSET_PATTERN.match("WALLET:SPOT_ASSET:eth")

    def test_invalid_numeric(self) -> None:
        assert not SPOT_ASSET_PATTERN.match("WALLET:SPOT_ASSET:123")

    def test_invalid_empty_token(self) -> None:
        assert not SPOT_ASSET_PATTERN.match("WALLET:SPOT_ASSET:")


class TestPerpetualPattern:
    """{VENUE}:PERPETUAL:{BASE}-{QUOTE}@LIN@{VENUE} format."""

    def test_valid_hyperliquid(self) -> None:
        assert PERPETUAL_PATTERN.match("HYPERLIQUID:PERPETUAL:ETH-USDC@LIN@HYPERLIQUID")

    def test_valid_binance_futures(self) -> None:
        assert PERPETUAL_PATTERN.match("BINANCE-FUTURES:PERPETUAL:BTC-USDT@LIN@BINANCE-FUTURES")

    def test_valid_aster(self) -> None:
        assert PERPETUAL_PATTERN.match("ASTER:PERPETUAL:ETH-USDC@LIN@ASTER")

    def test_invalid_missing_lin(self) -> None:
        assert not PERPETUAL_PATTERN.match("HYPERLIQUID:PERPETUAL:ETH-USDC")

    def test_invalid_lowercase_venue(self) -> None:
        assert not PERPETUAL_PATTERN.match("hyperliquid:PERPETUAL:ETH-USDC@LIN@HYPERLIQUID")


class TestATokenPattern:
    """AAVE_V3-{CHAIN}:A_TOKEN:A{TOKEN}@{CHAIN} format."""

    def test_valid_ausdt(self) -> None:
        assert A_TOKEN_PATTERN.match("AAVE_V3-ETHEREUM:A_TOKEN:aUSDT@ETHEREUM")

    def test_valid_aweth(self) -> None:
        assert A_TOKEN_PATTERN.match("AAVE_V3-ETHEREUM:A_TOKEN:aWETH@ETHEREUM")

    def test_valid_arbitrum(self) -> None:
        assert A_TOKEN_PATTERN.match("AAVE_V3-ARBITRUM:A_TOKEN:aUSDC@ARBITRUM")

    def test_invalid_no_a_prefix(self) -> None:
        assert not A_TOKEN_PATTERN.match("AAVE_V3-ETHEREUM:A_TOKEN:USDT@ETHEREUM")

    def test_invalid_wrong_venue(self) -> None:
        assert not A_TOKEN_PATTERN.match("MORPHO-ETHEREUM:A_TOKEN:aUSDT@ETHEREUM")


class TestDebtTokenPattern:
    """AAVE_V3-{CHAIN}:DEBT_TOKEN:DEBT{TOKEN}@{CHAIN} format."""

    def test_valid_debtweth(self) -> None:
        assert DEBT_TOKEN_PATTERN.match("AAVE_V3-ETHEREUM:DEBT_TOKEN:debtWETH@ETHEREUM")

    def test_valid_debtusdc(self) -> None:
        assert DEBT_TOKEN_PATTERN.match("AAVE_V3-ETHEREUM:DEBT_TOKEN:debtUSDC@ETHEREUM")

    def test_invalid_no_debt_prefix(self) -> None:
        assert not DEBT_TOKEN_PATTERN.match("AAVE_V3-ETHEREUM:DEBT_TOKEN:WETH@ETHEREUM")


class TestLstPattern:
    """{PROTOCOL}:LST:{TOKEN}@{CHAIN} format."""

    def test_valid_etherfi_weeth(self) -> None:
        assert LST_PATTERN.match("ETHERFI:LST:WEETH@ETHEREUM")

    def test_valid_lido_steth(self) -> None:
        assert LST_PATTERN.match("LIDO:LST:STETH@ETHEREUM")

    def test_invalid_missing_chain(self) -> None:
        assert not LST_PATTERN.match("ETHERFI:LST:WEETH")

    def test_invalid_lowercase_protocol(self) -> None:
        assert not LST_PATTERN.match("etherfi:LST:WEETH@ETHEREUM")


class TestSwapPattern:
    """{CHAIN}:SWAP:{TOKEN_IN}-{TOKEN_OUT} format."""

    def test_valid_eth_swap(self) -> None:
        assert SWAP_PATTERN.match("ETHEREUM:SWAP:WETH-USDC")

    def test_valid_uniswap_swap(self) -> None:
        assert SWAP_PATTERN.match("UNISWAP_V3-ETHEREUM:SWAP:WETH-USDT")

    def test_invalid_missing_token_out(self) -> None:
        assert not SWAP_PATTERN.match("ETHEREUM:SWAP:WETH")


class TestRewardPattern:
    """{PROTOCOL}:REWARD:{TOKEN}@{CHAIN} format."""

    def test_valid_eigenlayer(self) -> None:
        assert REWARD_PATTERN.match("EIGENLAYER:REWARD:EIGEN@ETHEREUM")

    def test_valid_etherfi(self) -> None:
        assert REWARD_PATTERN.match("ETHERFI:REWARD:ETHFI@ETHEREUM")

    def test_invalid_missing_chain(self) -> None:
        assert not REWARD_PATTERN.match("EIGENLAYER:REWARD:EIGEN")


class TestFlashLoanPattern:
    """{PROVIDER}:FLASH_LOAN:{TOKEN}@{CHAIN} format."""

    def test_valid_aave_flash_loan(self) -> None:
        assert FLASH_LOAN_PATTERN.match("AAVE_V3-ETHEREUM:FLASH_LOAN:WETH@ETHEREUM")

    def test_valid_morpho_flash_loan(self) -> None:
        assert FLASH_LOAN_PATTERN.match("MORPHO-ETHEREUM:FLASH_LOAN:USDC@ETHEREUM")

    def test_invalid_missing_chain(self) -> None:
        assert not FLASH_LOAN_PATTERN.match("AAVE_V3-ETHEREUM:FLASH_LOAN:WETH")


class TestYieldBearingPattern:
    """{PROTOCOL}-{CHAIN}:YIELD_BEARING:{TOKEN}@{CHAIN} format."""

    def test_valid_ethena_susde(self) -> None:
        assert YIELD_BEARING_PATTERN.match("ETHENA-ETHEREUM:YIELD_BEARING:sUSDe@ETHEREUM")

    def test_invalid_no_chain_in_venue(self) -> None:
        assert not YIELD_BEARING_PATTERN.match("ETHENA:YIELD_BEARING:sUSDe@ETHEREUM")


# ---------------------------------------------------------------------------
# Cross-Strategy Instrument Coverage Matrix
# ---------------------------------------------------------------------------

# Maps each strategy to the instrument types it requires.
STRATEGY_INSTRUMENT_MATRIX: dict[str, list[str]] = {
    "AAVE_LENDING": ["A_TOKEN", "SPOT_ASSET", "TRANSFER"],
    "BASIS_TRADE": ["SPOT_ASSET", "PERPETUAL", "SWAP"],
    "STAKED_BASIS": ["LST", "PERPETUAL", "SWAP", "REWARD"],
    "RECURSIVE_STAKED_BASIS": [
        "LST",
        "PERPETUAL",
        "A_TOKEN",
        "DEBT_TOKEN",
        "FLASH_LOAN",
        "SWAP",
        "REWARD",
    ],
    "AMM_LP": ["SWAP", "ADD_LIQUIDITY", "REMOVE_LIQUIDITY", "COLLECT_FEES"],
    "ETHENA_BENCHMARK": ["YIELD_BEARING", "TRANSFER", "STAKE"],
}

# All known valid pattern names (superset of instrument types and operation-like IDs)
KNOWN_VALID_PATTERNS: set[str] = {
    "SPOT_ASSET",
    "PERPETUAL",
    "A_TOKEN",
    "DEBT_TOKEN",
    "LST",
    "SWAP",
    "REWARD",
    "FLASH_LOAN",
    "YIELD_BEARING",
    "POOL",
    # Operation-like types used as instrument categories in coverage matrix
    "TRANSFER",
    "ADD_LIQUIDITY",
    "REMOVE_LIQUIDITY",
    "COLLECT_FEES",
    "STAKE",
}

# Maps instrument type names to their regex validators (for structural types only)
PATTERN_VALIDATORS: dict[str, re.Pattern[str]] = {
    "SPOT_ASSET": SPOT_ASSET_PATTERN,
    "PERPETUAL": PERPETUAL_PATTERN,
    "A_TOKEN": A_TOKEN_PATTERN,
    "DEBT_TOKEN": DEBT_TOKEN_PATTERN,
    "LST": LST_PATTERN,
    "SWAP": SWAP_PATTERN,
    "REWARD": REWARD_PATTERN,
    "FLASH_LOAN": FLASH_LOAN_PATTERN,
    "YIELD_BEARING": YIELD_BEARING_PATTERN,
}

# Known valid sample IDs for each structural instrument type
SAMPLE_VALID_IDS: dict[str, list[str]] = {
    "SPOT_ASSET": ["WALLET:SPOT_ASSET:ETH", "WALLET:SPOT_ASSET:USDT", "WALLET:SPOT_ASSET:WBTC"],
    "PERPETUAL": [
        "HYPERLIQUID:PERPETUAL:ETH-USDC@LIN@HYPERLIQUID",
        "BINANCE-FUTURES:PERPETUAL:BTC-USDT@LIN@BINANCE-FUTURES",
        "ASTER:PERPETUAL:ETH-USDC@LIN@ASTER",
    ],
    "A_TOKEN": ["AAVE_V3-ETHEREUM:A_TOKEN:aUSDT@ETHEREUM", "AAVE_V3-ETHEREUM:A_TOKEN:aWETH@ETHEREUM"],
    "DEBT_TOKEN": ["AAVE_V3-ETHEREUM:DEBT_TOKEN:debtWETH@ETHEREUM"],
    "LST": ["ETHERFI:LST:WEETH@ETHEREUM", "LIDO:LST:STETH@ETHEREUM"],
    "SWAP": ["ETHEREUM:SWAP:WETH-USDC", "UNISWAP_V3-ETHEREUM:SWAP:WETH-USDT"],
    "REWARD": ["EIGENLAYER:REWARD:EIGEN@ETHEREUM", "ETHERFI:REWARD:ETHFI@ETHEREUM"],
    "FLASH_LOAN": ["AAVE_V3-ETHEREUM:FLASH_LOAN:WETH@ETHEREUM"],
    "YIELD_BEARING": ["ETHENA-ETHEREUM:YIELD_BEARING:sUSDe@ETHEREUM"],
}


class TestCrossStrategyInstrumentCoverage:
    """Validate that each strategy's instrument set is a subset of known patterns."""

    def test_all_strategy_instrument_types_are_known(self) -> None:
        """Every instrument type referenced by a strategy is in KNOWN_VALID_PATTERNS."""
        for strategy, types in STRATEGY_INSTRUMENT_MATRIX.items():
            for inst_type in types:
                assert inst_type in KNOWN_VALID_PATTERNS, (
                    f"Strategy {strategy} references unknown instrument type: {inst_type}"
                )

    def test_aave_lending_instruments(self) -> None:
        required = {"A_TOKEN", "SPOT_ASSET", "TRANSFER"}
        actual = set(STRATEGY_INSTRUMENT_MATRIX["AAVE_LENDING"])
        assert required == actual

    def test_basis_trade_instruments(self) -> None:
        required = {"SPOT_ASSET", "PERPETUAL", "SWAP"}
        actual = set(STRATEGY_INSTRUMENT_MATRIX["BASIS_TRADE"])
        assert required == actual

    def test_staked_basis_instruments(self) -> None:
        required = {"LST", "PERPETUAL", "SWAP", "REWARD"}
        actual = set(STRATEGY_INSTRUMENT_MATRIX["STAKED_BASIS"])
        assert required == actual

    def test_recursive_staked_basis_instruments(self) -> None:
        required = {"LST", "PERPETUAL", "A_TOKEN", "DEBT_TOKEN", "FLASH_LOAN", "SWAP", "REWARD"}
        actual = set(STRATEGY_INSTRUMENT_MATRIX["RECURSIVE_STAKED_BASIS"])
        assert required == actual

    def test_amm_lp_instruments(self) -> None:
        required = {"SWAP", "ADD_LIQUIDITY", "REMOVE_LIQUIDITY", "COLLECT_FEES"}
        actual = set(STRATEGY_INSTRUMENT_MATRIX["AMM_LP"])
        assert required == actual

    def test_ethena_benchmark_instruments(self) -> None:
        required = {"YIELD_BEARING", "TRANSFER", "STAKE"}
        actual = set(STRATEGY_INSTRUMENT_MATRIX["ETHENA_BENCHMARK"])
        assert required == actual

    def test_sample_ids_match_their_patterns(self) -> None:
        """Every known valid sample ID matches its declared pattern."""
        for inst_type, validator in PATTERN_VALIDATORS.items():
            samples = SAMPLE_VALID_IDS.get(inst_type, [])
            for sample_id in samples:
                assert validator.match(sample_id), f"Sample ID '{sample_id}' does not match {inst_type} pattern"

    def test_sample_ids_all_match_generic_three_part(self) -> None:
        """All sample IDs match the generic VENUE:TYPE:DETAILS pattern."""
        for inst_type, samples in SAMPLE_VALID_IDS.items():
            for sample_id in samples:
                assert INSTRUMENT_ID_GENERIC.match(sample_id), (
                    f"Sample ID '{sample_id}' ({inst_type}) does not match generic three-part pattern"
                )

    def test_recursive_is_superset_of_staked(self) -> None:
        """RECURSIVE_STAKED_BASIS instruments are a superset of STAKED_BASIS."""
        staked = set(STRATEGY_INSTRUMENT_MATRIX["STAKED_BASIS"])
        recursive = set(STRATEGY_INSTRUMENT_MATRIX["RECURSIVE_STAKED_BASIS"])
        assert staked.issubset(recursive), f"STAKED_BASIS types {staked - recursive} not in RECURSIVE_STAKED_BASIS"
