#!/usr/bin/env python3
"""Weekly schema-validation canary: replay UAC VCR cassettes against live APIs.

Walks every VCR cassette in `unified_api_contracts/external/*/mocks/*.yaml`,
replays the first interaction against the live endpoint (subject to a
safe-replay filter), and writes the live response to
`collected_responses/<venue>/<cassette_stem>.json` for the downstream
`validate_schemas.py` step to diff against the cassette baseline.

Safe-replay policy:
- GET requests: replayed unless the path looks private (`/private/`, `/account/`,
  `/order`, `/withdraw`, `/transfer`).
- POST requests: replayed ONLY when (a) the URI path is in a small read-only
  whitelist (`/info`, `/graphql`, `/query`) or starts with `/graphql`, AND
  (b) the body contains no signature/nonce/wallet/secret tokens, AND
  (c) the body's `type` field (if present) is not a write op
  (cancel/order/place/withdraw/transfer/approve).
- Anything with an `Authorization` or `Cookie` header in the cassette is skipped
  (we strip and re-inject our own auth only for whitelisted venues below).
- Stub cassettes (`interactions: []` or `# STUB` banner) are skipped.

Auth-required venues optionally fetch an API key from GCP Secret Manager at
`projects/<GCP_PROJECT_ID>/secrets/uac_canary_<venue>_api_key/versions/latest`
and inject it per venue's auth scheme. Missing secret or missing
`google-cloud-secret-manager` import → BLOCKED-CREDENTIALS skip (not a failure).

Exits 0 always — per-cassette failures are isolated and surfaced via
`validate_schemas.py`. The workflow's drift_check step decides whether to
file an issue.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import importlib

import requests
import yaml

ROOT = Path(__file__).resolve().parent.parent
EXTERNAL_DIR = ROOT / "unified_api_contracts" / "external"
OUTPUT_DIR = ROOT / "collected_responses"

REQUEST_TIMEOUT = 15
USER_AGENT = (
    "uac-weekly-canary/1.0 (+https://github.com/IggyIkenna/unified-api-contracts)"
)

# Read-only URI paths for which POST replay is permitted.
_POST_SAFE_PATHS: set[str] = {"/info", "/graphql", "/v1/graphql", "/query"}

# Sensitive substrings that disqualify a POST body from replay.
_SENSITIVE_BODY_RE = re.compile(
    r'"(signature|private_key|api_secret|secret|nonce|wallet[Aa]ddress|'
    r'vault[Aa]ddress|"r":|"s":|"v":\s*\d+)',
    re.IGNORECASE,
)
_WRITE_TYPE_RE = re.compile(
    r'"type"\s*:\s*"(cancel|order|place|withdraw|transfer|approve|signed)',
    re.IGNORECASE,
)

# Auth headers we always strip from cassette before replay; if the venue is in
# AUTH_CONFIG we re-inject from Secret Manager.
_AUTH_HEADER_NAMES_LOWER = {
    "authorization",
    "x-apisports-key",
    "x-rapidapi-key",
    "x-rapidapi-host",
    "x-mbx-apikey",
    "kc-api-key",
    "kc-api-sign",
    "kc-api-passphrase",
    "kc-api-timestamp",
    "ok-access-key",
    "ok-access-sign",
    "ok-access-passphrase",
    "ok-access-timestamp",
    "bf-app-key",
    "x-bapi-api-key",
    "x-bapi-sign",
    "x-bapi-timestamp",
}

# Venues whose canonical endpoints need an API key. v1 supports a small set of
# injection patterns; complex flows (Betfair session, Matchbook session,
# Polymarket CLOB HMAC) are marked skip_v1.
AUTH_CONFIG: dict[str, dict[str, str]] = {
    "alchemy": {"injection": "url_path", "placeholder": "demo"},
    "api_football": {"injection": "header", "header_name": "x-apisports-key"},
    "fred": {"injection": "query_param", "param": "api_key"},
    "footystats": {"injection": "query_param", "param": "key"},
    "odds_api": {"injection": "query_param", "param": "apiKey"},
    "openbb": {"injection": "header_bearer", "header_name": "Authorization"},
    "soccer_football_info": {
        "injection": "header",
        "header_name": "X-RapidAPI-Key",
    },
    "betfair": {"injection": "skip_v1"},
    "matchbook": {"injection": "skip_v1"},
}


# Venue-specific URI rewriters: cassettes recorded against a specific
# market/condition_id may go stale as the market resolves and disappears.
# Each override callable receives (uri, headers) of the cassette interaction
# and returns a rewritten (uri, headers) targeting a currently-active equivalent.
# Returning the inputs unchanged means "replay as-is".
#
# Polymarket override (rationale 2026-05-20):
#   * /markets/<condition_id> or /market/<id> single-market lookups go 404 once
#     the recorded market resolves. The override redirects to the listing
#     endpoint with active=true&closed=false&limit=1 so the canary always hits
#     a live market shape rather than the resolved 404.
#   * Listing endpoints (/markets?active=true&...) are kept as-is — they're
#     intrinsically rolling.
def _polymarket_override(uri: str, headers: dict[str, str]) -> tuple[str, dict[str, str]]:
    from urllib.parse import urlsplit, urlunsplit

    parts = urlsplit(uri)
    path = parts.path
    # Single-market lookups: /markets/{condition_id} or /market/{id}
    # Match path with exactly one segment after /markets or /market.
    segs = [s for s in path.split("/") if s]
    is_single_market = (
        len(segs) >= 2
        and segs[-2] in ("markets", "market")
        # condition_id / market id are non-empty and not the listing keyword
        and segs[-1]
        and segs[-1] != "markets"
    )
    if is_single_market:
        # Rewrite to listing endpoint that always has live data
        new_path = "/markets"
        new_query = "active=true&closed=false&limit=1"
        new_uri = urlunsplit((parts.scheme, parts.netloc, new_path, new_query, ""))
        return new_uri, headers
    return uri, headers


VENUE_OVERRIDES: dict[str, "object"] = {
    "polymarket": _polymarket_override,
}


@dataclass
class ReplayResult:
    venue: str
    cassette: str
    status: str  # ok | fail | blocked | unsafe | stub
    detail: str = ""
    http_status: int | None = None
    latency_ms: int | None = None


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    cassette_paths = sorted(EXTERNAL_DIR.glob("*/mocks/*.yaml"))
    if not cassette_paths:
        print("No cassettes found — nothing to canary.")
        return 0

    venues = {p.parent.parent.name for p in cassette_paths}
    print(
        f"Found {len(cassette_paths)} cassettes across {len(venues)} venues.",
        flush=True,
    )

    results: list[ReplayResult] = []
    for path in cassette_paths:
        try:
            results.append(_process_cassette(path))
        except Exception as exc:  # noqa: BLE001 — per-cassette isolation
            results.append(
                ReplayResult(
                    venue=path.parent.parent.name,
                    cassette=path.stem,
                    status="fail",
                    detail=f"cassette processing error: {type(exc).__name__}: {exc}",
                )
            )

    _print_results(results)
    return 0


def _process_cassette(path: Path) -> ReplayResult:
    venue = path.parent.parent.name
    stem = path.stem

    # Negative-case cassettes (deliberately test 4xx/5xx) and internal-only
    # health probes are out of scope for a public-API drift canary.
    if stem.startswith("error_") or stem.endswith("_health"):
        return ReplayResult(venue, stem, "unsafe", f"non-canary cassette: {stem}")

    text = path.read_text(encoding="utf-8")
    if text.lstrip().startswith("# STUB"):
        return ReplayResult(venue, stem, "stub", "stub cassette")

    cassette = yaml.safe_load(text)
    interactions = ((cassette or {}).get("interactions")) or []
    if not interactions:
        return ReplayResult(venue, stem, "stub", "empty interactions")

    interaction = interactions[0]
    # Skip cassettes whose recorded response was itself an error — the baseline
    # has nothing to drift-validate against.
    recorded_status = (
        ((interaction.get("response") or {}).get("status") or {}).get("code")
    )
    if isinstance(recorded_status, int) and recorded_status >= 400:
        return ReplayResult(
            venue, stem, "unsafe", f"recorded baseline is HTTP {recorded_status}"
        )

    # Skip cassettes whose URI host is non-public (internal k8s services etc.).
    uri = (interaction.get("request") or {}).get("uri") or ""
    host = urlsplit(uri).hostname or ""
    if host and ("." not in host or host.startswith("localhost")):
        return ReplayResult(venue, stem, "unsafe", f"non-public host: {host}")

    return _replay_one(venue, stem, interaction)


def _replay_one(venue: str, stem: str, interaction: dict[str, Any]) -> ReplayResult:
    request = interaction.get("request") or {}
    method = (request.get("method") or "GET").upper()
    uri = request.get("uri") or ""
    body = request.get("body")
    headers_raw = request.get("headers") or {}

    if not uri:
        return ReplayResult(venue, stem, "fail", "no uri in cassette")

    safe, reason = _is_safe_to_replay(method, uri, body, headers_raw)
    if not safe:
        return ReplayResult(venue, stem, "unsafe", reason)

    headers = _normalize_headers(headers_raw)
    for h in list(headers.keys()):
        if h.lower() in _AUTH_HEADER_NAMES_LOWER:
            del headers[h]
    headers["User-Agent"] = USER_AGENT

    # Apply venue-specific URI/header rewriter (e.g. roll a stale Polymarket
    # condition_id to the live-listing endpoint so resolved markets don't 404).
    override = VENUE_OVERRIDES.get(venue)
    if override is not None:
        uri, headers = override(uri, headers)

    auth_cfg = AUTH_CONFIG.get(venue)
    if auth_cfg:
        injection = auth_cfg["injection"]
        if injection == "skip_v1":
            return ReplayResult(venue, stem, "blocked", "complex auth not supported in v1")
        api_key = _fetch_api_key(venue)
        if api_key is None:
            return ReplayResult(
                venue, stem, "blocked", "API key not in Secret Manager"
            )
        uri, headers = _inject_auth(uri, headers, auth_cfg, api_key)

    t0 = time.monotonic()
    try:
        resp = requests.request(
            method=method,
            url=uri,
            data=body if method != "GET" and body else None,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )
        latency_ms = int((time.monotonic() - t0) * 1000)
    except requests.RequestException as exc:
        return ReplayResult(
            venue, stem, "fail", f"network: {type(exc).__name__}: {exc}"
        )

    venue_dir = OUTPUT_DIR / venue
    venue_dir.mkdir(parents=True, exist_ok=True)
    try:
        resp_body: Any = resp.json()
    except ValueError:
        resp_body = resp.text[:5000]

    payload: dict[str, Any] = {
        "venue": venue,
        "cassette": stem,
        "request": {"method": method, "uri": uri, "body": body},
        "response_status": resp.status_code,
        "response_body": resp_body,
        "latency_ms": latency_ms,
        "fetched_at": int(time.time()),
    }
    (venue_dir / f"{stem}.json").write_text(json.dumps(payload, indent=2, default=str))

    if resp.status_code >= 400:
        detail_excerpt = json.dumps(resp_body)[:200] if not isinstance(resp_body, str) else resp_body[:200]
        return ReplayResult(
            venue,
            stem,
            "fail",
            f"http {resp.status_code}: {detail_excerpt}",
            http_status=resp.status_code,
            latency_ms=latency_ms,
        )

    return ReplayResult(
        venue, stem, "ok", "", http_status=resp.status_code, latency_ms=latency_ms
    )


def _is_safe_to_replay(
    method: str, uri: str, body: Any, headers_raw: dict[str, Any]
) -> tuple[bool, str]:
    for h in headers_raw:
        if h.lower() in {"authorization", "cookie"}:
            return False, "cassette has Authorization/Cookie header (auth required)"

    path = urlsplit(uri).path.lower()

    if method == "GET":
        for needle in ("/private/", "/account/", "/order", "/withdraw", "/transfer"):
            if needle in path:
                return False, f"GET to non-public path: {path}"
        return True, ""

    if method == "POST":
        if path not in _POST_SAFE_PATHS and not path.startswith("/graphql"):
            return False, f"POST to non-readonly path: {path}"
        body_str = (
            body
            if isinstance(body, str)
            else json.dumps(body, default=str)
            if body is not None
            else ""
        )
        if _SENSITIVE_BODY_RE.search(body_str):
            return False, "POST body contains sensitive token"
        if _WRITE_TYPE_RE.search(body_str):
            return False, "POST body has write-op type"
        return True, ""

    return False, f"method {method} not whitelisted"


def _normalize_headers(headers_raw: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for k, v in headers_raw.items():
        if isinstance(v, list):
            out[k] = ", ".join(str(x) for x in v) if v else ""
        else:
            out[k] = str(v)
    return out


def _fetch_api_key(venue: str) -> str | None:
    project_id = os.environ.get("GCP_PROJECT_ID")
    if not project_id:
        return None
    try:
        secretmanager = importlib.import_module("google.cloud.secretmanager")
    except ImportError:
        return None
    secret_name = (
        f"projects/{project_id}/secrets/uac_canary_{venue}_api_key/versions/latest"
    )
    try:
        client = secretmanager.SecretManagerServiceClient()
        resp = client.access_secret_version(name=secret_name)
        return resp.payload.data.decode("utf-8")
    except Exception:
        return None


def _inject_auth(
    uri: str, headers: dict[str, str], auth_cfg: dict[str, str], api_key: str
) -> tuple[str, dict[str, str]]:
    injection = auth_cfg["injection"]
    if injection == "header":
        headers[auth_cfg["header_name"]] = api_key
    elif injection == "header_bearer":
        headers[auth_cfg["header_name"]] = f"Bearer {api_key}"
    elif injection == "query_param":
        sep = "&" if "?" in uri else "?"
        uri = f"{uri}{sep}{auth_cfg['param']}={api_key}"
    elif injection == "url_path":
        uri = uri.replace(auth_cfg["placeholder"], api_key, 1)
    return uri, headers


def _print_results(results: list[ReplayResult]) -> None:
    icons = {"ok": "✅", "fail": "❌", "blocked": "⏭️ ", "unsafe": "⏭️ ", "stub": "⏭️ "}
    counts = {k: 0 for k in icons}
    for r in results:
        counts[r.status] += 1
        icon = icons.get(r.status, "?")
        if r.status == "ok":
            suffix = f" ({r.http_status} {r.latency_ms}ms)"
        elif r.detail:
            suffix = f" — {r.detail}"
        else:
            suffix = ""
        print(f"{icon} {r.venue}/{r.cassette}{suffix}", flush=True)
    print(flush=True)
    print(
        f"Summary: {counts['ok']} ✅ / {counts['fail']} ❌ / "
        f"{counts['blocked']} blocked / {counts['unsafe']} unsafe / {counts['stub']} stub",
        flush=True,
    )


if __name__ == "__main__":
    sys.exit(main())
