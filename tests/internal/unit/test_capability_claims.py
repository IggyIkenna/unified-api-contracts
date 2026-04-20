"""Tests for CapabilityClaims Firebase custom-claims schema.

Stage 3E G2 § 4. Canonical shape of the Odum-controlled claims on
every Firebase Auth user. Tests pin the shape so the Cloud Function
writer and Python + TS readers can't drift.

SSOT: codex/14-playbooks/infra-spec/stage-3e-g2-env-split.md § 4.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from unified_api_contracts.internal.architecture_v2 import CapabilityClaims


def test_minimal_claims_default_locked_down() -> None:
    claims = CapabilityClaims(role="viewer", audience="trading_platform_subscriber")
    assert claims.pricing_read_internal is False
    assert claims.strategy_catalogue_admin is False
    assert claims.im_desk is False
    assert claims.admin is False
    assert claims.org_id is None


def test_admin_claims_roundtrip_via_model_dump() -> None:
    """``model_dump()`` output is what ``auth.set_custom_user_claims(uid, ...)`` receives."""

    claims = CapabilityClaims(
        role="admin",
        audience="admin",
        org_id=None,
        pricing_read_internal=True,
        strategy_catalogue_admin=True,
        im_desk=True,
        admin=True,
    )
    payload = claims.model_dump()
    assert payload["role"] == "admin"
    assert payload["audience"] == "admin"
    assert payload["pricing_read_internal"] is True
    assert payload["admin"] is True


def test_rejects_unknown_audience() -> None:
    with pytest.raises(ValidationError):
        CapabilityClaims(role="viewer", audience="superuser")  # pyright: ignore[reportArgumentType]


def test_rejects_extra_claims() -> None:
    """``extra='forbid'`` prevents rogue claims landing in the ID token by mistake."""

    with pytest.raises(ValidationError):
        CapabilityClaims(  # pyright: ignore[reportCallIssue]
            role="viewer",
            audience="im_client",
            secret_feature_flag=True,  # pyright: ignore[reportCallIssue]
        )


def test_client_claims_carry_org_id() -> None:
    claims = CapabilityClaims(
        role="client",
        audience="trading_platform_subscriber",
        org_id="alpha-capital",
        im_desk=False,
        admin=False,
    )
    assert claims.org_id == "alpha-capital"


def test_claims_are_frozen() -> None:
    claims = CapabilityClaims(role="viewer", audience="im_client")
    with pytest.raises(ValidationError):
        claims.admin = True  # pyright: ignore[reportAttributeAccessIssue]
