"""Test that every venue's schemas match the venue manifest: REST/WebSocket/FIX and schema classes.

Ensures we can actually use the contracts: each venue exports the response and error types we claim.
"""

from __future__ import annotations

import importlib

import pytest

from unified_api_contracts.external.venue_manifest import VENUE_MANIFEST


def _schemas_module_for_venue(venue: str) -> str:
    """Return the schemas module path for a venue from the manifest."""
    contract = VENUE_MANIFEST[venue]
    return contract.get("module", f"unified_api_contracts.{venue}.schemas")


@pytest.mark.parametrize("venue", list(VENUE_MANIFEST))
def test_venue_schemas_module_imports(venue: str) -> None:
    """Every venue in the manifest must have an importable schemas module."""
    mod_path = _schemas_module_for_venue(venue)
    mod = importlib.import_module(mod_path)
    assert mod is not None


@pytest.mark.parametrize("venue", list(VENUE_MANIFEST))
def test_venue_has_claimed_response_schemas(venue: str) -> None:
    """Every response schema class listed in the manifest must exist in the venue's schemas module."""
    manifest = VENUE_MANIFEST[venue]
    expected = manifest["response_schema_classes"]
    if not expected:
        return
    mod_path = _schemas_module_for_venue(venue)
    mod = importlib.import_module(mod_path)
    missing = [c for c in expected if not hasattr(mod, c)]
    assert not missing, f"{venue}: missing response schema classes: {missing}"


@pytest.mark.parametrize("venue", list(VENUE_MANIFEST))
def test_venue_has_claimed_error_schemas(venue: str) -> None:
    """Every error schema class listed in the manifest must exist in the venue's schemas module."""
    manifest = VENUE_MANIFEST[venue]
    expected = manifest.get("error_schema_classes", [])
    if not expected:
        return
    mod_path = _schemas_module_for_venue(venue)
    mod = importlib.import_module(mod_path)
    missing = [c for c in expected if not hasattr(mod, c)]
    assert not missing, f"{venue}: missing error schema classes: {missing}"


def test_manifest_has_rest_websocket_fix_per_venue() -> None:
    """Every external venue in the manifest must declare has_rest, has_websocket, has_fix."""
    for venue, contract in VENUE_MANIFEST.items():
        if contract.get("is_internal", False):
            continue
        assert "has_rest" in contract, f"{venue}: missing has_rest"
        assert "has_websocket" in contract, f"{venue}: missing has_websocket"
        assert "has_fix" in contract, f"{venue}: missing has_fix"
        assert isinstance(contract["has_rest"], bool), f"{venue}: has_rest must be bool"
        assert isinstance(contract["has_websocket"], bool), f"{venue}: has_websocket must be bool"
        assert isinstance(contract["has_fix"], bool), f"{venue}: has_fix must be bool"


def test_manifest_venues_match_api_contracts_dirs() -> None:
    """Every venue in the manifest must have an importable schemas module."""
    for venue, contract in VENUE_MANIFEST.items():
        mod_path = contract.get("module", f"unified_api_contracts.{venue}.schemas")
        mod = importlib.import_module(mod_path)
        assert mod is not None, f"{venue}: cannot import {mod_path}"


def test_at_least_one_venue_has_rest() -> None:
    """At least one venue must claim REST (sanity check)."""
    rest_count = sum(1 for c in VENUE_MANIFEST.values() if c.get("has_rest", False))
    assert rest_count >= 1, "Manifest should have at least one venue with has_rest=True"


def test_at_least_one_venue_has_websocket() -> None:
    """At least one venue must claim WebSocket (sanity check)."""
    ws_count = sum(1 for c in VENUE_MANIFEST.values() if c.get("has_websocket", False))
    assert ws_count >= 1, "Manifest should have at least one venue with has_websocket=True"
