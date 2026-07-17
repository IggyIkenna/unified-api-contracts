"""Schema-level VCR cassette drift detector.

Walks a cassette directory looking for *.yaml cassette files. For each cassette
it attempts to validate recorded responses against UAC Pydantic models (when
available). Writes a JSON report and exits 0 (no drift) or 1 (drift detected).

Usage:
    python -m unified_api_contracts.testing.detect_cassette_drift \\
        --cassette-dir unified-api-contracts/external \\
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
from pydantic import BaseModel, ValidationError

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
        except (ImportError, ModuleNotFoundError, AttributeError, OSError):
            continue
        for _attr, obj in inspect.getmembers(mod, inspect.isclass):
            try:
                if issubclass(obj, BaseModel) and obj is not BaseModel:
                    registry[obj.__name__.lower()] = obj
            except TypeError:
                pass
    return registry


def _cassette_name_hint(path: Path) -> str:
    return path.stem.lower().replace("-", "_")


def _cassette_venue_module(path: Path) -> str | None:
    """Return the UAC module prefix owning this cassette, e.g.
    ``unified_api_contracts.external.bitget`` for ``external/bitget/mocks/ticker.yaml``.

    A cassette records what a VENUE returned, so the only models that can legitimately
    describe it are that venue's own RAW response models. Returns None when the path is not
    under ``external/<venue>/`` (then we refuse to guess — see _select_model).
    """
    parts = path.parts
    try:
        i = len(parts) - 1 - parts[::-1].index("external")
    except ValueError:
        return None
    if i + 1 >= len(parts):
        return None
    return f"{_uac_pkg.__name__}.external.{parts[i + 1]}"


def _select_model(cassette_path: Path, model_registry: dict[str, type]) -> type | None:
    """Pick the model to validate a cassette against — VENUE-SCOPED, or None.

    WHY THIS IS SCOPED (2026-07-17). The previous selector substring-matched the bare filename
    stem against a registry of EVERY BaseModel in UAC (~2172 of them), in BOTH directions, first
    dict hit wins:

        for key, cls in model_registry.items():
            if key in hint or hint in key:   # "ticker" in "canonicalticker" -> match!
                model = cls; break

    That is a category error: a cassette holds the RAW venue envelope, while ``Canonical*`` models
    describe the NORMALIZED shape an adapter EMITS after transforming it. They can never validate,
    so the nightly reported drift forever. Measured on 2026-07-17: 28 "drifted" of 179 — 28/28
    FALSE POSITIVES. 13 were canonical-vs-raw (``CanonicalTicker`` x8 for bitget/bybit/coingecko/
    deribit/ecb/kraken/okx/upbit, ``CanonicalMarketStateEvent`` x4, ``CanonicalOrderBook`` x1);
    10 were cross-venue collisions the stem match invented — alchemy's
    ``aave_get_user_account_data.yaml`` matched nautilus ``Account`` on the substring "account",
    hyperliquid ``*order*`` matched nautilus ``Order``, defillama ``yields`` matched
    ``YahooFinanceYieldSnapshot``, copper ``wallet_balances`` matched risk ``Balance``,
    hyperliquid ``meta`` matched ``FeatureMetadata``.

    Scoping to the cassette's OWN ``external/<venue>`` package fixes both classes at once and — the
    reason we scope rather than tighten the string match — PRESERVES the genuine matches, which all
    rely on the ``hint in key`` direction within their own venue:
    ``circle_cctp/attestation.yaml`` -> ``CircleCctpAttestation``, ``coinbase/products.yaml`` ->
    ``CoinbaseProductsResponse``, ``kraken_futures/tickers.yaml`` -> ``KrakenFuturesTickersResponse``
    (raw-vs-raw, all passing). A venue with no raw schema of its own (bitget has only
    ``normalize.py``) now correctly matches NOTHING and is SKIPPED.

    SKIP, NEVER GUESS: an unmatched cassette is reported as unvalidated, not as drift. Guessing is
    what produced 4 months of noise.
    """
    venue_mod = _cassette_venue_module(cassette_path)
    if venue_mod is None:
        return None
    hint = _cassette_name_hint(cassette_path)
    candidates: list[tuple[str, type]] = []
    for key, cls in model_registry.items():
        # Only this venue's OWN models are candidates.
        mod = getattr(cls, "__module__", "")
        if mod != venue_mod and not mod.startswith(venue_mod + "."):
            continue
        if key in hint or hint in key:
            candidates.append((key, cls))
    if not candidates:
        return None
    # MOST-SPECIFIC wins, not first-dict-hit. A cassette records the FULL response, so when a venue
    # models both the envelope and the inner object the envelope is the right node — and its name is
    # the longer one. Measured: kraken ships BOTH KrakenTickerData (inner, schemas.py:8) and
    # KrakenTickerResponse (envelope, schemas.py:22); hint "ticker" substring-matches both, and the
    # old first-hit-wins took whichever dict order surfaced first — picking the inner model made
    # kraken/mocks/ticker.yaml report drift forever against a cassette that is perfectly correct.
    candidates.sort(key=lambda kc: len(kc[0]), reverse=True)
    return candidates[0][1]


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

    model: type | None = _select_model(cassette_path, model_registry)

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

            except ValidationError as exc:
                errors.append(f"{cassette_path.name}[interaction={idx}]: {type(exc).__name__}: {exc}")
        else:
            # An EMPTY body is not malformed JSON — it is a body that was never JSON. These are
            # BINARY endpoints whose payload the recorder did not persist (the cassette carries
            # `string: ""`): databento's DBN timeseries and tardis' `datasets_csv_download`
            # (.csv.gz). `json.loads("")` raises, so all 3 were reported every night as
            # "may indicate API format change" against endpoints that never returned JSON at all.
            # Nothing about them can drift in a way this detector can see, so skip them.
            if isinstance(response_body, str) and response_body.strip():
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
    logger.info("%s", summary)
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
