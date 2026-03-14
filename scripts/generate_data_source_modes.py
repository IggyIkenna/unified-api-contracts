#!/usr/bin/env python3
"""Extract providers with 'modes' from provider_api_versions.yaml and print a markdown table.

Run from unified-api-contracts repo root:
    python scripts/generate_data_source_modes.py
    python scripts/generate_data_source_modes.py --check-secrets  # stub: future secret validation

Output columns: provider, modes, has_testnet, testnet_keys, data_type, keys_public, keys_private, ui_docs, gap.
"""

from pathlib import Path


def _load_yaml(path: Path) -> dict:
    """Load YAML using PyYAML, ruamel.yaml, or fallback to regex parsing."""
    try:
        import yaml

        with path.open() as f:
            return yaml.safe_load(f)
    except ImportError:
        pass
    try:
        from ruamel.yaml import YAML

        y = YAML(typ="safe")
        with path.open() as f:
            return y.load(f)
    except ImportError:
        pass
    return _parse_yaml_regex(path)


def _parse_yaml_regex(path: Path) -> dict:
    """Fallback: parse provider/modes via simple line parsing."""
    import re

    data: dict = {"providers": {}}
    current_provider: str | None = None
    for line in path.read_text().splitlines():
        m = re.match(r"^  ([a-z][a-z0-9_]*):\s*$", line)
        if m:
            current_provider = m.group(1)
            data["providers"][current_provider] = {}
            continue
        m = re.match(r"^    modes:\s*\[(.*)\]", line)
        if m and current_provider:
            modes_str = m.group(1).strip()
            modes = [s.strip() for s in modes_str.split(",")]
            data["providers"][current_provider]["modes"] = modes
    return data


def _get(cfg: dict, key: str, default: str = "") -> str:
    """Get value as string for table display."""
    val = cfg.get(key)
    if val is None:
        return default
    if isinstance(val, bool):
        return "✓" if val else "✗"
    if isinstance(val, list):
        return ", ".join(str(v) for v in val)
    return str(val)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Generate data source modes table from provider manifest")
    parser.add_argument(
        "--check-secrets",
        action="store_true",
        help="(Stub) Future: validate secret_names against Secret Manager",
    )
    args = parser.parse_args()

    if args.check_secrets:
        # Stub: future secret validation
        pass

    repo_root = Path.cwd()
    yaml_path = repo_root / "unified_api_contracts" / "config" / "provider_api_versions.yaml"
    if not yaml_path.exists():
        raise SystemExit(f"Not found: {yaml_path}. Run from unified-api-contracts repo root.")

    data = _load_yaml(yaml_path)
    providers = data.get("providers") or {}

    rows: list[dict[str, str]] = []
    for name, cfg in sorted(providers.items()):
        modes = cfg.get("modes")
        if modes is None:
            continue
        modes_str = ", ".join(str(m) for m in modes)
        has_testnet = _get(cfg, "has_testnet")
        testnet_keys = _get(cfg, "testnet_keys_we_have")
        data_type = _get(cfg, "data_type")
        keys_public = _get(cfg, "keys_public_we_have")
        keys_private = _get(cfg, "keys_private_we_have")
        ui_docs = "✓" if cfg.get("ui_docs_url") else ""

        # gap: missing keys or testnet when provider has testnet
        gap_parts: list[str] = []
        if cfg.get("has_testnet") and not cfg.get("testnet_keys_we_have"):
            gap_parts.append("testnet_keys")
        if cfg.get("data_type") in ("private", "both") and not cfg.get("keys_private_we_have"):
            gap_parts.append("keys_private")
        gap = ", ".join(gap_parts) if gap_parts else "—"

        rows.append(
            {
                "provider": name,
                "modes": modes_str,
                "has_testnet": has_testnet,
                "testnet_keys": testnet_keys,
                "data_type": data_type,
                "keys_public": keys_public,
                "keys_private": keys_private,
                "ui_docs": ui_docs,
                "gap": gap,
            }
        )

    print("| Provider | Modes | has_testnet | testnet_keys | data_type | keys_public | keys_private | ui_docs | gap |")
    print("|----------|-------|-------------|--------------|-----------|-------------|--------------|---------|-----|")
    for r in rows:
        print(
            f"| {r['provider']} | {r['modes']} | {r['has_testnet']} | {r['testnet_keys']} | "
            f"{r['data_type']} | {r['keys_public']} | {r['keys_private']} | {r['ui_docs']} | {r['gap']} |"
        )


if __name__ == "__main__":
    main()
