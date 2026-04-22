"""Tests for G2.9 gap #3 — FlashLoanReceiverRegistry."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from unified_api_contracts.internal.architecture_v2.flash_loan_receiver import (
    CONSUMER_CALL_SITES,
    FLASH_LOAN_RECEIVER_REGISTRY,
    FlashLoanProtocol,
    FlashLoanReceiverDeployment,
    FlashLoanReceiverNotFoundError,
    _is_valid_address,
    _validate_registry_invariants,
    flash_loan_receiver_for,
    receivers_for_chain,
    receivers_supporting_token,
)


class TestRegistryShape:
    def test_registry_not_empty(self) -> None:
        assert len(FLASH_LOAN_RECEIVER_REGISTRY) >= 5

    def test_chain_protocol_pairs_unique(self) -> None:
        pairs = [(e.chain, e.protocol) for e in FLASH_LOAN_RECEIVER_REGISTRY]
        assert len(pairs) == len(set(pairs))

    def test_every_entry_frozen(self) -> None:
        for entry in FLASH_LOAN_RECEIVER_REGISTRY:
            with pytest.raises(ValidationError):
                entry.chain = "MUTATED"  # type: ignore[misc]


class TestContent:
    def test_ethereum_aave_v3_resolvable(self) -> None:
        entry = flash_loan_receiver_for("ETHEREUM", FlashLoanProtocol.AAVE_V3)
        assert "USDC" in entry.supported_tokens
        assert entry.receiver_address.startswith("0x")

    def test_balancer_v2_on_ethereum(self) -> None:
        entry = flash_loan_receiver_for("ETHEREUM", FlashLoanProtocol.BALANCER_V2)
        assert entry.protocol is FlashLoanProtocol.BALANCER_V2

    def test_receivers_for_arbitrum(self) -> None:
        receivers = receivers_for_chain("ARBITRUM")
        protocols = {e.protocol for e in receivers}
        assert FlashLoanProtocol.AAVE_V3 in protocols
        assert FlashLoanProtocol.UNISWAP_V3_FLASH_SWAP in protocols

    def test_receivers_supporting_usdc(self) -> None:
        receivers = receivers_supporting_token("USDC")
        # USDC is borrowable on every chain — all entries include it.
        assert len(receivers) >= 5


class TestFailLoud:
    def test_unknown_chain_raises(self) -> None:
        with pytest.raises(FlashLoanReceiverNotFoundError, match="no FlashLoanReceiver"):
            flash_loan_receiver_for("UNKNOWN_CHAIN", FlashLoanProtocol.AAVE_V3)

    def test_chain_without_protocol_raises(self) -> None:
        with pytest.raises(FlashLoanReceiverNotFoundError):
            flash_loan_receiver_for("POLYGON", FlashLoanProtocol.UNISWAP_V3_FLASH_SWAP)


class TestAddressValidation:
    def test_evm_checksum_address_accepted(self) -> None:
        assert _is_valid_address("0x" + "a" * 40)

    def test_short_address_rejected(self) -> None:
        assert not _is_valid_address("0x123")

    def test_solana_program_id_accepted(self) -> None:
        # 32-44 base58 chars.
        assert _is_valid_address("BPFLoader2111111111111111111111111111111111")

    def test_non_hex_rejected(self) -> None:
        assert not _is_valid_address("0xZZZZ" + "a" * 36)


class TestInvariants:
    def test_duplicate_pair_rejected(self) -> None:
        bad = (
            FlashLoanReceiverDeployment(
                chain="X",
                protocol=FlashLoanProtocol.AAVE_V3,
                receiver_address="0x" + "a" * 40,
                deployment_commit_sha="abc1234",
                deployed_at_utc="2026-04-20T12:00:00Z",
                supported_tokens=("USDC",),
            ),
            FlashLoanReceiverDeployment(
                chain="X",
                protocol=FlashLoanProtocol.AAVE_V3,
                receiver_address="0x" + "b" * 40,
                deployment_commit_sha="abc1234",
                deployed_at_utc="2026-04-20T12:00:00Z",
                supported_tokens=("USDC",),
            ),
        )
        with pytest.raises(ValueError, match="duplicate"):
            _validate_registry_invariants(bad)

    def test_invalid_address_rejected(self) -> None:
        bad = (
            FlashLoanReceiverDeployment(
                chain="X",
                protocol=FlashLoanProtocol.AAVE_V3,
                receiver_address="not_an_address",
                deployment_commit_sha="abc1234",
                deployed_at_utc="2026-04-20T12:00:00Z",
                supported_tokens=("USDC",),
            ),
        )
        with pytest.raises(ValueError, match="not EVM/Solana shape"):
            _validate_registry_invariants(bad)

    def test_empty_tokens_rejected(self) -> None:
        bad = (
            FlashLoanReceiverDeployment(
                chain="X",
                protocol=FlashLoanProtocol.AAVE_V3,
                receiver_address="0x" + "a" * 40,
                deployment_commit_sha="abc1234",
                deployed_at_utc="2026-04-20T12:00:00Z",
                supported_tokens=(),
            ),
        )
        with pytest.raises(ValueError, match="must be non-empty"):
            _validate_registry_invariants(bad)


class TestConsumerReferences:
    def test_consumer_call_sites_non_empty(self) -> None:
        assert len(CONSUMER_CALL_SITES) >= 1

    def test_consumer_call_sites_include_aave(self) -> None:
        assert any("aave" in site for site in CONSUMER_CALL_SITES)
