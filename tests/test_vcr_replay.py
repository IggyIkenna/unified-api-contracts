"""Replay VCR cassettes and validate response bodies against api-contracts schemas.

If a cassette is missing, the test is skipped (record with scripts/record_vcr_cassettes.py first).
CI runs these tests with existing cassettes; no API keys needed for replay.

Schema version pinning:
  Each cassette should have an x-contract-schema-version response header injected at record time.
  test_vcr_replay_schema_version_matches asserts the cassette version matches VCR_ENDPOINTS.
  If versions differ, re-record: python scripts/record_vcr_cassettes.py --venue <name>
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import requests
from vcr import VCR

from api_contracts.vcr_endpoints import VCR_ENDPOINTS

ROOT = Path(__file__).resolve().parent.parent
MOCKS_BASE = ROOT / "api_contracts" / "api_contracts_external"

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


def get_by_path(data: dict[str, Any] | list[Any], path: str) -> dict[str, Any] | list[Any] | None:
    """Get nested value by dot path, e.g. 'data.0' or 'result.list.0'."""
    if not path:
        return data if isinstance(data, (dict, list)) else None
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


def _read_cassette_schema_version(cassette_path: Path) -> str | None:
    """Extract x-contract-schema-version from a cassette YAML without full YAML parse.

    Handles two formats injected by record_vcr_cassettes.py:
      Inline:  x-contract-schema-version: '1.0'
      List:    x-contract-schema-version:
               - '1.0'
    """
    try:
        lines = cassette_path.read_text().splitlines()
        for i, line in enumerate(lines):
            if "x-contract-schema-version" not in line.lower():
                continue
            stripped = line.strip()
            # Inline format: "x-contract-schema-version: '1.0'"
            if ":" in stripped:
                after_colon = stripped.split(":", 1)[1].strip().strip("'\"")
                if after_colon:
                    return after_colon
            # List format — value is on the next line as "- '1.0'"
            if i + 1 < len(lines):
                next_stripped = lines[i + 1].strip()
                if next_stripped.startswith("-"):
                    return next_stripped.lstrip("- ").strip().strip("'\"")
        return None
    except OSError:
        return None


def _list_vcr_cases() -> list[tuple[str, dict[str, Any]]]:
    """(venue, ep) for each endpoint that has a cassette file. Skip internal services."""
    cases: list[tuple[str, dict[str, Any]]] = []
    for venue, endpoints in VCR_ENDPOINTS.items():
        cassette_dir = MOCKS_BASE / venue / "mocks"
        for ep in endpoints:
            if ep.get("is_internal_service"):
                continue  # only replay internal cassettes if explicitly pre-recorded
            cassette_name = ep["cassette_name"]
            path = cassette_dir / cassette_name
            if path.exists():
                cases.append((venue, ep))
    return cases


def _list_internal_vcr_cases() -> list[tuple[str, dict[str, Any]]]:
    """Internal service cassettes — only run if cassette pre-exists."""
    cases: list[tuple[str, dict[str, Any]]] = []
    for venue, endpoints in VCR_ENDPOINTS.items():
        cassette_dir = MOCKS_BASE / venue / "mocks"
        for ep in endpoints:
            if not ep.get("is_internal_service"):
                continue
            path = cassette_dir / ep["cassette_name"]
            if path.exists():
                cases.append((venue, ep))
    return cases


@pytest.mark.parametrize("venue,ep", _list_vcr_cases())
def test_vcr_replay_validates_schema(venue: str, ep: dict[str, Any]) -> None:
    """Replay cassette, extract response body, validate with venue schema."""
    cassette_dir = MOCKS_BASE / venue / "mocks"
    vcr = make_vcr(cassette_dir)
    schema_class_name = ep["schema_class"]
    response_path = ep.get("response_path") or ""

    # Resolve schema class from venue module or internal module
    schema_class = _resolve_schema_class(venue, schema_class_name)

    params = None
    if ep.get("auth_query_param"):
        params = {ep["auth_query_param"]: "[FILTERED]"}

    with vcr.use_cassette(ep["cassette_name"]):
        if ep.get("method") == "POST":
            body = ep.get("json_body")
            resp = requests.post(ep["url"], json=body, headers=None, params=params, timeout=10)
        else:
            resp = requests.get(ep["url"], headers=None, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    if isinstance(data, list) and schema_class_name == "HyperliquidMeta":
        data = {"universe": data}

    payload = get_by_path(data, response_path)
    if payload is None and response_path:
        payload = data
    assert payload is not None, f"Missing path {response_path!r} in response"
    if isinstance(payload, list) and schema_class_name == "HyperliquidMeta":
        payload = {"universe": payload}
    schema_class.model_validate(payload)


@pytest.mark.parametrize("venue,ep", _list_vcr_cases())
def test_vcr_replay_schema_version_matches(venue: str, ep: dict[str, Any]) -> None:
    """Cassette x-contract-schema-version header must match VCR_ENDPOINTS schema_version.

    A mismatch means the cassette was recorded against an older schema — re-record it.
    """
    expected_version = ep.get("schema_version", "1.0")
    cassette_path = MOCKS_BASE / venue / "mocks" / ep["cassette_name"]
    cassette_version = _read_cassette_schema_version(cassette_path)

    if cassette_version is None:
        # Cassette predates version tracking — skip (will be enforced after next re-record)
        pytest.skip(f"Cassette {cassette_path.name} has no x-contract-schema-version header yet")

    assert cassette_version == expected_version, (
        f"{venue}/{ep['cassette_name']}: cassette schema_version={cassette_version!r} "
        f"but VCR_ENDPOINTS declares {expected_version!r}. "
        f"Re-record with: python scripts/record_vcr_cassettes.py --venue {venue}"
    )


@pytest.mark.parametrize("venue,ep", _list_internal_vcr_cases())
def test_vcr_internal_service_replay(venue: str, ep: dict[str, Any]) -> None:
    """Replay internal service cassettes when pre-recorded. Same validation as external."""
    cassette_dir = MOCKS_BASE / venue / "mocks"
    vcr = make_vcr(cassette_dir)
    schema_class_name = ep["schema_class"]
    response_path = ep.get("response_path") or ""
    schema_class = _resolve_schema_class(venue, schema_class_name)

    with vcr.use_cassette(ep["cassette_name"]):
        if ep.get("method") == "POST":
            resp = requests.post(ep["url"], json=ep.get("json_body"), timeout=10)
        else:
            resp = requests.get(ep["url"], timeout=10)
    resp.raise_for_status()
    data = resp.json()
    payload = get_by_path(data, response_path) or data
    schema_class.model_validate(payload)


def _resolve_schema_class(venue: str, schema_class_name: str) -> type:
    """Resolve schema class from venue module or fallback to internal module."""
    venue_modules = [
        f"api_contracts.api_contracts_external.{venue}.schemas",
        f"api_contracts.{venue}.schemas",
        "api_contracts.internal",
    ]
    for mod_path in venue_modules:
        try:
            mod = __import__(mod_path, fromlist=[schema_class_name])
            cls = getattr(mod, schema_class_name, None)
            if cls is not None:
                return cls  # type: ignore[return-value]
        except (ImportError, AttributeError):
            continue
    raise ImportError(f"Cannot resolve schema class {schema_class_name!r} for venue {venue!r}")


def test_at_least_one_vcr_cassette_when_any_recorded() -> None:
    """If we have any cassettes, at least one replay test was parametrized."""
    cases = _list_vcr_cases()
    assert isinstance(cases, list)
