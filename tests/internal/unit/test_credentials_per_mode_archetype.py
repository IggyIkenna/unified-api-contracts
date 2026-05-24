"""Validate per-mode + per-archetype credential subset YAMLs.

Plan: api_keys_wallets_accounts_readiness_2026_05_10.md Phase 7.A + 7.B.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

PER_MODE_PATH = Path(__file__).resolve().parents[3] / "unified_api_contracts" / "config" / "credentials_per_mode.yaml"
PER_ARCHETYPE_PATH = (
    Path(__file__).resolve().parents[3] / "unified_api_contracts" / "config" / "credentials_per_archetype.yaml"
)


def _load(path: Path) -> dict[str, object]:
    with path.open() as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# Phase 7.A — credentials_per_mode.yaml
# ---------------------------------------------------------------------------


def test_per_mode_yaml_exists_and_parses() -> None:
    assert PER_MODE_PATH.exists()
    data = _load(PER_MODE_PATH)
    assert data["version"] == 1


def test_per_mode_covers_three_modes() -> None:
    """Three modes: paper / batch / live."""
    data = _load(PER_MODE_PATH)
    modes = set(data["modes"].keys())
    assert modes == {"paper", "batch", "live"}


@pytest.mark.parametrize("mode", ["paper", "batch", "live"])
def test_per_mode_every_mode_declares_required(mode: str) -> None:
    """Every mode declares a non-empty `required` list."""
    data = _load(PER_MODE_PATH)
    mode_block = data["modes"][mode]
    assert "required" in mode_block
    assert "description" in mode_block
    assert len(mode_block["required"]) >= 5


def test_live_mode_includes_cloud_kms_cmk() -> None:
    """Live mode MUST declare cloud_kms_cmk_defi as a required credential (May-23 default)."""
    data = _load(PER_MODE_PATH)
    live_creds = [c["id"] for c in data["modes"]["live"]["required"]]
    assert "cloud_kms_cmk_defi" in live_creds


def test_live_mode_marks_post_cutover_only_creds() -> None:
    """Copper + Fireblocks creds are flagged post_cutover_only=True (June-1 flip)."""
    data = _load(PER_MODE_PATH)
    live_creds = data["modes"]["live"]["required"]
    copper_keys = [c for c in live_creds if "copper" in c["id"]]
    fireblocks_keys = [c for c in live_creds if "fireblocks" in c["id"]]
    assert copper_keys, "Copper creds missing from live mode"
    assert fireblocks_keys, "Fireblocks creds missing from live mode"
    for c in copper_keys + fireblocks_keys:
        assert c.get("post_cutover_only") is True, f"{c['id']} must be marked post_cutover_only=True"


def test_paper_mode_does_not_require_production_custody() -> None:
    """Paper mode uses sandbox custody only — no production CMKs or live MPC."""
    data = _load(PER_MODE_PATH)
    paper_creds = [c["id"] for c in data["modes"]["paper"]["required"]]
    assert "cloud_kms_cmk_defi" not in paper_creds
    assert "copper-api-key" not in paper_creds  # only sandbox creds permitted
    assert "fireblocks-api-key" not in paper_creds


def test_batch_mode_includes_read_scope_venue_keys() -> None:
    """Batch mode declares read-scope venue keys (not trade-scope)."""
    data = _load(PER_MODE_PATH)
    batch_creds = [c["id"] for c in data["modes"]["batch"]["required"]]
    # bybit has a single unscoped key in Secret Manager (bybit_api_key), not a
    # read/trade split like binance/deribit — match the real SM secret id.
    assert "bybit_api_key" in batch_creds
    assert "binance-read-api-key" in batch_creds
    # No trade-scope keys in batch (binance has a real read/trade split in SM)
    assert "binance-trade-api-key" not in batch_creds


# ---------------------------------------------------------------------------
# Phase 7.B — credentials_per_archetype.yaml
# ---------------------------------------------------------------------------


def test_per_archetype_yaml_exists_and_parses() -> None:
    assert PER_ARCHETYPE_PATH.exists()
    data = _load(PER_ARCHETYPE_PATH)
    assert data["version"] == 1


def test_per_archetype_covers_cutover_archetypes() -> None:
    """Both May-23 cutover archetypes are declared."""
    data = _load(PER_ARCHETYPE_PATH)
    archetypes = set(data["archetypes"].keys())
    assert "carry_staked_basis" in archetypes
    assert "ARBITRAGE_PRICE_DISPERSION" in archetypes


def test_carry_staked_basis_declares_all_5_chain_wallets() -> None:
    """csb requires its 5 per-chain wrapped PKs."""
    data = _load(PER_ARCHETYPE_PATH)
    csb_required = set(data["archetypes"]["carry_staked_basis"]["required_credentials"])
    expected_wallets = {
        "csb-eth-hot-lido-v1-wrapped",
        "csb-arb-hot-lido-v1-wrapped",
        "csb-base-hot-aave-v1-wrapped",
        "csb-poly-hot-aave-v1-wrapped",
        "csb-sol-hot-jito-v1-wrapped",
    }
    assert expected_wallets.issubset(csb_required)


def test_carry_staked_basis_declares_perp_hedge_venues() -> None:
    """csb requires 6 perp hedge venue trade keys."""
    data = _load(PER_ARCHETYPE_PATH)
    csb_required = set(data["archetypes"]["carry_staked_basis"]["required_credentials"])
    # Real GCP Secret Manager ids (one representative key per perp venue). okx is
    # per-client (exec-<client>-okx-*) so it is declared as a pattern, not a flat id.
    perp_keys = {
        "bybit_api_key",
        "binance-trade-api-key",
        "deribit-trade-api-key",
        "pattern:exec-<client>-okx-api-key",
        "hyperliquid-trade-key",
        "aster-api-key",
    }
    assert perp_keys.issubset(csb_required)


def test_arbitrage_price_dispersion_declares_config_variants() -> None:
    """ARBITRAGE_PRICE_DISPERSION lists its 2 config variants per UAC archetype canonicalisation."""
    data = _load(PER_ARCHETYPE_PATH)
    apd = data["archetypes"]["ARBITRAGE_PRICE_DISPERSION"]
    variants = set(apd["config_variants"])
    assert "funding_rate_dispersion" in variants
    assert "cross_venue_price_dispersion" in variants


def test_arbitrage_price_dispersion_declares_5_chain_wallets() -> None:
    """APD requires its 5 per-chain wrapped PKs."""
    data = _load(PER_ARCHETYPE_PATH)
    apd_required = set(data["archetypes"]["ARBITRAGE_PRICE_DISPERSION"]["required_credentials"])
    expected = {
        "apd-eth-hot-uniswap-v1-wrapped",
        "apd-arb-hot-uniswap-v1-wrapped",
        "apd-base-hot-uniswap-v1-wrapped",
        "apd-poly-hot-uniswap-v1-wrapped",
        "apd-sol-hot-raydium-v1-wrapped",
    }
    assert expected.issubset(apd_required)


def test_every_archetype_declares_telegram() -> None:
    """Every archetype includes telegram-bot-token (alerting hard requirement; real SM id)."""
    data = _load(PER_ARCHETYPE_PATH)
    for archetype, bundle in data["archetypes"].items():
        creds = bundle["required_credentials"]
        assert "telegram-bot-token" in creds, f"{archetype}: missing telegram-bot-token"


def test_every_archetype_declares_gcp_sa() -> None:
    """Every archetype requires gcp_service_account."""
    data = _load(PER_ARCHETYPE_PATH)
    for archetype, bundle in data["archetypes"].items():
        assert "gcp_service_account" in bundle["required_credentials"], f"{archetype}: missing gcp_service_account"


def test_archetype_credential_match_template_wallet_ids() -> None:
    """Wrapped PK refs in per-archetype YAML match wallet_ids in cutover template."""
    import json
    from pathlib import Path as _P

    template = (
        _P(__file__).resolve().parents[3]
        / "unified_api_contracts"
        / "config"
        / "cutover_wallet_provisioning_mainnet_template.json"
    )
    with template.open() as f:
        wallet_template = json.load(f)
    template_wallet_ids = {w["wallet_id"] for w in wallet_template["wallets"]}

    data = _load(PER_ARCHETYPE_PATH)
    # csb wrapped refs match wallet_ids modulo -wrapped suffix
    for archetype in ("carry_staked_basis", "ARBITRAGE_PRICE_DISPERSION"):
        for cred in data["archetypes"][archetype]["required_credentials"]:
            if cred.endswith("-wrapped"):
                wallet_id = cred[: -len("-wrapped")]
                assert wallet_id in template_wallet_ids, (
                    f"{archetype}: wrapped ref {cred} doesn't match template wallet_id"
                )
