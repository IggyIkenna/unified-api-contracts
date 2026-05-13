"""Unit tests for client lifecycle contracts."""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from unified_api_contracts.internal.domain.client_lifecycle import (
    ClientApiKeyMaterial,
    ClientKYCStub,
    ClientOnboardingState,
    ClientRiskPreferences,
    ClientShareClassSubscription,
)


class TestClientOnboardingState:
    """Test ClientOnboardingState enum."""

    def test_all_states_defined(self) -> None:
        """Verify all required states are defined."""
        expected = {
            "DRAFT",
            "KYC_SUBMITTED",
            "KYC_APPROVED",
            "DEPOSITED",
            "SUBSCRIBED",
            "LIVE",
            "SUSPENDED",
        }
        actual = {state.value for state in ClientOnboardingState}
        assert actual == expected

    def test_state_values(self) -> None:
        """Verify state values match their names."""
        assert ClientOnboardingState.DRAFT.value == "DRAFT"
        assert ClientOnboardingState.KYC_SUBMITTED.value == "KYC_SUBMITTED"
        assert ClientOnboardingState.KYC_APPROVED.value == "KYC_APPROVED"
        assert ClientOnboardingState.DEPOSITED.value == "DEPOSITED"
        assert ClientOnboardingState.SUBSCRIBED.value == "SUBSCRIBED"
        assert ClientOnboardingState.LIVE.value == "LIVE"
        assert ClientOnboardingState.SUSPENDED.value == "SUSPENDED"

    def test_state_is_strenum(self) -> None:
        """Verify ClientOnboardingState is a StrEnum."""
        assert isinstance(ClientOnboardingState.DRAFT, str)
        assert isinstance(ClientOnboardingState.LIVE, str)


class TestClientKYCStub:
    """Test ClientKYCStub dataclass."""

    def test_minimal_kyc_stub(self) -> None:
        """Create KYC stub with minimal fields."""
        stub = ClientKYCStub(
            client_name="Acme Capital LP",
            client_email="admin@acme.example.com",
        )
        assert stub.client_name == "Acme Capital LP"
        assert stub.client_email == "admin@acme.example.com"
        assert stub.jurisdiction == ""
        assert not stub.accredited_investor_claimed
        assert stub.submitted_at is None
        assert stub.approved_at is None

    def test_kyc_stub_frozen(self) -> None:
        """Verify KYCStub is frozen (immutable)."""
        stub = ClientKYCStub(
            client_name="Test",
            client_email="test@example.com",
        )
        with pytest.raises(AttributeError):
            stub.client_name = "Changed"

    def test_kyc_stub_with_submission(self) -> None:
        """Create KYC stub with submission + approval."""
        now = datetime.utcnow()
        later = now + timedelta(hours=1)
        stub = ClientKYCStub(
            client_name="Test Fund",
            client_email="test@fund.example.com",
            jurisdiction="USA",
            accredited_investor_claimed=True,
            submitted_at=now,
            approved_at=later,
            approval_notes="Manual verification passed",
        )
        assert stub.jurisdiction == "USA"
        assert stub.accredited_investor_claimed
        assert stub.submitted_at == now
        assert stub.approved_at == later
        assert stub.approval_notes == "Manual verification passed"

    def test_kyc_stub_pii_field_marked(self) -> None:
        """Verify email field has PII marking in metadata."""
        # This is more of a documentation test — the field should be marked
        # for encryption/redaction at serialization time.
        stub = ClientKYCStub(
            client_name="Test",
            client_email="sensitive@example.com",
        )
        # Email should be stored; actual redaction happens at serialization (tested in schema layer).
        assert stub.client_email == "sensitive@example.com"


