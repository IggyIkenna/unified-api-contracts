"""Sanity tests for ``PROTOCOL_LAUNCH_DATES`` — the per-(chain, protocol)
mainnet launch SSOT used by the data-status panel for pre-protocol-launch
date clipping.

Mirrors ``test_chain_genesis_dates.py`` but at the (chain, protocol)
shard-axis granularity per the codex shard-key matrix for DeFi:
``(asset_group=defi, chain, venue/protocol, data_type, instrument, day)``.
"""

from __future__ import annotations

import re
from datetime import date

import pytest

from unified_api_contracts.registry.chain_env import (
    _PROTOCOL_LAUNCH_PENDING_INVESTIGATION,
    CHAIN_GENESIS_DATES,
    PROTOCOL_LAUNCH_DATES,
    get_chain_genesis_date,
    get_protocol_launch_date,
)
from unified_api_contracts.registry.defi_venues import ALL_DEFI_VENUES

_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _split_canonical_venue(canonical: str) -> tuple[str, str] | None:
    """``"AAVE_V3-ARBITRUM"`` → ``("ARBITRUM", "AAVE_V3")``.

    Returns ``None`` for venues that don't follow the ``PROTOCOL-CHAIN``
    convention (currently none, but the helper future-proofs the test).
    """
    if "-" not in canonical:
        return None
    protocol, chain = canonical.rsplit("-", 1)
    return chain, protocol


def test_protocol_launch_dates_iso_format() -> None:
    """Every value is a parseable ISO YYYY-MM-DD."""
    for (chain, protocol), iso in PROTOCOL_LAUNCH_DATES.items():
        assert _ISO_DATE_RE.match(iso), f"({chain},{protocol}): {iso!r} not ISO YYYY-MM-DD"
        date.fromisoformat(iso)  # raises if invalid


def test_protocol_launch_dates_keys_are_uppercase() -> None:
    """Both halves of every key match the canonical UPPER form used in
    ``CHAIN_GENESIS_DATES``, ``ALL_DEFI_VENUES``, and the manifest."""
    for chain, protocol in PROTOCOL_LAUNCH_DATES:
        assert chain == chain.upper(), f"chain {chain!r} should be UPPER"
        assert protocol == protocol.upper(), f"protocol {protocol!r} should be UPPER"


def test_protocol_launch_dates_chain_known_to_genesis_ssot() -> None:
    """Every chain referenced by ``PROTOCOL_LAUNCH_DATES`` must also be
    declared in ``CHAIN_GENESIS_DATES`` — otherwise the
    ``max(chain_genesis, protocol_launch)`` composition silently drops
    one of the clips."""
    for chain, _protocol in PROTOCOL_LAUNCH_DATES:
        assert chain in CHAIN_GENESIS_DATES, f"chain {chain!r} in PROTOCOL_LAUNCH_DATES but not in CHAIN_GENESIS_DATES"


# Subgraphs for some (chain, protocol) pairs index PRE-public-mainnet-launch
# blocks (testnet/devnet phase blocks the chain rolled into mainnet at
# regenesis). For those pairs ``earliest_subgraph_event < chain_genesis``
# is correct on-disk reality — the right SSOT for ``PROTOCOL_LAUNCH_DATES``
# is "earliest day a subgraph query returns rows" (per Tab 14 fork1 audit
# 2026-05-08), so this test allow-lists the known cases. Adding a new pair
# here requires inline subgraph-probe citation in ``PROTOCOL_LAUNCH_DATES``.
_PRE_GENESIS_SUBGRAPH_INDEXED_ALLOWLIST: frozenset[tuple[str, str]] = frozenset(
    {
        ("ARBITRUM", "UNISWAP_V3"),  # subgraph indexes 2021-06-01; ARB public mainnet 2021-08-31
        ("ARBITRUM", "UNISWAP_V3"),  # canonical alias for UNISWAP_V3
        ("OPTIMISM", "UNISWAP_V3"),  # subgraph indexes 2021-11-11; OP regenesis mainnet 2021-12-16
        ("OPTIMISM", "UNISWAP_V3"),  # canonical alias for UNISWAP_V3
        ("BASE", "UNISWAP_V3"),  # subgraph indexes 2023-07-31; BASE public mainnet 2023-08-09
        ("BASE", "UNISWAP_V3"),  # canonical alias for UNISWAP_V3
        ("BASE", "COMPOUND_V3"),  # Comet cUSDbCv3 Base contract creation 2023-08-11 (corrected 2026-07-18)
        ("BASE", "COMPOUND_V3"),  # canonical alias for COMPOUND_V3
    }
)


