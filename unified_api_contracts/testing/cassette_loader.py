"""Cassette loader for UAC VCR cassettes.

Provides a single function for consumer repos (execution-service,
unified-defi-execution-interface, etc.) to load cassettes from the
canonical UAC external/<venue>/mocks/ directory instead of keeping
local copies.

Usage::

    from unified_api_contracts.testing.cassette_loader import (
        load_cassette,
        get_cassette_path,
        list_cassettes_for_venue,
    )

    # Get the Path object
    path = get_cassette_path("deribit", "auth_test.yaml")

    # Load and parse YAML + extract response body
    body = load_cassette("hyperliquid", "meta_and_asset_ctxs.yaml")

    # List all cassettes for a venue
    cassettes = list_cassettes_for_venue("deribit")
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

_EXTERNAL_ROOT: Path = Path(__file__).resolve().parents[1] / "external"


def get_cassette_path(venue: str, cassette_name: str) -> Path:
    """Return the absolute Path to a cassette YAML file.

    Raises FileNotFoundError if the cassette does not exist.
    """
    cassette_path = _EXTERNAL_ROOT / venue / "mocks" / cassette_name
    if not cassette_path.is_file():
        raise FileNotFoundError(
            f"Cassette not found: {cassette_path}. "
            f"Available cassettes for '{venue}': "
            f"{[p.name for p in list_cassettes_for_venue(venue)]}"
        )
    return cassette_path


def list_cassettes_for_venue(venue: str) -> list[Path]:
    """Return all *.yaml cassette files for a given venue."""
    mocks_dir = _EXTERNAL_ROOT / venue / "mocks"
    if not mocks_dir.is_dir():
        return []
    return sorted(mocks_dir.glob("*.yaml"))


def load_cassette(
    venue: str,
    cassette_name: str,
    interaction_index: int = 0,
) -> object:
    """Load a VCR cassette and return the parsed response body.

    Args:
        venue: External source name (e.g. "deribit", "hyperliquid").
        cassette_name: YAML filename (e.g. "auth_test.yaml").
        interaction_index: Which interaction to extract (default 0).

    Returns:
        Parsed JSON response body as a Python object (dict or list).

    Raises:
        FileNotFoundError: If cassette does not exist.
        ValueError: If cassette format is invalid.
    """
    cassette_path = get_cassette_path(venue, cassette_name)
    content = cassette_path.read_text(encoding="utf-8")
    parsed = yaml.safe_load(content)

    if not isinstance(parsed, dict) or "interactions" not in parsed:
        raise ValueError(f"Cassette {cassette_path.name} is not a valid VCR cassette (missing 'interactions' key)")

    interactions = parsed["interactions"]
    if not isinstance(interactions, list):
        raise ValueError(f"Cassette {cassette_path.name}: 'interactions' must be a list")

    if len(interactions) == 0:
        raise ValueError(f"Cassette {cassette_path.name} is a stub (empty interactions)")

    if interaction_index >= len(interactions):
        raise ValueError(
            f"Cassette {cassette_path.name} has only {len(interactions)} "
            f"interactions, requested index {interaction_index}"
        )

    interaction = interactions[interaction_index]
    if not isinstance(interaction, dict):
        raise ValueError(
            f"Cassette {cassette_path.name} interaction[{interaction_index}]: "
            f"expected dict, got {type(interaction).__name__}"
        )

    response = interaction.get("response")
    if not isinstance(response, dict):
        raise ValueError(
            f"Cassette {cassette_path.name} interaction[{interaction_index}]: missing or malformed 'response'"
        )

    body = response.get("body")
    if not isinstance(body, dict):
        raise ValueError(f"Cassette {cassette_path.name} interaction[{interaction_index}]: missing or malformed 'body'")

    body_string = body.get("string")
    if not isinstance(body_string, str) or not body_string.strip():
        raise ValueError(
            f"Cassette {cassette_path.name} interaction[{interaction_index}]: body string is empty or not a string"
        )

    return json.loads(body_string)


def load_cassette_raw(
    venue: str,
    cassette_name: str,
) -> dict[str, object]:
    """Load a VCR cassette and return the full parsed YAML as a dict.

    Useful when tests need access to the request details, all interactions,
    or the raw cassette structure.
    """
    cassette_path = get_cassette_path(venue, cassette_name)
    content = cassette_path.read_text(encoding="utf-8")
    parsed = yaml.safe_load(content)
    if not isinstance(parsed, dict):
        raise ValueError(f"Cassette {cassette_path.name}: expected dict at root")
    return parsed