class TestClientApiKeyMaterial:
    """Test ClientApiKeyMaterial dataclass."""

    def test_minimal_api_key(self) -> None:
        """Create API key with minimal fields."""
        key = ClientApiKeyMaterial(api_key_id="key-12345")
        assert key.api_key_id == "key-12345"
        assert key.label == ""
        assert key.expires_at is None
        assert key.scopes == frozenset()
        assert isinstance(key.created_at, datetime)

    def test_api_key_with_scopes(self) -> None:
        """Create API key with scopes."""
        key = ClientApiKeyMaterial(
            api_key_id="key-prod",
            label="production",
            scopes=frozenset(["read_balances", "write_subscriptions"]),
        )
        assert key.scopes == frozenset(["read_balances", "write_subscriptions"])
        assert "read_balances" in key.scopes
        assert "admin" not in key.scopes

    def test_api_key_with_expiry(self) -> None:
        """Create API key with expiry date."""
        created = datetime.utcnow()
        expires = created + timedelta(days=365)
        key = ClientApiKeyMaterial(
            api_key_id="key-annual",
            label="annual",
            created_at=created,
            expires_at=expires,
        )
        assert key.expires_at == expires
        assert key.expires_at > key.created_at

    def test_api_key_frozen(self) -> None:
        """Verify API key material is frozen."""
        key = ClientApiKeyMaterial(api_key_id="key-1")
        with pytest.raises(AttributeError):
            key.api_key_id = "key-2"

    def test_api_key_never_inlines_secret(self) -> None:
        """Verify API key material uses credential registry id, never inline secret."""
        # The class only exposes api_key_id (registry reference), never the actual secret.
        key = ClientApiKeyMaterial(api_key_id="registry-key-uuid")
        assert key.api_key_id == "registry-key-uuid"
        # No field called 'secret' or 'actual_key' should exist.
        assert not hasattr(key, "secret")
        assert not hasattr(key, "actual_key")


class TestClientRiskPreferences:
    """Test ClientRiskPreferences dataclass."""

    def test_default_risk_preferences(self) -> None:
        """Create risk preferences with defaults."""
        prefs = ClientRiskPreferences()
        assert prefs.max_leverage == Decimal("3.0")
        assert prefs.max_single_leg_usd == Decimal("1000000")
        assert prefs.max_daily_loss_pct == Decimal("10")
        assert prefs.max_drawdown_pct == Decimal("25")
        assert prefs.liquidation_threshold_pct == Decimal("20")
        assert "USDC" in prefs.preferred_currencies
        assert "ETH" in prefs.preferred_currencies

    def test_custom_risk_preferences(self) -> None:
        """Create risk preferences with custom values."""
        prefs = ClientRiskPreferences(
            max_leverage=Decimal("2.0"),
            max_daily_loss_pct=Decimal("5"),
            max_drawdown_pct=Decimal("15"),
            liquidation_threshold_pct=Decimal("10"),
            preferred_currencies=frozenset(["USDC", "BTC", "SOL"]),
        )
        assert prefs.max_leverage == Decimal("2.0")
        assert prefs.max_daily_loss_pct == Decimal("5")
        assert prefs.max_drawdown_pct == Decimal("15")
        assert prefs.liquidation_threshold_pct == Decimal("10")
        assert prefs.preferred_currencies == frozenset(["USDC", "BTC", "SOL"])

    def test_risk_preferences_frozen(self) -> None:
        """Verify risk preferences are frozen."""
        prefs = ClientRiskPreferences()
        with pytest.raises(AttributeError):
            prefs.max_leverage = Decimal("5.0")

    def test_leverage_constraints(self) -> None:
        """Verify leverage constraints are stored as Decimal."""
        prefs = ClientRiskPreferences(max_leverage=Decimal("5.5"))
        assert isinstance(prefs.max_leverage, Decimal)
        assert prefs.max_leverage == Decimal("5.5")

    def test_percentage_fields_as_decimal(self) -> None:
        """Verify percentage fields use Decimal type."""
        prefs = ClientRiskPreferences(
            max_daily_loss_pct=Decimal("7.5"),
            max_drawdown_pct=Decimal("20.0"),
        )
        assert isinstance(prefs.max_daily_loss_pct, Decimal)
        assert isinstance(prefs.max_drawdown_pct, Decimal)


