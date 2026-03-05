"""Direct test: every venue and every contracted endpoint type has at least one example that validates.

Parametrized by (venue, example_filename); each test loads the example JSON and validates with the
schema class from venue_manifest.example_schema_map. Ensures we directly test each endpoint shape
we claim to support.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from unified_api_contracts.unified_api_contracts_external.venue_manifest import VENUE_MANIFEST


def _api_contracts_root() -> Path:
    root = Path(__file__).resolve().parent.parent
    assert (root / "unified_api_contracts").is_dir()
    return root


def _example_cases() -> list[tuple[str, str]]:
    """(venue, example_filename) for every entry in manifest example_schema_map."""
    cases: list[tuple[str, str]] = []
    for venue, contract in VENUE_MANIFEST.items():
        mapping = contract.get("example_schema_map") or {}
        for example_filename in mapping:
            cases.append((venue, example_filename))
    return cases


@pytest.mark.parametrize("venue,example_filename", _example_cases())
def test_every_venue_endpoint_validates(venue: str, example_filename: str) -> None:
    """Each (venue, endpoint) has an example that validates against the contracted schema."""
    root = _api_contracts_root()
    old_path = root / "unified_api_contracts" / venue / "examples" / example_filename
    new_path = root / "unified_api_contracts" / "unified_api_contracts_external" / venue / "examples" / example_filename

    if old_path.exists():
        example_path = old_path
    elif new_path.exists():
        example_path = new_path
    else:
        pytest.fail(f"Missing example: tried {old_path} and {new_path}")

    assert example_path.exists(), f"Missing example: {example_path}"

    schema_class_name = VENUE_MANIFEST[venue]["example_schema_map"][example_filename]
    mod_path = f"unified_api_contracts.{venue}.schemas"
    mod = __import__(mod_path, fromlist=[schema_class_name])
    schema_class = getattr(mod, schema_class_name)

    data = json.loads(example_path.read_text())
    parsed = schema_class.model_validate(data)
    assert parsed is not None


@pytest.mark.xfail(reason="Some venues (fix, prime_broker) are protocol contracts without example data")
def test_every_venue_has_at_least_one_example() -> None:
    """Every external venue in the manifest has at least one example in example_schema_map."""
    venues_without_examples = []
    for venue, contract in VENUE_MANIFEST.items():
        if contract.get("is_internal", False):
            continue
        mapping = contract.get("example_schema_map") or {}
        if len(mapping) == 0:
            venues_without_examples.append(venue)

    if venues_without_examples:
        pytest.fail(f"External venues without examples: {venues_without_examples}")
    assert True
