"""Schema-validation tests for the per-wallet provisioning envelope.

Covers :class:`SigningSurface` / :class:`WalletKind` / :class:`SpendingCaps` /
:class:`WalletProvisioningConfig` per ``api_keys_wallets_accounts_readiness_2026_05_10.md``
Phase 3 (wallet provisioning schema) + cross-tab handshake to slot 5
(``defi_recursive_borrow_archetypes``) + slot 8 (``cross_cutting`` DART surfaces).
"""

from __future__ import annotations

import dataclasses
import json
import re
from decimal import Decimal

import pytest

from unified_api_contracts.internal.domain.defi import (
    CANONICAL_WALLET_PROVISIONING_VERSION,
    SigningSurface,
    SpendingCaps,
    WalletKind,
    WalletProvisioningConfig,
    WalletProvisioningError,
)

# ---------------------------------------------------------------------------
# SigningSurface — closed-set enum membership
# ---------------------------------------------------------------------------


def test_signing_surface_has_exactly_five_values() -> None:
    """The closed-set HSM tier vocabulary is exactly 5 values per R9 + R9-Cloud-KMS.

    Adding a sixth value MUST update ``custody-providers.md`` § 1 factory
    routing + ``wallet-hierarchy-and-capital-flow.md`` § Configuration Schema.
    """
    assert set(SigningSurface) == {
        SigningSurface.LOCAL_KEY,
        SigningSurface.CLOUD_KMS_ENCRYPTED,
        SigningSurface.COPPER_MPC,
        SigningSurface.FIREBLOCKS_MPC,
        SigningSurface.MOCK,
    }


def test_signing_surface_values_are_uppercase_strings() -> None:
    """StrEnum values match key names for stable serialization across services."""
    for surface in SigningSurface:
        assert surface.value == surface.name


# ---------------------------------------------------------------------------
# WalletKind — closed-set role classifier
# ---------------------------------------------------------------------------


def test_wallet_kind_has_exactly_four_values() -> None:
    """TREASURY + HOT_TRADING + GAS_RESERVE + FLASH_LOAN_RECEIVER."""
    assert set(WalletKind) == {
        WalletKind.TREASURY,
        WalletKind.HOT_TRADING,
        WalletKind.GAS_RESERVE,
        WalletKind.FLASH_LOAN_RECEIVER,
    }


# ---------------------------------------------------------------------------
# SpendingCaps — risk-envelope dataclass behaviour
# ---------------------------------------------------------------------------


def test_spending_caps_default_unbounded() -> None:
    """No caps set = no limit (caller's responsibility to populate)."""
    caps = SpendingCaps()
    assert caps.per_tx_usd is None
    assert caps.per_hour_usd is None
    assert caps.per_day_usd is None
    assert caps.per_protocol_usd == {}
    assert caps.is_within_per_tx(Decimal("1_000_000")) is True


def test_spending_caps_per_tx_enforced() -> None:
    caps = SpendingCaps(per_tx_usd=Decimal("50000"))
    assert caps.is_within_per_tx(Decimal("49999")) is True
    assert caps.is_within_per_tx(Decimal("50000")) is True
    assert caps.is_within_per_tx(Decimal("50001")) is False


def test_spending_caps_per_protocol_lookup() -> None:
    caps = SpendingCaps(
        per_protocol_usd={"AAVE_V3": Decimal("25000"), "UNISWAP_V3": Decimal("10000")},
    )
    assert caps.per_protocol_limit("AAVE_V3") == Decimal("25000")
    assert caps.per_protocol_limit("UNISWAP_V3") == Decimal("10000")
    assert caps.per_protocol_limit("MORPHO") is None  # not in map → fall through to per_tx/per_hour/per_day


# R-18 — effective_cap proportional tests


def test_effective_cap_proportional_tighter_than_absolute() -> None:
    """5% of $50k balance = $2.5k tighter than $100k absolute cap."""
    caps = SpendingCaps(
        per_day_usd=Decimal("100000"),
        per_day_pct_of_balance=Decimal("0.05"),
    )
    assert caps.effective_cap("per_day", Decimal("50000")) == Decimal("2500")