def test_protocol_launch_after_chain_genesis() -> None:
    """A protocol's earliest subgraph event must not predate chain
    genesis EXCEPT for documented cases where the subgraph indexes
    pre-public-launch blocks (see ``_PRE_GENESIS_SUBGRAPH_INDEXED_ALLOWLIST``).
    Catches typo-class data-entry errors while permitting the legitimate
    "subgraph indexes pre-mainnet" shape Tab 14's 2026-05-08 audit
    documented across UNISWAP_V3 ARB/OPT/BASE + COMPOUND_V3 BASE."""
    for (chain, protocol), launch_iso in PROTOCOL_LAUNCH_DATES.items():
        if (chain, protocol) in _PRE_GENESIS_SUBGRAPH_INDEXED_ALLOWLIST:
            continue
        chain_genesis_iso = CHAIN_GENESIS_DATES[chain]
        launch = date.fromisoformat(launch_iso)
        chain_genesis = date.fromisoformat(chain_genesis_iso)
        assert launch >= chain_genesis, (
            f"({chain},{protocol}) launch {launch_iso} predates chain genesis {chain_genesis_iso}"
        )


def test_every_defi_venue_declared_or_pending() -> None:
    """Every canonical ``PROTOCOL-CHAIN`` entry in ``ALL_DEFI_VENUES``
    must either have a launch date in ``PROTOCOL_LAUNCH_DATES`` OR be
    on the ``_PROTOCOL_LAUNCH_PENDING_INVESTIGATION`` skip list. Adding
    a new DeFi venue without doing one of those two is a CI failure —
    silent NaN clipping was the ARBITRUM 32/54 bug we are fixing."""
    declared = set(PROTOCOL_LAUNCH_DATES.keys())
    pending = _PROTOCOL_LAUNCH_PENDING_INVESTIGATION
    missing: list[tuple[str, str]] = []
    for venue in ALL_DEFI_VENUES:
        split = _split_canonical_venue(venue)
        if split is None:
            continue
        if split in declared or split in pending:
            continue
        missing.append(split)
    assert not missing, (
        f"DeFi (chain, protocol) pairs missing from PROTOCOL_LAUNCH_DATES: "
        f"{sorted(missing)}. Either research + declare the launch date OR "
        "add to _PROTOCOL_LAUNCH_PENDING_INVESTIGATION."
    )


def test_pending_investigation_disjoint_from_declared() -> None:
    """A pair is either declared with a date OR pending — not both.
    Catches stale skip-list entries left behind after research lands."""
    overlap = set(PROTOCOL_LAUNCH_DATES.keys()) & _PROTOCOL_LAUNCH_PENDING_INVESTIGATION
    assert not overlap, (
        f"({sorted(overlap)}) appear in both PROTOCOL_LAUNCH_DATES and "
        "_PROTOCOL_LAUNCH_PENDING_INVESTIGATION — remove the latter once "
        "the former lands."
    )


@pytest.mark.parametrize(
    ("chain", "protocol", "expected"),
    [
        ("ETHEREUM", "AAVE_V3", "2023-01-27"),  # AAVE V3 ETH mainnet — first
        # subgraph event 2023-01-27 08:00:11 UTC, verified 2026-05-08 via
        # gateway.thegraph.com Cd2gEDVeqnjBn1hSeqFMitw8Q1iiyV9FYUZkLNRcL87g.
        ("ethereum", "aavev3", "2023-01-27"),  # case-insensitive
        ("ARBITRUM", "AAVE_V3", "2022-03-16"),
        ("BASE", "AAVE_V3", "2023-08-22"),  # Tab 14 audit 2026-05-08
        ("OPTIMISM", "AAVE_V3", "2022-03-15"),  # Tab 14 audit 2026-05-08
        ("BSC", "AAVE_V3", "2024-01-23"),  # Tab 14 audit 2026-05-08
        ("ETHEREUM", "COMPOUND_V3", "2022-08-13"),  # Tab 14 subgraph audit 2026-05-08
        ("ARBITRUM", "UNISWAP_V3", "2021-06-01"),  # Tab 14 audit; pre-mainnet-open indexed
        ("ETHEREUM", "SPARK", "2023-03-07"),  # Tab 14 audit; added 2026-05-08
        ("ETHEREUM", "UNISWAP_V3", "2021-05-04"),
        ("SOLANA", "JITO", "2022-08-15"),
    ],
)
def test_get_protocol_launch_date_known(chain: str, protocol: str, expected: str) -> None:
    assert get_protocol_launch_date(chain, protocol) == expected


def test_get_protocol_launch_date_unknown_returns_none() -> None:
    assert get_protocol_launch_date("UNKNOWN_CHAIN", "AAVE_V3") is None
    assert get_protocol_launch_date("ETHEREUM", "UNKNOWN_PROTOCOL") is None
    assert get_protocol_launch_date("", "AAVE_V3") is None
    assert get_protocol_launch_date("ETHEREUM", "") is None


