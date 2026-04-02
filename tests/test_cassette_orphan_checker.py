"""Tests for the cassette orphan checker.

Verifies the orphan checker correctly identifies:
1. Orphan cassettes (files with no test references)
2. Missing cassettes (test references with no matching file)
3. Correct scanning of test files for cassette references
"""

from __future__ import annotations

from pathlib import Path

from unified_api_contracts.testing.cassette_orphan_checker import (
    collect_all_cassette_files,
    find_missing_cassettes,
    find_orphan_cassettes,
    scan_test_cassette_references,
)


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


class TestScanTestReferences:
    """Tests for scan_test_cassette_references."""

    def test_finds_references_in_uac_tests(self) -> None:
        """Scanning UAC repo root should find cassette references."""
        repo_root = Path(__file__).resolve().parents[1]
        refs = scan_test_cassette_references(repo_root)
        assert isinstance(refs, set)
        # Our own test files reference cassettes
        assert len(refs) > 0

    def test_finds_yaml_filenames(self) -> None:
        """References should be .yaml filenames."""
        repo_root = Path(__file__).resolve().parents[1]
        refs = scan_test_cassette_references(repo_root)
        for ref in refs:
            assert ref.endswith(".yaml")

    def test_known_cassettes_are_referenced(self) -> None:
        """Known cassettes we use in tests should appear in references."""
        repo_root = Path(__file__).resolve().parents[1]
        refs = scan_test_cassette_references(repo_root)
        # These are referenced in test_cassette_consolidation.py
        assert "auth_test.yaml" in refs
        assert "meta_and_asset_ctxs.yaml" in refs

    def test_scanning_empty_dir_returns_empty(self, tmp_path: Path) -> None:
        """Scanning an empty directory returns empty set."""
        refs = scan_test_cassette_references(tmp_path)
        assert refs == set()


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
    """Integration test: run against real UAC cassettes and tests."""

    def test_real_orphan_scan_succeeds(self) -> None:
        """Running orphan check against real UAC should not crash."""
        cassette_map = collect_all_cassette_files()
        repo_root = Path(__file__).resolve().parents[1]
        referenced = scan_test_cassette_references(repo_root)

        orphans = find_orphan_cassettes(cassette_map, referenced)
        missing = find_missing_cassettes(cassette_map, referenced)

        # These are informational; we do not assert zero orphans/missing
        # because some cassettes may be referenced only by downstream repos
        assert isinstance(orphans, list)
        assert isinstance(missing, list)