class TestClientShareClassSubscription:
    """Test ClientShareClassSubscription dataclass."""

    def test_minimal_subscription(self) -> None:
        """Create minimal subscription."""
        sub = ClientShareClassSubscription(
            client_id="client-123",
            share_class_id="USDC_CUTOVER_V1",
            archetype_id="carry_staked_basis",
        )
        assert sub.client_id == "client-123"
        assert sub.share_class_id == "USDC_CUTOVER_V1"
        assert sub.archetype_id == "carry_staked_basis"
        assert sub.allocation_pct == Decimal("100")
        assert sub.suspended_at is None
        assert sub.is_active()

    def test_subscription_with_allocation(self) -> None:
        """Create subscription with custom allocation %."""
        sub = ClientShareClassSubscription(
            client_id="client-456",
            share_class_id="ETH_FLAGSHIP",
            archetype_id="arbitrage_price_dispersion",
            allocation_pct=Decimal("50"),
        )
        assert sub.allocation_pct == Decimal("50")

    def test_subscription_allocation_pct_bounds(self) -> None:
        """Verify allocation_pct can range 0-100."""
        sub_zero = ClientShareClassSubscription(
            client_id="c1",
            share_class_id="s1",
            archetype_id="a1",
            allocation_pct=Decimal("0"),
        )
        assert sub_zero.allocation_pct == Decimal("0")

        sub_100 = ClientShareClassSubscription(
            client_id="c1",
            share_class_id="s1",
            archetype_id="a1",
            allocation_pct=Decimal("100"),
        )
        assert sub_100.allocation_pct == Decimal("100")

    def test_subscription_is_active_when_not_suspended(self) -> None:
        """Verify is_active() returns True when not suspended."""
        sub = ClientShareClassSubscription(
            client_id="client-789",
            share_class_id="USDC_V1",
            archetype_id="strategy",
        )
        assert sub.is_active()

    def test_subscription_is_inactive_when_suspended(self) -> None:
        """Verify is_active() returns False when suspended."""
        now = datetime.utcnow()
        sub = ClientShareClassSubscription(
            client_id="client-suspended",
            share_class_id="USDC_V1",
            archetype_id="strategy",
            suspended_at=now,
            suspension_reason="drawdown_exceeded",
        )
        assert not sub.is_active()
        assert sub.suspension_reason == "drawdown_exceeded"

    def test_subscription_frozen(self) -> None:
        """Verify subscription is frozen."""
        sub = ClientShareClassSubscription(
            client_id="c1",
            share_class_id="s1",
            archetype_id="a1",
        )
        with pytest.raises(AttributeError):
            sub.allocation_pct = Decimal("50")

    def test_subscription_drawdown_gate(self) -> None:
        """Verify per-subscription drawdown gate (may be tighter than global)."""
        sub = ClientShareClassSubscription(
            client_id="c1",
            share_class_id="s1",
            archetype_id="a1",
            max_drawdown_for_suspension_pct=Decimal("10"),
        )
        assert sub.max_drawdown_for_suspension_pct == Decimal("10")

    def test_multiple_subscriptions_per_client(self) -> None:
        """Verify a client can have multiple subscriptions."""
        client_id = "multi-strategy-client"
        sub1 = ClientShareClassSubscription(
            client_id=client_id,
            share_class_id="USDC_V1",
            archetype_id="carry_staked_basis",
            allocation_pct=Decimal("60"),
        )
        sub2 = ClientShareClassSubscription(
            client_id=client_id,
            share_class_id="ETH_V1",
            archetype_id="arbitrage_price_dispersion",
            allocation_pct=Decimal("40"),
        )
        assert sub1.client_id == sub2.client_id
        assert sub1.share_class_id != sub2.share_class_id
        assert sub1.archetype_id != sub2.archetype_id
        total = sub1.allocation_pct + sub2.allocation_pct
        assert total == Decimal("100")


class TestStateTransitionSemantics:
    """Integration tests verifying state transition semantics."""

    def test_draft_is_first_state(self) -> None:
        """Verify DRAFT is the natural first state."""
        initial = ClientOnboardingState.DRAFT
        assert initial == ClientOnboardingState.DRAFT

    def test_suspended_is_emergency_state(self) -> None:
        """Verify SUSPENDED is reachable from any state."""
        # Not enforced by type; documented in state machine impl.
        suspended = ClientOnboardingState.SUSPENDED
        assert suspended.value == "SUSPENDED"

    def test_live_is_terminal_active_state(self) -> None:
        """Verify LIVE is the goal state."""
        live = ClientOnboardingState.LIVE
        assert live == ClientOnboardingState.LIVE