def test_compose_with_chain_genesis_takes_max() -> None:
    """The documented composition ``max(chain_genesis, protocol_launch)``
    is the contract callers depend on. Verify with a concrete pair where
    the protocol launch postdates chain genesis (AAVE_V3-ARBITRUM)."""
    chain_genesis = get_chain_genesis_date("ARBITRUM")
    protocol_launch = get_protocol_launch_date("ARBITRUM", "AAVE_V3")
    assert chain_genesis == "2021-08-31"
    assert protocol_launch == "2022-03-16"
    # max of the two iso strings is the protocol launch (later)
    assert max(chain_genesis, protocol_launch) == "2022-03-16"


def test_venue_launch_dates_no_new_drift_vs_chain_env() -> None:
    """Cross-registry consistency guard — SSOT issue
    ``uac_defi_launch_date_registry_drift_2026_07_18``.

    ``venue_launch_dates.DEFI_VENUE_LAUNCH_DATES`` (PROTOCOL-CHAIN string keys) and
    ``chain_env.PROTOCOL_LAUNCH_DATES`` ((CHAIN, PROTOCOL) tuple keys) both carry DeFi
    launch dates; where they OVERLAP they must agree. ``AAVE_V3-ETHEREUM`` was corrected
    2026-07-18 (2022-03-16 was the debunked L2-cohort date -> 2023-01-27, the
    subgraph-audited value chain_env's own comment documents). The remaining overlaps
    below are KNOWN drifts (deltas 1-292d) PENDING per-pair on-chain re-verification —
    allowlisted so a NEW divergence FAILS this test; resolving one means REMOVING it here.
    """
    from unified_api_contracts.registry.venue_launch_dates import DEFI_VENUE_LAUNCH_DATES

    # The 6 drifts >=7d were ON-CHAIN VERIFIED + corrected 2026-07-18 (both registries now agree);
    # only the <=4d tail remains, pending a cheap re-audit (low-impact for the expected-window
    # denominator). Resolving one = REMOVING it here.
    known_drifts_pending_audit = {
        "AAVE_V3-POLYGON",  # 4d
        "AAVE_V3-AVALANCHE",  # 4d
        "AAVE_V3-OPTIMISM",  # 1d
        "COMPOUND_V3-SCROLL",  # 1d
        "UNISWAP_V2-ETHEREUM",  # 1d
        "UNISWAP_V3-ETHEREUM",  # 1d
        "UNISWAP_V3-POLYGON",  # 1d
        "ROCKETPOOL-ETHEREUM",  # 1d
        "ETHENA-ETHEREUM",  # 1d
        "ETHERFI-ETHEREUM",  # 1d
        "KAMINO-SOLANA",  # 1d
        "JITO-SOLANA",  # 1d
        "GMX-AVALANCHE",  # 1d
    }
    drifts: set[str] = set()
    for vkey, vdate in DEFI_VENUE_LAUNCH_DATES.items():
        if "-" not in vkey:
            continue
        protocol, chain = vkey.rsplit("-", 1)
        chain_env_date = PROTOCOL_LAUNCH_DATES.get((chain, protocol))
        if chain_env_date is not None and chain_env_date != vdate:
            drifts.add(vkey)

    new_drifts = drifts - known_drifts_pending_audit
    assert not new_drifts, (
        "NEW venue_launch_dates↔chain_env launch-date drift — reconcile the pair or, if a genuine "
        f"per-purpose divergence, add it to known_drifts_pending_audit with a comment: {sorted(new_drifts)}"
    )
    # The 2026-07-18 on-chain-verified corrections must hold (both registries agree on the verified value).
    assert "AAVE_V3-ETHEREUM" not in drifts
    on_chain_verified_2026_07_18 = (
        "AAVE_V3-BSC",
        "AAVE_V3-LINEA",
        "COMPOUND_V3-ETHEREUM",
        "COMPOUND_V3-BASE",
        "COMPOUND_V3-ARBITRUM",
        "COMPOUND_V3-OPTIMISM",
    )
    for resolved in on_chain_verified_2026_07_18:
        assert resolved not in drifts, f"{resolved} regressed — its 2026-07-18 verified correction was reverted"
    assert DEFI_VENUE_LAUNCH_DATES["AAVE_V3-ETHEREUM"] == "2023-01-27"
    assert DEFI_VENUE_LAUNCH_DATES["AAVE_V3-BSC"] == "2024-01-23"
    assert DEFI_VENUE_LAUNCH_DATES["AAVE_V3-LINEA"] == "2025-02-11"
