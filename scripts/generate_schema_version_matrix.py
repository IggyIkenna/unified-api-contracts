"""Generate docs/SCHEMA_VERSION_MATRIX.md and docs/schema_health.svg.

Reads unified_api_contracts/provider_api_versions.yaml, imports each provider
schema module, and compares the YAML api_version with the module-level
__api_version__ attribute.

Status logic:
  - YAML api_version != schema __api_version__  →  red
  - last_verified more than 90 days ago          →  yellow (unless already red)
  - Otherwise                                    →  status from YAML

Usage:
    python3 scripts/generate_schema_version_matrix.py
    python3 scripts/generate_schema_version_matrix.py --count-red   # outputs count only

Outputs:
    docs/SCHEMA_VERSION_MATRIX.md
    docs/schema_health.svg
"""

from __future__ import annotations

import importlib
import logging
import math
import sys
from datetime import date
from pathlib import Path
from typing import NamedTuple

import yaml

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[1]
_YAML_PATH = _REPO_ROOT / "unified_api_contracts" / "provider_api_versions.yaml"
_DOCS_DIR = _REPO_ROOT / "docs"
_MATRIX_MD = _DOCS_DIR / "SCHEMA_VERSION_MATRIX.md"
_SVG_PATH = _DOCS_DIR / "schema_health.svg"

_STALE_DAYS = 90

# Providers that are internal or infrastructure (not external APIs)
_SKIP_MODULE_IMPORT = frozenset(
    {
        "cloud_sdks",
        "defi",
        "macro",
        "mev",
        "odds_engine",
        "onchain",
        "prime_broker",
        "regulatory",
        "sentiment",
        "sports",
        "venue_manifest",
        "fix",
        "nautilus",
    }
)


class ProviderHealth(NamedTuple):
    """Immutable record for one provider's health state."""

    name: str
    yaml_version: str
    schema_version: str  # from __api_version__ or "N/A"
    last_verified: str
    yaml_status: str
    computed_status: str  # green | yellow | red
    notes: str


def _read_yaml() -> dict[str, object]:
    with _YAML_PATH.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)  # type: ignore[return-value]


def _import_schema_version(provider_name: str) -> str:
    """Try to import the provider's schema module and return __api_version__.

    Returns "N/A" on any import failure.
    """
    if provider_name in _SKIP_MODULE_IMPORT:
        return "N/A"

    # Try the multi-file package (external contracts)
    module_paths = [
        f"unified_api_contracts.unified_api_contracts_external.{provider_name}",
        f"unified_api_contracts.schemas.{provider_name}",
    ]

    for mod_path in module_paths:
        try:
            mod = importlib.import_module(mod_path)
            ver = getattr(mod, "__api_version__", None)
            if ver is not None:
                return str(ver)
        except (ImportError, AttributeError):
            pass

    return "N/A"


def _compute_status(
    yaml_version: str,
    schema_version: str,
    last_verified: str,
    yaml_status: str,
) -> str:
    """Return 'green' | 'yellow' | 'red' based on comparison rules."""
    # Version mismatch → red (only when schema_version is known)
    if schema_version != "N/A" and yaml_version != schema_version:
        return "red"

    # Stale verification → yellow (unless YAML already marks red)
    if yaml_status == "red":
        return "red"

    try:
        verified_date = date.fromisoformat(last_verified)
        age = (date.today() - verified_date).days
        if age > _STALE_DAYS:
            return "yellow"
    except ValueError:
        return "yellow"

    return yaml_status if yaml_status in ("green", "yellow", "red") else "yellow"


def load_providers() -> list[ProviderHealth]:
    """Read YAML and compute ProviderHealth records for all providers."""
    data = _read_yaml()
    providers_raw: dict[str, object] = data.get("providers", {})  # type: ignore[assignment]

    results: list[ProviderHealth] = []
    for name, info in providers_raw.items():
        info_dict: dict[str, str] = info  # type: ignore[assignment]
        yaml_ver: str = str(info_dict.get("api_version", "v1"))
        last_verified: str = str(info_dict.get("last_verified", "2000-01-01"))
        yaml_status: str = str(info_dict.get("status", "yellow"))
        notes: str = str(info_dict.get("notes", ""))

        schema_ver = _import_schema_version(name)
        computed = _compute_status(yaml_ver, schema_ver, last_verified, yaml_status)

        results.append(
            ProviderHealth(
                name=name,
                yaml_version=yaml_ver,
                schema_version=schema_ver,
                last_verified=last_verified,
                yaml_status=yaml_status,
                computed_status=computed,
                notes=notes,
            )
        )

    return results


def _status_icon(status: str) -> str:
    return {"green": "green", "yellow": "yellow", "red": "red"}.get(status, "yellow")


