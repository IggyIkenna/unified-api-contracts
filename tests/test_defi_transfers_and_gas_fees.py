"""Unit tests for DeFi transfer and gas fee types."""

from datetime import UTC, datetime
from decimal import Decimal

from unified_api_contracts.internal.domain.defi import (
    AlchemyTransferRecord,
    AlchemyTransfersResponse,
    BlockGasFee,
    BridgeProtocol,
    EthBalanceImpact,
    GasCostAction,
    GasFeeSnapshot,
    InstructionGasCost,
    TransferConfirmation,
    TransferRecord,
    TransferStatus,
    TransferType,
)


class TestTransferTypes:
    """Test transfer domain types."""

    def test_transfer_type_values(self) -> None:
        assert TransferType.SAME_CHAIN == "SAME_CHAIN"
        assert TransferType.CROSS_CHAIN == "CROSS_CHAIN"
        assert TransferType.CEX_WITHDRAWAL == "CEX_WITHDRAWAL"
        assert TransferType.SWEEP == "SWEEP"

    def test_transfer_status_values(self) -> None:
        assert TransferStatus.PENDING == "PENDING"
        assert TransferStatus.BRIDGING == "BRIDGING"
        assert TransferStatus.CONFIRMED == "CONFIRMED"

    def test_bridge_protocol_values(self) -> None:
        assert BridgeProtocol.SOCKET == "SOCKET"
        assert BridgeProtocol.STARGATE == "STARGATE"
        assert BridgeProtocol.ACROSS == "ACROSS"

    def test_transfer_record_serialization(self) -> None:
        record = TransferRecord(
            transfer_id="t-001",
            transfer_type=TransferType.SAME_CHAIN,
            status=TransferStatus.CONFIRMED,
            source_chain_id=1,
            dest_chain_id=1,
            source_address="0xabc",
            dest_address="0xdef",
            token="USDC",
            amount_wei="1000000",
            tx_hash="0x123",
            gas_used=65000,
            gas_price_gwei=Decimal("30"),
            gas_cost_eth=Decimal("0.00195"),
        )
        data = record.model_dump()
        assert data["transfer_id"] == "t-001"
        assert data["transfer_type"] == "SAME_CHAIN"
        assert data["gas_used"] == 65000

    def test_transfer_confirmation(self) -> None:
        confirmation = TransferConfirmation(
            transfer_id="t-001",
            tx_hash="0x123",
            block_number=1000,
            confirmed=True,
            actual_value=Decimal("1.0"),
            expected_value=Decimal("1.0"),
            discrepancy_wei=Decimal("0"),
            confirmations=12,
            timestamp=datetime.now(UTC),
        )
        assert confirmation.confirmed is True
        assert confirmation.discrepancy_wei == Decimal("0")

    def test_alchemy_transfer_record(self) -> None:
        record = AlchemyTransferRecord(
            block_num="0xb0eadc",
            unique_id="0x123:external",
            tx_hash="0x123",
            from_address="0xabc",
            to_address="0xdef",
            value=Decimal("0.5"),
            asset="ETH",
            category="external",
        )
        assert record.value == Decimal("0.5")
        assert record.category == "external"

    def test_alchemy_transfers_response(self) -> None:
        response = AlchemyTransfersResponse(
            transfers=[
                AlchemyTransferRecord(
                    block_num="0x1",
                    unique_id="uid1",
                    tx_hash="0xaaa",
                    from_address="0x1",
                    to_address="0x2",
                    category="external",
                )
            ],
            page_key="next-page",
        )
        assert len(response.transfers) == 1
        assert response.page_key == "next-page"


class TestGasFeeTypes:
    """Test gas fee domain types."""

    def test_gas_cost_action_extended_values(self) -> None:
        assert GasCostAction.TRANSFER == "TRANSFER"
        assert GasCostAction.BRIDGE == "BRIDGE"
        assert GasCostAction.APPROVE == "APPROVE"
        assert GasCostAction.ADD_LIQUIDITY == "ADD_LIQUIDITY"
        assert GasCostAction.FLASH_BORROW == "FLASH_BORROW"
        assert GasCostAction.ATOMIC_BUNDLE == "ATOMIC_BUNDLE"
        # Original values still present
        assert GasCostAction.SWAP == "SWAP"
        assert GasCostAction.BORROW == "BORROW"

    def test_block_gas_fee(self) -> None:
        fee = BlockGasFee(
            chain_id=1,
            block_number=19000000,
            timestamp=datetime.now(UTC),
            base_fee_gwei=Decimal("25.5"),
            priority_fee_p25_gwei=Decimal("1.0"),
            priority_fee_p50_gwei=Decimal("2.0"),
            priority_fee_p75_gwei=Decimal("5.0"),
            gas_used_ratio=0.75,
        )
        assert fee.chain_id == 1
        assert fee.base_fee_gwei == Decimal("25.5")
        assert fee.blob_base_fee_gwei is None

    def test_gas_fee_snapshot(self) -> None:
        snapshot = GasFeeSnapshot(
            chain_id=42161,
            timestamp=datetime.now(UTC),
            block_number=200000000,
            base_fee_gwei=Decimal("0.1"),
            priority_fee_gwei=Decimal("0.01"),
            eth_price_usd=Decimal("3500"),
        )
        assert snapshot.chain_id == 42161
        assert snapshot.eth_price_usd == Decimal("3500")

    def test_instruction_gas_cost(self) -> None:
        cost = InstructionGasCost(
            instruction_id="instr-001",
            operation="SWAP",
            chain_id=1,
            gas_units=200000,
            gas_price_gwei=Decimal("30"),
            priority_fee_gwei=Decimal("3"),
            gas_cost_eth=Decimal("0.006"),
            gas_cost_usd=Decimal("21.00"),
            eth_price_usd=Decimal("3500"),
            block_number=19000000,
            timestamp=datetime.now(UTC),
        )
        assert cost.gas_units == 200000
        assert cost.gas_cost_usd == Decimal("21.00")

    def test_eth_balance_impact(self) -> None:
        impact = EthBalanceImpact(
            wallet_address="0xabc",
            chain_id=1,
            instruction_id="instr-001",
            gas_cost_eth=Decimal("0.01"),
            eth_balance_before=Decimal("0.005"),
            eth_balance_after=Decimal("-0.005"),
            creates_eth_debt=True,
            debt_amount_eth=Decimal("0.005"),
        )
        assert impact.creates_eth_debt is True
        assert impact.debt_amount_eth == Decimal("0.005")
