"""Unit tests for ``resolve_lending_underlying`` (session-3 lending resolver, 2026-07-26).

SSOT: unified-trading-pm plans/active/defi_lending_writer_retire_prerequisite_2026_07_20.md
(Progress Log, todo 15) + codex/02-data/defi-canonical-naming-ssot.md.
"""

from unified_api_contracts import InstrumentType
from unified_api_contracts.internal.domain.defi.lending_underlying_resolver import (
    LendingUnderlyingRef,
    resolve_lending_underlying,
)


def test_aave_v3_a_token_resolves_supply_side() -> None:
    ref = resolve_lending_underlying("AAVE_V3-ETHEREUM:A_TOKEN:AUSDC", InstrumentType.A_TOKEN)

    assert ref == LendingUnderlyingRef(
        protocol="aave_v3",
        chain="ETHEREUM",
        underlying_symbol="USDC",
        rate_field="supply_apy",
    )


def test_aave_v3_debt_token_resolves_borrow_side() -> None:
    ref = resolve_lending_underlying("AAVE_V3-ARBITRUM:DEBT_TOKEN:DEBTUSDC", InstrumentType.DEBT_TOKEN)

    assert ref == LendingUnderlyingRef(
        protocol="aave_v3",
        chain="ARBITRUM",
        underlying_symbol="USDC",
        rate_field="borrow_apy",
    )


def test_spark_uses_same_prefix_pair_as_aave_v3() -> None:
    a_ref = resolve_lending_underlying("SPARK-ETHEREUM:A_TOKEN:ADAI", InstrumentType.A_TOKEN)
    debt_ref = resolve_lending_underlying("SPARK-ETHEREUM:DEBT_TOKEN:DEBTDAI", InstrumentType.DEBT_TOKEN)

    assert a_ref is not None and a_ref.underlying_symbol == "DAI" and a_ref.rate_field == "supply_apy"
    assert debt_ref is not None and debt_ref.underlying_symbol == "DAI" and debt_ref.rate_field == "borrow_apy"


def test_compound_v3_uses_different_prefix_pair_than_aave() -> None:
    """Regression guard: Compound V3 mints C{SYM}/BORROW{SYM}, NOT A{SYM}/DEBT{SYM} --
    a universal-prefix implementation would silently fail to resolve every
    Compound V3 instrument (or worse, resolve to the wrong underlying_symbol)."""
    a_ref = resolve_lending_underlying("COMPOUND_V3-ETHEREUM:A_TOKEN:CUSDC", InstrumentType.A_TOKEN)
    debt_ref = resolve_lending_underlying("COMPOUND_V3-ETHEREUM:DEBT_TOKEN:BORROWUSDC", InstrumentType.DEBT_TOKEN)

    assert a_ref is not None and a_ref.underlying_symbol == "USDC" and a_ref.protocol == "compound_v3"
    assert debt_ref is not None and debt_ref.underlying_symbol == "USDC"

    # An aave-shaped symbol under the compound_v3 protocol tag must NOT resolve --
    # proves the prefix table is genuinely per-protocol, not a shared default.
    wrong_shape = resolve_lending_underlying("COMPOUND_V3-ETHEREUM:A_TOKEN:AUSDC", InstrumentType.A_TOKEN)
    assert wrong_shape is None


def test_isolated_market_morpho_symbol_returns_none_not_a_guess() -> None:
    """Morpho mints A{marketId-derived-pair}, not a single-reserve symbol -- there is
    no well-defined underlying_symbol to join lending_indices on, so this must return
    an honest None rather than fabricate a wrong one."""
    ref = resolve_lending_underlying("MORPHO-ETHEREUM:A_TOKEN:AWETH-USDC-1a2b3c4d", InstrumentType.A_TOKEN)

    assert ref is None


def test_non_lending_instrument_type_returns_none() -> None:
    ref = resolve_lending_underlying("LIDO-ETHEREUM:LST:STETH", InstrumentType.LST)

    assert ref is None


def test_unregistered_protocol_returns_none() -> None:
    ref = resolve_lending_underlying("VENUS-BSC:A_TOKEN:AUSDC", InstrumentType.A_TOKEN)

    assert ref is None


def test_malformed_key_missing_type_segment_returns_none() -> None:
    ref = resolve_lending_underlying("AAVE_V3-ETHEREUM:AUSDC", InstrumentType.A_TOKEN)

    assert ref is None


def test_malformed_key_missing_chain_segment_returns_none() -> None:
    ref = resolve_lending_underlying("AAVE_V3:A_TOKEN:AUSDC", InstrumentType.A_TOKEN)

    assert ref is None


def test_a_token_symbol_without_matching_prefix_returns_none() -> None:
    """A DEBT_TOKEN-shaped symbol passed as A_TOKEN must not resolve -- proves the
    prefix match is exact, not a loose substring check."""
    ref = resolve_lending_underlying("AAVE_V3-ETHEREUM:A_TOKEN:DEBTUSDC", InstrumentType.A_TOKEN)

    assert ref is None
