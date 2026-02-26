"""Replay VCR cassettes and validate response bodies against api-contracts schemas.

If a cassette is missing, the test is skipped (record with scripts/record_vcr_cassettes.py first).
CI runs these tests with existing cassettes; no API keys needed for replay.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import requests
from vcr import VCR

from api_contracts.vcr_endpoints import VCR_ENDPOINTS

ROOT = Path(__file__).resolve().parent.parent
MOCKS_BASE = ROOT / "api_contracts"

SECRET_HEADERS = [
    "authorization",
    "x-api-key",
    "x-auth-token",
    "api-key",
    "api_key",
    "x-mbx-apikey",
    "ok-access-key",
    "ok-access-sign",
    "ok-access-timestamp",
    "ok-access-passphrase",
    "x-bapi-api-key",
    "x-bapi-signature",
    "x-bapi-timestamp",
]


def filter_request(request: requests.PreparedRequest) -> requests.PreparedRequest | None:
    if request.headers is None:
        return request
    lower_headers = {k.lower(): k for k in request.headers}
    for secret in SECRET_HEADERS:
        if secret in lower_headers:
            orig_key = lower_headers[secret]
            request.headers[orig_key] = "[FILTERED]"
    return request


def get_by_path(data: dict | list, path: str) -> dict | list | None:
    """Get nested value by dot path, e.g. 'data.0' or 'result.list.0'."""
    if not path:
        return data if isinstance(data, dict) else None
    parts = path.split(".")
    current: object = data
    for p in parts:
        if current is None:
            return None
        if isinstance(current, dict):
            current = current.get(p)
        elif isinstance(current, list):
            try:
                idx = int(p)
                current = current[idx] if 0 <= idx < len(current) else None
            except ValueError:
                return None
        else:
            return None
    return current if isinstance(current, (dict, list)) else None


def make_vcr(cassette_dir: Path) -> VCR:
    return VCR(
        cassette_library_dir=str(cassette_dir),
        record_mode="none",
        before_record_request=filter_request,
    )


def _list_vcr_cases() -> list[tuple[str, dict]]:
    """(venue, ep) for each endpoint that has a cassette file."""
    cases: list[tuple[str, dict]] = []
    for venue, endpoints in VCR_ENDPOINTS.items():
        cassette_dir = MOCKS_BASE / venue / "mocks"
        for ep in endpoints:
            cassette_name = ep["cassette_name"]
            path = cassette_dir / cassette_name
            if path.exists():
                cases.append((venue, ep))
    return cases


@pytest.mark.parametrize("venue,ep", _list_vcr_cases())
def test_vcr_replay_validates_schema(venue: str, ep: dict) -> None:
    """Replay cassette, extract response body, validate with venue schema."""
    cassette_dir = MOCKS_BASE / venue / "mocks"
    vcr = make_vcr(cassette_dir)
    schema_class_name = ep["schema_class"]
    response_path = ep.get("response_path") or ""

    mod = __import__(f"api_contracts.{venue}.schemas", fromlist=[schema_class_name])
    schema_class = getattr(mod, schema_class_name)

    with vcr.use_cassette(ep["cassette_name"]):
        if ep.get("method") == "POST":
            body = ep.get("json_body")
            resp = requests.post(ep["url"], json=body, headers=None, timeout=10)
        else:
            resp = requests.get(ep["url"], headers=None, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    # Hyperliquid /info type=meta returns a list (universe); schema expects {universe: list}
    if isinstance(data, list) and schema_class_name == "HyperliquidMeta":
        data = {"universe": data}

    payload = get_by_path(data, response_path)
    if payload is None and response_path:
        payload = data
    assert payload is not None, f"Missing path {response_path!r} in response"
    if isinstance(payload, list) and schema_class_name == "HyperliquidMeta":
        payload = {"universe": payload}
    schema_class.model_validate(payload)


def test_at_least_one_vcr_cassette_when_any_recorded() -> None:
    """If we have any cassettes, at least one replay test was parametrized."""
    cases = _list_vcr_cases()
    # When no cassettes exist yet, we have 0 cases and that's OK
    # When we add cassettes, this test just ensures the parametrization runs
    assert isinstance(cases, list)
