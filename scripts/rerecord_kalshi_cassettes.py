#!/usr/bin/env python3
# Epic: infrastructure_master
# Lifecycle: permanent
# Delete-when: NA
"""Re-record the Kalshi `markets.yaml` / `market_lookup.yaml` VCR cassettes against live data.

Why this exists
----------------
`scripts/validate_schemas.py` diffs a live API response against the cassette's OWN recorded
response body as the "expected shape" baseline (`markets.yaml`, `market_lookup.yaml` under
`unified_api_contracts/external/kalshi/mocks/`). When Kalshi's real API shape moves on (it has:
integer cent fields / bare `subtitle` / bare `liquidity` were removed after March 2026 in favor of
`*_dollars` fields + `yes_sub_title`/`no_sub_title`), the cassette goes stale and the weekly
`weekly-validation.yml` canary reports a false-positive DRIFT forever, even after the real schema
(`KalshiMarket` in `schemas.py`) has already been updated to match reality. Root-caused + fixed once
(2026-07-26, see `plans/active/issues/quickmerge_agent_files_pure_deletion_gap_2026_07_26.md`'s sibling
finding in the same session) — this script exists so the NEXT drift doesn't need the same investigation.

Two traps this script avoids (found the hard way — re-introduce them and the fix silently regresses)
------------------------------------------------------------------------------------------------------
1. `markets.yaml`'s recorded request URI must be `?limit=1&status=open` EXACTLY (no `series_ticker`
   filter) — `tests/vcr/test_kalshi_vcr.py` replays that exact query via vcrpy, which matches
   cassette interactions by exact request URI. A `series_ticker` filter makes the cassette
   deterministic (avoids landing on an unrepresentative multi-leg combo market) but BREAKS the local
   VCR replay tests, which don't pass that filter. Ship it broad-query, not narrowed.
2. `market_lookup.yaml`'s pinned ticker WILL expire (Kalshi markets close) — re-run this script
   periodically, not just once. It always re-pins to the CURRENT top result of the plain
   `?limit=1&status=open` query, so re-running naturally rotates to a fresh, non-expired ticker.

Usage
-----
    cd unified-api-contracts && uv run python scripts/rerecord_kalshi_cassettes.py

Then verify: `uv run python scripts/validate_schemas.py 2>&1 | grep kalshi` (expect both ✅) and
`uv run pytest tests/vcr/test_kalshi_vcr.py -v` (expect 4 passed).
"""

from __future__ import annotations

import json
import urllib.request
from typing import Any

import yaml

_MARKETS_URI = "https://api.elections.kalshi.com/trade-api/v2/markets?limit=1&status=open"
_CASSETTE_DIR = "unified_api_contracts/external/kalshi/mocks"


def _fetch(url: str) -> tuple[str, dict[str, str], int]:
    req = urllib.request.Request(  # noqa: S310 — fixed https Kalshi host, GET-only, no auth
        url, headers={"Accept": "*/*", "User-Agent": "python-requests/2.32.5"}
    )
    with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310 — see above
        return resp.read().decode("utf-8"), dict(resp.headers), resp.status


def _build_cassette(
    uri: str, headers_req: dict[str, list[str]], body_str: str, content_type: str
) -> dict[str, Any]:
    return {
        "interactions": [
            {
                "request": {"body": None, "headers": headers_req, "method": "GET", "uri": uri},
                "response": {
                    "body": {"string": body_str},
                    "headers": {"Content-Type": [content_type]},
                    "status": {"code": 200, "message": "OK"},
                },
            }
        ],
        "version": 1,
    }


def main() -> None:
    body, hdrs, status = _fetch(_MARKETS_URI)
    if status != 200:
        msg = f"Kalshi markets endpoint returned {status}, refusing to record a broken cassette"
        raise RuntimeError(msg)
    market = json.loads(body)["markets"][0]
    cassette = _build_cassette(
        _MARKETS_URI,
        {
            "Accept": ["*/*"],
            "Accept-Encoding": ["gzip, deflate"],
            "Connection": ["keep-alive"],
            "User-Agent": ["python-requests/2.32.5"],
        },
        body,
        hdrs.get("Content-Type", "application/json"),
    )
    with open(f"{_CASSETTE_DIR}/markets.yaml", "w") as f:
        yaml.dump(cassette, f, default_flow_style=False, sort_keys=True, width=100000)
    print(f"wrote markets.yaml, ticker={market['ticker']} close_time={market.get('close_time')}")

    ticker = market["ticker"]
    lookup_uri = f"https://api.elections.kalshi.com/trade-api/v2/markets/{ticker}"
    body2, hdrs2, status2 = _fetch(lookup_uri)
    if status2 != 200:
        msg = f"Kalshi market_lookup for {ticker!r} returned {status2}, refusing to record a broken cassette"
        raise RuntimeError(msg)
    cassette2 = _build_cassette(
        lookup_uri,
        {"Accept": ["*/*"], "User-Agent": ["python-urllib/3.13"]},
        body2,
        hdrs2.get("Content-Type", "application/json"),
    )
    with open(f"{_CASSETTE_DIR}/market_lookup.yaml", "w") as f:
        yaml.dump(cassette2, f, default_flow_style=False, sort_keys=True, width=100000)
    print(f"wrote market_lookup.yaml, ticker={ticker}")


if __name__ == "__main__":
    main()
