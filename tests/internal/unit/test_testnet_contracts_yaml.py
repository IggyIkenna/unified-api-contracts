"""Schema-validation tests for testnet_contracts.yaml.

Per api_keys_wallets_accounts_readiness_2026_05_10.md Phase 4.D.1 — adds 4
new testnet chains for May-23 cutover scope:

- Arbitrum Sepolia (chain_id 421614)
- Base Sepolia (84532)
- Polygon Amoy (80002)
- Solana devnet (103)

Plus Holesky (17000, pre-existing per Lido + EigenLayer requirement) +
Sepolia + Ethereum mainnet — total 7 entries.
"""

from __future__ import annotations

import importlib.resources
from pathlib import Path

import yaml

# testnet_contracts.yaml is packaged inside the unified_api_contracts package
# (alongside cloud-providers.yaml) so it is always available via
# importlib.resources — including inside a built wheel / Docker image where the
# repo-root config/ dir is absent (mirrors bucket_naming's UAC-packaged read).
YAML_PATH = Path(str(importlib.resources.files("unified_api_contracts") / "config" / "testnet_contracts.yaml"))


def _load() -> dict[int, dict[str, dict[str, str]]]:
    with YAML_PATH.open() as f:
        return yaml.safe_load(f)


def test_yaml_parses_cleanly() -> None:
    assert YAML_PATH.exists()
    data = _load()
    assert isinstance(data, dict)


def test_mainnet_present() -> None:
    """Ethereum mainnet (chain_id=1) is the production reference."""
    data = _load()
    assert 1 in data
    assert "aave_v3" in data[1]


def test_sepolia_present() -> None:
    """Sepolia (chain_id=11155111) is the primary EVM testnet."""
    data = _load()
    assert 11155111 in data
    assert "aave_v3" in data[11155111]
    assert "uniswap_v3" in data[11155111]
    assert data[11155111]["aave_v3"]["flash_loan_receiver"].startswith("0x")


def test_holesky_present_with_lido_and_eigenlayer() -> None:
    """Holesky (chain_id=17000) needed for Lido + EigenLayer integration."""
    data = _load()
    assert 17000 in data
    assert "lido" in data[17000]
    assert "eigenlayer" in data[17000]
    assert data[17000]["lido"]["steth"].startswith("0x")
    assert data[17000]["eigenlayer"]["delegation_manager"].startswith("0x")


def test_arbitrum_sepolia_present() -> None:
    """Arbitrum Sepolia (chain_id=421614) — added 2026-05-12 Phase 4.D.1."""
    data = _load()
    assert 421614 in data
    assert "aave_v3" in data[421614]
    assert "uniswap_v3" in data[421614]
    assert data[421614]["aave_v3"]["pool"].startswith("0x")


def test_base_sepolia_present() -> None:
    """Base Sepolia (chain_id=84532) — added 2026-05-12 Phase 4.D.1."""
    data = _load()
    assert 84532 in data
    assert "aave_v3" in data[84532]
    assert "uniswap_v3" in data[84532]


def test_polygon_amoy_present() -> None:
    """Polygon Amoy (chain_id=80002) — added 2026-05-12 Phase 4.D.1."""
    data = _load()
    assert 80002 in data
    assert "aave_v3" in data[80002]
    assert "uniswap_v3" in data[80002]


def test_solana_devnet_present() -> None:
    """Solana devnet (chain_id=103) — added 2026-05-12 Phase 4.D.1."""
    data = _load()
    assert 103 in data
    # Solana uses program IDs not EVM addresses
    assert "jito" in data[103]
    assert "drift_v2" in data[103]
    assert "pyth_hermes" in data[103]
    # Hermes devnet base_url is HTTPS not on-chain
    assert data[103]["pyth_hermes"]["base_url"].startswith("https://")


def test_all_testnet_chains_have_flash_loan_receiver() -> None:
    """Every EVM testnet declares a flash_loan_receiver (Phase 4.D.5)."""
    data = _load()
    evm_testnets = [11155111, 17000, 421614, 84532, 80002]
    for chain_id in evm_testnets:
        assert chain_id in data, f"missing chain {chain_id}"
        assert "aave_v3" in data[chain_id], f"missing aave_v3 on {chain_id}"
        assert "flash_loan_receiver" in data[chain_id]["aave_v3"], f"missing flash_loan_receiver on chain {chain_id}"
        flr = data[chain_id]["aave_v3"]["flash_loan_receiver"]
        assert flr.startswith("0x"), f"flash_loan_receiver on chain {chain_id} not 0x-prefixed"
        assert len(flr) == 42, f"flash_loan_receiver on chain {chain_id} not 20-byte EVM addr"


def test_evm_addresses_are_well_formed() -> None:
    """Every EVM address (string starting with 0x) is exactly 42 chars (20 bytes hex + 0x)."""
    data = _load()
    evm_chains = [1, 11155111, 17000, 421614, 84532, 80002]
    for chain_id in evm_chains:
        if chain_id not in data:
            continue
        for protocol, contracts in data[chain_id].items():
            for name, value in contracts.items():
                if isinstance(value, str) and value.startswith("0x"):
                    assert len(value) == 42, f"chain={chain_id} protocol={protocol} {name}={value!r} not 42 chars"


def test_six_chains_covered_for_may23_cutover() -> None:
    """May-23 cutover scope: 5 cutover chains (Eth + Arb + Base + Polygon + Sol) + Holesky for Lido/EigenLayer."""
    data = _load()
    cutover = {1, 421614, 84532, 80002, 103, 17000}  # mainnet + testnets per chain
    # All 5 cutover chains + Holesky represented (mainnet=1 acts as Ethereum cutover)
    assert cutover.issubset(set(data.keys())), f"missing chains: {cutover - set(data.keys())}"
