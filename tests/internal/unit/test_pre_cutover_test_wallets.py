"""Validate pre-cutover test wallet provisioning JSON.

Per api_keys_wallets_accounts_readiness_2026_05_10.md Phase 4.D.3
+ pod-elysium-client-onboarding.md § 3.1.

The file at config/test_wallet_provisioning_pre_cutover.json points at
operator's existing EVM PK (defi-wallet-private-key in Secret Manager,
wrapped 2026-05-12 via wallets-staging CMK) for pre-cutover smoke testing
across 5 EVM testnets (Sepolia / Arbitrum Sepolia / Base Sepolia /
Polygon Amoy / Holesky).
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from unified_api_contracts.internal.domain.defi import (
    SigningSurface,
    SpendingCaps,
    WalletKind,
    WalletProvisioningConfig,
)

CONFIG_PATH = (
    Path(__file__).resolve().parents[3]
    / "unified_api_contracts"
    / "config"
    / "test_wallet_provisioning_pre_cutover.json"
)


def _decimal_or_none(v: str | None) -> Decimal | None:
    return Decimal(v) if v is not None else None


def _load_wallets() -> list[WalletProvisioningConfig]:
    with CONFIG_PATH.open() as f:
        data = json.load(f)
    wallets = []
    for row in data["wallets"]:
        caps_raw = row.get("spending_caps", {})
        caps = SpendingCaps(
            per_tx_usd=_decimal_or_none(caps_raw.get("per_tx_usd")),
            per_hour_usd=_decimal_or_none(caps_raw.get("per_hour_usd")),
            per_day_usd=_decimal_or_none(caps_raw.get("per_day_usd")),
            per_protocol_usd={k: Decimal(v) for k, v in caps_raw.get("per_protocol_usd", {}).items()},
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


def test_config_file_exists_and_parses() -> None:
    assert CONFIG_PATH.exists()
    with CONFIG_PATH.open() as f:
        data = json.load(f)
    assert "_meta" in data
    assert "wallets" in data


def test_all_wallets_pass_validate() -> None:
    """Every test wallet entry passes WalletProvisioningConfig.validate()."""
    for wallet in _load_wallets():
        wallet.validate()


def test_five_evm_testnet_chains_covered() -> None:
    """5 EVM chains: SEPOLIA + ARBITRUM (sepolia) + BASE + POLYGON + HOLESKY."""
    wallets = _load_wallets()
    chains = {w.chain for w in wallets}
    expected = {"SEPOLIA", "ARBITRUM", "BASE", "POLYGON", "HOLESKY"}
    assert chains == expected


def test_all_wallets_use_staging_cmk() -> None:
    """Test wallets MUST use wallets-staging CMK, not wallets-prod."""
    for w in _load_wallets():
        assert "wallets-staging" in w.kms_key_uri
        assert "wallets-prod" not in w.kms_key_uri


def test_all_wallets_reference_operator_existing_pk() -> None:
    """All entries reference the operator's pre-existing wrapped PK secret."""
    for w in _load_wallets():
        assert w.private_key_secret_ref == "defi-wallet-private-key-wrapped"


def test_trust_wallet_address_matches_meta() -> None:
    """The 5 entries share operator's Trust Wallet-derived EVM address.

    Note: the PK in `defi-wallet-private-key` corresponds to Trust Wallet,
    NOT MetaMask (verified 2026-05-12 via web3.py from_key round-trip).
    """
    with CONFIG_PATH.open() as f:
        data = json.load(f)
    expected_addr = data["_meta"]["operator_existing_wallets"]["ethereum_trust_address"]
    for row in data["wallets"]:
        assert row["address"] == expected_addr


def test_spending_caps_small_for_test_amounts() -> None:
    """Test wallets capped at $100 per_tx + $1000 per_day."""
    for w in _load_wallets():
        assert w.spending_caps.per_tx_usd == Decimal("100")
        assert w.spending_caps.per_day_usd == Decimal("1000")


def test_kill_switch_id_is_asset_group_defi() -> None:
    """Test wallets bind to KILL_PER_ASSET_GROUP_DEFI for blast-radius containment."""
    for w in _load_wallets():
        assert w.kill_switch_id == "KILL_PER_ASSET_GROUP_DEFI"


def test_archetype_id_is_test_namespaced() -> None:
    """Archetype_id prefixed `test_` to disambiguate from production rows."""
    for w in _load_wallets():
        assert w.archetype_id.startswith("test_")


def test_solana_pending_flagged_in_meta() -> None:
    """_pending_solana_wallets meta section captures operator-action TODO."""
    with CONFIG_PATH.open() as f:
        data = json.load(f)
    assert "_pending_solana_wallets" in data
    assert "test-sol-devnet" in data["_pending_solana_wallets"]["missing"]
