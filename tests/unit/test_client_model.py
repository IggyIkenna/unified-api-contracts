"""Unit tests for the client + capital allocation SSOT.

Covers cross_cutting deliverable #3 — :class:`Client`, :class:`VenueAccount`,
:class:`CapitalAllocation`, the seed dictionaries, the lookup helpers, and the
fail-loud validators.

Plan:
``unified-trading-pm/plans/active/cross_cutting_may_23_deliverables_2026_05_08.md``
deliverable #3.
"""

from __future__ import annotations

import dataclasses

import pytest

from unified_api_contracts.canonical.domain.client.model import (
    CAPITAL_ALLOCATION_SEED,
    CLIENTS_SEED,
    AllocationViolationError,
    CapitalAllocation,
    Client,
    VenueAccount,
    get_capital_allocation,
    get_client,
    is_allocation_declared,
    is_within_allocation,
    validate_allocation_respect,
)

# ---------------------------------------------------------------------------
# VenueAccount — frozen + hashable
# ---------------------------------------------------------------------------


def test_venue_account_is_frozen() -> None:
    account = VenueAccount(venue="binance", account_id="a-binance-main")
    with pytest.raises(dataclasses.FrozenInstanceError):
        account.account_id = "tampered"  # type: ignore[misc]


def test_venue_account_is_hashable_and_set_member() -> None:
    """Frozen dataclasses are hashable; verify set membership works so
    callers can de-dup account collections."""
    main = VenueAccount(venue="binance", account_id="a-binance-main")
    sub = VenueAccount(
        venue="binance",
        account_id="a-binance-sub",
        is_subaccount=True,
        parent_account_id="a-binance-main",
    )
    accounts = {main, sub, main}  # duplicate main collapses
    assert len(accounts) == 2
    assert main in accounts
    assert sub in accounts


def test_venue_account_subaccount_defaults() -> None:
    """is_subaccount defaults to False and parent_account_id defaults to None."""
    account = VenueAccount(venue="okx", account_id="a-okx-main")
    assert account.is_subaccount is False
    assert account.parent_account_id is None


# ---------------------------------------------------------------------------
# Client — frozen + accounts_for_venue helper
# ---------------------------------------------------------------------------


def test_client_constructed_with_multiple_accounts() -> None:
    main = VenueAccount(venue="binance", account_id="x-binance-main")
    sub = VenueAccount(
        venue="binance",
        account_id="x-binance-sub-a",
        is_subaccount=True,
        parent_account_id="x-binance-main",
    )
    bybit = VenueAccount(venue="bybit", account_id="x-bybit-main")
    client = Client(client_id="x", display_name="X", accounts=(main, sub, bybit))
    assert client.client_id == "x"
    assert len(client.accounts) == 3


def test_accounts_for_venue_returns_main_and_subaccounts() -> None:
    """accounts_for_venue must include sub-accounts so caller code that walks
    a venue's accounts (for credential fetch / position rollup) sees the
    full subset."""
    main = VenueAccount(venue="binance", account_id="x-binance-main")
    sub = VenueAccount(
        venue="binance",
        account_id="x-binance-sub-a",
        is_subaccount=True,
        parent_account_id="x-binance-main",
    )
    bybit = VenueAccount(venue="bybit", account_id="x-bybit-main")
    client = Client(client_id="x", display_name="X", accounts=(main, sub, bybit))
    binance_accounts = client.accounts_for_venue("binance")
    assert binance_accounts == (main, sub)
    bybit_accounts = client.accounts_for_venue("bybit")
    assert bybit_accounts == (bybit,)
    assert client.accounts_for_venue("unknown") == ()


def test_client_default_accounts_empty_tuple() -> None:
    """Empty accounts tuple is the legitimate freshly-onboarded shape."""
    client = Client(client_id="fresh", display_name="Fresh")
    assert client.accounts == ()


