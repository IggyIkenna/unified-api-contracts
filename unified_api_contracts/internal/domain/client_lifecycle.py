"""Client lifecycle contracts: onboarding states, KYC, API keys, preferences, share-class subscriptions.

Cutover scope: demo client single-fund single-share-class. Post-cutover multi-fund, multi-share-class,
production KYC integration deferred.

Per ``wallet_treasury_client_flow_2026_05_10.md`` Phase 1.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum


class ClientOnboardingState(StrEnum):
    """Closed-set client lifecycle state.

    Transitions enforce: DRAFT → KYC_SUBMITTED → KYC_APPROVED → DEPOSITED → SUBSCRIBED → LIVE.
    Suspended = admin intervention. State machine enforced by
    :class:`unified_trading_library.client_lifecycle.onboarding.ClientOnboardingStateMachine`.
    """

    DRAFT = "DRAFT"
    """Onboarding initiated; pre-KYC submission."""

    KYC_SUBMITTED = "KYC_SUBMITTED"
    """KYC stub submitted; awaiting approval."""

    KYC_APPROVED = "KYC_APPROVED"
    """KYC approved; treasury wired."""

    DEPOSITED = "DEPOSITED"
    """Initial deposit confirmed."""

    SUBSCRIBED = "SUBSCRIBED"
    """Subscribed to ≥1 share class + archetype."""

    LIVE = "LIVE"
    """Ready for strategy orders."""

    SUSPENDED = "SUSPENDED"
    """Admin-suspended pending resolution."""


@dataclass(frozen=True)
class ClientKYCStub:
    """Stub KYC for cutover MVP.

    Post-cutover production KYC integrates with named provider (e.g., Midata, Trulioo).
    Cutover uses manual approval only.

    Fields marked with json_schema_extra pii=True are encrypted at rest + redacted from
    audit logs unless explicitly approved.
    """

    client_name: str
    """Client legal name (e.g., 'Acme Capital LP')."""

    client_email: str = field(metadata={"json_schema_extra": {"pii": True}})
    """Client contact email."""

    jurisdiction: str = ""
    """ISO 3166-1 alpha-3 country code (e.g., 'USA', 'GBR'). Empty if not yet provided."""

    accredited_investor_claimed: bool = False
    """Self-certification of accredited investor status (US)."""

    submitted_at: datetime | None = None
    """UTC timestamp of KYC submission. None if not yet submitted."""

    approved_at: datetime | None = None
    """UTC timestamp of KYC approval. None if not yet approved."""

    approval_notes: str = ""
    """Admin notes on approval (may contain PII)."""


@dataclass(frozen=True)
class ClientApiKeyMaterial:
    """API key + secret reference for client programmatic access.

    Keys are NEVER inlined — always referenced by credential-registry id.
    Actual secrets live in Secret Manager; this class carries the registry id only.

    Per ``interface-credential-convention.md`` § Credential Reference Pattern.
    """

    api_key_id: str
    """Credential-registry id for this key (not the key itself)."""

    label: str = ""
    """Human-readable label (e.g., 'production', 'staging')."""

    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    """Creation timestamp."""

    expires_at: datetime | None = None
    """Expiry timestamp. None = no expiration."""

    scopes: frozenset[str] = field(default_factory=frozenset)
    """Allowed API scopes (e.g., 'read_balances', 'write_subscriptions')."""


@dataclass(frozen=True)
class ClientRiskPreferences:
    """Per-client risk profile + constraints.

    Drives per-archetype position limits + leverage caps via
    ``strategy-service/risk`` integration. Per ``risk_simulations_limits_alerting_2026_05_10.md``
    Phase 2.
    """

    max_leverage: Decimal = Decimal("3.0")
    """Max notional leverage across all archetypes (e.g., 3.0x = 3x capital)."""

    max_single_leg_usd: Decimal = Decimal("1000000")
    """Max USD per single trade leg."""

    max_daily_loss_pct: Decimal = Decimal("10")
    """Max daily loss as % of starting NAV."""

    max_drawdown_pct: Decimal = Decimal("25")
    """Max peak-to-trough drawdown as % of NAV."""

    liquidation_threshold_pct: Decimal = Decimal("20")
    """If NAV falls below this % of starting capital, liquidate all positions."""

    preferred_currencies: frozenset[str] = field(default_factory=lambda: frozenset(["USDC", "ETH"]))
    """Preferred quote currencies (e.g., USDC for USD, ETH for denom)."""


@dataclass(frozen=True)
class ClientShareClassSubscription:
    """Per-client subscription to a share class + archetype pair.

    Multiple subscriptions per client support multi-strategy allocation.
    Cutover demo: single subscription (100% of one archetype).

    Per ``wallet_treasury_client_flow_2026_05_10.md`` Phase 2 allocation engine + Phase 4 HWM ledger.
    """

    client_id: str
    """Client identifier (UUID or human-readable)."""

    share_class_id: str
    """Share class (e.g., 'USDC_CUTOVER_V1', 'ETH_FLAGSHIP')."""

    archetype_id: str
    """Strategy archetype (e.g., 'carry_staked_basis', 'arbitrage_price_dispersion')."""

    allocation_pct: Decimal = Decimal("100")
    """Allocation % of client's capital to this archetype (0-100)."""

    max_drawdown_for_suspension_pct: Decimal = Decimal("15")
    """Archetype-specific drawdown gate (may tighten the global setting)."""

    subscribed_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    """Subscription timestamp."""

    suspended_at: datetime | None = None
    """Suspension timestamp if suspended by risk gate. None = active."""

    suspension_reason: str = ""
    """If suspended, the reason (e.g., 'drawdown_exceeded', 'client_request')."""

    def is_active(self) -> bool:
        """Returns True if subscription is currently active."""
        return self.suspended_at is None
