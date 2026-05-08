"""Tests for ClientContract Firestore document schema.

Stage 3E G2 § 2 — the schema stored under Firestore
``/contracts/{org_id}``. Tests pin the shape so mocks (dev cache),
staging Firebase, and prod Firebase can't drift. Concrete Firebase
project IDs are resolved at runtime via ``UnifiedCloudConfig`` (never
hardcoded); see SSOT below.

SSOT: codex/16-strategy-playbooks/infra-spec/stage-3e-g2-env-split.md § 2.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from unified_api_contracts.internal.architecture_v2 import (
    ClientContract,
    CommercialPath,
)


def _minimal_contract(**overrides: object) -> ClientContract:
    base: dict[str, object] = {
        "org_id": "alpha-capital",
        "audience": "trading_platform_subscriber",
        "commercial_path": CommercialPath.CLIENT_FULL_PIPELINE,
        "tier": "tier_b",
        "effective_from": "2026-05-01",
        "contract_version": "2026-05.v1",
        "signed_by": "admin@odum-research.com",
    }
    base.update(overrides)
    return ClientContract(**base)  # pyright: ignore[reportArgumentType]


def test_client_contract_minimal_happy_path() -> None:
    contract = _minimal_contract()
    assert contract.org_id == "alpha-capital"
    assert contract.tier == "tier_b"
    assert contract.effective_to is None
    assert contract.has_exclusivity is False
    assert contract.pricing_overrides == {}


def test_client_contract_rejects_unknown_field() -> None:
    """``extra='forbid'`` prevents Firestore schema drift."""

    with pytest.raises(ValidationError):
        ClientContract(  # pyright: ignore[reportCallIssue]
            org_id="beta",
            audience="im_client",
            commercial_path=CommercialPath.IM_REPORTING_ONLY,
            tier="tier_a",
            effective_from="2026-05-01",
            contract_version="2026-05.v1",
            signed_by="admin@odum-research.com",
            mystery_field="nope",  # pyright: ignore[reportCallIssue]
        )


def test_client_contract_rejects_bad_tier() -> None:
    with pytest.raises(ValidationError):
        _minimal_contract(tier="gold")


def test_client_contract_rejects_bad_audience() -> None:
    with pytest.raises(ValidationError):
        _minimal_contract(audience="superuser")


def test_client_contract_with_exclusivity_and_overrides() -> None:
    contract = _minimal_contract(
        has_exclusivity=True,
        pricing_overrides={"block_1_reporting_core": "0", "discount_percent": "15"},
        effective_to="2027-05-01",
    )
    assert contract.has_exclusivity is True
    assert contract.pricing_overrides["discount_percent"] == "15"
    assert contract.effective_to == "2027-05-01"


def test_client_contract_is_frozen() -> None:
    """Contracts must be immutable at runtime to prevent drift between Firestore read + cost()."""

    contract = _minimal_contract()
    with pytest.raises(ValidationError):
        contract.tier = "tier_a"  # pyright: ignore[reportAttributeAccessIssue]
