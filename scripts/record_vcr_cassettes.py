#!/usr/bin/env -S uv run python
"""
Record VCR cassettes for api_contracts/<venue>/mocks/ by performing live requests.

Secrets are filtered from recorded request headers (Authorization, X-API-Key, etc.).
Run once with network access; commit cassettes so CI can replay without keys.

Usage:
  uv run python scripts/record_vcr_cassettes.py [--venue binance|okx|...]
  If --venue omitted, records all venues that have VCR_ENDPOINTS and (when key_env set) env var set.

Requires: requests, vcrpy (dev deps). For key-based venues set e.g. TARDIS_API_KEY.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import requests
from vcr import VCR

# Project root
ROOT = Path(__file__).resolve().parent.parent
MOCKS_BASE = ROOT / "api_contracts"

# Headers to replace with [FILTERED] in cassettes (case-insensitive match)
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
    """Replace secret headers with [FILTERED] before recording."""
    if request.headers is None:
        return request
    lower_headers = {k.lower(): k for k in request.headers}
    for secret in SECRET_HEADERS:
        if secret in lower_headers:
            orig_key = lower_headers[secret]
            request.headers[orig_key] = "[FILTERED]"
    return request


def make_vcr(cassette_dir: Path) -> VCR:
    return VCR(
        cassette_library_dir=str(cassette_dir),
        record_mode="once",
        before_record_request=filter_request,
    )


def run() -> int:
    parser = argparse.ArgumentParser(description="Record VCR cassettes for api-contracts venues")
    parser.add_argument("--venue", type=str, help="Record only this venue (default: all)")
    args = parser.parse_args()

    # Import after potential path setup
    from api_contracts.vcr_endpoints import VCR_ENDPOINTS

    venues = [args.venue] if args.venue else list(VCR_ENDPOINTS.keys())
    recorded = 0
    skipped_no_key = 0
    errors: list[str] = []

    for venue in venues:
        if venue not in VCR_ENDPOINTS:
            errors.append(f"Unknown venue: {venue}")
            continue
        endpoints = VCR_ENDPOINTS[venue]
        if not endpoints:
            continue
        cassette_dir = MOCKS_BASE / venue / "mocks"
        cassette_dir.mkdir(parents=True, exist_ok=True)
        vcr = make_vcr(cassette_dir)

        for ep in endpoints:
            key_env = ep.get("key_env") or ""
            if key_env and not os.environ.get(key_env):
                skipped_no_key += 1
                continue
            headers: dict[str, str] = {}
            if key_env and os.environ.get(key_env):
                header_name = ep.get("header_name") or "Authorization"
                key = os.environ.get(key_env)
                if header_name.lower() == "authorization" and key and not key.startswith("Bearer "):
                    headers["Authorization"] = f"Bearer {key}"
                else:
                    headers[header_name] = key or ""

            cassette_name = ep["cassette_name"]
            with vcr.use_cassette(cassette_name):
                try:
                    if ep.get("method") == "POST":
                        body = ep.get("json_body")
                        resp = requests.post(ep["url"], json=body, headers=headers or None, timeout=30)
                    else:
                        resp = requests.get(ep["url"], headers=headers or None, timeout=30)
                    resp.raise_for_status()
                    recorded += 1
                    print(f"Recorded {venue}/{cassette_name}")
                except Exception as e:
                    errors.append(f"{venue}/{cassette_name}: {e}")

    if errors:
        for e in errors:
            print(e, file=sys.stderr)
    print(f"Recorded {recorded} cassette(s), skipped {skipped_no_key} (no key), {len(errors)} error(s).")
    return 0 if recorded > 0 else 1


if __name__ == "__main__":
    sys.exit(run())
