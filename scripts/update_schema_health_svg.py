"""Update docs/schema_health.svg based on pytest JSON report from integration tests.

Usage:
    pytest tests/vcr/ -m integration --json-report --json-report-file=test-results.json -q
    python3 scripts/update_schema_health_svg.py test-results.json

The script reads the test results, maps each provider to pass/fail/skip,
re-runs generate_schema_version_matrix.py logic, and overwrites the SVG
with status colours updated from test outcomes.

Pass/fail mapping:
    All tests for provider pass → green
    Any test for provider fails  → red
    All tests for provider skip  → yellow (no cassette)
    No tests for provider        → uses YAML-declared status

If the JSON report is not provided or not found, the SVG is regenerated from YAML only.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# Reuse the shared loader from generate_schema_version_matrix
sys.path.insert(0, str(REPO_ROOT / "scripts"))


def _extract_provider_results(report_path: Path) -> dict[str, str]:
    """Return provider → 'green' | 'yellow' | 'red' from pytest JSON report."""
    with report_path.open(encoding="utf-8") as fh:
        report = json.load(fh)

    provider_outcomes: dict[str, list[str]] = {}

    for test in report.get("tests", []):
        # Test node IDs look like:
        #   tests/vcr/test_schema_health.py::TestBinanceSchemaHealth::test_ticker_schema_validates
        #   tests/vcr/test_schema_health.py::test_cassette_body_parseable[binance-ticker_24hr.yaml]
        node_id: str = test.get("nodeid", "")
        outcome: str = test.get("outcome", "skipped")  # passed | failed | skipped

        if "test_schema_health" not in node_id:
            continue

        # Extract provider name
        provider: str | None = None
        if "test_cassette_body_parseable" in node_id:
            # parametrize form: [binance-ticker_24hr.yaml]
            start = node_id.rfind("[")
            end = node_id.rfind("]")
            if start != -1 and end != -1:
                param = node_id[start + 1 : end]
                provider = param.split("-")[0]
        else:
            # class form: TestBinanceSchemaHealth
            for part in node_id.split("::"):
                if part.startswith("Test") and part.endswith("SchemaHealth"):
                    # e.g. TestBinanceSchemaHealth → binance
                    inner = part[len("Test") : -len("SchemaHealth")]
                    provider = inner.lower()
                    break

        if provider:
            provider_outcomes.setdefault(provider, []).append(outcome)

    # Reduce: any fail → red; all skip → yellow; any pass → green
    results: dict[str, str] = {}
    for provider, outcomes in provider_outcomes.items():
        if "failed" in outcomes:
            results[provider] = "red"
        elif all(o == "skipped" for o in outcomes):
            results[provider] = "yellow"
        else:
            results[provider] = "green"

    return results


def main() -> int:

    from generate_schema_version_matrix import (
        ProviderHealth,
        load_providers,
        write_svg,
    )

    test_results: dict[str, str] = {}

    if len(sys.argv) > 1:
        report_path = Path(sys.argv[1])
        if report_path.exists():
            test_results = _extract_provider_results(report_path)
            print(f"Loaded test results from {report_path}: {len(test_results)} providers")
        else:
            print(f"WARN: report file {report_path} not found — using YAML status only")

    providers = load_providers()

    # Override computed_status with test results where available
    updated: list[ProviderHealth] = []
    for p in providers:
        if p.name in test_results:
            override = test_results[p.name]
            updated.append(p._replace(computed_status=override))
        else:
            updated.append(p)

    write_svg(updated)

    red = [p for p in updated if p.computed_status == "red"]
    yellow = [p for p in updated if p.computed_status == "yellow"]
    green = [p for p in updated if p.computed_status == "green"]
    print(f"SVG updated: {len(green)} green, {len(yellow)} yellow, {len(red)} red")

    if red:
        print("RED providers:")
        for p in red:
            print(f"  {p.name}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