# ---------------------------------------------------------------------------
# CapitalAllocation — __post_init__ bounds validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad_capital", [0.0, -0.01, -1_000_000.0])
def test_capital_allocation_rejects_non_positive_capital(bad_capital: float) -> None:
    with pytest.raises(ValueError, match="initial_capital_usd"):
        CapitalAllocation(
            client_id="x",
            archetype="carry_staked_basis",
            venue="aave_v3_arbitrum",
            initial_capital_usd=bad_capital,
        )


@pytest.mark.parametrize("bad_pct", [0.0, -0.1, 1.01, 2.0])
def test_capital_allocation_rejects_out_of_bounds_position_pct(bad_pct: float) -> None:
    with pytest.raises(ValueError, match="max_position_pct"):
        CapitalAllocation(
            client_id="x",
            archetype="carry_staked_basis",
            venue="aave_v3_arbitrum",
            initial_capital_usd=10_000.0,
            max_position_pct=bad_pct,
        )


@pytest.mark.parametrize("bad_pct", [0.0, -0.1, 1.01, 2.0])
def test_capital_allocation_rejects_out_of_bounds_drawdown_pct(bad_pct: float) -> None:
    with pytest.raises(ValueError, match="max_drawdown_pct"):
        CapitalAllocation(
            client_id="x",
            archetype="carry_staked_basis",
            venue="aave_v3_arbitrum",
            initial_capital_usd=10_000.0,
            max_drawdown_pct=bad_pct,
        )


def test_capital_allocation_accepts_boundary_values() -> None:
    """Exactly 1.0 is allowed for both percentage caps; tiny positive epsilon
    is allowed for capital."""
    allocation = CapitalAllocation(
        client_id="x",
        archetype="carry_staked_basis",
        venue="aave_v3_arbitrum",
        initial_capital_usd=0.01,
        max_position_pct=1.0,
        max_drawdown_pct=1.0,
    )
    assert allocation.max_position_pct == 1.0
    assert allocation.max_drawdown_pct == 1.0


