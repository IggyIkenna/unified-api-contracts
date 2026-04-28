"""Schema health tests: replay every cassette in UAC mocks/ and validate response bodies.

Marked @pytest.mark.integration so they don't run in the default fast test suite.
Run explicitly with:
    pytest tests/vcr/test_schema_health.py -m integration -v

These tests are the UAC-side counterpart to interface-repo recording sessions.
Interface repos record cassettes (they hold API keys) and PR the YAML files here.
UAC CI replays the cassettes and validates schema shape — no live network needed.

If a cassette is missing, the test is skipped.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml as pyyaml

REPO_ROOT = Path(__file__).resolve().parents[2]
EXTERNAL_DIR = REPO_ROOT / "unified_api_contracts" / "external"
YAML_PATH = REPO_ROOT / "unified_api_contracts" / "provider_api_versions.yaml"

pytestmark = pytest.mark.integration


def _load_manifest() -> dict[str, Any]:
    with YAML_PATH.open() as fh:
        return pyyaml.safe_load(fh).get("providers", {})


def _read_cassette_body(cassette_path: Path) -> Any:
    """Return the first response body from a VCR YAML cassette.

    JSON objects are parsed with :func:`json.loads`. Non-JSON strings (including
    explicit ``string: ""``) are returned as-is — empty bodies are used for
    binary/gzip/DBN stubs that intentionally record no bytes in YAML.
    """
    with cassette_path.open(encoding="utf-8") as fh:
        cassette = pyyaml.safe_load(fh)
    interactions = cassette.get("interactions", [])
    if not interactions:
        return None
    body_node = interactions[0].get("response", {}).get("body", {})
    if not isinstance(body_node, dict) or "string" not in body_node:
        return None
    raw = body_node.get("string")
    if raw is None:
        return None
    if raw == "":
        return ""
    if not isinstance(raw, str):
        raw = str(raw)
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return raw


def _list_cassettes(provider: str) -> list[Path]:
    mocks_dir = EXTERNAL_DIR / provider / "mocks"
    if not mocks_dir.is_dir():
        return []
    return sorted(mocks_dir.glob("*.yaml"))


def _yaml_has_recorded_interaction(cassette_path: Path) -> bool:
    """True when the file is a VCR cassette with at least one HTTP interaction.

    Placeholder cassettes (e.g. ``stub.yaml`` with ``interactions: []``) are
    not valid for body replay — skip them in schema health until recorded.
    """
    with cassette_path.open(encoding="utf-8") as fh:
        raw = pyyaml.safe_load(fh)
    if not isinstance(raw, dict):
        return False
    interactions = raw.get("interactions")
    if not isinstance(interactions, list):
        return False
    return len(interactions) > 0


def _list_recorded_cassettes(provider: str) -> list[Path]:
    """VCR files under ``mocks/`` that have a non-empty ``interactions`` list."""
    return [p for p in _list_cassettes(provider) if _yaml_has_recorded_interaction(p)]


# ── Per-provider schema health tests ──────────────────────────────────────────
# Each test class checks that every cassette for that provider:
#   1. Has a parseable body
#   2. Is not empty
# Pydantic schema validation is done where the provider schema class is known.
# Providers without cassettes are skipped automatically.


class _BaseSchemaHealthTest:
    """Base class providing the cassette-replay fixture."""

    provider: str = ""

    def _get_cassettes(self) -> list[Path]:
        return _list_recorded_cassettes(self.provider)

    def _assert_cassette_non_empty(self, cassette: Path) -> Any:
        body = _read_cassette_body(cassette)
        assert body is not None, f"Empty or unparseable cassette body in {cassette.name}"
        return body


# ── Providers with Pydantic schema validation ──────────────────────────────────


class TestBinanceSchemaHealth(_BaseSchemaHealthTest):
    provider = "binance"

    def test_ticker_cassette_body_non_empty(self) -> None:
        cassettes = self._get_cassettes()
        if not cassettes:
            pytest.skip(f"No cassettes for {self.provider}")
        for c in cassettes:
            self._assert_cassette_non_empty(c)

    def test_ticker_schema_validates(self) -> None:
        cassette = EXTERNAL_DIR / "binance" / "mocks" / "ticker_24hr.yaml"
        if not cassette.exists():
            pytest.skip("Cassette not recorded yet")
        from unified_api_contracts.external.binance.market_schemas import (
            BinanceTicker as BinanceFuturesTicker,
        )

        body = _read_cassette_body(cassette)
        assert isinstance(body, dict), "Expected JSON object from cassette"
        BinanceFuturesTicker.model_validate(body)


class TestBybitSchemaHealth(_BaseSchemaHealthTest):
    provider = "bybit"

    def test_cassettes_non_empty(self) -> None:
        cassettes = self._get_cassettes()
        if not cassettes:
            pytest.skip(f"No cassettes for {self.provider}")
        for c in cassettes:
            self._assert_cassette_non_empty(c)


class TestOkxSchemaHealth(_BaseSchemaHealthTest):
    provider = "okx"

    def test_cassettes_non_empty(self) -> None:
        cassettes = self._get_cassettes()
        if not cassettes:
            pytest.skip(f"No cassettes for {self.provider}")
        for c in cassettes:
            self._assert_cassette_non_empty(c)


class TestBetfairSchemaHealth(_BaseSchemaHealthTest):
    provider = "betfair"

    def test_cassettes_non_empty(self) -> None:
        cassettes = self._get_cassettes()
        if not cassettes:
            pytest.skip(f"No cassettes for {self.provider}")
        for c in cassettes:
            self._assert_cassette_non_empty(c)


class TestDeribitSchemaHealth(_BaseSchemaHealthTest):
    provider = "deribit"

    def test_cassettes_non_empty(self) -> None:
        cassettes = self._get_cassettes()
        if not cassettes:
            pytest.skip(f"No cassettes for {self.provider}")
        for c in cassettes:
            self._assert_cassette_non_empty(c)


class TestKalshiSchemaHealth(_BaseSchemaHealthTest):
    provider = "kalshi"

    def test_cassettes_non_empty(self) -> None:
        cassettes = self._get_cassettes()
        if not cassettes:
            pytest.skip(f"No cassettes for {self.provider}")
        for c in cassettes:
            self._assert_cassette_non_empty(c)


class TestPolymarketSchemaHealth(_BaseSchemaHealthTest):
    provider = "polymarket"

    def test_cassettes_non_empty(self) -> None:
        cassettes = self._get_cassettes()
        if not cassettes:
            pytest.skip(f"No cassettes for {self.provider}")
        for c in cassettes:
            self._assert_cassette_non_empty(c)


class TestCoingeckoSchemaHealth(_BaseSchemaHealthTest):
    provider = "coingecko"

    def test_cassettes_non_empty(self) -> None:
        cassettes = self._get_cassettes()
        if not cassettes:
            pytest.skip(f"No cassettes for {self.provider}")
        for c in cassettes:
            self._assert_cassette_non_empty(c)


class TestDefilllamaSchemaHealth(_BaseSchemaHealthTest):
    provider = "defillama"

    def test_cassettes_non_empty(self) -> None:
        cassettes = self._get_cassettes()
        if not cassettes:
            pytest.skip(f"No cassettes for {self.provider}")
        for c in cassettes:
            self._assert_cassette_non_empty(c)


class TestHyperliquidSchemaHealth(_BaseSchemaHealthTest):
    provider = "hyperliquid"

    def test_cassettes_non_empty(self) -> None:
        cassettes = self._get_cassettes()
        if not cassettes:
            pytest.skip(f"No cassettes for {self.provider}")
        for c in cassettes:
            self._assert_cassette_non_empty(c)


class TestMatchbookSchemaHealth(_BaseSchemaHealthTest):
    provider = "matchbook"

    def test_cassettes_non_empty(self) -> None:
        cassettes = self._get_cassettes()
        if not cassettes:
            pytest.skip(f"No cassettes for {self.provider}")
        for c in cassettes:
            self._assert_cassette_non_empty(c)


class TestManifoldSchemaHealth(_BaseSchemaHealthTest):
    provider = "manifold"

    def test_cassettes_non_empty(self) -> None:
        cassettes = self._get_cassettes()
        if not cassettes:
            pytest.skip(f"No cassettes for {self.provider}")
        for c in cassettes:
            self._assert_cassette_non_empty(c)


class TestFredSchemaHealth(_BaseSchemaHealthTest):
    provider = "fred"

    def test_cassettes_non_empty(self) -> None:
        cassettes = self._get_cassettes()
        if not cassettes:
            pytest.skip(f"No cassettes for {self.provider}")
        for c in cassettes:
            self._assert_cassette_non_empty(c)


class TestEcbSchemaHealth(_BaseSchemaHealthTest):
    provider = "ecb"

    def test_cassettes_non_empty(self) -> None:
        cassettes = self._get_cassettes()
        if not cassettes:
            pytest.skip(f"No cassettes for {self.provider}")
        for c in cassettes:
            self._assert_cassette_non_empty(c)


class TestFearGreedSchemaHealth(_BaseSchemaHealthTest):
    provider = "fear_greed"

    def test_cassettes_non_empty(self) -> None:
        cassettes = self._get_cassettes()
        if not cassettes:
            pytest.skip(f"No cassettes for {self.provider}")
        for c in cassettes:
            self._assert_cassette_non_empty(c)


class TestOpenMeteoSchemaHealth(_BaseSchemaHealthTest):
    provider = "open_meteo"

    def test_cassettes_non_empty(self) -> None:
        cassettes = self._get_cassettes()
        if not cassettes:
            pytest.skip(f"No cassettes for {self.provider}")
        for c in cassettes:
            self._assert_cassette_non_empty(c)


class TestAlchemySchemaHealth(_BaseSchemaHealthTest):
    provider = "alchemy"

    def test_cassettes_non_empty(self) -> None:
        cassettes = self._get_cassettes()
        if not cassettes:
            pytest.skip(f"No cassettes for {self.provider}")
        for c in cassettes:
            self._assert_cassette_non_empty(c)


class TestTardisSchemaHealth(_BaseSchemaHealthTest):
    provider = "tardis"

    def test_cassettes_non_empty(self) -> None:
        cassettes = self._get_cassettes()
        if not cassettes:
            pytest.skip(f"No cassettes for {self.provider}")
        for c in cassettes:
            self._assert_cassette_non_empty(c)


# ── Sweep test: validates ALL providers in the manifest ───────────────────────


def _all_providers_with_cassettes() -> list[tuple[str, Path]]:
    """Return (provider, cassette_path) pairs for all recorded cassettes."""
    manifest = _load_manifest()
    pairs: list[tuple[str, Path]] = []
    for name in manifest:
        for cassette in _list_recorded_cassettes(name):
            pairs.append((name, cassette))
    return pairs


@pytest.mark.parametrize("provider,cassette", _all_providers_with_cassettes())
def test_cassette_body_parseable(provider: str, cassette: Path) -> None:
    """All recorded cassettes must expose a readable first response body.

    Empty ``body.string`` (e.g. binary download stubs) is allowed. Non-VCR YAML
    files (no ``interactions`` key) are skipped — they are custom mock data.
    """
    with cassette.open(encoding="utf-8") as fh:
        raw = pyyaml.safe_load(fh)
    if not isinstance(raw, dict) or "interactions" not in raw:
        pytest.skip(f"{provider}/{cassette.name}: not a VCR cassette (no 'interactions' key) — skipped")
    if not raw.get("interactions"):
        pytest.skip(
            f"{provider}/{cassette.name}: placeholder cassette (interactions: []) — "
            "re-record with live mode or remove stub"
        )
    body = _read_cassette_body(cassette)
    assert body is not None, (
        f"{provider}/{cassette.name}: cassette body is None or empty. Re-record the cassette or delete the stale file."
    )
