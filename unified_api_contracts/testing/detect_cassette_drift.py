"""Schema-level VCR cassette drift detector.

Walks a cassette directory looking for *.yaml cassette files. For each cassette
it attempts to validate recorded responses against UAC Pydantic models (when
available). Writes a JSON report and exits 0 (no drift) or 1 (drift detected).

Usage:
    python -m unified_api_contracts.testing.detect_cassette_drift \\
        --cassette-dir unified-api-contracts/unified_api_contracts_external \\
        --output-json drift_report.json

    python -m unified_api_contracts.testing.detect_cassette_drift \\
        --cassette-dir unified-api-contracts/ \\
        --venues binance okx bybit \\
        --output-json drift_report.json
"""

from __future__ import annotations

import argparse
import importlib
import inspect
import json
import logging
import pkgutil
import sys
from pathlib import Path

import yaml
from pydantic import BaseModel

import unified_api_contracts as _uac_pkg

logger = logging.getLogger(__name__)


def _load_yaml(path: Path) -> object:
    with path.open() as fh:
        return yaml.safe_load(fh)


# ---------------------------------------------------------------------------
# Pydantic model registry (populated lazily from UAC package)
# ---------------------------------------------------------------------------


def _build_model_registry() -> dict[str, type]:
    """Walk the UAC package and build a {name_fragment: ModelClass} registry."""
    registry: dict[str, type] = {}
    for _importer, modname, _ispkg in pkgutil.walk_packages(
        path=_uac_pkg.__path__,
        prefix=_uac_pkg.__name__ + ".",
        onerror=lambda _name: None,
    ):
        try:
            mod = importlib.import_module(modname)
        except Exception:
            continue
        for _attr, obj in inspect.getmembers(mod, inspect.isclass):
            try:
                if issubclass(obj, BaseModel) and obj is not BaseModel:
                    registry[obj.__name__.lower()] = obj
            except Exception:
                pass
    return registry


def _cassette_name_hint(path: Path) -> str:
    return path.stem.lower().replace("-", "_")


# ---------------------------------------------------------------------------
# Drift detection logic
# ---------------------------------------------------------------------------


def _validate_cassette(
    cassette_path: Path,
    model_registry: dict[str, type],
) -> list[str]:
    """Validate a single cassette file. Returns list of error strings."""
    raw = _load_yaml(cassette_path)
    if raw is None:
        return []

    if not isinstance(raw, dict):
        return [f"Unexpected cassette structure (root is not a mapping): {cassette_path.name}"]

    interactions_val: object = raw.get("interactions")
    interactions: list[object] = list(interactions_val) if isinstance(interactions_val, list) else []
    if not interactions:
        return []

    hint = _cassette_name_hint(cassette_path)
    model: type | None = None
    for key, cls in model_registry.items():
        if key in hint or hint in key:
            model = cls
            break

    errors: list[str] = []
    for idx, interaction in enumerate(interactions):
        if not isinstance(interaction, dict):
            continue

        response_val: object = interaction.get("response")
        response_body: object = None
        if isinstance(response_val, dict):
            body_val: object = response_val.get("body")
            if isinstance(body_val, dict):
                response_body = body_val.get("string")
        if response_body is None:
            continue

        if model is not None:
            try:
                if isinstance(response_body, str):
                    data = json.loads(response_body)
                elif isinstance(response_body, dict):
                    data = response_body
                else:
                    continue

                if isinstance(data, list):
                    for item in data[:5]:
                        model.model_validate(item)
                else:
                    model.model_validate(data)

            except Exception as exc:
                errors.append(f"{cassette_path.name}[interaction={idx}]: {type(exc).__name__}: {exc}")
        else:
            if isinstance(response_body, str):
                try:
                    json.loads(response_body)
                except ValueError:
                    errors.append(
                        f"{cassette_path.name}[interaction={idx}]: "
                        f"response body is not valid JSON (may indicate API format change)"
                    )

    return errors


def run_drift_detection(
    cassette_dir: Path,
    output_json: Path,
    venues: list[str] | None = None,
) -> bool:
    """Walk cassette_dir for *.yaml files, optionally filtered by venue name.

    Args:
        cassette_dir: Root directory containing cassette YAML files.
        output_json: Path to write the JSON drift report.
        venues: If provided, only check cassettes whose path contains a venue name.

    Returns:
        True if drift was detected, False otherwise.
    """
    all_cassettes = sorted(cassette_dir.rglob("*.yaml"))

    if venues:
        cassette_files = [p for p in all_cassettes if any(v.lower() in str(p).lower() for v in venues)]
        logger.info("Venue filter %s: %d of %d cassettes selected", venues, len(cassette_files), len(all_cassettes))
    else:
        cassette_files = all_cassettes

    total_checked = len(cassette_files)

    if total_checked == 0:
        logger.info("No cassette files found under %s", cassette_dir)
        report: dict[str, object] = {
            "summary": f"No cassette files found under {cassette_dir}.",
            "drifted_cassettes": [],
            "total_checked": 0,
        }
        output_json.write_text(json.dumps(report, indent=2))
        return False

    model_registry = _build_model_registry()
    logger.info("Loaded %d Pydantic models from UAC registry", len(model_registry))
    logger.info("Checking %d cassette files...", total_checked)

    drifted: list[str] = []
    all_errors: list[str] = []

    for cassette_path in cassette_files:
        errors = _validate_cassette(cassette_path, model_registry)
        if errors:
            drifted.append(str(cassette_path.relative_to(cassette_dir)))
            all_errors.extend(errors)
            for err in errors:
                logger.warning("DRIFT: %s", err)
        else:
            logger.debug("OK: %s", cassette_path.name)

    drift_detected = len(drifted) > 0
    if drift_detected:
        summary = (
            f"{len(drifted)} of {total_checked} cassette(s) have schema drift. "
            f"Errors: {'; '.join(all_errors[:5])}" + (" (truncated)" if len(all_errors) > 5 else "")
        )
    else:
        summary = f"All {total_checked} cassette(s) match expected schemas."

    report = {
        "summary": summary,
        "drifted_cassettes": drifted,
        "all_errors": all_errors,
        "total_checked": total_checked,
    }
    output_json.write_text(json.dumps(report, indent=2))
    logger.info("Report written to %s", output_json)
    logger.info(summary)
    return drift_detected


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Detect schema drift in VCR cassettes against UAC Pydantic models.",
    )
    parser.add_argument(
        "--cassette-dir",
        required=True,
        type=Path,
        help="Root directory to search for *.yaml cassette files recursively.",
    )
    parser.add_argument(
        "--output-json",
        required=True,
        type=Path,
        help="Path for the JSON drift report output.",
    )
    parser.add_argument(
        "--venues",
        nargs="*",
        default=None,
        metavar="VENUE",
        help="Only check cassettes whose path contains one of these venue names.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        default=False,
        help="Enable debug logging.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s  %(message)s",
    )
    cassette_dir = args.cassette_dir.resolve()
    if not cassette_dir.exists():
        logger.error("cassette-dir does not exist: %s", cassette_dir)
        return 2

    drift_detected = run_drift_detection(
        cassette_dir=cassette_dir,
        output_json=args.output_json.resolve(),
        venues=args.venues,
    )
    return 1 if drift_detected else 0


if __name__ == "__main__":
    sys.exit(main())
