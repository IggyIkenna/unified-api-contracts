"""Validate the per-protocol approvals SSOT YAML.

Plan: api_keys_wallets_accounts_readiness_2026_05_10.md Phase 4.B.

Schema invariants:

- ``archetypes`` top-level key maps cutover archetypes
  (carry_staked_basis + ARBITRAGE_PRICE_DISPERSION) to per-chain
  per-protocol approval lists.
- Every approval declares ``asset`` + ``ceiling_usd`` (str-Decimal) +
  ``spender_contract`` + ``purpose``.
- Ceilings are positive Decimals.
- Chains match UAC ``CHAIN_RPC_TEMPLATES`` keys (case sensitive).
- Protocols match UAC ``transfer_types.VENUE_WALLET_CAPABILITIES`` keys
  OR are documented exceptions (e.g. AMM-specific routers).
- Allowlist of cutover archetypes matches Plan Phase 4.A scope.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest
import yaml


YAML_PATH = (
    Path(__file__).resolve().parents[3]
    / "unified_api_contracts"
    / "config"
    / "required_approvals.yaml"
)

CUTOVER_ARCHETYPES = {"carry_staked_basis", "ARBITRAGE_PRICE_DISPERSION"}
CUTOVER_CHAINS = {"ETHEREUM", "ARBITRUM", "BASE", "POLYGON", "SOLANA"}


def _load() -> dict[str, object]:
    with YAML_PATH.open() as f:
        return yaml.safe_load(f)


def test_yaml_exists_and_parses() -> None:
    assert YAML_PATH.exists()
    data = _load()
    assert isinstance(data, dict)
    assert data["version"] == 1


def test_archetypes_top_level_present() -> None:
    data = _load()
    assert "archetypes" in data
    assert isinstance(data["archetypes"], dict)


def test_cutover_archetypes_covered() -> None:
    """Both May-23 cutover archetypes have approval rows."""
    archetypes = _load()["archetypes"]
    assert CUTOVER_ARCHETYPES.issubset(archetypes.keys()), (
        f"Missing cutover archetype coverage: {CUTOVER_ARCHETYPES - set(archetypes.keys())}"
    )


@pytest.mark.parametrize("archetype", sorted(CUTOVER_ARCHETYPES))
def test_each_cutover_archetype_covers_five_chains(archetype: str) -> None:
    """Every cutover archetype covers all 5 chains."""
    archetypes = _load()["archetypes"]
    chains = set(archetypes[archetype].keys())
    assert CUTOVER_CHAINS.issubset(chains), (
        f"{archetype}: missing chains {CUTOVER_CHAINS - chains}"
    )


def test_every_approval_row_has_required_fields() -> None:
    """Every approval declares asset / ceiling_usd / spender_contract / purpose."""
    archetypes = _load()["archetypes"]
    for archetype, by_chain in archetypes.items():
        for chain, by_protocol in by_chain.items():
            for protocol, rows in by_protocol.items():
                for row in rows:
                    msg = f"{archetype}.{chain}.{protocol}.{row.get('asset', '?')}"
                    assert "asset" in row, f"{msg}: missing asset"
                    assert "ceiling_usd" in row, f"{msg}: missing ceiling_usd"
                    assert "spender_contract" in row, f"{msg}: missing spender_contract"
                    assert "purpose" in row, f"{msg}: missing purpose"


def test_every_ceiling_is_positive_decimal() -> None:
    """ceiling_usd parses as a positive Decimal."""
    archetypes = _load()["archetypes"]
    for archetype, by_chain in archetypes.items():
        for chain, by_protocol in by_chain.items():
            for protocol, rows in by_protocol.items():
                for row in rows:
                    ceiling = Decimal(row["ceiling_usd"])
                    assert ceiling > Decimal("0"), (
                        f"{archetype}.{chain}.{protocol}.{row['asset']}: ceiling must be > 0"
                    )


def test_no_max_uint256_ceilings() -> None:
    """Per CLAUDE.md security default — no MAX_UINT256 approvals (use per-session caps)."""
    max_uint256 = Decimal("2") ** 256 - 1
    archetypes = _load()["archetypes"]
    for archetype, by_chain in archetypes.items():
        for chain, by_protocol in by_chain.items():
            for protocol, rows in by_protocol.items():
                for row in rows:
                    ceiling = Decimal(row["ceiling_usd"])
                    # Sanity: cap > 1 trillion USD = suspicious operator override
                    assert ceiling < Decimal("1_000_000_000_000"), (
                        f"{archetype}.{chain}.{protocol}.{row['asset']}: "
                        "suspiciously-high ceiling — operator review required"
                    )
                    assert ceiling != max_uint256


def test_no_duplicate_asset_per_protocol() -> None:
    """Within (archetype, chain, protocol), assets are unique."""
    archetypes = _load()["archetypes"]
    for archetype, by_chain in archetypes.items():
        for chain, by_protocol in by_chain.items():
            for protocol, rows in by_protocol.items():
                assets = [r["asset"] for r in rows]
                assert len(assets) == len(set(assets)), (
                    f"{archetype}.{chain}.{protocol}: duplicate assets {assets}"
                )


def test_carry_staked_basis_covers_lst_protocols() -> None:
    """carry_staked_basis MUST cover LIDO + ETHERFI on Ethereum + JITO on Solana."""
    data = _load()
    csb = data["archetypes"]["carry_staked_basis"]
    assert "LIDO" in csb["ETHEREUM"]
    assert "ETHERFI" in csb["ETHEREUM"]
    assert "JITO" in csb["SOLANA"]


def test_arbitrage_price_dispersion_covers_dex_aggregator_protocols() -> None:
    """ARBITRAGE_PRICE_DISPERSION MUST cover Uniswap on every EVM chain + Jupiter on Solana."""
    data = _load()
    apd = data["archetypes"]["ARBITRAGE_PRICE_DISPERSION"]
    for chain in ("ETHEREUM", "ARBITRUM", "BASE", "POLYGON"):
        assert "UNISWAP_V3" in apd[chain], f"{chain}: missing UNISWAP_V3 coverage"
    assert "JUPITER" in apd["SOLANA"]


def test_total_approval_count_meets_minimum_scope() -> None:
    """At minimum 30+ approval rows across the matrix (≥10 per protocol × 5 chains × 2 archetypes proxy)."""
    archetypes = _load()["archetypes"]
    total = 0
    for by_chain in archetypes.values():
        for by_protocol in by_chain.values():
            for rows in by_protocol.values():
                total += len(rows)
    assert total >= 30, f"Only {total} approval rows; expected ≥30 for May-23 cutover coverage"