def test_effective_cap_absolute_tighter_than_proportional() -> None:
    """$10k absolute tighter than 50% of $50k = $25k proportional."""
    caps = SpendingCaps(
        per_tx_usd=Decimal("10000"),
        per_tx_pct_of_balance=Decimal("0.50"),
    )
    assert caps.effective_cap("per_tx", Decimal("50000")) == Decimal("10000")


def test_effective_cap_only_absolute_set() -> None:
    """Only absolute cap → returns absolute (no proportional)."""
    caps = SpendingCaps(per_hour_usd=Decimal("20000"))
    assert caps.effective_cap("per_hour", Decimal("1000000")) == Decimal("20000")


def test_effective_cap_only_proportional_set() -> None:
    """Only proportional cap → returns pct × balance."""
    caps = SpendingCaps(per_tx_pct_of_balance=Decimal("0.02"))
    assert caps.effective_cap("per_tx", Decimal("300000")) == Decimal("6000")


def test_effective_cap_neither_set_returns_none() -> None:
    """No cap configured for period → None (uncapped)."""
    caps = SpendingCaps()
    assert caps.effective_cap("per_day", Decimal("100000")) is None


def test_effective_cap_unknown_period_returns_none() -> None:
    """Unknown period string → None (safe default)."""
    caps = SpendingCaps(per_tx_usd=Decimal("5000"))
    assert caps.effective_cap("per_week", Decimal("50000")) is None


# ---------------------------------------------------------------------------
# WalletProvisioningConfig — validation rules
# ---------------------------------------------------------------------------


def _valid_kms_wallet() -> WalletProvisioningConfig:
    """Reusable May-23 cutover wallet shape: CLOUD_KMS_ENCRYPTED HOT_TRADING."""
    return WalletProvisioningConfig(
        wallet_id="trading-aave-eth-may23",
        chain="ETHEREUM",
        kind=WalletKind.HOT_TRADING,
        signing_surface=SigningSurface.CLOUD_KMS_ENCRYPTED,
        kms_key_uri=(
            "projects/test-project/locations/asia-northeast1/keyRings/wallets-prod/cryptoKeys/trading-aave-eth-v1"
        ),
        allowed_protocols=frozenset({"AAVE_V3", "UNISWAP_V3"}),
        spending_caps=SpendingCaps(
            per_tx_usd=Decimal("50000"),
            per_hour_usd=Decimal("250000"),
            per_day_usd=Decimal("1000000"),
            per_protocol_usd={"AAVE_V3": Decimal("500000")},
        ),
        kill_switch_id="KILL_PER_ARCHETYPE_CARRY_STAKED_BASIS",
        archetype_id="carry_staked_basis",
    )


def test_valid_kms_wallet_passes_validation() -> None:
    """The May-23 cutover default shape validates cleanly."""
    _valid_kms_wallet().validate()


def test_local_key_requires_secret_ref() -> None:
    """LOCAL_KEY surface MUST declare private_key_secret_ref."""
    cfg = WalletProvisioningConfig(
        wallet_id="dev-test-wallet",
        chain="SEPOLIA",
        kind=WalletKind.HOT_TRADING,
        signing_surface=SigningSurface.LOCAL_KEY,
        archetype_id="dev_test",
    )
    with pytest.raises(WalletProvisioningError, match="LOCAL_KEY requires private_key_secret_ref"):
        cfg.validate()


def test_cloud_kms_requires_key_uri() -> None:
    """CLOUD_KMS_ENCRYPTED surface MUST declare kms_key_uri."""
    cfg = WalletProvisioningConfig(
        wallet_id="trading-no-kms",
        chain="ETHEREUM",
        kind=WalletKind.HOT_TRADING,
        signing_surface=SigningSurface.CLOUD_KMS_ENCRYPTED,
        archetype_id="carry_staked_basis",
    )
    with pytest.raises(WalletProvisioningError, match="CLOUD_KMS_ENCRYPTED requires kms_key_uri"):
        cfg.validate()