def test_capital_allocation_is_frozen_and_hashable() -> None:
    allocation = CapitalAllocation(
        client_id="x",
        archetype="carry_staked_basis",
        venue="aave_v3_arbitrum",
        initial_capital_usd=10_000.0,
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        allocation.initial_capital_usd = 0.0  # type: ignore[misc]
    # Hashable smoke test
    _ = {allocation}


# ---------------------------------------------------------------------------
# get_capital_allocation + is_allocation_declared lookup behaviour
# ---------------------------------------------------------------------------


def test_get_capital_allocation_returns_seed_entry() -> None:
    allocation = get_capital_allocation("ikenna", "carry_staked_basis", "aave_v3_arbitrum")
    assert allocation.client_id == "ikenna"
    assert allocation.archetype == "carry_staked_basis"
    assert allocation.venue == "aave_v3_arbitrum"
    assert allocation.initial_capital_usd > 0


def test_get_capital_allocation_raises_for_unknown_triple() -> None:
    with pytest.raises(KeyError, match="No CapitalAllocation declared"):
        get_capital_allocation("nonexistent", "carry_staked_basis", "aave_v3_arbitrum")


def test_is_allocation_declared_membership() -> None:
    assert is_allocation_declared("ikenna", "carry_staked_basis", "aave_v3_arbitrum") is True
    assert is_allocation_declared("nonexistent", "carry_staked_basis", "aave_v3_arbitrum") is False


# ---------------------------------------------------------------------------
# is_within_allocation + validate_allocation_respect
# ---------------------------------------------------------------------------


def _sample_allocation() -> CapitalAllocation:
    return CapitalAllocation(
        client_id="x",
        archetype="carry_staked_basis",
        venue="aave_v3_arbitrum",
        initial_capital_usd=100_000.0,
        max_position_pct=0.5,
        max_drawdown_pct=0.10,
    )


def test_is_within_allocation_happy_path() -> None:
    allocation = _sample_allocation()
    # Position 40k USD < 50k cap; drawdown 5% < 10% cap.
    assert is_within_allocation(allocation, position_value_usd=40_000.0, drawdown_pct=0.05) is True


def test_is_within_allocation_returns_false_when_position_exceeds_cap() -> None:
    allocation = _sample_allocation()
    # Position 50_001 > cap 50_000.
    assert is_within_allocation(allocation, position_value_usd=50_001.0, drawdown_pct=0.0) is False


def test_is_within_allocation_returns_false_when_drawdown_exceeds_cap() -> None:
    allocation = _sample_allocation()
    # Position fine but drawdown 10.1% > 10% cap.
    assert is_within_allocation(allocation, position_value_usd=0.0, drawdown_pct=0.101) is False


@pytest.mark.parametrize(
    ("position", "drawdown", "match_dim"),
    [
        (50_001.0, 0.0, "Position"),
        (0.0, 0.101, "Drawdown"),
    ],
)
def test_validate_allocation_respect_raises_on_violation(position: float, drawdown: float, match_dim: str) -> None:
    allocation = _sample_allocation()
    with pytest.raises(AllocationViolationError, match=match_dim):
        validate_allocation_respect(allocation, position, drawdown)


def test_validate_allocation_respect_silent_on_within_envelope() -> None:
    allocation = _sample_allocation()
    # Should not raise.
    validate_allocation_respect(allocation, proposed_position_value_usd=10_000.0, current_drawdown_pct=0.05)


# ---------------------------------------------------------------------------
# Seed-dictionary invariants — coverage guarantee for May-23 cutover
# ---------------------------------------------------------------------------


def test_capital_allocation_seed_non_empty() -> None:
    assert len(CAPITAL_ALLOCATION_SEED) > 0


def test_capital_allocation_seed_covers_carry_archetype_family() -> None:
    """At least one carry archetype must be seeded — this is the May-23 lead."""
    archetypes = {key[1] for key in CAPITAL_ALLOCATION_SEED}
    assert any("carry" in archetype for archetype in archetypes), f"No carry archetype in seed: {archetypes}"


def test_capital_allocation_seed_covers_ml_directional_archetype_family() -> None:
    """At least one ml_directional archetype seeded — CeFi-ML is in May-23 scope."""
    archetypes = {key[1] for key in CAPITAL_ALLOCATION_SEED}
    assert any("ml_directional" in archetype for archetype in archetypes), (
        f"No ml_directional archetype in seed: {archetypes}"
    )


def test_capital_allocation_seed_keys_match_internal_fields() -> None:
    """Every seed key (client_id, archetype, venue) must match the
    CapitalAllocation's stored client_id / archetype / venue. Catches typos
    that would otherwise hide silent lookup mismatches."""
    for (key_client, key_archetype, key_venue), allocation in CAPITAL_ALLOCATION_SEED.items():
        assert allocation.client_id == key_client
        assert allocation.archetype == key_archetype
        assert allocation.venue == key_venue


def test_clients_seed_non_empty() -> None:
    assert len(CLIENTS_SEED) > 0


def test_clients_seed_at_least_one_client_has_four_or_more_venue_accounts() -> None:
    """Live CeFi (Bybit / Deribit / Binance / OKX) means any onboarded client
    in the May-23 cutover slice carries ≥4 venue accounts."""
    assert any(len(client.accounts) >= 4 for client in CLIENTS_SEED), (
        f"No client has >=4 venue accounts in seed: {[(c.client_id, len(c.accounts)) for c in CLIENTS_SEED]}"
    )


def test_get_client_returns_seed_entry() -> None:
    client = get_client("ikenna")
    assert client.client_id == "ikenna"
    assert client.display_name


def test_get_client_raises_for_unknown_client() -> None:
    with pytest.raises(KeyError, match="Unknown client_id"):
        get_client("nonexistent")
