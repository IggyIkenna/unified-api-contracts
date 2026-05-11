"""Validate the May-23 cutover wallet provisioning template.

The template at
``unified_api_contracts/config/cutover_wallet_provisioning_mainnet_template.json``
is the operational shape for May-23 — operator fills in mainnet addresses
post-cold-laptop key-gen per
``codex/05-infrastructure/custody-onboarding-checklist.md`` § B.3.

These tests verify the template parses cleanly into
:class:`WalletProvisioningConfig` instances (every row passes ``validate()``)
+ enforce cutover-specific invariants:

- ≥10 HOT_TRADING wallets (≥2 archetypes × ≥5 chains).
- ≥5 GAS_RESERVE wallets (1 per chain).
- All HOT_TRADING wallets bind to ``carry_staked_basis`` or
  ``ARBITRAGE_PRICE_DISPERSION`` (the two May-23 cutover archetypes).
- 5 chain coverage: ETHEREUM / ARBITRUM / BASE / POLYGON / SOLANA.
- Every wallet uses ``CLOUD_KMS_ENCRYPTED`` (May-23 cutover default).
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from unified_api_contracts.internal.domain.defi import (
    SigningSurface,
    SpendingCaps,
    WalletKind,
    WalletProvisioningConfig,
)


TEMPLATE_PATH = (
    Path(__file__).resolve().parents[3]
    / "unified_api_contracts"
    / "config"
    / "cutover_wallet_provisioning_mainnet_template.json"
)


def _decimal_or_none(v: str | None) -> Decimal | None:
    return Decimal(v) if v is not None else None


def _load_wallets() -> list[WalletProvisioningConfig]:
    """Parse the template into typed WalletProvisioningConfig instances."""
    with TEMPLATE_PATH.open() as f:
        data = json.load(f)
    wallets = []
    for row in data["wallets"]:
        caps_raw = row.get("spending_caps", {})
        caps = SpendingCaps(
            per_tx_usd=_decimal_or_none(caps_raw.get("per_tx_usd")),
            per_hour_usd=_decimal_or_none(caps_raw.get("per_hour_usd")),
            per_day_usd=_decimal_or_none(caps_raw.get("per_day_usd")),
            per_protocol_usd={
                k: Decimal(v) for k, v in caps_raw.get("per_protocol_usd", {}).items()
            },
        )
        wallets.append(
            WalletProvisioningConfig(
                wallet_id=row["wallet_id"],
                chain=row["chain"],
                kind=WalletKind(row["kind"]),
                signing_surface=SigningSurface(row["signing_surface"]),
                kms_key_uri=row.get("kms_key_uri", ""),
                private_key_secret_ref=row.get("private_key_secret_ref", ""),
                custodian_wallet_id=row.get("custodian_wallet_id", ""),
                allowed_protocols=frozenset(row.get("allowed_protocols", [])),
                allowed_destinations=frozenset(row.get("allowed_destinations", [])),
                spending_caps=caps,
                kill_switch_id=row.get("kill_switch_id", ""),
                archetype_id=row.get("archetype_id", ""),
                derivation_path=row.get("derivation_path", ""),
                label=row.get("label", ""),
            )
        )
    return wallets


def test_template_file_exists() -> None:
    assert TEMPLATE_PATH.exists(), f"Template missing at {TEMPLATE_PATH}"


def test_template_is_valid_json() -> None:
    with TEMPLATE_PATH.open() as f:
        data = json.load(f)
    assert "wallets" in data
    assert "_meta" in data
    assert isinstance(data["wallets"], list)


def test_every_wallet_passes_validate() -> None:
    """Every row in the template MUST pass WalletProvisioningConfig.validate()."""
    for wallet in _load_wallets():
        wallet.validate()


def test_cutover_archetype_coverage() -> None:
    """At least 1 HOT_TRADING wallet per May-23 cutover archetype × 5 chains."""
    wallets = _load_wallets()
    hot_trading = [w for w in wallets if w.kind == WalletKind.HOT_TRADING]
    archetypes_seen = {w.archetype_id for w in hot_trading}
    assert "carry_staked_basis" in archetypes_seen
    assert "ARBITRAGE_PRICE_DISPERSION" in archetypes_seen
    # ≥10 HOT_TRADING wallets (2 archetypes × 5 chains)
    assert len(hot_trading) >= 10


def test_chain_coverage_five_chains() -> None:
    """All 5 May-23 cutover chains have ≥1 HOT_TRADING wallet."""
    wallets = _load_wallets()
    hot_trading_chains = {w.chain for w in wallets if w.kind == WalletKind.HOT_TRADING}
    expected = {"ETHEREUM", "ARBITRUM", "BASE", "POLYGON", "SOLANA"}
    assert expected.issubset(hot_trading_chains), (
        f"Missing chain coverage: {expected - hot_trading_chains}"
    )


def test_gas_reserve_per_chain() -> None:
    """One GAS_RESERVE wallet per chain (5 total)."""
    wallets = _load_wallets()
    gas_reserves = [w for w in wallets if w.kind == WalletKind.GAS_RESERVE]
    gas_chains = {w.chain for w in gas_reserves}
    assert gas_chains == {"ETHEREUM", "ARBITRUM", "BASE", "POLYGON", "SOLANA"}
    assert len(gas_reserves) == 5


def test_every_wallet_uses_cloud_kms_for_cutover() -> None:
    """May-23 cutover default = CLOUD_KMS_ENCRYPTED across every row."""
    for wallet in _load_wallets():
        assert wallet.signing_surface == SigningSurface.CLOUD_KMS_ENCRYPTED, (
            f"{wallet.wallet_id}: expected CLOUD_KMS_ENCRYPTED, got {wallet.signing_surface}"
        )


def test_every_hot_trading_has_archetype_binding() -> None:
    """HOT_TRADING wallets MUST bind to one of the cutover archetypes."""
    valid_archetypes = {"carry_staked_basis", "ARBITRAGE_PRICE_DISPERSION"}
    for w in _load_wallets():
        if w.kind == WalletKind.HOT_TRADING:
            assert w.archetype_id in valid_archetypes, (
                f"{w.wallet_id}: archetype_id={w.archetype_id!r} not in {valid_archetypes}"
            )


def test_every_wallet_has_kill_switch_binding() -> None:
    """Every wallet MUST declare a kill_switch_id for May-23 cutover."""
    for w in _load_wallets():
        assert w.kill_switch_id, f"{w.wallet_id}: missing kill_switch_id"


def test_kms_key_uri_pattern() -> None:
    """All kms_key_uri values point at GCP Cloud HSM KeyRing wallets-prod in asia-northeast1."""
    for w in _load_wallets():
        assert "projects/central-element-323112" in w.kms_key_uri
        assert "locations/asia-northeast1" in w.kms_key_uri
        assert "keyRings/wallets-prod" in w.kms_key_uri


def test_per_archetype_spending_caps_present() -> None:
    """Every HOT_TRADING wallet declares per_tx + per_hour + per_day caps."""
    for w in _load_wallets():
        if w.kind == WalletKind.HOT_TRADING:
            assert w.spending_caps.per_tx_usd is not None
            assert w.spending_caps.per_hour_usd is not None
            assert w.spending_caps.per_day_usd is not None


def test_allowed_destinations_empty_for_non_treasury() -> None:
    """HOT_TRADING + GAS_RESERVE wallets MUST have empty allowed_destinations
    (only TREASURY may withdraw to external addresses)."""
    for w in _load_wallets():
        if w.kind in {WalletKind.HOT_TRADING, WalletKind.GAS_RESERVE}:
            assert not w.allowed_destinations, (
                f"{w.wallet_id} (kind={w.kind.value}) must have empty allowed_destinations"
            )


@pytest.mark.parametrize(
    "wallet_id,expected_kill_switch",
    [
        ("csb-eth-hot-lido-v1", "KILL_PER_ARCHETYPE_CARRY_STAKED_BASIS"),
        ("apd-eth-hot-uniswap-v1", "KILL_PER_ARCHETYPE_ARBITRAGE_PRICE_DISPERSION"),
        ("gas-reserve-eth-v1", "KILL_PER_ASSET_GROUP_DEFI"),
    ],
)
def test_specific_wallet_kill_switch_bindings(wallet_id: str, expected_kill_switch: str) -> None:
    """Sample wallet kill-switch bindings match the documented cutover plan."""
    wallets = {w.wallet_id: w for w in _load_wallets()}
    assert wallet_id in wallets, f"{wallet_id} not in template"
    assert wallets[wallet_id].kill_switch_id == expected_kill_switch
