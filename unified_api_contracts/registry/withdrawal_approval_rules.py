"""Withdrawal approval rules registry.

Default approval rules per TreasurySource for the May-23 cutover.

Per ``wallet_treasury_client_flow_2026_05_10.md`` Phase 5.C.

Rules define N-of-M quorum requirements based on withdrawal size:
  - SMALL  (≤ $10k): 1 approver
  - MEDIUM ($10k - $100k): 2 approvers (N-of-M where M = pool size)
  - LARGE  (> $100k): 3 approvers

Operator IDs listed are the canonical May-23 cutover approver pool.
"""

from __future__ import annotations

from decimal import Decimal

from unified_api_contracts.internal.domain.treasury import (
    TreasurySource,
    WithdrawalApprovalRule,
)

# Canonical cutover approver pool (operator IDs)
_CUTOVER_APPROVER_POOL: frozenset[str] = frozenset(
    [
        "operator:ikenna",
        "operator:harsh",
        "operator:system_admin",
    ]
)

# ---------------------------------------------------------------------------
# Default withdrawal approval rules (one per source per bucket tier)
# ---------------------------------------------------------------------------

# Each TreasurySource has a LARGE rule (threshold = $100k, 3-of-M quorum).
# Amounts at or below the threshold use the rule's single-approver path.
# For MEDIUM ($10k-$100k) amounts use 2-of-M; above $100k uses 3-of-M.
# We model this as two rules per source: the MEDIUM rule at $10k threshold,
# and the LARGE rule at $100k threshold, returning max required for the amount.

_DEFAULT_RULES: dict[TreasurySource, list[WithdrawalApprovalRule]] = {
    TreasurySource.COPPER: [
        WithdrawalApprovalRule(
            treasury_source=TreasurySource.COPPER,
            amount_bucket="MEDIUM",
            threshold_amount_usd=Decimal("10000"),
            required_approvers=2,
            approver_pool=_CUTOVER_APPROVER_POOL,
        ),
        WithdrawalApprovalRule(
            treasury_source=TreasurySource.COPPER,
            amount_bucket="LARGE",
            threshold_amount_usd=Decimal("100000"),
            required_approvers=3,
            approver_pool=_CUTOVER_APPROVER_POOL,
        ),
    ],
    TreasurySource.CEFFU: [
        WithdrawalApprovalRule(
            treasury_source=TreasurySource.CEFFU,
            amount_bucket="MEDIUM",
            threshold_amount_usd=Decimal("10000"),
            required_approvers=2,
            approver_pool=_CUTOVER_APPROVER_POOL,
        ),
        WithdrawalApprovalRule(
            treasury_source=TreasurySource.CEFFU,
            amount_bucket="LARGE",
            threshold_amount_usd=Decimal("100000"),
            required_approvers=3,
            approver_pool=_CUTOVER_APPROVER_POOL,
        ),
    ],
    TreasurySource.DEFI_HOT_WALLET: [
        WithdrawalApprovalRule(
            treasury_source=TreasurySource.DEFI_HOT_WALLET,
            amount_bucket="MEDIUM",
            threshold_amount_usd=Decimal("10000"),
            required_approvers=2,
            approver_pool=_CUTOVER_APPROVER_POOL,
        ),
        WithdrawalApprovalRule(
            treasury_source=TreasurySource.DEFI_HOT_WALLET,
            amount_bucket="LARGE",
            threshold_amount_usd=Decimal("100000"),
            required_approvers=3,
            approver_pool=_CUTOVER_APPROVER_POOL,
        ),
    ],
    TreasurySource.SUB_ACCOUNT_HYPERLIQUID: [
        WithdrawalApprovalRule(
            treasury_source=TreasurySource.SUB_ACCOUNT_HYPERLIQUID,
            amount_bucket="MEDIUM",
            threshold_amount_usd=Decimal("10000"),
            required_approvers=2,
            approver_pool=_CUTOVER_APPROVER_POOL,
        ),
        WithdrawalApprovalRule(
            treasury_source=TreasurySource.SUB_ACCOUNT_HYPERLIQUID,
            amount_bucket="LARGE",
            threshold_amount_usd=Decimal("100000"),
            required_approvers=3,
            approver_pool=_CUTOVER_APPROVER_POOL,
        ),
    ],
    TreasurySource.SUB_ACCOUNT_DRIFT: [
        WithdrawalApprovalRule(
            treasury_source=TreasurySource.SUB_ACCOUNT_DRIFT,
            amount_bucket="MEDIUM",
            threshold_amount_usd=Decimal("10000"),
            required_approvers=2,
            approver_pool=_CUTOVER_APPROVER_POOL,
        ),
        WithdrawalApprovalRule(
            treasury_source=TreasurySource.SUB_ACCOUNT_DRIFT,
            amount_bucket="LARGE",
            threshold_amount_usd=Decimal("100000"),
            required_approvers=3,
            approver_pool=_CUTOVER_APPROVER_POOL,
        ),
    ],
    TreasurySource.SUB_ACCOUNT_DYDX: [
        WithdrawalApprovalRule(
            treasury_source=TreasurySource.SUB_ACCOUNT_DYDX,
            amount_bucket="MEDIUM",
            threshold_amount_usd=Decimal("10000"),
            required_approvers=2,
            approver_pool=_CUTOVER_APPROVER_POOL,
        ),
        WithdrawalApprovalRule(
            treasury_source=TreasurySource.SUB_ACCOUNT_DYDX,
            amount_bucket="LARGE",
            threshold_amount_usd=Decimal("100000"),
            required_approvers=3,
            approver_pool=_CUTOVER_APPROVER_POOL,
        ),
    ],
}


def get_approval_rules(source: TreasurySource) -> list[WithdrawalApprovalRule]:
    """Return all approval rules for a given TreasurySource.

    Rules are sorted by threshold_amount_usd ascending (MEDIUM before LARGE).

    Args:
        source: TreasurySource to look up.

    Returns:
        List of WithdrawalApprovalRule sorted by threshold.

    Raises:
        KeyError: If source not in registry (should never happen for valid TreasurySource).
    """
    return _DEFAULT_RULES[source]


def get_required_approvers(source: TreasurySource, amount_usd: Decimal) -> int:
    """Return number of approvals required for a withdrawal of amount_usd from source.

    Applies rules in descending threshold order: if amount exceeds largest threshold,
    return largest required_approvers. If below all thresholds, return 1.

    Args:
        source: TreasurySource of the withdrawal.
        amount_usd: Amount (USD) to withdraw.

    Returns:
        Number of approvals required (>= 1).
    """
    rules = sorted(
        _DEFAULT_RULES[source],
        key=lambda r: r.threshold_amount_usd,
        reverse=True,
    )
    for rule in rules:
        if amount_usd > rule.threshold_amount_usd:
            return rule.required_approvers
    return 1


def get_approver_pool(source: TreasurySource) -> frozenset[str]:
    """Return the approver pool for a given source (union of all tiers)."""
    rules = _DEFAULT_RULES[source]
    return rules[0].approver_pool if rules else frozenset()