def test_copper_mpc_requires_custodian_wallet_id() -> None:
    """COPPER_MPC surface MUST declare custodian_wallet_id (Copper portfolioId)."""
    cfg = WalletProvisioningConfig(
        wallet_id="trading-copper-eth",
        chain="ETHEREUM",
        kind=WalletKind.HOT_TRADING,
        signing_surface=SigningSurface.COPPER_MPC,
        archetype_id="carry_staked_basis",
    )
    with pytest.raises(WalletProvisioningError, match="COPPER_MPC.*requires custodian_wallet_id"):
        cfg.validate()


def test_fireblocks_mpc_requires_custodian_wallet_id() -> None:
    """FIREBLOCKS_MPC surface MUST declare custodian_wallet_id (Fireblocks vaultAccountId)."""
    cfg = WalletProvisioningConfig(
        wallet_id="trading-fireblocks-eth",
        chain="ETHEREUM",
        kind=WalletKind.HOT_TRADING,
        signing_surface=SigningSurface.FIREBLOCKS_MPC,
        archetype_id="carry_staked_basis",
    )
    with pytest.raises(WalletProvisioningError, match="FIREBLOCKS_MPC.*requires custodian_wallet_id"):
        cfg.validate()


def test_hot_trading_requires_archetype_id() -> None:
    """HOT_TRADING wallets MUST bind to an archetype for per-strategy attribution."""
    cfg = WalletProvisioningConfig(
        wallet_id="trading-orphan",
        chain="ETHEREUM",
        kind=WalletKind.HOT_TRADING,
        signing_surface=SigningSurface.CLOUD_KMS_ENCRYPTED,
        kms_key_uri="projects/p/locations/l/keyRings/r/cryptoKeys/k",
    )
    with pytest.raises(WalletProvisioningError, match="kind=HOT_TRADING requires archetype_id"):
        cfg.validate()


def test_hot_trading_rejects_withdraw_destinations() -> None:
    """HOT_TRADING wallets MUST NOT have allowed_destinations — only TREASURY may withdraw."""
    cfg = WalletProvisioningConfig(
        wallet_id="trading-hot-with-whitelist",
        chain="ETHEREUM",
        kind=WalletKind.HOT_TRADING,
        signing_surface=SigningSurface.CLOUD_KMS_ENCRYPTED,
        kms_key_uri="projects/p/locations/l/keyRings/r/cryptoKeys/k",
        archetype_id="carry_staked_basis",
        allowed_destinations=frozenset({"0xabc123"}),
    )
    with pytest.raises(WalletProvisioningError, match="kind=HOT_TRADING.*empty allowed_destinations"):
        cfg.validate()


def test_gas_reserve_rejects_withdraw_destinations() -> None:
    """GAS_RESERVE wallets MUST NOT have allowed_destinations either."""
    cfg = WalletProvisioningConfig(
        wallet_id="gas-reserve-eth",
        chain="ETHEREUM",
        kind=WalletKind.GAS_RESERVE,
        signing_surface=SigningSurface.CLOUD_KMS_ENCRYPTED,
        kms_key_uri="projects/p/locations/l/keyRings/r/cryptoKeys/k",
        allowed_destinations=frozenset({"0xabc"}),
    )
    with pytest.raises(WalletProvisioningError, match="kind=GAS_RESERVE.*empty allowed_destinations"):
        cfg.validate()


def test_treasury_permits_withdraw_destinations() -> None:
    """TREASURY wallets DO allow allowed_destinations (client-deposit-source whitelist)."""
    cfg = WalletProvisioningConfig(
        wallet_id="treasury-usdc",
        chain="ETHEREUM",
        kind=WalletKind.TREASURY,
        signing_surface=SigningSurface.CLOUD_KMS_ENCRYPTED,
        kms_key_uri="projects/p/locations/l/keyRings/r/cryptoKeys/k",
        allowed_destinations=frozenset({"0xClientDepositAddr"}),
    )
    cfg.validate()  # no raise


