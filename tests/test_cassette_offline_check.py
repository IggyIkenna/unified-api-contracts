"""Canary offline check — validate ALL cassette YAML structure without network calls.

Per plans/active/canary_coverage_qg_enforcement_2026_05_20.md Phase 5 (canary_offline_check):
Every cassette file must be parseable YAML and conform to one of:
  - VCR format: has `interactions:` key (list of request/response pairs)
  - WS format:  has `ws_url:` key starting with wss://

These checks run without any live network calls and catch cassette corruption /
YAML syntax errors / structural drift on every PR to live-defi-rollout.

WS cassette frame JSON validity is already covered by test_ws_cassette_coexistence.py.
VCR cassette schema parity (live API diff) is covered by test_cassette_schema_parity.py.
This file covers the STRUCTURAL BASELINE that both formats share.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from yaml import CSafeLoader as _YamlLoader  # C extension: avoids pure-Python scanner hang on large cassette files

_EXTERNAL_ROOT = Path(__file__).resolve().parents[1] / "unified_api_contracts" / "external"

_ALL_CASSETTES = sorted(_EXTERNAL_ROOT.glob("*/mocks/*.yaml"))


def _cassette_id(cassette_path: Path) -> str:
    return f"{cassette_path.parent.parent.name}/{cassette_path.name}"


@pytest.fixture(params=_ALL_CASSETTES, ids=_cassette_id)
def cassette_path(request: pytest.FixtureRequest) -> Path:
    return request.param  # type: ignore[return-value]


# ── VCR vs WS detection ───────────────────────────────────────────────────────


def _load_cassette(p: Path) -> dict:
    try:
        data = yaml.load(p.read_text(), Loader=_YamlLoader) or {}
    except yaml.YAMLError as exc:
        pytest.fail(f"{_cassette_id(p)}: YAML parse error: {exc}")
    if not isinstance(data, dict):
        pytest.fail(f"{_cassette_id(p)}: expected YAML dict, got {type(data).__name__}")
    return data


def _is_vcr(data: dict) -> bool:
    return "interactions" in data


def _is_ws(data: dict) -> bool:
    return "ws_url" in data


def _is_doc_cassette(data: dict) -> bool:
    """Custom documentation YAMLs stored in mocks/ — not VCR or WS format.

    These are allowlisted in tests/cassette_orphan_allowlist.yaml with reason
    'recording-template'. They document API behavior (errors, rate limits, etc.)
    but are not parseable as VCR cassettes. Structural validation is skipped.
    """
    return "metadata" in data and "interactions" not in data and "ws_url" not in data


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_cassette_is_valid_yaml(cassette_path: Path) -> None:
    """Every cassette must parse as YAML without error."""
    _load_cassette(cassette_path)


def test_cassette_has_known_format(cassette_path: Path) -> None:
    """Every cassette must be VCR format, WS format, or a doc-cassette."""
    data = _load_cassette(cassette_path)
    if _is_vcr(data) or _is_ws(data) or _is_doc_cassette(data):
        return
    pytest.fail(
        f"{_cassette_id(cassette_path)}: cassette has neither 'interactions:' (VCR) "
        f"nor 'ws_url:' (WS) key, and is not a doc-cassette (no 'metadata:' key). "
        f"Keys present: {sorted(data.keys())}"
    )


def test_vcr_cassette_interactions_is_list(cassette_path: Path) -> None:
    """VCR cassettes: interactions must be a list (can be empty for stubs)."""
    data = _load_cassette(cassette_path)
    if not _is_vcr(data):
        pytest.skip("not a VCR cassette" if not _is_doc_cassette(data) else "doc-cassette")
    interactions = data["interactions"]
    if not isinstance(interactions, list):
        pytest.fail(f"{_cassette_id(cassette_path)}: interactions must be list, got {type(interactions).__name__}")


def test_vcr_cassette_interactions_have_required_fields(cassette_path: Path) -> None:
    """VCR cassettes: each interaction must have request.uri and response.status.code."""
    data = _load_cassette(cassette_path)
    if not _is_vcr(data):
        pytest.skip("not a VCR cassette")
    interactions = data.get("interactions") or []
    if not interactions:
        pytest.skip("stub cassette — empty interactions")
    for i, interaction in enumerate(interactions):
        if not isinstance(interaction, dict):
            pytest.fail(f"{_cassette_id(cassette_path)}: interaction[{i}] is not a dict")
        request = interaction.get("request", {})
        if not request.get("uri"):
            pytest.fail(f"{_cassette_id(cassette_path)}: interaction[{i}].request.uri missing")
        response = interaction.get("response", {})
        status = response.get("status", {})
        if status.get("code") is None:
            pytest.fail(f"{_cassette_id(cassette_path)}: interaction[{i}].response.status.code missing")


def test_ws_cassette_has_wss_url(cassette_path: Path) -> None:
    """WS cassettes: ws_url must start with wss://."""
    data = _load_cassette(cassette_path)
    if not _is_ws(data):
        pytest.skip("not a WS cassette")
    ws_url = data.get("ws_url", "")
    if not isinstance(ws_url, str) or not ws_url.startswith("wss://"):
        pytest.fail(f"{_cassette_id(cassette_path)}: ws_url must start with wss://, got {ws_url!r}")


def test_ws_cassette_frames_valid_json(cassette_path: Path) -> None:
    """WS cassettes: every frame payload must be valid JSON (stub frames=[] OK)."""
    data = _load_cassette(cassette_path)
    if not _is_ws(data):
        pytest.skip("not a WS cassette")
    frames = data.get("frames") or []
    for i, frame in enumerate(frames):
        payload = frame.get("payload")
        if payload is None:
            pytest.fail(f"{_cassette_id(cassette_path)}: frame[{i}] missing payload")
        try:
            json.loads(str(payload))
        except json.JSONDecodeError as exc:
            pytest.fail(f"{_cassette_id(cassette_path)}: frame[{i}] payload not valid JSON: {exc}")
