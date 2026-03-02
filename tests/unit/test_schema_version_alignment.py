"""CI gate: schema version alignment.

Ensures SCHEMA_VERSIONS.md (or machine-readable schema_versions.json) matches
pyproject.toml [schema-validation] and core dependencies. Optionally verifies
ENDPOINT_SCHEMA_MAP entries have resolvable schema classes.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest

from unified_api_contracts.endpoints import ENDPOINT_SCHEMA_MAP, get_schema_class_for_endpoint


def _repo_root() -> Path:
    root = Path(__file__).resolve().parent.parent.parent
    assert (root / "unified_api_contracts").is_dir()
    return root


def _parse_schema_versions_md() -> dict[str, str]:
    """Parse SCHEMA_VERSIONS.md 'Pinned [schema-validation] Dependencies' table.

    Returns dict mapping package name -> version spec (e.g. 'requests' -> '>=2.31.0').
    """
    root = _repo_root()
    path = root / "SCHEMA_VERSIONS.md"
    assert path.exists(), f"SCHEMA_VERSIONS.md not found at {path}"

    content = path.read_text()
    pinned_match = re.search(
        r"## Pinned \[schema-validation\] Dependencies.*?\n\n(.*?)(?=\n## |\Z)",
        content,
        re.DOTALL,
    )
    assert pinned_match, "Pinned [schema-validation] Dependencies section not found"

    table = pinned_match.group(1)
    rows = [line.strip() for line in table.split("\n") if line.strip().startswith("|") and "---" not in line]
    result: dict[str, str] = {}
    for row in rows:
        parts = [p.strip() for p in row.split("|") if p.strip()]
        if len(parts) >= 2 and parts[0].lower() not in ("package", "---"):
            pkg, version = parts[0].strip(), parts[1].strip()
            if pkg and version:
                result[pkg] = version
    return result


def _parse_pyproject_deps() -> tuple[dict[str, str], dict[str, str]]:
    """Parse pyproject.toml for core deps and schema-validation optional deps."""
    root = _repo_root()
    path = root / "pyproject.toml"
    assert path.exists()

    with path.open("rb") as f:
        data = tomllib.load(f)

    project = data.get("project", {})
    core: dict[str, str] = {}
    for spec in project.get("dependencies", []):
        pkg = re.split(r"[>=<]", spec)[0]
        core[pkg] = spec

    schema_validation: dict[str, str] = {}
    opt_deps = project.get("optional-dependencies", {})
    for spec in opt_deps.get("schema-validation", []):
        pkg = re.split(r"[>=<]", spec)[0]
        schema_validation[pkg] = spec

    return core, schema_validation


@pytest.mark.unit
def test_schema_validation_deps_match_schema_versions() -> None:
    """[schema-validation] deps in pyproject.toml must match SCHEMA_VERSIONS.md."""
    expected = _parse_schema_versions_md()
    core, schema_validation = _parse_pyproject_deps()

    def _version_spec(spec: str) -> str:
        """Extract version part from 'pkg>=1.0' or 'pkg==1.0'."""
        m = re.match(r"^[a-zA-Z0-9_.-]+(.*)$", spec)
        return m.group(1).strip() if m else spec

    if "pydantic" in expected:
        assert "pydantic" in core, "pydantic must be in [project] dependencies"
        py_ver = _version_spec(core["pydantic"])
        assert py_ver == expected["pydantic"], (
            f"pydantic: pyproject has {py_ver}, SCHEMA_VERSIONS.md expects {expected['pydantic']}"
        )

    for pkg, version in expected.items():
        if pkg == "pydantic":
            continue
        if pkg in schema_validation:
            py_ver = _version_spec(schema_validation[pkg])
            assert py_ver == version, f"{pkg}: pyproject has {py_ver}, SCHEMA_VERSIONS.md expects {version}"

    assert "requests" in schema_validation, "requests must be in [project.optional-dependencies] schema-validation"


@pytest.mark.unit
def test_endpoint_schema_map_has_resolvable_schemas() -> None:
    """Every (venue, endpoint) in ENDPOINT_SCHEMA_MAP must resolve to a schema class."""
    gaps: list[tuple[str, str, str]] = []
    for (venue, endpoint), schema_name in ENDPOINT_SCHEMA_MAP.items():
        cls = get_schema_class_for_endpoint(venue, endpoint)
        if cls is None:
            gaps.append((venue, endpoint, schema_name))
    assert not gaps, f"ENDPOINT_SCHEMA_MAP entries with missing schema classes: {gaps}"