def test_kill_switch_id_must_use_known_prefix() -> None:
    """kill_switch_id must match one of the KillSwitchId enum prefixes."""
    cfg = WalletProvisioningConfig(
        wallet_id="trading-bad-killswitch",
        chain="ETHEREUM",
        kind=WalletKind.HOT_TRADING,
        signing_surface=SigningSurface.CLOUD_KMS_ENCRYPTED,
        kms_key_uri="projects/p/locations/l/keyRings/r/cryptoKeys/k",
        archetype_id="carry_staked_basis",
        kill_switch_id="ARBITRARY_BUTTON",
    )
    with pytest.raises(WalletProvisioningError, match="kill_switch_id.*must start with"):
        cfg.validate()


@pytest.mark.parametrize(
    "kill_switch_id",
    [
        "KILL_ALL_LIVE",
        "KILL_PER_ARCHETYPE_CARRY_STAKED_BASIS",
        "KILL_PER_VENUE_BYBIT",
        "KILL_PER_ASSET_GROUP_DEFI",
        "KILL_PER_WALLET",  # added 2026-05-12 per Phase 5 wallet-tier kill-switch
    ],
)
def test_kill_switch_id_accepts_known_prefixes(kill_switch_id: str) -> None:
    """All five KillSwitchId prefix families are accepted."""
    cfg = WalletProvisioningConfig(
        wallet_id="trading-killswitch-ok",
        chain="ETHEREUM",
        kind=WalletKind.HOT_TRADING,
        signing_surface=SigningSurface.CLOUD_KMS_ENCRYPTED,
        kms_key_uri="projects/p/locations/l/keyRings/r/cryptoKeys/k",
        archetype_id="carry_staked_basis",
        kill_switch_id=kill_switch_id,
    )
    cfg.validate()  # no raise


def test_mock_signing_surface_needs_no_credentials() -> None:
    """MOCK surface has no credential requirement (test-only)."""
    cfg = WalletProvisioningConfig(
        wallet_id="mock-wallet",
        chain="ETHEREUM",
        kind=WalletKind.HOT_TRADING,
        signing_surface=SigningSurface.MOCK,
        archetype_id="test_strategy",
    )
    cfg.validate()  # no raise


# ---------------------------------------------------------------------------
# Allowlist behavior
# ---------------------------------------------------------------------------


def test_permits_protocol_closed_set() -> None:
    cfg = _valid_kms_wallet()
    assert cfg.permits_protocol("AAVE_V3") is True
    assert cfg.permits_protocol("UNISWAP_V3") is True
    assert cfg.permits_protocol("MORPHO") is False  # not allowlisted


def test_permits_destination_evm_case_insensitive() -> None:
    """EVM addresses are case-insensitive — checksum vs lowercase MUST match."""
    cfg = WalletProvisioningConfig(
        wallet_id="treasury-eth",
        chain="ETHEREUM",
        kind=WalletKind.TREASURY,
        signing_surface=SigningSurface.CLOUD_KMS_ENCRYPTED,
        kms_key_uri="projects/p/locations/l/keyRings/r/cryptoKeys/k",
        allowed_destinations=frozenset({"0xAbC123DeF456"}),
    )
    assert cfg.permits_destination("0xabc123def456") is True
    assert cfg.permits_destination("0XABC123DEF456") is True
    assert cfg.permits_destination("0xAbC123DeF456") is True
    assert cfg.permits_destination("0xOther") is False


def test_permits_destination_solana_case_sensitive() -> None:
    """Solana base58 addresses are case-sensitive."""
    cfg = WalletProvisioningConfig(
        wallet_id="treasury-sol",
        chain="SOLANA",
        kind=WalletKind.TREASURY,
        signing_surface=SigningSurface.CLOUD_KMS_ENCRYPTED,
        kms_key_uri="projects/p/locations/l/keyRings/r/cryptoKeys/k",
        allowed_destinations=frozenset({"7EcDhMpXg8mNqVrTzbAvWyKjPL3RfSdHnZmQwBxC"}),
    )
    assert cfg.permits_destination("7EcDhMpXg8mNqVrTzbAvWyKjPL3RfSdHnZmQwBxC") is True
    assert cfg.permits_destination("7ecdhmpxg8mnqvrtzbavwykjpl3rfsdhnzmqwbxc") is False


