"""Tests for the cassette orphan checker.

Verifies the orphan checker correctly identifies:
1. Orphan cassettes (cassettes with no PRODUCTION consumer)
2. Missing cassettes (test references with no matching file)
3. Correct scanning of production source for cassette references

Per plans/active/canary_coverage_qg_enforcement_2026_05_20.md Phase 1,
``TestIntegrationOrphanCheck`` now asserts that
``set(orphans) - set(allowlist) == set()`` — orphans not present in
``tests/cassette_orphan_allowlist.yaml`` fail the test.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from unified_api_contracts.testing.cassette_orphan_checker import (
    collect_all_cassette_files,
    find_missing_cassettes,
    find_orphan_cassettes,
    scan_production_cassette_references,
    scan_test_cassette_references,
)

_ALLOWLIST_PATH: Path = Path(__file__).resolve().parent / "cassette_orphan_allowlist.yaml"


def _load_orphan_allowlist() -> set[str]:
    """Load the orphan allowlist as a set of '<venue>/mocks/<file>' strings."""
    if not _ALLOWLIST_PATH.is_file():
        return set()
    with _ALLOWLIST_PATH.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        return set()
    allowed = data.get("allowed") or []
    out: set[str] = set()
    for entry in allowed:
        if isinstance(entry, dict) and isinstance(entry.get("path"), str):
            out.add(entry["path"])
    return out


class TestCollectCassettes:
    """Tests for collect_all_cassette_files."""

    def test_returns_dict_of_venue_to_paths(self) -> None:
        """Result is a dict mapping venue names to path lists."""
        result = collect_all_cassette_files()
        assert isinstance(result, dict)
        for venue, paths in result.items():
            assert isinstance(venue, str)
            assert isinstance(paths, list)
            for p in paths:
                assert isinstance(p, Path)
                assert p.suffix == ".yaml"

    def test_deribit_has_cassettes(self) -> None:
        """Deribit venue should have cassettes."""
        result = collect_all_cassette_files()
        assert "deribit" in result
        assert len(result["deribit"]) >= 1

    def test_hyperliquid_has_cassettes(self) -> None:
        """Hyperliquid venue should have cassettes."""
        result = collect_all_cassette_files()
        assert "hyperliquid" in result
        assert len(result["hyperliquid"]) >= 1

    def test_paths_are_absolute_and_exist(self) -> None:
        """All returned paths should be absolute and point to existing files."""
        result = collect_all_cassette_files()
        for paths in result.values():
            for p in paths:
                assert p.is_absolute()
                assert p.is_file()


class TestScanProductionReferences:
    """Tests for scan_production_cassette_references.

    The orphan checker scans PRODUCTION source (service repos) for cassette
    references, not test files. A cassette only exists to protect a real
    production consumer from upstream drift; test-file references alone
    are insufficient.
    """

    def test_returns_venue_aware_dict(self) -> None:
        """Result is a dict mapping (venue, name) -> set of consumer paths."""
        refs = scan_production_cassette_references()
        assert isinstance(refs, dict)
        for key, consumers in refs.items():
            assert isinstance(key, tuple)
            assert len(key) == 2
            venue, name = key
            assert isinstance(venue, str)
            assert isinstance(name, str)
            assert name.endswith(".yaml")
            assert isinstance(consumers, set)

    def test_scanning_empty_dir_returns_empty(self, tmp_path: Path) -> None:
        """Scanning a single empty directory returns empty references."""
        refs = scan_production_cassette_references(production_paths=[tmp_path])
        assert refs == {}


class TestScanTestReferencesLegacy:
    """Legacy backwards-compat wrapper. Deprecated signature still callable."""

    def test_legacy_wrapper_returns_set_of_names(self) -> None:
        refs = scan_test_cassette_references()
        assert isinstance(refs, set)
        for ref in refs:
            assert ref.endswith(".yaml")


class TestFindOrphanCassettes:
    """Tests for find_orphan_cassettes."""

    def test_no_orphans_when_all_referenced(self) -> None:
        """When all cassettes are referenced, no orphans."""
        cassette_map = {
            "venue_a": [Path("/fake/venue_a/mocks/alpha.yaml")],
            "venue_b": [Path("/fake/venue_b/mocks/beta.yaml")],
        }
        referenced = {"alpha.yaml", "beta.yaml"}
        orphans = find_orphan_cassettes(cassette_map, referenced)
        assert orphans == []

    def test_detects_orphan_cassettes(self) -> None:
        """Unreferenced cassettes should be detected as orphans."""
        cassette_map = {
            "venue_a": [
                Path("/fake/venue_a/mocks/alpha.yaml"),
                Path("/fake/venue_a/mocks/orphan.yaml"),
            ],
        }
        referenced = {"alpha.yaml"}
        orphans = find_orphan_cassettes(cassette_map, referenced)
        assert len(orphans) == 1
        venue, path = orphans[0]
        assert venue == "venue_a"
        assert path.name == "orphan.yaml"

    def test_empty_cassette_map(self) -> None:
        """No cassettes means no orphans."""
        orphans = find_orphan_cassettes({}, {"some_ref.yaml"})
        assert orphans == []

    def test_empty_references(self) -> None:
        """No references means all cassettes are orphans."""
        cassette_map = {
            "venue_a": [Path("/fake/venue_a/mocks/alpha.yaml")],
        }
        orphans = find_orphan_cassettes(cassette_map, set())
        assert len(orphans) == 1


class TestFindMissingCassettes:
    """Tests for find_missing_cassettes."""

    def test_no_missing_when_all_exist(self) -> None:
        """When all references have matching files, no missing."""
        cassette_map = {
            "venue_a": [Path("/fake/venue_a/mocks/alpha.yaml")],
        }
        referenced = {"alpha.yaml"}
        missing = find_missing_cassettes(cassette_map, referenced)
        assert missing == []

    def test_detects_missing_cassettes(self) -> None:
        """References to non-existent cassettes should be detected."""
        cassette_map = {
            "venue_a": [Path("/fake/venue_a/mocks/alpha.yaml")],
        }
        referenced = {"alpha.yaml", "ghost.yaml"}
        missing = find_missing_cassettes(cassette_map, referenced)
        assert "ghost.yaml" in missing

    def test_excludes_config_files(self) -> None:
        """References containing 'config' should be excluded."""
        cassette_map: dict[str, list[Path]] = {}
        referenced = {"config.yaml", "settings.yaml"}
        missing = find_missing_cassettes(cassette_map, referenced)
        assert missing == []

    def test_empty_references(self) -> None:
        """No references means no missing."""
        cassette_map = {
            "venue_a": [Path("/fake/venue_a/mocks/alpha.yaml")],
        }
        missing = find_missing_cassettes(cassette_map, set())
        assert missing == []


class TestIntegrationOrphanCheck:
    """Integration test: run against real UAC cassettes and production paths.

    Per plans/active/canary_coverage_qg_enforcement_2026_05_20.md Phase 1,
    this test is now a STRICT gate: every orphan cassette MUST be either
    (a) accompanied by a production consumer, or
    (b) explicitly listed in tests/cassette_orphan_allowlist.yaml with a
        documented reason + operator ack.
    Real orphans (not allowlisted) FAIL the test.
    """

    def test_no_unallowlisted_orphans(self) -> None:
        # Production consumers of these external-source cassettes live in sibling repos
        # (MTDS / features / instruments adapters). In per-repo CI (workspace-qg renders
        # dep_repos="") those siblings aren't checked out, so the workspace-wide consumer
        # scan finds nothing and every cassette looks orphan. Cross-repo consumer linkage
        # is validated under local quality-gates.sh / the full-workspace SIT job; skip when
        # the sibling consumer repos are absent rather than flag false orphans.
        workspace_root = Path(__file__).resolve().parents[1].parent
        if not (workspace_root / "market-tick-data-service").is_dir():
            pytest.skip(
                "per-repo CI checkout: sibling consumer repos absent; orphan-cassette "
                "linkage validated in the full-workspace SIT"
            )
        cassette_map = collect_all_cassette_files()
        referenced_keys = set(scan_production_cassette_references(cassette_map=cassette_map).keys())

        orphans = find_orphan_cassettes(cassette_map, referenced_keys)
        orphan_paths = {f"{venue}/mocks/{path.name}" for venue, path in orphans}
        allowlist = _load_orphan_allowlist()

        unexpected = orphan_paths - allowlist
        assert unexpected == set(), (
            f"Orphan cassettes detected: {sorted(unexpected)} — "
            f"each cassette must have a production consumer OR an entry in "
            f"{_ALLOWLIST_PATH.relative_to(Path(__file__).resolve().parents[1])} "
            "with reason + operator ack."
        )

    def test_allowlist_is_well_formed(self) -> None:
        """Every allowlist entry has the required fields."""
        if not _ALLOWLIST_PATH.is_file():
            return
        with _ALLOWLIST_PATH.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        if not data:
            return
        allowed = data.get("allowed") or []
        for entry in allowed:
            assert isinstance(entry, dict)
            for required_field in ("path", "reason", "detail", "acked_by"):
                assert required_field in entry, f"allowlist entry missing '{required_field}': {entry}"

    def test_missing_cassettes_is_list(self) -> None:
        """Missing-cassette detection still returns a list (informational)."""
        cassette_map = collect_all_cassette_files()
        referenced_keys = set(scan_production_cassette_references(cassette_map=cassette_map).keys())
        referenced_names = {name for _venue, name in referenced_keys}
        missing = find_missing_cassettes(cassette_map, referenced_names)
        assert isinstance(missing, list)
