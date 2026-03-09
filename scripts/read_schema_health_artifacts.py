"""Read CI schema health artifacts and update docs/schema_health.svg.

Usage
-----
    python3 scripts/read_schema_health_artifacts.py [--artifacts-dir ARTIFACTS_DIR]

CI artifact flow
----------------
1. Interface repo CI runs schema_validation tests.
2. On failure (or after all tests), it writes {provider}_schema_health.json to
   schema_artifacts/ (relative to the interface repo root).
3. The UAC CI job (schema-health-update.yml) downloads those artifact directories
   and places them under a local schema_artifacts/ directory.
4. This script reads all *.json files from schema_artifacts/, builds a provider→status
   map, and feeds it into update_schema_health_svg.py to regenerate docs/schema_health.svg.

Artifact format
---------------
Each file: {provider}_schema_health.json
Content:
    {
        "status": "green" | "yellow" | "red",
        "provider": "<provider_name>",
        "reason": "<human readable explanation>"
    }

Exit codes
----------
    0 — success (SVG updated or no artifacts to process)
    1 — one or more providers have "red" status (CI hard fail signal)
    2 — unexpected error (bad JSON, missing SVG script, etc.)
"""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARTIFACTS_DIR = REPO_ROOT / "schema_artifacts"
SVG_UPDATE_SCRIPT = REPO_ROOT / "scripts" / "update_schema_health_svg.py"
SCHEMA_HEALTH_SVG = REPO_ROOT / "docs" / "schema_health.svg"

# Valid status values
VALID_STATUSES = frozenset({"green", "yellow", "red"})


def _parse_artifact(artifact_path: Path) -> tuple[str, str, str]:
    """Return (provider, status, reason) from a health artifact JSON file.

    Raises ValueError if the JSON is malformed or missing required keys.
    """
    try:
        data = json.loads(artifact_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {artifact_path}: {exc}") from exc

    provider = data.get("provider", "")
    status = data.get("status", "")
    reason = data.get("reason", "")

    if not provider:
        raise ValueError(f"Missing 'provider' key in {artifact_path}")
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid status '{status}' in {artifact_path} — must be one of {sorted(VALID_STATUSES)}")
    return str(provider), str(status), str(reason)


def _load_all_artifacts(artifacts_dir: Path) -> dict[str, tuple[str, str]]:
    """Read all *_schema_health.json files and return provider → (status, reason) map."""
    results: dict[str, tuple[str, str]] = {}

    json_files = sorted(artifacts_dir.glob("*_schema_health.json"))
    if not json_files:
        logger.info("No schema health artifacts found in %s", artifacts_dir)
        return results

    for artifact_path in json_files:
        try:
            provider, status, reason = _parse_artifact(artifact_path)
            results[provider] = (status, reason)
            logger.info("  %-20s → %s  (%s)", provider, status.upper(), reason[:80])
        except ValueError as exc:
            logger.warning("Skipping malformed artifact %s: %s", artifact_path.name, exc)

    return results


def _write_merged_report(artifacts_dir: Path, results: dict[str, tuple[str, str]]) -> Path:
    """Write a consolidated merged_schema_health.json for update_schema_health_svg.py.

    The SVG update script expects a pytest-style JSON report. We produce a minimal
    compatible structure that the script can ingest via its --artifacts-mode flag.
    We write it to schema_artifacts/merged_schema_health.json.
    """
    merged_path = artifacts_dir / "merged_schema_health.json"
    merged = {
        "source": "ci_artifact_reader",
        "providers": {provider: {"status": status, "reason": reason} for provider, (status, reason) in results.items()},
    }
    merged_path.write_text(json.dumps(merged, indent=2), encoding="utf-8")
    logger.info("Wrote merged report to %s", merged_path)
    return merged_path


def _regenerate_svg(merged_report_path: Path) -> int:
    """Run update_schema_health_svg.py with the merged report.

    Returns the subprocess return code.
    """
    if not SVG_UPDATE_SCRIPT.exists():
        logger.error("SVG update script not found: %s", SVG_UPDATE_SCRIPT)
        return 2

    cmd = [sys.executable, str(SVG_UPDATE_SCRIPT), str(merged_report_path)]
    logger.info("Running: %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.stdout:
        logger.info(result.stdout.rstrip())
    if result.stderr:
        logger.warning(result.stderr.rstrip())

    return result.returncode


def main(argv: list[str] | None = None) -> int:
    """Entry point — read artifacts, update SVG, return exit code."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--artifacts-dir",
        default=str(DEFAULT_ARTIFACTS_DIR),
        help="Directory containing {provider}_schema_health.json files (default: %(default)s)",
    )
    parser.add_argument(
        "--fail-on-red",
        action="store_true",
        default=True,
        help="Exit with code 1 if any provider has red status (default: True)",
    )
    parser.add_argument(
        "--no-fail-on-red",
        dest="fail_on_red",
        action="store_false",
        help="Do not exit with code 1 on red providers",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Parse and report artifacts without updating the SVG",
    )

    args = parser.parse_args(argv)
    artifacts_dir = Path(args.artifacts_dir)

    if not artifacts_dir.exists():
        logger.info("Artifacts directory does not exist: %s — nothing to do", artifacts_dir)
        return 0

    logger.info("Reading schema health artifacts from: %s", artifacts_dir)
    results = _load_all_artifacts(artifacts_dir)

    if not results:
        logger.info("No valid artifacts found — SVG not updated")
        return 0

    # Summary
    red_providers = [p for p, (s, _) in results.items() if s == "red"]
    yellow_providers = [p for p, (s, _) in results.items() if s == "yellow"]
    green_providers = [p for p, (s, _) in results.items() if s == "green"]

    logger.info(
        "Summary: %d green, %d yellow, %d red",
        len(green_providers),
        len(yellow_providers),
        len(red_providers),
    )
    if red_providers:
        logger.warning("Red providers (schema stale or broken): %s", ", ".join(sorted(red_providers)))

    if args.dry_run:
        logger.info("--dry-run: skipping SVG update")
    else:
        merged_report_path = _write_merged_report(artifacts_dir, results)
        rc = _regenerate_svg(merged_report_path)
        if rc not in (0,):
            logger.warning("SVG update script exited with code %d — SVG may not be updated", rc)

    if args.fail_on_red and red_providers:
        logger.error(
            "CI HARD FAIL: %d provider(s) have red schema health: %s",
            len(red_providers),
            ", ".join(sorted(red_providers)),
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