def test_permits_destination_empty_allowlist_rejects_all() -> None:
    """Default empty allowlist = no destinations permitted (safe default)."""
    cfg = WalletProvisioningConfig(
        wallet_id="treasury-locked",
        chain="ETHEREUM",
        kind=WalletKind.TREASURY,
        signing_surface=SigningSurface.CLOUD_KMS_ENCRYPTED,
        kms_key_uri="projects/p/locations/l/keyRings/r/cryptoKeys/k",
    )
    assert cfg.permits_destination("0xanyone") is False


# ---------------------------------------------------------------------------
# Frozen / hashable
# ---------------------------------------------------------------------------


def test_wallet_provisioning_config_is_frozen() -> None:
    """The config dataclass is frozen — runtime mutation blocked for safety."""
    cfg = _valid_kms_wallet()
    with pytest.raises((AttributeError, Exception)):  # FrozenInstanceError subclasses AttributeError
        cfg.wallet_id = "other"  # type: ignore[misc]


def test_spending_caps_is_frozen() -> None:
    caps = SpendingCaps(per_tx_usd=Decimal("100"))
    with pytest.raises((AttributeError, Exception)):
        caps.per_tx_usd = Decimal("200")  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Round-trip serialization + schema versioning
# ---------------------------------------------------------------------------


def test_schema_version_constant_exists_and_is_semver() -> None:
    """CANONICAL_WALLET_PROVISIONING_VERSION must exist and follow X.Y.Z format."""
    assert re.match(r"^\d+\.\d+\.\d+$", CANONICAL_WALLET_PROVISIONING_VERSION) is not None


def test_signing_surface_all_values_round_trip_via_string() -> None:
    """Each SigningSurface value serialises to a string and deserialises back to the same enum member."""
    for surface in SigningSurface:
        serialised = surface.value
        assert isinstance(serialised, str)
        assert SigningSurface(serialised) == surface


def test_signing_surface_value_is_json_native() -> None:
    """SigningSurface.value is a plain str — JSON-serialisable without a custom encoder."""
    for surface in SigningSurface:
        encoded = json.dumps(surface.value)
        decoded = json.loads(encoded)
        assert SigningSurface(decoded) == surface


def test_wallet_provisioning_config_field_reconstruction() -> None:
    """Fields extracted from a frozen WalletProvisioningConfig reconstruct an equal instance."""
    original = WalletProvisioningConfig(
        wallet_id="hot-trading-eth-v1",
        chain="ETHEREUM",
        kind=WalletKind.HOT_TRADING,
        signing_surface=SigningSurface.CLOUD_KMS_ENCRYPTED,
        kms_key_uri="projects/pid/locations/us/keyRings/wallets/cryptoKeys/k1",
        archetype_id="carry_staked_basis",
        allowed_protocols=frozenset({"AAVE_V3", "UNISWAP_V3"}),
        allowed_destinations=frozenset(),
        spending_caps=SpendingCaps(per_tx_usd=Decimal("50000")),
        label="carry archetype hot wallet",
    )
    reconstructed = WalletProvisioningConfig(
        **{f.name: getattr(original, f.name) for f in dataclasses.fields(original)}
    )
    assert reconstructed == original


def test_spending_caps_decimal_precision_preserved() -> None:
    """Decimal fields on SpendingCaps retain full precision after field access and reconstruction."""
    caps = SpendingCaps(
        per_tx_usd=Decimal("99999.999999999999"),
        per_day_usd=Decimal("0.000000000000001"),
    )
    assert caps.per_tx_usd == Decimal("99999.999999999999")
    assert caps.per_day_usd == Decimal("0.000000000000001")
    reconstructed = SpendingCaps(**{f.name: getattr(caps, f.name) for f in dataclasses.fields(caps)})
    assert reconstructed == caps
