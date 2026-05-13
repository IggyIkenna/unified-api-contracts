"""Tests for WithdrawalApprovalRule UAC type + registry.

Phase 5.C — 6 tests.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from unified_api_contracts.internal.domain.treasury import (
    TreasurySource,
    WithdrawalApprovalRule,
)
from unified_api_contracts.registry.withdrawal_approval_rules import (
    get_approval_rules,
    get_approver_pool,
    get_required_approvers,
)

_POOL = frozenset(["op:alice", "op:bob", "op:charlie"])


class TestWithdrawalApprovalRule:
    def test_valid_rule_created(self) -> None:
        rule = WithdrawalApprovalRule(
            treasury_source=TreasurySource.COPPER,
            amount_bucket="LARGE",
            threshold_amount_usd=Decimal("100000"),
            required_approvers=2,
            approver_pool=_POOL,
        )
        assert rule.treasury_source == TreasurySource.COPPER
        assert rule.required_approvers == 2
        assert len(rule.approver_pool) == 3

    def test_approvers_required_below_threshold(self) -> None:
        rule = WithdrawalApprovalRule(
            treasury_source=TreasurySource.CEFFU,
            amount_bucket="MEDIUM",
            threshold_amount_usd=Decimal("10000"),
            required_approvers=2,
            approver_pool=_POOL,
        )
        # At or below threshold → 1 approver
        assert rule.approvers_required_for(Decimal("5000")) == 1
        assert rule.approvers_required_for(Decimal("10000")) == 1

    def test_approvers_required_above_threshold(self) -> None:
        rule = WithdrawalApprovalRule(
            treasury_source=TreasurySource.DEFI_HOT_WALLET,
            amount_bucket="LARGE",
            threshold_amount_usd=Decimal("100000"),
            required_approvers=3,
            approver_pool=_POOL,
        )
        assert rule.approvers_required_for(Decimal("100001")) == 3

    def test_quorum_pool_too_small_raises(self) -> None:
        with pytest.raises(ValueError, match="approver_pool size"):
            WithdrawalApprovalRule(
                treasury_source=TreasurySource.COPPER,
                amount_bucket="LARGE",
                threshold_amount_usd=Decimal("100000"),
                required_approvers=5,  # pool has only 3
                approver_pool=_POOL,
            )

    def test_required_approvers_zero_raises(self) -> None:
        with pytest.raises(ValueError, match="required_approvers must be >= 1"):
            WithdrawalApprovalRule(
                treasury_source=TreasurySource.COPPER,
                amount_bucket="SMALL",
                threshold_amount_usd=Decimal("0"),
                required_approvers=0,
                approver_pool=_POOL,
            )

    def test_negative_threshold_raises(self) -> None:
        with pytest.raises(ValueError, match="threshold_amount_usd must be >= 0"):
            WithdrawalApprovalRule(
                treasury_source=TreasurySource.COPPER,
                amount_bucket="SMALL",
                threshold_amount_usd=Decimal("-1"),
                required_approvers=1,
                approver_pool=_POOL,
            )


class TestWithdrawalApprovalRegistry:
    def test_rule_lookup_copper(self) -> None:
        rules = get_approval_rules(TreasurySource.COPPER)
        assert len(rules) == 2
        assert all(r.treasury_source == TreasurySource.COPPER for r in rules)

    def test_threshold_dispatch_small(self) -> None:
        # $5k → below MEDIUM threshold ($10k) → 1 approver
        assert get_required_approvers(TreasurySource.COPPER, Decimal("5000")) == 1

    def test_threshold_dispatch_medium(self) -> None:
        # $50k → above MEDIUM ($10k) but below LARGE ($100k) → 2 approvers
        assert get_required_approvers(TreasurySource.COPPER, Decimal("50000")) == 2

    def test_threshold_dispatch_large(self) -> None:
        # $500k → above LARGE ($100k) → 3 approvers
        assert get_required_approvers(TreasurySource.COPPER, Decimal("500000")) == 3

    def test_approver_pool_non_empty(self) -> None:
        pool = get_approver_pool(TreasurySource.DEFI_HOT_WALLET)
        assert len(pool) >= 3

    def test_all_sources_have_rules(self) -> None:
        for source in TreasurySource:
            rules = get_approval_rules(source)
            assert len(rules) > 0, f"No rules for {source}"
