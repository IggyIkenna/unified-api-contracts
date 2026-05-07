"""Sanity tests for ``CHAIN_GENESIS_DATES`` — the per-chain mainnet
launch SSOT used by the data-status panel for per-chain pre-launch
date clipping.
"""

from __future__ import annotations

import re
from datetime import date

import pytest

from unified_api_contracts.registry.chain_env import (
    CHAIN_GENESIS_DATES,
    MAINNET_CHAIN_IDS,
    get_chain_genesis_date,
)

_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def test_chain_genesis_dates_iso_format() -> None:
    """Every value is a parseable ISO YYYY-MM-DD."""
    for chain, iso in CHAIN_GENESIS_DATES.items():
        assert _ISO_DATE_RE.match(iso), f"{chain}: {iso!r} not ISO YYYY-MM-DD"
        date.fromisoformat(iso)  # raises if invalid


def test_chain_genesis_dates_keys_are_uppercase() -> None:
    """Keys match the canonical UPPER form used everywhere else
    (``MAINNET_CHAIN_IDS`` keys, manifest ``chain`` column, etc.)."""
    for chain in CHAIN_GENESIS_DATES:
        assert chain == chain.upper(), f"{chain!r} should be UPPER"


def test_every_evm_mainnet_has_a_genesis_date() -> None:
    """Every EVM mainnet chain we declare in MAINNET_CHAIN_IDS should
    also declare a genesis date — otherwise data-status falls back to
    the category-wide start and shows phantom missing dates back to
    ETHEREUM's 2015 genesis for that chain."""
    evm_mainnet = {k for k, v in MAINNET_CHAIN_IDS.items() if v != 0}
    declared = set(CHAIN_GENESIS_DATES.keys())
    missing = evm_mainnet - declared
    assert not missing, (
        f"EVM mainnets without genesis date: {sorted(missing)}. "
        "Add to CHAIN_GENESIS_DATES — research the mainnet launch date."
    )


@pytest.mark.parametrize(
    ("chain", "expected"),
    [
        ("ETHEREUM", "2015-07-30"),
        ("ethereum", "2015-07-30"),
        ("ARBITRUM", "2021-08-31"),
        ("BASE", "2023-08-09"),
        ("SOLANA", "2020-03-16"),
    ],
)
def test_get_chain_genesis_date_case_insensitive(chain: str, expected: str) -> None:
    assert get_chain_genesis_date(chain) == expected


def test_get_chain_genesis_date_unknown_returns_none() -> None:
    assert get_chain_genesis_date("UNKNOWN_CHAIN_XYZ") is None
    assert get_chain_genesis_date("") is None
