"""Unit tests for WithdrawalApprovalSignature + WithdrawalApprovalChain.

Per ``wallet_treasury_post_cutover_custody_signing_2026_06_01.md`` Phase 1.
8 test cases covering: single-sig HMAC, 2-of-2, M-of-N quorum, HMAC
verification positive/negative, canonical signature_input, chain quorum flag,
and pool rejection for unknown approvers.
"""

from __future__ import annotations

import hashlib
import hmac
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from unified_api_contracts.internal.domain.treasury import (
    TreasurySource,
    WithdrawalApprovalChain,
    WithdrawalApprovalSignature,
)

_SECRET_KEY = b"test-hmac-secret-32-bytes-pad---"
_APPROVER_POOL: frozenset[str] = frozenset(["operator:ikenna", "operator:harsh", "operator:system_admin"])
_WITHDRAWAL_ID = "wdl-2026-05-14-001"
_AMOUNT_USD = Decimal("50000")
_SOURCE = TreasurySource.DEFI_HOT_WALLET


class TestWithdrawalApprovalSignature:
    def test_create_produces_valid_hmac(self) -> None:
        """Single-sig create + verify round-trip."""
        sig = WithdrawalApprovalSignature.create(
            withdrawal_id=_WITHDRAWAL_ID,
            approver_id="operator:ikenna",
            amount_usd=_AMOUNT_USD,
            treasury_source=_SOURCE,
            secret_key=_SECRET_KEY,
        )
        assert sig.verify(_SECRET_KEY) is True

    def test_verify_rejects_tampered_amount(self) -> None:
        """Changing amount_usd after signing invalidates HMAC."""
        sig = WithdrawalApprovalSignature.create(
            withdrawal_id=_WITHDRAWAL_ID,
            approver_id="operator:ikenna",
            amount_usd=_AMOUNT_USD,
            treasury_source=_SOURCE,
            secret_key=_SECRET_KEY,
        )
        # Create a copy with different amount — different signature_input
        tampered = WithdrawalApprovalSignature(
            withdrawal_id=sig.withdrawal_id,
            approver_id=sig.approver_id,
            amount_usd=Decimal("999999"),  # tampered
            treasury_source=sig.treasury_source,
            hmac_signature=sig.hmac_signature,  # original signature — should fail
            signed_at=sig.signed_at,
        )
        assert tampered.verify(_SECRET_KEY) is False

    def test_verify_rejects_wrong_key(self) -> None:
        """HMAC verification fails with incorrect secret key."""
        sig = WithdrawalApprovalSignature.create(
            withdrawal_id=_WITHDRAWAL_ID,
            approver_id="operator:ikenna",
            amount_usd=_AMOUNT_USD,
            treasury_source=_SOURCE,
            secret_key=_SECRET_KEY,
        )
        wrong_key = b"wrong-key-32-bytes-padding------"
        assert sig.verify(wrong_key) is False

    def test_signature_input_canonical_format(self) -> None:
        """signature_input contains all required fields in canonical order."""
        signed_at = datetime(2026, 5, 14, 10, 0, 0, tzinfo=UTC)
        sig = WithdrawalApprovalSignature(
            withdrawal_id="wdl-001",
            approver_id="operator:ikenna",
            amount_usd=Decimal("10000"),
            treasury_source=TreasurySource.COPPER,
            hmac_signature="deadbeef",
            signed_at=signed_at,
        )
        expected = f"wdl-001:operator:ikenna:10000:COPPER:{signed_at.isoformat()}"
        assert sig.signature_input() == expected

    def test_hmac_matches_manual_computation(self) -> None:
        """HMAC matches what the caller computes manually with the same key."""
        sig = WithdrawalApprovalSignature.create(
            withdrawal_id=_WITHDRAWAL_ID,
            approver_id="operator:harsh",
            amount_usd=Decimal("25000"),
            treasury_source=TreasurySource.CEFFU,
            secret_key=_SECRET_KEY,
        )
        manual = hmac.new(
            _SECRET_KEY,
            sig.signature_input().encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        assert sig.hmac_signature == manual


class TestWithdrawalApprovalChain:
    def _new_chain(self, required_approvers: int = 2) -> WithdrawalApprovalChain:
        return WithdrawalApprovalChain.new(
            withdrawal_id=_WITHDRAWAL_ID,
            amount_usd=_AMOUNT_USD,
            treasury_source=_SOURCE,
            required_approvers=required_approvers,
            approver_pool=_APPROVER_POOL,
        )

    def test_two_of_two_quorum_reached(self) -> None:
        """2-of-2: quorum reached after exactly 2 approvals."""
        chain = self._new_chain(required_approvers=2)
        sig1 = WithdrawalApprovalSignature.create(
            withdrawal_id=_WITHDRAWAL_ID,
            approver_id="operator:ikenna",
            amount_usd=_AMOUNT_USD,
            treasury_source=_SOURCE,
            secret_key=_SECRET_KEY,
        )
        sig2 = WithdrawalApprovalSignature.create(
            withdrawal_id=_WITHDRAWAL_ID,
            approver_id="operator:harsh",
            amount_usd=_AMOUNT_USD,
            treasury_source=_SOURCE,
            secret_key=_SECRET_KEY,
        )
        chain.add_approval(sig1)
        assert chain.quorum_reached is False
        assert chain.approvers_remaining == 1
        chain.add_approval(sig2)
        assert chain.quorum_reached is True
        assert chain.quorum_reached_at is not None
        assert chain.approver_count == 2

    def test_three_of_three_quorum_reached(self) -> None:
        """M-of-N (3-of-3): quorum reached after 3 approvals."""
        chain = self._new_chain(required_approvers=3)
        approvers = ["operator:ikenna", "operator:harsh", "operator:system_admin"]
        for approver_id in approvers:
            sig = WithdrawalApprovalSignature.create(
                withdrawal_id=_WITHDRAWAL_ID,
                approver_id=approver_id,
                amount_usd=_AMOUNT_USD,
                treasury_source=_SOURCE,
                secret_key=_SECRET_KEY,
            )
            chain.add_approval(sig)
        assert chain.quorum_reached is True
        assert chain.approver_count == 3

    def test_add_approval_rejects_unknown_approver(self) -> None:
        """Adding approval from non-pool operator raises ValueError."""
        chain = self._new_chain()
        sig = WithdrawalApprovalSignature.create(
            withdrawal_id=_WITHDRAWAL_ID,
            approver_id="operator:unknown",  # not in pool
            amount_usd=_AMOUNT_USD,
            treasury_source=_SOURCE,
            secret_key=_SECRET_KEY,
        )
        with pytest.raises(ValueError, match="not in pool"):
            chain.add_approval(sig)

    def test_add_approval_rejects_duplicate_approver(self) -> None:
        """Same approver cannot sign twice for the same withdrawal."""
        chain = self._new_chain()
        sig1 = WithdrawalApprovalSignature.create(
            withdrawal_id=_WITHDRAWAL_ID,
            approver_id="operator:ikenna",
            amount_usd=_AMOUNT_USD,
            treasury_source=_SOURCE,
            secret_key=_SECRET_KEY,
        )
        chain.add_approval(sig1)
        sig2 = WithdrawalApprovalSignature.create(
            withdrawal_id=_WITHDRAWAL_ID,
            approver_id="operator:ikenna",  # same approver
            amount_usd=_AMOUNT_USD,
            treasury_source=_SOURCE,
            secret_key=_SECRET_KEY,
        )
        with pytest.raises(ValueError, match="already approved"):
            chain.add_approval(sig2)
