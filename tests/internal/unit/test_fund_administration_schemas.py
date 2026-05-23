"""Unit tests for the fund_administration domain sub-package + WalletRole on TradingAccount.

Covers:
- frozen-model invariants (all three wire types + enums)
- roundtrip serialisation via pydantic
- optional fields default to None
- facade re-exports from ``unified_api_contracts.internal`` + ``unified_api_contracts.account``
- TradingAccount back-compat (constructing without ``wallet_role`` still works)
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError


class TestEnums:
    def test_subscription_status_members(self) -> None:
        from unified_api_contracts.internal.domain.fund_administration import (
            SubscriptionStatus,
        )

        assert SubscriptionStatus.PENDING == "PENDING"
        assert SubscriptionStatus.APPROVED == "APPROVED"
        assert SubscriptionStatus.REJECTED == "REJECTED"
        assert SubscriptionStatus.SETTLED == "SETTLED"
        assert {s.value for s in SubscriptionStatus} == {
            "PENDING",
            "APPROVED",
            "REJECTED",
            "SETTLED",
        }

    def test_redemption_status_members(self) -> None:
        from unified_api_contracts.internal.domain.fund_administration import (
            RedemptionStatus,
        )

        assert {s.value for s in RedemptionStatus} == {
            "PENDING",
            "APPROVED",
            "REJECTED",
            "PROCESSED",
            "SETTLED",
        }

    def test_allocation_execution_status_members(self) -> None:
        from unified_api_contracts.internal.domain.fund_administration import (
            AllocationExecutionStatus,
        )

        assert {s.value for s in AllocationExecutionStatus} == {
            "PENDING",
            "IN_PROGRESS",
            "COMPLETED",
            "FAILED",
        }


class TestAllocatorSubscription:
    def _minimal(self) -> dict[str, object]:
        from unified_api_contracts.internal.domain.fund_administration import (
            SubscriptionStatus,
        )

        return {
            "subscription_id": "sub-1",
            "fund_id": "fund-alpha",
            "allocator_id": "client-42",
            "share_class": "USDC",
            "requested_amount_usd": Decimal("100000"),
            "requested_timestamp": datetime(2026, 4, 20, 10, tzinfo=UTC),
            "status": SubscriptionStatus.PENDING,
        }

    def test_minimal_construction_and_defaults(self) -> None:
        from unified_api_contracts.internal.domain.fund_administration import (
            AllocatorSubscription,
        )

        sub = AllocatorSubscription(**self._minimal())  # type: ignore[arg-type]
        assert sub.nav_strike_snapshot_id is None
        assert sub.units_issued is None
        assert sub.approval_timestamp is None
        assert sub.rejection_reason is None

    def test_full_construction(self) -> None:
        from unified_api_contracts.internal.domain.fund_administration import (
            AllocatorSubscription,
            SubscriptionStatus,
        )

        sub = AllocatorSubscription(
            subscription_id="sub-2",
            fund_id="fund-alpha",
            allocator_id="client-42",
            share_class="USDC",
            requested_amount_usd=Decimal("100000"),
            requested_timestamp=datetime(2026, 4, 20, 10, tzinfo=UTC),
            status=SubscriptionStatus.SETTLED,
            nav_strike_snapshot_id="nav-2026-04-20",
            units_issued=Decimal("99999.99887654"),
            approval_timestamp=datetime(2026, 4, 20, 11, tzinfo=UTC),
        )
        assert sub.units_issued == Decimal("99999.99887654")

    def test_frozen(self) -> None:
        from unified_api_contracts.internal.domain.fund_administration import (
            AllocatorSubscription,
        )

        sub = AllocatorSubscription(**self._minimal())  # type: ignore[arg-type]
        with pytest.raises(ValidationError):
            sub.subscription_id = "hacked"  # type: ignore[misc]

    def test_roundtrip(self) -> None:
        from unified_api_contracts.internal.domain.fund_administration import (
            AllocatorSubscription,
        )

        sub = AllocatorSubscription(**self._minimal())  # type: ignore[arg-type]
        payload = sub.model_dump(mode="json")
        assert payload["subscription_id"] == "sub-1"
        assert payload["status"] == "PENDING"
        restored = AllocatorSubscription.model_validate(payload)
        assert restored == sub

    def test_naive_timestamp_rejected(self) -> None:
        from unified_api_contracts.internal.domain.fund_administration import (
            AllocatorSubscription,
            SubscriptionStatus,
        )

        with pytest.raises(ValidationError):
            AllocatorSubscription(
                subscription_id="sub-3",
                fund_id="fund-alpha",
                allocator_id="client-42",
                share_class="USDC",
                requested_amount_usd=Decimal("1"),
                requested_timestamp=datetime(2026, 4, 20, 10),  # naive — rejected
                status=SubscriptionStatus.PENDING,
            )


class TestAllocatorRedemption:
    def _minimal(self) -> dict[str, object]:
        from unified_api_contracts.internal.domain.fund_administration import (
            RedemptionStatus,
        )

        return {
            "redemption_id": "red-1",
            "fund_id": "fund-alpha",
            "allocator_id": "client-42",
            "share_class": "USDC",
            "units_to_redeem": Decimal("1000"),
            "destination": "0xabc...",
            "requested_timestamp": datetime(2026, 4, 20, 12, tzinfo=UTC),
            "status": RedemptionStatus.PENDING,
            "grace_period_days": 5,
        }

    def test_minimal_defaults(self) -> None:
        from unified_api_contracts.internal.domain.fund_administration import (
            AllocatorRedemption,
        )

        red = AllocatorRedemption(**self._minimal())  # type: ignore[arg-type]
        assert red.redemption_nav_snapshot_id is None
        assert red.cash_amount_due_usd is None
        assert red.settlement_timestamp is None
        assert red.settlement_reference is None
        assert red.rejection_reason is None

    def test_processed_transition_fields(self) -> None:
        from unified_api_contracts.internal.domain.fund_administration import (
            AllocatorRedemption,
            RedemptionStatus,
        )

        red = AllocatorRedemption(
            redemption_id="red-2",
            fund_id="fund-alpha",
            allocator_id="client-42",
            share_class="USDC",
            units_to_redeem=Decimal("1000"),
            destination="0xabc",
            requested_timestamp=datetime(2026, 4, 20, 12, tzinfo=UTC),
            status=RedemptionStatus.PROCESSED,
            grace_period_days=5,
            redemption_nav_snapshot_id="nav-2026-04-25",
            cash_amount_due_usd=Decimal("100100"),
            settlement_reference="0xdeadbeef",
        )
        assert red.status == RedemptionStatus.PROCESSED
        assert red.settlement_reference == "0xdeadbeef"

    def test_roundtrip(self) -> None:
        from unified_api_contracts.internal.domain.fund_administration import (
            AllocatorRedemption,
        )

        red = AllocatorRedemption(**self._minimal())  # type: ignore[arg-type]
        payload = red.model_dump(mode="json")
        restored = AllocatorRedemption.model_validate(payload)
        assert restored == red


class TestFundAllocation:
    def test_minimal_defaults(self) -> None:
        from unified_api_contracts.internal.domain.fund_administration import (
            AllocationExecutionStatus,
            FundAllocation,
        )

        alloc = FundAllocation(
            allocation_id="alloc-1",
            fund_id="fund-alpha",
            share_class="USDC",
            strategy_id="btc-ml-spot",
            target_amount_usd=Decimal("500000"),
            allocation_timestamp=datetime(2026, 4, 20, 14, tzinfo=UTC),
            execution_status=AllocationExecutionStatus.PENDING,
        )
        assert alloc.executed_amount_usd is None
        assert alloc.executed_timestamp is None

    def test_completed_populates_execution_fields(self) -> None:
        from unified_api_contracts.internal.domain.fund_administration import (
            AllocationExecutionStatus,
            FundAllocation,
        )

        alloc = FundAllocation(
            allocation_id="alloc-2",
            fund_id="fund-alpha",
            share_class="USDC",
            strategy_id="btc-ml-spot",
            target_amount_usd=Decimal("500000"),
            allocation_timestamp=datetime(2026, 4, 20, 14, tzinfo=UTC),
            execution_status=AllocationExecutionStatus.COMPLETED,
            executed_amount_usd=Decimal("499950"),
            executed_timestamp=datetime(2026, 4, 20, 14, 5, tzinfo=UTC),
        )
        assert alloc.execution_status == AllocationExecutionStatus.COMPLETED

    def test_frozen(self) -> None:
        from unified_api_contracts.internal.domain.fund_administration import (
            AllocationExecutionStatus,
            FundAllocation,
        )

        alloc = FundAllocation(
            allocation_id="alloc-3",
            fund_id="fund-alpha",
            share_class="USDC",
            strategy_id="btc-ml-spot",
            target_amount_usd=Decimal("1"),
            allocation_timestamp=datetime(2026, 4, 20, 14, tzinfo=UTC),
            execution_status=AllocationExecutionStatus.PENDING,
        )
        with pytest.raises(ValidationError):
            alloc.allocation_id = "hacked"  # type: ignore[misc]


class TestInternalFacadeReExports:
    def test_sub_package_re_exports(self) -> None:
        from unified_api_contracts.internal.domain.fund_administration import (
            AllocationExecutionStatus,
            AllocatorRedemption,
            AllocatorSubscription,
            FundAllocation,
            RedemptionStatus,
            SubscriptionStatus,
        )

        assert SubscriptionStatus is not None
        assert RedemptionStatus is not None
        assert AllocationExecutionStatus is not None
        assert AllocatorSubscription is not None
        assert AllocatorRedemption is not None
        assert FundAllocation is not None

    def test_internal_facade_re_exports(self) -> None:
        from unified_api_contracts.internal import (
            AllocationExecutionStatus,
            AllocatorRedemption,
            AllocatorSubscription,
            FundAllocation,
            RedemptionStatus,
            SubscriptionStatus,
            TradingAccount,
            WalletRole,
        )

        # Each symbol resolves to the underlying definition.
        from unified_api_contracts.internal.domain.fund_administration import (
            AllocationExecutionStatus as InnerAllocationExecutionStatus,
        )
        from unified_api_contracts.internal.domain.fund_administration import (
            AllocatorSubscription as InnerAllocatorSubscription,
        )

        assert AllocationExecutionStatus is InnerAllocationExecutionStatus
        assert AllocatorSubscription is InnerAllocatorSubscription
        assert SubscriptionStatus("PENDING") is not None
        assert RedemptionStatus("PENDING") is not None
        assert AllocatorRedemption is not None
        assert FundAllocation is not None
        assert TradingAccount is not None
        assert WalletRole("TREASURY") is WalletRole.TREASURY


class TestTradingAccountWalletRole:
    def test_wallet_role_enum_values(self) -> None:
        from unified_api_contracts.account import WalletRole

        assert WalletRole.TREASURY == "TREASURY"
        assert WalletRole.TRADING == "TRADING"
        assert WalletRole.RESERVE == "RESERVE"
        assert {r.value for r in WalletRole} == {"TREASURY", "TRADING", "RESERVE"}

    def test_trading_account_back_compat_construction_without_wallet_role(
        self,
    ) -> None:
        """Existing call sites that never heard of wallet_role must still work."""
        from unified_api_contracts.account import AccountType, TradingAccount

        account = TradingAccount(
            client_id="c1",
            venue="BINANCE",
            account_label="main",
            account_type=AccountType.CEFI_EXCHANGE,
        )
        assert account.wallet_role is None
        assert account.account_id == "c1:BINANCE:main"

    def test_trading_account_with_wallet_role(self) -> None:
        from unified_api_contracts.account import (
            AccountType,
            TradingAccount,
            WalletRole,
        )

        account = TradingAccount(
            client_id="fund-alpha",
            venue="AAVE_V3-ETHEREUM",
            account_label="0xabc",
            account_type=AccountType.DEFI_WALLET,
            chain="ETHEREUM",
            share_class="USDC",
            wallet_role=WalletRole.TREASURY,
        )
        assert account.wallet_role == WalletRole.TREASURY

    def test_trading_account_frozen_dataclass(self) -> None:
        """TradingAccount is a frozen dataclass; wallet_role cannot be mutated."""
        from dataclasses import FrozenInstanceError

        from unified_api_contracts.account import (
            AccountType,
            TradingAccount,
            WalletRole,
        )

        account = TradingAccount(
            client_id="c1",
            venue="BINANCE",
            account_label="main",
            account_type=AccountType.CEFI_EXCHANGE,
        )
        with pytest.raises(FrozenInstanceError):
            account.wallet_role = WalletRole.TRADING  # type: ignore[misc]

    def test_account_module_facade_re_exports_wallet_role(self) -> None:
        from unified_api_contracts.account import WalletRole as F_WalletRole
        from unified_api_contracts.internal.domain.account import (
            WalletRole as _WalletRole,
        )

        assert F_WalletRole is _WalletRole
