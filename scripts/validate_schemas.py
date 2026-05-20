#!/usr/bin/env python3
"""Validate live API responses against UAC cassette baselines.

For each `collected_responses/<venue>/<stem>.json` produced by
`collect_responses.py`, locate the matching cassette in
`unified_api_contracts/external/<venue>/mocks/<stem>.yaml` and structurally
diff the live response against the cassette's recorded response body.

Drift signals:
- Missing keys in live response (vs cassette baseline)         → ❌ DRIFT
- Type change for a key (e.g. string → number, dict → list)    → ❌ DRIFT
- HTTP non-2xx                                                  → ❌ ENDPOINT_BROKEN
- Extra keys in live (additive)                                 → ✅ + additive note
- Cassette missing or stub                                      → ⚠️  (counted as warning)

Output: one line per response to stdout. The workflow's `Validate schemas`
step redirects stdout to `validation_report.txt`, and the drift_check step
counts the ❌ markers.

Exits 0 always — the workflow's count-based drift check is authoritative.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
EXTERNAL_DIR = ROOT / "unified_api_contracts" / "external"
COLLECTED_DIR = ROOT / "collected_responses"


def main() -> int:
    if not COLLECTED_DIR.exists():
        print("⚠️  No collected_responses/ directory — collect_responses.py did not run")
        return 0

    collected_files = sorted(COLLECTED_DIR.glob("*/*.json"))
    if not collected_files:
        print("⚠️  No collected responses to validate")
        return 0

    lines: list[str] = []
    for cf in collected_files:
        lines.append(_validate_one(cf))

    for line in lines:
        print(line)

    failed = sum(1 for line in lines if line.startswith("❌"))
    passed = sum(1 for line in lines if line.startswith("✅"))
    warned = len(lines) - failed - passed
    print()
    print(f"Summary: {passed} ✅ / {failed} ❌ / {warned} ⚠️")
    return 0


def _validate_one(collected_path: Path) -> str:
    venue = collected_path.parent.name
    stem = collected_path.stem
    label = f"{venue}/{stem}"

    cassette_path = EXTERNAL_DIR / venue / "mocks" / f"{stem}.yaml"
    if not cassette_path.exists():
        return f"⚠️  {label}: no matching cassette"

    try:
        live = json.loads(collected_path.read_text())
    except json.JSONDecodeError as exc:
        return f"❌ {label}: collected response not valid JSON: {exc}"

    http_status = live.get("response_status")
    if http_status is None or http_status >= 400:
        return f"❌ {label}: ENDPOINT_BROKEN http={http_status}"

    try:
        cassette = yaml.safe_load(cassette_path.read_text()) or {}
    except yaml.YAMLError as exc:
        return f"⚠️  {label}: cassette YAML parse: {exc}"

    interactions = cassette.get("interactions") or []
    if not interactions:
        return f"⚠️  {label}: cassette is stub"

    baseline_body_str = (
        ((interactions[0].get("response") or {}).get("body") or {}).get("string")
    )
    if baseline_body_str is None:
        return f"⚠️  {label}: cassette response has no body"

    try:
        baseline = json.loads(baseline_body_str)
    except json.JSONDecodeError:
        return f"⚠️  {label}: cassette baseline not JSON"

    live_body = live.get("response_body")
    if not isinstance(live_body, (dict, list)):
        return f"❌ {label}: live response not JSON object/array (got {type(live_body).__name__})"

    missing, type_diffs, extras = _structural_diff(baseline, live_body)
    if missing or type_diffs:
        details: list[str] = []
        if missing:
            details.append(f"missing: {missing[:5]}")
        if type_diffs:
            details.append(f"type-diffs: {type_diffs[:5]}")
        return f"❌ {label}: DRIFT — {' | '.join(details)}"

    if extras:
        return f"✅ {label} (additive: {len(extras)} new keys)"
    return f"✅ {label}"


def _structural_diff(
    baseline: Any, live: Any, path: str = "$"
) -> tuple[list[str], list[str], list[str]]:
    """Return (missing_paths, type_diff_paths, extra_paths) for live vs baseline.

    Treats int/float as compatible (both numeric). For lists, only diffs the
    first element's shape (most provider responses are homogeneous arrays).
    """
    missing: list[str] = []
    type_diffs: list[str] = []
    extras: list[str] = []

    b_type = _coarse_type(baseline)
    l_type = _coarse_type(live)
    if b_type != l_type:
        type_diffs.append(f"{path}: {b_type}→{l_type}")
        return missing, type_diffs, extras

    if isinstance(baseline, dict):
        assert isinstance(live, dict)
        # Time-series dicts (keys are unix timestamps / ISO dates) drift naturally
        # as new datapoints land; only validate one value's shape.
        if baseline and _is_timeseries_keyed(baseline):
            if live and _is_timeseries_keyed(live):
                b_sample = next(iter(baseline.values()))
                l_sample = next(iter(live.values()))
                m, t, e = _structural_diff(b_sample, l_sample, f"{path}.*")
                missing.extend(m)
                type_diffs.extend(t)
                extras.extend(e)
            else:
                type_diffs.append(f"{path}: timeseries-dict→non-timeseries")
            return missing, type_diffs, extras
        for k, v in baseline.items():
            sub = f"{path}.{k}"
            if k not in live:
                missing.append(sub)
                continue
            m, t, e = _structural_diff(v, live[k], sub)
            missing.extend(m)
            type_diffs.extend(t)
            extras.extend(e)
        for k in live:
            if k not in baseline:
                extras.append(f"{path}.{k}")
    elif isinstance(baseline, list):
        assert isinstance(live, list)
        if baseline and live:
            m, t, e = _structural_diff(baseline[0], live[0], f"{path}[0]")
            missing.extend(m)
            type_diffs.extend(t)
            extras.extend(e)

    return missing, type_diffs, extras


_TIMESTAMP_KEY_RE = __import__("re").compile(r"^(\d{10}|\d{13}|\d{4}-\d{2}-\d{2})")


def _is_timeseries_keyed(d: dict[str, Any]) -> bool:
    """True if all keys look like unix seconds, unix millis, or ISO dates."""
    return all(isinstance(k, str) and _TIMESTAMP_KEY_RE.match(k) for k in d.keys())


def _coarse_type(value: Any) -> str:
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "list"
    if isinstance(value, dict):
        return "dict"
    if value is None:
        return "null"
    return type(value).__name__


if __name__ == "__main__":
    sys.exit(main())
