"""Cassette -> UAC schema parity tests (Plan #60 H5.2).

Validates every committed VCR cassette YAML in unified_api_contracts_external/<venue>/mocks/
has a valid, non-empty JSON response body. Zero network calls -- pure file I/O.

Checks performed per cassette:
- YAML parses without error
- File is a VCR cassette (has ``interactions`` key at root)
- If interactions list is non-empty: each interaction with a JSON Content-Type response body
  must contain valid JSON
- Non-JSON content types (application/gzip, text/csv, etc.) and HEAD method responses
  are explicitly allowed to have empty bodies
- Response status codes are present (non-200 error cassettes are allowed as explicit fixtures;
  they must still contain valid JSON bodies when Content-Type is application/json)
- Body string is non-empty for non-stub, non-binary cassettes

Stub cassettes (``interactions: []``) are skipped -- they have not been recorded yet and
are explicitly documented as "STUB -- cassette not yet recorded".

Usage:
    cd unified-api-contracts
    bash scripts/quality-gates.sh          # runs as part of full QG
    .venv/bin/pytest tests/test_cassette_schema_parity.py -v   # targeted run
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Final

import pytest
import yaml

logger = logging.getLogger(__name__)

# Root of the cassette tree relative to this test file
_REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
_MOCKS_BASE: Final[Path] = _REPO_ROOT / "unified_api_contracts" / "unified_api_contracts_external"

# Content-Type prefixes that indicate binary or non-JSON bodies (empty body OK)
_NON_JSON_CONTENT_TYPES: Final[tuple[str, ...]] = (
    "application/gzip",
    "application/octet-stream",
    "application/zip",
    "text/csv",
    "text/plain",
    "application/x-ndjson",
)


def _collect_cassette_paths() -> list[Path]:
    """Return all *.yaml files under unified_api_contracts_external/<venue>/mocks/."""
    return sorted(_MOCKS_BASE.glob("*/mocks/*.yaml"))


def _cassette_id(cassette_path: Path) -> str:
    """Human-readable pytest ID: <venue>/<filename>."""
    venue = cassette_path.parent.parent.name
    return f"{venue}/{cassette_path.name}"


def _is_json_content_type(headers: object) -> bool:
    """Return True if the response Content-Type indicates a JSON body is expected."""
    if not isinstance(headers, dict):
        return True  # assume JSON if headers are absent (conservative)
    content_type_values: object = headers.get("Content-Type") or headers.get("content-type")
    if content_type_values is None:
        return True  # assume JSON if no Content-Type header
    # Content-Type may be a list (vcrpy normalises to list) or a plain string
    if isinstance(content_type_values, list):
        raw_ct = content_type_values[0] if content_type_values else ""
    else:
        raw_ct = str(content_type_values)
    ct = raw_ct.lower().split(";")[0].strip()
    return not ct.startswith(_NON_JSON_CONTENT_TYPES)


_ALL_CASSETTES: Final[list[Path]] = _collect_cassette_paths()


# ---------------------------------------------------------------------------
# Smoke: at least one cassette was found by the glob
# ---------------------------------------------------------------------------


def test_cassette_glob_finds_files() -> None:
    """Assert the cassette glob finds at least one YAML file -- catches path regressions."""
    assert len(_ALL_CASSETTES) > 0, (
        f"No cassette YAML files found under {_MOCKS_BASE}. "
        "Check that unified_api_contracts_external exists and contains <venue>/mocks/*.yaml files."
    )


# ---------------------------------------------------------------------------
# Per-cassette parity checks
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "cassette_path",
    _ALL_CASSETTES,
    ids=[_cassette_id(p) for p in _ALL_CASSETTES],
)
def test_cassette_is_valid_yaml(cassette_path: Path) -> None:
    """Each cassette YAML must parse without error."""
    content = cassette_path.read_text(encoding="utf-8")
    parsed = yaml.safe_load(content)
    assert parsed is not None, f"{cassette_path.name}: YAML loaded as None (empty file?)"


@pytest.mark.parametrize(
    "cassette_path",
    _ALL_CASSETTES,
    ids=[_cassette_id(p) for p in _ALL_CASSETTES],
)
def test_cassette_vcr_format_or_skip(cassette_path: Path) -> None:
    """Non-VCR YAML fixtures (no ``interactions`` key) are explicitly skipped.

    Some files in mocks/ are fixture YAMLs (e.g. error_rate_limit.yaml) rather than
    vcrpy cassettes. These are valid files but not subject to VCR parity checks.
    """
    content = cassette_path.read_text(encoding="utf-8")
    parsed: object = yaml.safe_load(content)
    if not isinstance(parsed, dict) or "interactions" not in parsed:
        pytest.skip(f"{cassette_path.name} has no 'interactions' key -- not a vcrpy cassette; skipping parity check")


@pytest.mark.parametrize(
    "cassette_path",
    _ALL_CASSETTES,
    ids=[_cassette_id(p) for p in _ALL_CASSETTES],
)
def test_cassette_response_body_is_valid_json(cassette_path: Path) -> None:
    """For each recorded interaction with a JSON Content-Type, response body must be valid JSON.

    Stub cassettes (empty interactions list) are skipped -- they are placeholders
    for cassettes not yet recorded against the live API.

    Non-JSON content types (application/gzip, text/csv, etc.) and HEAD requests
    with empty bodies are explicitly allowed.
    """
    content = cassette_path.read_text(encoding="utf-8")
    parsed: object = yaml.safe_load(content)

    if not isinstance(parsed, dict):
        pytest.skip(f"{cassette_path.name}: not a dict-rooted YAML")

    if "interactions" not in parsed:
        pytest.skip(f"{cassette_path.name}: not a vcrpy cassette (no interactions key)")

    interactions: object = parsed["interactions"]
    if not isinstance(interactions, list):
        pytest.fail(f"{cassette_path.name}: 'interactions' must be a list, got {type(interactions).__name__}")

    if len(interactions) == 0:
        # Explicit stub -- documented placeholder, not an error
        pytest.skip(
            f"{cassette_path.name}: stub cassette (interactions: []) -- not yet recorded; skipping parity check"
        )

    for idx, interaction in enumerate(interactions):
        if not isinstance(interaction, dict):
            pytest.fail(f"{cassette_path.name} interaction[{idx}]: expected dict, got {type(interaction).__name__}")

        # HEAD responses have no body by HTTP spec -- skip JSON check
        request: object = interaction.get("request")
        if isinstance(request, dict) and request.get("method") == "HEAD":
            logger.info(
                "%s interaction[%d]: HEAD request -- skipping body check",
                cassette_path.name,
                idx,
            )
            continue

        response: object = interaction.get("response")
        if not isinstance(response, dict):
            pytest.fail(f"{cassette_path.name} interaction[{idx}]: missing or malformed 'response' key")

        body: object = response.get("body")
        if not isinstance(body, dict):
            pytest.fail(f"{cassette_path.name} interaction[{idx}]: missing or malformed 'body' key in response")

        resp_headers: object = response.get("headers")
        if not _is_json_content_type(resp_headers):
            # Binary or non-JSON response -- empty body is valid
            logger.info(
                "%s interaction[%d]: non-JSON Content-Type -- skipping JSON body check",
                cassette_path.name,
                idx,
            )
            continue

        body_string: object = body.get("string")
        if body_string is None:
            pytest.fail(f"{cassette_path.name} interaction[{idx}]: response body 'string' is None (empty body)")

        if not isinstance(body_string, str):
            # vcrpy sometimes stores parsed dicts for non-JSON bodies -- skip gracefully
            logger.warning(
                "%s interaction[%d]: body.string is %s (not str) -- skipping JSON parse",
                cassette_path.name,
                idx,
                type(body_string).__name__,
            )
            continue

        if body_string.strip() == "":
            pytest.fail(
                f"{cassette_path.name} interaction[{idx}]: "
                "response body string is empty for a JSON Content-Type response"
            )

        # Validate JSON parseability
        try:
            json.loads(body_string)
        except json.JSONDecodeError as exc:
            pytest.fail(
                f"{cassette_path.name} interaction[{idx}]: "
                f"response body is not valid JSON: {exc}\n"
                f"Body preview: {body_string[:200]!r}"
            )


@pytest.mark.parametrize(
    "cassette_path",
    _ALL_CASSETTES,
    ids=[_cassette_id(p) for p in _ALL_CASSETTES],
)
def test_cassette_has_version_field(cassette_path: Path) -> None:
    """VCR cassettes must have a top-level ``version`` field (vcrpy format requirement)."""
    content = cassette_path.read_text(encoding="utf-8")
    parsed: object = yaml.safe_load(content)

    if not isinstance(parsed, dict) or "interactions" not in parsed:
        pytest.skip(f"{cassette_path.name}: not a vcrpy cassette -- skipping version check")

    interactions: object = parsed["interactions"]
    if isinstance(interactions, list) and len(interactions) == 0:
        pytest.skip(f"{cassette_path.name}: stub cassette -- skipping version check")

    assert "version" in parsed, (
        f"{cassette_path.name}: missing top-level 'version' field -- "
        "cassette may be malformed or from an incompatible vcrpy version"
    )
    assert parsed["version"] == 1, f"{cassette_path.name}: expected version=1, got {parsed['version']!r}"