def write_matrix_md(providers: list[ProviderHealth]) -> None:
    """Write docs/SCHEMA_VERSION_MATRIX.md."""
    today = date.today().isoformat()
    green = [p for p in providers if p.computed_status == "green"]
    yellow = [p for p in providers if p.computed_status == "yellow"]
    red = [p for p in providers if p.computed_status == "red"]

    lines: list[str] = [
        "# Schema Version Matrix",
        "",
        f"> Auto-generated by `scripts/generate_schema_version_matrix.py` on {today}.",
        "> Do not edit manually — regenerate with `python3 scripts/generate_schema_version_matrix.py`.",
        "",
        "## Summary",
        "",
        "| Status    | Count  |",
        "| --------- | ------ |",
        f"| green  | {len(green)}     |",
        f"| yellow | {len(yellow)}     |",
        f"| red    | {len(red)}      |",
        f"| **Total** | **{len(providers)}** |",
        "",
        "## Status Definitions",
        "",
        "| Status    | Meaning                                                                                                    |",
        "| --------- | ---------------------------------------------------------------------------------------------------------- |",
        "| green  | Schema validated against live API within last 90 days                                                      |",
        "| yellow | Not verified recently (> 90 days) OR verification pending                                                  |",
        "| red    | Known breaking change: `__api_version__` in schema file does not match YAML, or YAML explicitly set to red |",
        "",
        "## Full Matrix",
        "",
        "| Provider             | YAML API Version | Schema `__api_version__` | Last Verified | Status    | Notes                                                                |",
        "| -------------------- | ---------------- | ------------------------ | ------------- | --------- | -------------------------------------------------------------------- |",
    ]

    for p in providers:
        status_cell = f"{p.computed_status}"
        lines.append(
            f"| {p.name:<20} | {p.yaml_version:<16} | {p.schema_version:<24} | {p.last_verified} | {status_cell:<9} | {p.notes} |"
        )

    lines += [
        "",
        "---",
        "",
        "_See `docs/schema_health.svg` for the visual grid._",
        "",
    ]

    _MATRIX_MD.write_text("\n".join(lines), encoding="utf-8")
    logger.info(f"Written: {_MATRIX_MD}")


def write_svg(providers: list[ProviderHealth]) -> None:
    """Write docs/schema_health.svg — a coloured grid, 8 cells per row."""
    today = date.today().isoformat()

    cell_w = 120
    cell_h = 36
    cell_gap = 4
    cols = 8
    header_h = 44  # space for title

    rows = math.ceil(len(providers) / cols)
    total_w = cols * (cell_w + cell_gap)
    total_h = header_h + rows * (cell_h + cell_gap) + cell_gap

    color_fill = {
        "green": "#e8f5e9",
        "yellow": "#fff3e0",
        "red": "#ffebee",
    }
    color_stroke = {
        "green": "#4caf50",
        "yellow": "#ff9800",
        "red": "#f44336",
    }
    status_prefix = {
        "green": "v",
        "yellow": "~",
        "red": "!",
    }

    svg_parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{total_w}" height="{total_h}" font-family="monospace" font-size="11">',
        f'  <rect width="{total_w}" height="{total_h}" fill="#fafafa" rx="4"/>',
        f'  <text x="{total_w // 2}" y="30" text-anchor="middle" font-size="14" font-weight="bold" fill="#333">',
        f"    Schema Health Matrix \u2014 {today}",
        "  </text>",
    ]

    for idx, p in enumerate(providers):
        col = idx % cols
        row = idx // cols
        x = cell_gap + col * (cell_w + cell_gap)
        y = header_h + row * (cell_h + cell_gap)
        cx = x + cell_w // 2

        fill = color_fill.get(p.computed_status, color_fill["yellow"])
        stroke = color_stroke.get(p.computed_status, color_stroke["yellow"])
        prefix = status_prefix.get(p.computed_status, "~")

        # Truncate long names for display
        display_name = p.name if len(p.name) <= 13 else p.name[:12] + "\u2026"

        svg_parts += [
            "  <g>",
            f'    <rect x="{x}" y="{y}" width="{cell_w}" height="{cell_h}" fill="{fill}" stroke="{stroke}" stroke-width="1.5" rx="3"/>',
            f'    <text x="{cx}" y="{y + 14}" text-anchor="middle" fill="#333" font-size="10">{display_name}</text>',
            f'    <text x="{cx}" y="{y + 27}" text-anchor="middle" fill="{stroke}" font-weight="bold" font-size="10">{prefix} {p.yaml_version}</text>',
            f"    <title>{p.name} \u2014 {p.yaml_version} \u2014 {p.computed_status} (verified {p.last_verified})</title>",
            "  </g>",
        ]

    svg_parts += [
        "  <!-- legend: green=#4caf50 -->",
        "  <!-- legend: yellow=#ff9800 -->",
        "  <!-- legend: red=#f44336 -->",
        "</svg>",
    ]

    _SVG_PATH.write_text("\n".join(svg_parts) + "\n", encoding="utf-8")
    logger.info(f"Written: {_SVG_PATH}")


def main() -> int:
    logging.basicConfig(level=logging.INFO)

    count_red_mode = "--count-red" in sys.argv

    # Ensure repo root is importable so provider modules resolve
    repo_root_str = str(_REPO_ROOT)
    if repo_root_str not in sys.path:
        sys.path.insert(0, repo_root_str)

    providers = load_providers()

    red_count = sum(1 for p in providers if p.computed_status == "red")

    if count_red_mode:
        print(red_count)
        return 0

    write_matrix_md(providers)
    write_svg(providers)

    green = sum(1 for p in providers if p.computed_status == "green")
    yellow = sum(1 for p in providers if p.computed_status == "yellow")

    logger.info(f"Matrix: {green} green, {yellow} yellow, {red_count} red ({len(providers)} total)")

    if red_count:
        logger.warning(f"RED providers ({red_count}):")
        for p in providers:
            if p.computed_status == "red":
                logger.warning(f"  {p.name}: YAML={p.yaml_version!r} schema={p.schema_version!r}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
